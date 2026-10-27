# -*- coding: utf-8 -*-
"""R-754 (ROADMAP_V5 §٣: ٣.١ + ٣.٢ + ٣.٣): مهام دائمة قابلة للاستئناف.

فوق حلقة الوكيل (R-753):
- ٣.١ كائن المهمة الدائم: ملف JSON لكل مهمة (كتابة ذرية + fsync). نقطة تفتيش
  بعد كل خطوة — أي بعد أثرها الموقّع `tool_invoked`. الاستئناف يمرر الخطوات
  المنجزة للحلقة سجلًّا، فالمخطط (عديم الحالة) يكمل من بعدها لا من الصفر.
- ٣.٢ منع تكرار الأفعال الخارجية: قبل كل استدعاء تُكتب «نية» (المفتاح
  task_id:index)، وتُزال عند نقطة التفتيش. نية معلقة عند الاستئناف:
    • أداة داخلية → تُعاد (لا أثر خارجي).
    • أداة خارجية تعلن مدخل idempotency_key → تُعاد بنفس المفتاح (الطرف يزيل
      التكرار — هذا شرط «بالضبط مرة»).
    • أداة خارجية بلا مفتاح → لا تُعاد أبدًا: needs_owner_review (مرة واحدة على
      الأكثر). لا ادعاء «بالضبط مرة» بلا دعم الطرف — حد صادق.
- ٣.٣ تقرير التقدم: يُقرأ من الملف على القرص حرفيًا (الخطوات المنجزة فقط).

حد صادق: الملفات على قرص العملية — الدوام **عبر النشر** على Fly يتطلب ١.٤.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

TERMINAL = frozenset({"completed", "needs_owner_review", "tool_failed",
                      "verification_failed", "budget_exhausted", "cancelled",
                      "invalid_step", "planner_failed", "ledger_blocked",
                      "checkpoint_failed"})
IDEMPOTENCY_INPUT = "idempotency_key"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class TaskStore:
    def __init__(self, root):
        self.root = Path(root)

    def _path(self, task_id: str) -> Path:
        if not task_id or not all(c.isalnum() or c in "-_" for c in task_id):
            raise ValueError("معرف مهمة غير صالح")
        return self.root / f"{task_id}.json"

    def save(self, task: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        task["updated_at"] = _now()
        fd, tmp = tempfile.mkstemp(dir=str(self.root), prefix=".task-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(task, fh, ensure_ascii=False, indent=1, default=str)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self._path(task["id"]))
            dfd = os.open(str(self.root), os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def load(self, task_id: str) -> Dict[str, Any]:
        p = self._path(task_id)
        if not p.exists():
            raise KeyError(task_id)
        return json.loads(p.read_text(encoding="utf-8"))


def default_planner_factory(spec: Dict[str, Any]):
    from agent_loop import BrainPlanner, ScriptedPlanner
    kind = (spec or {}).get("kind")
    if kind == "scripted":
        return ScriptedPlanner(spec.get("steps") or [])
    if kind == "brain":
        return BrainPlanner()
    if kind == "brain-chat":
        # R-790: مخطط المرحلتين (R-789b — 8/8 حيًا) للعمال، مع خبرتهم السابقة المشابهة
        from chat_agent import ChatPlanner
        return ChatPlanner(lessons=spec.get("lessons") or "", chat_fn=spec.get("chat_fn"))
    raise ValueError(f"نوع مخطط غير معروف: {kind!r}")


class DurableRunner:
    def __init__(self, store: TaskStore, registry, *,
                 external_tools: Iterable[str] = (),
                 planner_factory: Callable[[Dict[str, Any]], Any] = default_planner_factory,
                 max_steps: int = 16):
        self.store = store
        self.registry = registry
        self.external = set(external_tools)
        self.planner_factory = planner_factory
        self.max_steps = int(max_steps)

    def _inputs_of(self, tool: str) -> Dict[str, Any]:
        for t in self.registry.list_tools():
            if t["name"] == tool:
                return t.get("inputs") or {}
        return {}

    def create(self, goal: str, planner: Dict[str, Any]) -> str:
        self.planner_factory(planner)                   # يتحقق من صلاحية المواصفة مبكرًا
        tid = uuid.uuid4().hex[:16]
        self.store.save({"id": tid, "goal": goal, "planner": planner,
                         "status": "pending", "steps": [], "intents": {},
                         "created_at": _now(), "result": None, "runs": 0})
        return tid

    def progress(self, task_id: str) -> Dict[str, Any]:
        """٣.٣: من القرص حرفيًا — المنجز فقط."""
        t = self.store.load(task_id)
        return {"task_id": t["id"], "goal": t["goal"], "status": t["status"],
                "done_steps": len(t["steps"]),
                "steps": [{"index": s.get("index"), "tool": s.get("tool"),
                           "ok": s.get("ok"), "verified": s.get("verified"),
                           "fingerprint": s.get("fingerprint")} for s in t["steps"]],
                "pending_intents": sorted(t.get("intents", {}).keys(), key=int),
                "updated_at": t.get("updated_at"), "runs": t.get("runs", 0)}

    def run(self, task_id: str) -> Dict[str, Any]:
        from agent_loop import AgentLoop
        task = self.store.load(task_id)
        if task["status"] in TERMINAL:
            return {**(task.get("result") or {}), "status": task["status"],
                    "task_id": task_id, "resumed": False, "already_terminal": True}
        resumed = task["status"] == "running" or bool(task["steps"]) or bool(task.get("intents"))

        done_idx = {int(s["index"]) for s in task["steps"]}
        for k, intent in sorted(task.get("intents", {}).items(), key=lambda kv: int(kv[0])):
            if int(k) in done_idx:
                continue
            tool = intent.get("tool")
            if tool in self.external and IDEMPOTENCY_INPUT not in self._inputs_of(tool):
                task["status"] = "needs_owner_review"
                task["result"] = {"status": "needs_owner_review", "failed_step": int(k),
                                  "error": f"فعل خارجي {tool} قد يكون نُفذ قبل الانقطاع "
                                           "والأداة لا تقبل مفتاح منع التكرار — لا إعادة"}
                self.store.save(task)
                return {**task["result"], "task_id": task_id, "resumed": resumed}

        task["status"] = "running"
        task["runs"] = int(task.get("runs", 0)) + 1
        self.store.save(task)

        def before_invoke(idx: int, step: Dict[str, Any]) -> Dict[str, Any]:
            key = f"{task_id}:{idx}"
            extra = {}
            if IDEMPOTENCY_INPUT in self._inputs_of(step["tool"]):
                extra[IDEMPOTENCY_INPUT] = key
            task.setdefault("intents", {})[str(idx)] = {"tool": step["tool"], "key": key,
                                                         "at": _now()}
            self.store.save(task)                    # النية على القرص قبل التنفيذ
            return extra

        def after_step(record: Dict[str, Any]) -> None:
            task["steps"].append(record)
            task.get("intents", {}).pop(str(record["index"]), None)
            self.store.save(task)                    # نقطة تفتيش بعد الأثر الموقّع

        loop = AgentLoop(self.registry, self.planner_factory(task["planner"]),
                         max_steps=self.max_steps, caller=f"task:{task_id}")
        res = loop.run(task["goal"], run_id=task_id,
                       initial_steps=list(task["steps"]),
                       before_invoke=before_invoke, after_step=after_step)
        task["status"] = res["status"]
        task["result"] = {k: v for k, v in res.items() if k != "steps"}
        self.store.save(task)
        return {**res, "task_id": task_id, "resumed": resumed}


_RUNNER: Optional[DurableRunner] = None


def get_runner() -> DurableRunner:
    global _RUNNER
    if _RUNNER is None:
        from tool_registry import get_registry
        root = os.environ.get("SOVEREIGN_TASKS_DIR") or str(
            Path(__file__).resolve().parents[1] / "data" / "tasks")
        # R-756: أفعال الموصلات الخارجية لا تُعاد بعد انقطاع (٣.٢)
        external = set()
        try:
            import connectors
            hub = connectors.get_hub()
            for n in hub.names():
                external |= {f"connector.{n}.{a}" for a in hub.spec(n).external_actions}
        except Exception:  # TOLERATED: بلا موصلات = لا أفعال خارجية مسجلة
            external = set()
        _RUNNER = DurableRunner(TaskStore(root), get_registry(), external_tools=external)
    return _RUNNER
