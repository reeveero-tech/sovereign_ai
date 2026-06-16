"""
NexusCore — مراقب صحة النظام
يراقب موارد النظام ومكونات NexusCore باستمرار.
"""
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nexus.security.health")


@dataclass
class HealthCheck:
    name: str
    status: str          # healthy / degraded / unhealthy
    latency_ms: float
    message: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class SystemMetrics:
    cpu_pct: float
    memory_mb: float
    memory_pct: float
    disk_free_gb: float
    process_count: int
    uptime_seconds: float
    timestamp: float = field(default_factory=time.time)


class HealthMonitor:
    """مراقب صحة شامل للنظام والمكونات"""

    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self.history: List[HealthCheck] = []
        self._start_time = time.time()
        logger.info("🩺 HealthMonitor initialized")

    def register_check(self, name: str, fn: Callable) -> None:
        self._checks[name] = fn

    def run_check(self, name: str) -> HealthCheck:
        fn = self._checks.get(name)
        if not fn:
            return HealthCheck(name=name, status="unhealthy",
                               latency_ms=0, message="Check not registered")
        start = time.time()
        try:
            result = fn()
            latency = (time.time() - start) * 1000
            if isinstance(result, dict):
                status = result.get("status", "healthy")
                msg    = result.get("message", "OK")
                meta   = result.get("metadata", {})
            else:
                status = "healthy" if result else "unhealthy"
                msg    = "OK" if result else "Check returned False"
                meta   = {}
        except Exception as exc:
            latency = (time.time() - start) * 1000
            status, msg, meta = "unhealthy", str(exc), {}
        check = HealthCheck(name=name, status=status,
                            latency_ms=round(latency, 2),
                            message=msg, metadata=meta)
        self.history.append(check)
        return check

    def run_all_checks(self) -> Dict[str, HealthCheck]:
        return {name: self.run_check(name) for name in self._checks}

    def get_system_metrics(self) -> SystemMetrics:
        try:
            import psutil
            cpu   = psutil.cpu_percent(interval=0.1)
            mem   = psutil.virtual_memory()
            disk  = psutil.disk_usage("/")
            procs = len(psutil.pids())
            return SystemMetrics(
                cpu_pct=cpu, memory_mb=round(mem.used / 1024 / 1024, 1),
                memory_pct=mem.percent, disk_free_gb=round(disk.free / 1024**3, 2),
                process_count=procs, uptime_seconds=time.time() - self._start_time,
            )
        except ImportError:
            # psutil غير متاح — نستخدم بديلاً أساسياً
            return SystemMetrics(
                cpu_pct=0.0, memory_mb=0.0, memory_pct=0.0,
                disk_free_gb=0.0, process_count=0,
                uptime_seconds=time.time() - self._start_time,
            )

    def get_overall_status(self) -> Dict:
        checks = self.run_all_checks()
        statuses = [c.status for c in checks.values()]
        if any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        elif any(s == "degraded" for s in statuses):
            overall = "degraded"
        else:
            overall = "healthy"
        metrics = self.get_system_metrics()
        return {
            "overall": overall,
            "checks": {name: {"status": c.status, "message": c.message,
                               "latency_ms": c.latency_ms}
                       for name, c in checks.items()},
            "system": {
                "cpu_pct": metrics.cpu_pct,
                "memory_mb": metrics.memory_mb,
                "disk_free_gb": metrics.disk_free_gb,
                "uptime_seconds": round(metrics.uptime_seconds, 1),
            },
        }
