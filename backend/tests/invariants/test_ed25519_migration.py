# backend/tests/invariants/test_ed25519_migration.py
"""
R-698 — هجرة Ed25519 (المسار المزدوج: HMAC تاريخي + Ed25519 جديد).

الاختبارات الأربعة الإلزامية (أمر المالك R-698) + متجهات RFC 8032 + عزل
الأنواع. كلها عبر المسار الفعلي (SovereignCore.append_event + KeyRing حقيقي
في دليل مؤقت) — لا أحداث مصنوعة يدويًا إلا حيث يُختبر الرفض الصريح نفسه.
"""

import json
import sys
from pathlib import Path

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from backend.sovereign.keys.keyring import KeyRing
from backend.sovereign.keys.verifier import (
    SignatureVerifier,
    VerificationStatus,
)
from backend.sovereign.keys import ed25519_verifier
from backend.memory.core import SovereignCore, EventType, IntegrityStatus


def _make_core(tmp_path, keyring):
    """SovereignCore حقيقي بمسارات مؤقتة وKeyRing محقون — المسار الفعلي."""
    sc_dir = tmp_path / "sovereign_core"
    sc_dir.mkdir(parents=True, exist_ok=True)
    (sc_dir / "blobs").mkdir(exist_ok=True)
    return SovereignCore(
        log_file=sc_dir / "ledger.jsonl",
        blobs_dir=sc_dir / "blobs",
        index_file=sc_dir / "index.json",
        meta_file=sc_dir / "meta.json",
        integrity_file=sc_dir / "integrity.json",
        sovereign_key="test_master_key_1234567890abcdef",
        keyring=keyring,
    )


def _read_events(tmp_path):
    ledger = tmp_path / "sovereign_core" / "ledger.jsonl"
    return [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]


def _ed25519_keyring(tmp_path):
    kr = KeyRing(keys_dir=tmp_path / "keys")
    kr.generate_new_ed25519_key(reason="r698-test")
    kr.save_to_disk()
    return kr


def _hmac_keyring(tmp_path):
    kr = KeyRing(keys_dir=tmp_path / "keys")
    kr.generate_new_key(reason="r698-test")
    kr.save_to_disk()
    return kr


# ---------- المتجهات (توافق مستقل — ليس نجاح توقيعي مع محققي وحده) ----------

def test_ed25519_rfc8032_vectors():
    """متجهات RFC 8032 §7.1 (T1 وT2) حرفيًا — توافق مستقل مع المعيار."""
    # T1: رسالة فارغة
    sk1 = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
    pk1 = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    sig1 = ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
            "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    assert ed25519_verifier.public_from_seed_hex(sk1) == pk1
    assert ed25519_verifier.sign_hex(b"", sk1) == sig1
    assert ed25519_verifier.verify_hex(pk1, b"", sig1) is True
    assert ed25519_verifier.verify_hex(pk1, b"x", sig1) is False

    # T2: رسالة بايت واحد 0x72
    sk2 = "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb"
    pk2 = "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c"
    sig2 = ("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
            "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
    assert ed25519_verifier.public_from_seed_hex(sk2) == pk2
    assert ed25519_verifier.sign_hex(bytes([0x72]), sk2) == sig2
    assert ed25519_verifier.verify_hex(pk2, bytes([0x72]), sig2) is True


# ---------- الاختبارات الإلزامية الأربعة ----------

def test_ed25519_sign_and_verify(tmp_path):
    """الإلزامي ١: توليد مفتاح Ed25519 في KeyRing، إلحاق أحداث فعلية عبر
    SovereignCore، التحقق منها (VERIFIED)، ورفض العبث (INVALID)."""
    kr = _ed25519_keyring(tmp_path)
    core = _make_core(tmp_path, kr)
    core.append_event(EventType.INTERACTION, {"r698": "sign_and_verify", "n": 1})
    core.append_event(EventType.RESPONSE, {"r698": "sign_and_verify", "n": 2})

    events = _read_events(tmp_path)
    assert len(events) == 2

    # الأحداث الجديدة تحمل المؤشر الصريح وتوقيع Ed25519 (64 بايتًا سداسيًا)
    for ev in events:
        assert ev.get("sig_type") == "ed25519"
        assert len(ev["signature"]) == 128
        assert set(ev["signature"]) <= set("0123456789abcdef")

    # التحقق عبر المسار المزدوج (SignatureVerifier يوزّع على Ed25519Verifier)
    sv = SignatureVerifier(kr)
    for ev in events:
        result = sv.verify_event(ev)
        assert result.status == VerificationStatus.VERIFIED, result.reason

    # العبث يُكشف: INVALID وليس أي شيء آخر
    tampered = dict(events[0])
    tampered["signature"] = "0" * 128
    result = sv.verify_event(tampered)
    assert result.status == VerificationStatus.INVALID

    # سلامة السجل الداخلية تمر (تحقق Ed25519 بالمفتاح العام — لا إعادة توقيع)
    assert core.verify_content_integrity() == IntegrityStatus.VERIFIED

    # التحقق لا يحتاج مادة التوقيع الخاصة أبدًا: نسخة تحقق بلا البذرة —
    # المفتاح العام وحده يكفي (عكس مسار HMAC التاريخي الذي يعيد التوقيع)
    kr_pub_only = KeyRing(keys_dir=tmp_path / "keys")
    kr_pub_only.load_from_disk()
    for rec in kr_pub_only.list_keys():
        rec.private_key = None  # إزالة مادة التوقيع الخاصة من جهة التحقق
    sv_pub_only = SignatureVerifier(kr_pub_only)
    for ev in events:
        result = sv_pub_only.verify_event(ev)
        assert result.status == VerificationStatus.VERIFIED, result.reason
    core_pub_only = _make_core(tmp_path, kr_pub_only)
    assert core_pub_only.verify_content_integrity() == IntegrityStatus.VERIFIED


def test_legacy_hmac_signature_still_verifies(tmp_path):
    """الإلزامي ٢: الدعم المزدوج — أحداث HMAC التاريخية (بلا sig_type)
    تظل تُتحقق بالمسار الحالي كما هي. اختبار عدم ارتداد."""
    kr = _hmac_keyring(tmp_path)
    core = _make_core(tmp_path, kr)
    core.append_event(EventType.INTERACTION, {"r698": "legacy_hmac", "n": 1})

    events = _read_events(tmp_path)
    assert len(events) == 1
    ev = events[0]

    # الحدث التاريخي لا يحمل sig_type (غياب النوع = المسار التاريخي)
    assert "sig_type" not in ev
    assert len(ev["signature"]) == 64  # HMAC-SHA256 hex

    sv = SignatureVerifier(kr)
    result = sv.verify_event(ev)
    assert result.status == VerificationStatus.VERIFIED, result.reason

    assert core.verify_content_integrity() == IntegrityStatus.VERIFIED


def test_cannot_verify_ed25519_with_hmac_key(tmp_path):
    """الإلزامي ٣: عزل الأنواع صراحةً في الاتجاهين — لا تحقق متقاطع:
    - حدث Ed25519 بمفتاح HMAC → رفض صريح (INVALID).
    - حدث HMAC بمفتاح Ed25519 → رفض صريح (INVALID — لا HMAC ببذرة Ed25519).
    - نوع مجهول → رفض صريح (INVALID — لا تخفيض تلقائي إلى HMAC)."""
    # اتجاه ١: مفتاح HMAC نشط، حدث موقّع Ed25519 منسوب إليه
    kr_hmac = _hmac_keyring(tmp_path)
    core_hmac = _make_core(tmp_path, kr_hmac)
    core_hmac.append_event(EventType.INTERACTION, {"r698": "isolation", "n": 1})
    ev_hmac = _read_events(tmp_path)[0]

    kr_ed = KeyRing(keys_dir=tmp_path / "keys_ed")
    ed_key = kr_ed.generate_new_ed25519_key(reason="r698-isolation")
    # وقّع نفس بيانات الحدث بـEd25519 وانسبه لمفتاح HMAC
    ev_fake = dict(ev_hmac)
    ev_fake["sig_type"] = "ed25519"
    ev_fake["key_id"] = kr_hmac.get_active_key().key_id
    data = (
        f"{ev_fake['hash']}|{ev_fake['prev_hash']}|{ev_fake['blob']}|"
        f"{ev_fake['time']}|{ev_fake['type']}|{ev_fake['key_id']}"
    )
    ev_fake["signature"] = ed25519_verifier.sign_hex(
        data.encode("utf-8"), ed_key.private_key
    )
    sv_hmac = SignatureVerifier(kr_hmac)
    result = sv_hmac.verify_event(ev_fake)
    assert result.status == VerificationStatus.INVALID, (
        "حدث Ed25519 منسوب لمفتاح HMAC يجب أن يُرفض صراحةً"
    )

    # اتجاه ٢: مفتاح Ed25519 نشط، حدث HMAC (بلا sig_type) منسوب إليه
    kr_ed2 = _ed25519_keyring(tmp_path / "ed2")
    ed_active = kr_ed2.get_active_key()
    ev_fake2 = dict(ev_hmac)
    ev_fake2.pop("sig_type", None)
    ev_fake2["key_id"] = ed_active.key_id
    data2 = (
        f"{ev_fake2['hash']}|{ev_fake2['prev_hash']}|{ev_fake2['blob']}|"
        f"{ev_fake2['time']}|{ev_fake2['type']}|{ev_fake2['key_id']}"
    )
    ev_fake2["signature"] = ed25519_verifier.sign_hex(  # أي توقيع غير HMAC
        data2.encode("utf-8"), ed_active.private_key
    )
    sv_ed = SignatureVerifier(kr_ed2)
    result2 = sv_ed.verify_event(ev_fake2)
    assert result2.status == VerificationStatus.INVALID, (
        "حدث بلا نوع منسوب لمفتاح Ed25519 يجب أن يُرفض صراحةً (لا HMAC ببذرة Ed25519)"
    )

    # نوع مجهول → رفض صريح لا تخفيض تلقائي
    ev_unknown = dict(ev_hmac)
    ev_unknown["sig_type"] = "rot13_super_sig"
    result3 = sv_hmac.verify_event(ev_unknown)
    assert result3.status == VerificationStatus.INVALID


def test_rotation_from_hmac_to_ed25519_preserves_history(tmp_path):
    """الإلزامي ٤: الدوران من مفتاح HMAC إلى مفتاح Ed25519 عبر مسار الدوران
    العام (KeyRotation.rotate) — التاريخ يُحفظ: المفتاح القديم يُقاعد
    (سياسة RETIRED القائمة كما هي — لا تغيير)، حدثه التاريخي يظل صحيحًا
    تشفيريًا (التوقيع يطابق) مع تصنيفه وفق سياسة الثقة القائمة
    (UNVERIFIABLE — ليس INVALID)، والمفاتيح تُحفظ وتُعاد تحميلًا بأنواعها،
    والأحداث الجديدة تُوقّع Ed25519 وتُتحقق VERIFIED."""
    from backend.sovereign.keys.rotation import KeyRotation

    kr = _hmac_keyring(tmp_path)
    core = _make_core(tmp_path, kr)
    core.append_event(EventType.INTERACTION, {"r698": "before_rotation"})

    old_key = kr.get_active_key()
    old_event = _read_events(tmp_path)[0]
    assert old_event["key_id"] == old_key.key_id
    assert "sig_type" not in old_event

    # الدوران عبر المسار العام — إلى Ed25519 (ledger الدوران منفصل هنا
    # لعزل فحص التاريخ. R-698 تصويب أمني: KEY_ROTATED صار حدث سلسلة موقّعًا
    # — حالة ledger النواة نفسه مغطاة في test_key_rotation_ledger_chain.py)
    rotation = KeyRotation(kr, ledger_path=tmp_path / "rotation_ledger.jsonl")
    new_key = rotation.rotate(reason="r698-hmac-to-ed25519", key_type="ed25519")
    assert new_key is not None
    assert new_key.key_type == "ed25519"
    assert kr.get_active_key().key_id == new_key.key_id

    # المفتاح القديم قُعد (لا حذف) — سياسة الحالة القائمة كما هي
    old_after = kr.get_key(old_key.key_id)
    assert old_after.status.value == "retired"

    # أحداث جديدة بعد الدوران — موقعة Ed25519 وتُتحقق VERIFIED
    core.append_event(EventType.RESPONSE, {"r698": "after_rotation"})
    events = _read_events(tmp_path)
    assert events[-1]["sig_type"] == "ed25519"
    assert events[-1]["key_id"] == new_key.key_id
    sv = SignatureVerifier(kr)
    assert sv.verify_event(events[-1]).status == VerificationStatus.VERIFIED

    # الحدث التاريخي: التوقيع ما زال صحيحًا تشفيريًا (إعادة الحساب بالمفتاح
    # القديم تطابق) — والتصنيف وفق سياسة RETIRED القائمة: UNVERIFIABLE
    # (ليس INVALID — ليس تزويرًا؛ وليس VERIFIED — المفتاح غير موثوق بعد الدوران)
    expected_old = sv._compute_signature(
        SignatureVerifier.extract_event_data(old_event), old_after.private_key
    )
    assert expected_old == old_event["signature"]
    result_old = sv.verify_event(old_event)
    assert result_old.status == VerificationStatus.UNVERIFIABLE_MISSING_KEY
    assert "RETIRED" in result_old.reason or "retired" in result_old.reason

    # الحفظ وإعادة التحميل: المفاتيح التاريخية محفوظة بأنواعها
    kr2 = KeyRing(keys_dir=tmp_path / "keys")
    kr2.load_from_disk()
    old_loaded = kr2.get_key(old_key.key_id)
    new_loaded = kr2.get_key(new_key.key_id)
    assert old_loaded is not None and old_loaded.key_type == "hmac"
    assert new_loaded is not None and new_loaded.key_type == "ed25519"
    assert old_loaded.public_key == old_key.public_key  # البصمة محفوظة

    # سجل HISTORY الإلحاقي يوثق الدورة كاملة
    history_lines = (tmp_path / "keys" / "HISTORY.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    actions = [json.loads(l).get("action") for l in history_lines if l.strip()]
    assert "KEY_CREATED" in actions
    assert "KEY_RETIRED" in actions

    # سلامة السجل ككل تمر بعد الدوران (القديم HMAC والجديد Ed25519 معًا)
    assert core.verify_content_integrity() == IntegrityStatus.VERIFIED
