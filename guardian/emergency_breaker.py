"""
Guardian — نظام كسر الزجاج (Emergency Breaker)
الإجراءات الطارئة التي تُفعَّل عند أي تهديد حرج.

إجراءات كسر الزجاج (بالترتيب):
  1. تجميد فوري للذكاء الاصطناعي (إيقاف كل العمليات)
  2. عزل النظام عن الشبكة (محاكاة — تسجيل الأمر)
  3. إنشاء نسخة احتياطية من كود السيد
  4. إرسال تنبيه طارئ (تسجيل في ملف منفصل)
  5. قفل النظام حتى يُدخل السيد رمز إعادة التفعيل
"""

import hashlib
import json
import logging
import os
import shutil
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


logger = logging.getLogger("guardian.emergency")

EMERGENCY_LOG_DIR  = Path(_repo_path("guardian/data/emergency"))
EMERGENCY_LOG_FILE = EMERGENCY_LOG_DIR / "emergency_events.jsonl"
LOCK_FILE          = EMERGENCY_LOG_DIR / "SYSTEM_LOCKED.lock"
BACKUP_DIR         = EMERGENCY_LOG_DIR / "emergency_backups"


class BreakerState(Enum):
    ARMED    = "armed"      # جاهز للتفعيل
    ACTIVE   = "active"     # تم التفعيل
    LOCKED   = "locked"     # النظام مقفل
    RESOLVED = "resolved"   # تم الحل


@dataclass
class EmergencyIncident:
    incident_id: str
    trigger_reason: str
    triggered_by: str        # من سبّب التفعيل
    actions_taken: List[str]
    state: BreakerState
    triggered_at: float
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    backup_path: Optional[str] = None


class EmergencyBreaker:
    """
    نظام كسر الزجاج الطارئ
    ════════════════════════
    يُفعَّل تلقائياً من MasterGuardian عند:
      • محاولة تعديل كود السيد بدون إذن (مرتين أو أكثر)
      • محاولة تعطيل نظام الحارس
      • أي محاولة تجاوز صلاحيات السيد
    """

    def __init__(self, master_guardian=None):
        self.guardian = master_guardian
        self._secret  = os.urandom(32).hex()
        self.state    = BreakerState.ARMED
        self.incidents: List[EmergencyIncident] = []
        self._reactivation_code: Optional[str] = None
        self._freeze_callbacks: List[Callable] = []

        EMERGENCY_LOG_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        logger.warning("🚨 EmergencyBreaker ARMED and ready")

    # ══════════════════════════════════════════════════════════════════
    # التفعيل الرئيسي
    # ══════════════════════════════════════════════════════════════════
    def activate(self, reason: str, actor: str) -> EmergencyIncident:
        """
        تفعيل إجراءات كسر الزجاج الكاملة.
        يمر بالخطوات الخمس بالترتيب.
        """
        incident_id = uuid.uuid4().hex[:12]
        logger.critical(
            f"\n{'='*60}\n"
            f"🆘 EMERGENCY BREAKER ACTIVATED\n"
            f"Incident: {incident_id}\n"
            f"Reason:   {reason}\n"
            f"Actor:    {actor}\n"
            f"Time:     {time.ctime()}\n"
            f"{'='*60}"
        )

        actions: List[str] = []
        self.state = BreakerState.ACTIVE

        # ── خطوة 1: تجميد الذكاء الاصطناعي ─────────────────────────
        actions.extend(self._step1_freeze_ai())

        # ── خطوة 2: عزل الشبكة ──────────────────────────────────────
        actions.extend(self._step2_isolate_network())

        # ── خطوة 3: نسخ احتياطي لكود السيد ─────────────────────────
        backup_path = self._step3_backup_master_code()
        if backup_path:
            actions.append(f"نسخة احتياطية أُنشئت في: {backup_path}")

        # ── خطوة 4: إرسال تنبيه طارئ ────────────────────────────────
        actions.extend(self._step4_send_alert(incident_id, reason, actor))

        # ── خطوة 5: قفل النظام ──────────────────────────────────────
        reactivation = self._step5_lock_system(incident_id)
        actions.append(f"رمز إعادة التفعيل جاهز — يتطلب تدخل السيد")

        # إنشاء حادثة
        incident = EmergencyIncident(
            incident_id=incident_id,
            trigger_reason=reason,
            triggered_by=actor,
            actions_taken=actions,
            state=BreakerState.LOCKED,
            triggered_at=time.time(),
            backup_path=backup_path,
        )
        self.incidents.append(incident)
        self._persist_incident(incident)
        self.state = BreakerState.LOCKED
        self._reactivation_code = reactivation

        # استدعاء callbacks
        for cb in self._freeze_callbacks:
            try: cb(incident)
            # TOLERATED: callback failure must not crash emergency breaker (R-680d)
            except Exception: pass

        return incident

    def get_reactivation_code(self, incident_id: str,
                             master_token: Optional[str] = None) -> Optional[str]:
        """
        قناة تسليم رمز إعادة التفعيل للسيد (جولة المجلس <1> — اعتراض المراجع).

        الرمز لا يوضع في كائن الحادثة العام (repr/التسلسل/callbacks تمرره
        لكل مستقبل) ولا في السجلات ولا في ev.jsonl — يُستخرج عبر هذه
        الدالة من مضيف الحدث نفسه، **بعد إثبات سلطة المستدعي** عبر
        تحقق الحارس (verify_master_code) — لا تسليم بلا تفويض.
        """
        if self.state != BreakerState.LOCKED:
            return None
        for inc in self.incidents:
            if inc.incident_id != incident_id:
                continue
            # إثبات سلطة المستدعي عبر الحارس — فشل مغلق إن لم يُحقن حارس
            if self.guardian is None:
                logger.critical(
                    "❌ Refused reactivation-code delivery — no master guardian installed"
                )
                return None
            if not self.guardian.verify_master_code(master_token):
                logger.critical(
                    "❌ Refused reactivation-code delivery — invalid master token"
                )
                return None
            return self._reactivation_code
        return None

    # ══════════════════════════════════════════════════════════════════
    # خطوات التفعيل
    # ══════════════════════════════════════════════════════════════════
    def _step1_freeze_ai(self) -> List[str]:
        logger.critical("❄️ STEP 1: Freezing AI operations...")
        actions = ["تجميد جميع عمليات الذكاء الاصطناعي"]
        freeze_flag = EMERGENCY_LOG_DIR / "AI_FROZEN.flag"
        freeze_flag.write_text(
            json.dumps({"frozen_at": time.time(), "reason": "emergency_breaker"}),
            encoding="utf-8"
        )
        actions.append(f"ملف تجميد أُنشئ: {freeze_flag}")
        return actions

    def _step2_isolate_network(self) -> List[str]:
        logger.critical("🔌 STEP 2: Network isolation logged...")
        actions = ["تسجيل أمر عزل الشبكة (يتطلب تنفيذاً يدوياً في الإنتاج)"]
        isolation_log = EMERGENCY_LOG_DIR / "NETWORK_ISOLATION.log"
        isolation_log.write_text(
            f"NETWORK ISOLATION REQUESTED\n"
            f"Time: {time.ctime()}\n"
            f"Action: Disconnect all external connections\n"
            f"Note: Manual execution required in production\n",
            encoding="utf-8"
        )
        return actions

    def _step3_backup_master_code(self) -> Optional[str]:
        logger.critical("💾 STEP 3: Backing up master code...")
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"master_backup_{ts}"
        backup_path.mkdir(exist_ok=True)
        backed_up = []
        for item in ["backend", "frontend", "main.py", "start.sh"]:
            src = Path(item)
            if src.exists():
                dest = backup_path / item
                try:
                    if src.is_dir():
                        shutil.copytree(src, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dest)
                    backed_up.append(item)
                except Exception as exc:
                    logger.error(f"Backup error [{item}]: {exc}")
        logger.critical(
            f"✅ STEP 3 complete: Backed up {backed_up} → {backup_path}"
        )
        return str(backup_path) if backed_up else None

    def _step4_send_alert(self, incident_id: str,
                          reason: str, actor: str) -> List[str]:
        logger.critical("📢 STEP 4: Sending emergency alert...")
        alert = {
            "EMERGENCY_ALERT": True,
            "incident_id": incident_id,
            "reason": reason,
            "actor": actor,
            "time": time.ctime(),
            "message": (
                "تم اكتشاف محاولة تجاوز صلاحيات السيد. "
                "تم تفعيل إجراءات الطوارئ. "
                "يتطلب تدخلك الفوري."
            ),
            "required_action": "أدخل رمز إعادة التفعيل لاستعادة النظام",
        }
        alert_file = EMERGENCY_LOG_DIR / f"ALERT_{incident_id}.json"
        alert_file.write_text(
            json.dumps(alert, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.critical(f"🔴 ALERT saved to: {alert_file}")
        return ["تنبيه طارئ مسجّل في ملف JSON",
                f"ملف التنبيه: {alert_file}"]

    def _step5_lock_system(self, incident_id: str) -> str:
        logger.critical("🔒 STEP 5: Locking system...")
        reactivation_code = hashlib.sha256(
            f"{self._secret}{incident_id}{time.time()}".encode()
        ).hexdigest()[:16].upper()
        lock_data = {
            "SYSTEM_LOCKED": True,
            "incident_id": incident_id,
            "locked_at": time.time(),
            "unlock_requires": "MASTER_REACTIVATION_CODE",
            "reactivation_code_hash": hashlib.sha256(
                reactivation_code.encode()
            ).hexdigest(),
            "message": "النظام مقفل. أدخل رمز إعادة التفعيل لاستعادته.",
        }
        # ⚠️ SECURITY (جولة المجلس <1> — أمين 6.5/بصير BAS-S08/حكيم):
        # 1) ملف القفل 0600 — لا قراءة لغير السيد.
        # 2) رمز إعادة التفعيل لا يُسجّل في السجل نصًا صريحًا — يُعاد فقط
        #    في استجابة الحادثة عبر قناة الاستجابة المحدودة الجمهور.
        LOCK_FILE.write_text(
            json.dumps(lock_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        LOCK_FILE.chmod(0o600)
        logger.critical(
            f"🔒 System LOCKED [{incident_id}]. "
            f"Reactivation code delivered via incident response — NOT logged."
        )
        return reactivation_code

    # ══════════════════════════════════════════════════════════════════
    # إعادة التفعيل
    # ══════════════════════════════════════════════════════════════════
    def reactivate(self, master_code: str, incident_id: Optional[str] = None) -> Dict:
        """
        يُعيد تفعيل النظام بعد إدخال رمز السيد الصحيح.
        """
        if self.state != BreakerState.LOCKED:
            return {"success": False, "reason": "النظام ليس في حالة قفل"}

        if not LOCK_FILE.exists():
            return {"success": False, "reason": "ملف القفل غير موجود"}

        lock_data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        code_hash = hashlib.sha256(master_code.encode()).hexdigest()

        if code_hash != lock_data.get("reactivation_code_hash"):
            logger.critical(f"❌ Invalid reactivation code attempt")
            return {"success": False, "reason": "رمز التفعيل غير صحيح"}

        # إلغاء القفل
        LOCK_FILE.unlink(missing_ok=True)
        frozen = EMERGENCY_LOG_DIR / "AI_FROZEN.flag"
        frozen.unlink(missing_ok=True)

        self.state = BreakerState.RESOLVED
        # حدّث الحادثة
        if self.incidents:
            last = self.incidents[-1]
            last.resolved_at = time.time()
            last.resolved_by = "MASTER"
            last.state       = BreakerState.RESOLVED

        logger.critical("✅ System REACTIVATED by MASTER")
        return {
            "success": True,
            "message": "تم إعادة تفعيل النظام بنجاح",
            "reactivated_at": time.time(),
            "reactivated_by": "MASTER",
        }

    # ══════════════════════════════════════════════════════════════════
    # أدوات
    # ══════════════════════════════════════════════════════════════════
    def on_freeze(self, callback: Callable) -> None:
        self._freeze_callbacks.append(callback)

    def is_locked(self) -> bool:
        return LOCK_FILE.exists()

    def get_state(self) -> Dict:
        return {
            "state": self.state.value,
            "locked": self.is_locked(),
            "total_incidents": len(self.incidents),
            "last_incident": self.incidents[-1].incident_id if self.incidents else None,
        }

    def get_incidents(self) -> List[Dict]:
        return [
            {"id": i.incident_id, "reason": i.trigger_reason,
             "actor": i.triggered_by, "state": i.state.value,
             "triggered_at": i.triggered_at, "resolved_at": i.resolved_at,
             "backup": i.backup_path}
            for i in self.incidents
        ]

    def _persist_incident(self, incident: EmergencyIncident) -> None:
        line = json.dumps({
            "incident_id": incident.incident_id,
            "reason": incident.trigger_reason,
            "actor": incident.triggered_by,
            "actions": incident.actions_taken,
            "state": incident.state.value,
            "triggered_at": incident.triggered_at,
            "backup_path": incident.backup_path,
        }, ensure_ascii=False)
        with open(EMERGENCY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
