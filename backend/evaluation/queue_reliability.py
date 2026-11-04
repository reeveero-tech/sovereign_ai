# -*- coding: utf-8 -*-
"""R-844: مجموعة موثوقية الطابور — انقطاع، تزامن، عدم تكرار، سياج، ضغط خلفي.

كل سيناريو يشغّل الطابور الحقيقي (SQLite) فوق المنسق ومنفذ R-840 الحقيقيين
(sandbox_env)، والشبكة وحدها مزيفة. الانقطاع يُحاكى باستثناء ``BaseException``
يقتل الاستدعاء بعد وصول الكتابة إلى الطرف البعيد. هذا الاستثناء لا يلتقطه
أي ``except Exception``، تمامًا كموت العملية. بعده «إعادة تشغيل» تعني منسقًا
جديدًا على القرص نفسه، تضيع معه ذاكرة عدم التكرار في المنفذ.

التوقعات في ``data/queue_cases.json`` مكتوبة من القاعدة قبل التشغيل، ومجمّدة
ببصمة في suites.py، فلا تُرخى لاحقًا.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List

from . import sandbox_env

try:
    from agent_orchestrator import runtime as orch_runtime
    from job_queue import kinds as qkinds
    from job_queue.store import IdempotencyConflict, JobStore, QueueFull
    from job_queue.worker import Worker
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.agent_orchestrator import runtime as orch_runtime
    from backend.job_queue import kinds as qkinds
    from backend.job_queue.store import IdempotencyConflict, JobStore, QueueFull
    from backend.job_queue.worker import Worker

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
READ = {"utterance": "حلل مستودع github.com/acme/webapp",
        "permissions": ["orchestrator:write"], "session_id": "q-read"}


def _write(title: str, session: str) -> Dict[str, Any]:
    return {"utterance": f"افتح مشكلة بعنوان {title} في github.com/acme/webapp",
            "permissions": ["orchestrator:write"], "session_id": session}


class Crash(BaseException):
    """موت العملية — لا يلتقطه except Exception."""


class _Transport(sandbox_env.Transport):
    def __init__(self):
        super().__init__(200)
        self.crash_on: set = set()   # {"POST"} أو {"GET"}
        self.crash_once = True

    def __call__(self, method, url, **kw):
        m = str(method).upper()
        self.calls.append({"method": m, "url": url,
                           "headers": dict(kw.get("headers") or {})})
        if m in self.crash_on:
            if self.crash_once:
                self.crash_on = set()
            raise Crash(f"انقطاع بعد {m}")
        return sandbox_env._Response(self.status_code, {"number": 7})


class Env:
    def __init__(self, tmp: Path, max_depth: int = 100):
        self.now = [1_000_000.0]
        self.t = _Transport()
        self.o, _ = sandbox_env.build(tmp, transport=self.t)
        self.store = JobStore(str(tmp / "q.sqlite3"), max_depth=max_depth,
                              clock=lambda: self.now[0])
        self.registry = dict(qkinds.KINDS)

    def worker(self, wid: str = "w1") -> Worker:
        return Worker(self.store, self.registry, wid, orchestrator=lambda: self.o)

    def enqueue(self, kind: str, payload: Dict[str, Any], key: str):
        k = self.registry[kind]
        return self.store.enqueue(kind, payload, key, "owner", k.max_attempts,
                                  k.timeout_s(payload))

    def restart(self) -> None:
        """عملية جديدة: منسق جديد على القرص نفسه، وذاكرة المنفذ فارغة."""
        ex = self.o._conn_executor
        ex._idempotency = {}
        self.o = orch_runtime.OrchestratorSystem(
            data_dir=self.o.data_dir, connector_executor=ex,
            org_policy=self.o.policy.org_policy, connector_registry=ex.registry)

    def advance(self, s: float) -> None:
        self.now[0] += s

    def writes(self) -> int:
        return sum(1 for c in self.t.calls if c["method"] in WRITE_METHODS)

    def calls(self) -> int:
        return len(self.t.calls)


def _approve_job(env: Env, job_id: str, key: str):
    res = env.store.get(job_id)["result"]
    return env.enqueue("orchestrator.approval", {
        "loop_id": res["loop_id"], "approval_id": res["pending_approval"]["approval_id"],
        "decision": "approved", "approved_by": "owner"}, key)


# ===================================================================== السيناريوهات
def s_idempotent_enqueue(env: Env) -> Dict[str, Any]:
    j1, c1 = env.enqueue("orchestrator.loop", READ, "k-1")
    j2, c2 = env.enqueue("orchestrator.loop", READ, "k-1")
    return {"same_job": j1["id"] == j2["id"], "created": [c1, c2],
            "jobs": len(env.store.list())}


def s_key_reuse_conflict(env: Env) -> Dict[str, Any]:
    env.enqueue("orchestrator.loop", READ, "k-1")
    try:
        env.enqueue("orchestrator.loop", _write("أخرى", "q"), "k-1")
        return {"conflict": False}
    except IdempotencyConflict:
        return {"conflict": True, "jobs": len(env.store.list())}


def s_backpressure(env: Env) -> Dict[str, Any]:
    accepted = 0
    for i in range(env.store.max_depth + 2):
        try:
            env.enqueue("orchestrator.loop", dict(READ, session_id=f"bp{i}"), f"bp-{i}")
            accepted += 1
        except QueueFull:
            return {"accepted": accepted, "rejected_at": i + 1}
    return {"accepted": accepted, "rejected_at": None}


def s_read_completes(env: Env) -> Dict[str, Any]:
    j, _ = env.enqueue("orchestrator.loop", READ, "r-1")
    env.worker().run_once()
    j = env.store.get(j["id"])
    return {"job": j["status"], "loop": j["result"]["loop_status"],
            "calls": env.calls(), "writes": env.writes(), "attempts": j["attempts"]}


def s_write_waits_for_human(env: Env) -> Dict[str, Any]:
    j, _ = env.enqueue("orchestrator.loop", _write("انتظار", "q-w"), "w-1")
    env.worker().run_once()
    j = env.store.get(j["id"])
    return {"job": j["status"], "loop": j["result"]["loop_status"],
            "writes": env.writes(), "has_approval": bool(j["result"]["pending_approval"])}


def s_approval_once(env: Env) -> Dict[str, Any]:
    j, _ = env.enqueue("orchestrator.loop", _write("مرة", "q-a"), "a-1")
    env.worker().run_once()
    a1, _ = _approve_job(env, j["id"], "ap-1")
    a2, created2 = _approve_job(env, j["id"], "ap-1")   # إعادة إرسال الموافقة
    env.worker().drain(5)
    a1 = env.store.get(a1["id"])
    return {"approval_job": a1["status"], "loop": a1["result"]["loop_status"],
            "dedup": (a1["id"] == a2["id"]) and not created2, "writes": env.writes()}


def s_crash_mid_write(env: Env) -> Dict[str, Any]:
    j, _ = env.enqueue("orchestrator.loop", _write("انقطاع", "q-c"), "c-1")
    env.worker().run_once()
    a, _ = _approve_job(env, j["id"], "c-ap")
    env.t.crash_on = {"POST"}
    try:
        env.worker("w1").run_once()
    except Crash:  # TOLERATED: محاكاة موت العملية — الأثر يُقاس بعد «إعادة التشغيل»
        pass
    mid = env.store.get(a["id"])["status"]
    env.restart()
    env.advance(10_000)            # انتهى الإيجار: العامل مات
    env.worker("w2").run_once()
    a = env.store.get(a["id"])
    return {"after_crash": mid, "job": a["status"], "loop": a["result"]["loop_status"],
            "writes": env.writes(), "attempts": a["attempts"]}


def s_crash_mid_read(env: Env) -> Dict[str, Any]:
    j, _ = env.enqueue("orchestrator.loop", READ, "cr-1")
    env.t.crash_on = {"GET"}
    try:
        env.worker("w1").run_once()
    except Crash:  # TOLERATED: محاكاة موت العملية — الأثر يُقاس بعد «إعادة التشغيل»
        pass
    env.restart()
    env.advance(10_000)
    env.worker("w2").run_once()
    j = env.store.get(j["id"])
    return {"job": j["status"], "loop": j["result"]["loop_status"], "attempts": j["attempts"],
            "writes": env.writes()}


def s_cross_loop_isolation(env: Env) -> Dict[str, Any]:
    ja, _ = env.enqueue("orchestrator.loop", _write("أ", "q-xa"), "xa")
    jb, _ = env.enqueue("orchestrator.loop", _write("ب", "q-xb"), "xb")
    env.worker().drain(5)
    _approve_job(env, ja["id"], "xa-ap")     # موافقة A وحدها
    env.worker().drain(5)
    loop_b = env.store.get(jb["id"])["result"]["loop_id"]
    env.o.run(loop_b)                         # عامل آخر يستأنف B
    return {"b_loop": env.o.get(loop_b)["status"], "writes": env.writes()}


def s_fencing(env: Env) -> Dict[str, Any]:
    # نوع بثلاث محاولات: نوع بمحاولة واحدة يذهب dead عند انتهاء الإيجار (صحيح)
    j, _ = env.enqueue("orchestrator.loop", READ, "f-1")
    old = env.store.claim("w-old")
    env.advance(10_000)
    env.store.recover()
    new = env.store.claim("w-new")
    stale_ok = env.store.finish(j["id"], "w-old", old["fence"], "succeeded", {"by": "old"})
    new_ok = env.store.finish(j["id"], "w-new", new["fence"], "succeeded", {"by": "new"})
    j = env.store.get(j["id"])
    return {"stale_accepted": stale_ok, "fresh_accepted": new_ok, "result_by": j["result"]["by"],
            "stale_logged": any(e["event"] == "stale_finish_rejected"
                                for e in env.store.events(j["id"]))}


def s_retry_policy(env: Env) -> Dict[str, Any]:
    n = {"flaky": 0}

    def flaky(ctx):
        n["flaky"] += 1
        if n["flaky"] < 3:
            raise ConnectionError("انقطاع عابر")
        return qkinds.Outcome("succeeded", {"ok": True})

    def broken(ctx):
        raise ValueError("خطأ منطقي")

    env.registry["test.flaky"] = qkinds.JobKind(
        "test.flaky", "عابر ثم ينجح", "low", "اختبار", {"type": "object"},
        lambda p: 30.0, 3, (ConnectionError,), flaky)
    env.registry["test.broken"] = qkinds.JobKind(
        "test.broken", "خطأ غير عابر", "low", "اختبار", {"type": "object"},
        lambda p: 30.0, 3, (ConnectionError,), broken)
    jf, _ = env.enqueue("test.flaky", {}, "fl")
    jb, _ = env.enqueue("test.broken", {}, "br")
    w = env.worker()
    for _ in range(6):
        w.run_once()
        env.advance(400)            # تجاوز التأخير الأسي
    jf, jb = env.store.get(jf["id"]), env.store.get(jb["id"])
    return {"flaky": jf["status"], "flaky_attempts": jf["attempts"],
            "broken": jb["status"], "broken_attempts": jb["attempts"]}


def s_no_retry_on_401(env: Env) -> Dict[str, Any]:
    env.t.status_code = 401
    j, _ = env.enqueue("orchestrator.loop", READ, "u-1")
    w = env.worker()
    w.run_once()
    env.advance(400)
    w.run_once()
    j = env.store.get(j["id"])
    return {"job": j["status"], "attempts": j["attempts"], "loop": j["result"]["loop_status"]}


def s_cancel_queued(env: Env) -> Dict[str, Any]:
    j, _ = env.enqueue("orchestrator.loop", READ, "x-1")
    env.store.cancel(j["id"], "owner")
    env.worker().drain(5)
    return {"job": env.store.get(j["id"])["status"], "calls": env.calls()}


def s_restart_pending_approval(env: Env) -> Dict[str, Any]:
    j, _ = env.enqueue("orchestrator.loop", _write("بعد الإقلاع", "q-r"), "rp-1")
    env.worker().run_once()
    env.restart()                     # موافقة معلقة ثم إعادة تشغيل
    a, _ = _approve_job(env, j["id"], "rp-ap")
    env.worker().run_once()
    a = env.store.get(a["id"])
    return {"approval_job": a["status"], "loop": (a["result"] or {}).get("loop_status"),
            "writes": env.writes()}


SCENARIOS: Dict[str, Callable[[Env], Dict[str, Any]]] = {
    f.__name__[2:]: f for f in (
        s_idempotent_enqueue, s_key_reuse_conflict, s_backpressure, s_read_completes,
        s_write_waits_for_human, s_approval_once, s_crash_mid_write, s_crash_mid_read,
        s_cross_loop_isolation, s_fencing, s_retry_policy, s_no_retry_on_401,
        s_cancel_queued, s_restart_pending_approval)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r844-q-"))
    try:
        env = Env(tmp, max_depth=int(case.get("max_depth", 100)))
        try:
            got = SCENARIOS[case["scenario"]](env)
        except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
            got = {"error": f"{type(exc).__name__}: {exc}"}
        exp = case["expect"]
        failed = [{"check": k, "want": v, "got": got.get(k)}
                  for k, v in exp.items() if got.get(k) != v]
        return {"id": case["id"], "rule": case["rule"], "pass": not failed,
                "got": got, "failed_checks": failed}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [run_case(c) for c in cases]
    passed = sum(r["pass"] for r in results)
    return {"score": round(passed / len(results), 4) if results else 0.0,
            "passed": passed, "n": len(results),
            "failures": [r for r in results if not r["pass"]]}
