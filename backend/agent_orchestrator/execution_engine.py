# -*- coding: utf-8 -*-
"""R-841 (4.4): محرك التنفيذ — كل استدعاء يمر: صلاحية ← موافقة ← تكلفة ← منفذ.

المنفذ هو محرك R-840 نفسه (retry/backoff/قاطع دائرة/Idempotency/تجديد 401
كلها موروثة لا معاد بناؤها). كل نتيجة خطوة تُسجَّل بالعقد 5.3 مع الأثر.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from . import schemas
from .approval_gate import ApprovalGate
from .governor import Budget
from .policy_gate import PolicyGate
from .tool_registry import ToolDefinition


class StepDenied(Exception):
    """رفض حوكمي (403) — برسالة وسبب وإجراء، لا صمت."""

    def __init__(self, reason: str, code: str = "forbidden"):
        super().__init__(reason)
        self.reason = reason
        self.code = code


class StepNeedsApproval(Exception):
    """الخطوة معلّقة على موافقة بشرية — لا تنفيذ بعدها."""

    def __init__(self, approval: Dict[str, Any]):
        super().__init__(f"بانتظار موافقة {approval['approval_id']}")
        self.approval = approval


class ExecutionEngine:
    """ينفّذ خطوة واحدة عبر البوابات الثلاث ثم المنفذ الموحد."""

    def __init__(self, tools, policy: PolicyGate, approvals: ApprovalGate,
                 connector_executor, connector_registry=None):
        self.tools = tools
        self.policy = policy
        self.approvals = approvals
        self.connector_executor = connector_executor   # R-840 executor
        self.connector_registry = connector_registry

    def _validated_inputs(self, step, tool) -> Dict[str, Any]:
        """مدخلات منقّاة أو رسالة الخطأ — لا استدعاء بمخطط فاسد."""
        try:
            schemas.validate(dict(step["inputs"]), tool.input_schema)
            return dict(step["inputs"])
        except schemas.SchemaError as exc:
            return {"_invalid": str(exc)}

    def dry_run(self, step: Dict[str, Any], actor_permissions,
                budget: Budget, actor: str = "user"
                ) -> Dict[str, Any]:
        """(4.16) معاينة جافة: ما سيُفعل دون تنفيذ — تُستخدم قبل الموافقة."""
        tool = self.tools.get(step["tool_id"])
        pd = self.policy.check(tool, actor_permissions, actor)
        est = {"tool": tool.tool_id, "connector": tool.connector_id,
               "operation": tool.operation,
               "inputs": self._validated_inputs(step, tool),
               "access": tool.access, "risk": tool.risk,
               "would_require_approval": pd.requires_approval,
               "policy_allows": pd.allowed,
               "policy_reason": pd.reason,
               "estimated_cost": tool.estimated_cost,
               "estimated_time_s": tool.estimated_time_s}
        return {"ok": pd.allowed, "preview": est}

    def execute(self, step: Dict[str, Any], actor_permissions,
                budget: Budget, session_id: str, actor: str = "user",
                trace_ref: str = "", tracer=None
                ) -> Dict[str, Any]:
        """تنفيذ خطوة عبر البوابات — يعيد نتيجة بعقد 5.3."""
        tool = self.tools.get(step["tool_id"])
        t0 = time.monotonic()
        span_tracer = tracer

        def _result(status, output=None, error=None):
            r = {"step_id": step["step_id"], "status": status,
                 "output": output or {}, "error": error,
                 "cost": tool.estimated_cost,
                 "duration_ms": int((time.monotonic() - t0) * 1000),
                 "trace_ref": trace_ref}
            schemas.validate(r, schemas.STEP_RESULT_SCHEMA)
            if span_tracer is not None:
                span_tracer.span(step["step_id"], dict(step["inputs"]),
                                 dict(r["output"]), r["duration_ms"], status)
            return r

        # بوابة ١: الصلاحية — قبل التنفيذ لا بعده
        pd = self.policy.check(tool, actor_permissions, actor)
        if not pd.allowed:
            return _result("denied", error={"code": pd.code,
                                            "message": pd.reason,
                                            "action": "widen_or_alternative"})
        # بوابة ٢: الموافقة (إن لزمت) — معتمدة سلفًا (جلسة أو مرة واحدة)؟
        if pd.requires_approval:
            if not self.approvals.session_granted(session_id, tool.tool_id) \
                    and not self.approvals.was_approved_for(step["step_id"]):
                ap = self.approvals.check(session_id, step, tool, actor)
                if ap is not None:
                    raise StepNeedsApproval(ap)
            self.approvals.consume_for_step(step["step_id"])

        # بوابة ٣: التكلفة — قبل الإنفاق؛ التجاوز يوقف الحلقة بنتيجة موثقة
        try:
            budget.check_before_step(budget._spent_steps)
        except Exception as exc:  # BudgetExceededError — إيقاف بسبب واضح
            return _result("denied", error={
                "code": "budget_exceeded", "message": str(exc),
                "action": "raise_budget"})
        if budget._spent_cost + tool.estimated_cost > budget.max_cost:
            return _result("denied", error={
                "code": "budget_exceeded",
                "message": f"تجاوز حد التكلفة ({budget.max_cost}) — أوقفت"
                           " الحلقة قبل الاستدعاء",
                "action": "raise_budget"})

        # تحقق مخطط المدخلات — لا استدعاء بمدخلات غير صالحة
        try:
            schemas.validate(dict(step["inputs"]), tool.input_schema)
        except schemas.SchemaError as exc:
            return _result("failure", error={"code": "invalid_inputs",
                                            "message": str(exc),
                                            "action": "clarify"})

        # Idempotency-Key إلزامي لكل عملية كتابة
        ikey = None
        if tool.access in ("write", "admin"):
            ikey = f"orch:{session_id}:{step['step_id']}:{uuid.uuid4().hex[:8]}"

        started = time.monotonic()
        try:
            out = self.connector_executor.run(
                tool.connector_id, tool.operation, dict(step["inputs"]),
                actor=actor, idempotency_key=ikey)
            budget.record_step(tool.estimated_cost)
            return _result("success", output=out)
        except Exception as exc:  # التصنيف في معالج الفشل (4.10)
            budget.record_step(0.0)
            kind = type(exc).__name__
            return _result("failure", error={"code": kind,
                                            "message": str(exc)[:300],
                                            "action": "classify"})
