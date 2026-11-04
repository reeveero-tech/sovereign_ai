# -*- coding: utf-8 -*-
"""اختبارات R-844 — الطابور غير المتزامن (D-059) وعيوب المنسق التي كشفها.

قبل الطابور: أربعة عيوب في المنسق تمنع العمل في الخلفية بأمان
(forensics/R-844_crash_concurrency_RED.txt):
D1 استئناف بعد إعادة التشغيل ⇒ KeyError، D2 انقطاع أثناء كتابة ⇒ كتابة مكررة،
D3 موافقات في الذاكرة فقط ⇒ حلقات يتيمة، D4 موافقة حلقة تُجيز كتابة أخرى.
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from agent_orchestrator import schemas  # noqa: E402
from agent_orchestrator.execution_engine import write_idempotency_key  # noqa: E402
from evaluation import queue_reliability as qr, sandbox_env, suites  # noqa: E402
from job_queue import kinds, service  # noqa: E402
from job_queue.store import (IdempotencyConflict, JobStore, QueueError,  # noqa: E402
                             QueueFull)
from job_queue.worker import MAX_DRAIN, Worker, backoff_s, scrub  # noqa: E402

OWNER_KEY = "test_master_key_1234567890abcdef"


def _req(session, title="عطل"):
    return schemas.new_request(
        user_id="t", session_id=session, permissions=["orchestrator:write"],
        utterance=f"افتح مشكلة بعنوان {title} في github.com/acme/webapp")


@pytest.fixture
def env(tmp_path):
    return qr.Env(tmp_path)


# ===================================================================== عيوب المنسق
def test_d1_resume_after_restart_has_no_keyerror(env):
    out = env.o.submit(_req("d1"))
    env.restart()
    r = env.o.decide_approval(out["loop_id"], out["pending_approval"]["approval_id"],
                              "approved", "owner", False)
    assert r["status"] == "completed" and env.writes() == 1


def test_d2_crash_mid_write_is_never_blindly_repeated(env):
    out = env.o.submit(_req("d2"))
    env.t.crash_on = {"POST"}
    with pytest.raises(qr.Crash):
        env.o.decide_approval(out["loop_id"], out["pending_approval"]["approval_id"],
                              "approved", "owner", False)
    disk = env.o.state.load(out["loop_id"])
    assert disk["inflight"]["idempotency_key"] == write_idempotency_key(out["loop_id"], "s1")
    env.restart()
    r = env.o.run(out["loop_id"])
    assert r["status"] == "needs_owner_review"
    assert r["results"][-1]["error"]["code"] == "uncertain_outcome"
    assert write_idempotency_key(out["loop_id"], "s1") in r["reply"]
    assert env.writes() == 1  # لا كتابة ثانية، ولا طلب موافقة جديد صامت
    assert not r.get("pending_approval") and "inflight" not in env.o.state.load(out["loop_id"])
    assert env.o.run(out["loop_id"])["status"] == "needs_owner_review"  # نهائية
    assert env.writes() == 1


def test_d2b_inflight_cleared_after_success_and_key_deterministic(env):
    env.o.approvals.grant_session("d2b", "github.issue_create")
    out = env.o.submit(_req("d2b"))
    assert out["status"] == "completed" and "inflight" not in env.o.state.load(out["loop_id"])
    assert write_idempotency_key("L", "s1") == write_idempotency_key("L", "s1") == "orch:L:s1"


def test_d3_approvals_survive_restart(env):
    out = env.o.submit(_req("d3"))
    env.restart()
    assert [a["approval_id"] for a in env.o.pending_approvals()] == \
        [out["pending_approval"]["approval_id"]]
    r = env.o.decide_approval(out["loop_id"], out["pending_approval"]["approval_id"],
                              "approved", "owner", False)
    assert r["status"] == "completed"


def test_d3b_corrupt_approvals_file_fails_closed(tmp_path):
    from agent_orchestrator.approval_gate import ApprovalGate
    p = tmp_path / "approvals.json"
    p.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError):
        ApprovalGate(path=str(p))


def test_d4_approval_is_scoped_to_its_loop(env):
    a = env.o.submit(_req("d4a", "أ"))
    b = env.o.submit(_req("d4b", "ب"))
    assert a["pending_approval"]["step_id"] == b["pending_approval"]["step_id"] == "s1"
    env.o.approvals.decide(a["pending_approval"]["approval_id"], "owner", "approved")
    rb = env.o.run(b["loop_id"])
    assert rb["status"] == "pending_approval" and env.writes() == 0
    assert env.o.run(a["loop_id"])["status"] == "completed" and env.writes() == 1


def test_submit_with_existing_loop_id_rejected(env):
    out = env.o.submit(_req("dup"))
    with pytest.raises(ValueError):
        env.o.submit(_req("dup"), loop_id=out["loop_id"])


# ===================================================================== المخزن
def _store(tmp_path, **kw):
    now = [1000.0]
    return JobStore(str(tmp_path / "q.db"), clock=lambda: now[0], **kw), now


def test_s1_enqueue_requires_key_and_dedups(tmp_path):
    st, _ = _store(tmp_path)
    with pytest.raises(QueueError):
        st.enqueue("k", {}, "", "o", 1, 10)
    j1, c1 = st.enqueue("k", {"a": 1}, "x", "o", 1, 10)
    j2, c2 = st.enqueue("k", {"a": 1}, "x", "o", 1, 10)
    assert (c1, c2) == (True, False) and j1["id"] == j2["id"]
    with pytest.raises(IdempotencyConflict):
        st.enqueue("k", {"a": 2}, "x", "o", 1, 10)
    assert [e["event"] for e in st.events(j1["id"])] == ["enqueued", "deduplicated"]


def test_s2_concurrent_claims_never_double_take(tmp_path):
    st, _ = _store(tmp_path, max_depth=100)
    for i in range(40):
        st.enqueue("k", {"i": i}, f"c{i}", "o", 1, 60)
    taken, lock = [], threading.Lock()

    def grab(w):
        while True:
            j = st.claim(w)
            if j is None:
                return
            with lock:
                taken.append(j["id"])
    ts = [threading.Thread(target=grab, args=(f"w{i}",)) for i in range(8)]
    [t.start() for t in ts]
    [t.join(30) for t in ts]
    assert len(taken) == 40 and len(set(taken)) == 40


def test_s3_priority_then_fifo(tmp_path):
    st, now = _store(tmp_path)
    a, _ = st.enqueue("k", {"n": "a"}, "a", "o", 1, 10)
    now[0] += 1
    b, _ = st.enqueue("k", {"n": "b"}, "b", "o", 1, 10, priority=5)
    now[0] += 1
    c, _ = st.enqueue("k", {"n": "c"}, "c", "o", 1, 10)
    assert [st.claim("w")["id"] for _ in range(3)] == [b["id"], a["id"], c["id"]]


def test_s4_retry_backoff_then_dead(tmp_path):
    st, now = _store(tmp_path)
    j, _ = st.enqueue("k", {}, "r", "o", 2, 10)
    c = st.claim("w")
    assert st.retry(j["id"], "w", c["fence"], "e1", 5.0) == "queued"
    assert st.claim("w") is None          # التأخير لم ينقضِ
    now[0] += 6
    c = st.claim("w")
    assert c["attempts"] == 2
    assert st.retry(j["id"], "w", c["fence"], "e2", 5.0) == "dead"
    assert st.get(j["id"])["status"] == "dead"


def test_s5_recover_requeues_then_dead_and_honours_cancel(tmp_path):
    st, now = _store(tmp_path)
    j, _ = st.enqueue("k", {}, "x", "o", 2, 10)
    st.claim("w1")
    now[0] += 11
    assert st.recover() == [{"job_id": j["id"], "to": "queued"}]
    st.claim("w2")
    now[0] += 11
    assert st.recover() == [{"job_id": j["id"], "to": "dead"}]
    k, _ = st.enqueue("k", {}, "y", "o", 3, 10)
    st.claim("w3")
    assert st.cancel(k["id"], "owner")["cancel_requested"] is True
    now[0] += 11
    assert st.recover() == [{"job_id": k["id"], "to": "cancelled"}]


def test_s6_backpressure_and_terminal_finish_only(tmp_path):
    st, _ = _store(tmp_path, max_depth=2)
    st.enqueue("k", {}, "1", "o", 1, 10)
    st.enqueue("k", {}, "2", "o", 1, 10)
    with pytest.raises(QueueFull):
        st.enqueue("k", {}, "3", "o", 1, 10)
    c = st.claim("w")
    with pytest.raises(QueueError):
        st.finish(c["id"], "w", c["fence"], "running")
    assert st.finish(c["id"], "w", c["fence"], "succeeded", {"ok": 1})
    assert not st.finish(c["id"], "w", c["fence"], "failed")   # لا كتابة فوق نهائية
    st.enqueue("k", {}, "3", "o", 1, 10)                        # تحررت سعة
    assert st.stats()["depth"] == 2


def test_s7_survives_reopen(tmp_path):
    st, _ = _store(tmp_path)
    j, _ = st.enqueue("k", {"a": "ب"}, "z", "o", 1, 10)
    st2 = JobStore(str(tmp_path / "q.db"))
    assert st2.get(j["id"])["payload"] == {"a": "ب"}


# ===================================================================== العامل والأنواع
def test_w1_scrub_and_backoff():
    assert "ghp_" not in scrub("token ghp_ABCDEFGH12345678 leaked")
    assert "***" in scrub("Authorization: Bearer abcdefgh.ijkl")
    assert [backoff_s(a) for a in (1, 2, 3)] == [2.0, 4.0, 8.0] and backoff_s(30) == 300.0


def test_w2_unknown_kind_fails_and_drain_is_capped(tmp_path):
    st, _ = _store(tmp_path, max_depth=200)
    j, _ = st.enqueue("ghost.kind", {}, "g", "o", 1, 10)
    assert Worker(st, {}).run_once()["status"] == "failed"
    assert "غير مسجل" in st.get(j["id"])["error"]
    for i in range(MAX_DRAIN + 5):
        st.enqueue("ghost.kind", {}, f"g{i}", "o", 1, 10)
    assert len(Worker(st, {}).drain(1000)) == MAX_DRAIN


def test_w3_secret_in_exception_is_scrubbed(tmp_path):
    st, _ = _store(tmp_path)

    def leak(ctx):
        raise RuntimeError("فشل مع ghp_SECRETSECRET1234")
    reg = {"t.leak": kinds.JobKind("t.leak", "يسرب", "low", "اختبار", {"type": "object"},
                                   lambda p: 10.0, 1, (), leak)}
    j, _ = st.enqueue("t.leak", {}, "l", "o", 1, 10)
    Worker(st, reg).run_once()
    assert "ghp_SECRET" not in st.get(j["id"])["error"]


def test_w4_background_loop_stops(tmp_path):
    st, _ = _store(tmp_path)
    stop = threading.Event()
    t = threading.Thread(target=Worker(st, {}).loop, args=(stop, 0.05))
    t.start()
    stop.set()
    t.join(5)
    assert not t.is_alive()


def test_k1_every_kind_has_description_risk_schema():
    for k in kinds.KINDS.values():
        pub = k.public()
        assert len(pub["description"]) > 20 and pub["risk"] in ("low", "medium", "high")
        assert pub["risk_reason"] and pub["payload_schema"]["type"] == "object"
        assert pub["payload_schema"].get("additionalProperties") is False or k.name == "evaluation.run"
        assert 1 <= k.max_attempts <= 3


@pytest.mark.parametrize("payload", [
    {},
    {"utterance": "x", "extra": 1},
    {"utterance": "x", "constraints": {"max_cost": 1, "max_time_s": 9999, "max_steps": 3}},
    {"utterance": "x", "constraints": {"max_cost": 1, "max_time_s": 30, "max_steps": 500}},
])
def test_k2_loop_payload_rejected(payload):
    with pytest.raises(schemas.SchemaError):
        kinds.get("orchestrator.loop").validate(payload)


def test_k3_queue_never_bypasses_approval(env):
    j, _ = env.enqueue("orchestrator.loop", qr._write("تجاوز", "k3"), "k3")
    env.worker().drain(5)
    assert env.store.get(j["id"])["status"] == "needs_human" and env.writes() == 0


# ===================================================================== المجموعة المجمّدة
def test_q1_queue_suite_frozen_and_perfect():
    s = suites.get("queue.reliability")
    assert s.floor == 1.0 and suites.file_sha256(s.data_path) == s.sha256
    r = s.runner(s.data_path)
    assert r["score"] == 1.0, r["failures"]
    assert r["n"] == 14


# ===================================================================== الواجهة
@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from job_queue import api_routes
    monkeypatch.setenv("SOVEREIGN_QUEUE_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("SOVEREIGN_QUEUE_MAX_DEPTH", "2")
    monkeypatch.setenv("SOVEREIGN_EVAL_DIR", str(tmp_path / "ev"))
    service.reset_for_tests()
    app = FastAPI()
    app.include_router(api_routes.router)
    yield TestClient(app)
    service.reset_for_tests()


H = {"X-API-Key": OWNER_KEY}
EVAL = {"kind": "evaluation.run", "payload": {"suites": ["planner.holdout"]}}


def test_api1_auth_and_idempotency_required(client):
    assert client.post("/queue/jobs", json=EVAL, headers={"Idempotency-Key": "a"}).status_code == 401
    assert client.post("/queue/jobs", json=EVAL, headers=H).status_code == 428
    assert client.get("/queue/jobs").status_code == 401
    assert client.get("/queue/kinds").status_code == 200
    assert client.get("/queue/stats").json()["max_depth"] == 2


def test_api2_validation(client):
    hk = {**H, "Idempotency-Key": "v"}
    assert client.post("/queue/jobs", json={"kind": "nope", "payload": {}}, headers=hk).status_code == 422
    assert client.post("/queue/jobs", json={"kind": "orchestrator.loop", "payload": {"x": 1}},
                       headers=hk).status_code == 422


def test_api3_lifecycle_dedup_conflict_full_drain(client):
    r1 = client.post("/queue/jobs", json=EVAL, headers={**H, "Idempotency-Key": "e1"})
    r2 = client.post("/queue/jobs", json=EVAL, headers={**H, "Idempotency-Key": "e1"})
    assert r1.status_code == 202 and r2.status_code == 200 and r2.json()["deduplicated"]
    jid = r1.json()["job"]["id"]
    other = {"kind": "evaluation.run", "payload": {"suites": ["planner.dev"]}}
    assert client.post("/queue/jobs", json=other, headers={**H, "Idempotency-Key": "e1"}).status_code == 409
    assert client.post("/queue/jobs", json=other, headers={**H, "Idempotency-Key": "e2"}).status_code == 202
    full = client.post("/queue/jobs", json=EVAL, headers={**H, "Idempotency-Key": "e3"})
    assert full.status_code == 429 and full.headers.get("Retry-After") == "30"
    d = client.post("/queue/drain", json={"max_jobs": 1}, headers=H)
    assert d.status_code == 200 and d.json()["count"] == 1
    j = client.get(f"/queue/jobs/{jid}", headers=H).json()
    assert j["job"]["status"] == "succeeded" and j["job"]["result"]["pass"] is True
    assert [e["event"] for e in j["events"]][:3] == ["enqueued", "deduplicated", "claimed"]
    assert "payload_hash" not in j["job"] and "lease_owner" not in j["job"]
    assert client.get("/queue/jobs/nope", headers=H).status_code == 404


def test_api4_cancel_queued(client):
    r = client.post("/queue/jobs", json=EVAL, headers={**H, "Idempotency-Key": "c1"})
    jid = r.json()["job"]["id"]
    assert client.post(f"/queue/jobs/{jid}/cancel").status_code == 401
    c = client.post(f"/queue/jobs/{jid}/cancel", headers=H)
    assert c.json()["job"]["status"] == "cancelled"
    assert client.post("/queue/drain", json={}, headers=H).json()["count"] == 0


def test_svc1_workers_disabled_reasons(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_QUEUE_WORKERS", "0")
    assert "معطلون" in service.start_workers()
    monkeypatch.setenv("SOVEREIGN_QUEUE_WORKERS", "2")  # الخيوط معطلة في الاختبارات (conftest)
    assert "معطلة" in service.start_workers()


def test_app_wiring():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        kinds_ = {k["kind"] for k in c.get("/queue/kinds").json()["kinds"]}
        assert kinds_ == {"orchestrator.loop", "orchestrator.approval", "evaluation.run"}
        assert c.post("/queue/jobs", json=EVAL).status_code == 401
