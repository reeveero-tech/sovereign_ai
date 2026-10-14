# backend/sovereign/keys/__init__.py
# الوحدة السيادية للمفاتيح (المرحلة 1 من ROADMAP_V2)
# الغرض: بناء نظام إدارة مفاتيح تاريخي كامل (KeyRing) + تحقق + تدوير.
# المبدأ: "لا نُصلح الماضي، بل نُثبّته" — الأحداث القديمة لا يُعاد
# توقيعها (تزوير)، ولا تُحذف (إنكار). تُصنّف كـ UNVERIFIABLE_MISSING_KEY.

from .keyring import KeyRing, KeyRecord, KeyStatus
from .verifier import SignatureVerifier, VerificationResult, VerificationStatus
from .rotation import KeyRotation

__all__ = [
    "KeyRing",
    "KeyRecord",
    "KeyStatus",
    "SignatureVerifier",
    "VerificationResult",
    "VerificationStatus",
    "KeyRotation",
]
