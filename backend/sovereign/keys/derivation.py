# backend/sovereign/keys/derivation.py
# R-697 — فصل اشتقاق المفاتيح الغرضي من SOVEREIGN_KEY (تنفيذ قرار المالك D-033)
# HKDF-SHA256 (RFC 5869): salt=None (أصفار بطول التجزئة)، info=الغرض، طول 32 بايت.
#
# القاعدة: لا يستخدم أي مسار في النظام SOVEREIGN_KEY الخام للتوقيع أو التشفير
# أو الهوية أو المصادقة — كل غرض يشتق مفتاحه الخاص من هنا. الجذر يبقى في config.py
# (تحميل وبصمات فقط) وفي مسارات legacy موسومة LEGACY-ROOT-KEY (قراءة فقط،
# للبيانات التاريخية المشفرة/الموقعة بالجذر قبل R-697 — لا كتابة جديدة به).

import hashlib
import hmac

# الأغراض الستة المعتمدة (أمر المالك — جولة R-697):
#   signing          — توقيع أحداث ledger وأفعال السلامة
#   encryption       — تشفير المخزن (ختم الهوية وبياناته)
#   keyring_identity — هوية الختم/الحلقة المرتبطة بمفتاح السيد
#   phoenix_seed     — دورة الفينيق: بذور/مفتاح الإحياء الرئيسي وتغليفه
#   phoenix_ash      — دورة الفينيق: مفاتيح موت/رماد البيانات
#   api_auth         — مصادقة API (المفتاح القياسي الجديد؛ الجذر legacy مقبول للقراءة)
PURPOSES = frozenset({
    "signing",
    "encryption",
    "keyring_identity",
    "phoenix_seed",
    "phoenix_ash",
    "api_auth",
})

_DERIVED_KEY_LEN = 32  # 256-bit
_HASH = hashlib.sha256  # HKDF-SHA256


def _hkdf_sha256(ikm: bytes, length: int, info: bytes) -> bytes:
    """HKDF-SHA256 حسب RFC 5869 — salt=None يعادل HashLen أصفارًا (Extract)،
    ثم Expand مع info. حتمي تمامًا: نفس (ikm, info) → نفس الناتج دائمًا."""
    salt = b"\x00" * 32  # salt=None → HashLen(zeros) لكل RFC 5869 §2.2
    # Extract
    prk = hmac.new(salt, ikm, _HASH).digest()
    # Expand
    okm = b""
    block = b""
    counter = 1
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), _HASH).digest()
        okm += block
        counter += 1
    return okm[:length]


def _root_key_bytes(root_key=None) -> bytes:
    """جذر الاشتقاق: الوسيط الصريح، أو SOVEREIGN_KEY من config (تحميل كسول)."""
    if root_key is not None:
        return root_key.encode("utf-8")
    try:
        from config import SOVEREIGN_KEY as _root
    except ImportError:  # بديل بيئة الاختبار — نفس نمط memory/core.py
        import os
        _root = os.getenv("SOVEREIGN_KEY", "")
    if not _root:
        raise RuntimeError("SOVEREIGN_KEY غير متاح — لا اشتقاق بدون جذر")
    return _root.encode("utf-8")


def derive_key(purpose: str, root_key=None) -> bytes:
    """اشتقاق مفتاح 32 بايتًا لغرض معين من جذر واحد.

    - غرض غير معروف → ValueError (لا صمت، لا افتراضات).
    - حتمي: نفس الجذر + نفس الغرض → نفس المفتاح دائمًا.
    - info = الغرض نفسه (وسم صريح في الاشتقاق — قابل للتكذيب من الاختبارات).
    """
    if purpose not in PURPOSES:
        raise ValueError(
            f"غرض اشتقاق غير معروف: {purpose!r} — الأغراض المعتمدة: {sorted(PURPOSES)}"
        )
    ikm = _root_key_bytes(root_key)
    return _hkdf_sha256(ikm, _DERIVED_KEY_LEN, purpose.encode("utf-8"))


def derive_key_from_module(purpose: str, module_globals: dict) -> bytes:
    """اشتقاق بجذر يُقرأ من متغيرات وحدة الاستدعاء وقت الاستدعاء.

    لوحدات الذاكرة التي تحمل نسختها من جذر السيد على مستوى الوحدة —
    قراءة الجذر من globals الوحدة تحترم monkeypatch في اختبارات الفينيق
    (تغيير الجذر يجب أن يُفشل فك الحالات القديمة — سلوك R-682 محفوظ).
    الجذر هنا إدخال اشتقاق (IKM لـ HKDF) وليس استخدامًا تشفيريًا مباشرًا."""
    root = module_globals.get("SOVEREIGN_KEY")
    return derive_key(purpose, root_key=root)


def derive_key_hex(purpose: str, root_key=None) -> str:
    """نفس derive_key بصيغة hex — للمقارنات النصية (api_auth)."""
    return derive_key(purpose, root_key=root_key).hex()
