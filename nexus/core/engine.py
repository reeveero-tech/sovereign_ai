"""
NexusCore — المحرك الرئيسي
يتولى تنسيق جميع مكونات المنصة وإدارة دورة حياتها.
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nexus.core")


class EngineState(Enum):
    INITIALIZING = "initializing"
    RUNNING      = "running"
    PAUSED       = "paused"
    STOPPED      = "stopped"
    ERROR        = "error"


@dataclass
class ComponentInfo:
    name: str
    instance: Any
    healthy: bool = True
    last_check: float = field(default_factory=time.time)
    error_count: int = 0


@dataclass
class EngineMetrics:
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    avg_cycle_ms: float = 0.0
    start_time: float = field(default_factory=time.time)


class CoreEngine:
    """المحرك الرئيسي لـ NexusCore"""

    def __init__(self, config: Optional[Dict] = None):
        self.engine_id = str(uuid.uuid4())[:8]
        self.state = EngineState.INITIALIZING
        self.config = config or {}
        self.components: Dict[str, ComponentInfo] = {}
        self.metrics = EngineMetrics()
        self._hooks: Dict[str, List[Callable]] = {
            "on_cycle_start": [], "on_cycle_end": [], "on_error": []
        }
        self._running = False
        logger.info(f"🚀 NexusCore Engine [{self.engine_id}] initializing…")

    # ── تسجيل المكونات ──────────────────────────
    def register_component(self, name: str, instance: Any) -> None:
        self.components[name] = ComponentInfo(name=name, instance=instance)
        logger.info(f"✅ Component registered: {name}")

    def get_component(self, name: str) -> Optional[Any]:
        info = self.components.get(name)
        return info.instance if info else None

    # ── Hooks ────────────────────────────────────
    def on(self, event: str, callback: Callable) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def _fire(self, event: str, **kwargs) -> None:
        for cb in self._hooks.get(event, []):
            try:
                cb(**kwargs)
            except Exception as exc:
                logger.warning(f"Hook error [{event}]: {exc}")

    # ── دورة المعالجة ─────────────────────────────
    async def run_cycle(self, data: Dict) -> Dict:
        cycle_id = str(uuid.uuid4())[:8]
        start = time.time()
        self._fire("on_cycle_start", cycle_id=cycle_id, data=data)
        try:
            result = {"cycle_id": cycle_id, "status": "ok", "data": data}
            self.metrics.total_cycles += 1
            self.metrics.successful_cycles += 1
            elapsed_ms = (time.time() - start) * 1000
            n = self.metrics.successful_cycles
            self.metrics.avg_cycle_ms = (
                (self.metrics.avg_cycle_ms * (n - 1) + elapsed_ms) / n
            )
            self._fire("on_cycle_end", cycle_id=cycle_id, result=result)
            return result
        except Exception as exc:
            self.metrics.total_cycles += 1
            self.metrics.failed_cycles += 1
            logger.error(f"Cycle error [{cycle_id}]: {exc}")
            self._fire("on_error", cycle_id=cycle_id, error=str(exc))
            return {"cycle_id": cycle_id, "status": "error", "error": str(exc)}

    # ── تشغيل / إيقاف ────────────────────────────
    async def start(self) -> None:
        self.state = EngineState.RUNNING
        self._running = True
        logger.info("✅ NexusCore Engine running")

    async def stop(self) -> None:
        self._running = False
        self.state = EngineState.STOPPED
        logger.info("🛑 NexusCore Engine stopped")

    # ── الحالة ───────────────────────────────────
    def get_status(self) -> Dict:
        uptime = time.time() - self.metrics.start_time
        return {
            "engine_id": self.engine_id,
            "state": self.state.value,
            "uptime_seconds": round(uptime, 2),
            "components": {
                n: {"healthy": c.healthy, "errors": c.error_count}
                for n, c in self.components.items()
            },
            "metrics": {
                "total_cycles": self.metrics.total_cycles,
                "successful": self.metrics.successful_cycles,
                "failed": self.metrics.failed_cycles,
                "avg_cycle_ms": round(self.metrics.avg_cycle_ms, 2),
            },
        }


_instance: Optional[CoreEngine] = None


def get_engine(config: Optional[Dict] = None) -> CoreEngine:
    global _instance
    if _instance is None:
        _instance = CoreEngine(config)
    return _instance
