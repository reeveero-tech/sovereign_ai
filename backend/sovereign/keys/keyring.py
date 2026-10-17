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
import stat as statmod
import tempfile
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
        # ⚠️ SECURITY (جولة المجلس <1> — اعتراض المراجع): علم «فشل التحميل»
        # يمنع أي حفظ لاحق فوق ملف تالف — لا يُستبدل ملف فشل تحميله.
        self._load_failed = False

        # R-621 (معطل — R-634): كان fallback للقراءة فقط — إذا كان keyring.json
        # غير موجود في الجذر المعزول، يُحاول القراءة من المسار الحقيقي.
        # R-634 (من مراجعة المستشار): هذا يكسر العزل — الجذر المعزول يجب
        # ألا يتجاوز إلى أسرار التشغيل. عُطّل السلوك (لا حذف — الأثر محفوظ
        # غير مفعّل احترامًا لقيد عدم الحذف).
        #
        # Affect السابق (معطل):
        #   self._readonly_fallback: Optional[Path] = None
        #   if not self.keyring_file.exists():
        #       _repo_root = Path(__file__).resolve().parent.parent.parent.parent
        #       _real_keyring = _repo_root / "data" / "keys" / "keyring.json"
        #       if _real_keyring.exists():
        #           self._readonly_fallback = _real_keyring
        self._readonly_fallback: Optional[Path] = None  # R-634: معطل دائمًا

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
        
        R-634: fallback معطل — الجذر المحدد (keys_dir) حدٌّ لا يتجاوزه إلى
        أسرار التشغيل. إذا كان فارغًا، يبقى فارغًا (لا قراءة من المسار الحقيقي).
        """
        if self.keyring_file.exists():
            try:
                data = json.loads(self.keyring_file.read_text(encoding="utf-8"))
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
                # ⚠️ SECURITY (جولة المجلس <1> — أمين 3.2/بصير BAS-S14 + اعتراض المراجع):
                # فشل مغلق مزدوج: (1) ملف تالف يرفع استثناء — لا يُحمّل صمتًا
                # كفارغ، (2) علم _load_failed يمنع أي حفظ لاحق فوقه حتى لو
                # التقط المستدعي الاستثناء وواصل — فلا تضيع المفاتيح القائمة.
                self._load_failed = True
                logger.error(f"❌ فشل تحميل KeyRing — ملف تالف: {e}")
                raise ValueError(
                    f"فشل تحميل KeyRing (فشل مغلق — جولة المجلس <1>): "
                    f"{self.keyring_file} تالف أو غير صالح"
                ) from e
        else:
            logger.info("ℹ️ KeyRing فارغ — أول تهيئة")
        return self

    def save_to_disk(self) -> bool:
        """
        يحفظ الحالة إلى القرص (لا يُحذف أي سطر من HISTORY).

        ⚠️ SECURITY (جولة المجلس <1> — بصير BAS-S01/S14/أمين 3.1/حكيم):
        كتابة ذرية بأذونات ضيقة — ملف مؤقت 0600 + os.replace، ودليل
        0700. فشل الاستبدال لا يتلف النسخة السابقة (لا write_text
        مباشر على الملف النهائي).
        """
        # ⚠️ SECURITY (اعتراض المراجع على الجولة <1>): رفض الحفظ بعد فشل
        # تحميل — حتى لو التقط المستدعي استثناء التحميل وواصل، لا يُستبدل
        # الملف التالف بمحتوى جديد فتضيع المفاتيح القائمة.
        if self._load_failed:
            logger.error(
                "❌ رفض حفظ KeyRing: التحميل السابق فشل (_load_failed) — "
                "لا يُستبدل ملف تالف؛ افحص الملف يدويًا أولًا"
            )
            return False
        tmp_path = None
        try:
            self.keys_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            # إن كان الدليل قائمًا بأذونات أوسع — نضيّقه، والفشل يُسقط الحفظ
            # صراحة (لا ابتلاع صامت: ضمان 0700 جزء من العقد الأمني).
            current_mode = statmod.S_IMODE(self.keys_dir.stat().st_mode)
            if current_mode & 0o077:
                self.keys_dir.chmod(0o700)
                if statmod.S_IMODE(self.keys_dir.stat().st_mode) & 0o077:
                    raise OSError(
                        f"تعذر تضييق أذونات دليل المفاتيح إلى 0700 "
                        f"(الحالي {oct(statmod.S_IMODE(self.keys_dir.stat().st_mode))})"
                    )
            data = {
                "keys": [k.to_full_dict() for k in self._keys.values()],
                "active_key_id": self._active_key_id,
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            payload = json.dumps(data, ensure_ascii=False, indent=2)
            # ملف مؤقت فريد بإنشاء حصري (0600 افتراضيًا من mkstemp) داخل
            # دليل المفاتيح — ثم استبدال ذري. لا إعادة استخدام اسم ثابت
            # (اعتراض المراجع: O_CREAT|O_TRUNC لا يضبط أذونات ملف قائم).
            fd, tmp_name = tempfile.mkstemp(
                prefix=".keyring.", suffix=".tmp", dir=str(self.keys_dir)
            )
            tmp_path = Path(tmp_name)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, self.keyring_file)
            tmp_path = None  # استُبدل بنجاح
            return True
        except Exception as e:
            logger.error(f"❌ فشل حفظ KeyRing: {e}")
            # TOLERATED: تنظيف الملف المؤقت بعد فشل الحفظ — فشل التنظيف
            # لا يُسقط العملية (اسم الملف المؤقت فريد فلا يُشاركه أحد).
            if tmp_path is not None:
                try:
                    if tmp_path.exists():
                        tmp_path.unlink()
                except OSError:
                    pass
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
        """يُعيد المفتاح النشط الحالي (أو None).
        
        R-633: يتحقق أن المفتاح نشط فعلًا (ACTIVE) — المفاتيح المخترقة
        أو المتقاعدة أو المفقودة لا تُعاد كمفتاح نشط.
        """
        if self._active_key_id:
            rec = self._keys.get(self._active_key_id)
            if rec is None:
                return None
            # R-633: فقط ACTIVE يُعاد (COMPROMISED/RETIRED/LOST/EXPIRED → None)
            if rec.status != KeyStatus.ACTIVE:
                return None
            return rec
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

    def mark_key_compromised(self, key_id: str, reason: str = "") -> bool:
        """
        R-633: يُعلّم مفتاحًا كمخترق (COMPROMISED).
        
        - لا يُستخدم للكتابة أبدًا (فشل مُغلق في append_event)
        - أحداثه التاريخية تُتحقق (لا يُمنع التحقق — فقط الكتابة)
        - يُسجّل في HISTORY (لا حذف)
        """
        rec = self._keys.get(key_id)
        if rec is None:
            return False
        rec.status = KeyStatus.COMPROMISED
        rec.reason_for_retirement = f"compromised: {reason}" if reason else "compromised"
        if self._active_key_id == key_id:
            self._active_key_id = None

        self._append_history({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": "KEY_MARKED_COMPROMISED",
            "key_id": key_id,
            "reason": reason,
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
