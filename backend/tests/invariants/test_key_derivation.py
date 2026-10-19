"""
R-697 — فصل اشتقاق المفاتيح الغرضي من SOVEREIGN_KEY (HKDF-SHA256)

تنفيذ قرار المالك D-033: مفتاح مستقل مشتق لكل غرض، ممنوع استخدام مفتاح
واحد في أكثر من غرض. الأغراض الستة (الجولة R-697 — أمر المالك):
  signing / encryption / keyring_identity / phoenix_seed / phoenix_ash / api_auth

سبعة اختبارات، كل منها كُتب قبل التنفيذ وشُوهد فشله فعليًا (RED) ثم نجاحه
(GREEN) — السجلان في forensics/R-697_HKDF.md.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")

from backend.sovereign.keys.derivation import PURPOSES, derive_key  # noqa: E402
from config import SOVEREIGN_KEY  # noqa: E402


def test_derive_key_deterministic():
    """نفس المدخلات → نفس المفتاح دائمًا (حتمية كاملة)."""
    a = derive_key("signing")
    b = derive_key("signing")
    c = derive_key("signing", root_key=SOVEREIGN_KEY)
    assert isinstance(a, bytes)
    assert len(a) == 32
    assert a == b
    assert a == c  # نفس الجذر صراحةً = نفس الناتج
    # جذر مختلف → مفتاح مختلف (العزل عن الجذر)
    assert derive_key("signing", root_key="another_root_key_123") != a


def test_derive_key_purpose_isolated():
    """مفتاح كل غرض مستقل: signing ≠ encryption ≠ keyring_identity (+ أزواج أخرى)."""
    keys = {p: derive_key(p) for p in sorted(PURPOSES)}
    values = list(keys.values())
    # كل المفاتيح الستة متمايزة زوجيًا
    assert len(set(values)) == len(values), f"تصادم بين مفاتيح الأغراض: {keys}"
    # الأزواج المنصوص عليها في أمر الجولة
    assert keys["signing"] != keys["encryption"]
    assert keys["encryption"] != keys["keyring_identity"]
    assert keys["phoenix_seed"] != keys["phoenix_ash"]
    assert keys["api_auth"] != keys["signing"]
    assert keys["phoenix_seed"] != keys["api_auth"]


def test_derive_key_unknown_purpose_rejected():
    """غرض غير معروف → ValueError صريح (لا صمت ولا مفتاح افتراضي)."""
    with pytest.raises(ValueError):
        derive_key("definitely_not_a_purpose")
    with pytest.raises(ValueError):
        derive_key("")
    with pytest.raises(ValueError):
        derive_key("Signing")  # حساسية حالة — لا تمرير صامت


def test_signing_key_differs_from_root():
    """مفتاح التوقيع ≠ SOVEREIGN_KEY الخام (ولا اشتقاق ساذج منه)."""
    signing = derive_key("signing")
    root = SOVEREIGN_KEY.encode("utf-8")
    assert signing != root
    # ليس مجرد sha256 للجذر — بل HKDF كامل
    assert signing != hashlib.sha256(root).digest()
    assert signing != hashlib.sha3_256(root).digest()


def test_encryption_uses_derived_key_not_root():
    """فحص سلوكي: تشفير ختم الهوية يستدعي derive_key بغرض 'encryption' صريحًا."""
    from backend.consciousness import identity_core

    core = identity_core.IdentityCore()
    called_purposes = []
    original = identity_core.derive_key

    def spy(purpose, *args, **kwargs):
        called_purposes.append(purpose)
        return original(purpose, *args, **kwargs)

    payload = json.dumps({"round": "R-697", "value": "سيادي"})
    with mock.patch.object(identity_core, "derive_key", side_effect=spy):
        encrypted = core._encrypt_seal(payload)
        decrypted = core._decrypt_seal(encrypted)

    # دورة كاملة عبر المفتاح المشتق — نفس الصيغة (hex XOR) لا غير
    assert decrypted == payload
    assert "encryption" in called_purposes, (
        "تشفير الختم لم يستدعِ derive_key بغرض 'encryption' — ما زال يستخدم الجذر مباشرة"
    )


def test_legacy_decrypt_path_exists_and_writes_nothing_new():
    """المسار القديم (مفتاح الجذر) يقرأ فقط؛ أي كتابة جديدة به تفشل."""
    from backend.consciousness import identity_core

    core = identity_core.IdentityCore()

    # (أ) المسار القديم موجود صراحةً ويقرأ بيانات شُفرت بالمفتاح الجذر (بدون اشتقاق)
    assert hasattr(identity_core.IdentityCore, "_decrypt_legacy")
    payload = json.dumps({"legacy": True, "n": 1})
    legacy_key = hashlib.sha3_256(SOVEREIGN_KEY.encode("utf-8")).digest()
    raw = payload.encode("utf-8")
    keystream = (legacy_key * (len(raw) // 32 + 1))[: len(raw)]
    legacy_ciphertext = bytes(a ^ b for a, b in zip(raw, keystream))
    assert core._decrypt_seal(legacy_ciphertext) == payload

    # (ب) الكتابة الجديدة لا تعود للجذر أبدًا: تعطيل الاشتقاق يُفشل التشفير
    def no_derivation(*args, **kwargs):
        raise RuntimeError("الاشتقاق غير متاح — لا كتابة بالمفتاح الجذر")

    with mock.patch.object(identity_core, "derive_key", side_effect=no_derivation):
        with pytest.raises(RuntimeError):
            core._encrypt_seal("أي بيانات جديدة")


def test_all_consumers_migrated():
    """فحص ثابت: لا استدعاء مباشر لـSOVEREIGN_KEY في الكود الحيّ (التوقيع/التشفير/الهوية/المصادقة) خارج وحدة الاشتقاق والمسارات الموسومة legacy (قراءة فقط)."""
    backend_root = _REPO_ROOT / "backend"
    excluded_dirs = {"__pycache__", "tests"}
    derivation_rel = "sovereign" + os.sep + "keys" + os.sep + "derivation.py"
    violations = []

    for py in backend_root.rglob("*.py"):
        rel_parts = py.relative_to(backend_root).parts
        if any(part in excluded_dirs for part in rel_parts):
            continue
        rel = py.relative_to(backend_root)
        if str(rel).replace("/", os.sep) == derivation_rel:
            continue
        if rel == Path("config.py"):
            # محمّل الجذر والبصمات — ليس مسار توقيع/تشفير
            continue
        text = py.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "SOVEREIGN_KEY" in line:
                # مسموح فقط لو وسِم سطر الاستخدام نفسه بأنه مسار legacy قراءة فقط
                if "LEGACY-ROOT-KEY" not in line:
                    violations.append(f"{rel}:{lineno}: {line.strip()}")

    assert not violations, (
        "استخدامات مباشرة غير موسومة لـSOVEREIGN_KEY خارج وحدة الاشتقاق "
        f"(يجب migrate أو وسم LEGACY-ROOT-KEY read-only):\n" + "\n".join(violations)
    )
