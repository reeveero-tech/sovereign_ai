"""
NexusCore — Middleware
Rate limiting + logging للطلبات الواردة.
"""
import logging
import time
from collections import defaultdict
from typing import Callable, Dict, List

logger = logging.getLogger("nexus.api_gateway.middleware")


class RateLimiter:
    """Rate limiter بسيط (Token Bucket)"""

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self._buckets: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        bucket = self._buckets[client_id]
        # احذف الطلبات القديمة (أقدم من دقيقة)
        self._buckets[client_id] = [t for t in bucket if now - t < 60]
        if len(self._buckets[client_id]) >= self.rpm:
            logger.warning(f"Rate limit exceeded for {client_id}")
            return False
        self._buckets[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        now    = time.time()
        bucket = [t for t in self._buckets.get(client_id, []) if now - t < 60]
        return max(0, self.rpm - len(bucket))


class RequestLogger:
    """يسجل الطلبات الواردة"""

    def __init__(self):
        self.requests: List[Dict] = []
        self.max_history = 10_000

    def log(self, method: str, path: str, client_ip: str,
            status_code: int, duration_ms: float) -> None:
        entry = {
            "method": method, "path": path, "client_ip": client_ip,
            "status": status_code, "duration_ms": round(duration_ms, 2),
            "timestamp": time.time(),
        }
        self.requests.append(entry)
        if len(self.requests) > self.max_history:
            self.requests = self.requests[-self.max_history:]
        if status_code >= 400:
            logger.warning(f"{method} {path} → {status_code} ({client_ip})")

    def get_stats(self) -> Dict:
        if not self.requests:
            return {}
        total = len(self.requests)
        errors = sum(1 for r in self.requests if r["status"] >= 400)
        avg_ms = sum(r["duration_ms"] for r in self.requests) / total
        return {
            "total_requests": total,
            "error_rate": round(errors / total, 3),
            "avg_duration_ms": round(avg_ms, 2),
        }
