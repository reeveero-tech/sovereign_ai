# backend/sovereign/keys/verifier.py
# SignatureVerifier — التحقق من توقيعات الأحداث (المرحلة 1 من ROADMAP_V2)
#
# الغرض: يميّز بدقة بين ثلاث حالات مختلفة:
# 1. VERIFIED — الحدث موقّع بمفتاح معروف وصالح
# 2. UNVERIFIABLE_MISSING_KEY — لا نعرف (المفتاح فُقد)
# 3. INVALID — نعرف أنه مزوّر (التوقيع لا يطابق المفتاح المعروف)
#
# القاعدة الصارمة: لا خلط بين UNVERIFIABLE_MISSING_KEY و INVALID أبدًا.

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .keyring import KeyRing, KeyRecord, KeyStatus

logger = logging.getLogger("sovereign.keys.verifier")


class VerificationStatus(str, Enum):
    """حالة التحقق من توقيع حدث"""
    VERIFIED = "verified"                      # موقّع بمفتاح معروف وصالح
    UNVERIFIABLE_MISSING_KEY = "unverifiable_missing_key"  # لا نعرف — المفتاح فُقد
    INVALID = "invalid"                       # نعرف أنه مزوّر


@dataclass
class VerificationResult:
    """نتيجة التحقق من حدث واحد"""
    status: VerificationStatus
    key_id: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "key_id": self.key_id,
            "reason": self.reason,
        }


class SignatureVerifier:
    """
    يتحقق من توقيعات الأحداث باستخدام KeyRing.

    المنطق:
    1. يستخرج key_id من الحدث (إن وُجد)
    2. يبحث عن المفتاح في KeyRing
    3. إذا وُجد → تحقق فعلي (تطابق التوقيع)
    4. إذا لم يوجد → UNVERIFIABLE_MISSING_KEY (ليس INVALID)
    5. إذا وُجد لكن التوقيع لا يطابق → INVALID (مزوّر)
    """

    def __init__(self, keyring: KeyRing):
        self.keyring = keyring

    @staticmethod
    def _compute_signature(data: str, private_key: str) -> str:
        """يحسب HMAC-SHA256 للتوقيع (نفس منطق memory/core.py)."""
        return hmac.new(
            private_key.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def extract_event_data(event: Dict) -> str:
        """
        يستخرج البيانات المُوقّعة من حدث (نفس صيغة memory/core.py).
        
        R-620: الصيغة الجديدة تشمل key_id في بيانات التوقيع:
        {hash}|{prev_hash}|{blob}|{time}|{type}|{key_id}
        
        الأحداث التاريخية (بلا key_id): الصيغة القديمة بلا key_id.
        """
        key_id_part = event.get("key_id") or ""
        return f"{event['hash']}|{event['prev_hash']}|{event['blob']}|{event['time']}|{event['type']}|{key_id_part}"

    def verify_event(self, event: Dict) -> VerificationResult:
        """
        يتحقق من توقيع حدث واحد.

        المنطق:
        1. إذا كان الحدث يحمل key_id → ابحث عنه في KeyRing
           - إذا وُجد → تحقق فعلي
           - إذا لم يوجد → UNVERIFIABLE_MISSING_KEY
        2. إذا كان الحدث لا يحمل key_id (قديم — LEGACY_PRE_KEYRING) →
           UNVERIFIABLE_MISSING_KEY (لا نعرف أي مفتاح استُخدم)
        """
        # R-698 (المسار المزدوج — أمر المالك): نوع التوقيع يُكتشف من الحدث
        # نفسه — صريحًا لا استنتاجًا:
        # - sig_type غائب أو "hmac" → المسار التاريخي الحالي (HMAC-SHA256).
        # - sig_type صريح "ed25519" → Ed25519Verifier.
        # - أي نوع آخر → رفض صريح INVALID (لا تخفيض تلقائي إلى HMAC).
        sig_type = event.get("sig_type")
        if sig_type == "ed25519":
            from .ed25519_verifier import Ed25519Verifier
            return Ed25519Verifier(self.keyring).verify_event(event)
        if sig_type is not None and sig_type != "hmac":
            return VerificationResult(
                status=VerificationStatus.INVALID,
                key_id=event.get("key_id"),
                reason=(
                    f"unknown sig_type '{sig_type}' — explicit rejection "
                    f"(no automatic fallback to HMAC)"
                ),
            )

        event_data = self.extract_event_data(event)
        event_key_id = event.get("key_id")

        if not event_key_id:
            # حدث قديم — LEGACY_PRE_KEYRING (لا يحمل key_id)
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                reason="LEGACY_PRE_KEYRING: event has no key_id (pre-KeyRing era)"
            )

        # ابحث عن المفتاح
        key_record = self.keyring.get_key(event_key_id)
        if key_record is None:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                key_id=event_key_id,
                reason=f"key_id {event_key_id} not found in KeyRing"
            )

        # وُجد المفتاح — تحقق فعلي
        if key_record.private_key is None:
            # المفتاح معروف لكن الخاص به مفقود (فُقد)
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                key_id=event_key_id,
                reason=f"key {event_key_id} exists but private_key is lost"
            )

        # ملاحظة مهمة (R-615): إذا كان المفتاح معروفًا لكن حالته LOST،
        # فالأحداث الموقعة به يجب أن تكون UNVERIFIABLE_MISSING_KEY (وليس VERIFIED).
        # السبب: المفتاح مفقود تاريخيًا — لا نستطيع التحقق، لكننا لا نستطيع
        # أيضًا ادعاء التزوير. (لو تحققنا فعليًا بالمفتاح، سنُعيد VERIFIED
        # رغم أن المفتاح مُعلّم كمفقود — هذا تناقض.)
        if key_record.status == KeyStatus.LOST:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                key_id=event_key_id,
                reason=f"key {event_key_id} is marked LOST — cannot verify, not claiming forgery"
            )

        # R-698 (عزل الأنواع — الاتجاه الآخر): حدث بلا sig_type منسوب لمفتاح
        # Ed25519 → رفض صريح INVALID — لا يُحسب HMAC ببذرة Ed25519 أبدًا.
        if getattr(key_record, "key_type", "hmac") == "ed25519":
            return VerificationResult(
                status=VerificationStatus.INVALID,
                key_id=event_key_id,
                reason=(
                    f"type mismatch: event has no sig_type (historical HMAC) but "
                    f"key {event_key_id} is ed25519 — explicit rejection"
                ),
            )

        # ⚠️ SECURITY (جولة المجلس <1> — أمين 3.3/بصير BAS-D03/حكيم):
        # فحص HMAC أولًا متى توفرت مادة المفتاح — التزوير يُكشف (INVALID)
        # مهما كانت حالة المفتاح. الحدث المزوّر المنسوب لمفتاح RETIRED
        # كان يُصنّف UNVERIFIABLE فلا يُعلّم مزوّرًا — الآن يُعلّم.
        # مفتاح COMPROMISED/EXPIRED/RETIRED بتوقيع مطابق لا يُعاد VERIFIED
        # أبدًا (سياسة R-668 محفوظة) — يبقى UNVERIFIABLE.
        expected = self._compute_signature(event_data, key_record.private_key)
        actual = event.get("signature", "")
        signature_matches = hmac.compare_digest(expected, actual)

        if not signature_matches:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                key_id=event_key_id,
                reason=(
                    f"signature does not match known key {event_key_id} "
                    f"(status {key_record.status.value}) — possible tampering"
                ),
            )

        # R-668 (البوابة 5 — إصلاح الثغرة): مفتاح COMPROMISED/EXPIRED/RETIRED
        # لا يُعاد VERIFIED — التحقق به غير موثوق (المفتاح مخترق/منتهي/مستبدل).
        # RETIRED: تحقق تاريخي مشروط — لا يُعاد VERIFIED (لأن المفتاح مُستبدل).
        # COMPROMISED: مخترق — لا يُعاد VERIFIED.
        # EXPIRED: منتهي — لا يُعاد VERIFIED.
        if key_record.status in (KeyStatus.COMPROMISED, KeyStatus.EXPIRED, KeyStatus.RETIRED):
            status_names = {
                KeyStatus.COMPROMISED: "COMPROMISED",
                KeyStatus.EXPIRED: "EXPIRED",
                KeyStatus.RETIRED: "RETIRED",
            }
            status_name = status_names[key_record.status]
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                key_id=event_key_id,
                reason=(
                    f"key {event_key_id} is {status_name} — "
                    f"signature matches but key is not trusted (not VERIFIED)"
                ),
            )

        # تحقق فعلي — HMAC (مطابق + ACTIVE)
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            key_id=event_key_id,
            reason="signature matches known key"
        )

    def verify_batch(self, events: List[Dict]) -> Dict[str, int]:
        """
        يتحقق من مجموعة أحداث ويُعيد إحصائيات مفصلة.
        """
        stats = {
            "total": len(events),
            "verified": 0,
            "unverifiable_missing_key": 0,
            "invalid": 0,
        }
        for ev in events:
            result = self.verify_event(ev)
            stats[result.status.value] += 1
        return stats

    def classify_ledger(self, ledger_path) -> Dict:
        """
        يُصنّف كل الأحداث في ملف ledger (JSONL) ويُعيد تقريرًا كاملًا.

        هذا هو جوهر "لا حدث بدون تصنيف" من معايير القبول.
        """
        import json as _json
        from pathlib import Path

        ledger_path = Path(ledger_path)
        if not ledger_path.exists():
            return {"error": f"ledger not found: {ledger_path}"}

        stats = {
            "total_events": 0,
            "verified": 0,
            "unverifiable_missing_key": 0,
            "invalid": 0,
            "legacy_pre_keyring": 0,   # أحداث بدون key_id
        }

        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = _json.loads(line)
                except Exception:
                    stats["invalid"] += 1
                    continue

                stats["total_events"] += 1
                if "key_id" not in event:
                    stats["legacy_pre_keyring"] += 1

                result = self.verify_event(event)
                stats[result.status.value] += 1

        return stats
