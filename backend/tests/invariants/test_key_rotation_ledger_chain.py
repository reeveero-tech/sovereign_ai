# -*- coding: utf-8 -*-
"""
R-698 — التزام التصويب الأمني: حدث KEY_ROTATED لا يكسر سلسلة prev_hash.

العيب المُثبت (المرحلة صفر 2026-10-20، على 71fa4dd):
`KeyRotation._write_rotation_event` كان يُلحق سطر JSON خامًا (بلا hash ولا
prev_hash ولا blob ولا signature) في ledger النواة الافتراضي — فتصير
`verify_content_integrity` = CORRUPTED عند أول دوران على المؤسسة الحية،
والحدث نفسه غير موقّع رغم ادعاء التعليق «موقّعًا بالمفتاح الجديد».

مسار كسر ثانٍ يغطيه هذا الملف: النواة الحية تحتفظ بآخر تجزئة في الذاكرة —
فلو كتب كاتب آخر حدثًا موسلسلًا في الملف نفسه، ستبني النواة الحية حدثها
التالي على تجزئة قديمة فتكسر السلسلة. الإصلاح يعيد مزامنة آخر تجزئة من
القرص تحت القفل قبل كل إلحاق.

كلها عبر المسار الفعلي (SovereignCore + KeyRing + KeyRotation حقيقية في
دليل مؤقت) — المسار الافتراضي للدوران نفسه (SOVEREIGN_DATA_ROOT) لا مسار
منفصل.
"""

import json
from pathlib import Path

import pytest

from backend.sovereign.keys.keyring import KeyRing
from backend.sovereign.keys.rotation import KeyRotation
from backend.sovereign.keys.verifier import SignatureVerifier, VerificationStatus
from backend.memory.core import SovereignCore, EventType, IntegrityStatus


def _core_at(data_root: Path, keyring) -> SovereignCore:
    """نواة حقيقية بتخطيط المسار الافتراضي نفسه: <root>/sovereign_core/..."""
    sc = data_root / "sovereign_core"
    sc.mkdir(parents=True, exist_ok=True)
    (sc / "blobs").mkdir(exist_ok=True)
    return SovereignCore(
        log_file=sc / "ledger.jsonl",
        blobs_dir=sc / "blobs",
        index_file=sc / "index.json",
        meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json",
        sovereign_key="test_master_key_1234567890abcdef",
        keyring=keyring,
    )


def _keyring(tmp_path: Path) -> KeyRing:
    kr = KeyRing(keys_dir=tmp_path / "keys")
    kr.generate_new_key(reason="r698-fix-baseline")
    kr.save_to_disk()
    return kr


def _events(core: SovereignCore):
    return [json.loads(l) for l in
            core.log_file.read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.fixture
def live(tmp_path, monkeypatch):
    """مؤسسة حية: جذر بيانات + KeyRing + نواة بحدثين صالحين + دوران بالمسار
    الافتراضي (بلا ledger_path — يُشتق من SOVEREIGN_DATA_ROOT)."""
    data_root = tmp_path / "data"
    monkeypatch.setenv("SOVEREIGN_DATA_ROOT", str(data_root))
    kr = _keyring(tmp_path)
    core = _core_at(data_root, kr)
    core.append_event(EventType.INTERACTION, {"r698": "before-1"})
    core.append_event(EventType.RESPONSE, {"r698": "before-2"})
    assert core.verify_content_integrity() == IntegrityStatus.VERIFIED
    rotation = KeyRotation(kr)  # المسار الافتراضي — ledger النواة نفسه
    assert rotation.ledger_path == core.log_file, (
        "الاختبار يجب أن يمارس المسار الافتراضي: ledger الدوران = ledger النواة"
    )
    return data_root, kr, core, rotation


def test_rotation_on_core_ledger_keeps_integrity_verified(live):
    """الثغرة نفسها: الدوران على ledger النواة الافتراضي يُبقي السلسلة
    سليمة (كان: CORRUPTED عند السطر 3، prev_hash=None)."""
    data_root, kr, core, rotation = live
    new_key = rotation.rotate(reason="r698-security-fix")
    assert new_key is not None
    fresh = _core_at(data_root, kr)  # يُعيد القراءة من القرص
    assert fresh.verify_content_integrity() == IntegrityStatus.VERIFIED, (
        "KEY_ROTATED كسر سلسلة prev_hash في ledger النواة"
    )


def test_key_rotated_event_is_chained_and_signed_by_new_key(live):
    """الحدث نفسه: موسلسل (prev_hash = تجزئة الحدث السابق)، يحمل key_id
    الجديد، موقّع ويُتحقق VERIFIED، ومحتواه (old/new/reason) داخل blob
    المُجزّأ — لا حقول علوية غير موثقة."""
    data_root, kr, core, rotation = live
    old_key = kr.get_active_key()
    before = _events(core)
    new_key = rotation.rotate(reason="r698-security-fix")
    after = _events(core)
    assert len(after) == len(before) + 1
    ev = after[-1]
    assert ev["type"] == "KEY_ROTATED"
    assert ev["prev_hash"] == before[-1]["hash"], "KEY_ROTATED غير موسلسل"
    for field in ("hash", "blob", "time", "signature"):
        assert ev.get(field), f"KEY_ROTATED بلا حقل {field}"
    assert ev["key_id"] == new_key.key_id
    assert SignatureVerifier(kr).verify_event(ev).status == VerificationStatus.VERIFIED, (
        "KEY_ROTATED يجب أن يكون موقّعًا بالمفتاح الجديد ويُتحقق"
    )
    payload = _core_at(data_root, kr).get_payload(ev)
    assert payload["new_key_id"] == new_key.key_id
    assert payload["old_key_id"] == old_key.key_id
    assert payload["reason"] == "r698-security-fix"


@pytest.mark.parametrize("key_type", ["hmac", "ed25519"])
def test_live_core_appends_after_rotation_keep_chain(live, key_type):
    """مسار الكسر الثاني: النواة الحية (نسخة غير التي كتبت KEY_ROTATED)
    تُلحق بعد الدوران — يجب أن تبني على KEY_ROTATED لا على تجزئتها
    المخزنة في الذاكرة. لنوعي المفتاح الجديد."""
    data_root, kr, core, rotation = live
    new_key = rotation.rotate(reason=f"r698-{key_type}", key_type=key_type)
    assert new_key is not None and new_key.key_type == key_type
    core.append_event(EventType.INTERACTION, {"r698": "after"})
    evs = _events(core)
    assert evs[-2]["type"] == "KEY_ROTATED"
    assert evs[-1]["prev_hash"] == evs[-2]["hash"], (
        "النواة الحية بنت على تجزئة قديمة في الذاكرة — كسر السلسلة"
    )
    assert _core_at(data_root, kr).verify_content_integrity() == IntegrityStatus.VERIFIED
    sv = SignatureVerifier(kr)
    assert sv.verify_event(evs[-1]).status == VerificationStatus.VERIFIED
    assert sv.verify_event(evs[-2]).status == VerificationStatus.VERIFIED


def test_rotation_with_injected_core_uses_it(tmp_path):
    """حقن النواة صراحة: الحدث يُكتب عبرها (كاتب واحد) — والنواة بحلقة
    مفاتيح مختلفة تُرفض صراحة (لا توقيع بحلقة غير التي دارت)."""
    kr = _keyring(tmp_path)
    core = _core_at(tmp_path / "data", kr)
    core.append_event(EventType.INTERACTION, {"r698": "x"})
    rotation = KeyRotation(kr, core=core)
    assert rotation.ledger_path == core.log_file
    assert rotation.rotate(reason="injected") is not None
    evs = _events(core)
    assert evs[-1]["type"] == "KEY_ROTATED"
    assert evs[-1]["prev_hash"] == evs[-2]["hash"]
    assert core.verify_content_integrity() == IntegrityStatus.VERIFIED

    other = KeyRing(keys_dir=tmp_path / "other_keys")
    other.generate_new_key(reason="other")
    with pytest.raises(ValueError):
        KeyRotation(other, core=core)
