"""R-604: اختبارات سلامة ختم الهوية (Identity Seal Integrity).

تتحقق من أن ختم الهوية:
- يُنشأ بصيغة v4 ويُتحقق منه فوراً.
- يبقى سليماً عبر التطور الطبيعي (إضافة أحداث + تحديث الأنماط الأصلية).
- يكشف التلاعب (تغيير مفتاح السيد أو التوقيع).
- يبقى سليماً بعد إعادة التحميل من القرص.
- يهاجر الأختام القديمة (v3) إلى الصيغة v4 دون إنذارات تلف كاذبة.
"""

import hashlib
import json
import os
import shutil
import time

os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

from consciousness.identity_core import (
    get_identity_core,
    IDENTITY_SEAL_FILE,
    IDENTITY_DIR,
    IdentitySeal,
)


def _clean_identity_state():
    """إزالة ختم الهوية والنسخ الاحتياطية لبدء اختبار نظيف."""
    if IDENTITY_SEAL_FILE.exists():
        IDENTITY_SEAL_FILE.unlink()
    backups = IDENTITY_DIR / "backups"
    if backups.exists():
        shutil.rmtree(backups)


def _fresh_identity():
    _clean_identity_state()
    identity = get_identity_core()
    identity.seal = None
    identity.is_sealed = False
    return identity


def test_fresh_seal_verifies():
    """ختم جديد (v4) يُتحقق منه فور إنشائه."""
    identity = _fresh_identity()
    seal = identity.create_seal()
    assert seal.seal_version == 4
    assert identity.verify_seal() is True
    assert identity.is_sealed is True


def test_seal_survives_normal_archetype_drift():
    """التطور الطبيعي (تحديث الأنماط) لا يكسر الختم."""
    identity = _fresh_identity()
    identity.create_seal()
    archetypes = identity.archetypes
    for _ in range(3):
        archetypes.update_archetypes()
    assert identity.verify_seal() is True


def test_seal_survives_event_append():
    """إضافة أحداث إلى سلسلة الذاكرة لا تكسر الختم (سلسلة الذاكرة تبقى سليمة)."""
    identity = _fresh_identity()
    identity.create_seal()
    for i in range(3):
        identity.core.append_event(event_type="test::seal_event", payload={"n": i})
    assert identity.verify_seal() is True


def test_seal_detects_sovereign_key_tampering():
    """تغيير مفتاح السيد يُكتشف كتلاعب."""
    identity = _fresh_identity()
    seal = identity.create_seal()
    seal.sovereign_key_hash = "0" * 128
    assert identity.verify_seal() is False


def test_seal_detects_signature_tampering():
    """تغيير التوقيع يُكتشف كتلاعب."""
    identity = _fresh_identity()
    seal = identity.create_seal()
    seal.signature = "0" * 128
    assert identity.verify_seal() is False


def test_seal_persists_and_reloads_valid():
    """الختم يُحفظ ويُعاد تحميله سليماً."""
    identity = _fresh_identity()
    identity.create_seal()
    identity._save_seal()
    identity.seal = None
    identity.is_sealed = False
    identity._load_seal()
    assert identity.seal is not None
    assert identity.seal.seal_version == 4
    assert identity.verify_seal() is True
    assert identity.is_sealed is True


def test_legacy_v3_seal_migrates_to_v4():
    """ختم قديم (v3) يُهاجر إلى v4 ويُتحقق منه دون إنذار تلف كاذب."""
    _clean_identity_state()
    sovereign_key_hash = hashlib.sha3_512(os.environ["SOVEREIGN_KEY"].encode()).hexdigest()
    core_hash = "GENESIS"

    # بصمة قديمة متغيرة (احتمالات الأنماط)
    from memory.biological.archetypes import get_archetypes
    archetype_status = get_archetypes().get_archetype_status()
    archetype_fingerprint = hashlib.sha256(
        json.dumps(archetype_status.get("top_archetypes", []), sort_keys=True).encode()
    ).hexdigest()

    # توقيع قديم: طابع زمني مختلف عن created_at (الخطأ الأصلي)
    seal_data = f"{sovereign_key_hash}:{core_hash}:{archetype_fingerprint}:{time.time()}"
    signature = hashlib.sha3_512(seal_data.encode()).hexdigest()

    legacy = IdentitySeal(
        id="seal_legacy_test",
        created_at=time.time(),
        signature=signature,
        fingerprint=hashlib.sha3_256(seal_data.encode()).hexdigest(),
        sovereign_key_hash=sovereign_key_hash,
        core_hash=core_hash,
        archetype_fingerprint=archetype_fingerprint,
        integrity_verified=True,
        seal_version=3,
    )

    # تشفير وحفظ بصيغة v3 القديمة
    key = hashlib.sha3_256(os.environ["SOVEREIGN_KEY"].encode()).digest()
    data_bytes = json.dumps(legacy.__dict__, ensure_ascii=False).encode()
    encrypted = bytes(a ^ b for a, b in zip(data_bytes, key * (len(data_bytes) // 32 + 1)))
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True)
    with open(IDENTITY_SEAL_FILE, "wb") as f:
        f.write(encrypted)

    # التحميل عبر النواة يجب أن يهاجر الختم إلى v4 ويُتحقق منه
    identity = get_identity_core()
    assert identity.seal is not None
    assert identity.seal.seal_version == 4
    assert identity.verify_seal() is True
    assert identity.is_sealed is True
