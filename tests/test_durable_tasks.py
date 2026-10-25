# -*- coding: utf-8 -*-
"""R-754 (ROADMAP_V5 §٣: ٣.١ + ٣.٢ + ٣.٣ — بأمر المالك 2026-10-25 «أسلمك المشروع»):
مهام دائمة قابلة للاستئناف فوق حلقة الوكيل (R-753).

- ٣.١: نقطة تفتيش على القرص بعد كل خطوة (بعد أثرها الموقّع)؛ قتل العملية فعلًا
  (SIGKILL) ثم الاستئناف يكمل من آخر نقطة لا من الصفر.
- ٣.٢: الفعل الخارجي لا يتكرر: نية تُكتب قبل التنفيذ وإنجاز بعده. نية بلا إنجاز
  عند الاستئناف: أداة تقبل idempotency_key تُعاد بنفس المفتاح (الطرف يزيل
  التكرار)، وأداة لا تقبله لا تُعاد أبدًا → needs_owner_review (مرة واحدة على
  الأكثر — لا ادعاء «بالضبط مرة» بلا دعم الطرف).
- ٣.٣: تقرير التقدم يُقرأ من نقاط التفتيش على القرص حرفيًا.
"""

import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

HARNESS = textwrap.dedent('''
    import json, os, sys, time
    sys.path.insert(0, os.path.join(os.environ["REPO"], "backend"))
    import memory.core as core_mod

    class FakeCore:
        def append_event(self, event_type, payload, user=None):
            with open(os.environ["LEDGER"], "a") as fh:
                fh.write(json.dumps([str(event_type), payload], default=str) + "\\n")
    core_mod.get_core = lambda: FakeCore()

    from tool_registry import ToolRegistry, ToolSpec
    from durable_tasks import TaskStore, DurableRunner

    W = os.environ["WORK"]

    def bump(name):
        p = os.path.join(W, name)
        n = int(open(p).read()) if os.path.exists(p) else 0
        open(p, "w").write(str(n + 1))
        return n + 1

    def build():
        r = ToolRegistry()
        r.register(ToolSpec(name="step.a", description="", inputs={}, outputs="",
                            handler=lambda: {"a": bump("a.count")}))

        def notify(text, idempotency_key):
            seen = os.path.join(W, "notify.keys")
            keys = open(seen).read().split() if os.path.exists(seen) else []
            if idempotency_key not in keys:           # الطرف الخارجي يزيل التكرار
                open(seen, "a").write(idempotency_key + "\\n")
                bump("notify.count")
            if os.environ.get("KILL_AFTER_EFFECT") == "1":
                os.kill(os.getpid(), 9)               # قتل فعلي بعد الأثر قبل الإنجاز
            return {"sent": True}
        r.register(ToolSpec(name="notify.send", description="", outputs="",
                            inputs={"text": "", "idempotency_key": ""}, handler=notify))

        def slow():
            bump("slow.count")
            open(os.path.join(W, "slow.started"), "w").write("1")
            if os.environ.get("HANG") == "1":
                time.sleep(120)
            return {"slow": True}
        r.register(ToolSpec(name="step.slow", description="", inputs={}, outputs="",
                            handler=slow))
        return r

    store = TaskStore(os.path.join(W, "tasks"))
    runner = DurableRunner(store, build(), external_tools={"notify.send"})
    mode = sys.argv[1]
    if mode == "create":
        steps = json.loads(os.environ["STEPS"])
        tid = runner.create("هدف دائم", {"kind": "scripted", "steps": steps})
        print(tid, flush=True)
        runner.run(tid)
    else:
        print(json.dumps(runner.run(sys.argv[2]), ensure_ascii=False, default=str))
''')

CALL = lambda tool, inputs=None: {"action": "call", "tool": tool,
                                  "inputs": inputs or {}, "check": {"type": "ok"}}
FINISH = {"action": "finish", "answer": "تم"}


def _env(tmp_path, **extra):
    (tmp_path / "harness.py").write_text(HARNESS, encoding="utf-8")
    env = dict(os.environ, REPO=str(REPO_ROOT), WORK=str(tmp_path),
               LEDGER=str(tmp_path / "ledger.jsonl"))
    env.update(extra)
    return env


def _count(tmp_path, name):
    p = tmp_path / name
    return int(p.read_text()) if p.exists() else 0


def _py(tmp_path, args, env, timeout=60):
    return subprocess.run([sys.executable, str(tmp_path / "harness.py"), *args],
                          env=env, capture_output=True, text=True, timeout=timeout)


def test_sigkill_mid_task_resumes_from_last_checkpoint(tmp_path):
    steps = [CALL("step.a"), CALL("step.slow"), FINISH]
    env = _env(tmp_path, STEPS=json.dumps(steps), HANG="1")
    proc = subprocess.Popen([sys.executable, str(tmp_path / "harness.py"), "create"],
                            env=env, stdout=subprocess.PIPE, text=True)
    tid = proc.stdout.readline().strip()
    deadline = time.time() + 30
    while not (tmp_path / "slow.started").exists() and time.time() < deadline:
        time.sleep(0.05)
    assert (tmp_path / "slow.started").exists()
    os.kill(proc.pid, signal.SIGKILL)                 # قتل فعلي من الخارج
    proc.wait(timeout=10)
    assert proc.returncode == -signal.SIGKILL

    disk = json.loads((tmp_path / "tasks" / f"{tid}.json").read_text(encoding="utf-8"))
    assert disk["status"] == "running" and len(disk["steps"]) == 1  # نقطة تفتيش الخطوة ٠

    out = _py(tmp_path, ["resume", tid], _env(tmp_path, STEPS="[]"))
    res = json.loads(out.stdout.strip().splitlines()[-1])
    assert res["status"] == "completed" and res["resumed"] is True
    assert _count(tmp_path, "a.count") == 1           # الخطوة ٠ لم تُعد
    assert _count(tmp_path, "slow.count") == 2        # الخطوة المقطوعة (داخلية) أعيدت


def test_external_action_with_key_never_repeats_after_kill(tmp_path):
    steps = [CALL("step.a"), CALL("notify.send", {"text": "مرحبا"}), FINISH]
    env = _env(tmp_path, STEPS=json.dumps(steps), KILL_AFTER_EFFECT="1")
    first = _py(tmp_path, ["create"], env)
    assert first.returncode == -signal.SIGKILL
    tid = first.stdout.strip().splitlines()[0]
    assert _count(tmp_path, "notify.count") == 1

    out = _py(tmp_path, ["resume", tid], _env(tmp_path, STEPS="[]"))
    res = json.loads(out.stdout.strip().splitlines()[-1])
    assert res["status"] == "completed"
    assert _count(tmp_path, "notify.count") == 1      # حدث مرة واحدة فقط
    assert _count(tmp_path, "a.count") == 1


def test_external_without_key_support_is_not_retried(tmp_path, monkeypatch):
    """نية بلا إنجاز لأداة خارجية لا تقبل مفتاحًا → لا إعادة، مراجعة المالك."""
    import memory.core as core_mod
    from durable_tasks import TaskStore, DurableRunner
    from tool_registry import ToolRegistry, ToolSpec

    class FC:
        def append_event(self, *a, **k):
            return {}
    monkeypatch.setattr(core_mod, "get_core", lambda: FC())
    sent = []
    r = ToolRegistry()
    r.register(ToolSpec(name="mail.send", description="", inputs={"to": ""}, outputs="",
                        handler=lambda to: sent.append(to) or {"ok": 1}))
    store = TaskStore(tmp_path / "tasks")
    runner = DurableRunner(store, r, external_tools={"mail.send"})
    tid = runner.create("g", {"kind": "scripted",
                              "steps": [CALL("mail.send", {"to": "x"}), FINISH]})
    task = store.load(tid)                             # محاكاة انقطاع بعد كتابة النية
    task["status"] = "running"
    task["intents"] = {"0": {"tool": "mail.send", "key": f"{tid}:0"}}
    store.save(task)
    res = runner.run(tid)
    assert res["status"] == "needs_owner_review" and sent == []
    assert store.load(tid)["status"] == "needs_owner_review"


def test_progress_report_matches_disk_checkpoints(tmp_path, monkeypatch):
    import memory.core as core_mod
    from durable_tasks import TaskStore, DurableRunner
    from tool_registry import ToolRegistry, ToolSpec

    class FC:
        def append_event(self, *a, **k):
            return {}
    monkeypatch.setattr(core_mod, "get_core", lambda: FC())
    r = ToolRegistry()
    r.register(ToolSpec(name="echo", description="", inputs={"t": ""}, outputs="",
                        handler=lambda t: {"t": t}))
    store = TaskStore(tmp_path / "tasks")
    runner = DurableRunner(store, r)
    tid = runner.create("g", {"kind": "scripted", "steps": [
        CALL("echo", {"t": "1"}), CALL("echo", {"t": "2"}), FINISH]})
    runner.run(tid)
    rep = runner.progress(tid)
    disk = json.loads((tmp_path / "tasks" / f"{tid}.json").read_text(encoding="utf-8"))
    assert rep["status"] == disk["status"] == "completed"
    assert rep["done_steps"] == len(disk["steps"]) == 2
    assert [s["tool"] for s in rep["steps"]] == [s["tool"] for s in disk["steps"]]
    assert "planned" not in json.dumps(rep)           # لا تقدم مُدّعى من الخطة


def test_completed_task_is_not_rerun(tmp_path, monkeypatch):
    import memory.core as core_mod
    from durable_tasks import TaskStore, DurableRunner
    from tool_registry import ToolRegistry, ToolSpec

    class FC:
        def append_event(self, *a, **k):
            return {}
    monkeypatch.setattr(core_mod, "get_core", lambda: FC())
    n = []
    r = ToolRegistry()
    r.register(ToolSpec(name="echo", description="", inputs={}, outputs="",
                        handler=lambda: n.append(1) or {"x": 1}))
    runner = DurableRunner(TaskStore(tmp_path / "t"), r)
    tid = runner.create("g", {"kind": "scripted", "steps": [CALL("echo"), FINISH]})
    runner.run(tid)
    res = runner.run(tid)
    assert res["status"] == "completed" and len(n) == 1


def test_tasks_resume_tool_registered_and_inventory_moves():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        names = {t["name"] for t in client.get("/tools/list").json()["tools"]}
        assert {"tasks.resume", "tasks.progress"} <= names
        caps = {c["id"]: c for c in client.get("/capabilities").json()["capabilities"]}
        assert caps["durable_tasks"]["level"] != "missing"
