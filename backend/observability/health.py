# -*- coding: utf-8 -*-
"""R-846: الجاهزية الحقيقية — فحوص صريحة بدل «healthy» الثابت.

كل فحص دالة خالصة بتبعيات محقونة تعيد ``{check, status, reason}`` حيث
``status`` ∈ ok/degraded/failing. الحالة الكلية = أسوأ فحص. الأسباب لا
تحمل مسارات ولا أسرارًا (تُعرض على نقطة مفتوحة).

الفحوص:
- ``queue.store``: مخزن الطابور يُقرأ.
- ``queue.depth``: العمق/السقف ≥ 0.9 ⇒ degraded.
- ``queue.workers``: عمال متوقعون (العدد > 0 والخيوط مسموحة وبدأ التشغيل)
  وأحدهم ميت ⇒ failing.
- ``queue.dead_jobs``: مهام ماتت في آخر ساعة ⇒ degraded.
- ``notifications.dispatcher``: موزع متوقع وليس حيًا ⇒ failing.
- ``notifications.channels``: قناة معطلة آليًا ⇒ degraded.
- ``notifications.backlog``: أقدم تسليم معلّق > 600ث ⇒ degraded.
- ``disk``: حر < 5% ⇒ degraded، < 1% ⇒ failing.

``HealthWatcher.tick()`` يحوّل التدهور إلى إشعار للمالك — مرة واحدة لكل
(حالة، فحص، ساعة) بمفتاح عدم التكرار، لا سيل تنبيهات.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Any, Callable, Dict, List, Optional

_log = logging.getLogger("observability.health")

OK, DEGRADED, FAILING = "ok", "degraded", "failing"
LEVEL = {OK: 0, DEGRADED: 1, FAILING: 2}
DEPTH_RATIO = 0.9
BACKLOG_S = 600.0
DEAD_WINDOW_S = 3600.0


def _r(check: str, status: str, reason: str) -> Dict[str, str]:
    return {"check": check, "status": status, "reason": reason[:200]}


def worst(checks: List[Dict[str, str]]) -> str:
    return max((c["status"] for c in checks), key=lambda s: LEVEL.get(s, 2), default=OK)


# ------------------------------------------------------------ الطابور
def check_queue(store: Any, workers: List[Dict[str, Any]], workers_expected: bool,
                now: Optional[float] = None) -> List[Dict[str, str]]:
    now = time.time() if now is None else now
    out: List[Dict[str, str]] = []
    try:
        st = store.stats()
    except Exception as exc:  # TOLERATED: مخزن لا يُقرأ ⇒ failing صريح بنوع الخطأ
        return [_r("queue.store", FAILING, f"مخزن الطابور لا يُقرأ ({type(exc).__name__})")]
    out.append(_r("queue.store", OK, "مخزن الطابور يُقرأ"))
    depth, cap = int(st.get("depth", 0)), max(1, int(st.get("max_depth", 1)))
    ratio = depth / cap
    out.append(_r("queue.depth", DEGRADED if ratio >= DEPTH_RATIO else OK,
                  f"العمق {depth}/{cap} ({ratio:.0%})"))
    if workers_expected:
        dead = [w for w in workers if not w.get("alive")]
        if not workers:
            out.append(_r("queue.workers", FAILING, "عمال متوقعون ولا عامل مسجلًا"))
        elif dead:
            out.append(_r("queue.workers", FAILING, f"{len(dead)}/{len(workers)} عامل ميت"))
        else:
            out.append(_r("queue.workers", OK, f"{len(workers)} عامل حي"))
    else:
        out.append(_r("queue.workers", OK, "العمال غير متوقعين في هذه البيئة (تصريف يدوي)"))
    try:
        n = store.finished_since("dead", now - DEAD_WINDOW_S)
        out.append(_r("queue.dead_jobs", DEGRADED if n else OK,
                      f"{n} مهمة ميتة في آخر ساعة"))
    except Exception as exc:  # TOLERATED: عدّ الميتة تعذر ⇒ degraded معلن لا صمت
        out.append(_r("queue.dead_jobs", DEGRADED, f"تعذر العد ({type(exc).__name__})"))
    return out


# ------------------------------------------------------------ الإشعارات
def check_notifications(store: Any, dispatcher_running: bool, dispatcher_expected: bool,
                        channels: List[Any], now: Optional[float] = None
                        ) -> List[Dict[str, str]]:
    now = time.time() if now is None else now
    out: List[Dict[str, str]] = []
    if dispatcher_expected and not dispatcher_running:
        out.append(_r("notifications.dispatcher", FAILING, "الموزع متوقع وليس حيًا"))
    else:
        out.append(_r("notifications.dispatcher", OK,
                      "الموزع حي" if dispatcher_running else "الموزع غير متوقع (تصريف يدوي)"))
    try:
        disabled = [ch.name for ch in channels
                    if store.channel_disabled(ch.name, ch.fingerprint())]
        out.append(_r("notifications.channels", DEGRADED if disabled else OK,
                      f"قنوات معطلة: {disabled}" if disabled else "لا قناة معطلة"))
        oldest = store.oldest_pending_at()
        age = (now - oldest) if oldest else 0.0
        out.append(_r("notifications.backlog", DEGRADED if age > BACKLOG_S else OK,
                      f"أقدم تسليم معلّق منذ {int(age)}ث"))
    except Exception as exc:  # TOLERATED: صندوق لا يُقرأ ⇒ failing صريح بنوع الخطأ
        out.append(_r("notifications.store", FAILING,
                      f"صندوق الإشعارات لا يُقرأ ({type(exc).__name__})"))
    return out


# ------------------------------------------------------------ القرص
def check_disk(path: str, usage: Callable[[str], Any] = shutil.disk_usage
               ) -> List[Dict[str, str]]:
    try:
        u = usage(path)
        free = u.free / max(1, u.total)
    except Exception as exc:  # TOLERATED: تعذر القياس ⇒ degraded معلن
        return [_r("disk", DEGRADED, f"تعذر قياس القرص ({type(exc).__name__})")]
    st = FAILING if free < 0.01 else DEGRADED if free < 0.05 else OK
    return [_r("disk", st, f"الحر {free:.1%}")]


def report(checks: List[Dict[str, str]]) -> Dict[str, Any]:
    return {"status": worst(checks), "checks": checks, "ts": time.time()}


# ------------------------------------------------------------ التجميع الحي
def _imports():
    try:
        from job_queue import service as jq
        from notifications import service as nt, channels as ch
        from runtime.threads import background_threads_enabled
        from config import DATA_DIR
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.job_queue import service as jq
        from backend.notifications import service as nt, channels as ch
        from backend.runtime.threads import background_threads_enabled
        from backend.config import DATA_DIR
    return jq, nt, ch, background_threads_enabled, str(DATA_DIR)


def live_checks() -> List[Dict[str, str]]:
    """الفحوص على المكونات الحية للعملية الحالية."""
    jq, nt, ch, threads_on, data_dir = _imports()
    started = bool(_STATE.get("started"))
    want_workers = (started and threads_on()
                    and jq._int_env("SOVEREIGN_QUEUE_WORKERS", 1, 0, jq.MAX_WORKERS) > 0)
    want_disp = (started and threads_on()
                 and os.environ.get("SOVEREIGN_NOTIFY_DISPATCH", "1").strip() != "0")
    checks = check_queue(jq.get_store(), jq.workers_status(), want_workers)
    checks += check_notifications(nt.get_store(), nt.dispatcher_status()["running"],
                                  want_disp, ch.all_channels())
    checks += check_disk(data_dir if os.path.isdir(data_dir) else ".")
    return checks


_STATE: Dict[str, Any] = {}


def mark_started() -> None:
    """يُستدعى بعد إقلاع العمال والموزع — قبله لا يُتوقع أن يكونوا أحياء."""
    _STATE["started"] = True


# ------------------------------------------------------------ المراقب
class HealthWatcher:
    """يحوّل التدهور إلى إشعار — مرة لكل (حالة، فحص، ساعة)."""

    def __init__(self, checks_fn: Callable[[], List[Dict[str, str]]],
                 emit: Callable[[Optional[Dict[str, Any]]], Any],
                 clock: Callable[[], float] = time.time):
        self.checks_fn, self.emit, self.clock = checks_fn, emit, clock
        self.last: Dict[str, Any] = {}

    def tick(self) -> Dict[str, Any]:
        try:
            from notifications import events
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from backend.notifications import events
        rep = report(self.checks_fn())
        hour = int(self.clock() // 3600)
        emitted = 0
        for c in rep["checks"]:
            if c["status"] == OK:
                continue
            ev = events.make(f"health.{c['status']}", f"health.{c['status']}:{c['check']}:{hour}",
                             c["check"], f"{c['check']}: {c['reason']}", c["reason"],
                             "/observability/health")
            if self.emit(ev) is not None:
                emitted += 1
        self.last = {**rep, "emitted": emitted}
        return self.last

    def loop(self, stop, interval: float) -> None:
        while not stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # TOLERATED: دورة فحص فاشلة تُسجَّل والمراقب يكمل
                _log.error("R-846: دورة فحص الجاهزية فشلت: %s", type(exc).__name__)
            stop.wait(interval)
