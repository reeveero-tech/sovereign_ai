# -*- coding: utf-8 -*-
"""R-846: مجموعة موثوقية الرصد — سيناريوهات فوق المكونات الحقيقية.

المزيف هنا: الشبكة (نقل المنسق من R-844)، والساعة، وحالة العمال (قائمة
بعامل ميت). الوسيط والسجل والسجلات والآثار والفحوص ومراقب الجاهزية
والصندوق ونقاط ``/metrics`` و``/observability/health`` كلها حقيقية. كل حالة
تبني سجل مقاييس خاصًا بها ولا تلمس السجل العام للعملية.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List

from . import notify_reliability as nr
from . import queue_reliability as qr

try:
    from agent_orchestrator import runtime as orch_runtime, schemas
    from job_queue.store import JobStore
    from notifications import channels as nch
    from notifications import service as nsvc
    from notifications.store import OutboxStore
    from observability import api_routes as oapi, context as octx, health as oh
    from observability import logs as olog, metrics as om, service as osvc
    from observability.http import ObservabilityMiddleware
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.agent_orchestrator import runtime as orch_runtime, schemas
    from backend.job_queue.store import JobStore
    from backend.notifications import channels as nch
    from backend.notifications import service as nsvc
    from backend.notifications.store import OutboxStore
    from backend.observability import api_routes as oapi, context as octx, health as oh
    from backend.observability import logs as olog, metrics as om, service as osvc
    from backend.observability.http import ObservabilityMiddleware

OWNER = "owner-key-for-observability-suite"
METRICS_TOKEN = "m" * 24
SECRET = "ghp_" + "Z9" * 15
_RID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_LINE_RE = re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{([^}]*)\})? (-?[0-9.e+-]+|\+Inf|-Inf|NaN)$')


# ===================================================================== أدوات
def _client(reg: om.Registry, checks=None, extra=None):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()

    @app.get("/items/{item_id}")
    def _item(item_id: str):
        return {"id": item_id}

    for r in extra or []:
        app.include_router(r)
    app.add_middleware(ObservabilityMiddleware, root_app=app, registry=lambda: reg)
    return TestClient(app)


def _router(reg: om.Registry, checks=None):
    return oapi.make_router(registry=lambda: reg,
                            checks=checks or (lambda: []),
                            owner_ok=lambda k: k == OWNER,
                            summary=lambda: {})


def _series(reg: om.Registry, name: str) -> List[Dict[str, str]]:
    met = reg._metrics.get(name)
    if met is None:
        return []
    with met._lock:
        return [dict(zip(met.labelnames, k)) for k in met._series]


def _read_req(session: str) -> Dict[str, Any]:
    return schemas.new_request(user_id="t", session_id=session,
                               permissions=["orchestrator:write"],
                               utterance=qr.READ["utterance"])


@contextmanager
def _env(**kv):
    saved = {k: os.environ.get(k) for k in kv}
    try:
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ===================================================================== HTTP
def s_request_id_generated(tmp: Path) -> Dict[str, Any]:
    c = _client(om.Registry())
    a, b = c.get("/items/1").headers.get("x-request-id"), c.get("/items/2").headers.get("x-request-id")
    return {"has_header": bool(a and b), "valid_format": bool(a and b and _RID_RE.match(a)
                                                              and _RID_RE.match(b)),
            "distinct": bool(a and b and a != b)}


def s_request_id_propagated(tmp: Path) -> Dict[str, Any]:
    c = _client(om.Registry())
    good = "upstream-req.1234"
    kept = c.get("/items/1", headers={"X-Request-ID": good}).headers.get("x-request-id")
    bad = c.get("/items/1", headers={"X-Request-ID": "x\"; DROP <script>"}).headers.get("x-request-id")
    long_ = c.get("/items/1", headers={"X-Request-ID": "a" * 100}).headers.get("x-request-id")
    return {"kept": kept == good,
            "replaced_invalid": bool(bad) and "<" not in bad and bool(_RID_RE.match(bad)),
            "replaced_long": bool(long_) and long_ != "a" * 100 and bool(_RID_RE.match(long_))}


def s_route_template_label(tmp: Path) -> Dict[str, Any]:
    reg = om.Registry()
    c = _client(reg)
    c.get("/items/111")
    c.get("/items/222")
    s = _series(reg, "http_requests_total") + _series(reg, "http_request_duration_seconds")
    # قيم الوسوم وحدها — البحث في النص كله التقط "111" من أرقام الزمن (مثل 0.00111)
    # فتذبذبت الحالة في CI (R-846، خلل قياس لا خلل كود)
    vals = [v for lbl in s for v in lbl.values()]
    return {"series": len(_series(reg, "http_requests_total")),
            "route": s[0]["route"] if s else None,
            "ids_in_labels": any("111" in v or "222" in v for v in vals)}


def s_unmatched_single_series(tmp: Path) -> Dict[str, Any]:
    reg = om.Registry()
    c = _client(reg)
    for i in range(60):
        c.get(f"/scan/{i}/wp-admin.php")
    routes = {x["route"] for x in _series(reg, "http_requests_total")}
    return {"route_series": len(routes), "route": next(iter(routes)) if len(routes) == 1 else None}


# ===================================================================== المقاييس
def s_cardinality_cap(tmp: Path) -> Dict[str, Any]:
    reg = om.Registry()
    ctr = reg.counter("t_events_total", "اختبار", ["key"])
    # عدد ثابت والسقف من العقد الموثق (200) لا من الثابت نفسه — طفرة رفع السقف
    # كشفت أن ربط الحلقة بالثابت يحوّل الحالة إلى مليار إدخال (R-846، أول طفرة)
    n, contract_cap = 500, 200
    for i in range(n):
        ctr.inc({"key": f"k{i}"})
    over = reg.overflow.value({"metric": "t_events_total"})
    return {"series_le_cap": ctr.series_count() <= contract_cap + 1,
            "overflow_counted": over == n - contract_cap
            and ctr.value({"key": om.OVERFLOW}) == n - contract_cap}


def _parse(text: str):
    samples, ok = [], True
    for line in text.splitlines():
        if not line or line.startswith("#"):
            if line.startswith("#") and not re.match(r"^# (HELP|TYPE) [a-zA-Z_:][a-zA-Z0-9_:]* ", line):
                ok = False
            continue
        mt = _LINE_RE.match(line)
        if not mt:
            ok = False
            continue
        labels = dict(re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"', mt.group(3) or ""))
        samples.append((mt.group(1), labels, float(mt.group(4).replace("+Inf", "inf"))))
    return ok, samples


def s_exposition_valid(tmp: Path) -> Dict[str, Any]:
    reg = om.Registry()
    h = reg.histogram("t_latency_seconds", "اختبار", ["op"])
    for v in (0.001, 0.02, 0.02, 0.3, 4.0, 100.0):
        h.observe({"op": 'a"b\\c'}, v)
    reg.counter("t_total", "اختبار").inc()
    ok, samples = _parse(reg.render())
    buckets = [(lb["le"], v) for n, lb, v in samples if n == "t_latency_seconds_bucket"]
    vals = [v for _, v in buckets]
    count = next((v for n, _, v in samples if n == "t_latency_seconds_count"), None)
    inf = next((v for le, v in buckets if le == "+Inf"), None)
    return {"parse_ok": ok and bool(samples),
            "buckets_monotonic": bool(vals) and all(a <= b for a, b in zip(vals, vals[1:])),
            "inf_equals_count": inf is not None and inf == count == 6}


def s_metrics_auth(tmp: Path) -> Dict[str, Any]:
    reg = om.Registry()
    with _env(SOVEREIGN_METRICS_TOKEN=METRICS_TOKEN):
        c = _client(reg, extra=[_router(reg)])
        r_key = c.get("/metrics", headers={"X-API-Key": OWNER})
        return {"no_key": c.get("/metrics").status_code,
                "wrong_bearer": c.get("/metrics", headers={
                    "Authorization": "Bearer " + "x" * 24}).status_code,
                "key": r_key.status_code,
                "bearer": c.get("/metrics", headers={
                    "Authorization": f"Bearer {METRICS_TOKEN}"}).status_code,
                "content_type_ok": r_key.headers.get("content-type", "").startswith(
                    "text/plain; version=0.0.4")}


def s_broken_collector(tmp: Path) -> Dict[str, Any]:
    reg = om.Registry()
    reg.counter("t_alive_total", "اختبار").inc()

    def boom():
        raise RuntimeError("collector down")
    reg.register_collector("boom", boom)
    reg.register_collector("fine", lambda: [("t_fine", "gauge", "اختبار", {}, 7)])
    c = _client(reg, extra=[_router(reg)])
    r = c.get("/metrics", headers={"X-API-Key": OWNER})
    return {"status": r.status_code,
            "collector_errors": int(reg.collector_errors.value({"collector": "boom"})),
            "other_metrics_present": "t_alive_total 1" in r.text and "t_fine 7" in r.text}


# ===================================================================== السجلات
def _logger(name: str, fmt: logging.Formatter):
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setFormatter(fmt)
    lg = logging.getLogger(f"r846.eval.{name}")
    lg.handlers[:] = [h]
    lg.propagate = False
    lg.setLevel(logging.INFO)
    olog.install_logging(root=lg)
    return lg, buf


def s_log_secret_scrubbed(tmp: Path) -> Dict[str, Any]:
    lg, buf = _logger("plain", logging.Formatter("%(levelname)s %(message)s"))
    jl, jbuf = _logger("json", olog.JsonFormatter())
    lg.warning("فشل الاتصال بالرمز %s", SECRET)
    jl.warning("فشل الاتصال بالرمز %s", SECRET)
    try:
        raise RuntimeError(f"auth failed token={SECRET}")
    except RuntimeError:
        lg.exception("استثناء")
        jl.exception("استثناء")
    plain, js = buf.getvalue(), jbuf.getvalue()
    return {"plain_leak": SECRET in plain.split("Traceback")[0],
            "json_leak": SECRET in js,
            "exc_leak": SECRET in plain or "Traceback" not in plain}


def s_json_log_context(tmp: Path) -> Dict[str, Any]:
    jl, buf = _logger("ctx", olog.JsonFormatter())
    with octx.bind(request_id="req-abcdef12", loop_id="loop-1234"):
        # WARNING لا INFO: بوابة التقييم تعطل INFO عالميًا (logging.disable) — اكتُشف في أول تشغيل
        jl.warning("حدث داخل طلب")
    try:
        rec = json.loads(buf.getvalue().strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"valid_json": False, "request_id": False, "loop_id": False}
    return {"valid_json": True, "request_id": rec.get("request_id") == "req-abcdef12",
            "loop_id": rec.get("loop_id") == "loop-1234"}


# ===================================================================== الآثار
def s_trace_survives_restart(tmp: Path) -> Dict[str, Any]:
    e = qr.Env(tmp / "q")
    out = e.o.submit(_read_req("o10"))
    before = e.o.trace(out["loop_id"])
    e.restart()
    after = e.o.trace(out["loop_id"])
    ids = lambda t: [s["span_id"] for s in t.get("spans", [])]
    return {"before_ok": "error" not in before and before.get("span_count", 0) > 0,
            "after_ok": "error" not in after and after.get("span_count", 0) > 0,
            "same_spans": bool(ids(before)) and ids(before) == ids(after)}


def s_trace_memory_bounded(tmp: Path) -> Dict[str, Any]:
    e = qr.Env(tmp / "q")
    first = None
    for i in range(orch_runtime.MAX_TRACERS + 25):
        out = e.o.submit(schemas.new_request(
            user_id="t", session_id=f"o11-{i}", permissions=["orchestrator:write"],
            utterance=qr._write(f"o11-{i}", f"o11-{i}")["utterance"]))
        first = first or out["loop_id"]
    t = e.o.trace(first)
    return {"tracers_le_cap": len(e.o.tracers) <= orch_runtime.MAX_TRACERS,
            "evicted_trace_ok": first not in e.o.tracers and "error" not in t
            and t.get("loop_id") == first}


def s_trace_resume_keeps_history(tmp: Path) -> Dict[str, Any]:
    e = qr.Env(tmp / "q")
    out = e.o.submit(nr._req("o12", "o12-title"))
    before = e.o.trace(out["loop_id"]).get("span_count", 0)
    e.restart()
    ap = out.get("pending_approval") or {}
    res = e.o.decide_approval(out["loop_id"], ap.get("approval_id", ""), "approved", "owner")
    t = e.o.trace(out["loop_id"])
    return {"loop": res.get("status"), "spans_grew": t.get("span_count", 0) > before,
            "has_approval_decision": any(d.get("decision_type") == "approval"
                                         for d in t.get("decisions", []))}


def s_trace_secret_on_disk(tmp: Path) -> Dict[str, Any]:
    e = qr.Env(tmp / "q")
    out = e.o.submit(nr._req("o13", f"issue-{SECRET}"))
    # الموافقة ثم التنفيذ: حلقة معلّقة لا امتداد لها بعد، فالسر لا يدخل الأثر
    # أصلًا — طفرة إلغاء التنقية النجت بهذا (R-846). الامتداد يحمل المدخلات.
    ap = out.get("pending_approval") or {}
    e.o.decide_approval(out["loop_id"], ap.get("approval_id", ""), "approved", "owner")
    files = list((Path(e.o.data_dir) / "traces").glob("*.json"))
    raw = "".join(f.read_text(encoding="utf-8") for f in files)
    t = e.o.trace(out["loop_id"])
    return {"leak_on_disk": SECRET in raw or not files,
            "trace_ok": "error" not in t and t.get("loop_id") == out["loop_id"]}


# ===================================================================== الجاهزية
def _dead_worker_checks(tmp: Path):
    store = JobStore(str(tmp / "hq.sqlite3"), max_depth=100)
    return lambda: oh.check_queue(store, [{"worker_id": "w1", "alive": False}], True)


def _non_ok(rep):
    return next((c["check"] for c in rep["checks"] if c["status"] != oh.OK), None)


def s_health_dead_worker(tmp: Path) -> Dict[str, Any]:
    checks = _dead_worker_checks(tmp)
    rep = oh.report(checks())
    reg = om.Registry()
    c = _client(reg, extra=[_router(reg, checks)])
    return {"status": rep["status"], "check": _non_ok(rep),
            "http": c.get("/observability/health").status_code}


def s_health_saturation(tmp: Path) -> Dict[str, Any]:
    store = JobStore(str(tmp / "sat.sqlite3"), max_depth=10)
    for i in range(9):
        store.enqueue("orchestrator.loop", {"i": i, **qr.READ}, f"sat-{i}", "owner", 3, 60.0)
    rep = oh.report(oh.check_queue(store, [], False))
    return {"status": rep["status"], "check": _non_ok(rep)}


def s_health_channel_disabled(tmp: Path) -> Dict[str, Any]:
    with nr._env():
        store = OutboxStore(str(tmp / "ob.sqlite3"))
        chans = nch.all_channels()
        hook = next(c for c in chans if c.name == "webhook")
        store.disable_channel(hook.name, "auth: 401", hook.fingerprint())
        rep = oh.report(oh.check_notifications(store, False, False, chans))
    return {"status": rep["status"], "check": _non_ok(rep)}


def s_health_watcher_notifies_once(tmp: Path) -> Dict[str, Any]:
    store = OutboxStore(str(tmp / "ob.sqlite3"))
    w = oh.HealthWatcher(_dead_worker_checks(tmp), lambda ev: nsvc.safe_emit(ev, store, []),
                         clock=lambda: 7_200_000.0)
    w.tick()
    first = store.list(limit=50)
    w.tick()
    return {"notifications": len(first), "event": first[0]["event"] if first else None,
            "after_second_tick": len(store.list(limit=50))}


def s_loop_metrics(tmp: Path) -> Dict[str, Any]:
    reg = om.Registry()
    e = qr.Env(tmp / "q")
    e.o.observers.append(osvc.loop_observer(reg))
    e.o.submit(nr._req("o18", "o18-title"))
    e.o.submit(_read_req("o18-read"))
    ctr = reg.counter("orchestrator_loops_total", "x", ["status"])
    return {"pending_approval": int(ctr.value({"status": "pending_approval"})),
            "completed": int(ctr.value({"status": "completed"}))}


SCENARIOS = {f.__name__[2:]: f for f in (
    s_request_id_generated, s_request_id_propagated, s_route_template_label,
    s_unmatched_single_series, s_cardinality_cap, s_exposition_valid, s_metrics_auth,
    s_log_secret_scrubbed, s_json_log_context, s_trace_survives_restart,
    s_trace_memory_bounded, s_trace_resume_keeps_history, s_trace_secret_on_disk,
    s_health_dead_worker, s_health_saturation, s_health_channel_disabled,
    s_health_watcher_notifies_once, s_loop_metrics, s_broken_collector)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r846-o-"))
    try:
        try:
            got = SCENARIOS[case["scenario"]](tmp)
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
