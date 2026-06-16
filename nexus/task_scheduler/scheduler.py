"""
NexusCore — جدولة المهام الأسينكرونية
يجدول ويدير المهام المتكررة والمؤجلة.
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nexus.task_scheduler")


class TaskStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    task_id: str
    name: str
    fn: Callable
    args: tuple
    kwargs: Dict
    interval_seconds: Optional[float]   # None = одноразовая задача
    next_run: float
    status: TaskStatus = TaskStatus.PENDING
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    last_result: Any = None
    max_retries: int = 3


class TaskScheduler:
    """جدول مهام async بسيط"""

    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        logger.info("⏰ TaskScheduler initialized")

    def schedule_once(self, name: str, fn: Callable,
                      delay_seconds: float = 0,
                      args: tuple = (), kwargs: Optional[Dict] = None) -> str:
        tid = uuid.uuid4().hex[:8]
        task = ScheduledTask(
            task_id=tid, name=name, fn=fn,
            args=args, kwargs=kwargs or {},
            interval_seconds=None,
            next_run=time.time() + delay_seconds,
        )
        self.tasks[tid] = task
        logger.info(f"⏰ One-time task scheduled: {name} (delay={delay_seconds}s)")
        return tid

    def schedule_recurring(self, name: str, fn: Callable,
                           interval_seconds: float,
                           args: tuple = (), kwargs: Optional[Dict] = None) -> str:
        tid = uuid.uuid4().hex[:8]
        task = ScheduledTask(
            task_id=tid, name=name, fn=fn,
            args=args, kwargs=kwargs or {},
            interval_seconds=interval_seconds,
            next_run=time.time() + interval_seconds,
        )
        self.tasks[tid] = task
        logger.info(f"🔁 Recurring task scheduled: {name} (every {interval_seconds}s)")
        return tid

    def cancel(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if task and task.status in (TaskStatus.PENDING,):
            task.status = TaskStatus.CANCELLED
            return True
        return False

    async def run_pending(self) -> int:
        now = time.time()
        ran = 0
        for task in list(self.tasks.values()):
            if task.status == TaskStatus.CANCELLED:
                continue
            if task.status == TaskStatus.PENDING and now >= task.next_run:
                await self._execute(task)
                ran += 1
        return ran

    async def _execute(self, task: ScheduledTask) -> None:
        task.status = TaskStatus.RUNNING
        try:
            if asyncio.iscoroutinefunction(task.fn):
                result = await task.fn(*task.args, **task.kwargs)
            else:
                result = task.fn(*task.args, **task.kwargs)
            task.last_result = result
            task.run_count += 1
            task.status = TaskStatus.COMPLETED
            if task.interval_seconds:
                task.next_run = time.time() + task.interval_seconds
                task.status   = TaskStatus.PENDING
            logger.debug(f"✅ Task '{task.name}' completed (run #{task.run_count})")
        except Exception as exc:
            task.error_count += 1
            task.last_error  = str(exc)
            task.status      = TaskStatus.FAILED
            logger.error(f"❌ Task '{task.name}' failed: {exc}")
            if task.interval_seconds and task.error_count < task.max_retries:
                task.status   = TaskStatus.PENDING
                task.next_run = time.time() + task.interval_seconds

    async def start_loop(self, poll_interval: float = 1.0) -> None:
        self._running = True
        logger.info("▶️ TaskScheduler loop started")
        while self._running:
            await self.run_pending()
            await asyncio.sleep(poll_interval)

    def stop(self) -> None:
        self._running = False

    def get_all_tasks(self) -> List[Dict]:
        return [
            {"id": t.task_id, "name": t.name, "status": t.status.value,
             "runs": t.run_count, "errors": t.error_count,
             "next_run": t.next_run, "recurring": t.interval_seconds is not None}
            for t in self.tasks.values()
        ]
