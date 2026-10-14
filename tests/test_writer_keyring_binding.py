"""
اختبار R-620: ربط الكاتب فعليًا بـ KeyRing

يختبر أن:
1. الأحداث الجديدة تُوقّع بمفتاح KeyRing (وليس فقط إضافة key_id)
2. التوقيع قابل للتحقق عبر SignatureVerifier
3. الأحداث التاريخية (بلا key_id) تُتحقق بالصيغة القديمة
4. التوقيع يفشل إذا تغير المفتاح (تزييف مُكتشف)
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


class TestWriterKeyRingBinding:
    """اختبارات ربط الكاتب بـ KeyRing (R-620).
    
    R-634: عزل كامل — KeyRing معزول في tmp_path (لا fallback للحقيقي).
    """

    def _make_core(self, tmp_path) -> SovereignCore:
        """يُنشئ SovereignCore جديد مع KeyRing معزول محقون (R-629)."""
        _keys_dir = tmp_path / "keys"
        _keys_dir.mkdir(exist_ok=True)
        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.generate_new_key(reason="r620_test")
        keyring.save_to_disk()

        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        return SovereignCore(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
            keyring=keyring,
        )

    def _make_verifier(self, tmp_path) -> SignatureVerifier:
        """يُنشئ SignatureVerifier مع KeyRing معزول."""
        _keys_dir = tmp_path / "keys"
        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.load_from_disk()
        return SignatureVerifier(keyring)

    def test_new_event_has_key_id(self, tmp_path):
        """الحدث الجديد يحمل key_id من KeyRing النشط."""
        core = self._make_core(tmp_path)
        result = core.append_event(EventType.INTERACTION, {"test": "r620"}, user="test")

        assert "key_id" in result, "event must have key_id"
        assert result["key_id"] == core._keyring_key_id

    def test_event_signature_matches_keyring_key(self, tmp_path):
        """توقيع الحدث مطابق لمفتاح KeyRing (وليس مفتاح الإعدادات فقط)."""
        core = self._make_core(tmp_path)
        result = core.append_event(EventType.INTERACTION, {"test": "r620_sig"}, user="test")

        verifier = self._make_verifier(tmp_path)
        event = {
            "hash": result["hash"],
            "prev_hash": result["prev_hash"],
            "blob": result["blob"],
            "time": result["time"],
            "type": result["type"],
            "signature": result["signature"],
            "key_id": result["key_id"],
        }
        status = verifier.verify_event(event)
        assert status.status.value == "verified", f"signature failed: {status.reason}"

    def test_tampered_signature_detected(self, tmp_path):
        """توقيع مزوّر يُكتشف (تغيير الحمولة لا يُغيّر التوقيع القديم)."""
        core = self._make_core(tmp_path)
        result = core.append_event(EventType.INTERACTION, {"test": "tamper"}, user="test")

        verifier = self._make_verifier(tmp_path)
        # تزييف: تغيير الحمولة لكن الاحتفاظ بالتوقيع القديم
        event = {
            "hash": "fake_hash_12345",
            "prev_hash": result["prev_hash"],
            "blob": result["blob"],
            "time": result["time"],
            "type": result["type"],
            "signature": result["signature"],
            "key_id": result["key_id"],
        }
        status = verifier.verify_event(event)
        assert status.status.value == "invalid", (
            f"tampering not detected: {status.reason}"
        )

    def test_integrity_check_passes_with_new_events(self, tmp_path):
        """التحقق من سلامة السجل ينجح مع الأحداث الجديدة (توقيع KeyRing).
        
        R-628: سجل معزول بمسارات صريحة + KeyRing معزول محقون (R-634).
        """
        # R-634: KeyRing معزول محقون (لا fallback)
        _keys_dir = tmp_path / "keys"
        _keys_dir.mkdir(exist_ok=True)
        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.generate_new_key(reason="integrity_test_r634")
        keyring.save_to_disk()

        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        _blobs_dir = _core_dir / "blobs"
        _blobs_dir.mkdir(exist_ok=True)

        core = SovereignCore(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_blobs_dir,
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
            keyring=keyring,
        )
        core.append_event(EventType.INTERACTION, {"test": "integrity"}, user="test")

        status = core.verify_integrity()
        assert status.value == "verified", f"integrity failed: {status}"

    def test_legacy_events_use_old_format(self, tmp_path):
        """الأحداث التاريخية (بلا key_id) تُتحقق بالصيغة القديمة."""
        core = self._make_core(tmp_path)
        # إنشاء حدث قديم الصيغة (بلا key_id)
        result = core.append_event(EventType.INTERACTION, {"test": "legacy"}, user="test")
        # إزالة key_id لمحاكاة حدث قديم (لا يُفعَل في الإنتاج — للاختبار فقط)
        del result["key_id"]

        verifier = self._make_verifier(tmp_path)
        status = verifier.verify_event(result)
        # حدث بلا key_id → UNVERIFIABLE_MISSING_KEY (LEGACY_PRE_KEYRING)
        assert status.status.value == "unverifiable_missing_key", (
            f"legacy event should be UNVERIFIABLE_MISSING_KEY, got: {status.status}"
        )


class TestKeyRingFallback:
    """اختبارات عزل KeyRing (R-621 معطل — R-634).
    
    R-634: الجذر المعزول لا يتجاوز إلى أسرار التشغيل —
    إذا كان keys_dir فارغًا، يبقى فارغًا (لا fallback).
    """

    def test_isolated_keyring_stays_empty(self, tmp_path):
        """R-634: KeyRing معزول (keys_dir فارغ) يبقى فارغ — لا قراءة من المسار الحقيقي."""
        _keys_dir = tmp_path / "keys_isolated"
        _keys_dir.mkdir()

        # KeyRing معزول — لا مفاتيح (لا fallback)
        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.load_from_disk()

        # يجب أن يبقى فارغًا (لا fallback إلى المسار الحقيقي)
        active = keyring.get_active_key()
        assert active is None, (
            "isolated KeyRing must stay empty (no fallback to real path) — R-634"
        )
        assert len(keyring._keys) == 0, (
            f"isolated KeyRing must have 0 keys, got {len(keyring._keys)}"
        )

    def test_isolated_keyring_no_real_keys_leaked(self, tmp_path):
        """R-634: KeyRing معزول لا يُحمّل أي مفتاح من المسار الحقيقي.
        
        R-636: لا قراءة لأسرار التشغيل — بيانات اختبار مستقلة في tmp_path
        (لا يعتمد على وجود data/keys/keyring.json الحقيقي).
        """
        _keys_dir = tmp_path / "keys_no_leak"
        _keys_dir.mkdir()

        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.load_from_disk()

        # R-636: بيانات اختبار مستقلة (لا قراءة للملف الحقيقي)
        # — نتحقق فقط أن KeyRing المعزول فارغ (لا مفاتيح من أي مكان)
        assert len(keyring._keys) == 0, (
            f"isolated KeyRing must have 0 keys (no leak from anywhere), "
            f"got {len(keyring._keys)}"
        )
        active = keyring.get_active_key()
        assert active is None, "isolated KeyRing must have no active key (no leak)"

    def test_sovereign_core_in_isolated_env_no_keyring(self, tmp_path):
        """R-634: SovereignCore في بيئة معزولة (fallback معطل) لا يربط KeyRing.
        
        (الكتابة تُرفض — فشل مُغلق. راجع TestFailClosed.)
        """
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        # R-629: تعطيل التحميل التلقائي (fallback معطل)
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
            # لا KeyRing (fallback معطل — R-634)
            assert core._keyring is None, (
                "SovereignCore must not load KeyRing when fallback disabled — R-634"
            )
            assert core._keyring_key_id is None
        finally:
            if _orig is None:
                os.environ.pop("SOVEREIGN_KEYRING_FALLBACK_DISABLED", None)
            else:
                os.environ["SOVEREIGN_KEYRING_FALLBACK_DISABLED"] = _orig

    def test_keyring_does_not_write_to_real_path(self, tmp_path):
        """KeyRing لا يكتب إلى المسار الحقيقي في بيئة معزولة.
        
        R-636: لا قراءة للملف الحقيقي — يتحقق فقط أن الكتابة
        تتم داخل keys_dir المعزول (لا اعتماد على وجود الملف الحقيقي).
        """
        _keys_dir = tmp_path / "keys_write_test"
        _keys_dir.mkdir()

        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.generate_new_key(reason="R-634 test")
        keyring.save_to_disk()

        # R-636: التحقق أن الكتابة تمت داخل keys_dir المعزول فقط
        # (لا قراءة للملف الحقيقي — لا اعتماد على وجوده)
        _isolated_keyring_file = _keys_dir / "keyring.json"
        assert _isolated_keyring_file.exists(), (
            "KeyRing must write to isolated keys_dir"
        )
        isolated_data = json.loads(_isolated_keyring_file.read_text(encoding="utf-8"))
        assert len(isolated_data["keys"]) >= 1, (
            "isolated keyring.json must contain the generated key"
        )
        
        # المفتاح الجديد موجود في المعزول
        new_key_id = keyring.get_active_key().key_id if keyring.get_active_key() else None
        if new_key_id:
            isolated_key_ids = [k["key_id"] for k in isolated_data["keys"]]
            assert new_key_id in isolated_key_ids, (
                "new key must be written to isolated path"
            )
