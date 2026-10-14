"""
اختبارات الوحدة السيادية للمفاتيح (المرحلة 1 من ROADMAP_V2)
KeyRing + SignatureVerifier + KeyRotation — اختبارات حقيقية (لا mocks).

تتحقق من:
1. KeyRing: إنشاء، حفظ، تحميل، تقاعد، تعليم كمفقود
2. SignatureVerifier: التمييز بين VERIFIED / UNVERIFIABLE_MISSING_KEY / INVALID
3. KeyRotation: تدوير كامل + تسجيل KEY_ROTATED
4. القاعدة الصارمة: HISTORY.jsonl لا يُحذف منه سطر أبدًا
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.sovereign.keys import (
    KeyRing, KeyRecord, KeyStatus,
    SignatureVerifier, VerificationResult, VerificationStatus,
    KeyRotation,
)


@pytest.fixture
def isolated_keyring():
    """يُنشئ KeyRing في جذر مؤقت معزول (لا يُلمس data/ الحقيقي)."""
    tmp_root = tempfile.mkdtemp(prefix="sovereign_keyring_test_")
    keys_dir = Path(tmp_root) / "keys"
    ring = KeyRing(keys_dir=keys_dir)
    ring.load_from_disk()
    return ring, keys_dir


def test_keyring_generates_unique_keys(isolated_keyring):
    """KeyRing يُنشئ مفاتيح فريدة (key_id مختلف لكل مفتاح)."""
    ring, _ = isolated_keyring

    key1 = ring.generate_new_key(reason="test1")
    key2 = ring.generate_new_key(reason="test2")

    assert key1.key_id != key2.key_id, "each key must have unique key_id"
    assert len(key1.key_id) == 16, f"key_id should be 16 chars, got {len(key1.key_id)}"
    assert key1.status == KeyStatus.ACTIVE
    assert key2.status == KeyStatus.ACTIVE


def test_keyring_save_and_load_roundtrip(isolated_keyring):
    """KeyRing يُحفظ ويُحمّل بشكل صحيح (roundtrip)."""
    ring, keys_dir = isolated_keyring

    # إنشاء مفتاح وحفظ
    key = ring.generate_new_key(reason="roundtrip_test")
    assert ring.save_to_disk() is True

    # إنشاء KeyRing جديد وتحميل من القرص
    ring2 = KeyRing(keys_dir=keys_dir)
    ring2.load_from_disk()

    loaded = ring2.get_key(key.key_id)
    assert loaded is not None, "key must survive save/load roundtrip"
    assert loaded.key_id == key.key_id
    assert loaded.status == KeyStatus.ACTIVE
    assert loaded.private_key == key.private_key


def test_keyring_retire_key(isolated_keyring):
    """تقاعد المفتاح يُغيّر حالته ولا يحذفه أبدًا."""
    ring, _ = isolated_keyring

    key = ring.generate_new_key(reason="retire_test")
    key_id = key.key_id

    # تقاعد
    assert ring.retire_key(key_id, reason="rotated", notes="test retirement") is True

    # المفتاح ما زال موجودًا (لم يُحذف)
    retired = ring.get_key(key_id)
    assert retired is not None, "retired key must NOT be deleted"
    assert retired.status == KeyStatus.RETIRED
    assert retired.reason_for_retirement == "rotated"
    assert retired.valid_until is not None


def test_keyring_mark_lost(isolated_keyring):
    """تعليم مفتاح كمفقود (LOST) — الأحداث تصبح UNVERIFIABLE."""
    ring, _ = isolated_keyring

    key = ring.generate_new_key(reason="lost_test")
    assert ring.mark_key_lost(key.key_id, notes="original key lost") is True

    lost = ring.get_key(key.key_id)
    assert lost.status == KeyStatus.LOST
    assert lost.reason_for_retirement == "lost"


def test_keyring_history_never_deletes(isolated_keyring):
    """القاعدة الصارمة: HISTORY.jsonl لا يُحذف منه سطر أبدًا."""
    ring, keys_dir = isolated_keyring
    history_file = keys_dir / "HISTORY.jsonl"

    # إنشاء عدة مفاتيح → عدة أسطر HISTORY
    ring.generate_new_key(reason="h1")
    ring.generate_new_key(reason="h2")
    ring.generate_new_key(reason="h3")

    # HISTORY يجب أن يحتوي 3 أسطر (KEY_CREATED × 3)
    assert history_file.exists(), "HISTORY.jsonl must exist"
    lines = history_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3, f"expected 3 history lines, got {len(lines)}"

    # تقاعد مفتاح → يُضاف سطر (لا يُحذف شيء)
    key_ids = list(ring._keys.keys())
    ring.retire_key(key_ids[0], reason="rotated")

    lines_after = history_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines_after) == 4, (
        f"retirement must ADD a line (4 total), got {len(lines_after)}"
    )
    # الأسطر الثلاثة الأولى ما زالت موجودة (لم تُحذف)
    assert lines_after[:3] == lines, "original history lines must never be deleted"


def test_verifier_distinguishes_three_states(isolated_keyring):
    """
    التمييز الحاسم بين ثلاث حالات (جوهر المرحلة 1):
    1. VERIFIED — الحدث موقّع بمفتاح معروف وصالح
    2. UNVERIFIABLE_MISSING_KEY — لا نعرف (المفتاح فُقد)
    3. INVALID — نعرف أنه مزوّر (التوقيع لا يطابق المفتاح المعروف)
    """
    ring, _ = isolated_keyring
    verifier = SignatureVerifier(ring)

    # إنشاء مفتاح وحدث موقّع به
    key = ring.generate_new_key(reason="verify_test")
    event_data = "hash|prev_hash|blob|2026-10-14T00:00:00Z|test_type"
    signature = SignatureVerifier._compute_signature(event_data, key.private_key)

    signed_event = {
        "hash": "hash", "prev_hash": "prev_hash", "blob": "blob",
        "time": "2026-10-14T00:00:00Z", "type": "test_type",
        "signature": signature,
        "key_id": key.key_id,  # القاعدة الصارمة: كل حدث جديد يحمل key_id
    }

    # 1) VERIFIED — التوقيع صحيح
    result = verifier.verify_event(signed_event)
    assert result.status == VerificationStatus.VERIFIED, (
        f"correctly signed event must be VERIFIED, got {result.status}"
    )

    # 2) UNVERIFIABLE_MISSING_KEY — الحدث بدون key_id (قديم)
    legacy_event = {
        "hash": "hash", "prev_hash": "prev_hash", "blob": "blob",
        "time": "2026-10-14T00:00:00Z", "type": "test_type",
        "signature": signature,
        # لا key_id — LEGACY_PRE_KEYRING
    }
    result2 = verifier.verify_event(legacy_event)
    assert result2.status == VerificationStatus.UNVERIFIABLE_MISSING_KEY, (
        f"event without key_id must be UNVERIFIABLE_MISSING_KEY, got {result2.status}"
    )

    # 3) INVALID — التوقيع لا يطابق المفتاح المعروف (مزوّر)
    tampered_event = {
        "hash": "hash", "prev_hash": "prev_hash", "blob": "blob",
        "time": "2026-10-14T00:00:00Z", "type": "test_type",
        "signature": "0" * 64,  # توقيع مزوّر
        "key_id": key.key_id,
    }
    result3 = verifier.verify_event(tampered_event)
    assert result3.status == VerificationStatus.INVALID, (
        f"tampered signature with known key must be INVALID, got {result3.status}"
    )


def test_verifier_missing_key_id_in_keyring(isolated_keyring):
    """حدث يحمل key_id غير موجود في KeyRing → UNVERIFIABLE_MISSING_KEY."""
    ring, _ = isolated_keyring
    verifier = SignatureVerifier(ring)

    event = {
        "hash": "h", "prev_hash": "p", "blob": "b",
        "time": "2026-10-14T00:00:00Z", "type": "t",
        "signature": "s" * 64,
        "key_id": "nonexistent_key_id",
    }
    result = verifier.verify_event(event)
    assert result.status == VerificationStatus.UNVERIFIABLE_MISSING_KEY


def test_verifier_lost_key_returns_unverifiable(isolated_keyring):
    """مفتاح مفقود (LOST) → أحداثه UNVERIFIABLE_MISSING_KEY (وليست INVALID)."""
    ring, _ = isolated_keyring
    verifier = SignatureVerifier(ring)

    key = ring.generate_new_key(reason="lost_verify")
    event_data = "h|p|b|2026-10-14T00:00:00Z|t"
    sig = SignatureVerifier._compute_signature(event_data, key.private_key)

    event = {
        "hash": "h", "prev_hash": "p", "blob": "b",
        "time": "2026-10-14T00:00:00Z", "type": "t",
        "signature": sig,
        "key_id": key.key_id,
    }

    # قبل التعليم كمفقود — يجب أن يكون VERIFIED
    result_before = verifier.verify_event(event)
    assert result_before.status == VerificationStatus.VERIFIED

    # تعليم المفتاح كمفقود
    ring.mark_key_lost(key.key_id)

    # بعد التعليم — يجب أن يكون UNVERIFIABLE_MISSING_KEY (وليس INVALID)
    result_after = verifier.verify_event(event)
    assert result_after.status == VerificationStatus.UNVERIFIABLE_MISSING_KEY, (
        "lost key events must be UNVERIFIABLE_MISSING_KEY (not INVALID) — "
        "we don't know, we don't claim forgery"
    )


def test_key_rotation_full_cycle(isolated_keyring):
    """KeyRotation: تدوير كامل — مفتاح جديد + تقاعد القديم + KEY_ROTATED في ledger."""
    ring, keys_dir = isolated_keyring

    # إنشاء مفتاح أولي
    key1 = ring.generate_new_key(reason="initial")

    # ledger في جذر مؤقت معزول
    tmp_ledger = keys_dir.parent / "ledger_test.jsonl"

    rotation = KeyRotation(ring, ledger_path=tmp_ledger)

    # تدوير
    new_key = rotation.rotate(reason="test_rotation")
    assert new_key is not None, "rotation must produce a new key"
    assert new_key.key_id != key1.key_id

    # المفتاح القديم تقاعد (ولم يُحذف)
    old = ring.get_key(key1.key_id)
    assert old is not None, "old key must NOT be deleted after rotation"
    assert old.status == KeyStatus.RETIRED
    assert old.reason_for_retirement == "rotated"

    # المفتاح الجديد هو النشط
    assert ring.get_active_key().key_id == new_key.key_id

    # حدث KEY_ROTATED موجود في ledger (موقّعًا بالمفتاح الجديد)
    assert tmp_ledger.exists(), "rotation must write KEY_ROTATED to ledger"
    ledger_lines = tmp_ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(ledger_lines) >= 1
    rot_event = json.loads(ledger_lines[-1])
    assert rot_event["type"] == "KEY_ROTATED"
    assert rot_event["key_id"] == new_key.key_id  # القاعدة الصارمة
    assert rot_event["old_key_id"] == key1.key_id
    assert rot_event["reason"] == "test_rotation"


def test_keyring_stats(isolated_keyring):
    """إحصائيات KeyRing تعمل بشكل صحيح."""
    ring, _ = isolated_keyring

    k1 = ring.generate_new_key(reason="stats1")
    k2 = ring.generate_new_key(reason="stats2")
    ring.mark_key_lost(k2.key_id)

    stats = ring.stats()
    assert stats["total_keys"] == 2
    assert stats["active"] == 1
    assert stats["lost"] == 1


def test_keyring_respects_sovereign_data_root():
    """KeyRing يحترم SOVEREIGN_DATA_ROOT للعزل (نفس نمط config.py)."""
    tmp_root = tempfile.mkdtemp(prefix="sovereign_keyring_root_")
    os.environ["SOVEREIGN_DATA_ROOT"] = tmp_root
    try:
        ring = KeyRing()  # بدون keys_dir صريح
        # keys_dir يجب أن يكون داخل الجذر المؤقت
        assert str(tmp_root) in str(ring.keys_dir), (
            f"keys_dir must be under SOVEREIGN_DATA_ROOT ({tmp_root}), got {ring.keys_dir}"
        )
    finally:
        os.environ.pop("SOVEREIGN_DATA_ROOT", None)
