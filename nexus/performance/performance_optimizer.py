"""
NexusCore — محسّن الأداء
بديل آمن لـ self_improvement/ — يقيس ويحلل ويقترح تحسينات.
"""
import logging
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Dict, Generator, List, Optional

logger = logging.getLogger("nexus.performance.optimizer")


@dataclass
class Measurement:
    name: str
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict = field(default_factory=dict)


@dataclass
class PerformanceReport:
    name: str
    count: int
    avg_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    p99_ms: float


class PerformanceOptimizer:
    """يقيس أداء الكود ويولد تقارير تحسين"""

    def __init__(self, max_history: int = 10_000):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._baselines: Dict[str, float] = {}
        logger.info("⚡ PerformanceOptimizer initialized")

    @contextmanager
    def measure(self, name: str, **tags) -> Generator[None, None, None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._metrics[name].append(
                Measurement(name=name, duration_ms=elapsed_ms, tags=tags)
            )

    def record(self, name: str, duration_ms: float, **tags) -> None:
        self._metrics[name].append(
            Measurement(name=name, duration_ms=duration_ms, tags=tags)
        )

    def set_baseline(self, name: str, expected_ms: float) -> None:
        self._baselines[name] = expected_ms

    def get_report(self, name: str) -> Optional[PerformanceReport]:
        measurements = list(self._metrics.get(name, []))
        if not measurements:
            return None
        durations = sorted(m.duration_ms for m in measurements)
        n = len(durations)
        return PerformanceReport(
            name=name,
            count=n,
            avg_ms=round(sum(durations) / n, 2),
            min_ms=round(durations[0], 2),
            max_ms=round(durations[-1], 2),
            p95_ms=round(durations[int(n * 0.95)], 2),
            p99_ms=round(durations[int(n * 0.99)], 2),
        )

    def get_all_reports(self) -> List[PerformanceReport]:
        return [r for name in self._metrics
                if (r := self.get_report(name)) is not None]

    def identify_bottlenecks(self, threshold_ms: float = 500.0) -> List[Dict]:
        bottlenecks = []
        for name in self._metrics:
            report = self.get_report(name)
            if report and report.avg_ms > threshold_ms:
                baseline = self._baselines.get(name)
                bottlenecks.append({
                    "name": name,
                    "avg_ms": report.avg_ms,
                    "p99_ms": report.p99_ms,
                    "threshold_ms": threshold_ms,
                    "regression": round(report.avg_ms / baseline, 2) if baseline else None,
                })
        return sorted(bottlenecks, key=lambda x: x["avg_ms"], reverse=True)

    def time_function(self, fn: Callable, *args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        self.record(fn.__name__, elapsed)
        return result
