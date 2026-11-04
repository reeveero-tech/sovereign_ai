# -*- coding: utf-8 -*-
"""R-841 (4.8): واجهة الذاكرة — كل خطوة تقرأ وتكتب عبر واجهة موحدة.

أربع طبقات: حلقة (قصيرة المدى)، جلسة (تراكم الحلقات)، طويلة المدى
(مفوضة لطبقة الفهم)، وإجرائية (سياسات التنفيذ). لا وصول مباشر للبنية.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional


class MemoryInterface:
    """بوابة واحدة لكل قراءة/كتابة ذاكرة في الحلقة."""

    def __init__(self):
        self._loop: Dict[str, Dict[str, Any]] = {}
        self._session: Dict[str, Dict[str, Any]] = {}
        self._procedural: Dict[str, str] = {
            "write_needs_approval": "كل عملية كتابة تمر ببوابة الموافقة",
            "no_blind_retry_on_403": "لا إعادة محاولة على 401/403 بلا تحقق",
            "idempotency_for_writes": "Idempotency-Key إلزامي لكل كتابة",
        }
        self._long_term_reader = None  # مفوض لطبقة الفهم (R-838)
        self._lock = threading.RLock()

    # ------------------------------------------------------------- حلقة واحدة
    def loop_new(self, loop_id: str, request: Dict[str, Any]) -> None:
        with self._lock:
            self._loop[loop_id] = {"request": request, "steps": [],
                                  "decisions": []}

    def loop_read(self, loop_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            m = self._loop.get(loop_id)
            return dict(m) if m else None

    def _loop_entry(self, loop_id: str) -> Dict[str, Any]:
        """R-844: الذاكرة العاملة داخل العملية — بعد إعادة التشغيل تُنشأ من جديد
        (الحالة الدائمة في StateStore) بدل KeyError يكسر الاستئناف."""
        return self._loop.setdefault(
            loop_id, {"request": None, "steps": [], "decisions": []})

    def loop_write_step(self, loop_id: str, record: Dict[str, Any]) -> None:
        with self._lock:
            self._loop_entry(loop_id)["steps"].append(record)

    def loop_write_decision(self, loop_id: str, record: Dict[str, Any]) -> None:
        with self._lock:
            self._loop_entry(loop_id)["decisions"].append(record)

    # ------------------------------------------------------------- الجلسة
    def session_write(self, session_id: str, key: str, value: Any) -> None:
        with self._lock:
            self._session.setdefault(session_id, {})[key] = value

    def session_read(self, session_id: str, key: str,
                     default: Any = None) -> Any:
        with self._lock:
            return self._session.get(session_id, {}).get(key, default)

    def session_summary(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._session.get(session_id, {}))

    # ------------------------------------------------------------- الإجرائية
    def policy_get(self, name: str) -> Optional[str]:
        return self._procedural.get(name)

    def policy_all(self) -> Dict[str, str]:
        return dict(self._procedural)

    # -------------------------------------------------------- طويلة المدى (جسر)
    def attach_long_term(self, reader) -> None:
        """ربط قارئ الذاكرة طويلة المدى بطبقة الفهم (R-838) — مرجع لا سر."""
        self._long_term_reader = reader

    def long_term_lookup(self, key: str) -> Any:
        if self._long_term_reader is None:
            return None
        try:
            return self._long_term_reader(key)
        except Exception:  # TOLERATED: الذاكرة البعيدة اختيارية لا حرجة
            return None
