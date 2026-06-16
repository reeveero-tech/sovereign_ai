"""
NexusCore — مخصص الموارد الذكي
يدير وزيع الموارد الحاسوبية بين المكونات.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("nexus.resource.allocator")


@dataclass
class Resource:
    name: str
    total: float
    allocated: float = 0.0
    unit: str = "units"

    @property
    def available(self) -> float:
        return max(0.0, self.total - self.allocated)

    @property
    def utilization(self) -> float:
        return self.allocated / self.total if self.total > 0 else 0.0


@dataclass
class Allocation:
    alloc_id: str
    consumer: str
    resource_name: str
    amount: float
    priority: int          # 1=highest … 10=lowest
    allocated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None


class ResourceAllocator:
    """مخصص موارد بالأولوية مع دعم TTL"""

    def __init__(self):
        import uuid
        self._uuid = uuid
        self.resources: Dict[str, Resource] = {}
        self.allocations: Dict[str, Allocation] = {}
        logger.info("🎯 ResourceAllocator initialized")

    def register_resource(self, name: str, total: float, unit: str = "units") -> None:
        self.resources[name] = Resource(name=name, total=total, unit=unit)
        logger.info(f"Resource registered: {name} ({total} {unit})")

    def allocate(self, consumer: str, resource_name: str, amount: float,
                 priority: int = 5, ttl_seconds: Optional[int] = None) -> Optional[Allocation]:
        self._expire_old()
        resource = self.resources.get(resource_name)
        if not resource:
            logger.error(f"Resource not found: {resource_name}")
            return None
        if resource.available < amount:
            # حاول تحرير موارد منخفضة الأولوية
            freed = self._preempt_low_priority(resource_name, amount, priority)
            if resource.available < amount - freed:
                logger.warning(f"Insufficient {resource_name}: need {amount}, have {resource.available}")
                return None
        alloc = Allocation(
            alloc_id=self._uuid.uuid4().hex[:8],
            consumer=consumer, resource_name=resource_name,
            amount=amount, priority=priority,
            expires_at=time.time() + ttl_seconds if ttl_seconds else None,
        )
        resource.allocated += amount
        self.allocations[alloc.alloc_id] = alloc
        logger.info(f"✅ Allocated {amount} {resource.unit} of {resource_name} to {consumer}")
        return alloc

    def release(self, alloc_id: str) -> bool:
        alloc = self.allocations.pop(alloc_id, None)
        if not alloc:
            return False
        resource = self.resources.get(alloc.resource_name)
        if resource:
            resource.allocated = max(0.0, resource.allocated - alloc.amount)
        logger.info(f"Released {alloc.amount} of {alloc.resource_name} from {alloc.consumer}")
        return True

    def _expire_old(self) -> int:
        now = time.time()
        expired = [
            aid for aid, a in self.allocations.items()
            if a.expires_at and now > a.expires_at
        ]
        for aid in expired:
            self.release(aid)
        return len(expired)

    def _preempt_low_priority(self, resource_name: str, needed: float,
                               requester_priority: int) -> float:
        candidates = sorted(
            [a for a in self.allocations.values()
             if a.resource_name == resource_name
             and a.priority > requester_priority],
            key=lambda x: x.priority, reverse=True
        )
        freed = 0.0
        for cand in candidates:
            if freed >= needed:
                break
            freed += cand.amount
            self.release(cand.alloc_id)
            logger.info(f"Preempted allocation {cand.alloc_id} (priority={cand.priority})")
        return freed

    def get_snapshot(self) -> Dict:
        return {
            "resources": {
                name: {"total": r.total, "allocated": round(r.allocated, 2),
                       "available": round(r.available, 2),
                       "utilization_pct": round(r.utilization * 100, 1),
                       "unit": r.unit}
                for name, r in self.resources.items()
            },
            "active_allocations": len(self.allocations),
        }
