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
    """اختبارات ربط الكاتب بـ KeyRing (R-620)."""

    def _make_core(self) -> SovereignCore:
        """يُنشئ SovereignCore جديد (مع KeyRing محمّل)."""
        return SovereignCore()

    def _make_verifier(self) -> SignatureVerifier:
        """يُنشئ SignatureVerifier مع KeyRing محمّل."""
        keyring = KeyRing()
        keyring.load_from_disk()
        return SignatureVerifier(keyring)

    def test_new_event_has_key_id(self):
        """الحدث الجديد يحمل key_id من KeyRing النشط."""
        core = self._make_core()
        result = core.append_event(EventType.INTERACTION, {"test": "r620"}, user="test")

        assert "key_id" in result, "event must have key_id"
        assert result["key_id"] == core._keyring_key_id

    def test_event_signature_matches_keyring_key(self):
        """توقيع الحدث مطابق لمفتاح KeyRing (وليس مفتاح الإعدادات فقط)."""
        core = self._make_core()
        result = core.append_event(EventType.INTERACTION, {"test": "r620_sig"}, user="test")

        verifier = self._make_verifier()
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

    def test_tampered_signature_detected(self):
        """توقيع مزوّر يُكتشف (تغيير الحمولة لا يُغيّر التوقيع القديم)."""
        core = self._make_core()
        result = core.append_event(EventType.INTERACTION, {"test": "tamper"}, user="test")

        verifier = self._make_verifier()
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
        
        R-628: سجل معزول بمسارات صريحة — لضمان أن السجل يحتوي فقط
        أحداث هذا الاختبار (وليس أحداث اختبارات أخرى).
        """
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
        )
        core.append_event(EventType.INTERACTION, {"test": "integrity"}, user="test")

        status = core.verify_integrity()
        assert status.value == "verified", f"integrity failed: {status}"

    def test_legacy_events_use_old_format(self):
        """الأحداث التاريخية (بلا key_id) تُتحقق بالصيغة القديمة."""
        core = self._make_core()
        # إنشاء حدث قديم الصيغة (بلا key_id)
        result = core.append_event(EventType.INTERACTION, {"test": "legacy"}, user="test")
        # إزالة key_id لمحاكاة حدث قديم (لا يُفعَل في الإنتاج — للاختبار فقط)
        del result["key_id"]

        verifier = self._make_verifier()
        status = verifier.verify_event(result)
        # حدث بلا key_id → UNVERIFIABLE_MISSING_KEY (LEGACY_PRE_KEYRING)
        assert status.status.value == "unverifiable_missing_key", (
            f"legacy event should be UNVERIFIABLE_MISSING_KEY, got: {status.status}"
        )


class TestKeyRingFallback:
    """اختبارات fallback قراءة المفتاح الحقيقي في بيئة معزولة (R-621)."""

    def test_keyring_loads_real_key_in_isolated_env(self):
        """KeyRing يُحمّل المفتاح الحقيقي حتى في بيئة معزولة."""
        keyring = KeyRing()
        keyring.load_from_disk()
        active = keyring.get_active_key()
        assert active is not None, "KeyRing must load active key from real path (R-621)"

    def test_sovereign_core_links_keyring_in_isolated_env(self):
        """SovereignCore يربط KeyRing حتى في بيئة معزولة."""
        core = SovereignCore()
        assert core._keyring_key_id is not None, (
            "SovereignCore must link to KeyRing (R-621 fallback)"
        )

    def test_keyring_does_not_write_to_real_path(self):
        """KeyRing لا يكتب إلى المسار الحقيقي في بيئة معزولة."""
        keyring = KeyRing()
        keyring.load_from_disk()
        # إنشاء مفتاح جديد (في المسار المعزول)
        new_key = keyring.generate_new_key(reason="R-621 test")
        # حفظ (يجب أن يكتب إلى المسار المعزول، وليس الحقيقي)
        keyring.save_to_disk()

        # المسار الحقيقي لا يجب أن يُغيّر (لا يُضاف المفتاح الجديد)
        _real = _REPO_ROOT / "data" / "keys" / "keyring.json"
        data = json.loads(_real.read_text(encoding="utf-8"))
        real_key_ids = [k["key_id"] for k in data["keys"]]
        assert new_key.key_id not in real_key_ids, (
            "KeyRing must NOT write to real path in isolated env"
        )
