# -*- coding: utf-8 -*-
"""اختبارات R-845 — الإشعارات (D-060).

قبل R-845 (forensics/R-845_notifications_RED.txt): حلقة تصل «انتظار موافقة» أو
«مراجعة المالك» ولا يعلم المالك إلا باستطلاع يدوي.
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from evaluation import notify_reliability as nr, queue_reliability as qr, suites  # noqa: E402
from notifications import channels as nch, dispatcher as ndisp, events as nev  # noqa: E402
from notifications import service as nsvc, store as nstore  # noqa: E402
from notifications.store import OutboxStore  # noqa: E402

OWNER_KEY = "test_master_key_1234567890abcdef"
H = {"X-API-Key": OWNER_KEY}


@pytest.fixture
def hook_env(monkeypatch):
    for k in nr._ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("SOVEREIGN_NOTIFY_WEBHOOK_URL", nr.HOOK_URL)
    monkeypatch.setenv("SOVEREIGN_NOTIFY_WEBHOOK_SECRET", nr.HOOK_SECRET)
    net = nr._Net()
    monkeypatch.setattr(nch, "TRANSPORT", net)
    return net


@pytest.fixture
def ostore(tmp_path):
    now = [5000.0]
    st = OutboxStore(str(tmp_path / "o.db"), clock=lambda: now[0])
    st.now = now
    return st


# ===================================================================== الأحداث
@pytest.mark.parametrize("view,event", [
    ({"status": "pending_approval", "loop_id": "L", "pending_approval": {"approval_id": "A", "step_id": "s1"}},
     "approval.requested"),
    ({"status": "needs_owner_review", "loop_id": "L"}, "review.required"),
    ({"status": "needs_clarification", "loop_id": "L", "reply": "؟"}, "clarification.needed"),
    ({"status": "failed", "loop_id": "L"}, "loop.failed"),
])
def test_e1_loop_states_map_to_events(view, event):
    assert nev.from_loop(view)["event"] == event


@pytest.mark.parametrize("view", [
    {"status": "completed", "loop_id": "L"}, {"status": "running", "loop_id": "L"},
    {"status": "cancelled", "loop_id": "L"}, {"status": "pending_approval", "loop_id": "L"},
    {"status": "failed"}])
def test_e2_no_event_for_quiet_or_malformed_states(view):
    assert nev.from_loop(view) is None


def test_e3_job_events_and_no_double_for_loop_jobs():
    assert nev.from_job({"id": "J", "status": "dead", "kind": "k"})["event"] == "job.dead"
    assert nev.from_job({"id": "J", "status": "failed", "kind": "k"})["event"] == "job.failed"
    assert nev.from_job({"id": "J", "status": "failed", "kind": "orchestrator.loop",
                         "loop_id": "L"}) is None
    assert nev.from_job({"id": "J", "status": "failed", "kind": "evaluation.run",
                         "result": {"pass": False}})["event"] == "eval.failed"
    assert nev.from_job({"id": "J", "status": "succeeded", "kind": "k"}) is None
    assert nev.from_job({}) is None


def test_e4_unknown_event_and_scrub_and_link(monkeypatch):
    with pytest.raises(ValueError):
        nev.make("nope", "k", "s", "x")
    assert "***" in nev.scrub("bot 123456789:" + "A" * 35)
    assert "***" in nev.scrub("xoxb-1234567890-abcdef")
    monkeypatch.setenv("SOVEREIGN_PUBLIC_URL", "http://insecure.example")
    assert nev.make("job.dead", "k", "s", "x", link="/q")["link"] == "/q"
    monkeypatch.setenv("SOVEREIGN_PUBLIC_URL", "https://app.example/")
    assert nev.make("job.dead", "k", "s", "x", link="/q")["link"] == "https://app.example/q"


# ===================================================================== القنوات
def test_c1_webhook_configuration_rules(monkeypatch):
    for k in nr._ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    w = nch.WebhookChannel()
    assert not w.configured()[0]
    monkeypatch.setenv("SOVEREIGN_NOTIFY_WEBHOOK_URL", "http://x.example")
    assert "https" in w.configured()[1]
    monkeypatch.setenv("SOVEREIGN_NOTIFY_WEBHOOK_URL", "https://x.example")
    monkeypatch.setenv("SOVEREIGN_NOTIFY_WEBHOOK_SECRET", "short")
    assert "توقيع" in w.configured()[1]
    monkeypatch.setenv("SOVEREIGN_NOTIFY_WEBHOOK_SECRET", "s" * 16)
    assert w.configured() == (True, "مضبوط")


def test_c2_telegram_configuration_and_public_hides_secrets(monkeypatch):
    for k in nr._ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    t = nch.TelegramChannel()
    assert not t.configured()[0]
    monkeypatch.setenv("SOVEREIGN_TELEGRAM_BOT_TOKEN", nr.TG_TOKEN)
    assert "CHAT_ID" in t.configured()[1]
    monkeypatch.setenv("SOVEREIGN_TELEGRAM_CHAT_ID", "1")
    fp1 = t.fingerprint()
    assert t.configured()[0] and nr.TG_TOKEN not in json.dumps(t.public())
    monkeypatch.setenv("SOVEREIGN_TELEGRAM_BOT_TOKEN", "987654321:" + "Z" * 35)
    assert t.fingerprint() != fp1 and len(fp1) == 16


@pytest.mark.parametrize("status,kind", [(401, "auth"), (403, "auth"), (400, "permanent"),
                                         (404, "permanent"), (408, "transient"),
                                         (429, "transient"), (500, "transient"),
                                         (503, "transient")])
def test_c3_http_classification(monkeypatch, status, kind):
    monkeypatch.setattr(nch, "TRANSPORT", lambda *a: (status, "x"))
    with pytest.raises(nch.SendError) as ei:
        nch._post("https://h", b"{}", {}, "t")
    assert ei.value.kind == kind


def test_c4_network_error_never_leaks_url(monkeypatch):
    def boom(url, *a):
        raise OSError(f"failed {url}")
    monkeypatch.setattr(nch, "TRANSPORT", boom)
    with pytest.raises(nch.SendError) as ei:
        nch._post("https://api.telegram.org/bot123:SECRET/sendMessage", b"{}", {}, "telegram")
    assert ei.value.kind == "transient" and "SECRET" not in str(ei.value)
    monkeypatch.setattr(nch, "TRANSPORT", lambda *a: (204, ""))
    nch._post("https://h", b"{}", {}, "t")   # 2xx لا يرفع


def test_c5_telegram_plain_text_no_parse_mode(monkeypatch, hook_env):
    monkeypatch.setenv("SOVEREIGN_TELEGRAM_BOT_TOKEN", nr.TG_TOKEN)
    monkeypatch.setenv("SOVEREIGN_TELEGRAM_CHAT_ID", "7")
    nch.TelegramChannel().send({"id": "N", "event": "job.dead", "severity": "high",
                                "title": "<b>t</b>", "summary": "s", "link": "/l",
                                "created_at": 1})
    body = hook_env.calls[0]["body"]
    assert "parse_mode" not in body and body["chat_id"] == "7" and "<b>t</b>" in body["text"]


# ===================================================================== المخزن
def test_s1_emit_dedupes_and_validates(ostore):
    ev = nev.make("job.dead", "k1", "s", "x")
    n1, c1 = ostore.emit(ev, [("webhook", "pending", "")])
    n2, c2 = ostore.emit(ev, [("webhook", "pending", "")])
    assert (c1, c2) == (True, False) and n1["id"] == n2["id"]
    assert len(ostore.deliveries_for(n1["id"])) == 1
    with pytest.raises(ValueError):
        ostore.emit(nev.make("job.dead", "k2", "s", "x"), [("webhook", "sent", "")])
    with pytest.raises(ValueError):
        ostore.mark_final(n1["id"], "webhook", "sent", "x")


def test_s2_prune_caps_growth(ostore, monkeypatch):
    monkeypatch.setattr(nstore, "MAX_KEEP", 3)
    for i in range(6):
        ostore.now[0] += 1
        ostore.emit(nev.make("job.dead", f"p{i}", "s", "x"), [("webhook", "pending", "")])
    assert ostore.stats()["notifications"] == 3
    assert ostore.stats()["deliveries"]["pending"] == 3


def test_s3_claim_is_atomic_across_threads(ostore):
    for i in range(30):
        ostore.emit(nev.make("job.dead", f"c{i}", "s", "x"), [("webhook", "pending", "")])
    got, lock = [], threading.Lock()

    def grab():
        for d in ostore.claim_due(50):
            with lock:
                got.append(d["notification_id"])
    ts = [threading.Thread(target=grab) for _ in range(6)]
    [t.start() for t in ts]
    [t.join(30) for t in ts]
    assert len(got) == 30 and len(set(got)) == 30


def test_s4_read_and_stats(ostore):
    n, _ = ostore.emit(nev.make("job.dead", "r", "s", "x"), [("webhook", "skipped", "سبب")])
    assert ostore.stats()["unread"] == 1
    t1 = ostore.mark_read(n["id"])["read_at"]
    ostore.now[0] += 10
    assert ostore.mark_read(n["id"])["read_at"] == t1     # القراءة مرة واحدة
    assert ostore.mark_read("nope") is None
    assert ostore.stats()["deliveries"]["skipped"] == 1 and ostore.list(unread_only=True) == []


# ===================================================================== الموزع
def test_d1_backoff_and_batch_cap(ostore, hook_env):
    assert [ndisp.backoff_s(a) for a in (1, 2, 3)] == [5.0, 10.0, 20.0]
    assert ndisp.backoff_s(99) == 600.0
    for i in range(ndisp.MAX_BATCH + 5):
        nsvc.emit(nev.make("job.dead", f"b{i}", "s", "x"), ostore)
    assert len(ndisp.Dispatcher(ostore, max_per_hour=1000).dispatch_once(999)) == ndisp.MAX_BATCH


def test_d2_unregistered_or_unconfigured_channel_fails(ostore, hook_env, monkeypatch):
    n, _ = ostore.emit(nev.make("job.dead", "u", "s", "x"), [("pigeon", "pending", "")])
    assert ndisp.Dispatcher(ostore).dispatch_once()[0]["status"] == "failed"
    n2, _ = nsvc.emit(nev.make("job.dead", "u2", "s", "x"), ostore)
    monkeypatch.delenv("SOVEREIGN_NOTIFY_WEBHOOK_SECRET")
    r = ndisp.Dispatcher(ostore).dispatch_once()
    assert r[0]["status"] == "failed" and hook_env.calls == []


def test_d3_unexpected_error_is_final_not_retried(ostore, monkeypatch):
    class Bad(nch.Channel):
        name = "bad"

        def configured(self):
            return True, "مضبوط"

        def fingerprint(self):
            return "f"

        def send(self, n):
            raise KeyError("خلل برمجي")
    n, _ = ostore.emit(nev.make("job.dead", "x", "s", "x"), [("bad", "pending", "")])
    d = ndisp.Dispatcher(ostore, channels=lambda: {"bad": Bad()})
    assert d.dispatch_once()[0]["status"] == "failed"
    ostore.now[0] += 10_000
    assert d.dispatch_once() == []


def test_d4_repeated_crashes_are_bounded(ostore, hook_env):
    n, _ = nsvc.emit(nev.make("job.dead", "cr", "s", "x"), ostore)
    for _ in range(ndisp.MAX_ATTEMPTS):
        ostore.claim_due()              # حجز ثم «موت» بلا تسجيل
        ostore.now[0] += nstore.LEASE_S + 1
    r = ndisp.Dispatcher(ostore).dispatch_once()
    assert r[0]["status"] == "failed" and hook_env.calls == []


def test_d5_background_loop_stops(ostore):
    stop = threading.Event()
    t = threading.Thread(target=ndisp.Dispatcher(ostore, channels=lambda: {}).loop,
                         args=(stop, 0.05))
    t.start()
    stop.set()
    t.join(5)
    assert not t.is_alive()


# ===================================================================== الربط
def test_w1_orchestrator_observer_and_isolation(tmp_path, ostore):
    q = qr.Env(tmp_path / "q")
    seen = []
    q.o.observers.append(lambda v: seen.append(v["status"]))
    q.o.observers.append(lambda v: 1 / 0)       # معطوب
    out = q.o.submit(nr._req("w1", "W1"))
    assert out["status"] == "pending_approval" and seen == ["pending_approval"]


def test_w2_worker_hooks_called_and_tolerated(tmp_path):
    q = qr.Env(tmp_path / "q")
    seen = []
    w = q.worker()
    w.on_finish = [lambda j: 1 / 0, lambda j: seen.append(j["status"])]
    q.enqueue("orchestrator.loop", qr.READ, "w2")
    assert w.run_once()["status"] == "succeeded" and seen == ["succeeded"]


def test_w3_install_is_idempotent(tmp_path, monkeypatch):
    from job_queue import service as jq
    monkeypatch.setattr(jq, "FINISH_HOOKS", [])
    q = qr.Env(tmp_path / "q")
    nsvc.install(q.o)
    nsvc.install(q.o)
    assert len(q.o.observers) == 1 and len(jq.FINISH_HOOKS) == 1


def test_w4_safe_emit_swallows(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("قرص ممتلئ")
    monkeypatch.setattr(nsvc, "emit", boom)
    assert nsvc.safe_emit(nev.make("job.dead", "z", "s", "x")) is None
    assert nsvc.safe_emit(None) is None


def test_w5_dispatcher_disabled_reasons(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_NOTIFY_DISPATCH", "0")
    assert "معطل" in nsvc.start_dispatcher()
    monkeypatch.setenv("SOVEREIGN_NOTIFY_DISPATCH", "1")   # الخيوط معطلة في الاختبارات
    assert "معطلة" in nsvc.start_dispatcher()


# ===================================================================== المجموعة المجمّدة
def test_q1_notify_suite_frozen_and_perfect():
    s = suites.get("notify.reliability")
    assert s.floor == 1.0 and suites.file_sha256(s.data_path) == s.sha256
    r = s.runner(s.data_path)
    assert r["score"] == 1.0 and r["n"] == 15, r["failures"]


# ===================================================================== الواجهة
@pytest.fixture
def client(tmp_path, monkeypatch, hook_env):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from notifications import api_routes
    monkeypatch.setenv("SOVEREIGN_NOTIFY_DB", str(tmp_path / "api.db"))
    nsvc.reset_for_tests()
    app = FastAPI()
    app.include_router(api_routes.router)
    yield TestClient(app)
    nsvc.reset_for_tests()


def test_api1_open_endpoints_hide_config(client):
    r = client.get("/notifications/channels")
    assert r.status_code == 200
    txt = r.text
    assert nr.HOOK_URL not in txt and nr.HOOK_SECRET not in txt
    assert {c["channel"]: c["configured"] for c in r.json()["channels"]}["webhook"] is True
    assert client.get("/notifications/stats").json()["notifications"] == 0


def test_api2_auth_idempotency_dedup_dispatch_read(client, hook_env):
    assert client.get("/notifications").status_code == 401
    assert client.post("/notifications/test", headers={"Idempotency-Key": "a"}).status_code == 401
    assert client.post("/notifications/test", headers=H).status_code == 428
    r1 = client.post("/notifications/test", headers={**H, "Idempotency-Key": "t1"})
    r2 = client.post("/notifications/test", headers={**H, "Idempotency-Key": "t1"})
    assert r1.status_code == 202 and r2.status_code == 200 and r2.json()["deduplicated"]
    nid = r1.json()["notification"]["id"]
    assert client.post("/notifications/dispatch").status_code == 401
    d = client.post("/notifications/dispatch", json={"max_items": 5}, headers=H).json()
    assert d["count"] == 1 and d["dispatched"][0]["status"] == "sent"
    assert len(hook_env.calls) == 1 and hook_env.calls[0]["headers"]["Idempotency-Key"] == nid
    lst = client.get("/notifications", headers=H).json()["notifications"]
    by = {d["channel"]: d for d in lst[0]["deliveries"]}
    assert by["webhook"]["status"] == "sent" and by["telegram"]["status"] == "skipped"
    assert "غير مضبوطة" in by["telegram"]["reason"]
    assert client.post("/notifications/nope/read", headers=H).status_code == 404
    assert client.post(f"/notifications/{nid}/read", headers=H).json()["notification"]["read_at"]


def test_api3_enable_channel(client):
    assert client.post("/notifications/channels/pigeon/enable", headers=H).status_code == 404
    nsvc.get_store().disable_channel("webhook", "401", "fp")
    r = client.post("/notifications/channels/webhook/enable", headers=H)
    assert r.json()["was_disabled"] is True


def test_app_wiring():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        assert c.get("/notifications/channels").status_code == 200
        assert c.get("/notifications").status_code == 401
        from agent_orchestrator.api_routes import get_orchestrator
        assert any(getattr(f, "r845", False) for f in get_orchestrator().observers)
