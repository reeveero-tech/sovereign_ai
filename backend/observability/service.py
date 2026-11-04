# -*- coding: utf-8 -*-
"""R-846: ربط الرصد بالمكونات — مراقبون، خطافات، جامعون، ومراقب الجاهزية.

البيئة:
- ``SOVEREIGN_LOG_FORMAT=json``: سجلات JSON (الافتراضي نصي).
- ``SOVEREIGN_METRICS_TOKEN``: رمز Bearer لقراءة ``/metrics`` من جامع خارجي
  (16 حرفًا على الأقل؛ وإلا يُقبل ``X-API-Key`` فقط).
- ``SOVEREIGN_HEALTH_WATCH_S``: دورة مراقب الجاهزية بالثواني (افتراضي 60، 0 يعطله).

قاعدة الربط: الرصد لا يكسر ما يرصده. عطل مراقب أو جامع يُسجَّل ويُعدّ.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Iterable, List, Optional

from . import health
from . import metrics as m

_log = logging.getLogger("observability")
_WATCH: Dict[str, Any] = {}
_LOCK = threading.Lock()


def _deps():
    try:
        from agent_orchestrator.api_routes import get_orchestrator
        from job_queue import service as jq
        from notifications import service as nt, channels as ch
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.agent_orchestrator.api_routes import get_orchestrator
        from backend.job_queue import service as jq
        from backend.notifications import service as nt, channels as ch
    return get_orchestrator, jq, nt, ch


def loop_observer(registry: Optional[m.Registry] = None):
    def _obs(view: Dict[str, Any]) -> None:
        (registry or m.registry()).counter("orchestrator_loops_total", "حلقات المنسق حسب الحالة عند كل نهاية/تعليق",
                             ["status"]).inc({"status": str(view.get("status") or "?")})
    _obs.r846 = True
    return _obs


def job_hook(registry: Optional[m.Registry] = None):
    def _hook(job: Dict[str, Any]) -> None:
        (registry or m.registry()).counter("queue_jobs_finished_total", "مهام الطابور المنتهية حسب النوع والحالة",
                             ["kind", "status"]).inc(
            {"kind": str(job.get("kind") or "?"), "status": str(job.get("status") or "?")})
    _hook.r846 = True
    return _hook


def _queue_collector(jq) -> Iterable[m.Sample]:
    st = jq.get_store().stats()
    for status, n in st["counts"].items():
        yield ("queue_jobs", "gauge", "مهام الطابور حسب الحالة", {"status": status}, n)
    yield ("queue_depth", "gauge", "عمق الطابور (queued+running)", {}, st["depth"])
    yield ("queue_max_depth", "gauge", "سقف عمق الطابور", {}, st["max_depth"])
    yield ("queue_oldest_queued_age_seconds", "gauge", "عمر أقدم مهمة منتظرة", {},
           st["oldest_queued_age_s"])
    ws = jq.workers_status()
    yield ("queue_workers_alive", "gauge", "عمال الطابور الأحياء", {},
           sum(1 for w in ws if w["alive"]))


def _notify_collector(nt) -> Iterable[m.Sample]:
    st = nt.get_store().stats()
    for status, n in st["deliveries"].items():
        yield ("notify_deliveries", "gauge", "تسليمات الإشعارات حسب الحالة", {"status": status}, n)
    yield ("notify_unread", "gauge", "إشعارات غير مقروءة", {}, st["unread"])
    yield ("notify_channels_disabled", "gauge", "قنوات معطلة آليًا", {},
           len(st["disabled_channels"]))
    yield ("notify_dispatcher_running", "gauge", "الموزع حي (1/0)", {},
           1 if nt.dispatcher_status()["running"] else 0)


def _health_collector() -> Iterable[m.Sample]:
    for c in health.live_checks():
        yield ("obs_health_status", "gauge", "حالة كل فحص: 0 سليم، 1 متدهور، 2 فاشل",
               {"check": c["check"]}, health.LEVEL.get(c["status"], 2))


def install(orchestrator=None, registry: Optional[m.Registry] = None) -> str:
    """ربط الرصد — مرة واحدة (idempotent)."""
    get_orchestrator, jq, nt, _ch = _deps()
    reg = registry or m.registry()
    o = orchestrator or get_orchestrator()
    if not any(getattr(f, "r846", False) for f in o.observers):
        o.observers.append(loop_observer())
    if not any(getattr(f, "r846", False) for f in jq.FINISH_HOOKS):
        jq.FINISH_HOOKS.append(job_hook())
    reg.register_collector("queue", lambda: _queue_collector(jq))
    reg.register_collector("notifications", lambda: _notify_collector(nt))
    reg.register_collector("health", _health_collector)
    return "الرصد: مراقبو المنسق والطابور + جامعو الطابور والإشعارات والجاهزية"


def watcher() -> health.HealthWatcher:
    _g, _jq, nt, _ch = _deps()
    return health.HealthWatcher(health.live_checks, lambda ev: nt.safe_emit(ev))


def start_watcher() -> str:
    try:
        from runtime.threads import start_managed
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.runtime.threads import start_managed
    raw = os.environ.get("SOVEREIGN_HEALTH_WATCH_S", "60").strip()
    try:
        interval = max(0, min(int(raw or "60"), 3600))
    except ValueError:
        _log.warning("R-846: SOVEREIGN_HEALTH_WATCH_S=%r غير صالح — الافتراضي 60", raw)
        interval = 60
    if interval == 0:
        return "الرصد: مراقب الجاهزية معطل (SOVEREIGN_HEALTH_WATCH_S=0)"
    with _LOCK:
        t = _WATCH.get("thread")
        if t is not None and t.is_alive():
            return "الرصد: مراقب الجاهزية يعمل مسبقًا"
        w, stop = watcher(), threading.Event()
        t = start_managed(lambda: w.loop(stop, float(interval)), name="health-watcher",
                          stop_event=stop)
        if t is None:
            return "الرصد: خيوط الخلفية معطلة — /observability/health عند الطلب فقط"
        _WATCH.update(thread=t, stop=stop, watcher=w)
    return f"الرصد: مراقب الجاهزية كل {interval}ث"


def watcher_status() -> Dict[str, Any]:
    t = _WATCH.get("thread")
    w = _WATCH.get("watcher")
    return {"running": bool(t is not None and t.is_alive()),
            "last": {k: v for k, v in (w.last if w else {}).items() if k != "checks"}}


def summary() -> Dict[str, Any]:
    rep = health.report(health.live_checks())
    return {"health": rep, "watcher": watcher_status(), "metrics": m.registry().snapshot()}
