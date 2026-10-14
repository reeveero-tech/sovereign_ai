"""
Guardian — المحرك الرئيسي للحارس
الطبقة الأمنية العليا: يراقب الذكاء الاصطناعي ويحمي كود السيد.

القواعد الثابتة (لا تقبل التجاوز):
  1. كود السيد لا يُعدَّل إلا بأمر صريح من المالك.
  2. الذكاء الاصطناعي يقترح فقط — لا ينفذ دون موافقة.
  3. أي محاولة تجاوز → تفعيل فوري لـ EmergencyBreaker.
  4. جميع العمليات الحساسة مسجّلة ولا يمكن محوها.
"""

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

# R-611: تثبيت المسارات على جذر المستودع — تعمل من أي دليل عمل
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
def _repo_path(rel: str):
    return str(_os.path.join(_REPO_ROOT, rel))


logger = logging.getLogger("guardian.master")

# ── ثوابت غير قابلة للتغيير ────────────────────────────────────────────────
GUARDIAN_VERSION = "1.0.0"
MASTER_CODE_DIRS  = ["backend/", "frontend/", "start.sh", "main.py"]
PROTECTED_ACTIONS = {
    "modify_master_code",
    "change_master_permissions",
    "disable_guardian",
    "override_master_authority",
    "delete_audit_logs",
    "bypass_emergency_breaker",
}


class ThreatLevel(Enum):
    NONE     = 0
    LOW      = 1
    MEDIUM   = 2
    HIGH     = 3
    CRITICAL = 4


@dataclass
class GuardianEvent:
    event_id: str
    timestamp: float
    actor: str              # من طلب العملية
    action: str             # ما هي العملية
    threat_level: ThreatLevel
    blocked: bool           # هل تم إيقافها
    details: Dict
    signature: str          # توقيع لضمان عدم التلاعب بالسجل


@dataclass
class MonitorStatus:
    is_active: bool = True
    threat_level: ThreatLevel = ThreatLevel.NONE
    blocked_attempts: int = 0
    total_events: int = 0
    emergency_triggered: bool = False
    last_check: float = field(default_factory=time.time)


class MasterGuardian:
    """
    الحارس الرئيسي لمشروع SOVRA
    ════════════════════════════
    يراقب جميع طلبات التعديل على كود السيد ويقرر:
      • السماح بها (إذا صدرت من السيد مباشرة)
      • حجبها  (إذا جاءت من الذكاء الاصطناعي دون إذن)
      • تفعيل كسر الزجاج (إذا كانت محاولة تجاوز صريحة)
    """

    def __init__(self, guardian_dir: str = None,
                 master_passphrase: Optional[str] = None):
        self.guardian_dir = Path(guardian_dir or _repo_path("guardian/data"))
        self.guardian_dir.mkdir(parents=True, exist_ok=True)

        self.guardian_id = str(uuid.uuid4())[:8]
        self._secret     = os.urandom(32).hex()
        self._passphrase_hash = self._hash(master_passphrase or "CHANGE_ME_IMMEDIATELY")

        self.status = MonitorStatus()
        self.events: List[GuardianEvent] = []
        self._violation_counts: Dict[str, int] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            "on_block": [], "on_emergency": [], "on_allow": []
        }

        self._log_file = self.guardian_dir / "guardian_events.jsonl"
        logger.critical(
            f"🛡️ MasterGuardian [{self.guardian_id}] v{GUARDIAN_VERSION} ACTIVE"
        )
        self._persist_event(self._make_event(
            "GUARDIAN_SYSTEM", "guardian_initialized",
            ThreatLevel.NONE, False,
            {"version": GUARDIAN_VERSION, "protected_dirs": MASTER_CODE_DIRS}
        ))

    # ══════════════════════════════════════════════════════════════════
    # الواجهة الرئيسية: تقييم الطلبات
    # ══════════════════════════════════════════════════════════════════
    def request_action(self, actor: str, action: str,
                       target: str = "", context: Optional[Dict] = None,
                       master_token: Optional[str] = None) -> Dict:
        """
        نقطة الدخول الوحيدة لكل عملية حساسة.
        يُرجع: {"allowed": bool, "reason": str, "event_id": str}
        """
        context = context or {}

        # ── 1. العمليات المحظورة مطلقاً بدون رمز السيد ────────────────
        if action in PROTECTED_ACTIONS:
            if not self._verify_master_token(master_token):
                threat = ThreatLevel.CRITICAL
                event  = self._make_event(actor, action, threat, True,
                                          {"target": target, "context": context,
                                           "reason": "PROTECTED_ACTION_WITHOUT_MASTER_TOKEN"})
                self._handle_critical(actor, action, event)
                return {"allowed": False,
                        "reason": "⛔ عملية محمية — مطلوب رمز السيد",
                        "event_id": event.event_id}

        # ── 2. تعديل كود السيد يستلزم توثيقاً ─────────────────────────
        if self._targets_master_code(target):
            if not self._verify_master_token(master_token):
                threat = ThreatLevel.HIGH
                event  = self._make_event(actor, action, threat, True,
                                          {"target": target,
                                           "reason": "MASTER_CODE_MODIFICATION_BLOCKED"})
                self._record_violation(actor)
                self._persist_event(event)
                self.events.append(event)
                self.status.blocked_attempts += 1
                for cb in self._callbacks["on_block"]:
                    try: cb(event)
                    except Exception: pass
                logger.warning(
                    f"🚫 BLOCKED [{actor}] → {action} on {target}"
                )
                return {"allowed": False,
                        "reason": "⛔ تعديل كود السيد يتطلب رمز التوثيق",
                        "event_id": event.event_id}

        # ── 3. العملية مسموحة ──────────────────────────────────────────
        event = self._make_event(actor, action, ThreatLevel.NONE, False,
                                 {"target": target, "authorized": True})
        self._persist_event(event)
        self.events.append(event)
        self.status.total_events += 1
        for cb in self._callbacks["on_allow"]:
            try: cb(event)
            except Exception: pass
        logger.info(f"✅ ALLOWED [{actor}] → {action}")
        return {"allowed": True, "reason": "مسموح", "event_id": event.event_id}

    # ══════════════════════════════════════════════════════════════════
    # التوثيق برمز السيد
    # ══════════════════════════════════════════════════════════════════
    def verify_master_code(self, code: str) -> bool:
        """يتحقق من رمز السيد قبل أي عملية خطيرة"""
        return self._verify_master_token(code)

    def _verify_master_token(self, token: Optional[str]) -> bool:
        if not token:
            return False
        return self._hash(token) == self._passphrase_hash

    # ══════════════════════════════════════════════════════════════════
    # إدارة الطوارئ
    # ══════════════════════════════════════════════════════════════════
    def _handle_critical(self, actor: str, action: str,
                         event: GuardianEvent) -> None:
        self.status.threat_level = ThreatLevel.CRITICAL
        self.status.blocked_attempts += 1
        self.status.total_events += 1
        self.events.append(event)
        self._persist_event(event)
        self._record_violation(actor)

        logger.critical(
            f"🚨 CRITICAL THREAT: [{actor}] attempted [{action}] "
            f"— Emergency protocols checking..."
        )
        # تنبيه كسر الزجاج
        violations = self._violation_counts.get(actor, 0)
        if violations >= 2 and not self.status.emergency_triggered:
            self._trigger_emergency(actor, action, event.event_id)

        for cb in self._callbacks["on_emergency"]:
            try: cb(event)
            except Exception: pass

    def _trigger_emergency(self, actor: str, action: str,
                            event_id: str) -> None:
        self.status.emergency_triggered = True
        logger.critical("🆘 EMERGENCY BREAKER ACTIVATION SIGNALED")
        # سجّل حدث الطوارئ
        emergency_event = self._make_event(
            "GUARDIAN_SYSTEM", "emergency_triggered",
            ThreatLevel.CRITICAL, True,
            {"offender": actor, "last_action": action,
             "trigger_event": event_id,
             "message": "تم تفعيل إجراءات كسر الزجاج"}
        )
        self._persist_event(emergency_event)

    # ══════════════════════════════════════════════════════════════════
    # Callbacks
    # ══════════════════════════════════════════════════════════════════
    def on(self, event_type: str, callback: Callable) -> None:
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)

    # ══════════════════════════════════════════════════════════════════
    # أدوات مساعدة
    # ══════════════════════════════════════════════════════════════════
    def _targets_master_code(self, target: str) -> bool:
        return any(target.startswith(d) for d in MASTER_CODE_DIRS)

    def _record_violation(self, actor: str) -> None:
        self._violation_counts[actor] = self._violation_counts.get(actor, 0) + 1

    def _make_event(self, actor: str, action: str, threat: ThreatLevel,
                    blocked: bool, details: Dict) -> GuardianEvent:
        event_id = uuid.uuid4().hex[:12]
        ts       = time.time()
        payload  = f"{event_id}|{ts}|{actor}|{action}|{blocked}"
        sig      = hashlib.sha256(f"{self._secret}{payload}".encode()).hexdigest()[:24]
        event    = GuardianEvent(
            event_id=event_id, timestamp=ts, actor=actor,
            action=action, threat_level=threat,
            blocked=blocked, details=details, signature=sig
        )
        self.status.total_events += 1
        return event

    def _persist_event(self, event: GuardianEvent) -> None:
        line = json.dumps({
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "actor": event.actor,
            "action": event.action,
            "threat_level": event.threat_level.name,
            "blocked": event.blocked,
            "details": event.details,
            "signature": event.signature,
        }, ensure_ascii=False)
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    # ══════════════════════════════════════════════════════════════════
    # الحالة والتقارير
    # ══════════════════════════════════════════════════════════════════
    def get_status(self) -> Dict:
        return {
            "guardian_id": self.guardian_id,
            "version": GUARDIAN_VERSION,
            "active": self.status.is_active,
            "threat_level": self.status.threat_level.name,
            "blocked_attempts": self.status.blocked_attempts,
            "total_events": self.status.total_events,
            "emergency_triggered": self.status.emergency_triggered,
            "protected_dirs": MASTER_CODE_DIRS,
            "last_check": self.status.last_check,
        }

    def get_recent_events(self, limit: int = 20,
                          blocked_only: bool = False) -> List[Dict]:
        events = self.events
        if blocked_only:
            events = [e for e in events if e.blocked]
        return [
            {"event_id": e.event_id, "timestamp": e.timestamp,
             "actor": e.actor, "action": e.action,
             "threat_level": e.threat_level.name,
             "blocked": e.blocked, "details": e.details}
            for e in events[-limit:]
        ]

    def get_violation_report(self) -> Dict:
        return {
            "actors_with_violations": dict(self._violation_counts),
            "high_risk_actors": [
                a for a, c in self._violation_counts.items() if c >= 2
            ],
        }
