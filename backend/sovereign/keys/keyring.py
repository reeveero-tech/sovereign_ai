# backend/sovereign/keys/keyring.py
# KeyRing — نظام المفاتيح السيادي (المرحلة 1 من ROADMAP_V2)
#
# الغرض: يحمل كل المفاتيح التي استُخدمت في تاريخ النظام، مع لكل مفتاح
# هوية وسبب التقاعد. هذا يجعل فقدان المفتاح حدثًا موثقًا (وليس كارثة
# صامتة)، ويجعل الأحداث القديمة مصنّفة (UNVERIFIABLE_MISSING_KEY وليس INVALID).
#
# القاعدة الصارمة: سجل data/keys/HISTORY.jsonl لا يُحذف منه سطر أبدًا.

import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("sovereign.keys.keyring")


class KeyStatus(str, Enum):
    """حالة المفتاح في دورة حياته"""
    ACTIVE = "active"
    RETIRED = "retired"
    LOST = "lost"           # فُقد — الأحداث الموقعة به UNVERIFIABLE
    COMPROMISED = "compromised"
    EXPIRED = "expired"


@dataclass
class KeyRecord:
    """
    سجل مفتاح واحد في الـ KeyRing.

    يحمل كل المعلومات اللازمة للتحقق من الأحداث الموقعة بهذا المفتاح،
    وسبب تقاعده إن تقاعد.
    """
    key_id: str                    # فريد — sha256 أول 16 حرفًا من المفتاح
    public_key: str                # بصمة عامة (آمنة للنشر)
    private_key: Optional[str]      # المفتاح الفعلي (None إذا فُقد/تقاعد)
    valid_from: str                # ISO8601
    valid_until: Optional[str]     # ISO8601 (None = ما زال صالحًا)
    status: KeyStatus
    reason_for_retirement: Optional[str] = None  # "lost"|"rotated"|"compromised"|"expired"
    notes: str = ""

    def to_dict(self) -> Dict:
        """يُعيد نسخة dict قابلة للـ JSON (بدون المفتاح الخاص للنشر)"""
        d = asdict(self)
        # لا يُنشر المفتاح الخاص في الواجهات العامة (سرية)
        if d.get("private_key"):
            d["private_key"] = "***redacted***"
        d["status"] = self.status.value
        return d

    def to_full_dict(self) -> Dict:
        """يُعيد نسخة كاملة (للتخزين الداخلي فقط — لا يُنشر)"""
        d = asdict(self)
        d["status"] = self.status.value
        return d


class KeyRing:
    """
    يحمل كل المفاتيح التاريخية للنظام.

    التخزين:
    - data/keys/keyring.json — الحالة الحالية (كل المفاتيح + حالتها)
    - data/keys/HISTORY.jsonl — سجل إلحاقي لا يُحذف منه سطر أبدًا
      (كل تغيير حالة يُسجّل هنا)

    الاستخدام:
    - load_from_disk() → يُعيد KeyRing محمّلًا
    - get_key(key_id) → KeyRecord أو None
    - verify_key(key_id, signature, data) → bool
    - rotate(reason) → يُنشئ مفتاحًا جديدًا ويُقاعد القديم
    """

    def __init__(self, keys_dir: Optional[Path] = None):
        if keys_dir is None:
            # المسار الافتراضي — يُحترم SOVEREIGN_DATA_ROOT للعزل
            data_root = os.getenv("SOVEREIGN_DATA_ROOT")
            if data_root:
                keys_dir = Path(data_root) / "keys"
            else:
                # جذر المستودع
                repo_root = Path(__file__).resolve().parent.parent.parent.parent
                keys_dir = repo_root / "data" / "keys"

        self.keys_dir = Path(keys_dir)
        self.keyring_file = self.keys_dir / "keyring.json"
        self.history_file = self.keys_dir / "HISTORY.jsonl"

        # R-621: fallback للقراءة فقط — إذا كان keyring.json غير موجود في الجذر المعزول
        # (اختباري)، يُحاول القراءة من المسار الحقيقي (data/keys/keyring.json).
        # هذا يجعل الاختبارات المعزولة تُحمّل المفتاح الفعلي، دون كتابة عليه.
        self._readonly_fallback: Optional[Path] = None
        if not self.keyring_file.exists():
            _repo_root = Path(__file__).resolve().parent.parent.parent.parent
            _real_keyring = _repo_root / "data" / "keys" / "keyring.json"
            if _real_keyring.exists():
                self._readonly_fallback = _real_keyring

        # المفاتيح في الذاكرة
        self._keys: Dict[str, KeyRecord] = {}
        self._active_key_id: Optional[str] = None

        # ضمان وجود المجلد
        self.keys_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # التحميل والحفظ
    # ============================================================

    def load_from_disk(self) -> "KeyRing":
        """يُحمّل الحالة من القرص. إذا لم يوجد ملف، يبدأ فارغًا.
        
        R-621: إذا كان الجذر معزولًا (اختباري) و keyring.json غير موجود،
        يُحمّل من المسار الحقيقي (قراءة فقط) — لضمان أن الاختبارات
        تستخدم المفتاح الفعلي، دون كتابة عليه.
        """
        # R-621: تحديد الملف الذي سيُقرأ (الحقيقي أو المعزول أو fallback)
        _load_file = self.keyring_file
        if not self.keyring_file.exists() and self._readonly_fallback is not None:
            _load_file = self._readonly_fallback

        if _load_file.exists():
            try:
                data = json.loads(_load_file.read_text(encoding="utf-8"))
                for kd in data.get("keys", []):
                    rec = KeyRecord(
                        key_id=kd["key_id"],
                        public_key=kd["public_key"],
                        private_key=kd.get("private_key"),
                        valid_from=kd["valid_from"],
                        valid_until=kd.get("valid_until"),
                        status=KeyStatus(kd["status"]),
                        reason_for_retirement=kd.get("reason_for_retirement"),
                        notes=kd.get("notes", ""),
                    )
                    self._keys[rec.key_id] = rec
                self._active_key_id = data.get("active_key_id")
            except Exception as e:
                logger.error(f"❌ فشل تحميل KeyRing: {e}")
        else:
            logger.info("ℹ️ KeyRing فارغ — أول تهيئة")
        return self

    def save_to_disk(self) -> bool:
        """يحفظ الحالة إلى القرص (لا يُحذف أي سطر من HISTORY)."""
        try:
            data = {
                "keys": [k.to_full_dict() for k in self._keys.values()],
                "active_key_id": self._active_key_id,
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self.keyring_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            return True
        except Exception as e:
            logger.error(f"❌ فشل حفظ KeyRing: {e}")
            return False

    def _append_history(self, entry: Dict) -> None:
        """
        يُضيف سطرًا إلى HISTORY.jsonl — سجل إلحاقي لا يُحذف منه سطر أبدًا.
        (هذا هو جوهر 'لا حذف' في الدستور — حتى التقاعد يُسجَّل ولا يُمحى.)
        """
        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"❌ فشل كتابة HISTORY.jsonl: {e}")

    # ============================================================
    # إدارة المفاتيح
    # ============================================================

    @staticmethod
    def compute_key_id(private_key: str) -> str:
        """يُحسب key_id فريد من المفتاح (sha256 أول 16 حرفًا)."""
        return hashlib.sha256(private_key.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def compute_public_fingerprint(private_key: str) -> str:
        """بصمة عامة آمنة للنشر (لا تكشف المفتاح)."""
        return hashlib.sha256(
            ("public:" + private_key).encode("utf-8")
        ).hexdigest()

    def generate_new_key(self, reason: str = "initial") -> KeyRecord:
        """يُنشئ مفتاحًا سياديًا جديدًا (لا يُقاعد أي مفتاح — فقط يُنشئ)."""
        private_key = secrets.token_urlsafe(32)
        key_id = self.compute_key_id(private_key)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        rec = KeyRecord(
            key_id=key_id,
            public_key=self.compute_public_fingerprint(private_key),
            private_key=private_key,
            valid_from=now,
            valid_until=None,  # ما زال نشطًا
            status=KeyStatus.ACTIVE,
            reason_for_retirement=None,
            notes=reason,
        )
        self._keys[key_id] = rec
        self._active_key_id = key_id

        # تسجيل في HISTORY (إلحاقي — لا حذف)
        self._append_history({
            "ts": now,
            "action": "KEY_CREATED",
            "key_id": key_id,
            "public_key": rec.public_key,
            "reason": reason,
        })
        return rec

    def get_key(self, key_id: str) -> Optional[KeyRecord]:
        """يُعيد KeyRecord بالمفتاح المحدد أو None."""
        return self._keys.get(key_id)

    def get_active_key(self) -> Optional[KeyRecord]:
        """يُعيد المفتاح النشط الحالي (أو None)."""
        if self._active_key_id:
            return self._keys.get(self._active_key_id)
        return None

    def list_keys(self) -> List[KeyRecord]:
        """يُعيد كل المفاتيح (مرتبة زمنيًا)."""
        return sorted(self._keys.values(), key=lambda k: k.valid_from)

    def retire_key(self, key_id: str, reason: str, notes: str = "") -> bool:
        """
        يُقعد مفتاحًا (لا يُحذف — فقط يُغيّر حالته ويُسجّل السبب).
        """
        rec = self._keys.get(key_id)
        if rec is None:
            logger.warning(f"⚠️ retire_key: المفتاح {key_id} غير موجود")
            return False

        rec.status = KeyStatus.RETIRED
        rec.reason_for_retirement = reason
        rec.valid_until = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if notes:
            rec.notes = (rec.notes + " | " + notes) if rec.notes else notes

        # إذا كان المفتاح النشط، نُبطل النشط
        if self._active_key_id == key_id:
            self._active_key_id = None

        # تسجيل في HISTORY
        self._append_history({
            "ts": rec.valid_until,
            "action": "KEY_RETIRED",
            "key_id": key_id,
            "reason": reason,
            "notes": notes,
        })
        return True

    def mark_key_lost(self, key_id: str, notes: str = "") -> bool:
        """
        يُعلّم مفتاحًا كمفقود (LOST).
        الأحداث الموقعة به تصبح UNVERIFIABLE_MISSING_KEY (ليست INVALID).
        """
        rec = self._keys.get(key_id)
        if rec is None:
            return False
        rec.status = KeyStatus.LOST
        rec.reason_for_retirement = "lost"
        rec.notes = (rec.notes + " | " + notes) if notes else rec.notes
        if self._active_key_id == key_id:
            self._active_key_id = None

        self._append_history({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": "KEY_MARKED_LOST",
            "key_id": key_id,
            "notes": notes,
        })
        return True

    # ============================================================
    # إحصائيات
    # ============================================================

    def stats(self) -> Dict:
        """يُعيد إحصائيات سريعة عن الـ KeyRing."""
        keys = list(self._keys.values())
        return {
            "total_keys": len(keys),
            "active": sum(1 for k in keys if k.status == KeyStatus.ACTIVE),
            "retired": sum(1 for k in keys if k.status == KeyStatus.RETIRED),
            "lost": sum(1 for k in keys if k.status == KeyStatus.LOST),
            "compromised": sum(1 for k in keys if k.status == KeyStatus.COMPROMISED),
            "expired": sum(1 for k in keys if k.status == KeyStatus.EXPIRED),
            "active_key_id": self._active_key_id,
        }
