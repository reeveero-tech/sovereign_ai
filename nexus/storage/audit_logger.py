"""
NexusCore — مسجل التدقيق
يسجل جميع العمليات الحساسة مع ختم زمني وتوقيع.
"""
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.storage.audit")


@dataclass
class AuditEvent:
    event_id: str
    timestamp: float
    actor: str
    action: str
    resource: str
    details: Dict
    result: str       # success / failure / warning
    signature: str    # تحقق من سلامة السجل


class AuditLogger:
    """مسجل التدقيق الأمني — لا يمكن التراجع عن سجلاته"""

    def __init__(self, log_dir: str = "nexus_data/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._buffer: List[AuditEvent] = []
        self._secret = os.urandom(16).hex()
        logger.info(f"📋 AuditLogger initialized at {self.log_dir}")

    def log(self, actor: str, action: str, resource: str,
            details: Optional[Dict] = None, result: str = "success") -> AuditEvent:
        import uuid
        event_id = str(uuid.uuid4())
        ts = time.time()
        payload = f"{event_id}|{ts}|{actor}|{action}|{resource}|{result}"
        sig = hashlib.sha256(f"{self._secret}{payload}".encode()).hexdigest()[:16]
        event = AuditEvent(
            event_id=event_id, timestamp=ts, actor=actor,
            action=action, resource=resource,
            details=details or {}, result=result, signature=sig
        )
        self._buffer.append(event)
        self._persist(event)
        return event

    def _persist(self, event: AuditEvent) -> None:
        date_str = time.strftime("%Y-%m-%d", time.gmtime(event.timestamp))
        log_file = self.log_dir / f"audit_{date_str}.jsonl"
        line = json.dumps({
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "actor": event.actor,
            "action": event.action,
            "resource": event.resource,
            "details": event.details,
            "result": event.result,
            "signature": event.signature,
        }, ensure_ascii=False)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def query(self, actor: Optional[str] = None,
              action: Optional[str] = None,
              result: Optional[str] = None,
              limit: int = 100) -> List[AuditEvent]:
        filtered = self._buffer
        if actor:
            filtered = [e for e in filtered if e.actor == actor]
        if action:
            filtered = [e for e in filtered if e.action == action]
        if result:
            filtered = [e for e in filtered if e.result == result]
        return filtered[-limit:]

    def get_stats(self) -> Dict:
        return {
            "total_events": len(self._buffer),
            "log_files": len(list(self.log_dir.glob("*.jsonl"))),
        }
