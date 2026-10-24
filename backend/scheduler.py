"""R-732 (البند ٣.٦ — بأمر المالك «تابع»): أداة الجدولة.

مجدول داخلي يوقظ النظام دوريًا لتنفيذ مهام فحص — مبني على سجل الأدوات
الحقيقي (R-729/البند ٣.١)، لا على شيفرة حرة:

- لا ينفذ إلا أدوات مسجلة، عبر ToolRegistry.invoke(caller="scheduler") — فكل
  تشغيل يترك أثر tool_invoked موقعًا في السجل السيادي (fail-closed بنمط R-635).
- معطل افتراضيًا ويعلن السبب: كل تشغيل يُلحق حدثًا بالسجل الدائم في الإنتاج،
  فالتفعيل هناك قرار المالك: SOVEREIGN_SCHEDULER=1 (والفاصل
  SOVEREIGN_SCHEDULER_INTERVAL بالثواني، افتراضيًا 300).
- العزل: فشل الأداة أو تعذر التوقيع يُسجل في حالة المهمة ولا يوقف الحلقة.
- لا تشغيل فوري عند الإقلاع: أول تشغيل بعد فاصل كامل (لا انفجار أحداث مع كل نشر).
- الحالة (/scheduler/status) بيانات وصفية + بصمة آخر نتيجة فقط — لا نتيجة كاملة
  ولا سر (المادة ٩).
"""

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 300
ENV_ENABLE = "SOVEREIGN_SCHEDULER"
ENV_INTERVAL = "SOVEREIGN_SCHEDULER_INTERVAL"


@dataclass
class ScheduledTask:
    name: str
    tool: str
    interval_seconds: float
    runs: int = 0
    last_run: Optional[float] = None
    last_ok: Optional[bool] = None
    last_error: Optional[str] = None
    last_fingerprint: Optional[str] = None
    next_due: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tool": self.tool,
            "interval_seconds": self.interval_seconds,
            "runs": self.runs,
            "last_run": self.last_run,
            "last_ok": self.last_ok,
            "last_error": self.last_error,
            "last_fingerprint": self.last_fingerprint,
            "next_due": self.next_due,
        }


class Scheduler:
    def __init__(self, tasks: List[ScheduledTask], enabled: bool, reason: str = "") -> None:
        self.tasks = tasks
        self.enabled = enabled
        self.reason = reason
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        start = time.time()
        for t in self.tasks:
            if t.next_due is None:
                t.next_due = start + t.interval_seconds

    # ---- التنفيذ (متزامن وحتمي — تستدعيه الحلقة والاختبارات) ----
    def run_due(self, now: Optional[float] = None) -> List[Dict[str, Any]]:
        import tool_registry  # يُحل وقت التشغيل (يسمح باستبداله في الاختبارات)

        now = time.time() if now is None else now
        results = []
        with self._lock:
            for t in self.tasks:
                if t.next_due is not None and now < t.next_due:
                    continue
                t.runs += 1
                t.last_run = now
                t.next_due = now + t.interval_seconds
                try:
                    out = tool_registry.get_registry().invoke(t.tool, caller="scheduler")
                    t.last_ok = bool(out.get("ok"))
                    t.last_error = out.get("error")
                    t.last_fingerprint = out.get("trace", {}).get("result_fingerprint")
                except Exception as exc:  # أداة غير مسجلة / تعذر التوقيع — يُسجل ولا يكسر
                    t.last_ok = False
                    t.last_error = f"{type(exc).__name__}: {exc}"[:200]
                    t.last_fingerprint = None
                    logger.warning("R-732: فشل مهمة مجدولة %s — %s", t.name, t.last_error)
                results.append(t.to_dict())
        return results

    # ---- الحلقة الخلفية ----
    async def _loop(self) -> None:
        tick = max(0.2, min(1.0, min((t.interval_seconds for t in self.tasks), default=1.0)))
        try:
            while True:
                self.run_due()
                await asyncio.sleep(tick)
        except asyncio.CancelledError:  # R-732: الإلغاء إشارة الإيقاف الطبيعية من stop() — ليس خطأ
            pass

    def start(self) -> None:
        if not self.enabled or self.running:
            return
        self._task = asyncio.get_running_loop().create_task(self._loop())
        self.running = True
        logger.info("R-732: المجدول يعمل — %d مهمة", len(self.tasks))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # R-732: انتظار انتهاء الحلقة الملغاة عمدًا — الإلغاء متوقع
                pass
            self._task = None
        self.running = False

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "running": self.running,
                "reason": self.reason,
                "tasks": [t.to_dict() for t in self.tasks],
            }


def build_from_env() -> Scheduler:
    """المهام المعلنة + التفعيل من البيئة (يُقرأ عند الإقلاع)."""
    raw_interval = os.environ.get(ENV_INTERVAL, "")
    try:
        interval = float(raw_interval) if raw_interval else DEFAULT_INTERVAL_SECONDS
        if interval < 1:
            interval = DEFAULT_INTERVAL_SECONDS
    except ValueError:
        interval = DEFAULT_INTERVAL_SECONDS
    tasks = [
        # فحص ذاتي دوري: لقطة الصحة — أساس البند ٤.٣ (اكتشاف العيوب ذاتيًا)
        ScheduledTask(name="self_health_check", tool="health.snapshot", interval_seconds=interval),
        # R-743 (البند ٤.٣): دورة اكتشاف العيوب ذاتيًا — قائمة عمل في /defects/report
        ScheduledTask(name="self_defect_scan", tool="defects.scan", interval_seconds=interval),
    ]
    enabled = os.environ.get(ENV_ENABLE, "").strip() == "1"
    reason = (
        f"مفعّل ({ENV_ENABLE}=1) — كل تشغيل يُسجل في السجل السيادي"
        if enabled else
        f"معطل: {ENV_ENABLE} غير مضبوط على 1 — التفعيل في الإنتاج قرار المالك "
        "(كل تشغيل يُلحق حدثًا بالسجل الدائم)"
    )
    return Scheduler(tasks, enabled=enabled, reason=reason)
