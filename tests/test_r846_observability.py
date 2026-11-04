# -*- coding: utf-8 -*-
"""اختبارات R-846 — الرصد (D-061).

قبل R-846 (forensics/R-846_observability_RED.txt): أثر الحلقة يضيع بعد إعادة
التشغيل، والمتتبعات تتضخم بلا حد، و/health «healthy» ثابتة لا ترى الطابور ولا
الإشعارات، ولا X-Request-ID، و/metrics غير موجودة، وسر في رسالة سجل يمر كما هو.
"""
from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from agent_orchestrator import runtime as rt, tracing as tr  # noqa: E402
from evaluation import observability_reliability as orl, queue_reliability as qr, suites  # noqa: E402
from job_queue.store import JobStore  # noqa: E402
from notifications import events as nev  # noqa: E402
from notifications.store import OutboxStore  # noqa: E402
from observability import api_routes as oapi, context as ctx, health as oh  # noqa: E402
from observability import logs as olog, metrics as om, redact as ord_, service as osvc  # noqa: E402

OWNER_KEY = "test_master_key_1234567890abcdef"
H = {"X-API-Key": OWNER_KEY}
SECRET = "ghp_" + "A1" * 15


# ===================================================================== التنقية والسياق
@pytest.mark.parametrize("s", [SECRET, "sbp_" + "x" * 30, "rnd_" + "y" * 20,
                               "Bearer abcdefghijkl", "123456789:" + "T" * 35,
                               "password=hunter22", "api_key: s3cr3tvalue"])
def test_red1_redact_patterns(s):
    out = ord_.redact(f"قبل {s} بعد")
    assert s not in out and "***" in out and out.startswith("قبل")


def test_ctx1_accept_and_bind():
    assert ctx.accept_request_id("good-id.1234") == "good-id.1234"
    for bad in (None, "", "short", "a" * 65, "has space 12345", "x\";<b>12345"):
        rid = ctx.accept_request_id(bad)
        assert rid != bad and len(rid) == 32
    assert ctx.current() == {}
    with ctx.bind(request_id="r-12345678", loop_id="L1"):
        with ctx.bind(job_id="J1"):
            assert ctx.current() == {"request_id": "r-12345678", "loop_id": "L1", "job_id": "J1"}
        assert "job_id" not in ctx.current()
    assert ctx.current() == {}


# ===================================================================== المقاييس
def test_m1_counter_gauge_histogram_render():
    reg = om.Registry()
    c = reg.counter("a_total", "عداد", ["k"])
    c.inc({"k": "x"}, 2)
    with pytest.raises(ValueError):
        c.inc({"k": "x"}, -1)
    with pytest.raises(ValueError):
        c.inc({"wrong": "x"})
    g = reg.gauge("b", "مقياس")
    g.set(None, 5)
    g.inc(None, -2)
    hst = reg.histogram("c_seconds", "زمن", buckets=(0.1, 1.0))
    hst.observe(None, 0.05)
    hst.observe(None, 5)
    txt = reg.render()
    assert 'a_total{k="x"} 2' in txt and "\nb 3\n" in txt
    assert 'c_seconds_bucket{le="0.1"} 1' in txt and 'c_seconds_bucket{le="+Inf"} 2' in txt
    assert "c_seconds_count 2" in txt and "# TYPE c_seconds histogram" in txt
    assert "process_uptime_seconds" in txt


def test_m2_same_name_other_type_refused():
    reg = om.Registry()
    reg.counter("dup_total", "x", ["a"])
    assert reg.counter("dup_total", "x", ["a"]) is reg.counter("dup_total", "x", ["a"])
    with pytest.raises(ValueError):
        reg.gauge("dup_total", "x", ["a"])
    with pytest.raises(ValueError):
        reg.counter("bad-name", "x")
    with pytest.raises(ValueError):
        reg.histogram("h", "x", ["le"])


def test_m3_label_values_scrubbed_and_escaped():
    reg = om.Registry()
    reg.counter("s_total", "x", ["v"]).inc({"v": f'a"b\n{SECRET}'})
    txt = reg.render()
    assert SECRET not in txt and '\\"' in txt and "\\n" in txt


def test_m4_snapshot_and_collector_override():
    reg = om.Registry()
    reg.register_collector("c", lambda: [("q_depth", "gauge", "x", {}, 1)])
    reg.register_collector("c", lambda: [("q_depth", "gauge", "x", {}, 4)])
    snap = reg.snapshot()
    assert snap["q_depth"] == [{"labels": {}, "value": 4}]


# ===================================================================== السجلات
def _capture(fmt, name):
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setFormatter(fmt)
    lg = logging.getLogger(f"r846.test.{name}")
    lg.handlers[:] = [h]
    lg.propagate = False
    lg.setLevel(logging.INFO)
    olog.install_logging(root=lg)
    return lg, buf


def test_l1_scrub_message_args_and_exception():
    lg, buf = _capture(logging.Formatter("%(message)s"), "l1")
    lg.warning("token %s and %d", SECRET, 3)
    try:
        raise ValueError(f"bad {SECRET}")
    except ValueError:
        lg.exception("boom")
    out = buf.getvalue()
    assert SECRET not in out and "token *** and 3" in out and "Traceback" in out


def test_l2_json_formatter_context():
    lg, buf = _capture(olog.JsonFormatter(), "l2")
    with ctx.bind(request_id="rq-12345678", job_id="J9"):
        lg.warning("x %s", SECRET)
    rec = json.loads(buf.getvalue().strip())
    assert rec["request_id"] == "rq-12345678" and rec["job_id"] == "J9"
    assert rec["level"] == "WARNING" and SECRET not in rec["msg"] and rec["ts"].endswith("Z")


def test_l3_install_idempotent(monkeypatch):
    lg = logging.getLogger("r846.test.l3")
    h = logging.StreamHandler(io.StringIO())
    lg.handlers[:] = [h]
    olog.install_logging(root=lg)
    olog.install_logging(root=lg)
    f = logging.getLogRecordFactory()
    olog.install_logging(root=lg)
    assert logging.getLogRecordFactory() is f
    assert len([x for x in h.filters if isinstance(x, olog.ScrubFilter)]) == 1
    monkeypatch.setenv("SOVEREIGN_LOG_FORMAT", "json")
    assert "JSON" in olog.install_logging(root=lg)
    assert isinstance(h.formatter, olog.JsonFormatter)


# ===================================================================== HTTP
def test_h1_middleware_request_id_and_template():
    reg = om.Registry()
    c = orl._client(reg)
    r = c.get("/items/42", headers={"X-Request-ID": "abc-12345678"})
    assert r.headers["x-request-id"] == "abc-12345678"
    c.get("/nothing/here")
    routes = {s["route"] for s in orl._series(reg, "http_requests_total")}
    assert routes == {"/items/{item_id}", "__unmatched__"}
    statuses = {s["status"] for s in orl._series(reg, "http_requests_total")}
    assert statuses == {"200", "404"}


def test_h2_exception_counts_500():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from observability.http import ObservabilityMiddleware
    reg = om.Registry()
    app = FastAPI()

    @app.get("/boom")
    def boom():
        raise RuntimeError("x")
    app.add_middleware(ObservabilityMiddleware, root_app=app, registry=lambda: reg)
    c = TestClient(app, raise_server_exceptions=False)
    assert c.get("/boom").status_code == 500
    assert orl._series(reg, "http_requests_total")[0]["status"] == "500"


# ===================================================================== الآثار
def test_t1_scrub_string_values():
    out = tr.scrub({"title": f"x {SECRET}", "nested": [f"Bearer {'q' * 20}"]})
    assert SECRET not in json.dumps(out) and "q" * 20 not in json.dumps(out)


def test_t2_trace_store_roundtrip_invalid_id_and_prune(tmp_path):
    st = tr.TraceStore(str(tmp_path / "t"), max_files=10)
    assert st.save({"loop_id": "../evil", "spans": []}) is False
    assert st.load("../evil") is None
    for i in range(15):
        assert st.save({"loop_id": f"L{i}", "spans": [], "decisions": []})
    st.prune()
    assert st.count() == 10 and st.load("L14")["loop_id"] == "L14"


def test_t3_restore_keeps_duration():
    t = tr.Tracer.restore({"loop_id": "L", "spans": [{"span_id": "s"}], "decisions": [],
                           "total_duration_ms": 1000.0})
    s = t.summary()
    assert s["span_count"] == 1 and s["total_duration_ms"] >= 1000.0


def test_t4_runtime_restart_and_eviction(tmp_path):
    e = qr.Env(tmp_path / "q")
    out = e.o.submit(orl._read_req("t4"))
    assert out["loop_id"] not in e.o.tracers  # منتهية ⇒ مطرودة من الذاكرة
    e.restart()
    t = e.o.trace(out["loop_id"])
    assert t["loop_id"] == out["loop_id"] and t["span_count"] > 0
    assert e.o.trace("nope")["ok"] is False


def test_t5_corrupt_trace_file_is_no_trace(tmp_path):
    e = qr.Env(tmp_path / "q")
    out = e.o.submit(orl._read_req("t5"))
    p = Path(e.o.data_dir) / "traces" / f"{out['loop_id']}.json"
    p.write_text("{not json", encoding="utf-8")
    assert e.o.trace(out["loop_id"])["ok"] is False


def test_t6_persist_failure_does_not_break_loop(tmp_path, monkeypatch):
    e = qr.Env(tmp_path / "q")
    monkeypatch.setattr(e.o.traces, "save", lambda s: (_ for _ in ()).throw(OSError("disk")))
    out = e.o.submit(orl._read_req("t6"))
    assert out["status"] == "completed" and out["loop_id"] in e.o.tracers


# ===================================================================== الجاهزية
def test_hc1_queue_checks(tmp_path):
    st = JobStore(str(tmp_path / "j.db"), max_depth=10)
    rep = oh.report(oh.check_queue(st, [], False))
    assert rep["status"] == "ok"
    assert oh.report(oh.check_queue(st, [], True))["status"] == "failing"
    assert oh.report(oh.check_queue(st, [{"alive": True}], True))["status"] == "ok"

    class Broken:
        def stats(self):
            raise OSError("/secret/path")
    r = oh.check_queue(Broken(), [], False)
    assert r[0]["status"] == "failing" and "/secret" not in r[0]["reason"]


def test_hc2_notification_backlog(tmp_path):
    now = [10_000.0]
    st = OutboxStore(str(tmp_path / "o.db"), clock=lambda: now[0])
    st.emit(nev.make("job.dead", "k1", "s", "x"), [("webhook", "pending", "")])
    assert oh.report(oh.check_notifications(st, True, True, [], now=now[0] + 10))["status"] == "ok"
    rep = oh.report(oh.check_notifications(st, True, True, [], now=now[0] + 601))
    assert rep["status"] == "degraded"
    assert oh.report(oh.check_notifications(st, False, True, []))["status"] == "failing"


def test_hc3_disk():
    from collections import namedtuple
    U = namedtuple("U", "total used free")
    assert oh.check_disk("/", lambda p: U(100, 50, 50))[0]["status"] == "ok"
    assert oh.check_disk("/", lambda p: U(100, 97, 3))[0]["status"] == "degraded"
    assert oh.check_disk("/", lambda p: U(100, 99.5, 0.5))[0]["status"] == "failing"
    assert oh.check_disk("/", lambda p: 1 / 0)[0]["status"] == "degraded"


def test_hc4_health_events_registered():
    assert nev.EVENTS["health.failing"][0] == "critical"
    assert nev.EVENTS["health.degraded"][0] == "high"


def test_hc5_watcher_survives_broken_checks():
    import threading
    w = oh.HealthWatcher(lambda: 1 / 0, lambda ev: None)
    stop = threading.Event()
    stop.set()
    w.loop(stop, 0.01)  # يخرج فورًا بلا استثناء
    with pytest.raises(ZeroDivisionError):
        w.tick()


def test_hc6_watch_disabled_by_env(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_HEALTH_WATCH_S", "0")
    assert "معطل" in osvc.start_watcher()


# ===================================================================== الواجهة
@pytest.fixture
def api(monkeypatch):
    reg = om.Registry()
    r = oapi.make_router(registry=lambda: reg, checks=lambda: [oh._r("x", "ok", "")],
                         owner_ok=lambda k: k == OWNER_KEY, summary=lambda: {"s": 1})
    return orl._client(reg, extra=[r]), reg


def test_api1_metrics_auth(api, monkeypatch):
    c, _ = api
    assert c.get("/metrics").status_code == 401
    assert c.get("/metrics", headers=H).status_code == 200
    monkeypatch.setenv("SOVEREIGN_METRICS_TOKEN", "short")
    assert c.get("/metrics", headers={"Authorization": "Bearer short"}).status_code == 401
    monkeypatch.setenv("SOVEREIGN_METRICS_TOKEN", "t" * 20)
    assert c.get("/metrics", headers={"Authorization": "Bearer " + "t" * 20}).status_code == 200
    assert c.get("/metrics", headers={"Authorization": "Basic " + "t" * 20}).status_code == 401


def test_api2_health_and_summary(api):
    c, _ = api
    r = c.get("/observability/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert c.get("/observability/summary").status_code == 401
    assert c.get("/observability/summary", headers=H).json() == {"s": 1}


def test_suite_registered_and_green():
    s = suites.get("observability.reliability")
    assert s.floor == 1.0 and s.data_path.name == "observability_cases.json"
    r = s.runner(s.data_path)
    assert r["score"] == 1.0 and r["n"] == 19, r["failures"]


def test_app_wiring():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.status_code == 200 and len(r.headers["x-request-id"]) == 32
        assert c.get("/metrics").status_code == 401
        m = c.get("/metrics", headers=H)
        assert m.status_code == 200 and "http_requests_total" in m.text
        assert "queue_depth" in m.text and "obs_health_status" in m.text
        h = c.get("/observability/health")
        assert h.status_code in (200, 503) and {x["check"] for x in h.json()["checks"]} >= {
            "queue.workers", "notifications.channels", "disk"}
        assert c.get("/observability/summary", headers=H).json()["health"]["status"]
        from agent_orchestrator.api_routes import get_orchestrator
        assert any(getattr(f, "r846", False) for f in get_orchestrator().observers)


def test_l4_exc_info_preserved_and_formatted_text_scrubbed():
    """انحدار التقطه الجناح الكامل: المرشّح كان يمسح exc_info فيُخفي المكدس."""
    lg, buf = _capture(logging.Formatter("%(message)s"), "l4")
    seen = []

    class Keep(logging.Handler):
        def emit(self, record):
            seen.append(record)
    k = Keep()
    k.addFilter(olog.ScrubFilter())
    lg.addHandler(k)
    try:
        raise RuntimeError(f"x {SECRET}")
    except RuntimeError:
        lg.exception("boom")
    assert seen and seen[0].exc_info is not None
    assert SECRET not in buf.getvalue() and "RuntimeError" in buf.getvalue()
