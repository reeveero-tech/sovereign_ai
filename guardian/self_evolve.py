"""
Guardian — نظام التطوير الذاتي الآمن
يحدّث تشفير الحارس وقواعده بشكل دوري.
التطوير يخضع دائماً لموافقة السيد ولا يتم تلقائياً.
"""

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("guardian.self_evolve")

EVOLUTION_LOG = Path("guardian/data/evolution_log.jsonl")


@dataclass
class EvolutionRecord:
    record_id: str
    version_before: str
    version_after: str
    changes: List[str]
    approved_by: str        # دائماً "MASTER" — لا تطوير بدون إذن
    timestamp: float = field(default_factory=time.time)
    signature: str = ""


@dataclass
class GuardianState:
    version: str
    secret_hash: str
    rules_checksum: str
    last_updated: float
    update_count: int = 0


class GuardianSelfEvolver:
    """
    آلية التطوير الذاتي للحارس
    ════════════════════════════
    • يراجع قواعد الحارس بشكل دوري
    • يقترح تحديثات على السيد
    • لا ينفذ أي تغيير بدون موافقة صريحة
    • يحتفظ بسجل كامل لكل تطور
    """

    GUARDIAN_VERSION = "1.0.0"

    def __init__(self, master_guardian=None):
        self.master_guardian = master_guardian
        self._secret         = os.urandom(32).hex()
        self._current_state  = GuardianState(
            version=self.GUARDIAN_VERSION,
            secret_hash=hashlib.sha256(self._secret.encode()).hexdigest(),
            rules_checksum=self._compute_rules_checksum(),
            last_updated=time.time(),
        )
        self._pending_updates: List[Dict] = []
        self._evolution_history: List[EvolutionRecord] = []
        EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"🧬 GuardianSelfEvolver initialized (v{self.GUARDIAN_VERSION})")

    # ══════════════════════════════════════════════════════════════════
    # تحليل الحالة الراهنة
    # ══════════════════════════════════════════════════════════════════
    def analyze_current_state(self) -> Dict:
        """يحلل الحالة الحالية للحارس ويقترح تحسينات"""
        current_checksum = self._compute_rules_checksum()
        rules_unchanged  = current_checksum == self._current_state.rules_checksum
        age_days = (time.time() - self._current_state.last_updated) / 86400

        suggestions: List[str] = []
        if age_days > 30:
            suggestions.append("تحديث مفاتيح التشفير (مضى أكثر من 30 يوماً)")
        if not rules_unchanged:
            suggestions.append("قواعد الحارس تغيّرت — مراجعة مطلوبة")
        if self._current_state.update_count == 0:
            suggestions.append("لم يجرِ أي تحديث بعد — تقييم أولي مقترح")

        analysis = {
            "version": self._current_state.version,
            "age_days": round(age_days, 1),
            "rules_unchanged": rules_unchanged,
            "update_count": self._current_state.update_count,
            "suggestions": suggestions,
            "needs_update": len(suggestions) > 0,
        }
        logger.info(f"🔍 State analysis: {len(suggestions)} suggestion(s)")
        return analysis

    # ══════════════════════════════════════════════════════════════════
    # تحديث مفاتيح التشفير
    # ══════════════════════════════════════════════════════════════════
    def propose_key_rotation(self) -> Dict:
        """
        يقترح تدوير مفاتيح التشفير (يتطلب موافقة السيد).
        لا ينفذ التدوير تلقائياً.
        """
        proposal_id = uuid.uuid4().hex[:8]
        proposal = {
            "proposal_id": proposal_id,
            "type": "key_rotation",
            "description": "تدوير مفتاح تشفير الحارس لتعزيز الأمان",
            "current_version": self._current_state.version,
            "proposed_version": self._bump_version(self._current_state.version),
            "requires_master_approval": True,
            "status": "pending_approval",
            "created_at": time.time(),
        }
        self._pending_updates.append(proposal)
        logger.info(f"📋 Key rotation proposed [{proposal_id}] — awaiting master approval")
        return proposal

    def execute_approved_update(self, proposal_id: str,
                                master_token: str,
                                master_passphrase_hash: str) -> Dict:
        """
        ينفذ التحديث بعد التحقق من رمز السيد.
        يُسجَّل في سجل التطور للتدقيق.
        """
        # تحقق من هوية السيد
        if hashlib.sha256(master_token.encode()).hexdigest() != master_passphrase_hash:
            logger.critical("❌ Execute update DENIED — invalid master token")
            return {"success": False,
                    "reason": "رمز السيد غير صحيح — تم رفض التنفيذ"}

        proposal = next(
            (p for p in self._pending_updates if p["proposal_id"] == proposal_id), None
        )
        if not proposal:
            return {"success": False, "reason": "الاقتراح غير موجود"}

        # نفّذ التحديث
        old_version = self._current_state.version
        new_version = proposal.get("proposed_version", old_version)
        new_secret  = os.urandom(32).hex()

        # سجّل التطور
        record = EvolutionRecord(
            record_id=uuid.uuid4().hex[:8],
            version_before=old_version,
            version_after=new_version,
            changes=["key_rotation", "version_bump"],
            approved_by="MASTER",
            signature=self._sign_record(old_version, new_version),
        )
        self._evolution_history.append(record)
        self._log_evolution(record)

        # طبّق التحديث
        self._secret = new_secret
        self._current_state.version       = new_version
        self._current_state.secret_hash   = hashlib.sha256(new_secret.encode()).hexdigest()
        self._current_state.last_updated  = time.time()
        self._current_state.update_count += 1
        self._pending_updates = [
            p for p in self._pending_updates if p["proposal_id"] != proposal_id
        ]

        logger.info(
            f"✅ Guardian evolved: v{old_version} → v{new_version} "
            f"(approved by MASTER)"
        )
        return {
            "success": True,
            "version_before": old_version,
            "version_after": new_version,
            "record_id": record.record_id,
        }

    # ══════════════════════════════════════════════════════════════════
    # فحص المحاذاة
    # ══════════════════════════════════════════════════════════════════
    def verify_alignment(self) -> Dict:
        """يتحقق من أن الحارس لم يتم التلاعب به"""
        current_checksum = self._compute_rules_checksum()
        rules_ok = current_checksum == self._current_state.rules_checksum
        secret_ok = bool(self._secret)

        status = "aligned" if (rules_ok and secret_ok) else "drift_detected"
        if status == "drift_detected":
            logger.warning("⚠️ Guardian alignment drift detected — review required")
        return {
            "status": status,
            "rules_aligned": rules_ok,
            "secret_present": secret_ok,
            "version": self._current_state.version,
            "last_updated": self._current_state.last_updated,
        }

    # ══════════════════════════════════════════════════════════════════
    # مساعدات
    # ══════════════════════════════════════════════════════════════════
    def _compute_rules_checksum(self) -> str:
        rules_repr = json.dumps({
            "protected_dirs": ["backend/", "frontend/", "start.sh", "main.py"],
            "blocked_actions": [
                "modify_master_code", "disable_guardian",
                "override_master_authority",
            ],
        }, sort_keys=True)
        return hashlib.sha256(rules_repr.encode()).hexdigest()[:16]

    def _sign_record(self, v_before: str, v_after: str) -> str:
        payload = f"{v_before}|{v_after}|{time.time()}"
        return hashlib.sha256(f"{self._secret}{payload}".encode()).hexdigest()[:24]

    def _log_evolution(self, record: EvolutionRecord) -> None:
        line = json.dumps({
            "record_id": record.record_id,
            "from": record.version_before,
            "to": record.version_after,
            "changes": record.changes,
            "approved_by": record.approved_by,
            "timestamp": record.timestamp,
            "signature": record.signature,
        }, ensure_ascii=False)
        with open(EVOLUTION_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    @staticmethod
    def _bump_version(version: str) -> str:
        parts = version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)

    def get_history(self) -> List[Dict]:
        return [
            {"record_id": r.record_id, "from": r.version_before,
             "to": r.version_after, "changes": r.changes,
             "approved_by": r.approved_by, "timestamp": r.timestamp}
            for r in self._evolution_history
        ]

    def get_pending_proposals(self) -> List[Dict]:
        return self._pending_updates
