"""
NexusCore — سجل المهام
يتتبع جميع المهام المعرّفة في النظام.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("nexus.task_scheduler.registry")


@dataclass
class TaskDefinition:
    name: str
    fn: Callable
    description: str
    category: str
    tags: List[str] = field(default_factory=list)
    registered_at: float = field(default_factory=time.time)
    call_count: int = 0


class TaskRegistry:
    """سجل مركزي لجميع المهام القابلة للجدولة"""

    def __init__(self):
        self._registry: Dict[str, TaskDefinition] = {}
        logger.info("📋 TaskRegistry initialized")

    def register(self, name: str, fn: Callable,
                 description: str = "", category: str = "general",
                 tags: Optional[List[str]] = None) -> None:
        self._registry[name] = TaskDefinition(
            name=name, fn=fn, description=description,
            category=category, tags=tags or [],
        )
        logger.info(f"📋 Task registered: {name}")

    def task(self, description: str = "", category: str = "general",
             tags: Optional[List[str]] = None):
        """Decorator لتسجيل الدوال كمهام"""
        def decorator(fn: Callable) -> Callable:
            self.register(fn.__name__, fn, description, category, tags)
            return fn
        return decorator

    def get(self, name: str) -> Optional[TaskDefinition]:
        return self._registry.get(name)

    def call(self, name: str, *args, **kwargs):
        defn = self._registry.get(name)
        if not defn:
            raise KeyError(f"Task not found: {name}")
        defn.call_count += 1
        return defn.fn(*args, **kwargs)

    def list_tasks(self, category: Optional[str] = None) -> List[Dict]:
        tasks = self._registry.values()
        if category:
            tasks = [t for t in tasks if t.category == category]
        return [
            {"name": t.name, "description": t.description,
             "category": t.category, "tags": t.tags,
             "call_count": t.call_count}
            for t in tasks
        ]

    def get_categories(self) -> List[str]:
        return list({t.category for t in self._registry.values()})
