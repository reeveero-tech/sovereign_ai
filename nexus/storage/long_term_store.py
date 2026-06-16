"""
NexusCore — التخزين طويل الأمد
يخزن البيانات بشكل دائم في ملفات JSON (قابل للاستبدال بقاعدة بيانات).
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.storage.long_term")


class LongTermStore:
    """مخزن بيانات دائم مبني على ملفات JSON"""

    def __init__(self, base_dir: str = "nexus_data/store"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, Dict] = {}
        self._load_index()
        logger.info(f"📦 LongTermStore initialized at {self.base_dir}")

    # ── CRUD ──────────────────────────────────────
    def save(self, collection: str, key: str, data: Any,
             metadata: Optional[Dict] = None) -> str:
        coll_dir = self.base_dir / collection
        coll_dir.mkdir(exist_ok=True)
        record = {
            "key": key,
            "collection": collection,
            "data": data,
            "metadata": metadata or {},
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        file_path = coll_dir / f"{key}.json"
        file_path.write_text(json.dumps(record, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        self._index_entry(collection, key, record["created_at"])
        return key

    def load(self, collection: str, key: str) -> Optional[Any]:
        file_path = self.base_dir / collection / f"{key}.json"
        if not file_path.exists():
            return None
        try:
            record = json.loads(file_path.read_text(encoding="utf-8"))
            return record.get("data")
        except Exception as exc:
            logger.error(f"Load error [{collection}/{key}]: {exc}")
            return None

    def delete(self, collection: str, key: str) -> bool:
        file_path = self.base_dir / collection / f"{key}.json"
        if file_path.exists():
            file_path.unlink()
            self._index.get(collection, {}).pop(key, None)
            return True
        return False

    def list_keys(self, collection: str) -> List[str]:
        coll_dir = self.base_dir / collection
        if not coll_dir.exists():
            return []
        return [f.stem for f in coll_dir.glob("*.json")]

    def query(self, collection: str, filter_fn=None) -> List[Any]:
        results = []
        for key in self.list_keys(collection):
            data = self.load(collection, key)
            if data is not None:
                if filter_fn is None or filter_fn(data):
                    results.append(data)
        return results

    # ── Index ─────────────────────────────────────
    def _index_entry(self, collection: str, key: str, created_at: float) -> None:
        self._index.setdefault(collection, {})[key] = created_at

    def _load_index(self) -> None:
        for coll_dir in self.base_dir.iterdir():
            if coll_dir.is_dir():
                for f in coll_dir.glob("*.json"):
                    self._index.setdefault(coll_dir.name, {})[f.stem] = f.stat().st_mtime

    def get_stats(self) -> Dict:
        return {
            "collections": list(self._index.keys()),
            "total_records": sum(len(v) for v in self._index.values()),
        }
