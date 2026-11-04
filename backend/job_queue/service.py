# -*- coding: utf-8 -*-
"""R-844: تجميع الطابور — المخزن المشترك وعمال الخلفية من البيئة.

البيئة:
- ``SOVEREIGN_QUEUE_DB``: مسار قاعدة الطابور (الافتراضي DATA_DIR/queue/jobs.sqlite3).
- ``SOVEREIGN_QUEUE_MAX_DEPTH``: حد المهام النشطة (افتراضي 100، بين 1 و10000).
- ``SOVEREIGN_QUEUE_WORKERS``: عدد العمال (افتراضي 1، و0 يعطلهم، والسقف 4).
  السقف 4 لأن الخادم عملية uvicorn واحدة والحلقات تحجز الخيط.
- ``SOVEREIGN_QUEUE_POLL_S``: فاصل الاستطلاع عند الفراغ (افتراضي 1ث).
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional

from . import kinds
from .store import JobStore
from .worker import Worker

_log = logging.getLogger("job_queue")
_STORE: Optional[JobStore] = None
_WORKERS: List[Dict[str, Any]] = []
_LOCK = threading.Lock()
MAX_WORKERS = 4
# R-845: مراقبو انتهاء المهام (الإشعارات تسجل هنا عبر notifications.service.install)
FINISH_HOOKS: List[Any] = []


def _int_env(name: str, default: int, lo: int, hi: int) -> int:
    raw = os.environ.get(name, "")
    try:
        v = int(raw) if raw.strip() else default
    except ValueError:
        _log.warning("R-844: %s=%r غير صالح — الافتراضي %s", name, raw, default)
        v = default
    return max(lo, min(v, hi))


def _db_path() -> str:
    p = os.environ.get("SOVEREIGN_QUEUE_DB", "").strip()
    if p:
        return p
    try:
        from config import DATA_DIR
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.config import DATA_DIR
    return os.path.join(str(DATA_DIR), "queue", "jobs.sqlite3")


def get_store() -> JobStore:
    global _STORE
    with _LOCK:
        if _STORE is None:
            _STORE = JobStore(_db_path(), max_depth=_int_env(
                "SOVEREIGN_QUEUE_MAX_DEPTH", 100, 1, 10000))
        return _STORE


def reset_for_tests() -> None:
    global _STORE
    with _LOCK:
        _STORE = None


def start_workers() -> str:
    """تشغيل عمال الخلفية — يعيد سببًا معلنًا (يُسجَّل في الإقلاع)."""
    try:
        from runtime.threads import start_managed
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.runtime.threads import start_managed
    n = _int_env("SOVEREIGN_QUEUE_WORKERS", 1, 0, MAX_WORKERS)
    if n == 0:
        return "الطابور: العمال معطلون (SOVEREIGN_QUEUE_WORKERS=0) — /queue/drain يدويًا"
    poll = float(_int_env("SOVEREIGN_QUEUE_POLL_S", 1, 1, 60))
    store = get_store()
    started = 0
    for i in range(n):
        w = Worker(store, on_finish=FINISH_HOOKS)
        stop = threading.Event()
        t = start_managed(lambda w=w, stop=stop: w.loop(stop, poll),
                          name=f"job-queue-{i}", stop_event=stop)
        if t is not None:
            _WORKERS.append({"worker_id": w.worker_id, "thread": t, "stop": stop})
            started += 1
    if started == 0:
        return "الطابور: خيوط الخلفية معطلة في هذه البيئة — /queue/drain يدويًا"
    return f"الطابور: {started} عامل(ة) — قاعدة {store.path}"


def workers_status() -> List[Dict[str, Any]]:
    return [{"worker_id": w["worker_id"], "alive": w["thread"].is_alive()}
            for w in _WORKERS]


def kinds_public() -> List[Dict[str, Any]]:
    return [k.public() for k in kinds.KINDS.values()]
