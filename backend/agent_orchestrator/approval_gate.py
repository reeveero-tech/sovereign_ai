# -*- coding: utf-8 -*-
"""R-841 (4.6): بوابة الموافقة — لا تنفيذ لعملية حساسة بلا موافقة صريحة.

تدعم: موافقة مرة واحدة، موافقة لجلسة كاملة، رفض، تعديل.
كل موافقة/رفض مسجل بهوية صاحبه ووقته — والرفض يوقف الخطوة فورًا.

R-844 (D-059):
- نطاق الموافقة «مرة واحدة» هو (الحلقة، الخطوة) لا الخطوة وحدها: معرّفات
  الخطوات (s1، s2…) تتكرر بين الحلقات، فكانت موافقة حلقة تُجيز كتابة حلقة
  أخرى ما تزال موافقتها معلّقة (forensics/R-844_crash_concurrency_RED.txt).
- الدوام: مع ``path`` تُحفظ الموافقات والمنح والاستهلاك ذريًا بعد كل تغيير
  وتُحمَّل عند الإقلاع — كانت في الذاكرة فقط، فتصير كل حلقة معلّقة يتيمة بعد
  إعادة التشغيل.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

try:  # R-781: كتابة ذرية موحدة — نمط الاستيراد المزدوج
    from runtime.atomic_json import atomic_write_json
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم (تشغيل الاختبارات من الجذر)
    from backend.runtime.atomic_json import atomic_write_json

from . import schemas
from .tool_registry import ToolDefinition


class ApprovalError(Exception):
    pass


class ApprovalGate:
    """مخزن الموافقات + منطق الجلسات — بطاقة موافقة لكل خطوة حساسة."""

    def __init__(self, path: Optional[str] = None):
        self._approvals: Dict[str, Dict[str, Any]] = {}
        self._session_grants: Dict[str, List[str]] = {}  # session_id → [tool_id]
        self._consumed: set = set()  # موافقات "مرة واحدة" استُهلكت
        self._loop_of: Dict[str, str] = {}  # R-844: approval_id → loop_id (النطاق)
        self._lock = threading.RLock()
        self._path = path
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)  # تالف ⇒ استثناء صريح: لا بدء بموافقات مجهولة
            self._approvals = dict(data.get("approvals") or {})
            self._session_grants = {k: list(v) for k, v in
                                    (data.get("session_grants") or {}).items()}
            self._consumed = set(data.get("consumed") or [])
            self._loop_of = dict(data.get("loop_of") or {})

    def _persist(self) -> None:
        """يُستدعى تحت القفل بعد كل تغيير — كتابة ذرية (R-781)."""
        if not self._path:
            return
        atomic_write_json(self._path, {
            "approvals": self._approvals, "session_grants": self._session_grants,
            "consumed": sorted(self._consumed), "loop_of": self._loop_of},
            ensure_ascii=False, indent=1)

    def request(self, step: Dict[str, Any], tool: ToolDefinition,
                requested_by: str, loop_id: str = "") -> Dict[str, Any]:
        """إنشاء طلب موافقة معلّق — يعرض ما سيُفعل وعلى أي مورد وبأي أثر."""
        ap = schemas.new_approval(
            step_id=step["step_id"],
            action_summary=f"{tool.name}: {step['goal']}",
            impact_summary=f"عملية {tool.access} عبر {tool.connector_id}"
                           f".{tool.operation} — {tool.description[:120]}",
            requested_by=requested_by)
        with self._lock:
            self._approvals[ap["approval_id"]] = ap
            self._loop_of[ap["approval_id"]] = loop_id
            self._persist()
        return ap

    def loop_of(self, approval_id: str) -> str:
        with self._lock:
            return self._loop_of.get(approval_id, "")

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
            self._persist()
        return out

    def grant_session(self, session_id: str, tool_id: str) -> None:
        """موافقة لجلسة: الأداة لا تسأل ثانيةً داخل الجلسة نفسها."""
        with self._lock:
            grants = self._session_grants.setdefault(session_id, [])
            if tool_id not in grants:
                grants.append(tool_id)
                self._persist()

    def session_granted(self, session_id: str, tool_id: str) -> bool:
        with self._lock:
            return tool_id in self._session_grants.get(session_id, [])

    def _in_scope(self, a: Dict[str, Any], step_id: str, loop_id: str) -> bool:
        return (a["step_id"] == step_id and
                self._loop_of.get(a["approval_id"], "") == loop_id)

    def was_approved_for(self, step_id: str, loop_id: str = "") -> bool:
        """موافقة صريحة (مرة واحدة) ما تزال صالحة لهذه الخطوة في هذه الحلقة.

        R-844: النطاق (loop_id, step_id) — موافقة حلقة لا تُجيز خطوة حلقة أخرى.
        """
        with self._lock:
            return any(self._in_scope(a, step_id, loop_id) and
                       a["status"] in ("approved", "modified") and
                       a["approval_id"] not in self._consumed
                       for a in self._approvals.values())

    def consume_for_step(self, step_id: str, loop_id: str = "") -> None:
        """استهلاك موافقة "مرة واحدة" قبل تنفيذها — لا إعادة استخدام صامتة."""
        with self._lock:
            for a in self._approvals.values():
                if self._in_scope(a, step_id, loop_id) and \
                        a["status"] in ("approved", "modified"):
                    self._consumed.add(a["approval_id"])
            self._persist()

    def check(self, session_id: str, step: Dict[str, Any],
              tool: ToolDefinition, actor: str, loop_id: str = ""
              ) -> Optional[Dict[str, Any]]:
        """هل الخطوة معتمدة؟ يعيد None إذا معتمدة (جلسة) وإلا بطاقة معلّقة.

        القاعدة: لا تنفيذ بعد رفض — الرفض يُعاد للخطوة كفشل حوكمي.
        """
        if self.session_granted(session_id, tool.tool_id):
            return None
        ap = self.request(step, tool, requested_by=actor, loop_id=loop_id)
        return ap

    def record(self, tool_registry, loop_state) -> None:
        """إرفاق حسم كل الموافقات في أثر الحلقة للتدقيق (سجل الموافقات)."""
        with self._lock:
            loop_state["approvals"] = [dict(a) for a in
                                       self._approvals.values()]
