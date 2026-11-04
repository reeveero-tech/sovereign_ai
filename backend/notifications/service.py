# -*- coding: utf-8 -*-
"""R-845: تجميع الإشعارات — المخزن المشترك، والإصدار، والربط، والموزع.

البيئة:
- ``SOVEREIGN_NOTIFY_DB``: مسار الصندوق (الافتراضي DATA_DIR/notifications/outbox.sqlite3).
- ``SOVEREIGN_NOTIFY_MIN_SEVERITY``: أدنى شدة للقنوات الخارجية (افتراضي high)،
  ولكل قناة ``SOVEREIGN_NOTIFY_<CHANNEL>_MIN_SEVERITY``. الصندوق الداخلي يتلقى كل شيء.
- ``SOVEREIGN_NOTIFY_MAX_PER_HOUR``: حد الإرسال لكل قناة (افتراضي 30، من 1 إلى 1000).
- ``SOVEREIGN_NOTIFY_DISPATCH``: 0 يعطل موزع الخلفية (التصريف يدويًا).
- ``SOVEREIGN_NOTIFY_WEBHOOK_URL`` + ``SOVEREIGN_NOTIFY_WEBHOOK_SECRET``.
- ``SOVEREIGN_TELEGRAM_BOT_TOKEN`` + ``SOVEREIGN_TELEGRAM_CHAT_ID``.
- ``SOVEREIGN_PUBLIC_URL``: بادئة https للروابط في الإشعار (اختياري).

قاعدة الربط: الإصدار لا يكسر المُصدِر أبدًا. أي عطل في الإشعارات يُسجَّل،
والحلقة أو المهمة تكمل كما لو لم تكن هناك إشعارات.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from . import channels as ch_mod
from . import events
from .dispatcher import Dispatcher
from .store import OutboxStore

_log = logging.getLogger("notifications")
_STORE: Optional[OutboxStore] = None
_LOCK = threading.Lock()
_DISPATCHER: Dict[str, Any] = {}


def _int_env(name: str, default: int, lo: int, hi: int) -> int:
    raw = os.environ.get(name, "")
    try:
        v = int(raw) if raw.strip() else default
    except ValueError:
        _log.warning("R-845: %s=%r غير صالح — الافتراضي %s", name, raw, default)
        v = default
    return max(lo, min(v, hi))


def _db_path() -> str:
    p = os.environ.get("SOVEREIGN_NOTIFY_DB", "").strip()
    if p:
        return p
    try:
        from config import DATA_DIR
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.config import DATA_DIR
    return os.path.join(str(DATA_DIR), "notifications", "outbox.sqlite3")


def get_store() -> OutboxStore:
    global _STORE
    with _LOCK:
        if _STORE is None:
            _STORE = OutboxStore(_db_path())
        return _STORE


def reset_for_tests() -> None:
    global _STORE
    with _LOCK:
        _STORE = None


def dispatcher(store: Optional[OutboxStore] = None) -> Dispatcher:
    return Dispatcher(store or get_store(),
                      max_per_hour=_int_env("SOVEREIGN_NOTIFY_MAX_PER_HOUR", 30, 1, 1000))


def emit(ev: Dict[str, Any], store: Optional[OutboxStore] = None,
         chans: Optional[List[ch_mod.Channel]] = None) -> Tuple[Dict[str, Any], bool]:
    """إشعار في الصندوق + تسليم لكل قناة خارجية (pending أو skipped بسبب)."""
    st = store or get_store()
    deliveries = []
    for ch in (chans if chans is not None else ch_mod.all_channels()):
        status, reason = ch_mod.eligible(ch, ev["severity"])
        deliveries.append((ch.name, status, reason))
    return st.emit(ev, deliveries)


def safe_emit(ev: Optional[Dict[str, Any]], store: Optional[OutboxStore] = None,
              chans: Optional[List[ch_mod.Channel]] = None) -> Optional[Dict[str, Any]]:
    if ev is None:
        return None
    try:
        return emit(ev, store, chans)[0]
    except Exception as exc:  # TOLERATED: الإشعار لا يكسر المُصدِر — يُسجَّل فقط
        _log.error("R-845: تعذر إصدار %s: %s", ev.get("event"), events.scrub(str(exc)))
        return None


def loop_observer(store: Optional[OutboxStore] = None, chans=None):
    """مراقب لحالة المنسق (يُسجَّل في ``OrchestratorSystem.observers``)."""
    def _obs(view: Dict[str, Any]) -> None:
        safe_emit(events.from_loop(view), store, chans)
    _obs.r845 = True
    return _obs


def job_observer(store: Optional[OutboxStore] = None, chans=None):
    """مراقب لانتهاء مهام الطابور (يُسجَّل في ``job_queue.service.FINISH_HOOKS``)."""
    def _obs(job: Dict[str, Any]) -> None:
        safe_emit(events.from_job(job), store, chans)
    _obs.r845 = True
    return _obs


def install(orchestrator=None) -> str:
    """ربط الإشعارات بالمنسق المشترك والطابور — مرة واحدة (idempotent)."""
    try:
        from agent_orchestrator.api_routes import get_orchestrator
        from job_queue import service as jq
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.agent_orchestrator.api_routes import get_orchestrator
        from backend.job_queue import service as jq
    o = orchestrator or get_orchestrator()
    if not any(getattr(f, "r845", False) for f in o.observers):
        o.observers.append(loop_observer())
    if not any(getattr(f, "r845", False) for f in jq.FINISH_HOOKS):
        jq.FINISH_HOOKS.append(job_observer())
    return "الإشعارات: مربوطة بالمنسق والطابور"


def start_dispatcher() -> str:
    try:
        from runtime.threads import start_managed
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.runtime.threads import start_managed
    if os.environ.get("SOVEREIGN_NOTIFY_DISPATCH", "1").strip() == "0":
        return "الإشعارات: الموزع معطل (SOVEREIGN_NOTIFY_DISPATCH=0) — /notifications/dispatch يدويًا"
    if _DISPATCHER.get("thread") is not None and _DISPATCHER["thread"].is_alive():
        return "الإشعارات: الموزع يعمل مسبقًا"
    d, stop = dispatcher(), threading.Event()
    t = start_managed(lambda: d.loop(stop, 2.0), name="notify-dispatcher", stop_event=stop)
    if t is None:
        return "الإشعارات: خيوط الخلفية معطلة في هذه البيئة — /notifications/dispatch يدويًا"
    _DISPATCHER.update(thread=t, stop=stop)
    configured = [c.name for c in ch_mod.all_channels() if c.configured()[0]]
    return f"الإشعارات: الموزع يعمل — القنوات المضبوطة: {configured or 'لا شيء (الصندوق الداخلي فقط)'}"


def dispatcher_status() -> Dict[str, Any]:
    t = _DISPATCHER.get("thread")
    return {"running": bool(t is not None and t.is_alive())}


def channels_public() -> List[Dict[str, Any]]:
    st = get_store()
    out = []
    for c in ch_mod.all_channels():
        p = c.public()
        p["disabled"] = st.channel_disabled(c.name, c.fingerprint())
        out.append(p)
    return out
