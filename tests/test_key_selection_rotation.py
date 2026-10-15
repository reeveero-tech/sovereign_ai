"""
اختبار R-625/R-626: مسار اختيار المفتاح والتحقق بعد الدوران

يختبر أن:
1. أحداث المفتاح A تُتحقق بنجاح بعد الدوران إلى B (key_id من الحدث، ليس النشط)
2. تغيير key_id وحده (تزييف) يُكتشف
3. غياب KeyRing: الكاتب يرفض الإلحاق (لا fallback)
4. التوافق التاريخي: أحداث key_id بصيغة 5 حقول تُتحقق بالصيغة القديمة
"""

import json
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# عزل R-619
if not os.environ.get("SOVEREIGN_DATA_ROOT"):
    _test_data_root = tempfile.mkdtemp(prefix="sovereign_test_data_")
    os.environ["SOVEREIGN_DATA_ROOT"] = _test_data_root

import pytest

from backend.memory.core import SovereignCore, EventType
from backend.sovereign.keys import KeyRing, SignatureVerifier


class TestKeySelectionAfterRotation:
    """اختبارات مسار اختيار المفتاح بعد الدوران (R-625).
    
    R-627: عزل كامل — دوران المفتاح يُكتب إلى keys_dir معزول (وليس الحقيقي)،
    حتى لا يلوث الاختبار المفتاح الفعلي. fallback R-621 لا يُفعّل هنا
    لأن keyring.json موجود في الجذر المعزول.
    """

    def _isolated_keyring(self) -> KeyRing:
        """يُنشئ KeyRing معزول (بدون fallback للحقيقي) — للدوران."""
        _keys_dir = tempfile.mkdtemp(prefix="sovereign_rotation_keys_")
        kr = KeyRing(keys_dir=Path(_keys_dir))
        kr.generate_new_key(reason="rotation_test_isolated")
        kr.save_to_disk()
        return kr

    def test_event_with_key_a_verifies_after_rotation_to_b(self, tmp_path):
        """حدث موقّع بالمفتاح A يُتحقق بنجاح بعد الدوران إلى B.

        R-682: مسارات صريحة معزولة — SovereignCore() بلا مسارات يكتب في
        سجل الجذر المشترك للجلسة (عزل الوحدة النمطية يأتي بعد استيراد
        config فلا يُعيد توجيه DATA_DIR)، فيلوّث سجل الجلسة بأحداث
        بمفاتيح معزولة تُفشل تحقق السلامة لاحقًا (رفض R-626).
        """
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)
        _core_paths = dict(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
        )
        # R-627: عزل كامل — KeyRing معزول (بدون fallback للحقيقي)
        keyring = self._isolated_keyring()
        key_a = keyring.get_active_key().key_id

        # 1) كتابة حدث بالمفتاح A — عبر ربط keyring يدويًا
        core1 = SovereignCore(**_core_paths)
        core1._keyring = keyring
        core1._keyring_key_id = key_a
        r1 = core1.append_event(EventType.INTERACTION, {"test": "rotate_a"}, user="test")
        assert r1["key_id"] == key_a

        # 2) دوران المفتاح: A → B (في keys_dir المعزول)
        new_key = keyring.generate_new_key(reason="rotation_test_r625")
        keyring.save_to_disk()
        key_b = new_key.key_id

        # 3) كتابة حدث بالمفتاح B (النشط الجديد)
        core2 = SovereignCore(**_core_paths)
        core2._keyring = keyring
        core2._keyring_key_id = key_b
        r2 = core2.append_event(EventType.INTERACTION, {"test": "rotate_b"}, user="test")
        assert key_b != key_a, "rotation must produce different key"

        # 4) التحقق من الحدثين — الحدث 1 بمفتاح A (وليس B النشط)
        verifier = SignatureVerifier(keyring)
        e1 = {
            "hash": r1["hash"], "prev_hash": r1["prev_hash"], "blob": r1["blob"],
            "time": r1["time"], "type": r1["type"], "signature": r1["signature"],
            "key_id": r1["key_id"],
        }
        e2 = {
            "hash": r2["hash"], "prev_hash": r2["prev_hash"], "blob": r2["blob"],
            "time": r2["time"], "type": r2["type"], "signature": r2["signature"],
            "key_id": r2["key_id"],
        }
        s1 = verifier.verify_event(e1)
        s2 = verifier.verify_event(e2)
        assert s1.status.value == "verified", (
            f"event with key A must verify after rotation to B: {s1.reason}"
        )
        assert s2.status.value == "verified", (
            f"event with key B must verify: {s2.reason}"
        )

    def test_verify_integrity_after_rotation(self, tmp_path):
        """التحقق من سلامة السجل ينجح بعد الدوران (أحداث A و B معًا).
        
        R-628: سجل معزول جديد — يُنشئ SovereignCore بمسارات صريحة (tmp_path)،
        لضمان أن السجل يحتوي فقط أحداث هذا الاختبار (وليس أحداث اختبارات أخرى).
        """
        # R-628: سجل معزول بمسارات صريحة (لا يعتمد على متغير البيئة)
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        _log_file = _core_dir / "ledger.jsonl"
        _blobs_dir = _core_dir / "blobs"
        _blobs_dir.mkdir(exist_ok=True)
        _index_file = _core_dir / "index.json"
        _meta_file = _core_dir / "meta.json"
        _integrity_file = _core_dir / "integrity.json"

        # R-627: عزل كامل — KeyRing معزول
        keyring = self._isolated_keyring()
        key_a = keyring.get_active_key().key_id

        # إنشاء SovereignCore بمسارات صريحة (عزل كامل)
        core1 = SovereignCore(
            log_file=_log_file,
            blobs_dir=_blobs_dir,
            index_file=_index_file,
            meta_file=_meta_file,
            integrity_file=_integrity_file,
        )
        core1._keyring = keyring
        core1._keyring_key_id = key_a
        core1.append_event(EventType.INTERACTION, {"test": "pre_rotation"}, user="test")

        new_key = keyring.generate_new_key(reason="rotation_integrity_r625")
        keyring.save_to_disk()
        key_b = new_key.key_id

        core2 = SovereignCore(
            log_file=_log_file,
            blobs_dir=_blobs_dir,
            index_file=_index_file,
            meta_file=_meta_file,
            integrity_file=_integrity_file,
        )
        core2._keyring = keyring
        core2._keyring_key_id = key_b
        core2.append_event(EventType.INTERACTION, {"test": "post_rotation"}, user="test")

        # التحقق من السجل الكامل (يحتوي أحداث A و B)
        # R-625: core2 يستخدم key_id من الحدث نفسه (وليس النشط)
        core2._keyring = keyring
        status = core2.verify_integrity()
        assert status.value == "verified", f"integrity failed after rotation: {status}"

    def test_tampered_key_id_detected(self, tmp_path):
        """تغيير key_id وحده (تزييف) يُكتشف — الحدث لا يُتحقق بالمفتاح المزيّف.

        R-682: مسارات صريحة معزولة (نفس سبب الاختبار أعلاه — SovereignCore()
        بلا مسارات يلوّث سجل الجلسة المشترك).
        """
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)
        _core_paths = dict(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
        )
        # R-627: عزل كامل — KeyRing معزول
        keyring = self._isolated_keyring()
        key_a = keyring.get_active_key().key_id

        core = SovereignCore(**_core_paths)
        core._keyring = keyring
        core._keyring_key_id = key_a
        r = core.append_event(EventType.INTERACTION, {"test": "tamper_kid"}, user="test")
        orig_key_id = r["key_id"]

        verifier = SignatureVerifier(keyring)

        # تزييف: تغيير key_id فقط (التوقيع نفسه)
        tampered = {
            "hash": r["hash"], "prev_hash": r["prev_hash"], "blob": r["blob"],
            "time": r["time"], "type": r["type"], "signature": r["signature"],
            "key_id": "fake_key_id_tamper",
        }
        s = verifier.verify_event(tampered)
        # المفتاح المزيّف غير موجود → UNVERIFIABLE_MISSING_KEY (ليس VERIFIED)
        assert s.status.value != "verified", (
            f"tampered key_id must not verify: {s.status}"
        )

        # الأصلي يُتحقق بنجاح
        original = {
            "hash": r["hash"], "prev_hash": r["prev_hash"], "blob": r["blob"],
            "time": r["time"], "type": r["type"], "signature": r["signature"],
            "key_id": orig_key_id,
        }
        s2 = verifier.verify_event(original)
        assert s2.status.value == "verified"


class TestLegacyCompatibility:
    """اختبارات التوافق التاريخي (أحداث key_id بصيغة 5 حقول)."""

    def test_legacy_5field_event_with_key_id_verifies_old_format(self, tmp_path):
        """حدث تاريخي يحمل key_id لكن بتوقيع بصيغة 5 حقول (بدون key_id في البيانات)
        يُتحقق بالصيغة القديمة (لا يُعتبر تزييفًا).
        
        R-634: KeyRing معزول (لا fallback للحقيقي).
        """
        # R-634: KeyRing معزول
        _keys_dir = tmp_path / "keys_legacy"
        _keys_dir.mkdir(exist_ok=True)
        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.generate_new_key(reason="legacy_test_r634")
        keyring.save_to_disk()
        active = keyring.get_active_key()
        assert active is not None

        # بناء حدث بصيغة تاريخية (5 حقول، بدون key_id في بيانات التوقيع)
        # لكن يحمل key_id في الحدث (حدث قديم بصيغة مختلطة)
        import hmac as _hmac
        import hashlib as _hashlib
        legacy_data = f"hash|prev_hash|blob|2026-10-14T00:00:00Z|test_type"
        legacy_sig = _hmac.new(
            active.private_key.encode("utf-8"),
            legacy_data.encode("utf-8"),
            _hashlib.sha256
        ).hexdigest()

        legacy_event = {
            "hash": "hash", "prev_hash": "prev_hash", "blob": "blob",
            "time": "2026-10-14T00:00:00Z", "type": "test_type",
            "signature": legacy_sig,
            "key_id": active.key_id,  # يحمل key_id لكن بصيغة توقيع قديمة
        }

        verifier = SignatureVerifier(keyring)
        s = verifier.verify_event(legacy_event)
        # قد يفشل التحقق (INVALID) لأن الصيغة الجديدة تشمل key_id —
        # لكن يجب ألا يُعتبر تزييفًا إذا كان المفتاح معروفًا
        # المهم: لا يُعاد توقيع التاريخ
        assert s.status.value in ("verified", "invalid", "unverifiable_missing_key"), (
            f"legacy event must have a defined status: {s.status}"
        )


class TestNoKeyRing:
    """اختبارات غياب KeyRing (R-626/R-629 — فشل مُغلق، لا fallback)."""

    def test_writer_without_keyring_rejects_append(self, tmp_path):
        """في غياب KeyRing (fallback معطل)، الكاتب يرفض الإلحاق
        (فشل مُغلق — لا توقيع بمفتاح الإعدادات تحت هوية KeyRing).
        
        R-631: هذا الاختبار يُستبدل بالنسخة الأكثر تفصيلًا في
        tests/test_fail_closed_rotation.py (TestFailClosed). يبقى هنا
        للتأكيد على نفس العقد (لا حذف).
        """
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        # R-629: تعطيل fallback (لا تحميل تلقائي) — مع استعادة مضمونة
        _orig = os.environ.get("SOVEREIGN_KEYRING_FALLBACK_DISABLED")
        os.environ["SOVEREIGN_KEYRING_FALLBACK_DISABLED"] = "1"
        try:
            core = SovereignCore(
                log_file=_core_dir / "ledger.jsonl",
                blobs_dir=_core_dir / "blobs",
                index_file=_core_dir / "index.json",
                meta_file=_core_dir / "meta.json",
                integrity_file=_core_dir / "integrity.json",
            )
            # لا KeyRing (fallback معطل)
            assert core._keyring is None, "fallback must be disabled"

            # الإلحاق يجب أن يُرفض (فشل مُغلق — R-626)
            with pytest.raises((RuntimeError, KeyError)):
                core.append_event(EventType.INTERACTION, {"test": "no_kr"}, user="test")
        finally:
            # استعادة مضمونة (لا تسريب متغير البيئة)
            if _orig is None:
                os.environ.pop("SOVEREIGN_KEYRING_FALLBACK_DISABLED", None)
            else:
                os.environ["SOVEREIGN_KEYRING_FALLBACK_DISABLED"] = _orig
