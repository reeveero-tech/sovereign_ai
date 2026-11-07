# -*- coding: utf-8 -*-
"""R-853 (٦.٢.٤): تكامل نقاط /tasks مع المشغل الدائم.

المنطق (القتل الحقيقي، الإيجار، الماسح) مغطى بالمجموعة المجمّدة tasks.resume؛ هنا:
الصلاحيات، الإنشاء في الخلفية بخطة chain من أدوات حقيقية مسجلة، التقدم، الاستئناف،
ورفض الخطة غير الصالحة — على مشغل معزول بمجلد مؤقت ومخزن دائم مزيف.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


@pytest.fixture
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app as app_mod
    import durable_tasks as D
    import scoped_tokens
    from evaluation.tasks_resume import DirStore
    from tool_registry import get_registry

    remote = DirStore(tmp_path / "remote")
    runner = D.DurableRunner(D.TaskStore(tmp_path / "tasks", remote=remote), get_registry())
    monkeypatch.setattr(D, "_RUNNER", runner)
    mgr = scoped_tokens.TokenManager(tmp_path / "auth", key=b"t" * 32, store=None,
                                     audit=lambda e, p: None)
    monkeypatch.setattr(scoped_tokens, "_MGR", mgr)
    master = app_mod._derive_api_auth("api_auth")
    with TestClient(app_mod.app) as client:
        yield client, runner, remote, master, mgr


def _wait_done(client, tid, key, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        p = client.get(f"/tasks/{tid}", headers={"X-Sovereign-Key": key}).json()
        if p["status"] not in ("pending", "running"):
            return p
        time.sleep(0.1)
    raise AssertionError("المهمة لم تنته")


PLAN = [{"tool": "skills.catalog", "inputs": {}},
        {"tool": "time.wait", "inputs": {"seconds": "1"}},
        {"tool": "ledger.recent", "inputs": {"limit": "{{steps.0.result.count}}"}}]


def test_r853_status_public(env):
    client = env[0]
    body = client.get("/tasks/status").json()
    assert body["auto_resume"] is False          # معطل تحت pytest صدقًا
    assert body["scanner"]["state"] == "disabled" or body["scanner"]["state"] == "idle"
    assert body["lease_s"] == 60 and "boot" in body


def test_r853_create_requires_tools_scope(env):
    client, _, _, _, mgr = env
    assert client.post("/tasks", json={"goal": "g", "plan": PLAN}).status_code == 401
    read_only = mgr.issue(["read"], 3600)["token"]
    assert client.post("/tasks", json={"goal": "g", "plan": PLAN},
                       headers={"X-Sovereign-Key": read_only}).status_code == 401
    assert client.get("/tasks").status_code == 401


def test_r853_chain_of_real_tools_runs_in_background(env):
    client, _, remote, _, mgr = env
    tok = mgr.issue(["tools", "read"], 3600)["token"]
    h = {"X-Sovereign-Key": tok}
    t0 = time.time()
    r = client.post("/tasks", json={"goal": "ثلاث أدوات متسلسلة", "plan": PLAN}, headers=h)
    assert r.status_code == 202, r.text
    assert time.time() - t0 < 1.0                # لا ينتظر الخطوات
    tid = r.json()["task_id"]
    p = _wait_done(client, tid, tok)
    assert p["status"] == "completed", p
    assert [s["tool"] for s in p["steps"]] == ["skills.catalog", "time.wait", "ledger.recent"]
    assert p["steps"][2]["inputs"]["limit"] == str(3)   # من ناتج الخطوة 0 (3 مهارات)
    # الحفظ محلي ثم دائم: الحالة المحلية قد تسبق المرآة بأجزاء ثانية (سباق ظهر في CI)
    deadline = time.time() + 10
    while remote.load_blob("tasks", tid)["status"] != "completed" and time.time() < deadline:
        time.sleep(0.05)
    assert remote.load_blob("tasks", tid)["status"] == "completed"
    listed = client.get("/tasks", headers=h).json()["tasks"]
    assert any(t["task_id"] == tid and t["done_steps"] == 3 for t in listed)


def test_r853_invalid_plan_422(env):
    client, _, _, master, _ = env
    h = {"X-Sovereign-Key": master}
    bad = client.post("/tasks", json={"goal": "g", "plan": [{"tool": "agent.run", "inputs": {}}]},
                      headers=h)
    assert bad.status_code == 422
    assert client.get("/tasks/nope", headers=h).status_code == 404
    assert client.post("/tasks/nope/resume", headers=h).status_code == 404


def test_r853_resume_endpoint_continues_orphan(env):
    client, runner, _, master, _ = env
    h = {"X-Sovereign-Key": master}
    tid = runner.create("g", {"kind": "chain", "steps": PLAN}, auto_resume=True)
    t = runner.store.load(tid)
    t["status"] = "running"                      # يتيمة: قُتلت عمليتها قبل أي خطوة
    t["lease"] = {"boot": "dead-boot", "until": 0}
    runner.store.save(t)
    r = client.post(f"/tasks/{tid}/resume", headers=h)
    assert r.status_code == 202 and r.json()["started"] is True
    p = _wait_done(client, tid, master)
    assert p["status"] == "completed" and p["runs"] == 1 and p["done_steps"] == 3


def test_r853_time_wait_bounds():
    from tool_registry import get_registry
    import app  # noqa: F401 — يسجل الأدوات
    reg = get_registry()
    assert reg.invoke("time.wait", caller="owner", inputs={"seconds": "0"})["ok"] is False
    assert reg.invoke("time.wait", caller="owner", inputs={"seconds": "31"})["ok"] is False
    ok = reg.invoke("time.wait", caller="owner", inputs={"seconds": "1"})
    assert ok["ok"] and ok["result"]["waited_s"] == 1
