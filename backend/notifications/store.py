# -*- coding: utf-8 -*-
"""R-845 (D-060): الصندوق الصادر — SQLite بوضع WAL.

- ``notifications``: الإشعار نفسه، وهو أيضًا «الصندوق الداخلي» الذي يعمل دائمًا
  ولو لم تُضبط أي قناة خارجية. ``dedupe_key`` فريد: الحدث نفسه لا يُنشئ إشعارين.
- ``deliveries``: تسليم واحد لكل (إشعار، قناة) بحالة:
  pending / sent / failed / suppressed / skipped.
- ``channel_state``: قناة رفضت المصادقة (401/403) تُعطَّل ببصمة إعدادها،
  فلا يتكرر الطرق على باب مغلق. تعود تلقائيًا إذا تغيّر الإعداد (تدوير الرمز).

كل عملية كتابة داخل ``BEGIN IMMEDIATE``، فحجز التسليم ذري بين الموزع
والتصريف اليدوي.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

MAX_KEEP = 2000          # سقف الصندوق — الأقدم يُحذف (لا نمو بلا حد)
LEASE_S = 60.0           # مهلة حجز التسليم؛ انتهاؤها ⇒ يعود مستحقًا (أقل مرة واحدة)
DELIVERY_STATUSES = ("pending", "sent", "failed", "suppressed", "skipped")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notifications (
  id TEXT PRIMARY KEY, dedupe_key TEXT NOT NULL UNIQUE, event TEXT NOT NULL,
  severity TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL,
  body TEXT NOT NULL, link TEXT NOT NULL, subject TEXT NOT NULL,
  created_at REAL NOT NULL, read_at REAL
);
CREATE TABLE IF NOT EXISTS deliveries (
  notification_id TEXT NOT NULL, channel TEXT NOT NULL, status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL,
  lease_until REAL, last_error TEXT, sent_at REAL, reason TEXT,
  PRIMARY KEY (notification_id, channel)
);
CREATE INDEX IF NOT EXISTS ix_deliv_due ON deliveries(status, next_at);
CREATE TABLE IF NOT EXISTS channel_state (
  channel TEXT PRIMARY KEY, disabled_reason TEXT NOT NULL,
  fingerprint TEXT NOT NULL, disabled_at REAL NOT NULL
);
"""


class OutboxStore:
    def __init__(self, path: str, clock: Optional[Callable[[], float]] = None):
        self.path = path
        self.clock = clock or time.time
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        self._local = threading.local()
        c = self._conn()
        c.executescript(_SCHEMA)

    # ------------------------------------------------------------ الاتصال
    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=30, isolation_level=None,
                                check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = c
        return c

    def _tx(self):
        store = self

        class _T:
            def __enter__(self_inner):
                self_inner.c = store._conn()
                self_inner.c.execute("BEGIN IMMEDIATE")
                return self_inner.c

            def __exit__(self_inner, et, ev, tb):
                self_inner.c.execute("COMMIT" if et is None else "ROLLBACK")
                return False
        return _T()

    # ------------------------------------------------------------ الإنشاء
    def emit(self, ev: Dict[str, Any], deliveries: List[Tuple[str, str, str]]
             ) -> Tuple[Dict[str, Any], bool]:
        """إشعار واحد لكل dedupe_key. deliveries: [(قناة، حالة أولية، سبب)].

        يعيد (الإشعار، أُنشئ؟). التكرار لا يضيف تسليمات جديدة.
        """
        now = self.clock()
        with self._tx() as c:
            row = c.execute("SELECT * FROM notifications WHERE dedupe_key=?",
                            (ev["dedupe_key"],)).fetchone()
            if row is not None:
                return self._notif(row), False
            nid = uuid.uuid4().hex
            c.execute("INSERT INTO notifications (id, dedupe_key, event, severity, title,"
                      " summary, body, link, subject, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (nid, ev["dedupe_key"], ev["event"], ev["severity"], ev["title"],
                       ev["summary"], ev["body"], ev["link"], ev["subject"], now))
            for ch, status, reason in deliveries:
                if status not in ("pending", "skipped"):
                    raise ValueError(f"حالة تسليم أولية غير صالحة: {status}")
                c.execute("INSERT INTO deliveries (notification_id, channel, status, next_at,"
                          " reason) VALUES (?,?,?,?,?)", (nid, ch, status, now, reason or None))
            n = c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
            if n > MAX_KEEP:
                old = [r[0] for r in c.execute(
                    "SELECT id FROM notifications ORDER BY created_at ASC LIMIT ?",
                    (n - MAX_KEEP,))]
                for oid in old:
                    c.execute("DELETE FROM deliveries WHERE notification_id=?", (oid,))
                    c.execute("DELETE FROM notifications WHERE id=?", (oid,))
            row = c.execute("SELECT * FROM notifications WHERE id=?", (nid,)).fetchone()
            return self._notif(row), True

    # ------------------------------------------------------------ التسليم
    def claim_due(self, limit: int = 20) -> List[Dict[str, Any]]:
        """حجز ذري للتسليمات المستحقة (pending، حان موعدها، بلا حجز نافذ)."""
        now = self.clock()
        out = []
        with self._tx() as c:
            rows = c.execute(
                "SELECT d.*, n.event, n.severity, n.title, n.summary, n.link, n.created_at"
                " FROM deliveries d JOIN notifications n ON n.id = d.notification_id"
                " WHERE d.status='pending' AND d.next_at<=?"
                " AND (d.lease_until IS NULL OR d.lease_until<?)"
                " ORDER BY d.next_at ASC LIMIT ?", (now, now, int(limit))).fetchall()
            for r in rows:
                c.execute("UPDATE deliveries SET lease_until=?, attempts=attempts+1"
                          " WHERE notification_id=? AND channel=?",
                          (now + LEASE_S, r["notification_id"], r["channel"]))
                d = dict(r)
                d["attempts"] += 1
                out.append(d)
        return out

    def _set(self, nid: str, ch: str, **fields) -> bool:
        cols = ", ".join(f"{k}=?" for k in fields)
        with self._tx() as c:
            cur = c.execute(f"UPDATE deliveries SET {cols} WHERE notification_id=? AND channel=?"
                            " AND status='pending'", (*fields.values(), nid, ch))
            return cur.rowcount == 1

    def mark_sent(self, nid: str, ch: str) -> bool:
        return self._set(nid, ch, status="sent", sent_at=self.clock(), lease_until=None)

    def mark_retry(self, nid: str, ch: str, delay_s: float, err: str) -> bool:
        return self._set(nid, ch, next_at=self.clock() + delay_s, lease_until=None,
                         last_error=err[:300])

    def mark_final(self, nid: str, ch: str, status: str, reason: str,
                   err: Optional[str] = None) -> bool:
        if status not in ("failed", "suppressed"):
            raise ValueError(f"حالة نهائية غير صالحة: {status}")
        return self._set(nid, ch, status=status, reason=reason, lease_until=None,
                         last_error=(err or "")[:300] or None)

    def sent_since(self, ch: str, since: float) -> int:
        return self._conn().execute(
            "SELECT COUNT(*) FROM deliveries WHERE channel=? AND status='sent' AND sent_at>=?",
            (ch, since)).fetchone()[0]

    # ------------------------------------------------------------ حالة القناة
    def disable_channel(self, ch: str, reason: str, fingerprint: str) -> None:
        with self._tx() as c:
            c.execute("INSERT OR REPLACE INTO channel_state VALUES (?,?,?,?)",
                      (ch, reason[:300], fingerprint, self.clock()))

    def enable_channel(self, ch: str) -> bool:
        with self._tx() as c:
            return c.execute("DELETE FROM channel_state WHERE channel=?", (ch,)).rowcount == 1

    def channel_disabled(self, ch: str, fingerprint: str) -> Optional[str]:
        """سبب التعطيل إن كان قائمًا لنفس الإعداد؛ تغيّر الإعداد ⇒ يُرفع التعطيل."""
        r = self._conn().execute("SELECT * FROM channel_state WHERE channel=?",
                                 (ch,)).fetchone()
        if r is None:
            return None
        if r["fingerprint"] != fingerprint:
            self.enable_channel(ch)
            return None
        return r["disabled_reason"]

    # ------------------------------------------------------------ القراءة
    def get(self, nid: str) -> Optional[Dict[str, Any]]:
        c = self._conn()
        r = c.execute("SELECT * FROM notifications WHERE id=?", (nid,)).fetchone()
        if r is None:
            return None
        n = self._notif(r)
        n["deliveries"] = [self._deliv(d) for d in c.execute(
            "SELECT * FROM deliveries WHERE notification_id=? ORDER BY channel", (nid,))]
        return n

    def list(self, unread_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
        q = "SELECT * FROM notifications"
        if unread_only:
            q += " WHERE read_at IS NULL"
        q += " ORDER BY created_at DESC LIMIT ?"
        rows = self._conn().execute(q, (max(1, min(int(limit), 200)),)).fetchall()
        return [self.get(r["id"]) for r in rows]

    def mark_read(self, nid: str) -> Optional[Dict[str, Any]]:
        with self._tx() as c:
            c.execute("UPDATE notifications SET read_at=COALESCE(read_at, ?) WHERE id=?",
                      (self.clock(), nid))
        return self.get(nid)

    def stats(self) -> Dict[str, Any]:
        c = self._conn()
        by = {s: 0 for s in DELIVERY_STATUSES}
        for r in c.execute("SELECT status, COUNT(*) n FROM deliveries GROUP BY status"):
            by[r["status"]] = r["n"]
        return {
            "notifications": c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0],
            "unread": c.execute("SELECT COUNT(*) FROM notifications WHERE read_at IS NULL"
                                ).fetchone()[0],
            "deliveries": by,
            "disabled_channels": [dict(r) for r in c.execute(
                "SELECT channel, disabled_reason, disabled_at FROM channel_state")],
        }

    def deliveries_for(self, nid: str) -> List[Dict[str, Any]]:
        return [self._deliv(d) for d in self._conn().execute(
            "SELECT * FROM deliveries WHERE notification_id=?", (nid,))]

    @staticmethod
    def _notif(r) -> Dict[str, Any]:
        return {k: r[k] for k in r.keys()}

    @staticmethod
    def _deliv(r) -> Dict[str, Any]:
        d = {k: r[k] for k in r.keys()}
        d.pop("lease_until", None)
        return d


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
