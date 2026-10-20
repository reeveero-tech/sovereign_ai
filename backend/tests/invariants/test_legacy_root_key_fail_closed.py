# -*- coding: utf-8 -*-
"""
R-699 — مفتاح الجذر التاريخي: لا ثابت مكشوف بديلًا (fail-closed).

العيب (اكتُشف 2026-10-20 بعد تصويب R-698):
`SovereignCore.__init__` كان يستبدل مفتاح الجذر الفارغ أو الافتراضي بالثابت
المكشوف في الكود `b'new_generated_key_here'`، و`verify_integrity` يتحقق من
الأحداث التاريخية (بلا key_id) بهذا المفتاح. فأي من يملك كتابة ملف ledger
يستطيع تزوير حدث تاريخي موقّع بالثابت العلني فيُعلن السجل VERIFIED.
كما أن HMAC بمفتاح فارغ قابل للحساب لأي أحد، والقيمة الافتراضية العربية في
fallback الاستيراد (`يجب_تغيير_هذا_المفتاح_فوراً`) لم تكن ضمن قائمة الرفض.

الإصلاح: بلا مفتاح جذر حقيقي لا يوجد مفتاح تحقق تاريخي إطلاقًا — الأحداث
التاريخية لا تُعلن VERIFIED (PARTIAL: تحقق غير مكتمل، لا ادعاء تلاعب).
"""

import json

import pytest

from backend.memory.core import (
    SovereignCore, EventType, IntegrityStatus, compute_hmac, utc_now_iso,
)
from backend.sovereign.keys.keyring import KeyRing

_PUBLIC_WEAK_KEYS = [
    "",
    "you_must_change_this_key_immediately",
    "يجب_تغيير_هذا_المفتاح_فوراً",
]
_PUBLIC_FALLBACK_CONSTANT = b"new_generated_key_here"


def _paths(root):
    sc = root / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    return dict(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json",
    )


def _write_legacy_event(core: SovereignCore, signing_key: bytes) -> None:
    """حدث بصيغة تاريخية (بلا key_id) — سلسلة وblob صحيحان، والتوقيع بالمفتاح
    المعطى. هذه صيغة المهاجم: يملك كتابة الملف لا المفتاح الحقيقي."""
    blob = core.blob_store.put(json.dumps({"forged": True}).encode("utf-8"),
                               compress=True)
    t = utc_now_iso()
    etype = EventType.INTERACTION.value
    ehash = core._compute_event_hash("GENESIS", blob, t, etype)
    sig = compute_hmac(f"{ehash}|GENESIS|{blob}|{t}|{etype}".encode("utf-8"),
                       signing_key)
    event = {"hash": ehash, "prev_hash": "GENESIS", "blob": blob, "time": t,
             "type": etype, "signature": sig}
    with open(core.log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


@pytest.mark.parametrize("weak", _PUBLIC_WEAK_KEYS)
@pytest.mark.parametrize("forge_key", [_PUBLIC_FALLBACK_CONSTANT, b"", None],
                         ids=["public_constant", "empty_key", "weak_key_itself"])
def test_forged_legacy_event_not_verified_without_real_root_key(
        tmp_path, weak, forge_key):
    """بمفتاح جذر ضعيف/فارغ: حدث تاريخي مزوّر بمفتاح علني لا يُعلن VERIFIED
    (الثابت البديل، المفتاح الفارغ، أو القيمة الضعيفة العلنية نفسها)."""
    if forge_key is None:
        forge_key = weak.encode("utf-8")
    p = _paths(tmp_path)
    core = SovereignCore(**p, sovereign_key=weak, keyring=None)
    _write_legacy_event(core, forge_key)
    fresh = SovereignCore(**p, sovereign_key=weak, keyring=None)
    status = fresh.verify_integrity(verbose=True)
    assert status != IntegrityStatus.VERIFIED, (
        f"حدث مزوّر بمفتاح علني {forge_key!r} أُعلن VERIFIED بمفتاح جذر {weak!r}"
    )
    assert status == IntegrityStatus.PARTIAL


def test_no_public_constant_as_legacy_key(tmp_path):
    """لا مادة مفتاح علنية: مفتاح الجذر الضعيف لا يُستبدل بثابت من الكود."""
    for weak in _PUBLIC_WEAK_KEYS:
        core = SovereignCore(**_paths(tmp_path / str(len(weak))),
                             sovereign_key=weak, keyring=None)
        assert core.signing_key is None, (
            f"مفتاح جذر ضعيف {weak!r} استُبدل بمادة {core.signing_key!r}"
        )


def test_genuine_legacy_event_still_verifies_with_real_root_key(tmp_path):
    """عدم ارتداد: حدث تاريخي موقّع بمفتاح الجذر الحقيقي يبقى VERIFIED، والمزوّر
    بالثابت العلني يصير CORRUPTED (التوقيع لا يطابق المفتاح الحقيقي)."""
    real = "a-real-legacy-root-key-0123456789abcdef"
    p = _paths(tmp_path / "ok")
    core = SovereignCore(**p, sovereign_key=real, keyring=None)
    _write_legacy_event(core, real.encode("utf-8"))
    assert SovereignCore(**p, sovereign_key=real, keyring=None) \
        .verify_integrity(verbose=True) == IntegrityStatus.VERIFIED

    p2 = _paths(tmp_path / "forged")
    core2 = SovereignCore(**p2, sovereign_key=real, keyring=None)
    _write_legacy_event(core2, _PUBLIC_FALLBACK_CONSTANT)
    assert SovereignCore(**p2, sovereign_key=real, keyring=None) \
        .verify_integrity(verbose=True) == IntegrityStatus.CORRUPTED


def test_keyring_events_unaffected_without_root_key(tmp_path):
    """الأحداث الجديدة (KeyRing) لا تعتمد على مفتاح الجذر: VERIFIED حتى بلا جذر."""
    kr = KeyRing(keys_dir=tmp_path / "keys")
    kr.generate_new_key(reason="r699")
    p = _paths(tmp_path)
    core = SovereignCore(**p, sovereign_key="", keyring=kr)
    core.append_event(EventType.INTERACTION, {"r699": 1})
    core.append_event(EventType.RESPONSE, {"r699": 2})
    assert SovereignCore(**p, sovereign_key="", keyring=kr) \
        .verify_integrity(verbose=True) == IntegrityStatus.VERIFIED
