# -*- coding: utf-8 -*-
"""R-790 (ROADMAP_V6 ٦.٩.٢): المدير — ينشئ الوكلاء بنفسه وينظم عملهم.

سؤال المالك (2026-10-27): «هل يستطيع إنشاء وكلاء بنفسه؟ هل يستطيع إدارة وتنظيم الوكلاء
والعمل؟» — قبل هذه الوحدة: الأسطول (R-758) موجود، لكن الأهداف الجزئية يكتبها المستدعي بيده؛
لا أحد يقرر كم وكيلًا يلزم ولا ماذا يفعل كل منهم ولا يجمع نتائجهم.

الدورة (كل قرار فيها من العقل الحي، لا قالب):
  1. تخطيط: العقل يقرأ الهدف + فهرس الأدوات الحقيقي + الخبرة السابقة المشابهة (R-790
     experience) ويقرر بنفسه: كم وكيلًا (1..MAX_AGENTS)، دور كل منهم، وهدفه الجزئي — JSON
     مقيّد بمخطط.
  2. إنشاء: لكل مهمة جزئية عامل (fleet.Worker) بمخطط المرحلتين (R-789b ChatPlanner) وأدوات
     مسموحة محددة (لا مدير داخل عامل — لا تكرار لا نهائي). أثر موقّع لكل إنشاء ونتيجة.
  3. تنظيم: FleetCoordinator — سقف تزامن، عزل الفاشل، إعادة محاولة واحدة، تقرير صادق.
  4. تجميع: العقل يكتب الجواب النهائي من نتائج العمال الحقيقية فقط.
  5. تعلّم: التشغيل كله وكل عامل يُسجلان في الخبرة — فالتخطيط التالي يرى ما نجح وما فشل.

حدود صادقة: العمال خيوط في عملية واحدة؛ العقل الحي واحد فيصطف الطلب عليه — التزامن الحقيقي
محدود بالعقل لا بعدد العمال. فشل العقل في أي مرحلة ⇒ حالة صادقة (planner_failed) بسببها الفعلي.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

MAX_AGENTS = int(os.getenv("MANAGER_MAX_AGENTS", "4") or 4)
MAX_CONCURRENCY = int(os.getenv("MANAGER_MAX_CONCURRENCY", "2") or 2)
WORKER_MAX_STEPS = int(os.getenv("MANAGER_WORKER_STEPS", "4") or 4)
WORKER_MAX_SECONDS = float(os.getenv("MANAGER_WORKER_SECONDS", "300") or 300)

# أدوات لا يحملها العامل: كل ما ينشئ وكلاء أو مهام أو أهدافًا (لا تكرار لا نهائي)
WORKER_EXCLUDED = frozenset({"agent.run", "agent.manage", "fleet.spawn", "tasks.start",
                             "tasks.resume", "goals.add", "goals.work", "autonomy.tick"})

_PLAN_SYSTEM = (
    "أنت مدير وكلاء نظام sovereign_ai. أمامك هدف وقائمة الأدوات الحقيقية المتاحة للوكلاء. "
    "قرر بنفسك كم وكيلًا يلزم (من 1 إلى {max_agents}) ودور كل وكيل وهدفه الجزئي الواضح القابل "
    "للتنفيذ بالأدوات المتاحة. وكيل واحد إن كان الهدف بسيطًا؛ أكثر فقط إن كان للهدف أجزاء مستقلة. "
    "لا تكلف وكيلًا بما لا تملكه الأدوات. استفد من التجارب السابقة: كرر ما نجح وتجنب ما فشل.\n"
    "الأدوات:\n{tools}\n{lessons}"
    'أجب JSON فقط: {{"subtasks":[{{"role":"<اسم دور قصير>","goal":"<هدف جزئي>"}}],"reason":"<سبب قصير>"}}'
)
# R-790a: لكل وكيل أداة رئيسية من القائمة (أو none لكتابة/تلخيص بلا بيانات)، والأهداف بالعربية
_PLAN_TOOL_RULE = (
    "\nلكل وكيل حدد tool: الأداة الرئيسية التي سيجلب بها الحقيقة (من القائمة حرفيًا)، أو none إن "
    "كانت مهمته كتابة لا تحتاج بيانات. وكيل لكل أداة مختلفة؛ لا وكيلان لنفس الأداة. "
    "اكتب الأهداف بالعربية."
    '\nأجب JSON فقط: {"subtasks":[{"role":"<دور>","goal":"<هدف جزئي>","tool":"<أداة أو none>"}],'
    '"reason":"<سبب>"}'
)

_SYNTH_SYSTEM = (
    "أنت عقل نظام sovereign_ai. وكلاؤك أنجزوا أجزاء هدف المالك. اكتب الجواب النهائي للمالك "
    "بالعربية الفصحى من نتائجهم الحقيقية فقط: اذكر الأرقام كما وردت، وإن فشل وكيل فقل ذلك "
    "بصدق وما الذي لم يُنجز. لا تختلق معلومة لم ترد في النتائج."
)


def plan_schema(max_agents: int, tools: Optional[List[str]] = None) -> Dict[str, Any]:
    """R-790a: كل مهمة جزئية تحمل أداة من السجل فعلًا (تعداد) — قياس حي: بلا ذلك خطط
    qwen2.5:3b وكيلًا بلا أداة («تقييم الأداء») فأجاب من رأسه."""
    if tools:
        item = {"type": "object",
                "properties": {"role": {"type": "string"}, "goal": {"type": "string"},
                               "tool": {"type": "string", "enum": sorted(set(tools)) + ["none"]}},
                "required": ["role", "goal", "tool"]}
        return {"type": "object",
                "properties": {"subtasks": {"type": "array", "minItems": 1,
                                            "maxItems": max_agents, "items": item},
                               "reason": {"type": "string"}},
                "required": ["subtasks"]}
    return {"type": "object",
            "properties": {"subtasks": {"type": "array", "minItems": 1, "maxItems": max_agents,
                                        "items": {"type": "object",
                                                  "properties": {"role": {"type": "string"},
                                                                 "goal": {"type": "string"}},
                                                  "required": ["role", "goal"]}},
                           "reason": {"type": "string"}},
            "required": ["subtasks"]}


def _trace(payload: Dict[str, Any]) -> None:
    from memory.core import get_core
    get_core().append_event("manager_run", payload, user="manager")


def _slug(role: str, used: set) -> str:
    base = "".join(ch for ch in (role or "agent") if ch.isalnum() or ch in "_-")[:24] or "agent"
    name, i = base, 2
    while name in used:
        name, i = f"{base}{i}", i + 1
    used.add(name)
    return name


class AgentManager:
    def __init__(self, registry, *, chat_fn=None, max_agents: int = MAX_AGENTS,
                 max_concurrency: int = MAX_CONCURRENCY,
                 worker_max_steps: int = WORKER_MAX_STEPS,
                 worker_max_seconds: float = WORKER_MAX_SECONDS,
                 allowed_tools: Optional[List[str]] = None, source: str = "manager"):
        self.registry = registry
        self._chat = chat_fn
        self.max_agents = max(1, int(max_agents))
        self.max_concurrency = max(1, int(max_concurrency))
        self.worker_max_steps = int(worker_max_steps)
        self.worker_max_seconds = float(worker_max_seconds)
        self.allowed = list(allowed_tools) if allowed_tools is not None else None
        self.source = source

    # ------------------------------------------------------------------
    def _call(self, system: str, user: str, **kw) -> Optional[str]:
        chat = self._chat
        if chat is None:
            import ollama_client
            chat = ollama_client.chat
        return chat(system, user, **kw)

    def worker_tools(self) -> List[str]:
        names = [t["name"] for t in self.registry.list_tools()]
        if self.allowed is not None:
            names = [n for n in names if n in set(self.allowed)]
        return [n for n in names if n not in WORKER_EXCLUDED]

    def plan(self, goal: str, tools: List[str]) -> Dict[str, Any]:
        from agent_loop import PlannerError, _extract_json
        import experience
        catalog = {t["name"]: t for t in self.registry.list_tools()}
        lines = [f"- {n}: {catalog[n].get('description', '')[:120]}" for n in tools if n in catalog]
        lessons = experience.lessons_text(goal, k=3)
        system = _PLAN_SYSTEM.format(
            max_agents=self.max_agents, tools="\n".join(lines),
            lessons=("تجارب سابقة مشابهة (وقائع مسجلة):\n" + lessons + "\n") if lessons else "")
        system += _PLAN_TOOL_RULE
        reply = self._call(system, goal, json_mode=True, max_tokens=400,
                           json_schema=plan_schema(self.max_agents, tools))
        if reply is None:
            from chat_agent import _brain_failure_reason
            raise PlannerError(_brain_failure_reason())
        obj = _extract_json(reply)
        subs = obj.get("subtasks") if isinstance(obj, dict) else None
        if not isinstance(subs, list) or not subs:
            raise PlannerError("العقل لم يُرجع مهامًا جزئية")
        used: set = set()
        parts = []
        for s in subs[: self.max_agents]:
            if not isinstance(s, dict):
                continue
            g = str(s.get("goal") or "").strip()
            if not g:
                continue
            tool = str(s.get("tool") or "none")
            tool = tool if tool in tools else "none"
            if tool != "none" and any(p.get("tool") == tool for p in parts):
                continue        # R-790a: وكيلان لنفس الأداة = تكرار لا تقسيم
            parts.append({"role": _slug(str(s.get("role") or "agent"), used), "goal": g[:500],
                          "tool": tool})
        if not parts:
            raise PlannerError("كل المهام الجزئية فارغة")
        return {"subtasks": parts, "reason": str(obj.get("reason") or "")[:300],
                "lessons_used": bool(lessons)}

    def synthesize(self, goal: str, results: List[Dict[str, Any]]) -> Optional[str]:
        view = [{"role": r.get("role"), "goal": r.get("goal"), "status": r.get("status"),
                 "answer": r.get("answer"), "error": r.get("error")} for r in results]
        user = json.dumps({"goal": goal, "agents": view}, ensure_ascii=False, default=str)[:9000]
        return self._call(_SYNTH_SYSTEM, user, max_tokens=500)

    # ------------------------------------------------------------------
    def run(self, goal: str) -> Dict[str, Any]:
        import experience
        from fleet import FleetCoordinator
        run_id = uuid.uuid4().hex[:12]
        t0 = time.monotonic()
        rep: Dict[str, Any] = {"run_id": run_id, "goal": goal, "answer": None}
        try:
            _trace({"run_id": run_id, "phase": "start", "goal": goal[:300]})
        except Exception as exc:
            rep.update(status="ledger_blocked", error=f"تعذر أثر البدء — لا تنفيذ: {type(exc).__name__}")
            return rep
        tools = self.worker_tools()
        try:
            plan = self.plan(goal, tools)
        except Exception as exc:
            rep.update(status="planner_failed", error=str(exc)[:300],
                       duration_s=round(time.monotonic() - t0, 2))
            self._finish(rep, [])
            return rep
        rep["plan"] = plan
        lessons_by_goal = {p["role"]: experience.lessons_text(p["goal"], k=2) for p in plan["subtasks"]}
        parts = [{"role": p["role"], "allowed_tools": tools,
                  "goal": p["goal"] + (f" (الأداة: {p['tool']})" if p.get("tool") not in (None, "none") else ""),
                  "planner": {"kind": "brain-chat", "lessons": lessons_by_goal.get(p["role"], ""),
                              "chat_fn": self._chat}}
                 for p in plan["subtasks"]]
        fleet = FleetCoordinator(self.registry, max_concurrency=self.max_concurrency,
                                 max_retries=1, worker_max_steps=self.worker_max_steps,
                                 worker_max_seconds=self.worker_max_seconds)
        frep = fleet.run(parts)
        goals_by_role = {p["role"]: p["goal"] for p in parts}
        results = []
        for r in frep.get("results") or []:
            r = dict(r)
            r["goal"] = goals_by_role.get(r.get("role"))
            results.append(r)
            experience.record_run(f"worker:{r.get('role')}", r["goal"] or "",
                                  {"status": r.get("status"), "answer": r.get("answer"),
                                   "error": r.get("error"), "steps": r.get("step_log") or []},
                                  manager_run=run_id)
        rep.update(agents_created=len(parts), fleet_status=frep.get("status"),
                   measured_peak_concurrency=frep.get("measured_peak_concurrency"),
                   agents=[{k: r.get(k) for k in ("role", "goal", "status", "answer", "error",
                                                  "attempts", "tools")} for r in results])
        done = [r for r in results if r.get("status") == "completed"]
        if not done:
            rep.update(status="failed", error="لم يُكمل أي وكيل مهمته",
                       duration_s=round(time.monotonic() - t0, 2))
            self._finish(rep, results)
            return rep
        try:
            text = self.synthesize(goal, results)
        except Exception as exc:  # TOLERATED: يُعلن أدناه
            text, rep["synth_error"] = None, f"{type(exc).__name__}"
        if text and text.strip():
            rep["answer"] = text.strip()
            rep["status"] = "completed" if len(done) == len(results) else "partial"
        else:
            rep["status"] = "synthesis_failed"
            rep["error"] = "العقل لم يكتب الجواب النهائي من نتائج الوكلاء"
        rep["duration_s"] = round(time.monotonic() - t0, 2)
        self._finish(rep, results)
        return rep

    def _finish(self, rep: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
        import experience
        tools = [t for r in results for t in (r.get("tools") or [])]
        experience.record_run(self.source, rep.get("goal") or "",
                              {"status": rep.get("status"), "answer": rep.get("answer"),
                               "error": rep.get("error"), "duration_s": rep.get("duration_s"),
                               "steps": [{"tool": t, "ok": True} for t in tools]},
                              agents=len(results), run_id=rep.get("run_id"))
        try:
            _trace({"run_id": rep.get("run_id"), "phase": "finish", "status": rep.get("status"),
                    "agents": len(results)})
        except Exception as exc:  # TOLERATED: الأفعال وقعت بأثرها؛ نهاية بلا أثر تُعلن
            rep["trace_warning"] = f"تعذر أثر النهاية: {type(exc).__name__}"


def manage(goal: str, max_agents: Any = None, owner: bool = True) -> Dict[str, Any]:
    """مدخل أداة agent.manage فوق السجل العام والعقل الحي."""
    from tool_registry import get_registry
    import chat_agent
    if not chat_agent.brain_enabled():
        return {"status": "brain_disabled", "goal": goal,
                "error": "العقل اللغوي غير مفعّل — لا تخطيط ولا وكلاء دونه"}
    reg = get_registry()
    allowed = chat_agent.allowed_tools(reg, owner=owner)
    n = MAX_AGENTS if max_agents in (None, "") else max(1, min(int(max_agents), MAX_AGENTS))
    return AgentManager(reg, max_agents=n, allowed_tools=allowed).run(goal)
