# -*- coding: utf-8 -*-
"""R-844 (D-059): مخزن الطابور الدائم — SQLite (مكتبة قياسية، لا خدمة إضافية).

لماذا SQLite لا ملفات JSON: الحجز الذري لمهمة («من يأخذها؟») يحتاج معاملة
واحدة. ``BEGIN IMMEDIATE`` يمنع عاملين من أخذ المهمة نفسها، حتى في عمليتين.

دورة المهمة::

    queued ──claim──▶ running ──▶ succeeded | needs_human | failed | cancelled
       ▲                 │
       └── retry/lease ──┘        (استنفاد المحاولات ⇒ dead)

- **عدم التكرار**: ``idem_key`` فريد. المفتاح نفسه بالحمولة نفسها يعيد المهمة
  القائمة، وبحمولة مختلفة يرفع ``IdempotencyConflict``. المفتاح لا يُعاد
  استعماله لعمل آخر.
- **الإيجار والسياج**: الحجز يعطي ``lease_until`` ويزيد ``fence``. الإنهاء
  مشروط بالمالك والسياج معًا، فعامل قديم انتهى إيجاره لا يكتب فوق نتيجة
  عامل أحدث (``stale``).
- **الاستعادة**: الإيجار المنتهي (العملية ماتت) يعيد المهمة إلى الطابور إن
  بقيت محاولات، وإلا ``dead``.
- **الضغط الخلفي**: ``max_depth`` يحد عدد المهام النشطة (queued+running)، وما
  زاد يُرفض بـ``QueueFull``. لا قبول بلا حد.
- **الأثر**: كل انتقال يُلحق حدثًا في ``job_events`` داخل المعاملة نفسها.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple

ACTIVE = ("queued", "running")
TERMINAL = ("succeeded", "needs_human", "failed", "dead", "cancelled")
STATUSES = ACTIVE + TERMINAL

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
  payload_hash TEXT NOT NULL, idem_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 0,
  attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
  timeout_s REAL NOT NULL, available_at REAL NOT NULL,
  lease_owner TEXT, lease_until REAL, fence INTEGER NOT NULL DEFAULT 0,
  cancel_requested INTEGER NOT NULL DEFAULT 0,
  loop_id TEXT, actor TEXT NOT NULL, result TEXT, error TEXT,
  created_at REAL NOT NULL, updated_at REAL NOT NULL,
  started_at REAL, finished_at REAL);
CREATE INDEX IF NOT EXISTS jobs_ready ON jobs(status, available_at, priority);
CREATE TABLE IF NOT EXISTS job_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
  ts REAL NOT NULL, event TEXT NOT NULL, detail TEXT);
CREATE INDEX IF NOT EXISTS job_events_job ON job_events(job_id, seq);
"""


class QueueError(Exception):
    pass


class IdempotencyConflict(QueueError):
    """المفتاح نفسه بحمولة مختلفة — لا إعادة استعمال لمفتاح في عمل آخر."""


class QueueFull(QueueError):
    """الضغط الخلفي: الطابور بلغ حده."""


def payload_hash(kind: str, payload: Dict[str, Any]) -> str:
    raw = json.dumps({"kind": kind, "payload": payload}, sort_keys=True,
                     ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class JobStore:
    def __init__(self, path: str, max_depth: int = 100,
                 clock=time.time):
        self.path = path
        self.max_depth = int(max_depth)
        self.clock = clock
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        c = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:  # executescript يلتزم ضمنيًا — خارج _tx
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(_SCHEMA)
        finally:
            c.close()

    # ------------------------------------------------------------ أساس
    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        """معاملة واحدة بقفل كتابة فوري: الكل أو لا شيء."""
        with self._lock:
            c = sqlite3.connect(self.path, timeout=10, isolation_level=None)
            c.row_factory = sqlite3.Row
            try:
                c.execute("PRAGMA synchronous=FULL")
                c.execute("BEGIN IMMEDIATE")
                try:
                    yield c
                except BaseException:
                    c.execute("ROLLBACK")
                    raise
                c.execute("COMMIT")
            finally:
                c.close()

    def _event(self, c, job_id: str, event: str, detail: Any = None) -> None:
        c.execute("INSERT INTO job_events(job_id, ts, event, detail) VALUES (?,?,?,?)",
                  (job_id, self.clock(), event,
                   None if detail is None else json.dumps(detail, ensure_ascii=False)))

    @staticmethod
    def _row(r: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if r is None:
            return None
        d = dict(r)
        d["payload"] = json.loads(d["payload"])
        d["result"] = json.loads(d["result"]) if d["result"] else None
        d["cancel_requested"] = bool(d["cancel_requested"])
        return d

    # ------------------------------------------------------------ الإدخال
    def enqueue(self, kind: str, payload: Dict[str, Any], idem_key: str,
                actor: str, max_attempts: int, timeout_s: float,
                priority: int = 0) -> Tuple[Dict[str, Any], bool]:
        """يعيد (المهمة، أُنشئت؟). المفتاح نفسه بالحمولة نفسها ⇒ المهمة القائمة."""
        if not idem_key or len(idem_key) > 200:
            raise QueueError("Idempotency-Key مطلوب (1–200 حرف)")
        h = payload_hash(kind, payload)
        now = self.clock()
        with self._tx() as c:
            old = c.execute("SELECT * FROM jobs WHERE idem_key=?", (idem_key,)).fetchone()
            if old is not None:
                if old["payload_hash"] != h:
                    raise IdempotencyConflict(
                        "Idempotency-Key مستعمل لعمل مختلف — لا إعادة استعمال")
                self._event(c, old["id"], "deduplicated", {"actor": actor})
                return self._row(old), False
            depth = c.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')"
                              ).fetchone()[0]
            if depth >= self.max_depth:
                raise QueueFull(f"الطابور ممتلئ ({depth}/{self.max_depth}) — أعد لاحقًا")
            jid = str(uuid.uuid4())
            c.execute("""INSERT INTO jobs(id, kind, payload, payload_hash, idem_key, status,
                         priority, attempts, max_attempts, timeout_s, available_at, actor,
                         created_at, updated_at) VALUES (?,?,?,?,?,'queued',?,0,?,?,?,?,?,?)""",
                      (jid, kind, json.dumps(payload, ensure_ascii=False), h, idem_key,
                       int(priority), int(max_attempts), float(timeout_s), now, actor,
                       now, now))
            self._event(c, jid, "enqueued", {"kind": kind, "actor": actor})
            return self._row(c.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()), True

    # ------------------------------------------------------------ الحجز
    def claim(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """حجز ذري لأقدم مهمة جاهزة بأعلى أولوية — أو None."""
        now = self.clock()
        with self._tx() as c:
            r = c.execute("""SELECT id FROM jobs WHERE status='queued' AND available_at<=?
                             AND cancel_requested=0
                             ORDER BY priority DESC, created_at ASC LIMIT 1""",
                          (now,)).fetchone()
            if r is None:
                return None
            c.execute("""UPDATE jobs SET status='running', lease_owner=?,
                         lease_until=?+timeout_s, attempts=attempts+1, fence=fence+1,
                         started_at=COALESCE(started_at, ?), updated_at=? WHERE id=?""",
                      (worker_id, now, now, now, r["id"]))
            job = self._row(c.execute("SELECT * FROM jobs WHERE id=?", (r["id"],)).fetchone())
            self._event(c, job["id"], "claimed", {"worker": worker_id,
                                                  "attempt": job["attempts"],
                                                  "fence": job["fence"]})
            return job

    def _owned(self, c, job_id: str, worker_id: str, fence: int) -> bool:
        r = c.execute("SELECT status, lease_owner, fence FROM jobs WHERE id=?",
                      (job_id,)).fetchone()
        return (r is not None and r["status"] == "running"
                and r["lease_owner"] == worker_id and r["fence"] == fence)

    def set_loop(self, job_id: str, worker_id: str, fence: int, loop_id: str) -> bool:
        """تسجيل معرّف الحلقة قبل أي أثر — الاستعادة تستأنف الحلقة نفسها."""
        with self._tx() as c:
            if not self._owned(c, job_id, worker_id, fence):
                return False
            c.execute("UPDATE jobs SET loop_id=?, updated_at=? WHERE id=?",
                      (loop_id, self.clock(), job_id))
            self._event(c, job_id, "loop_bound", {"loop_id": loop_id})
            return True

    def finish(self, job_id: str, worker_id: str, fence: int, status: str,
               result: Optional[Dict[str, Any]] = None,
               error: Optional[str] = None) -> bool:
        """إنهاء مسيَّج — False إن لم يعد العامل مالكها (نتيجة قديمة تُرفض)."""
        if status not in TERMINAL:
            raise QueueError(f"حالة إنهاء غير صالحة: {status}")
        now = self.clock()
        with self._tx() as c:
            if not self._owned(c, job_id, worker_id, fence):
                self._event(c, job_id, "stale_finish_rejected",
                            {"worker": worker_id, "fence": fence, "wanted": status})
                return False
            c.execute("""UPDATE jobs SET status=?, result=?, error=?, lease_owner=NULL,
                         lease_until=NULL, finished_at=?, updated_at=? WHERE id=?""",
                      (status, json.dumps(result, ensure_ascii=False) if result is not None
                       else None, error, now, now, job_id))
            self._event(c, job_id, status, {"error": error} if error else None)
            return True

    def retry(self, job_id: str, worker_id: str, fence: int, error: str,
              delay_s: float) -> Optional[str]:
        """فشل عابر: إعادة للطابور بعد تأخير إن بقيت محاولات، وإلا dead."""
        now = self.clock()
        with self._tx() as c:
            if not self._owned(c, job_id, worker_id, fence):
                self._event(c, job_id, "stale_finish_rejected",
                            {"worker": worker_id, "fence": fence, "wanted": "retry"})
                return None
            r = c.execute("SELECT attempts, max_attempts FROM jobs WHERE id=?",
                          (job_id,)).fetchone()
            if r["attempts"] >= r["max_attempts"]:
                c.execute("""UPDATE jobs SET status='dead', error=?, lease_owner=NULL,
                             lease_until=NULL, finished_at=?, updated_at=? WHERE id=?""",
                          (error, now, now, job_id))
                self._event(c, job_id, "dead", {"error": error,
                                                "attempts": r["attempts"]})
                return "dead"
            c.execute("""UPDATE jobs SET status='queued', error=?, lease_owner=NULL,
                         lease_until=NULL, available_at=?, updated_at=? WHERE id=?""",
                      (error, now + delay_s, now, job_id))
            self._event(c, job_id, "retry_scheduled", {"error": error, "delay_s": delay_s,
                                                       "attempt": r["attempts"]})
            return "queued"

    # ------------------------------------------------------------ الاستعادة
    def recover(self) -> List[Dict[str, Any]]:
        """مهام running انتهى إيجارها (العملية ماتت/علقت) ⇒ طابور أو dead."""
        now = self.clock()
        out = []
        with self._tx() as c:
            rows = c.execute("""SELECT id, attempts, max_attempts, lease_owner,
                                cancel_requested FROM jobs
                                WHERE status='running' AND lease_until < ?""",
                             (now,)).fetchall()
            for r in rows:
                to = ("cancelled" if r["cancel_requested"] else
                      "queued" if r["attempts"] < r["max_attempts"] else "dead")
                c.execute("""UPDATE jobs SET status=?, lease_owner=NULL, lease_until=NULL,
                             available_at=?, updated_at=?,
                             error=COALESCE(error, 'انتهى الإيجار — العامل لم يُنهِ'),
                             finished_at=CASE WHEN ?<>'queued' THEN ? ELSE finished_at END
                             WHERE id=?""", (to, now, now, to, now, r["id"]))
                self._event(c, r["id"], "lease_expired",
                            {"worker": r["lease_owner"], "to": to})
                out.append({"job_id": r["id"], "to": to})
        return out

    # ------------------------------------------------------------ الإلغاء
    def cancel(self, job_id: str, actor: str) -> Optional[Dict[str, Any]]:
        """queued ⇒ cancelled فورًا؛ running ⇒ طلب إلغاء (المعالج يلغي الحلقة)."""
        now = self.clock()
        with self._tx() as c:
            r = c.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if r is None:
                return None
            if r["status"] == "queued":
                c.execute("""UPDATE jobs SET status='cancelled', finished_at=?, updated_at=?
                             WHERE id=?""", (now, now, job_id))
                self._event(c, job_id, "cancelled", {"actor": actor})
            elif r["status"] == "running":
                c.execute("UPDATE jobs SET cancel_requested=1, updated_at=? WHERE id=?",
                          (now, job_id))
                self._event(c, job_id, "cancel_requested", {"actor": actor})
            return self._row(c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    # ------------------------------------------------------------ القراءة
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._tx() as c:
            return self._row(c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def events(self, job_id: str) -> List[Dict[str, Any]]:
        with self._tx() as c:
            rows = c.execute("SELECT ts, event, detail FROM job_events WHERE job_id=? "
                             "ORDER BY seq", (job_id,)).fetchall()
        return [{"ts": r["ts"], "event": r["event"],
                 "detail": json.loads(r["detail"]) if r["detail"] else None} for r in rows]

    def list(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with self._tx() as c:
            if status:
                rows = c.execute("SELECT * FROM jobs WHERE status=? ORDER BY created_at DESC "
                                 "LIMIT ?", (status, limit)).fetchall()
            else:
                rows = c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                                 (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        now = self.clock()
        with self._tx() as c:
            counts = {s: 0 for s in STATUSES}
            for r in c.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status"):
                counts[r["status"]] = r["n"]
            oldest = c.execute("SELECT MIN(created_at) FROM jobs WHERE status='queued'"
                               ).fetchone()[0]
        return {"counts": counts, "depth": counts["queued"] + counts["running"],
                "max_depth": self.max_depth,
                "oldest_queued_age_s": round(now - oldest, 1) if oldest else 0.0}
