# -*- coding: utf-8 -*-
"""R-841 (4.10): معالج الفشل وإعادة التخطيط — الفشل متوقع فلا انهيار.

التصنيف: فشل أداة (timeout/5xx) ← retry عبر المنفذ ثم إعادة تخطيط؛
فشل صلاحية (403/ScopeDenied) ← لا retry أعمى؛ فشل تكلفة/زمن ← إيقاف؛
فشل منطقي ← انعكاس وإعادة تخطيط؛ فشل سياق ← طبقة الفهم.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import schemas
from .tool_registry import new_decision

# أخطاء R-840 المصنفة — تُربط بالاسم لأن الاستيراد المزدوج قائم في المشروع
_RETRYABLE = {"ConnectorUnavailableError", "RateLimitedError",
              "ConnectorExecutionError", "TimeoutError", "ReadTimeout",
              "ConnectTimeout"}
_AUTH = {"ScopeDeniedError", "RequiresConnectionError"}
_BUDGET = {"BudgetExceededError", "max_steps", "max_time_s", "budget_exceeded",
           "session_cost", "user_cost"}


def classify(error: Dict[str, Any]) -> str:
    """تصنيف حاسم من رمز الخطأ — يحدد مسار المعالجة كله."""
    code = error.get("code", "") if isinstance(error, dict) else str(error)
    if code in _AUTH:
        return "auth"
    if code in _BUDGET or "budget" in str(code):
        return "budget"
    if code == "invalid_inputs":
        return "context"
    if code in _RETRYABLE:
        return "tool"
    return "logical"


class FailureHandler:
    """يقرر: retry (عبر المنفذ) أم إعادة تخطيط أم إيقاف أم طلب توضيح."""

    def __init__(self, planner):
        self.planner = planner

    def handle(self, step_result: Dict[str, Any], plan: Dict[str, Any],
               trace_ref: str) -> Dict[str, Any]:
        """يعيد قرار المعالجة + الخطة المحدثة إن لزم إعادة التخطيط."""
        err = step_result.get("error") or {}
        kind = classify(err)
        step_id = step_result["step_id"]
        if kind == "budget":
            return {"action": "stop", "reason": err.get("message", "تجاوز حد"),
                    "code": err.get("code", "budget"),
                    "plan": plan, "decision": new_decision(
                        step_id, "stop", "إيقاف", [],
                        f"فشل تكلفة/زمن: {err.get('message', '')}", 1.0,
                        trace_ref)}
        if kind == "auth":
            # لا retry على 401/403 بلا تحقق — إما توسيع أو بديل
            return {"action": "deny", "reason": err.get("message", "صلاحية"),
                    "code": err.get("code", "forbidden"),
                    "plan": plan, "decision": new_decision(
                        step_id, "escalate", "طلب صلاحية/بديل", [],
                        "رفض صلاحية: لا إعادة محاولة عمياء — طلب توسيع"
                        " أو أداة بديلة", 1.0, trace_ref)}
        if kind == "context":
            return {"action": "clarify", "reason": err.get("message", "سياق"),
                    "code": "context", "plan": plan, "decision": new_decision(
                        step_id, "clarify", "طلب توضيح", [],
                        "مرجع خاطئ أو مدخلات ناقصة — سؤال توضيحي واحد", 0.8,
                        trace_ref)}
        # فشل أداة أو منطقي: إعادة تخطيط (retry الكلي عند المنفذ قد حدث)
        try:
            new_plan = self.planner.replan(plan, step_id,
                                           err.get("message", ""), trace_ref)
            return {"action": "replan", "reason": err.get("message", "فشل"),
                    "code": err.get("code", "tool"), "plan": new_plan,
                    "decision": new_decision(
                        step_id, "replan", "إعادة تخطيط", [step_id],
                        f"فشل أداة ({err.get('code', '')}) — الخطة البديلة"
                        " تُسقط الخطوة أو تعيد المحاولة", 0.7, trace_ref)}
        except ValueError:
            return {"action": "stop", "reason": "لا بديل بعد الفشل",
                    "code": "no_fallback", "plan": plan, "decision": new_decision(
                        step_id, "stop", "إيقاف", [],
                        "فشل حرج بلا خطة بديلة — إيقاف صادق", 1.0, trace_ref)}
