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

R-853 (٦.٢.٤ / D-068): استئناف بعد القتل فعلًا لا نظريًا:
- مرآة دائمة: كل نقطة تفتيش (ونية) تُدفع إلى المخزن الدائم (فضاء ``tasks``) قبل
  الخطوة التالية؛ فشل الدفع = checkpoint_failed (لا خطوة بلا نقطة دائمة). قرص
  جديد (إعادة تشغيل/نشر Render) يقرأ المهمة من المخزن بأعلى ``rev``.
- عقد إيجار: ``lease`` = {boot, until} يُجدَّد بنبض كل ``HEARTBEAT_S``؛ تشغيلان
  متزامنان لمهمة واحدة مرفوضان (في العملية نفسها أو بإيجار حي من إقلاع آخر).
- استئناف تلقائي: عند الإقلاع يمسح ماسح المهام اليتيمة (running/pending بإيجار
  منتهٍ) ويستأنفها في الخلفية.
- مخطط ``chain``: خطوات معلنة تشير لنواتج سابقة (``$steps.N.path`` أو
  ``{{steps.N.path}}``) — تسلسل أدوات حقيقي، حتمي ومعلن (ليس ذكاء تخطيط ٦.٢.٣).
"""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

TERMINAL = frozenset({"completed", "needs_owner_review", "tool_failed",
                      "verification_failed", "budget_exhausted", "cancelled",
                      "invalid_step", "planner_failed", "ledger_blocked",
                      "checkpoint_failed"})
IDEMPOTENCY_INPUT = "idempotency_key"
DURABLE_NAMESPACE = "tasks"
BOOT_ID = uuid.uuid4().hex[:12]     # هوية هذا الإقلاع — تميّز الخطوات قبل القتل وبعده
LEASE_S = 60
HEARTBEAT_S = 15
BOOT_SCAN_WINDOW_S = 300
BOOT_SCAN_EVERY_S = 20
CHAIN_MAX_STEPS = 16
try:
    import socket as _socket
    _HOST = _socket.gethostname()
except OSError:  # TOLERATED (R-853): بلا اسم مضيف = لا كشف موت محلي (انتظار الإيجار)
    _HOST = ""
logger = logging.getLogger("durable_tasks")


class DurableWriteError(RuntimeError):
    """تعذر دفع نقطة التفتيش للمخزن الدائم — لا خطوة تالية (فشل مغلق)."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class TaskStore:
    def __init__(self, root, remote: Any = None):
        self.root = Path(root)
        self.remote = remote          # R-853: مرآة دائمة (SupabaseDisk) أو None
        self._lock = threading.Lock()

    def _path(self, task_id: str) -> Path:
        if not task_id or not all(c.isalnum() or c in "-_" for c in task_id):
            raise ValueError("معرف مهمة غير صالح")
        return self.root / f"{task_id}.json"

    def save(self, task: Dict[str, Any]) -> None:
        import skills_durable
        text = json.dumps(task, ensure_ascii=False, default=str)
        if skills_durable._has_secret(text):   # R-853: لا سر على القرص ولا في المخزن
            raise DurableWriteError("سجل المهمة يحوي نمط سر — لا يُحفظ")
        with self._lock:
            task["rev"] = int(task.get("rev", 0)) + 1
            self._save_local(task)
            if self.remote is not None:
                self._push(task)

    def _push(self, task: Dict[str, Any]) -> None:
        """R-853: الدفع قبل الخطوة التالية؛ رفض المخزن = خطأ صريح (لا خطوة تالية)."""
        text = json.dumps(task, ensure_ascii=False, default=str)
        try:
            ok = bool(self.remote.save_blob(DURABLE_NAMESPACE, task["id"], json.loads(text)))
        except Exception as exc:  # TOLERATED (R-853): يتحول لخطأ صريح أدناه لا صمت
            ok, err = False, type(exc).__name__
        else:
            err = "rejected"
        if not ok:
            raise DurableWriteError(f"المخزن الدائم لم يقبل نقطة التفتيش ({err})")

    def _save_local(self, task: Dict[str, Any]) -> None:
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

    def _local(self, task_id: str) -> Optional[Dict[str, Any]]:
        p = self._path(task_id)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def load(self, task_id: str) -> Dict[str, Any]:
        """R-853: النسخة الأحدث (rev) بين القرص والمخزن؛ قرص جديد يُعبّأ من المخزن."""
        local = self._local(task_id)
        remote = None
        if self.remote is not None:
            try:
                remote = self.remote.load_blob(DURABLE_NAMESPACE, task_id)
            except Exception:  # TOLERATED (R-853): المخزن بعيد — النسخة المحلية تكفي إن وُجدت
                remote = None
        best = _newest(local, remote)
        if best is None:
            raise KeyError(task_id)
        if best is not local:
            with self._lock:
                self._save_local(best)            # تعبئة القرص الجديد بلا رفع rev
        return best

    def list(self) -> List[Dict[str, Any]]:
        found: Dict[str, Dict[str, Any]] = {}
        if self.root.exists():
            for p in self.root.glob("*.json"):
                try:
                    t = json.loads(p.read_text(encoding="utf-8"))
                except ValueError:  # TOLERATED (R-853): ملف تالف لا يُسرد — load يكشفه صراحة
                    continue
                found[t.get("id", p.stem)] = t
        if self.remote is not None:
            try:
                rows = self.remote.list_blobs(DURABLE_NAMESPACE, limit=500) or []
            except Exception:  # TOLERATED (R-853): بلا مخزن = سرد محلي معلن
                rows = []
            for row in rows:
                t = (row or {}).get("payload")
                if isinstance(t, dict) and t.get("id"):
                    found[t["id"]] = _newest(found.get(t["id"]), t)
        return sorted(found.values(), key=lambda t: t.get("created_at") or "", reverse=True)


def _newest(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]):
    if a is None:
        return b
    if b is None:
        return a
    return b if int(b.get("rev", 0)) > int(a.get("rev", 0)) else a


_REF_FULL = re.compile(r"^\$steps\.(\d+)((?:\.[\w\-]+)*)$")
_REF_TPL = re.compile(r"\{\{steps\.(\d+)((?:\.[\w\-]+)*)\}\}")


def _ref_value(history: List[Dict[str, Any]], idx: int, path: str):
    if idx >= len(history):
        raise ValueError(f"مرجع لخطوة لم تنفذ بعد: steps.{idx}")
    cur: Any = history[idx]
    for part in [p for p in path.split(".") if p]:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            raise ValueError(f"مسار غير موجود: steps.{idx}{path}")
    return cur


def _resolve(value: Any, history: List[Dict[str, Any]]) -> Any:
    if isinstance(value, str):
        m = _REF_FULL.match(value)
        if m:
            return _ref_value(history, int(m.group(1)), m.group(2))
        return _REF_TPL.sub(lambda mm: str(_ref_value(history, int(mm.group(1)), mm.group(2))),
                            value)
    if isinstance(value, dict):
        return {k: _resolve(v, history) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, history) for v in value]
    return value


class ChainPlanner:
    """R-853: خطوات معلنة متسلسلة — كل خطوة قد تشير لنواتج ما قبلها. عديم الحالة
    (موضعه من السجل) فيستأنف من نقطة التفتيش كما هو. ينهي تلقائيًا بعد آخر خطوة."""

    kind = "chain"

    def __init__(self, steps: Iterable[Dict[str, Any]]):
        self._steps = list(steps)

    def next_step(self, goal: str, tools: List[Dict[str, Any]],
                  history: List[Dict[str, Any]]) -> Dict[str, Any]:
        from agent_loop import PlannerError
        i = len(history)
        if i >= len(self._steps):
            return {"action": "finish",
                    "answer": f"اكتملت {i} خطوات متسلسلة: " + " → ".join(
                        h.get("tool", "?") for h in history)}
        step = copy.deepcopy(self._steps[i])
        try:
            step["inputs"] = _resolve(step.get("inputs") or {}, history)
        except ValueError as exc:
            raise PlannerError(str(exc))
        return step


def validate_chain(steps: Any, tool_names: Iterable[str]) -> List[Dict[str, Any]]:
    """فحص مبكر عند الإنشاء: 1..16 خطوة call بأدوات مسجلة ومراجع لخطوات سابقة فقط."""
    if not isinstance(steps, list) or not 1 <= len(steps) <= CHAIN_MAX_STEPS:
        raise ValueError(f"الخطة قائمة من 1 إلى {CHAIN_MAX_STEPS} خطوة")
    names = set(tool_names)
    out = []
    for i, st in enumerate(steps):
        if not isinstance(st, dict) or not isinstance(st.get("tool"), str):
            raise ValueError(f"الخطوة {i}: يلزم tool")
        if st["tool"] not in names or st["tool"] in {"agent.run", "tasks.start", "tasks.resume"}:
            raise ValueError(f"الخطوة {i}: أداة غير مسموحة أو غير مسجلة: {st['tool']}")
        inputs = st.get("inputs") or {}
        if not isinstance(inputs, dict):
            raise ValueError(f"الخطوة {i}: inputs كائن")
        text = json.dumps(inputs, ensure_ascii=False)
        for m in re.finditer(r"steps\.(\d+)", text):
            if int(m.group(1)) >= i:
                raise ValueError(f"الخطوة {i}: مرجع لخطوة لاحقة steps.{m.group(1)}")
        step = {"action": "call", "tool": st["tool"], "inputs": inputs}
        if isinstance(st.get("check"), dict):
            step["check"] = st["check"]
        out.append(step)
    return out


def default_planner_factory(spec: Dict[str, Any]):
    from agent_loop import BrainPlanner, ScriptedPlanner
    kind = (spec or {}).get("kind")
    if kind == "scripted":
        return ScriptedPlanner(spec.get("steps") or [])
    if kind == "chain":
        return ChainPlanner(spec.get("steps") or [])
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
        self._active: Dict[str, Dict[str, Any]] = {}     # R-853: المهام الجارية هنا
        self._active_lock = threading.Lock()
        self._hb: Optional[threading.Thread] = None
        self.scanner: Dict[str, Any] = {"state": "idle", "resumed": []}

    def _inputs_of(self, tool: str) -> Dict[str, Any]:
        for t in self.registry.list_tools():
            if t["name"] == tool:
                return t.get("inputs") or {}
        return {}

    def create(self, goal: str, planner: Dict[str, Any], auto_resume: bool = False) -> str:
        if (planner or {}).get("kind") == "chain":
            planner = {**planner, "steps": validate_chain(
                planner.get("steps"), [t["name"] for t in self.registry.list_tools()])}
        self.planner_factory(planner)                   # يتحقق من صلاحية المواصفة مبكرًا
        tid = uuid.uuid4().hex[:16]
        self.store.save({"id": tid, "goal": goal, "planner": planner,
                         "status": "pending", "steps": [], "intents": {},
                         "created_at": _now(), "result": None, "runs": 0,
                         "auto_resume": bool(auto_resume), "lease": None, "boots": []})
        return tid

    def progress(self, task_id: str) -> Dict[str, Any]:
        """٣.٣: من القرص حرفيًا — المنجز فقط."""
        t = self.store.load(task_id)
        return {"task_id": t["id"], "goal": t["goal"], "status": t["status"],
                "done_steps": len(t["steps"]),
                "steps": [{"index": s.get("index"), "tool": s.get("tool"),
                           "ok": s.get("ok"), "verified": s.get("verified"),
                           "fingerprint": s.get("fingerprint"), "boot": s.get("boot"),
                           "at": s.get("at"), "inputs": s.get("inputs")} for s in t["steps"]],
                "pending_intents": sorted(t.get("intents", {}).keys(), key=int),
                "updated_at": t.get("updated_at"), "runs": t.get("runs", 0),
                "boots": t.get("boots", []), "lease": t.get("lease"),
                "planner": (t.get("planner") or {}).get("kind"),
                "answer": (t.get("result") or {}).get("answer"),
                "error": (t.get("result") or {}).get("error")}

    # ---------------------------------------------------------------- R-853
    def _lease_live(self, task: Dict[str, Any]) -> bool:
        """إيجار حي = لم ينته وقته، إلا إن كان صاحبه على هذا المضيف وعمليته ميتة
        (قتل محلي يُكتشف فورًا؛ مضيف آخر — نشر Render — ينتظر انتهاء الوقت)."""
        lease = task.get("lease") or {}
        if not lease or float(lease.get("until", 0)) <= time.time():
            return False
        if lease.get("host") == _HOST and lease.get("pid") and lease.get("boot") != BOOT_ID:
            try:
                os.kill(int(lease["pid"]), 0)
            except ProcessLookupError:
                return False
            except (PermissionError, OSError, ValueError):  # TOLERATED (R-853): لا يقين بالموت = حي
                return True
        return True

    def _save(self, task: Dict[str, Any]) -> None:
        if task.get("status") == "running":
            task["lease"] = {"boot": BOOT_ID, "until": time.time() + LEASE_S,
                             "host": _HOST, "pid": os.getpid()}
        self.store.save(task)

    def _heartbeat(self) -> None:
        while True:
            time.sleep(HEARTBEAT_S)
            with self._active_lock:
                live = list(self._active.values())
                if not live:
                    self._hb = None
                    return
            for task in live:
                try:
                    if task.get("status") == "running":
                        self._save(task)
                except Exception as exc:  # TOLERATED (R-853): النبض التالي يعيد؛ الخطوة نفسها تفشل صراحة
                    logger.warning("R-853: تعذر تجديد إيجار %s: %s", task.get("id"),
                                   type(exc).__name__)

    def start_async(self, task_id: str) -> Dict[str, Any]:
        """تشغيل في الخلفية — نتيجة فورية؛ التقدم عبر progress."""
        with self._active_lock:
            if task_id in self._active:
                return {"task_id": task_id, "started": False, "reason": "already_running"}
        t = threading.Thread(target=self._run_safe, args=(task_id,), daemon=True,
                             name=f"task-{task_id}")
        t.start()
        return {"task_id": task_id, "started": True, "boot": BOOT_ID}

    def _run_safe(self, task_id: str) -> None:
        try:
            self.run(task_id)
        except Exception as exc:  # TOLERATED (R-853): يُسجل؛ المهمة تبقى running فيستأنفها الماسح
            logger.error("R-853: توقف تشغيل المهمة %s: %s", task_id, type(exc).__name__)

    def resume_orphans(self) -> List[str]:
        """مهام running/pending ذاتية الاستئناف بإيجار منتهٍ وليست جارية هنا ⇒ تُستأنف."""
        started = []
        for t in self.store.list():
            if t.get("status") not in ("running", "pending") or not t.get("auto_resume"):
                continue
            if self._lease_live(t) or t.get("id") in self._active:
                continue
            if self.start_async(t["id"]).get("started"):
                started.append(t["id"])
        return started

    def boot_scan(self, window_s: float = BOOT_SCAN_WINDOW_S,
                  every_s: float = BOOT_SCAN_EVERY_S) -> None:
        """ماسح الإقلاع: يكرر المسح طوال النافذة ليلتقط إيجارات إقلاع سابق حين تنتهي."""
        self.scanner = {"state": "scanning", "resumed": [], "since": _now()}
        end = time.time() + window_s
        while True:
            try:
                self.scanner["resumed"] += self.resume_orphans()
            except Exception as exc:  # TOLERATED (R-853): مسح لاحق يعيد؛ الحالة تُعلن
                self.scanner["last_error"] = type(exc).__name__
            if time.time() >= end:
                break
            time.sleep(every_s)
        self.scanner["state"] = "done"


    def run(self, task_id: str) -> Dict[str, Any]:
        with self._active_lock:
            if task_id in self._active:
                return {"task_id": task_id, "status": "running", "already_running": True}
            self._active[task_id] = {"id": task_id, "status": "claiming"}
        try:
            return self._run(task_id)
        finally:
            with self._active_lock:
                self._active.pop(task_id, None)

    def _run(self, task_id: str) -> Dict[str, Any]:
        from agent_loop import AgentLoop
        task = self.store.load(task_id)
        if task["status"] == "running" and self._lease_live(task) \
                and (task.get("lease") or {}).get("boot") != BOOT_ID:
            return {"task_id": task_id, "status": "running", "leased_elsewhere": True,
                    "lease": task.get("lease")}
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
        task.setdefault("boots", []).append({"boot": BOOT_ID, "at": _now(),
                                             "from_step": len(task["steps"])})
        try:
            self._save(task)
        except DurableWriteError as exc:
            return {"task_id": task_id, "status": "checkpoint_failed", "resumed": resumed,
                    "error": f"لا تشغيل بلا نقطة تفتيش دائمة: {exc}"}
        with self._active_lock:
            self._active[task_id] = task
            if self._hb is None:
                self._hb = threading.Thread(target=self._heartbeat, daemon=True,
                                            name="tasks-heartbeat")
                self._hb.start()

        def before_invoke(idx: int, step: Dict[str, Any]) -> Dict[str, Any]:
            key = f"{task_id}:{idx}"
            extra = {}
            if IDEMPOTENCY_INPUT in self._inputs_of(step["tool"]):
                extra[IDEMPOTENCY_INPUT] = key
            task.setdefault("intents", {})[str(idx)] = {"tool": step["tool"], "key": key,
                                                         "at": _now(), "boot": BOOT_ID}
            self._save(task)                         # النية على القرص (والمخزن) قبل التنفيذ
            return extra

        def after_step(record: Dict[str, Any]) -> None:
            record["boot"], record["at"] = BOOT_ID, _now()
            task["steps"].append(record)
            task.get("intents", {}).pop(str(record["index"]), None)
            self._save(task)                         # نقطة تفتيش بعد الأثر الموقّع

        loop = AgentLoop(self.registry, self.planner_factory(task["planner"]),
                         max_steps=self.max_steps, caller=f"task:{task_id}")
        res = loop.run(task["goal"], run_id=task_id,
                       initial_steps=list(task["steps"]),
                       before_invoke=before_invoke, after_step=after_step)
        task["status"] = res["status"]
        task["result"] = {k: v for k, v in res.items() if k != "steps"}
        task["lease"] = None
        try:
            self._save(task)
        except DurableWriteError as exc:   # النتيجة محسوبة؛ تعذر حفظها يُعلن لا يُبتلع
            res = {**res, "durable_error": str(exc)}
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
        try:
            import skills_durable
            remote = skills_durable.make_store()     # R-853: مرآة دائمة إن وُجد مخزن
        except Exception:  # TOLERATED (R-853): بلا مخزن = قرص محلي فقط (يُعلن في الحالة)
            remote = None
        _RUNNER = DurableRunner(TaskStore(root, remote=remote), get_registry(),
                                external_tools=external)
    return _RUNNER


def auto_resume_enabled() -> bool:
    """مفعّل افتراضيًا؛ ``SOVEREIGN_TASKS_AUTO_RESUME=0`` يعطله، ومعطل تحت pytest."""
    flag = os.environ.get("SOVEREIGN_TASKS_AUTO_RESUME", "")
    if flag == "1":
        return True
    return flag != "0" and "pytest" not in sys.modules


def start_boot_scanner() -> Dict[str, Any]:
    if not auto_resume_enabled():
        get_runner().scanner = {"state": "disabled", "resumed": []}
        return {"started": False}
    threading.Thread(target=get_runner().boot_scan, daemon=True, name="tasks-boot-scan").start()
    return {"started": True, "boot": BOOT_ID}


def status() -> Dict[str, Any]:
    r = get_runner()
    with r._active_lock:
        active = sorted(k for k, v in r._active.items() if v.get("status") == "running")
    remote = r.store.remote
    return {"boot": BOOT_ID, "active": active, "scanner": r.scanner,
            "auto_resume": auto_resume_enabled(), "lease_s": LEASE_S,
            "heartbeat_s": HEARTBEAT_S,
            "durable": ({"backend": type(remote).__name__} if remote is not None else None)}
