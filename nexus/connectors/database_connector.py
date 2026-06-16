"""
NexusCore — موصل قواعد البيانات
يدعم SQLite محلياً وPostgreSQL عبر psycopg2.
"""
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger("nexus.connectors.database")


@dataclass
class QueryResult:
    query: str
    rows: List[Dict]
    count: int
    elapsed_ms: float
    success: bool
    error: Optional[str] = None


class DatabaseConnector:
    """موصل قواعد بيانات شامل"""

    def __init__(self, db_path: str = "nexus_data/nexus.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self.stats = {"queries": 0, "errors": 0, "total_rows": 0}
        self._init_db()
        logger.info(f"🗄️ DatabaseConnector initialized at {db_path}")

    def _init_db(self) -> None:
        import pathlib
        pathlib.Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    namespace TEXT DEFAULT 'default',
                    created_at REAL,
                    updated_at REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    payload TEXT,
                    created_at REAL
                )
            """)
            conn.commit()

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, query: str,
                params: Optional[Tuple] = None) -> QueryResult:
        start = time.time()
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(query, params or ())
                conn.commit()
                rows = [dict(r) for r in (cursor.fetchall() or [])]
                elapsed = (time.time() - start) * 1000
                self.stats["queries"] += 1
                self.stats["total_rows"] += len(rows)
                return QueryResult(query=query, rows=rows, count=len(rows),
                                   elapsed_ms=round(elapsed, 2), success=True)
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            self.stats["errors"] += 1
            logger.error(f"DB error: {exc}")
            return QueryResult(query=query, rows=[], count=0,
                               elapsed_ms=round(elapsed, 2), success=False, error=str(exc))

    # ── KV Store helpers ─────────────────────────
    def kv_set(self, key: str, value: Any, namespace: str = "default") -> bool:
        import json
        now = time.time()
        result = self.execute(
            "INSERT OR REPLACE INTO kv_store VALUES (?,?,?,?,?)",
            (key, json.dumps(value, ensure_ascii=False), namespace, now, now)
        )
        return result.success

    def kv_get(self, key: str, namespace: str = "default") -> Optional[Any]:
        import json
        result = self.execute(
            "SELECT value FROM kv_store WHERE key=? AND namespace=?",
            (key, namespace)
        )
        if result.rows:
            return json.loads(result.rows[0]["value"])
        return None

    def log_event(self, event_type: str, payload: Dict) -> bool:
        import json
        result = self.execute(
            "INSERT INTO events (event_type, payload, created_at) VALUES (?,?,?)",
            (event_type, json.dumps(payload, ensure_ascii=False), time.time())
        )
        return result.success

    def get_stats(self) -> Dict:
        return {**self.stats,
                "db_path": self.db_path,
                "error_rate": round(self.stats["errors"] / max(self.stats["queries"], 1), 3)}
