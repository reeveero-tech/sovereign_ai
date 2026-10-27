# backend/sovereign/keys/ed25519_verifier.py
# Ed25519Verifier — التوقيع والتحقق Ed25519 (R-698 — تنفيذ بند ٢ من ROADMAP_V3)
#
# القاعدة الصارمة (أمر المالك R-698): لا كسر التحقق التاريخي — مسار مزدوج:
# - أحداث HMAC-SHA256 التاريخية (أو بلا نوع صريح) → SignatureVerifier الحالي.
# - أحداث Ed25519 الجديدة (تحمل sig_type="ed25519" صراحة) → Ed25519Verifier هنا.
# - نوع مجهول → رفض صريح (لا تخفيض تلقائي إلى HMAC).
# - اختلاف نوع الحدث عن نوع المفتاح → رفض صريح في الاتجاهين.
#
# التنفيذ: pycryptodome (الاعتمادية المثبتة في requirements.txt) عبر
# Crypto.Signature.eddsa بوضع rfc8032 — مطابق لمتجهات RFC 8032 §7.1
# (مثبت بالاختبار test_ed25519_rfc8032_vectors — T1 وT2 حرفيًا).

import binascii
import logging
import secrets
from typing import Dict

from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa

from .verifier import VerificationResult, VerificationStatus
from .keyring import KeyStatus

logger = logging.getLogger("sovereign.keys.ed25519_verifier")

SIG_TYPE = "ed25519"


# ============================================================
# البدائيّات (RFC 8032 عبر pycryptodome)
# ============================================================

def generate_seed_hex() -> str:
    """يولّد بذرة Ed25519 (32 بايتًا سداسية عشرية — 64 حرفًا)."""
    return secrets.token_hex(32)


def public_from_seed_hex(seed_hex: str) -> str:
    """يشتق المفتاح العام (32 بايتًا خامًا سداسيًا) من البذرة."""
    key = ECC.construct(curve="Ed25519", seed=binascii.unhexlify(seed_hex))
    return binascii.hexlify(key.public_key().export_key(format="raw")).decode()


def sign_hex(data: bytes, seed_hex: str) -> str:
    """يوقّع البيانات (RFC 8032 — توقيع حتمي) — يعيد التوقيع 64 بايتًا سداسيًا."""
    key = ECC.construct(curve="Ed25519", seed=binascii.unhexlify(seed_hex))
    sig = eddsa.new(key, "rfc8032").sign(data)
    return binascii.hexlify(sig).decode()


# R-788: مسار سريع عبر OpenSSL (مكتبة cryptography). مقيس محليًا: ~0.12ms للتحقق مقابل
# ~2.45ms في pycryptodome (حساب النقاط بلغة Python). السجل الحي 138k حدثًا ⇒ /sovereignty/score
# كان يحتاج دقائق معالج ويحجب الخادم (forensics/R-788_evidence_RED.txt). الدلالة محفوظة:
# فشل المسار السريع لا يُعتمد وحده — يُعاد الحكم بالمسار القديم (فلا يتحول توقيع كان صالحًا
# إلى غير صالح أبدًا)؛ وبغياب المكتبة يعمل القديم وحده كما كان حرفيًا.
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey as _FastPub
    from cryptography.exceptions import InvalidSignature as _FastInvalid
    FAST_ED25519 = True
except ImportError:  # TOLERATED: المسار القديم (pycryptodome) يبقى صحيحًا وحده
    _FastPub = None
    _FastInvalid = Exception
    FAST_ED25519 = False

import functools as _functools


@_functools.lru_cache(maxsize=64)
def _fast_public_key(public_hex: str):
    return _FastPub.from_public_bytes(binascii.unhexlify(public_hex))


def _fast_verify(public_hex: str, data: bytes, sig_hex: str) -> bool:
    if not FAST_ED25519:
        return False
    try:
        _fast_public_key(public_hex).verify(binascii.unhexlify(sig_hex), data)
        return True
    except (_FastInvalid, ValueError, TypeError, binascii.Error):
        return False


def verify_hex(public_hex: str, data: bytes, sig_hex: str) -> bool:
    """يتحقق بالتوقيع بالمفتاح العام — يعيد False عند أي فشل (لا استثناءات).

    المفتاح العام يُخزن خامًا (32 بايتًا) ويُغلَّف هنا بصيغة X.509 SPKI
    ثابتة البنية (OID Ed25519 = 1.3.101.112) للاستيراد — لا مفاتيح خاصة أبدًا.
    """
    if _fast_verify(public_hex, data, sig_hex):
        return True  # R-788: OpenSSL — الحكم بالقبول نهائي؛ الرفض يُعاد بالمسار القديم أدناه
    try:
        raw = binascii.unhexlify(public_hex)
        spki = bytes.fromhex("302a300506032b6570032100") + raw
        public_key = ECC.import_key(spki)
        verifier = eddsa.new(public_key, "rfc8032")
        verifier.verify(data, binascii.unhexlify(sig_hex))
        return True
    except Exception:
        return False


# ============================================================
# Ed25519Verifier — نفس دلالات SignatureVerifier تمامًا
# ============================================================

class Ed25519Verifier:
    """يتحقق من أحداث ledger الموقعة بـEd25519 (sig_type="ed25519").

    نفس الفصل الصارم بين الحالات الثلاث (لا خلط أبدًا):
    - VERIFIED — مفتاح معروف صالح وتوقيع مطابق
    - UNVERIFIABLE_MISSING_KEY — لا نعرف (المفتاح فُقد)
    - INVALID — نعرف أنه مزوّر (التوقيع لا يطابق / نوع لا يطابق المفتاح)

    التحقق بالمفتاح العام فقط — لا يحتاج مادة التوقيع الخاصة أبدًا
    (عكس مسار HMAC التاريخي الذي يعيد حساب التوقيع بالمفتاح الخاص).
    """

    def __init__(self, keyring):
        self.keyring = keyring

    def verify_event(self, event: Dict) -> VerificationResult:
        event_key_id = event.get("key_id")

        if not event_key_id:
            # حدث Ed25519 بلا key_id — لا يُعرف مفتاحه (الأحداث الجديدة
            # تحمل key_id دائمًا — انعدامه في حدث ed25519 يعني خللًا)
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                reason="Ed25519 event has no key_id — cannot identify key",
            )

        key_record = self.keyring.get_key(event_key_id)
        if key_record is None:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                key_id=event_key_id,
                reason=f"key_id {event_key_id} not found in KeyRing",
            )

        # عزل الأنواع (أمر المالك R-698): حدث ed25519 منسوب لمفتاح ليس
        # Ed25519 → رفض صريح INVALID (نوع الحدث لا يطابق نوع المفتاح)
        if getattr(key_record, "key_type", "hmac") != SIG_TYPE:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                key_id=event_key_id,
                reason=(
                    f"type mismatch: event is Ed25519 but key {event_key_id} "
                    f"is {getattr(key_record, 'key_type', 'hmac')} — explicit rejection"
                ),
            )

        # LOST — لا نستطيع التحقق ولا ندّعي تزويرًا (نفس سياسة SignatureVerifier)
        if key_record.status == KeyStatus.LOST:
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                key_id=event_key_id,
                reason=f"key {event_key_id} is marked LOST — cannot verify, not claiming forgery",
            )

        # التحقق الفعلي بالمفتاح العام — يكشف التزوير مهما كانت حالة المفتاح
        event_data = (
            f"{event.get('hash', '')}|{event.get('prev_hash', '')}|"
            f"{event.get('blob', '')}|{event.get('time', '')}|"
            f"{event.get('type', '')}|{event_key_id}"
        )
        signature = event.get("signature", "")
        verified = verify_hex(key_record.public_key, event_data.encode("utf-8"), signature)

        if not verified:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                key_id=event_key_id,
                reason=(
                    f"Ed25519 signature does not match public key of {event_key_id} "
                    f"(status {key_record.status.value}) — possible tampering"
                ),
            )

        # سياسة الثقة القائمة كما هي (R-668): مفتاح COMPROMISED/EXPIRED/RETIRED
        # بتوقيع مطابق لا يُعاد VERIFIED — يبقى UNVERIFIABLE
        if key_record.status in (KeyStatus.COMPROMISED, KeyStatus.EXPIRED, KeyStatus.RETIRED):
            return VerificationResult(
                status=VerificationStatus.UNVERIFIABLE_MISSING_KEY,
                key_id=event_key_id,
                reason=(
                    f"key {event_key_id} is {key_record.status.value} — "
                    f"signature matches but key is not trusted (not VERIFIED)"
                ),
            )

        # تحقق فعلي — Ed25519 بالمفتاح العام + ACTIVE
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            key_id=event_key_id,
            reason="verified with Ed25519 public key (R-698)",
        )
