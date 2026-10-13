"""Bounded in-memory sliding-window rate limiter for API endpoints."""

from collections import OrderedDict, deque
from math import ceil
from threading import Lock
import time
from typing import Deque, Optional


class SlidingWindowRateLimiter:
    """Limit requests per key within a rolling time window.

    State is intentionally process-local; use a shared store for multi-worker
    or horizontally scaled production deployments.
    """

    def __init__(
        self, max_requests: int, window_seconds: int = 60, max_clients: int = 10000
    ):
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")
        if max_clients < 1:
            raise ValueError("max_clients must be at least 1")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._requests: OrderedDict[str, Deque[float]] = OrderedDict()
        self._lock = Lock()

    def check(
        self, key: str, now: Optional[float] = None
    ) -> Optional[int]:
        """Record a request; return retry-after seconds when the key is limited."""
        timestamp = time.monotonic() if now is None else now
        normalized_key = key or "unknown"
        threshold = timestamp - self.window_seconds

        with self._lock:
            requests = self._requests.pop(normalized_key, deque())
            while requests and requests[0] <= threshold:
                requests.popleft()

            if len(requests) >= self.max_requests:
                retry_after = max(1, ceil(self.window_seconds - (timestamp - requests[0])))
                self._requests[normalized_key] = requests
                if len(self._requests) > self.max_clients:
                    self._requests.popitem(last=False)
                return retry_after

            requests.append(timestamp)
            self._requests[normalized_key] = requests
            if len(self._requests) > self.max_clients:
                self._requests.popitem(last=False)
            return None
