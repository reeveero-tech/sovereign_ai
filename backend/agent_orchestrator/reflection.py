# -*- coding: utf-8 -*-
"""R-841 (4.7): محرك الانعكاس والتصحيح — الانعكاس ليس اختياريًا.

كل خطوة (وكل حلقة قبل الرد النهائي) تمر بمرحلة انعكاس: هل تحقق معيار
النجاح؟ هل السياق صحيح؟ هل نعيد التخطيط؟ هل نسأل المستخدم؟ هل خطر؟
"""
from __future__ import annotations

from typing import Any, Dict

from .tool_registry import new_decision


def reflect(step_result: Dict[str, Any], step: Dict[str, Any],
            trace_ref: str) -> Dict[str, Any]:
    """انعكاس خطوة واحدة — يعيد قرار المتابعة/الإيقاف/السؤال."""
    if step_result["status"] == "success":
        ok = bool(step_result.get("output", {}).get("ok", True))
        if ok:
            return {"action": "continue",
                    "decision": new_decision(
                        step["step_id"], "reflection", "متابعة", [],
                        f"تحقق معيار النجاح: {step['success_criteria']}",
                        0.9, trace_ref)}
        return {"action": "replan",
                "decision": new_decision(
                    step["step_id"], "reflection", "إعادة تخطيط", [],
                    "النتيجة لم تحقق معيار النجاح رغم نجاح الاستدعاء —"
                    " نتيجة غير متوقعة تحتاج معالجة", 0.6, trace_ref)}
    if step_result["status"] == "denied":
        return {"action": "deny",
                "decision": new_decision(
                    step["step_id"], "reflection", "رفض حوكمي", [],
                    f"رفض بوابة: {step_result.get('error', {}).get('message')}",
                    1.0, trace_ref)}
    if step_result["status"] == "cancelled":
        return {"action": "stop",
                "decision": new_decision(
                    step["step_id"], "reflection", "إيقاف", [],
                    "إلغاء من المستخدم — توثيق ما تم وما لم يتم", 1.0,
                    trace_ref)}
    return {"action": "failure",
            "decision": new_decision(
                step["step_id"], "reflection", "فشل", [],
                f"فشل الخطوة: {step_result.get('error', {}).get('code')}",
                1.0, trace_ref)}


def reflect_loop(results: list, plan: Dict[str, Any], budget_spent: Dict,
                 trace_ref: str) -> Dict[str, Any]:
    """انعكاس الحلقة كاملة قبل الرد النهائي — إلزامي لا يجازف."""
    succeeded = [r for r in results if r["status"] == "success"]
    denied = [r for r in results if r["status"] == "denied"]
    if not results:
        return {"action": "stop", "reason": "لا نتائج — حلقة فارغة",
                "decision": new_decision("", "reflection", "إيقاف", [],
                                        "لا خطوة نُفذت", 1.0, trace_ref)}
    if denied and not succeeded:
        return {"action": "deny",
                "reason": denied[0].get("error", {}).get("message", "رفض"),
                "decision": new_decision("", "reflection", "رفض كامل", [],
                                        "كل الخطوات رُفضت حوكميًا", 1.0,
                                        trace_ref)}
    failed = [r for r in results if r["status"] == "failure"]
    if failed and not succeeded:
        # R-843: كشفه التقييم المستقل — فشل كل الخطوات كان يُعلن «اكتملت»
        msg = (failed[0].get("error") or {}).get("message") or "فشلت كل الخطوات"
        return {"action": "fail",
                "reason": f"لم تنجح أي خطوة ({len(failed)} فشلت): {msg}",
                "decision": new_decision("", "reflection", "فشل كامل", [],
                                        "لا خطوة ناجحة — لا رد بنجاح كاذب",
                                        1.0, trace_ref)}
    if budget_spent.get("steps", 0) >= plan["max_steps"]:
        return {"action": "stop",
                "reason": "بلغنا حد الخطوات الأقصى",
                "decision": new_decision("", "reflection", "إيقاف", [],
                                        "سقف الخطوات — لا دوران", 1.0,
                                        trace_ref)}
    return {"action": "reply",
            "reason": f"اكتملت {len(succeeded)}/{len(results)} خطوات",
            "decision": new_decision("", "reflection", "رد نهائي", [],
                                     f"انعكاس الحلقة: {len(succeeded)} نجحت"
                                     f" و{len(denied)} رفضت", 0.9, trace_ref)}
