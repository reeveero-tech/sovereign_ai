# -*- coding: utf-8 -*-
"""R-853: مجموعة مجمّدة tasks.resume — مهام متعددة الخطوات تستأنف بعد القتل (٦.٢.٤).

كل سيناريو معزول: مجلد مؤقت، سجل أدوات جديد بأدوات عدّ/انتظار، سجل سيادي مزيف
(عقد append_event)، ومخزن دائم مزيف على ملفات (يحاكي SupabaseDisk ويُشارك بين
العمليات). سيناريو ``real_process_kill`` يقتل عملية فرعية بـSIGKILL في منتصف
المهمة ثم يستأنفها إقلاع جديد بقرص محلي فارغ — قتل حقيقي لا محاكاة.
التوقعات في data/tasks_resume_cases.json مكتوبة قبل أول تشغيل ومجمّدة ببصمة.
"""
from __future__ import annotations

import json
import re
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

import durable_tasks as D  # noqa: E402
from tool_registry import ToolRegistry, ToolSpec  # noqa: E402


class Killed(BaseException):
    """قتل محاكى داخل العملية — يعبر الحلقة كما يعبرها SIGKILL (لا يُلتقط كـException)."""


class FakeCore:
    def append_event(self, *a, **k):
        return {"hash": "0" * 64}


class DirStore:
    """مخزن دائم على ملفات (مشترك بين عمليات) بعقد SupabaseDisk."""

    def __init__(self, root: Path, fail: bool = False):
        self.root = Path(root)
        self.fail = fail
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, ns, key):
        return self.root / f"{ns}__{key}.json"

    def save_blob(self, ns, key, payload):
        if self.fail:
            return False
        tmp = self._p(ns, key).with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._p(ns, key))
        return True

    def load_blob(self, ns, key):
        p = self._p(ns, key)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def list_blobs(self, ns, limit=1000, offset=0):
        return [{"key": p.stem.split("__", 1)[1],
                 "payload": json.loads(p.read_text(encoding="utf-8"))}
                for p in sorted(self.root.glob(f"{ns}__*.json"))]


def make_registry(calls_file: Path, kill_on: str = "") -> ToolRegistry:
    reg = ToolRegistry()

    def count(tag="", n=""):
        with open(calls_file, "a", encoding="utf-8") as fh:
            fh.write(f"{tag}\n")
        if kill_on and tag == kill_on:
            raise Killed()
        return {"tag": tag, "n": n, "len": len(str(tag))}

    def wait(seconds="1"):
        time.sleep(float(seconds))
        return {"waited_s": float(seconds)}

    def send(message="", **_):
        with open(calls_file, "a", encoding="utf-8") as fh:
            fh.write(f"send:{message}\n")
        if kill_on == "send":
            raise Killed()
        return {"sent": True}

    reg.register(ToolSpec(name="t.count", description="عدّ", inputs={"tag": "t", "n": "n"},
                          outputs="tag", handler=count))
    reg.register(ToolSpec(name="t.wait", description="انتظار", inputs={"seconds": "s"},
                          outputs="waited_s", handler=wait))
    reg.register(ToolSpec(name="ext.send", description="فعل خارجي بلا مفتاح",
                          inputs={"message": "m"}, outputs="sent", handler=send))
    return reg


def calls(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


class Env:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.remote = DirStore(tmp / "remote")
        self.calls = tmp / "calls.txt"

    def runner(self, local: str = "diskA", kill_on: str = "", remote=None, external=()):
        return D.DurableRunner(D.TaskStore(self.tmp / local,
                                           remote=self.remote if remote is None else remote),
                               make_registry(self.calls, kill_on), external_tools=external)


CHAIN = [{"tool": "t.count", "inputs": {"tag": "a"}},
         {"tool": "t.count", "inputs": {"tag": "$steps.0.result.tag", "n": "{{steps.0.result.len}}"}},
         {"tool": "t.count", "inputs": {"tag": "c"}}]


def _chain_planner(steps=None):
    return {"kind": "chain", "steps": steps or CHAIN}


def _new_boot(monkey: Dict[str, Any], boot: str) -> None:
    monkey.setdefault("BOOT_ID", D.BOOT_ID)
    D.BOOT_ID = boot


def _child_rc(proc) -> int:
    """رمز نتيجة الابن من سطر CHILD_RC (لا نعتمد رمز الخروج — R-686)."""
    m = re.search(r"CHILD_RC=(\d+)", proc.stdout or "")
    return int(m.group(1)) if (m and proc.returncode == 0) else -1


def _kill_mid(env: Env, kill_tag: str = "c", steps=None, external=()):
    r = env.runner(kill_on=kill_tag, external=external)
    tid = r.create("goal", _chain_planner(steps), auto_resume=True)
    try:
        r.run(tid)
    except Killed:  # TOLERATED (R-853): القتل المحاكى هو المقصود
        pass
    return tid


# ------------------------------------------------------------------ السيناريوهات
def s_chain_resolves(env, m):
    r = env.runner()
    tid = r.create("goal", _chain_planner())
    res = r.run(tid)
    t = r.store.load(tid)
    return {"status": res["status"], "steps": len(t["steps"]),
            "step1_inputs": t["steps"][1]["inputs"], "calls": calls(env.calls)}


def s_validation_rejects(env, m):
    r = env.runner()
    bad = {"future_ref": [{"tool": "t.count", "inputs": {"tag": "$steps.1.result.tag"}},
                          {"tool": "t.count", "inputs": {}}],
           "unknown_tool": [{"tool": "nope.tool", "inputs": {}}],
           "forbidden": [{"tool": "agent.run", "inputs": {}}],
           "empty": [],
           "too_long": [{"tool": "t.count", "inputs": {}}] * 17,
           "inputs_not_object": [{"tool": "t.count", "inputs": ["x"]}]}
    out = {}
    for name, steps in bad.items():
        try:
            r.create("g", {"kind": "chain", "steps": steps})
            out[name] = "accepted"
        except ValueError:
            out[name] = "rejected"
    return {"results": out, "remote_tasks": len(env.remote.list_blobs("tasks"))}


def s_missing_path_honest(env, m):
    r = env.runner()
    tid = r.create("g", _chain_planner([{"tool": "t.count", "inputs": {"tag": "a"}},
                                        {"tool": "t.count",
                                         "inputs": {"tag": "$steps.0.result.nothing"}}]))
    res = r.run(tid)
    return {"status": res["status"], "calls": calls(env.calls)}


def s_fresh_disk_restores(env, m):
    tid = _kill_mid(env)
    _new_boot(m, "bootB")
    fresh = env.runner(local="diskB")
    p = fresh.progress(tid)
    return {"status": p["status"], "done_steps": p["done_steps"],
            "pending_intents": p["pending_intents"], "local_cached": (env.tmp / "diskB" / f"{tid}.json").exists()}


def s_resume_after_kill(env, m):
    tid = _kill_mid(env)
    _new_boot(m, "bootB")
    fresh = env.runner(local="diskB")
    t = fresh.store.load(tid)
    t["lease"]["until"] = 0  # الإيجار انتهى (العملية ماتت ولا نبض)
    fresh.store._save_local(t)
    res = fresh.run(tid)
    p = fresh.progress(tid)
    return {"status": res["status"], "resumed": res["resumed"], "runs": p["runs"],
            "calls": calls(env.calls),
            "step_boots": [s["boot"] if s["boot"] == "bootB" else "old" for s in p["steps"]],
            "pending_intents": p["pending_intents"]}


def s_concurrent_single_execution(env, m):
    r = env.runner()
    tid = r.create("g", _chain_planner([{"tool": "t.wait", "inputs": {"seconds": "0.3"}},
                                        {"tool": "t.count", "inputs": {"tag": "x"}}]))
    outs: List[Dict[str, Any]] = []
    th = [threading.Thread(target=lambda: outs.append(r.run(tid))) for _ in range(3)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    return {"calls": calls(env.calls),
            "already_running": sum(1 for o in outs if o.get("already_running")),
            "completed": sum(1 for o in outs if o.get("status") == "completed")}


def s_live_lease_elsewhere(env, m):
    tid = _kill_mid(env)
    _new_boot(m, "bootB")
    fresh = env.runner(local="diskB")
    res = fresh.run(tid)       # إيجار bootA ما زال حيًا (لم يمض LEASE_S)
    started = fresh.resume_orphans()
    return {"leased_elsewhere": res.get("leased_elsewhere"), "orphans_started": started,
            "calls": calls(env.calls)}


def s_scanner_resumes_orphan(env, m):
    tid = _kill_mid(env)
    _new_boot(m, "bootB")
    fresh = env.runner(local="diskB")
    t = fresh.store.load(tid)
    t["lease"]["until"] = 0
    env.remote.save_blob("tasks", tid, {**t, "rev": t["rev"] + 1})
    fresh.boot_scan(window_s=0, every_s=0)
    deadline = time.time() + 10
    while time.time() < deadline and fresh.progress(tid)["status"] == "running":
        time.sleep(0.05)
    time.sleep(0.1)
    return {"scanner_resumed": fresh.scanner["resumed"] == [tid],
            "status": fresh.progress(tid)["status"], "calls": calls(env.calls)}


def s_scanner_skips_non_auto_and_terminal(env, m):
    r = env.runner(kill_on="c")
    manual = r.create("g", _chain_planner())
    try:
        r.run(manual)
    except Killed:  # TOLERATED (R-853): القتل المحاكى هو المقصود
        pass
    done = r.create("g", _chain_planner([{"tool": "t.count", "inputs": {"tag": "z"}}]),
                    auto_resume=True)
    r.run(done)
    _new_boot(m, "bootB")
    fresh = env.runner(local="diskB")
    for tid in (manual,):
        t = fresh.store.load(tid)
        t["lease"]["until"] = 0
        fresh.store._save_local(t)
        env.remote.save_blob("tasks", tid, {**t, "rev": t["rev"] + 1})
    return {"started": fresh.resume_orphans(), "manual_status": fresh.progress(manual)["status"],
            "done_status": fresh.progress(done)["status"]}


def s_push_failure_fail_closed(env, m):
    remote = DirStore(env.tmp / "remote2")
    r = env.runner(remote=remote)
    tid = r.create("g", _chain_planner())
    remote.fail = True
    res = r.run(tid)
    return {"status": res.get("status"), "calls": calls(env.calls)}


def s_secret_never_pushed(env, m):
    r = env.runner()
    fake = "ghp_" + "Z" * 36
    try:
        r.create(f"اكتب {fake}", _chain_planner())
        refused = False
    except D.DurableWriteError:
        refused = True
    pushed = any(fake in json.dumps(x["payload"]) for x in env.remote.list_blobs("tasks"))
    return {"refused": refused, "pushed": pushed}


def s_newest_rev_wins(env, m):
    r = env.runner()
    tid = r.create("g", _chain_planner())
    r.run(tid)
    stale = env.runner(local="diskC")
    t = r.store.load(tid)
    old = {**t, "status": "running", "steps": [], "rev": 1}
    (env.tmp / "diskC").mkdir(parents=True, exist_ok=True)
    (env.tmp / "diskC" / f"{tid}.json").write_text(json.dumps(old), encoding="utf-8")
    got = stale.store.load(tid)
    return {"status": got["status"], "steps": len(got["steps"]), "rev_gt_1": got["rev"] > 1}


def s_external_not_repeated(env, m):
    steps = [{"tool": "t.count", "inputs": {"tag": "a"}},
             {"tool": "ext.send", "inputs": {"message": "hi"}}]
    tid = _kill_mid(env, kill_tag="send", steps=steps, external=("ext.send",))
    _new_boot(m, "bootB")
    fresh = env.runner(local="diskB", external=("ext.send",))
    t = fresh.store.load(tid)
    t["lease"]["until"] = 0
    fresh.store._save_local(t)
    res = fresh.run(tid)
    return {"status": res["status"], "calls": calls(env.calls)}


def s_heartbeat_renews(env, m):
    old = D.HEARTBEAT_S
    D.HEARTBEAT_S = 0.2
    try:
        r = env.runner()
        tid = r.create("g", _chain_planner([{"tool": "t.wait", "inputs": {"seconds": "1.2"}}]))
        th = threading.Thread(target=r.run, args=(tid,))
        th.start()
        time.sleep(0.3)
        first = env.remote.load_blob("tasks", tid)["lease"]["until"]
        time.sleep(0.6)
        second = env.remote.load_blob("tasks", tid)["lease"]["until"]
        th.join()
        final = env.remote.load_blob("tasks", tid)
    finally:
        D.HEARTBEAT_S = old
    return {"renewed": second > first, "final_status": final["status"],
            "final_lease": final["lease"]}


def s_progress_reports_boots(env, m):
    tid = _kill_mid(env)
    _new_boot(m, "bootB")
    fresh = env.runner(local="diskB")
    t = fresh.store.load(tid)
    t["lease"]["until"] = 0
    fresh.store._save_local(t)
    fresh.run(tid)
    p = fresh.progress(tid)
    return {"boots": [[b["boot"] if b["boot"] == "bootB" else "old", b["from_step"]]
                      for b in p["boots"]],
            "planner": p["planner"], "answer_has_chain": "t.count → t.count → t.count" in (p["answer"] or "")}


def s_start_async_dedup(env, m):
    r = env.runner()
    tid = r.create("g", _chain_planner([{"tool": "t.wait", "inputs": {"seconds": "0.5"}}]))
    t0 = time.time()
    a = r.start_async(tid)
    fast = time.time() - t0 < 0.3
    time.sleep(0.1)
    b = r.start_async(tid)
    deadline = time.time() + 5
    while time.time() < deadline and r.progress(tid)["status"] != "completed":
        time.sleep(0.05)
    return {"first_started": a["started"], "returned_fast": fast,
            "second": b.get("reason"), "status": r.progress(tid)["status"]}


def s_auto_resume_flag(env, m):
    prev = os.environ.get("SOVEREIGN_TASKS_AUTO_RESUME")
    out = {}
    try:
        os.environ["SOVEREIGN_TASKS_AUTO_RESUME"] = "0"
        out["off"] = D.auto_resume_enabled()
        os.environ["SOVEREIGN_TASKS_AUTO_RESUME"] = "1"
        out["on"] = D.auto_resume_enabled()
        os.environ.pop("SOVEREIGN_TASKS_AUTO_RESUME")
        out["default_under_pytest"] = D.auto_resume_enabled() if "pytest" in sys.modules else False
    finally:
        if prev is None:
            os.environ.pop("SOVEREIGN_TASKS_AUTO_RESUME", None)
        else:
            os.environ["SOVEREIGN_TASKS_AUTO_RESUME"] = prev
    return out


def s_terminal_idempotent(env, m):
    r = env.runner()
    tid = r.create("g", _chain_planner())
    r.run(tid)
    again = r.run(tid)
    return {"already_terminal": again.get("already_terminal"), "calls": len(calls(env.calls))}


def s_real_process_kill(env, m):
    """قتل حقيقي: عملية A تبدأ المهمة وتُقتل بـSIGKILL أثناء خطوة الانتظار؛ عملية B
    بقرص محلي فارغ تقلع وماسحها يستأنف من المخزن الدائم المشترك."""
    py = sys.executable
    here = str(Path(__file__).resolve())
    a = subprocess.Popen([py, here, "--child", "start", str(env.tmp)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tid, deadline = None, time.time() + 30
    while time.time() < deadline:
        rows = env.remote.list_blobs("tasks")
        t = rows[0]["payload"] if rows else None
        if t and len(t.get("steps", [])) >= 2 and "2" in (t.get("intents") or {}):
            tid = t["id"]
            break
        time.sleep(0.05)
    a.send_signal(signal.SIGKILL)
    a.wait(10)
    killed_at = calls(env.calls)
    b = subprocess.run([py, here, "--child", "resume", str(env.tmp)],
                       capture_output=True, text=True, timeout=60)
    final = env.remote.load_blob("tasks", tid) if tid else {}
    boots = [x["boot"] for x in final.get("steps", [])]
    return {"killed_signal": a.returncode == -signal.SIGKILL, "calls_at_kill": killed_at,
            "child_b_rc": _child_rc(b), "status": final.get("status"),
            "calls_final": calls(env.calls), "runs": final.get("runs"),
            "distinct_boots": len(set(boots)), "boot_split": boots[:2] != boots[2:4] and len(boots) == 4,
            "intents_left": len(final.get("intents") or {})}


def _child(role: str, root: str) -> int:
    """عملية فرعية حقيقية. إيجار قصير (2ث، نبض 0.5ث) ليظهر انتهاؤه الطبيعي بعد القتل."""
    import memory.core as mc
    mc.get_core = lambda: FakeCore()
    D.LEASE_S, D.HEARTBEAT_S = 2, 0.5
    env = Env(Path(root))
    plan = [{"tool": "t.count", "inputs": {"tag": "a"}},
            {"tool": "t.count", "inputs": {"tag": "$steps.0.result.tag"}},
            {"tool": "t.wait", "inputs": {"seconds": "3"}},
            {"tool": "t.count", "inputs": {"tag": "d"}}]
    if role == "start":
        r = env.runner(local="diskA")
        tid = r.create("قتل حقيقي", {"kind": "chain", "steps": plan}, auto_resume=True)
        r.run(tid)
        return 0
    r = env.runner(local="diskB")        # قرص محلي فارغ = نشر/إعادة تشغيل جديدة
    r.boot_scan(window_s=8, every_s=0.5)  # يلتقط المهمة حين ينتهي إيجار العملية المقتولة
    deadline = time.time() + 30
    while time.time() < deadline:
        rows = r.store.list()
        if rows and rows[0].get("status") not in ("running", "pending"):
            return 0
        time.sleep(0.1)
    return 3


SCENARIOS = {f.__name__[2:]: f for f in (
    s_chain_resolves, s_validation_rejects, s_missing_path_honest, s_fresh_disk_restores,
    s_resume_after_kill, s_concurrent_single_execution, s_live_lease_elsewhere,
    s_scanner_resumes_orphan, s_scanner_skips_non_auto_and_terminal, s_push_failure_fail_closed,
    s_secret_never_pushed, s_newest_rev_wins, s_external_not_repeated, s_heartbeat_renews,
    s_progress_reports_boots, s_start_async_dedup, s_auto_resume_flag, s_terminal_idempotent,
    s_real_process_kill)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    import logging
    import memory.core as mc
    tmp = Path(tempfile.mkdtemp(prefix="r853-e-"))
    saved_core, monkey = mc.get_core, {}
    mc.get_core = lambda: FakeCore()
    logging.disable(logging.CRITICAL)
    try:
        try:
            got = SCENARIOS[case["scenario"]](Env(tmp), monkey)
        except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
            got = {"error": f"{type(exc).__name__}: {exc}"}
        got = json.loads(json.dumps(got, default=list))
        failed = [{"check": k, "want": v, "got": got.get(k)}
                  for k, v in case["expect"].items() if got.get(k) != v]
        return {"id": case["id"], "rule": case["rule"], "pass": not failed,
                "got": got, "failed_checks": failed}
    finally:
        logging.disable(logging.NOTSET)
        mc.get_core = saved_core
        if "BOOT_ID" in monkey:
            D.BOOT_ID = monkey["BOOT_ID"]
        shutil.rmtree(tmp, ignore_errors=True)


def run(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [run_case(c) for c in cases]
    passed = sum(r["pass"] for r in results)
    return {"score": round(passed / len(results), 4) if results else 0.0,
            "passed": passed, "n": len(results),
            "failures": [r for r in results if not r["pass"]]}


if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "--child":
    print("CHILD_RC=%d" % _child(sys.argv[2], sys.argv[3]))  # رمز النتيجة عبر المخرج (لا مسار إنهاء — R-686)
