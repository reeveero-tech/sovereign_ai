# -*- coding: utf-8 -*-
"""R-844 (D-059): العامل — يحجز مهمة واحدة ويشغّلها ثم ينهيها بسياج.

حدود صريحة (ممنوع «حلقة بلا حد»):
- ``run_once``: مهمة واحدة على الأكثر، ومهلتها من نوعها (إيجار).
- ``drain(max_jobs)``: سقف صلب ``MAX_DRAIN``.
- حلقة الخلفية: مهمة ثم انتظار قابل للمقاطعة، والإيقاف عبر
  ``runtime.threads`` (stop_event).

ما لا يفعله العامل: لا يقتل خيطًا تجاوز مهلته (بايثون لا يدعم ذلك بأمان).
التجاوز يُسجَّل حدثًا ``overran``، وإذا أُعيد حجز المهمة بعد انتهاء الإيجار
فالسياج يرفض نتيجة العامل القديم.
"""
from __future__ import annotations

import logging
import os
import socket
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from . import kinds as kinds_mod
from .store import JobStore

try:
    from secret_guard import catalog as _catalog
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.secret_guard import catalog as _catalog

_log = logging.getLogger("job_queue.worker")

MAX_DRAIN = 50
BACKOFF_BASE_S = 2.0
BACKOFF_CAP_S = 300.0


def scrub(text: str) -> str:
    """لا سر في نص خطأ محفوظ — R-848: الكتالوج الموحد (secret_guard.catalog)."""
    return _catalog.redact(text or "", 300)


def backoff_s(attempt: int) -> float:
    """أسّي حتمي: 2، 4، 8… بسقف 300ث."""
    return min(BACKOFF_BASE_S * (2 ** max(0, attempt - 1)), BACKOFF_CAP_S)


class Worker:
    def __init__(self, store: JobStore, registry: Optional[Dict[str, Any]] = None,
                 worker_id: Optional[str] = None, orchestrator=None,
                 on_finish: Optional[List[Any]] = None):
        self.store = store
        # R-845: مراقبو انتهاء المهام — قائمة مشتركة (تُقرأ عند كل نداء)
        self.on_finish = on_finish if on_finish is not None else []
        self.orchestrator = orchestrator  # None ⇒ منسق الخادم المشترك
        self.registry = registry if registry is not None else kinds_mod.KINDS
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"

    def _notify(self, jid: str) -> None:
        if not self.on_finish:
            return
        job = self.store.get(jid)
        for hook in list(self.on_finish):
            try:
                hook(job)
            except Exception as exc:  # TOLERATED: مراقب معطوب لا يكسر العامل — يُسجَّل
                _log.error("R-844/R-845: مراقب الانتهاء فشل للمهمة %s: %s",
                           jid[:8], type(exc).__name__)

    def run_once(self) -> Optional[Dict[str, Any]]:
        """استعادة الإيجارات المنتهية ثم مهمة واحدة. يعيد ملخصها أو None."""
        out = self._run_once()
        if out is not None and out.get("status") != "stale":
            self._notify(out["job_id"])
        return out

    def _run_once(self) -> Optional[Dict[str, Any]]:
        for tr in self.store.recover():
            if tr.get("to") in ("dead", "cancelled"):
                self._notify(tr["job_id"])
        job = self.store.claim(self.worker_id)
        if job is None:
            return None
        jid, fence = job["id"], job["fence"]
        kind = self.registry.get(job["kind"])
        if kind is None:
            self.store.finish(jid, self.worker_id, fence, "failed",
                              error=f"نوع غير مسجل: {job['kind']}")
            return {"job_id": jid, "status": "failed"}
        ctx = kinds_mod.JobContext(
            job=job,
            bind_loop=lambda lid: self.store.set_loop(jid, self.worker_id, fence, lid),
            cancel_requested=lambda: bool((self.store.get(jid) or {}).get("cancel_requested")),
            orchestrator=self.orchestrator)
        t0 = time.monotonic()
        try:
            kind.validate(job["payload"])
            outcome = kind.handler(ctx)
        except kinds_mod.StaleJob as exc:
            _log.warning("R-844: مهمة %s: %s", jid, exc)
            return {"job_id": jid, "status": "stale"}
        except kind.retryable as exc:
            err = scrub(f"{type(exc).__name__}: {exc}")
            to = self.store.retry(jid, self.worker_id, fence, err, backoff_s(job["attempts"]))
            return {"job_id": jid, "status": to or "stale", "error": err}
        except Exception as exc:  # فشل غير عابر — لا إعادة عمياء
            err = scrub(f"{type(exc).__name__}: {exc}")
            ok = self.store.finish(jid, self.worker_id, fence, "failed", error=err)
            return {"job_id": jid, "status": "failed" if ok else "stale", "error": err}
        elapsed = time.monotonic() - t0
        limit = kind.timeout_s(job["payload"])
        result = dict(outcome.result)
        if elapsed > limit:
            result["overran_s"] = round(elapsed - limit, 1)
        ok = self.store.finish(jid, self.worker_id, fence, outcome.status, result,
                               scrub(outcome.error) if outcome.error else None)
        return {"job_id": jid, "status": outcome.status if ok else "stale"}

    def drain(self, max_jobs: int = 10) -> List[Dict[str, Any]]:
        out = []
        for _ in range(max(0, min(int(max_jobs), MAX_DRAIN))):
            r = self.run_once()
            if r is None:
                break
            out.append(r)
        return out

    def loop(self, stop: threading.Event, poll_s: float = 1.0) -> None:
        """حلقة الخلفية — تتوقف عند ضبط stop (إيقاف منظم من runtime.threads)."""
        while not stop.is_set():
            try:
                did = self.run_once()
            except Exception as exc:  # TOLERATED: عطل المخزن (قرص/قفل) يُسجَّل والعامل يبقى حيًا — لا موت للطابور كله
                _log.error("R-844: عطل في العامل %s: %s", self.worker_id, scrub(str(exc)))
                did = None
            if did is None:
                stop.wait(poll_s)
