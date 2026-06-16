"""
NexusCore — مدير الكاش (TTL Cache)
كاش سريع في الذاكرة مع انتهاء صلاحية تلقائي.
"""
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("nexus.storage.cache")


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    hits: int = 0


class CacheManager:
    """كاش TTL سريع في الذاكرة"""

    def __init__(self, default_ttl: int = 300, max_size: int = 5000):
        self._store: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
        logger.info(f"💾 CacheManager initialized (TTL={default_ttl}s, max={max_size})")

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if len(self._store) >= self.max_size:
            self._evict()
        ttl = ttl if ttl is not None else self.default_ttl
        self._store[key] = CacheEntry(value=value, expires_at=time.time() + ttl)

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            self._stats["misses"] += 1
            return None
        if time.time() > entry.expires_at:
            del self._store[key]
            self._stats["misses"] += 1
            return None
        entry.hits += 1
        self._stats["hits"] += 1
        return entry.value

    def delete(self, key: str) -> bool:
        return bool(self._store.pop(key, None))

    def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    def _evict(self) -> None:
        now = time.time()
        expired = [k for k, e in self._store.items() if now > e.expires_at]
        for k in expired:
            del self._store[k]
            self._stats["evictions"] += 1
        if len(self._store) >= self.max_size:
            oldest = sorted(self._store.items(), key=lambda x: x[1].expires_at)[:100]
            for k, _ in oldest:
                del self._store[k]
                self._stats["evictions"] += 1

    def get_stats(self) -> Dict:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            "size": len(self._store),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(self._stats["hits"] / total, 3) if total else 0.0,
            "evictions": self._stats["evictions"],
        }
