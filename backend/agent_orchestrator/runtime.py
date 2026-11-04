# -*- coding: utf-8 -*-
"""R-841 (4.1): محرك التشغيل — يقود الحلقة من الطلب إلى الرد.

التدفق: فهم (طبقة R-838) ← تخطيط ← (معاينة جافة إن طلبت) ← تنفيذ عبر
البوابات مع checkpoint لكل خطوة ← انعكاس ← معالجة فشل وإعادة تخطيط ←
انعكاس نهائي ← رد + أثر إجراءات + تحديث حالة.

كل حلقة: معرّف، أثر كامل، سقوف خطوات/تكلفة/زمن، إلغاء واستئناف.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional

from . import schemas
from .approval_gate import ApprovalGate
from .context_manager import ContextManager
from .execution_engine import ExecutionEngine, StepNeedsApproval
from .failure import FailureHandler
from .governor import Budget, BudgetExceededError, CostGovernor
from .hitl import HumanInTheLoop
from .memory import MemoryInterface
from .planner import Planner
from .policy_gate import PolicyGate
from .reflection import reflect, reflect_loop
from .rollback import RollbackEngine
from .state import StateStore
from .tool_registry import ToolRegistry, new_decision
from .tracing import Tracer

STATUS_ACTIVE = ("running", "pending_approval", "paused")


class OrchestratorSystem:
    """التجميع الحاكم: كل البوابات والمحركات في حلقة واحدة."""

    def __init__(self, data_dir: str, connector_executor=None,
                 org_policy=None, connector_registry=None,
                 connector_system=None):
        self.data_dir = data_dir
        self.tools = ToolRegistry()
        from .tool_registry import seed_registry
        self.tools = seed_registry()
        self.policy = PolicyGate(self.tools, org_policy, connector_registry)
        self.approvals = ApprovalGate()
        self.planner = Planner(self.tools)
        self.memory = MemoryInterface()
        self.context = ContextManager()
        self.governor = CostGovernor()
        self.hitl = HumanInTheLoop()
        self.state = StateStore(data_dir)
        self.tracers: Dict[str, Tracer] = {}
        self.failure = FailureHandler(self.planner)
        self._conn_system = connector_system
        self._conn_executor = connector_executor
        self._lock = threading.RLock()
        self._cancel_flags: set = set()

    # ------------------------------------------------------------ المنفذ
    def _executor(self) -> Any:
        """منفذ R-840 — لا يعاد بناء شيء: retry/قاطع/Idempotency موروثة."""
        if self._conn_executor is not None:
            return self._conn_executor
        system = self._conn_system
        if system is None:
            try:
                from ..connector_system import get_system
            except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
                from connector_system import get_system
            system = get_system()
        self._conn_executor = system.executor
        return self._conn_executor

    def _engine(self) -> ExecutionEngine:
        return ExecutionEngine(self.tools, self.policy, self.approvals,
                               self._executor())

    # ------------------------------------------------------------ الفهم
    def understand(self, utterance: str, session_id: str) -> Dict[str, Any]:
        """التمثيل الدلالي من طبقة الفهم R-838 — لا نص خام للتخطيط."""
        try:
            try:
                from ..multilingual import pipeline as _mp
            except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
                from multilingual import pipeline as _mp
            state = self._session_state(session_id, _mp)
            out = state.process_user_message(utterance)
            frame = out.get("frame") or {}
            return {
                "utterance": utterance,
                "intent": frame.get("intent", {}),
                "entities": frame.get("entities", []),
                "references": frame.get("references", []),
                "ambiguities": frame.get("ambiguities", []),
                "languages": frame.get("languages", ["ar"]),
                "user_lang": frame.get("languages", ["ar"])[0],
            }
        except Exception:  # TOLERATED: الفهم إثراء — الطلب يعمل بدونه
            return {"utterance": utterance, "intent": {"label": "request"},
                    "entities": [], "references": [], "ambiguities": [],
                    "languages": ["ar"], "user_lang": "ar"}

    def _session_state(self, session_id: str, pipeline_mod):
        """حالة محادثة لكل جلسة — الذاكرة عبر الحلقات محفوظة."""
        with self._lock:
            if not hasattr(self, "_conv_states"):
                self._conv_states: Dict[str, Any] = {}
            if session_id not in self._conv_states:
                self._conv_states[session_id] = \
                    pipeline_mod.ConversationState()
            return self._conv_states[session_id]

    # ------------------------------------------------------------ الحلقة
    def submit(self, request: Dict[str, Any],
               semantic: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """استقبال طلب بعقد 5.1 وقيادة الحلقة حتى الرد/الانتظار/الإيقاف."""
        schemas.validate(request, schemas.REQUEST_SCHEMA)
        loop_id = str(uuid.uuid4())
        sem = semantic or self.understand(
            request["utterance"], request["session_id"])
        state = {
            "loop_id": loop_id,
            "request": request,
            "semantic": sem,
            "status": "running",
            "plan": None,
            "results": [],
            "pending_approval": None,
            "reply": None,
            "budget_spent": None,
            "created_at": __import__("time").time(),
            "interventions": [],
        }
        tracer = Tracer(loop_id)
        with self._lock:
            self.tracers[loop_id] = tracer
        self.memory.loop_new(loop_id, request)
        self.state.save(state)

        # غموض مؤثر: لا أداة مطابقة أو مدخلات ناقصة → سؤال توضيحي واحد
        try:
            plan = self.planner.build(request, sem, tracer.trace_ref)
        except ValueError as exc:
            state["status"] = "needs_clarification"
            state["reply"] = _clarify_question(sem, str(exc))
            tracer.decision(new_decision(
                "", "clarify", "سؤال توضيحي واحد", [], str(exc), 0.9,
                tracer.trace_ref))
            self.state.save(state)
            return self._finalize(state, tracer)
        state["plan"] = plan
        tracer.decision(new_decision(
            "", "tool_choice", plan["mode"], [],
            plan["planning_reason"], 1.0, tracer.trace_ref))
        sel = plan.get("selection")
        if sel:  # R-842: قرار اختيار الأداة نفسه — المختار والبدائل والثقة
            alts = [f"{t}={s}" for t, s in sorted(
                sel["scores"].items(), key=lambda x: -x[1])
                if t not in sel["chosen"]] + list(sel["rejected"])
            tracer.decision(new_decision(
                "", "tool_choice", ",".join(sel["chosen"]) or "none", alts,
                f"{sel['planner']}: {sel.get('reason') or '-'}",
                float(sel["confidence"]), tracer.trace_ref))
        self.state.save(state)
        return self.run(loop_id)

    # ------------------------------------------------------------ التنفيذ
    def run(self, loop_id: str) -> Dict[str, Any]:
        """استئناف/استمرار الحلقة — checkpoint عند كل خطوة."""
        state = self.state.load(loop_id)
        if state is None:
            return {"ok": False, "error": "حلقة غير موجودة"}
        if state["status"] not in STATUS_ACTIVE:
            return self._view(state)
        request = state["request"]
        budget = Budget.from_constraints(request["constraints"])
        budget._spent_steps = len([r for r in state["results"]
                                   if r["status"] != "pending_approval"])
        engine = self._engine()
        tracer = self._tracer(loop_id)

        # معاينة جافة: خطة كاملة بلا تنفيذ (4.16)
        if request.get("dry_run"):
            state["status"] = "completed"
            state["reply"] = "معاينة جافة — لم يُنفَّذ شيء"
            previews = []
            for s in state["plan"]["steps"]:
                pv = engine.dry_run(s, request["permissions"], budget,
                                    actor=request["user_id"])
                previews.append(pv)
                tracer.span(s["step_id"], dict(s["inputs"]), pv, 0.0,
                            "dry_run")
            state["dry_run_preview"] = previews
            self.state.save(state)
            return self._finalize(state, tracer)

        # استئناف خطوة معلّقة على موافقة حُسمت
        pending = state.get("pending_approval")
        if pending and state["status"] == "pending_approval":
            ap = self.approvals.get(pending["approval_id"])
            if ap["status"] == "approved":
                state["status"] = "running"
                state["pending_approval"] = None
                self.state.save(state)
            elif ap["status"] == "rejected":
                step = next((s for s in state["plan"]["steps"]
                             if s["step_id"] == pending["step_id"]), None)
                if step:
                    r = {"step_id": step["step_id"], "status": "denied",
                         "output": {}, "error": {"code": "approval_rejected",
                                                "message": "رفض المستخدم"
                                                           " الموافقة —"
                                                           " لا تنفيذ",
                                                "action": "rejected"},
                         "cost": 0.0, "duration_ms": 0,
                         "trace_ref": tracer.trace_ref}
                    schemas.validate(r, schemas.STEP_RESULT_SCHEMA)
                    state["results"].append(r)
                state["pending_approval"] = None
                state["status"] = "running"
                self.state.save(state)

        results: List[Dict[str, Any]] = state["results"]
        try:
            # حلقة تنفيذ بمؤشر: إعادة التخطيط تستبدل الخطة فنتابع الجديدة
            i = 0
            executed = {r["step_id"] for r in results}
            while i < len(state["plan"]["steps"]):
                step = state["plan"]["steps"][i]
                i += 1
                if loop_id in self._cancel_flags:
                    return self._cancel(state, tracer)
                if step["step_id"] in executed:
                    continue  # مُنفذة في تشغيل سابق (استئناف)
                executed.add(step["step_id"])
                if self._blocked_by_failed_dep(step, results):
                    r = {"step_id": step["step_id"], "status": "skipped",
                         "output": {},
                         "error": {"code": "dependency_failed",
                                   "message": "اعتمادية فاشلة — تخطّي",
                                   "action": "none"},
                         "cost": 0.0, "duration_ms": 0,
                         "trace_ref": tracer.trace_ref}
                    schemas.validate(r, schemas.STEP_RESULT_SCHEMA)
                    results.append(r)
                    self.memory.loop_write_step(loop_id, r)
                    self.state.save(state)
                    continue
                try:
                    r = engine.execute(
                        step, request["permissions"], budget,
                        request["session_id"], actor=request["user_id"],
                        trace_ref=tracer.trace_ref, tracer=tracer)
                except StepNeedsApproval as pending_ap:
                    state["status"] = "pending_approval"
                    state["pending_approval"] = {
                        "approval_id": pending_ap.approval["approval_id"],
                        "step_id": step["step_id"]}
                    state["reply"] = (f"بانتظار موافقتك على: "
                                      f"{pending_ap.approval['action_summary']}"
                                      f" — الأثر: "
                                      f"{pending_ap.approval['impact_summary']}")
                    tracer.decision(new_decision(
                        step["step_id"], "approval", "انتظار موافقة", [],
                        "عملية حساسة — بوابة موافقة قبل التنفيذ", 1.0,
                        tracer.trace_ref))
                    self.state.save(state)
                    return self._finalize(state, tracer)
                results.append(r)
                self.memory.loop_write_step(loop_id, r)
                self.state.save(state)

                # انعكاس الخطوة — إلزامي (4.7)
                ref = reflect(r, step, tracer.trace_ref)
                tracer.decision(ref["decision"])
                self.memory.loop_write_decision(loop_id, ref["decision"])
                if ref["action"] in ("failure", "replan"):
                    handled = self.failure.handle(
                        r, state["plan"], tracer.trace_ref)
                    tracer.decision(handled["decision"])
                    if handled["action"] == "replan":
                        budget.record_replan()
                        state["plan"] = handled["plan"]
                        self.state.save(state)
                    elif handled["action"] in ("stop", "deny", "clarify"):
                        state["status"] = "failed" \
                            if handled["action"] == "stop" else state["status"]
                        state["reply"] = handled["reason"]
                        if handled["action"] == "clarify":
                            state["status"] = "needs_clarification"
                            state["reply"] = _clarify_question(
                                state["semantic"], handled["reason"])
                        self.state.save(state)
                        return self._finalize(state, tracer)
        except BudgetExceededError as exc:
            state["status"] = "failed"
            state["reply"] = str(exc)
            tracer.stop_reason(str(exc))
            self.state.save(state)
            return self._finalize(state, tracer)

        # انعكاس الحلقة النهائي — لا رد بدونه (ممنوع صريح)
        loop_ref = reflect_loop(results, state["plan"], budget.spent,
                                tracer.trace_ref)
        tracer.decision(loop_ref["decision"])
        if loop_ref["action"] == "deny":
            state["status"] = "failed"
            state["reply"] = loop_ref["reason"]
        else:
            state["status"] = "completed"
            state["reply"] = _compose_reply(state, results)
        state["budget_spent"] = budget.spent
        self.state.save(state)
        return self._finalize(state, tracer)

    # ------------------------------------------------------------ الإلغاء
    def cancel(self, loop_id: str, actor: str = "user") -> Dict[str, Any]:
        state = self.state.load(loop_id)
        if state is None:
            return {"ok": False, "error": "حلقة غير موجودة"}
        with self._lock:
            self._cancel_flags.add(loop_id)
        if state["status"] in STATUS_ACTIVE:
            state["status"] = "cancelled"
            tracer = self._tracer(loop_id)
            doc = RollbackEngine(self.tools, self._engine()) \
                .cancel_document(state)
            state["cancel_document"] = doc
            state["reply"] = (f"أُلغيت الحلقة — نُفذ {len(doc['executed'])}"
                              f" خطوة ولم يُنفَّذ {len(doc['not_executed'])}")
            tracer.stop_reason("إلغاء من المستخدم")
            self.state.save(state)
        return self._view(state)

    def _cancel(self, state, tracer) -> Dict[str, Any]:
        with self._lock:
            self._cancel_flags.discard(state["loop_id"])
        state["status"] = "cancelled"
        doc = RollbackEngine(self.tools, self._engine()).cancel_document(state)
        state["cancel_document"] = doc
        state["reply"] = f"أُلغيت — نفّذنا {len(doc['executed'])} خطوة"
        tracer.stop_reason("إلغاء أثناء التنفيذ")
        self.state.save(state)
        return self._finalize(state, tracer)

    # ------------------------------------------------------------ الموافقة
    def decide_approval(self, loop_id: str, approval_id: str,
                        decision: str, approved_by: str,
                        session_scope: bool = False) -> Dict[str, Any]:
        """حسم موافقة ثم استئناف الحلقة — الرفض يوثق ولا يُنفذ."""
        state = self.state.load(loop_id)
        if state is None:
            return {"ok": False, "error": "حلقة غير موجودة"}
        try:
            current = self.approvals.get(approval_id)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        if current["status"] == "pending":
            try:
                ap = self.approvals.decide(approval_id, approved_by, decision)
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        else:
            ap = current  # محسومة سلفًا (تجاوز مسؤول مثلًا) — استئناف فقط
        if decision in ("approved", "modified") and session_scope:
            step = next((s for s in state["plan"]["steps"]
                         if s["step_id"] == ap["step_id"]), None)
            if step:
                self.approvals.grant_session(
                    state["request"]["session_id"], step["tool_id"])
        tracer = self._tracer(loop_id)
        if ap["status"] == "pending":
            tracer.decision(new_decision(
                ap["step_id"], "approval", decision, [],
                f"قرار موافقة من {approved_by}: {ap['action_summary']}", 1.0,
                tracer.trace_ref))
        if state["status"] == "pending_approval":
            return self.run(loop_id)
        return self._view(state)

    # ------------------------------------------------------------ التراجع
    def rollback(self, loop_id: str, step_id: str, actor: str = "admin"
                 ) -> Dict[str, Any]:
        state = self.state.load(loop_id)
        if state is None:
            return {"ok": False, "error": "حلقة غير موجودة"}
        if state["status"] not in ("completed", "failed", "cancelled"):
            return {"ok": False, "error": "لا تراجع عن حلقة جارية — ألغِ أولًا"}
        budget = Budget.from_constraints(state["request"]["constraints"])
        tracer = self._tracer(loop_id)
        rb = RollbackEngine(self.tools, self._engine())
        out = rb.rollback(state, step_id, actor, budget, tracer.trace_ref,
                          tracer)
        if out.get("decision"):
            tracer.decision(out["decision"])
        state.setdefault("rollbacks", []).append(
            {"step_id": step_id, "ok": out.get("ok", False),
             "action": out.get("action"), "by": actor})
        self.state.save(state)
        return out

    # ------------------------------------------------------------ العرض
    def get(self, loop_id: str) -> Dict[str, Any]:
        state = self.state.load(loop_id)
        if state is None:
            return {"ok": False, "error": "حلقة غير موجودة"}
        return self._view(state)

    def trace(self, loop_id: str) -> Dict[str, Any]:
        with self._lock:
            t = self.tracers.get(loop_id)
        if t is None:
            state = self.state.load(loop_id)
            return {"ok": False,
                    "error": "لا أثر لهذه الحلقة (منتهية قبل التسجيل)"}
        return t.full()

    def pending_approvals(self) -> List[Dict[str, Any]]:
        return self.approvals.pending()

    def _tracer(self, loop_id: str) -> Tracer:
        with self._lock:
            if loop_id not in self.tracers:
                self.tracers[loop_id] = Tracer(loop_id)
            return self.tracers[loop_id]

    def _blocked_by_failed_dep(self, step, results) -> bool:
        by_id = {r["step_id"]: r for r in results}
        return any(by_id.get(d, {}).get("status")
                   in ("failure", "denied", "skipped", "timeout")
                   for d in step.get("depends_on", []))

    def _view(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, **{k: v for k, v in state.items()
                                if k != "semantic"},
                "plan": state.get("plan")}

    def _finalize(self, state: Dict[str, Any], tracer: Tracer
                  ) -> Dict[str, Any]:
        self.memory.session_write(
            state["request"]["session_id"],
            f"loop:{state['loop_id'][:8]}", state["status"])
        out = self._view(state)
        out["trace"] = tracer.summary()
        return out


def _clarify_question(semantic: Dict[str, Any], reason: str) -> str:
    lang = semantic.get("user_lang", "ar")
    if lang.startswith("en"):
        return (f"One clarification needed instead of guessing: {reason} —"
                " what exactly should I target?")
    return (f"سؤال توضيحي واحد بدل الافتراض: {reason} — ما الهدف تحديدًا؟")


def _compose_reply(state: Dict[str, Any], results: List[Dict[str, Any]]
                   ) -> str:
    """رد صادق من نتائج فعلية — لا ادعاء نتائج لم تحدث."""
    lang = state["semantic"].get("user_lang", "ar")
    parts, denied = [], 0
    for r in results:
        if r["status"] == "success":
            out = r.get("output", {})
            brief = ", ".join(f"{k}={_short(v)}" for k, v in
                              list(out.items())[:3] if k != "ok")
            parts.append(f"✓ {r['step_id']}{(': ' + brief) if brief else ''}")
        elif r["status"] == "denied":
            denied += 1
            parts.append(f"✗ {r['step_id']} رُفض: "
                         f"{r.get('error', {}).get('message', '')[:80]}")
        elif r["status"] == "skipped":
            parts.append(f"- {r['step_id']} تُخطّي (اعتمادية فاشلة)")
    head = ("تم التنفيذ:" if not lang.startswith("en")
            else "Executed:")
    return head + "\n" + "\n".join(parts) + (
        f"\n({denied} رُفضت حوكميًا)" if denied else "")


def _short(v: Any) -> str:
    s = str(v)
    return s[:60] + ("…" if len(s) > 60 else "")
