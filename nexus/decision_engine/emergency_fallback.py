"""
NexusCore — نظام الطوارئ الاحتياطي
بديل آمن لـ override_chamber.py — يدير حالات الطوارئ بشفافية كاملة.
"""
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("nexus.decision.fallback")


class FallbackLevel(Enum):
    L1_WARN    = "warn"        # تحذير فقط
    L2_PAUSE   = "pause"       # إيقاف مؤقت للمكون
    L3_ISOLATE = "isolate"     # عزل المكون
    L4_RESTORE = "restore"     # استعادة من نسخة احتياطية


@dataclass
class FallbackEvent:
    event_id: str
    level: FallbackLevel
    reason: str
    component: str
    actions_taken: List[str]
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: Optional[float] = None


class EmergencyFallback:
    """نظام الطوارئ الاحتياطي — شفاف، موثق، قابل للتدقيق"""

    def __init__(self, log_dir: str = "nexus_data/emergency"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events: List[FallbackEvent] = []
        self._handlers: Dict[str, Callable] = {}
        logger.info("🚨 EmergencyFallback initialized")

    def register_handler(self, component: str, handler: Callable) -> None:
        self._handlers[component] = handler

    def trigger(self, level: FallbackLevel, component: str, reason: str) -> FallbackEvent:
        event = FallbackEvent(
            event_id=str(uuid.uuid4())[:8],
            level=level, reason=reason, component=component,
            actions_taken=[]
        )
        logger.warning(f"🚨 Fallback [{level.value}] on {component}: {reason}")
        actions = self._execute_level(level, component, event)
        event.actions_taken = actions
        self.events.append(event)
        self._persist(event)
        return event

    def _execute_level(self, level: FallbackLevel, component: str,
                       event: FallbackEvent) -> List[str]:
        actions: List[str] = []
        if level == FallbackLevel.L1_WARN:
            actions.append(f"تسجيل تحذير لـ {component}")
            logger.warning(f"⚠️ Warning for {component}")
        elif level == FallbackLevel.L2_PAUSE:
            actions.append(f"إيقاف مؤقت لـ {component}")
            if component in self._handlers:
                try:
                    self._handlers[component]("pause")
                    actions.append("تم تنفيذ handler.pause")
                except Exception as exc:
                    actions.append(f"خطأ في handler: {exc}")
        elif level == FallbackLevel.L3_ISOLATE:
            actions.append(f"عزل {component} عن باقي النظام")
            actions.append("تسجيل حدث عزل في سجل التدقيق")
        elif level == FallbackLevel.L4_RESTORE:
            actions.append(f"بدء استعادة {component} من آخر نسخة احتياطية")
            actions.append("إشعار المشرف مطلوب لإتمام الاستعادة")
        return actions

    def resolve(self, event_id: str) -> bool:
        for ev in self.events:
            if ev.event_id == event_id and not ev.resolved:
                ev.resolved = True
                ev.resolved_at = time.time()
                logger.info(f"✅ Event {event_id} resolved")
                return True
        return False

    def _persist(self, event: FallbackEvent) -> None:
        file = self.log_dir / f"fallback_{event.event_id}.json"
        file.write_text(json.dumps({
            "event_id": event.event_id,
            "level": event.level.value,
            "reason": event.reason,
            "component": event.component,
            "actions": event.actions_taken,
            "timestamp": event.timestamp,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_active_events(self) -> List[Dict]:
        return [
            {"id": e.event_id, "level": e.level.value, "component": e.component,
             "reason": e.reason, "ts": e.timestamp}
            for e in self.events if not e.resolved
        ]
