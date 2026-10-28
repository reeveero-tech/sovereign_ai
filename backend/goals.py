# -*- coding: utf-8 -*-
"""R-791 (ROADMAP_V6 ٦.٩.٣ + ٦.٩.٤): أهداف وخطط دائمة + حلقة استقلال.

سؤال المالك (2026-10-27): «هل يستطيع أن يكون حرًا بحيث يتصرف بذكاء وحكمة وأهداف وخطط؟»
— قبل هذه الوحدة: لا. النظام يرد فقط حين يُسأل؛ لا أهداف دائمة، لا خطط، لا عمل ذاتي.

الآن:
- **الأهداف:** يضعها المالك (origin=owner) أو يقترحها العقل نفسه من ملاحظاته الحقيقية عن
  النظام (origin=self — `reflect`). كل هدف له أولوية وخطة وسجل تقدم.
- **العمل على هدف (`work`):** العقل يقرأ الهدف وخطته وما أُنجز فعلًا وخبرته السابقة، ويقرر
  بنفسه: work (مهمة جزئية ينفذها المدير R-790 بوكلاء ينشئهم) / replan / done / blocked.
  كل نتيجة تُسجل في سجل الهدف وفي الخبرة.
- **حلقة الاستقلال (`AutonomyLoop`):** خيط خلفي يوقظ العقل كل فاصل: يعمل على أعلى هدف نشط
  أولوية (والأقدم عملًا)، وإن لم توجد أهداف نشطة يتأمل حالة النظام ويقترح أهدافًا. لا تشغيل
  فوري عند الإقلاع (أول دورة بعد فاصل كامل). SOVEREIGN_AUTONOMY=1 يفعّلها؛ الفاصل
  SOVEREIGN_AUTONOMY_INTERVAL (ثوانٍ، افتراضي 1800).

الحدود (معلنة لا مخفية):
- أدوات العمل الذاتي = أدوات المدير عدا أفعال الموصلات الخارجية (connector.*) وقرارات المالك
  (proposals.decide) والوسائط والقياس الثقيل — لا فعل خارجي باسم المالك دون طلبه.
- تنفيذ الكود يبقى محجوبًا (D-041)، وتعديل شيفرة النظام نفسه يبقى باقتراح وموافقة (٤.٥).
- سقف تشغيلات لكل هدف (GOAL_MAX_RUNS) ثم حالة exhausted صادقة؛ سقف أهداف ذاتية نشطة.
- الذاكرة إلحاقية (ExperienceStore — المادة ٨): حالة الهدف تُعاد بناؤها من أحداثه.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sovereign.goals")

GOAL_MAX_RUNS = int(os.getenv("GOAL_MAX_RUNS", "6") or 6)
MAX_SELF_GOALS = int(os.getenv("AUTONOMY_MAX_SELF_GOALS", "3") or 3)
STATUSES = ("active", "done", "blocked", "exhausted", "paused", "failed")
AUTONOMY_EXCLUDED = frozenset({"proposals.decide", "media.image", "benchmark.run"})
AUTONOMY_EXCLUDED_PREFIXES = ("connector.",)

_NEXT_SYSTEM = (
    "أنت العقل المستقل لنظام sovereign_ai، تعمل على هدف دائم. أمامك: الهدف، خطته، ما أُنجز "
    "فعلًا (نتائج حقيقية من وكلاء)، وتجارب سابقة. قرر الخطوة التالية بحكمة:\n"
    "- work: مهمة جزئية واحدة واضحة قابلة للتنفيذ بالأدوات المتاحة ولم تُنجز بعد.\n"
    "- replan: الخطة الحالية لا تصلح — اكتب خطة جديدة (خطوات قصيرة).\n"
    "- done: الهدف تحقق — اكتب ملخصًا مبنيًا على النتائج المنجزة فقط.\n"
    "- blocked: لا يمكن تحقيقه بالأدوات المتاحة — اذكر السبب الحقيقي.\n"
    "لا تكرر مهمة نجحت. الأدوات المتاحة للوكلاء:\n{tools}\n{lessons}"
    'أجب JSON فقط: {{"decision":"work|replan|done|blocked","task":"","plan":[],"summary":"","reason":""}}'
)

_PLAN_SYSTEM = (
    "أنت العقل المستقل لنظام sovereign_ai. ضع خطة قصيرة (2 إلى 5 خطوات) لتحقيق الهدف بالأدوات "
    "المتاحة فقط. الأدوات:\n{tools}\n"
    'أجب JSON فقط: {{"plan":["<خطوة>", "..."]}}'
)

_REFLECT_SYSTEM = (
    "أنت العقل المستقل لنظام sovereign_ai. أمامك ملاحظات حقيقية عن حالة النظام الآن وأهدافه "
    "القائمة وخبرته. اقترح من 0 إلى {n} أهداف جديدة مفيدة للمالك وللنظام، قابلة للتحقيق بالأدوات "
    "المتاحة (فحص، تشخيص عطل حقيقي ظاهر في الملاحظات، تعلم معرفة تنقصه). لا تكرر هدفًا قائمًا، "
    "ولا تقترح شيئًا لا تدعمه الملاحظات. صفر أهداف مقبول إن لم يلزم شيء.\nالأدوات:\n{tools}\n"
    'أجب JSON فقط: {{"goals":[{{"title":"<هدف>","why":"<سبب من الملاحظات>","priority":1}}]}}'
)
# R-791a: كل هدف ذاتي يحمل دليلًا منقولًا من الملاحظات — يُرفض ما لا يسنده نصها (قياس حي:
# اقترح العقل «إعادة ترتيب الأحداث في الذاكرة» بلا أي ملاحظة تسنده)
_REFLECT_EVIDENCE_RULE = (
    "\nلكل هدف حقل evidence: انقل حرفيًا من الملاحظات الرقم أو النص الذي يثبت الحاجة إليه. "
    "هدف بلا دليل من الملاحظات يُرفض. الأهداف بالعربية."
    '\nأجب JSON فقط: {"goals":[{"title":"<هدف>","why":"<سبب>","evidence":"<نص من الملاحظات>",'
    '"priority":1}]}'
)


def grounded(evidence: str, observations_text: str) -> bool:
    """الدليل مسنود إن ورد نصه في الملاحظات، أو ورد فيها رقم منه (رقمان على الأقل)."""
    import re as _re
    ev = " ".join((evidence or "").split())
    obs = " ".join((observations_text or "").split())
    if len(ev) >= 4 and ev in obs:
        return True
    nums = [n for n in _re.findall(r"\d+(?:\.\d+)?", ev) if len(n) >= 2]
    return bool(nums) and all(n in obs for n in nums)

# R-791a: فحص التحقق مرحلة مستقلة صغيرة بعد كل تشغيل — قياس حي: qwen2.5:3b لم يعلن «done»
# بعد أن أجاب الوكيل بالرقم المطلوب (148,887 حدثًا)، وكرر مهمة ناجحة مرتين.
_CHECK_SYSTEM = (
    "أنت مدقق صارم. أمامك هدف ونتائج حقيقية أنجزها الوكلاء. هل تحقق الهدف كاملًا بهذه النتائج؟ "
    "achieved=true فقط إن كانت النتائج تجيب عن الهدف فعلًا. summary: الجواب للمالك بالعربية من "
    "النتائج حرفيًا (الأرقام كما وردت). missing: ما الذي ما زال ناقصًا إن لم يتحقق."
    '\nأجب JSON فقط: {"achieved":true,"summary":"","missing":""}'
)
# R-793 (٦.٩.٧): المدقق يرى نتائج الأدوات الخام لا الجواب المُصاغ وحده — قياس حي: قال الوكيل
# «22» والحقيقة total_events=152413. التناقض بين الجواب والنتيجة الخام ⇒ achieved=false.
_CHECK_SYSTEM = _CHECK_SYSTEM + (
    " إن وُجد tool_results (نتائج الأدوات الخام) فهي المرجع: إن ناقض الجواب رقمًا فيها فـ"
    "achieved=false واذكر التناقض في missing، وفي summary انقل الأرقام من tool_results.")
CHECK_SCHEMA = {"type": "object",
                "properties": {"achieved": {"type": "boolean"}, "summary": {"type": "string"},
                               "missing": {"type": "string"}},
                "required": ["achieved"]}
REPEAT_SIMILARITY = 0.6

NEXT_SCHEMA = {"type": "object",
               "properties": {"decision": {"type": "string",
                                           "enum": ["work", "replan", "done", "blocked"]},
                              "task": {"type": "string"},
                              "plan": {"type": "array", "items": {"type": "string"}},
                              "summary": {"type": "string"}, "reason": {"type": "string"}},
               "required": ["decision"]}
PLAN_SCHEMA = {"type": "object", "properties": {"plan": {"type": "array", "maxItems": 6,
                                                         "items": {"type": "string"}}},
               "required": ["plan"]}


def reflect_schema(n: int) -> Dict[str, Any]:
    return {"type": "object",
            "properties": {"goals": {"type": "array", "maxItems": max(0, n),
                                     "items": {"type": "object",
                                                                "properties": {"title": {"type": "string"},
                                                              "why": {"type": "string"},
                                                              "evidence": {"type": "string"},
                                                              "priority": {"type": "integer"}},
                                               "required": ["title", "evidence"]}}},
            "required": ["goals"]}


def _trace(payload: Dict[str, Any]) -> None:
    from memory.core import get_core
    get_core().append_event("goal_event", payload, user="autonomy")


class GoalStore:
    """أحداث الأهداف إلحاقية في ExperienceStore (ملف goals.jsonl) — الحالة تُعاد بناؤها."""

    def __init__(self, store=None):
        if store is None:
            import experience
            store = experience.get_store()
        self.store = store

    def _events(self) -> List[Dict[str, Any]]:
        return self.store._load("goal")

    def state(self) -> Dict[str, Dict[str, Any]]:
        goals: Dict[str, Dict[str, Any]] = {}
        for e in self._events():
            gid, op = e.get("goal_id"), e.get("op")
            if op == "add":
                goals[gid] = {"id": gid, "title": e.get("title"), "why": e.get("why"),
                              "origin": e.get("origin"), "priority": e.get("priority", 3),
                              "status": "active", "plan": [], "runs": [], "created": e.get("ts"),
                              "last_worked": None, "summary": None}
            elif gid in goals:
                g = goals[gid]
                if op == "plan":
                    g["plan"] = list(e.get("plan") or [])
                elif op == "run":
                    g["runs"].append({k: e.get(k) for k in ("task", "status", "answer", "error",
                                                            "agents", "manager_run", "ts",
                                                            "tools")})
                    g["last_worked"] = e.get("ts")
                elif op == "evidence":  # R-793: نتائج خام لآخر تشغيل (إلحاقي لا يمس حدث run)
                    if g["runs"]:
                        g["runs"][-1]["raw_results"] = list(e.get("raw_results") or [])
                elif op == "status":
                    g["status"] = e.get("status")
                    g["summary"] = e.get("summary") or g["summary"]
        return goals

    def add(self, title: str, *, origin: str = "owner", why: str = "",
            priority: int = 3) -> Dict[str, Any]:
        title = (title or "").strip()
        if not title:
            raise ValueError("هدف فارغ")
        gid = "G-" + uuid.uuid4().hex[:8]
        self.store._append("goal", {"op": "add", "goal_id": gid, "title": title[:400],
                                    "why": (why or "")[:400], "origin": origin,
                                    "priority": max(1, min(int(priority or 3), 5))})
        return self.state()[gid]

    def log(self, gid: str, op: str, **fields) -> None:
        if gid not in self.state():
            raise KeyError(f"هدف غير موجود: {gid}")
        if op == "status" and fields.get("status") not in STATUSES:
            raise ValueError(f"حالة غير معروفة: {fields.get('status')!r}")
        self.store._append("goal", {"op": op, "goal_id": gid, **fields})

    def active(self) -> List[Dict[str, Any]]:
        act = [g for g in self.state().values() if g["status"] == "active"]
        # أعلى أولوية (1 أعلى) ثم الأقدم عملًا
        return sorted(act, key=lambda g: (g["priority"], g["last_worked"] or 0, g["created"] or 0))


class GoalEngine:
    def __init__(self, registry=None, *, chat_fn=None, store: Optional[GoalStore] = None,
                 manager_factory=None, max_runs: int = GOAL_MAX_RUNS):
        if registry is None:
            from tool_registry import get_registry
            registry = get_registry()
        self.registry = registry
        self._chat = chat_fn
        self.goals = store or GoalStore()
        self.max_runs = int(max_runs)
        self._manager_factory = manager_factory

    def _call(self, system: str, user: str, **kw) -> Optional[str]:
        chat = self._chat
        if chat is None:
            import ollama_client
            chat = ollama_client.chat
        return chat(system, user, **kw)

    def tools(self) -> List[str]:
        from manager import WORKER_EXCLUDED
        out = []
        for t in self.registry.list_tools():
            n = t["name"]
            if n in WORKER_EXCLUDED or n in AUTONOMY_EXCLUDED:
                continue
            if any(n.startswith(p) for p in AUTONOMY_EXCLUDED_PREFIXES):
                continue
            out.append(n)
        return out

    def _catalog(self, tools: List[str]) -> str:
        cat = {t["name"]: t for t in self.registry.list_tools()}
        return "\n".join(f"- {n}: {cat[n].get('description', '')[:110]}" for n in tools if n in cat)

    def _manager(self, tools: List[str]):
        if self._manager_factory is not None:
            return self._manager_factory(tools)
        from manager import AgentManager
        return AgentManager(self.registry, chat_fn=self._chat, allowed_tools=tools,
                            source="goal")

    def _json(self, system: str, user: str, schema: Dict[str, Any], max_tokens: int):
        from agent_loop import PlannerError, _extract_json
        reply = self._call(system, user, json_mode=True, max_tokens=max_tokens, json_schema=schema)
        if reply is None:
            from chat_agent import _brain_failure_reason
            raise PlannerError(_brain_failure_reason())
        return _extract_json(reply)

    # ------------------------------------------------------------------
    def work(self, gid: str) -> Dict[str, Any]:
        """خطوة واحدة على هدف: قرار العقل ثم تنفيذه — كل شيء يُسجل."""
        import experience
        g = self.goals.state().get(gid)
        if g is None:
            return {"status": "not_found", "goal_id": gid}
        if g["status"] != "active":
            return {"status": "not_active", "goal_id": gid, "goal_status": g["status"]}
        tools = self.tools()
        catalog = self._catalog(tools)
        try:
            _trace({"goal_id": gid, "phase": "work", "title": (g["title"] or "")[:200]})
        except Exception as exc:
            return {"status": "ledger_blocked", "goal_id": gid,
                    "error": f"تعذر الأثر — لا تنفيذ: {type(exc).__name__}"}
        if len(g["runs"]) >= self.max_runs:
            self.goals.log(gid, "status", status="exhausted",
                           summary=f"بلغ سقف التشغيلات ({self.max_runs}) دون إعلان تحقق")
            return {"status": "exhausted", "goal_id": gid}
        try:
            if not g["plan"]:
                p = self._json(_PLAN_SYSTEM.format(tools=catalog), g["title"], PLAN_SCHEMA, 300)
                plan = [str(x)[:200] for x in (p.get("plan") or []) if str(x).strip()][:6]
                if plan:
                    self.goals.log(gid, "plan", plan=plan)
                    g["plan"] = plan
            lessons = experience.lessons_text(g["title"], k=3)
            user = json.dumps({"goal": g["title"], "why": g.get("why"), "plan": g["plan"],
                               "done_so_far": [{"task": r["task"], "status": r["status"],
                                                "answer": (r.get("answer") or "")[:300],
                                                "error": r.get("error")} for r in g["runs"]],
                               "plan_tools_not_run": self.unrun_plan_tools(g)},
                              ensure_ascii=False, default=str)[:8000]
            d = self._json(_NEXT_SYSTEM.format(
                tools=catalog, lessons=("تجارب سابقة:\n" + lessons + "\n") if lessons else ""),
                user, NEXT_SCHEMA, 400)
        except Exception as exc:
            return {"status": "planner_failed", "goal_id": gid, "error": str(exc)[:300]}
        decision = d.get("decision")
        if decision == "done":
            summary = str(d.get("summary") or "")[:800]
            self.goals.log(gid, "status", status="done", summary=summary)
            return {"status": "done", "goal_id": gid, "summary": summary}
        if decision == "blocked":
            reason = str(d.get("reason") or "")[:500]
            self.goals.log(gid, "status", status="blocked", summary=reason)
            # R-796: هدف تعذر بالأدوات المتاحة ⇒ مهمة تطوير ذاتي (النظام يبني ما ينقصه)
            try:
                import self_develop
                self_develop.get_engine().request(
                    f"هدف متعذر: {g.get('title') or gid}"[:300],
                    detail=f"السبب الذي أعلنه العقل: {reason}", source="goal", ref=gid)
            except Exception as exc:  # TOLERATED: تعذر الربط لا يغيّر قرار الهدف — يُسجل
                logger.warning("R-796: تعذر تحويل الهدف المتعذر %s إلى مهمة تطوير: %s", gid, exc)
            return {"status": "blocked", "goal_id": gid, "reason": reason}
        if decision == "replan":
            plan = [str(x)[:200] for x in (d.get("plan") or []) if str(x).strip()][:6]
            if plan:
                self.goals.log(gid, "plan", plan=plan)
            return {"status": "replanned", "goal_id": gid, "plan": plan}
        task = str(d.get("task") or "").strip()
        if not task:
            return {"status": "invalid_decision", "goal_id": gid, "decision": d}
        repeat = next((r for r in g["runs"] if r.get("status") in ("completed", "partial")
                       and experience.similarity(task, r.get("task") or "") >= REPEAT_SIMILARITY),
                      None)
        if repeat is not None:
            # R-791a: لا تكرار لمهمة نجحت — يُسجل ويُفحص التحقق من النتائج القائمة
            self.goals.log(gid, "run", task=task[:400], status="repeat_prevented",
                           answer=None, error=f"تكرار لمهمة منجزة: {repeat.get('task')}"[:300])
            out = {"status": "repeat_prevented", "goal_id": gid, "task": task}
        else:
            rep = self._manager(tools).run(task)
            self.goals.log(gid, "run", task=task[:400], status=rep.get("status"),
                           answer=(rep.get("answer") or "")[:800], error=rep.get("error"),
                           agents=rep.get("agents_created"), manager_run=rep.get("run_id"),
                           tools=rep.get("tools_used"))
            if rep.get("raw_results"):  # R-793 (٦.٩.٧)
                self.goals.log(gid, "evidence", raw_results=list(rep["raw_results"])[:12])
            out = {"status": "worked", "goal_id": gid, "task": task,
                   "run_status": rep.get("status"), "answer": rep.get("answer"),
                   "agents_created": rep.get("agents_created"), "error": rep.get("error")}
        out["check"] = self.check(gid)
        if out["check"].get("achieved"):
            out["goal_status"] = "done"
        return out

    def unrun_plan_tools(self, g: Dict[str, Any]) -> List[str]:
        """R-792a: أدوات في خطة الهدف نفسها (أسماء أدوات مسجلة) لم تُنفذ بنجاح في أي تشغيل.

        حي 2026-10-27: الخطة [memory.stats, disk.status]، نُفذ disk.status وحده، فأعلن
        العقل «تحقق» — نجاح زائف. الحارس بنيوي (خطة النظام نفسه ⇔ الأدوات المنفذة فعلًا)
        لا جواب مزروع. تشغيلات قديمة بلا حقل tools ⇒ لا حكم (لا نعرف ما نُفذ)."""
        runs = g.get("runs") or []
        if not any("tools" in r and r.get("tools") is not None for r in runs):
            return []
        try:
            names = {t["name"] for t in self.registry.list_tools()}
        except Exception:  # TOLERATED: بلا سجل لا حارس
            return []
        used = {t for r in runs if r.get("status") in ("completed", "partial")
                for t in (r.get("tools") or [])}
        return [p for p in (g.get("plan") or []) if p in names and p not in used]

    def check(self, gid: str) -> Dict[str, Any]:
        """R-791a: هل تحقق الهدف بالنتائج المنجزة؟ — قرار العقل في مرحلة مستقلة."""
        g = self.goals.state().get(gid)
        done = [r for r in (g or {}).get("runs", []) if r.get("status") in ("completed", "partial")
                and r.get("answer")]
        if not g or not done:
            return {"achieved": False, "missing": "لا نتائج منجزة بعد"}
        pending = self.unrun_plan_tools(g)
        if pending:  # R-792a: لا «تحقق» وخطوات الخطة لم تُنفذ
            return {"achieved": False, "missing": "خطوات من الخطة لم تُنفذ: " + "، ".join(pending),
                    "guard": "plan_tools_not_run"}
        user = json.dumps({"goal": g["title"], "results": [{"task": r["task"],
                                                            "answer": (r["answer"] or "")[:600]}
                                                           for r in done[-4:]]},
                          ensure_ascii=False, default=str)[:7000]
        raw = [x for r in done[-4:] for x in (r.get("raw_results") or [])][:8]
        if raw:  # R-793 (٦.٩.٧): المدقق يرى الخام مع الجواب
            user = json.dumps({"goal": g["title"], "tool_results": raw,
                               "results": [{"task": r["task"], "answer": (r["answer"] or "")[:600]}
                                           for r in done[-4:]]},
                              ensure_ascii=False, default=str)[:7000]
        try:
            c = self._json(_CHECK_SYSTEM, user, CHECK_SCHEMA, 350)
        except Exception as exc:  # TOLERATED: الفحص يُعاد في الخطوة التالية
            return {"achieved": False, "error": str(exc)[:200]}
        if c.get("achieved") is True:
            self.goals.log(gid, "status", status="done", summary=str(c.get("summary") or "")[:800])
            return {"achieved": True, "summary": c.get("summary")}
        return {"achieved": False, "missing": str(c.get("missing") or "")[:300]}

    def observations(self) -> Dict[str, Any]:
        """ملاحظات حقيقية من أدوات القراءة — مادة التأمل (لا افتراض)."""
        import experience
        obs: Dict[str, Any] = {}
        registered = {t["name"] for t in self.registry.list_tools()}
        for name in ("health.snapshot", "defects.scan"):
            if name not in registered:
                continue
            try:
                inv = self.registry.invoke(name, caller="autonomy", inputs={})
                if inv.get("ok"):
                    from chat_agent import _compact
                    obs[name] = _compact(inv.get("result"), 1200)
                else:
                    obs[name] = f"فشل: {inv.get('error')}"
            except Exception as exc:  # TOLERATED: ملاحظة ناقصة تُعلن
                obs[name] = f"تعذر: {type(exc).__name__}"
        if "disk.status" in registered:  # R-792: مساحة/عُقد القرص الحقيقية
            try:
                inv = self.registry.invoke("disk.status", caller="autonomy", inputs={})
                res = inv.get("result") if inv.get("ok") else None
                if isinstance(res, dict) and res.get("local_volume"):
                    obs["local_volume"] = res["local_volume"]
            except Exception as exc:  # TOLERATED: ملاحظة ناقصة تُعلن
                obs["local_volume"] = f"تعذر: {type(exc).__name__}"
        st = experience.get_store()
        stats = st.stats()
        obs["experience"] = {"experiences": stats["experiences"], "by_status": stats["by_status"]}
        obs["failing_tools"] = {t: d for t, d in st.tool_stats().items() if d["failed"]}
        return obs

    def reflect(self) -> Dict[str, Any]:
        """العقل يتأمل حالة النظام الحقيقية ويقترح أهدافًا لنفسه (بسقف)."""
        import experience
        state = self.goals.state()
        active_self = [g for g in state.values() if g["origin"] == "self" and g["status"] == "active"]
        room = MAX_SELF_GOALS - len(active_self)
        if room <= 0:
            return {"status": "skipped", "reason": f"سقف الأهداف الذاتية النشطة ({MAX_SELF_GOALS})"}
        tools = self.tools()
        observations = self.observations()
        obs_text = json.dumps(observations, ensure_ascii=False, default=str)
        user = json.dumps({"observations": observations,
                           "existing_goals": [{"title": g["title"], "status": g["status"]}
                                              for g in state.values()][-15:]},
                          ensure_ascii=False, default=str)[:9000]
        try:
            out = self._json(_REFLECT_SYSTEM.format(n=room, tools=self._catalog(tools))
                             + _REFLECT_EVIDENCE_RULE, user, reflect_schema(room), 400)
        except Exception as exc:
            return {"status": "planner_failed", "error": str(exc)[:300]}
        added, rejected = [], []
        existing = [g["title"] or "" for g in state.values()]
        for item in (out.get("goals") or [])[:room]:
            title = str((item or {}).get("title") or "").strip()
            if not title:
                continue
            if not grounded(str(item.get("evidence") or ""), obs_text):
                rejected.append({"title": title[:200], "evidence": str(item.get("evidence") or "")[:200],
                                 "reason": "الدليل لا يرد في الملاحظات الحقيقية"})
                continue
            if any(experience.similarity(title, e) >= 0.5 for e in existing + [a["title"] for a in added]):
                continue
            added.append(self.goals.add(title, origin="self", why=str(item.get("why") or ""),
                                        priority=int(item.get("priority") or 3)))
        return {"status": "reflected", "added": [{"id": a["id"], "title": a["title"]} for a in added],
                "rejected": rejected}

    def tick(self) -> Dict[str, Any]:
        """دورة استقلال واحدة: عمل على أعلى هدف نشط، وإلا تأمل واقتراح."""
        act = self.goals.active()
        if act:
            return {"tick": "work", **self.work(act[0]["id"])}
        return {"tick": "reflect", **self.reflect()}


class AutonomyLoop:
    def __init__(self, engine_factory=GoalEngine, interval: float = 1800.0, enabled: bool = False,
                 reason: str = ""):
        self.engine_factory = engine_factory
        self.interval = float(interval)
        self.enabled = enabled
        self.reason = reason
        self.ticks = 0
        self.last: Optional[Dict[str, Any]] = None
        self.last_at: Optional[float] = None
        self.next_at: Optional[float] = None
        self._stop = threading.Event()
        self._busy = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def run_once(self) -> Dict[str, Any]:
        if not self._busy.acquire(blocking=False):
            return {"tick": "skipped", "reason": "دورة سابقة ما زالت تعمل"}
        try:
            try:
                out = self.engine_factory().tick()
            except Exception as exc:  # TOLERATED: عزل — فشل دورة لا يوقف الحلقة ويُسجل
                out = {"tick": "crashed", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            self.ticks += 1
            self.last, self.last_at = out, time.time()
            return out
        finally:
            self._busy.release()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.next_at = time.time() + self.interval
            if self._stop.wait(self.interval):
                break
            out = self.run_once()
            logger.info("autonomy tick: %s", {k: out.get(k) for k in ("tick", "status", "goal_id")})

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="autonomy", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def status(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "reason": self.reason, "interval_s": self.interval,
                "ticks": self.ticks, "last_at": self.last_at, "next_at": self.next_at,
                "running": bool(self._thread and self._thread.is_alive()),
                "last": self.last}


_LOOP: Optional[AutonomyLoop] = None


def build_from_env() -> AutonomyLoop:
    global _LOOP
    on = os.getenv("SOVEREIGN_AUTONOMY", "0").strip().lower() in ("1", "true", "yes", "on")
    no_bg = os.getenv("SOVEREIGN_DISABLE_BACKGROUND_THREADS", "0") == "1"
    try:
        interval = max(60.0, float(os.getenv("SOVEREIGN_AUTONOMY_INTERVAL", "1800") or 1800))
    except ValueError:
        interval = 1800.0
    if not on:
        reason = "معطلة (SOVEREIGN_AUTONOMY غير مفعّل)"
    elif no_bg:
        reason = "معطلة (SOVEREIGN_DISABLE_BACKGROUND_THREADS=1)"
    else:
        reason = f"مفعّلة — دورة كل {int(interval)} ثانية"
    _LOOP = AutonomyLoop(interval=interval, enabled=on and not no_bg, reason=reason)
    return _LOOP


def get_loop() -> AutonomyLoop:
    global _LOOP
    if _LOOP is None:
        _LOOP = AutonomyLoop(enabled=False, reason="لم تُبنَ من البيئة بعد")
    return _LOOP
