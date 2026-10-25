# -*- coding: utf-8 -*-
"""R-753 (ROADMAP_V5 §٢: ٢.١ + ٢.٢ + ٢.٣): حلقة الوكيل العامة.

هدف → خطوة من المخطِّط → تنفيذ عبر سجل الأدوات (R-729) فقط → تحقق من الناتج
قبل الاعتماد عليه → استمرار أو توقف صادق. بميزانيات (خطوات/وقت/استدعاءات)
وإلغاء صريح، وأثر إلزامي: حدث `agent_run` في السجل السيادي عند البدء والنهاية
(وكل استدعاء أداة يترك `tool_invoked` عبر السجل نفسه). تعذر الأثر = لا تنفيذ.

المخطِّط قابل للاستبدال (واجهة next_step):
- ScriptedPlanner: خطوات ثابتة — بديل اختبار حتمي **معلن**، ليس ذكاءً.
- BrainPlanner: العقل الحي عبر ollama_client.chat — بلا عقل مفعّل (١.٦) يفشل
  صادقًا (planner_failed) ولا يتظاهر بالتخطيط.

حالات النهاية (لا «نجاح» إلا completed):
completed / tool_failed / verification_failed / budget_exhausted / cancelled /
invalid_step / planner_failed / ledger_blocked
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from typing import Any, Callable, Dict, Iterable, List, Optional

# أدوات لا تستدعيها الحلقة أبدًا: نفسها (لا تكرار لا نهائي)
FORBIDDEN_TOOLS = frozenset({"agent.run"})
CHECK_TYPES = ("ok", "non_empty", "key_equals", "contains")


class CancelToken:
    """إلغاء من المالك — يُفحص قبل كل خطوة وبعدها."""

    def __init__(self) -> None:
        self._ev = threading.Event()
        self.by: Optional[str] = None

    def cancel(self, by: str = "owner") -> None:
        self.by = by
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()


class PlannerError(Exception):
    pass


class ScriptedPlanner:
    """بديل اختبار حتمي: الخطوة رقم len(history) من القائمة. ليس ذكاءً.
    عديم الحالة (يُشتق موضعه من السجل) — فيستأنف من نقطة تفتيش (§٣) كما هو."""

    kind = "scripted"

    def __init__(self, steps: Iterable[Dict[str, Any]]):
        self._steps = list(steps)

    def next_step(self, goal: str, tools: List[Dict[str, Any]],
                  history: List[Dict[str, Any]]) -> Dict[str, Any]:
        i = len(history)
        if i >= len(self._steps):
            raise PlannerError("نفدت خطوات المخطط دون إعلان إنهاء")
        return self._steps[i]


_SYSTEM = (
    "أنت مخطط وكيل. أجب بكائن JSON واحد فقط دون أي نص آخر. الأشكال المسموحة:\n"
    '{"action":"call","tool":"<اسم أداة من القائمة>","inputs":{...},'
    '"check":{"type":"ok|non_empty|key_equals|contains","key":"...","value":...}}\n'
    '{"action":"finish","answer":"<الجواب النهائي المبني على نتائج الخطوات>"}\n'
    "لا تستدعِ أداة خارج القائمة. أنهِ فقط حين تثبت النتائج الجواب."
)


def _extract_json(text: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise PlannerError("رد العقل ليس JSON")
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise PlannerError(f"رد العقل JSON فاسد: {exc.msg}") from exc
    if not isinstance(obj, dict):
        raise PlannerError("رد العقل ليس كائنًا")
    return obj


class BrainPlanner:
    """مخطط العقل الحي (ollama_client — Ollama أو متوافق OpenAI)."""

    kind = "brain"

    def __init__(self, timeout: Optional[float] = None):
        self.timeout = timeout

    def next_step(self, goal: str, tools: List[Dict[str, Any]],
                  history: List[Dict[str, Any]]) -> Dict[str, Any]:
        import ollama_client
        catalog = [{"name": t["name"], "description": t.get("description", ""),
                    "inputs": t.get("inputs", {})} for t in tools]
        hist = [{k: h.get(k) for k in ("tool", "inputs", "ok", "verified",
                                        "result", "error")} for h in history]
        user = json.dumps({"goal": goal, "tools": catalog, "history": hist},
                          ensure_ascii=False, default=str)[:12000]
        reply = ollama_client.chat(_SYSTEM, user, timeout=self.timeout)
        if reply is None:
            raise PlannerError("العقل غير متاح أو غير مفعّل (ROADMAP_V5 ١.٦) — لا تخطيط")
        return _extract_json(reply)


def verify(check: Dict[str, Any], invocation: Dict[str, Any]) -> bool:
    """٢.٢: هل الناتج يطابق الشرط؟ — لا خطوة تالية بلا فحص."""
    if not invocation.get("ok"):
        return False
    result = invocation.get("result")
    ctype = (check or {}).get("type", "ok")
    if ctype == "ok":
        return True
    if ctype == "non_empty":
        return result not in (None, "", [], {})
    key = check.get("key")
    val = result.get(key) if isinstance(result, dict) and key else result
    if ctype == "key_equals":
        return val == check.get("value")
    if ctype == "contains":
        return val is not None and str(check.get("value")) in str(val)
    return False


class AgentLoop:
    def __init__(self, registry, planner, *, max_steps: int = 8,
                 max_seconds: float = 120.0, max_tool_calls: Optional[int] = None,
                 allowed_tools: Optional[Iterable[str]] = None,
                 cancel: Optional[CancelToken] = None,
                 clock: Callable[[], float] = time.monotonic,
                 caller: str = "agent"):
        self.registry = registry
        self.planner = planner
        self.max_steps = int(max_steps)
        self.max_seconds = float(max_seconds)
        self.max_tool_calls = int(max_tool_calls if max_tool_calls is not None else max_steps)
        self.allowed = set(allowed_tools) if allowed_tools is not None else None
        self.cancel = cancel or CancelToken()
        self.clock = clock
        self.caller = caller

    # ------------------------------------------------------------------
    def _trace(self, payload: Dict[str, Any]) -> None:
        from memory.core import get_core
        get_core().append_event("agent_run", payload, user=self.caller)

    def _tools(self) -> List[Dict[str, Any]]:
        out = []
        for t in self.registry.list_tools():
            if t["name"] in FORBIDDEN_TOOLS:
                continue
            if self.allowed is not None and t["name"] not in self.allowed:
                continue
            out.append(t)
        return out

    def _validate(self, step: Any, tool_names: set) -> Optional[str]:
        if not isinstance(step, dict):
            return "الخطوة ليست كائنًا"
        action = step.get("action")
        if action == "finish":
            return None
        if action != "call":
            return f"فعل غير معروف: {action!r}"
        tool = step.get("tool")
        if tool not in tool_names:
            return f"أداة غير مسموحة أو غير مسجلة: {tool!r}"
        if not isinstance(step.get("inputs", {}), dict):
            return "المدخلات ليست كائنًا"
        ctype = (step.get("check") or {}).get("type", "ok")
        if ctype not in CHECK_TYPES:
            return f"نوع تحقق غير معروف: {ctype!r}"
        return None

    def run(self, goal: str) -> Dict[str, Any]:
        run_id = uuid.uuid4().hex[:12]
        start = self.clock()
        steps: List[Dict[str, Any]] = []
        res: Dict[str, Any] = {"run_id": run_id, "goal": goal,
                               "planner": getattr(self.planner, "kind", "custom"),
                               "steps": steps, "answer": None}
        try:
            self._trace({"run_id": run_id, "phase": "start", "goal": goal[:300],
                         "planner": res["planner"],
                         "budget": {"max_steps": self.max_steps,
                                    "max_seconds": self.max_seconds,
                                    "max_tool_calls": self.max_tool_calls}})
        except Exception as exc:
            res.update(status="ledger_blocked",
                       error=f"تعذر أثر البدء — لا تنفيذ: {type(exc).__name__}: {str(exc)[:160]}")
            return res

        tools = self._tools()
        names = {t["name"] for t in tools}
        tool_calls = 0
        status, extra = None, {}
        while status is None:
            if self.cancel.cancelled:
                status, extra = "cancelled", {"cancelled_by": self.cancel.by}
                break
            if len(steps) >= self.max_steps:
                status, extra = "budget_exhausted", {"budget": "max_steps"}
                break
            if tool_calls >= self.max_tool_calls:
                status, extra = "budget_exhausted", {"budget": "max_tool_calls"}
                break
            if self.clock() - start > self.max_seconds:
                status, extra = "budget_exhausted", {"budget": "max_seconds"}
                break
            try:
                step = self.planner.next_step(goal, tools, steps)
            except Exception as exc:
                status, extra = "planner_failed", {"error": f"{exc}"[:300]}
                break
            problem = self._validate(step, names)
            if problem:
                status, extra = "invalid_step", {"error": problem, "failed_step": len(steps)}
                break
            if step["action"] == "finish":
                status = "completed"
                res["answer"] = step.get("answer")
                break
            idx = len(steps)
            try:
                inv = self.registry.invoke(step["tool"], caller=self.caller,
                                           inputs=step.get("inputs") or {})
            except RuntimeError as exc:
                status, extra = "ledger_blocked", {
                    "error": f"تعذر أثر الأداة — توقف: {str(exc)[:160]}", "failed_step": idx}
                break
            tool_calls += 1
            ok_check = verify(step.get("check") or {"type": "ok"}, inv)
            steps.append({"index": idx, "tool": step["tool"],
                          "inputs": step.get("inputs") or {}, "ok": inv.get("ok"),
                          "verified": ok_check, "result": inv.get("result"),
                          "error": inv.get("error"),
                          "fingerprint": (inv.get("trace") or {}).get("result_fingerprint")})
            if not inv.get("ok"):
                status, extra = "tool_failed", {"error": inv.get("error"), "failed_step": idx}
            elif not ok_check:
                status, extra = "verification_failed", {
                    "error": f"ناتج الخطوة {idx} لا يطابق الشرط {step.get('check')}",
                    "failed_step": idx}

        res.update(status=status, **extra)
        res["duration_s"] = round(self.clock() - start, 3)
        phase = {"completed": "finish", "cancelled": "cancelled"}.get(status, "stopped")
        try:
            self._trace({"run_id": run_id, "phase": phase, "status": status,
                         "steps": len(steps), "tool_calls": tool_calls,
                         **({"cancelled_by": extra.get("cancelled_by")}
                            if status == "cancelled" else {}),
                         **({"failed_step": extra.get("failed_step")}
                            if "failed_step" in extra else {})})
        except Exception as exc:  # الأفعال وقعت بأثرها؛ نهاية بلا أثر تُعلن صراحة
            res["trace_warning"] = f"تعذر أثر النهاية: {type(exc).__name__}"
        if status != "completed":
            res["answer"] = None
        return res


def run_goal(goal: str, max_steps: int = 8) -> Dict[str, Any]:
    """مدخل أداة agent.run: العقل الحي مخططًا فوق السجل العام."""
    from tool_registry import get_registry
    return AgentLoop(get_registry(), BrainPlanner(),
                     max_steps=max(1, min(int(max_steps), 32))).run(goal)
