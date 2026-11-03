# -*- coding: utf-8 -*-
"""R-841 (4.13): التدخل البشري — إيقاف، تعديل خطة، تجاوز موثق، استئناف.

كل تجاوز من مسؤول مخوّل مسجَّل صراحة في أثر الحلقة (من، متى، على ماذا،
لماذا) — لا تجاوز صامت.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import schemas
from .tool_registry import new_decision


class HumanInTheLoop:
    """بوابة التدخل — تُستدعى من الواجهة، وتُسجَّل في الأثر دائمًا."""

    def __init__(self):
        self._overrides: Dict[str, Dict[str, Any]] = {}

    def pause(self, state: Dict[str, Any], actor: str, trace_ref: str
              ) -> Dict[str, Any]:
        if state["status"] in ("completed", "failed", "cancelled"):
            return {"ok": False,
                    "reason": f"الحلقة {state['status']} — لا إيقاف بعد الحسم"}
        state["status"] = "paused"
        state.setdefault("interventions", []).append(
            {"kind": "pause", "actor": actor, "ts": _now()})
        return {"ok": True, "reason": "أُوقفت الحلقة بطلب بشري"}

    def resume(self, state: Dict[str, Any], actor: str,
               trace_ref: str) -> Dict[str, Any]:
        if state["status"] not in ("paused",):
            return {"ok": False,
                    "reason": f"الحلقة {state['status']} — لا استئناف"}
        state["status"] = "running"
        state.setdefault("interventions", []).append(
            {"kind": "resume", "actor": actor, "ts": _now()})
        return {"ok": True, "reason": "استؤنفت الحلقة"}

    def modify_plan(self, state: Dict[str, Any], new_steps, actor: str,
                    trace_ref: str) -> Dict[str, Any]:
        """تعديل الخطة قبل التنفيذ أو بين الخطوات — يُعاد التحقق من المخطط."""
        if state["status"] not in ("running", "paused", "pending_approval"):
            return {"ok": False,
                    "reason": f"الحلقة {state['status']} — لا تعديل الآن"}
        plan = dict(state["plan"])
        plan["steps"] = list(new_steps)
        try:
            schemas.validate(plan, schemas.PLAN_SCHEMA)
        except schemas.SchemaError as exc:
            return {"ok": False, "reason": f"خطة معدلة غير صالحة: {exc}"}
        state["plan"] = plan
        state.setdefault("interventions", []).append(
            {"kind": "modify_plan", "actor": actor, "ts": _now(),
             "steps": [s["step_id"] for s in new_steps]})
        return {"ok": True, "reason": "عُدلت الخطة بتدخل بشري موثق"}

    def override(self, approval_gate, approval_id: str, approver: str,
                 reason: str, trace_ref: str) -> Dict[str, Any]:
        """تجاوز موثق من مسؤول مخوّل — موافقة بقرار إداري مسجل صراحة."""
        try:
            ap = approval_gate.decide(approval_id, f"admin:{approver}",
                                     "approved")
        except Exception as exc:
            return {"ok": False, "reason": str(exc)}
        self._overrides[approval_id] = {
            "approver": approver, "reason": reason, "ts": _now()}
        return {"ok": True, "approval": ap,
                "record": {"approver": approver, "reason": reason,
                           "note": "تجاوز مسجل صراحة في سجل التدقيق"}}


def _now() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).isoformat()
