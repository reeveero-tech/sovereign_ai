# -*- coding: utf-8 -*-
"""R-758 (ROADMAP_V5 §٥: ٥.١ + ٥.٢ + ٥.٣): أسطول الوكلاء.

- ٥.١ `Worker`: عامل = حلقة R-753 بدور واحد وهدف جزئي وميزانية خطوات خاصة؛
  يُنشأ ويُوقف ويسلم نتيجته بأثر `fleet_event` (spawn/stop/result). تعذر أثر
  الإنشاء = لا تشغيل (ledger_blocked).
- ٥.٢ `FleetCoordinator`: توزيع الأجزاء على مجمع خيوط بسقف تزامن، تجميع النتائج،
  عزل الفاشل (استثناء عامل لا يمس غيره)، إعادة جدولة الفاشل حتى `max_retries`،
  وتقرير يذكر الفشل صادقًا (status=partial لا completed).
- ٥.٣ `measure_scale`: تشغيل فعلي بعبء حقيقي (كل عامل يستدعي أداة تنتظر I/O)
  يعلن: المسجل / القابل للتشغيل (سقف التزامن) / **المتزامن فعلًا** (ذروة عداد حي
  يُقاس داخل التنفيذ لا يُحسب)، الزمن، ذروة الذاكرة RSS المقيسة بأخذ عينات،
  الأعطال، وموارد البيئة المعلنة.

حدود صادقة: العمال خيوط في عملية واحدة — مناسبة لعبء I/O (استدعاء أدوات/شبكة)
لا لعبء حسابي ثقيل (GIL). القياس في هذه البيئة لا يثبت شيئًا عن آلة Fly
(512MB) — ذلك يتطلب النشر (١.٧). كل عامل حي يتطلب العقل (١.٦) للتخطيط.
"""

from __future__ import annotations

import json
import math
import os
import platform
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional


def _trace(op: str, payload: Dict[str, Any]) -> None:
    from memory.core import get_core
    get_core().append_event("fleet_event", {"op": op, **payload},
                            user=payload.get("role"))


class _Gauge:
    """عداد تزامن حي — الذروة تُقاس من التنفيذ الفعلي."""

    def __init__(self):
        self._lock = threading.Lock()
        self.now = 0
        self.peak = 0

    def enter(self):
        with self._lock:
            self.now += 1
            self.peak = max(self.peak, self.now)

    def leave(self):
        with self._lock:
            self.now -= 1


class Worker:
    def __init__(self, role: str, goal: str, planner: Dict[str, Any], registry, *,
                 max_steps: int = 8, max_seconds: float = 120.0,
                 gauge: Optional[_Gauge] = None, attempt: int = 1):
        from agent_loop import CancelToken
        self.role, self.goal, self.planner_spec = role, goal, planner
        self.registry = registry
        self.max_steps, self.max_seconds = max_steps, max_seconds
        self.cancel = CancelToken()
        self.gauge = gauge
        self.attempt = attempt
        self.result: Optional[Dict[str, Any]] = None

    def stop(self, by: str = "owner") -> None:
        self.cancel.cancel(by=by)
        try:
            _trace("worker.stop", {"role": self.role, "by": by})
        except Exception:  # TOLERATED: الإيقاف نافذ دائمًا (الإلغاء أمان) — غياب الأثر يُعلن في النتيجة
            self.cancel.by = f"{by} (بلا أثر — السجل لا يوقّع)"

    def run(self) -> Dict[str, Any]:
        from agent_loop import AgentLoop
        from durable_tasks import default_planner_factory
        try:
            _trace("worker.spawn", {"role": self.role, "goal": self.goal[:200],
                                    "attempt": self.attempt, "budget_steps": self.max_steps})
        except Exception as exc:
            self.result = {"status": "ledger_blocked", "role": self.role, "answer": None,
                           "error": f"تعذر أثر الإنشاء — لا تشغيل: {type(exc).__name__}"}
            return self.result
        if self.gauge:
            self.gauge.enter()
        try:
            loop = AgentLoop(self.registry, default_planner_factory(self.planner_spec),
                             max_steps=self.max_steps, max_seconds=self.max_seconds,
                             cancel=self.cancel, caller=f"worker:{self.role}")
            res = loop.run(self.goal)
        except Exception as exc:  # عزل: عامل ينهار لا يُسقط الأسطول
            res = {"status": "crashed", "answer": None, "steps": [],
                   "error": f"{type(exc).__name__}: {str(exc)[:160]}"}
        finally:
            if self.gauge:
                self.gauge.leave()
        self.result = {"role": self.role, "status": res["status"], "answer": res.get("answer"),
                       "error": res.get("error"), "steps": len(res.get("steps") or []),
                       "attempt": self.attempt}
        try:
            _trace("worker.result", {"role": self.role, "status": res["status"],
                                     "attempt": self.attempt})
        except Exception:  # TOLERATED: النتيجة وقعت بأثر خطواتها؛ غياب أثر التسليم يُعلن
            self.result["trace_warning"] = "تعذر أثر التسليم"
        return self.result


class FleetCoordinator:
    def __init__(self, registry, *, max_concurrency: int = 8, max_retries: int = 1,
                 worker_max_steps: int = 8):
        if max_concurrency < 1:
            raise ValueError("سقف التزامن ≥ 1")
        self.registry = registry
        self.max_concurrency = int(max_concurrency)
        self.max_retries = int(max_retries)
        self.worker_max_steps = worker_max_steps
        self.gauge = _Gauge()
        self.workers: Dict[str, Worker] = {}
        self._lock = threading.Lock()

    def stop_all(self, by: str = "owner") -> None:
        with self._lock:
            ws = list(self.workers.values())
        for w in ws:
            w.stop(by=by)

    def _run_part(self, part: Dict[str, Any]) -> Dict[str, Any]:
        attempts, last = 0, None
        while attempts <= self.max_retries:
            attempts += 1
            w = Worker(part["role"], part["goal"], part["planner"], self.registry,
                       max_steps=self.worker_max_steps, gauge=self.gauge, attempt=attempts)
            with self._lock:
                self.workers[part["role"]] = w
            last = w.run()
            if last["status"] in ("completed", "ledger_blocked", "cancelled"):
                break                                   # لا إعادة لما لا تصلحه الإعادة
        last = dict(last)
        last["attempts"] = attempts
        return last

    def run(self, parts: List[Dict[str, Any]]) -> Dict[str, Any]:
        roles = [p["role"] for p in parts]
        if len(set(roles)) != len(roles):
            raise ValueError("أدوار مكررة في الأسطول")
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=self.max_concurrency,
                                thread_name_prefix="fleet") as pool:
            results = list(pool.map(self._run_part, parts))
        done = [r for r in results if r["status"] == "completed"]
        blocked = [r for r in results if r["status"] == "ledger_blocked"]
        failed = [{"role": r["role"], "status": r["status"], "error": r.get("error"),
                   "attempts": r["attempts"]} for r in results if r["status"] != "completed"]
        if len(blocked) == len(results) and results:
            status = "blocked"
        elif len(done) == len(results):
            status = "completed"
        elif done:
            status = "partial"
        else:
            status = "failed"
        return {"status": status, "registered": len(parts),
                "runnable_concurrency_cap": self.max_concurrency,
                "measured_peak_concurrency": self.gauge.peak,
                "waves_min": math.ceil(len(parts) / self.max_concurrency) if parts else 0,
                "completed": len(done), "failed": failed,
                "retried": {r["role"]: r["attempts"] - 1 for r in results if r["attempts"] > 1},
                "results": results, "wall_s": round(time.perf_counter() - start, 3)}


# ---------------------------------------------------------------- ٥.٣ القياس
def _rss_mb() -> float:
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:  # TOLERATED: منصة بلا /proc — يُعلن -1 (غير مقيس) لا رقم مختلق
        return -1.0
    return -1.0


def _mem_total_mb() -> float:
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:  # TOLERATED: منصة بلا /proc — يُعلن -1 (غير مقيس)
        return -1.0
    return -1.0


def _default_scale_registry():
    from tool_registry import ToolRegistry, ToolSpec
    r = ToolRegistry()

    def work(n, ms=20):
        time.sleep(int(ms) / 1000.0)
        return {"n": int(n), "sq": int(n) * int(n)}
    r.register(ToolSpec(name="work", description="عبء I/O مقيس", inputs={"n": "", "ms": ""},
                        outputs="n/sq", handler=work))
    return r


def measure_scale(n: int, *, max_concurrency: int, work_ms: int = 20,
                  registry=None) -> Dict[str, Any]:
    reg = registry or _default_scale_registry()
    parts = [{"role": f"w{i}", "goal": f"جزء {i}", "planner": {"kind": "scripted", "steps": [
        {"action": "call", "tool": "work", "inputs": {"n": i, "ms": work_ms},
         "check": {"type": "key_equals", "key": "n", "value": i}},
        {"action": "finish", "answer": i}]}} for i in range(n)]
    rss_base = _rss_mb()
    peak = {"rss": rss_base}
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            peak["rss"] = max(peak["rss"], _rss_mb())
            stop.wait(0.02)
    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    try:
        rep = FleetCoordinator(reg, max_concurrency=max_concurrency, max_retries=1).run(parts)
    finally:
        stop.set()
        th.join(1)
    wall = rep["wall_s"] or 1e-9
    return {"registered": rep["registered"],
            "runnable_concurrency_cap": rep["runnable_concurrency_cap"],
            "measured_peak_concurrency": rep["measured_peak_concurrency"],
            "completed": rep["completed"], "failures": rep["failed"],
            "status": rep["status"], "wall_s": rep["wall_s"],
            "throughput_per_s": round(rep["completed"] / wall, 2),
            "work_ms_per_worker": work_ms,
            "rss_mb_base": round(rss_base, 1), "rss_mb_peak": round(peak["rss"], 1),
            "cpu_count": os.cpu_count(), "mem_total_mb": round(_mem_total_mb(), 1),
            "environment": {"python": platform.python_version(),
                            "platform": platform.platform(),
                            "note": "بيئة العمل (sandbox) — ليست آلة Fly 512MB؛ قياس Fly يتطلب ١.٧"}}


def parse_goals(goals: Any) -> List[str]:
    """R-766: أهداف `fleet.spawn` — قائمة، أو نص قائمة JSON، أو نص بأسطر.

    مدخلات `/tools/invoke` نصوص (`Dict[str, str]`)، و`list(نص)` كان يفكك الهدف إلى حروف
    فيصير كل حرف عاملًا. نص بلا أسطر = هدف واحد. الفارغ يُسقط.
    """
    if isinstance(goals, str):
        text = goals.strip()
        items: Any = None
        if text.startswith("["):
            try:
                items = json.loads(text)
            except ValueError:
                items = None
        if not isinstance(items, list):
            items = text.splitlines()
    else:
        items = list(goals)
    return [str(g).strip() for g in items if str(g).strip()]


def spawn_goals(goals: Any, max_concurrency: int = 4) -> Dict[str, Any]:
    """مدخل أداة fleet.spawn: عمال بالعقل الحي فوق السجل العام."""
    from tool_registry import get_registry
    goals = parse_goals(goals)
    cap = max(1, min(int(max_concurrency), int(os.environ.get("FLEET_MAX_CONCURRENCY", "8"))))
    parts = [{"role": f"w{i}", "goal": g, "planner": {"kind": "brain"}}
             for i, g in enumerate(goals[:1000])]
    return FleetCoordinator(get_registry(), max_concurrency=cap).run(parts)
