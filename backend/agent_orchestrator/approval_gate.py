# -*- coding: utf-8 -*-
"""R-841 (4.6): بوابة الموافقة — لا تنفيذ لعملية حساسة بلا موافقة صريحة.

تدعم: موافقة مرة واحدة، موافقة لجلسة كاملة، رفض، تعديل.
كل موافقة/رفض مسجل بهوية صاحبه ووقته — والرفض يوقف الخطوة فورًا.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from . import schemas
from .tool_registry import ToolDefinition


class ApprovalError(Exception):
    pass


class ApprovalGate:
    """مخزن الموافقات + منطق الجلسات — بطاقة موافقة لكل خطوة حساسة."""

    def __init__(self):
        self._approvals: Dict[str, Dict[str, Any]] = {}
        self._session_grants: Dict[str, List[str]] = {}  # session_id → [tool_id]
        self._consumed: set = set()  # موافقات "مرة واحدة" استُهلكت
        self._lock = threading.RLock()

    def request(self, step: Dict[str, Any], tool: ToolDefinition,
                requested_by: str) -> Dict[str, Any]:
        """إنشاء طلب موافقة معلّق — يعرض ما سيُفعل وعلى أي مورد وبأي أثر."""
        ap = schemas.new_approval(
            step_id=step["step_id"],
            action_summary=f"{tool.name}: {step['goal']}",
            impact_summary=f"عملية {tool.access} عبر {tool.connector_id}"
                           f".{tool.operation} — {tool.description[:120]}",
            requested_by=requested_by)
        with self._lock:
            self._approvals[ap["approval_id"]] = ap
        return ap

    def get(self, approval_id: str) -> Dict[str, Any]:
        with self._lock:
            ap = self._approvals.get(approval_id)
        if ap is None:
            raise ApprovalError(f"موافقة غير موجودة: {approval_id}")
        return dict(ap)

    def pending(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(a) for a in self._approvals.values()
                    if a["status"] == "pending"]

    def decide(self, approval_id: str, approved_by: str,
               decision: str) -> Dict[str, Any]:
        """تسجيل قرار موافقة/رفض/تعديل — بهوية صاحبه ووقته."""
        if decision not in ("approved", "rejected", "modified"):
            raise ApprovalError(f"قرار موافقة غير معروف: {decision}")
        with self._lock:
            ap = self._approvals.get(approval_id)
            if ap is None:
                raise ApprovalError(f"موافقة غير موجودة: {approval_id}")
            if ap["status"] != "pending":
                raise ApprovalError(
                    f"الموافقة {approval_id} محسومة سلفًا ({ap['status']})"
                    " — لا تنفيذ لعمليات معلّقة بلا قرار صريح جديد")
            import datetime as _dt
            ap["status"] = decision
            ap["approved_by"] = approved_by
            ap["timestamp"] = _dt.datetime.now(
                _dt.timezone.utc).isoformat()
            out = dict(ap)
        return out

    def grant_session(self, session_id: str, tool_id: str) -> None:
        """موافقة لجلسة: الأداة لا تسأل ثانيةً داخل الجلسة نفسها."""
        with self._lock:
            grants = self._session_grants.setdefault(session_id, [])
            if tool_id not in grants:
                grants.append(tool_id)

    def session_granted(self, session_id: str, tool_id: str) -> bool:
        with self._lock:
            return tool_id in self._session_grants.get(session_id, [])

    def was_approved_for(self, step_id: str) -> bool:
        """موافقة صريحة (مرة واحدة) ما تزال صالحة لهذه الخطوة."""
        with self._lock:
            return any(a["step_id"] == step_id and
                       a["status"] in ("approved", "modified") and
                       a["approval_id"] not in self._consumed
                       for a in self._approvals.values())

    def consume_for_step(self, step_id: str) -> None:
        """استهلاك موافقة "مرة واحدة" بعد تنفيذها — لا إعادة استخدام صامتة."""
        with self._lock:
            for a in self._approvals.values():
                if a["step_id"] == step_id and \
                        a["status"] in ("approved", "modified"):
                    self._consumed.add(a["approval_id"])

    def check(self, session_id: str, step: Dict[str, Any],
              tool: ToolDefinition, actor: str
              ) -> Optional[Dict[str, Any]]:
        """هل الخطوة معتمدة؟ يعيد None إذا معتمدة (جلسة) وإلا بطاقة معلّقة.

        القاعدة: لا تنفيذ بعد رفض — الرفض يُعاد للخطوة كفشل حوكمي.
        """
        if self.session_granted(session_id, tool.tool_id):
            return None
        ap = self.request(step, tool, requested_by=actor)
        return ap

    def record(self, tool_registry, loop_state) -> None:
        """إرفاق حسم كل الموافقات في أثر الحلقة للتدقيق (سجل الموافقات)."""
        with self._lock:
            loop_state["approvals"] = [dict(a) for a in
                                       self._approvals.values()]
