# -*- coding: utf-8 -*-
"""R-841 (4.11): حاكم التكلفة والزمن — حدود صارمة توقف الحلقة عند التجاوز.

لا حلقة بلا سقوف: خطوات، تكلفة، زمن. التجاوز يوقف فورًا بسبب واضح
يُعرض على المستخدم — لا دوران ولا استنزاف.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class BudgetExceededError(Exception):
    """تجاوز الحدود — يوقف الحلقة برسالة واضحة."""

    def __init__(self, reason: str, code: str = "budget_exceeded"):
        super().__init__(reason)
        self.reason = reason
        self.code = code


@dataclass
class Budget:
    """ميزانية حلقة واحدة — تُقرأ من عقد الطلب (constraints)."""
    max_steps: int = 12
    max_cost: float = 1.0
    max_time_s: float = 120.0
    max_replans: int = 2
    _spent_steps: int = field(default=0, init=False)
    _spent_cost: float = field(default=0.0, init=False)
    _replans: int = field(default=0, init=False)
    _started_at: float = field(default_factory=time.monotonic, init=False)

    @classmethod
    def from_constraints(cls, c: Dict[str, Any]) -> "Budget":
        return cls(max_steps=int(c.get("max_steps", 12)),
                   max_cost=float(c.get("max_cost", 1.0)),
                   max_time_s=float(c.get("max_time_s", 120.0)))

    def check_before_step(self, step_index: int) -> None:
        """فحص قبل كل خطوة — يوقف قبل التنفيذ لا بعده."""
        if step_index >= self.max_steps:
            raise BudgetExceededError(
                f"تجاوز حد الخطوات ({self.max_steps}) — أوقفت الحلقة لمنع"
                " الدوران؛ ضيّق الطلب أو ارفع السقف صراحة", "max_steps")
        if self._spent_cost >= self.max_cost:
            raise BudgetExceededError(
                f"تجاوز حد التكلفة ({self.max_cost}) — أوقفت الحلقة;"
                " نفّذ الطلب على دفعات أو ارفع السقف صراحة", "max_cost")
        elapsed = time.monotonic() - self._started_at
        if elapsed >= self.max_time_s:
            raise BudgetExceededError(
                f"تجاوز حد الزمن ({self.max_time_s:.0f}ث) — أوقفت الحلقة",
                "max_time_s")

    def record_step(self, cost: float) -> None:
        self._spent_steps += 1
        self._spent_cost += max(0.0, float(cost))

    def record_replan(self) -> None:
        self._replans += 1
        if self._replans > self.max_replans:
            raise BudgetExceededError(
                f"تجاوز حد إعادات التخطيط ({self.max_replans}) — أوقفت الحلقة"
                " لمنع الدوران", "max_replans")

    @property
    def spent(self) -> Dict[str, Any]:
        return {"steps": self._spent_steps,
                "cost": round(self._spent_cost, 6),
                "elapsed_s": round(time.monotonic() - self._started_at, 3),
                "replans": self._replans}

    def remaining_time_s(self) -> float:
        return max(0.0, self.max_time_s - (time.monotonic() - self._started_at))


class CostGovernor:
    """تجميع الحدود لكل حلقة/جلسة/مستخدم — سقف صلب لا استئناف بعده."""

    def __init__(self):
        self._session_spent: Dict[str, float] = {}
        self._user_spent: Dict[str, float] = {}
        self._session_limits: Dict[str, float] = {}
        self._user_limits: Dict[str, float] = {}

    def set_session_limit(self, session_id: str, max_cost: float) -> None:
        self._session_limits[session_id] = max_cost

    def set_user_limit(self, user_id: str, max_cost: float) -> None:
        self._user_limits[user_id] = max_cost

    def check_session(self, session_id: str, extra: float = 0.0) -> None:
        spent = self._session_spent.get(session_id, 0.0) + extra
        limit = self._session_limits.get(session_id)
        if limit is not None and spent > limit:
            raise BudgetExceededError(
                f"تجاوز حد تكلفة الجلسة ({limit}) — أوقفت الحلقة", "session_cost")

    def check_user(self, user_id: str, extra: float = 0.0) -> None:
        spent = self._user_spent.get(user_id, 0.0) + extra
        limit = self._user_limits.get(user_id)
        if limit is not None and spent > limit:
            raise BudgetExceededError(
                f"تجاوز حد تكلفة المستخدم ({limit}) — أوقفت الحلقة", "user_cost")

    def record(self, session_id: str, user_id: str, cost: float) -> None:
        self._session_spent[session_id] = \
            self._session_spent.get(session_id, 0.0) + cost
        self._user_spent[user_id] = \
            self._user_spent.get(user_id, 0.0) + cost
