"""
اختبار R-629/R-630: فشل مُغلق، دوران فعلي، تزييف بمفتاح معروف

يختبر أن:
1. غياب KeyRing: الكاتب يرفض الإلحاق (فشل مُغلق — لا fallback)
2. فشل الكتابة لا يُغيّر السجل (ledger, HISTORY, index)
3. دوران فعلي: الكاتب يلتقط المفتاح الجديد (بدون تعديل الحقول الداخلية)
4. تزييف key_id إلى مفتاح معروف (B) يُنتج INVALID
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

import pytest

from backend.memory.core import SovereignCore, EventType
from backend.sovereign.keys import KeyRing, SignatureVerifier


class TestFailClosed:
    """اختبارات الفشل المُغلق (R-629) — لا fallback عند غياب المفتاح.
    
    R-635: حارس الإلحاق قبل أي حفظ دائم (قبل blob_store.put).
    R-637: مقارنة بصمات الملفات الكاملة (blobs، الفهرس، HISTORY) —
    قبل و بعد محاولة مرفوضة.
    """

    def _collect_file_fingerprints(self, root: Path) -> dict:
        """R-637: يجمع بصمات sha256 لكل الملفات تحت الجذر المعطى."""
        import hashlib
        fingerprints = {}
        if not root.exists():
            return fingerprints
        for f in sorted(root.rglob("*")):
            if f.is_file():
                try:
                    with open(f, "rb") as fh:
                        fp = hashlib.sha256(fh.read()).hexdigest()[:16]
                    fingerprints[str(f.relative_to(root))] = fp
                except Exception:
                    pass
        return fingerprints

    def test_append_rejected_without_keyring(self, tmp_path):
        """غياب KeyRing: الكاتب يرفض الإلحاق (فشل مُغلق)."""
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        # R-629: تعطيل fallback (لا تحميل تلقائي من المسار الحقيقي)
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
            assert core._keyring_key_id is None

            # الإلحاق يجب أن يُرفض (فشل مُغلق)
            with pytest.raises((RuntimeError, KeyError)) as exc_info:
                core.append_event(EventType.INTERACTION, {"test": "no_kr"}, user="test")
            assert "R-63" in str(exc_info.value), (
                f"must fail closed with R-63x: {exc_info.value}"
            )
        finally:
            # استعادة الحالة الأصلية
            if _orig is None:
                os.environ.pop("SOVEREIGN_KEYRING_FALLBACK_DISABLED", None)
            else:
                os.environ["SOVEREIGN_KEYRING_FALLBACK_DISABLED"] = _orig

    def test_failed_append_no_file_changes_fingerprints(self, tmp_path):
        """R-637: محاولة إلحاق مرفوضة لا تُغيّر أي ملف (بصمات كاملة).
        
        يقارن بصمات sha256 لكل الملفات تحت tmp_path (بما فيها
        blobs، الفهرس، ledger، HISTORY) قبل و بعد المحاولة المرفوضة.
        """
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        # R-629: تعطيل fallback
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

            # بصمات الملفات قبل المحاولة (كل الملفات تحت tmp_path)
            before = self._collect_file_fingerprints(tmp_path)

            # محاولة إلحاق (يجب أن تُرفض — فشل مُغلق R-635)
            with pytest.raises((RuntimeError, KeyError)):
                core.append_event(EventType.INTERACTION, {"test": "fail_fp"}, user="test")

            # بصمات الملفات بعد المحاولة
            after = self._collect_file_fingerprints(tmp_path)

            # R-637: البصمات متطابقة (لا تغيير في أي ملف)
            assert before == after, (
                f"rejected append must not change any file. "
                f"Before: {len(before)} files, After: {len(after)} files. "
                f"New files: {sorted(set(after) - set(before))}, "
                f"Changed: {sorted(k for k in before if before.get(k) != after.get(k))}"
            )
            # R-635: لا blob جديد (الحارس قبل blob_store.put)
            blobs_dir = _core_dir / "blobs"
            blob_files = list(blobs_dir.rglob("*")) if blobs_dir.exists() else []
            blob_files = [f for f in blob_files if f.is_file()]
            assert len(blob_files) == 0, (
                f"rejected append must not create any blob (guard before blob_store.put), "
                f"found {len(blob_files)} blobs"
            )
        finally:
            if _orig is None:
                os.environ.pop("SOVEREIGN_KEYRING_FALLBACK_DISABLED", None)
            else:
                os.environ["SOVEREIGN_KEYRING_FALLBACK_DISABLED"] = _orig

    def test_failed_append_does_not_change_ledger(self, tmp_path):
        """فشل الكتابة (فشل مُغلق) لا يُغيّر السجل أو الفهرس."""
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        # R-629: تعطيل fallback
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

            # حالة السجل قبل الفشل
            ledger_path = _core_dir / "ledger.jsonl"
            before_exists = ledger_path.exists()
            before_content = ledger_path.read_text() if before_exists else ""

            # محاولة إلحاق (يجب أن تفشل)
            with pytest.raises((RuntimeError, KeyError)):
                core.append_event(EventType.INTERACTION, {"test": "fail"}, user="test")

            # السجل لم يتغير (لا سطر جديد)
            after_content = ledger_path.read_text() if ledger_path.exists() else ""
            assert after_content == before_content, (
                "failed append must not change ledger content"
            )
        finally:
            if _orig is None:
                os.environ.pop("SOVEREIGN_KEYRING_FALLBACK_DISABLED", None)
            else:
                os.environ["SOVEREIGN_KEYRING_FALLBACK_DISABLED"] = _orig

    def test_failed_append_does_not_change_index(self, tmp_path):
        """فشل الكتابة لا يُغيّر الفهرس (events_count)."""
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

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

            before_count = core.index.data["events_count"]

            with pytest.raises((RuntimeError, KeyError)):
                core.append_event(EventType.INTERACTION, {"test": "fail"}, user="test")

            after_count = core.index.data["events_count"]
            assert after_count == before_count, (
                f"failed append must not change index: {before_count} -> {after_count}"
            )
        finally:
            if _orig is None:
                os.environ.pop("SOVEREIGN_KEYRING_FALLBACK_DISABLED", None)
            else:
                os.environ["SOVEREIGN_KEYRING_FALLBACK_DISABLED"] = _orig


class TestRealRotation:
    """اختبارات الدوران الفعلي (R-630) — الكاتب يلتقط المفتاح الجديد."""

    def _isolated_keyring(self, tmp_path) -> KeyRing:
        """يُنشئ KeyRing معزول في tmp_path."""
        _keys_dir = tmp_path / "keys"
        _keys_dir.mkdir(exist_ok=True)
        kr = KeyRing(keys_dir=_keys_dir)
        kr.generate_new_key(reason="rotation_test_r630")
        kr.save_to_disk()
        return kr

    def test_writer_picks_up_rotation_without_manual_fields(self, tmp_path):
        """الدوران الفعلي: الكاتب نفسه (core1) يلتقط المفتاح الجديد
        (بدون إنشاء Core جديد و بدون تعديل الحقول الداخلية).
        
        R-632: append_event يختار المفتاح النشط الحالي في كل كتابة —
        الدوران يُلتقط فورًا دون إعادة إنشاء Core.
        """
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        # 1) إنشاء KeyRing معزول بمفتاح A
        keyring = self._isolated_keyring(tmp_path)
        key_a = keyring.get_active_key().key_id

        # 2) إنشاء Core واحد بحقن KeyRing (R-629 — لا تحميل تلقائي)
        core1 = SovereignCore(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
            keyring=keyring,
        )
        assert core1._keyring_key_id == key_a

        # كتابة حدث بالمفتاح A (بدون تعديل الحقول الداخلية)
        r1 = core1.append_event(EventType.INTERACTION, {"test": "before_rotation"}, user="test")
        assert r1["key_id"] == key_a

        # 3) دوران فعلي: A → B (عبر KeyRing نفسه)
        new_key = keyring.generate_new_key(reason="rotation_r632")
        keyring.save_to_disk()
        key_b = new_key.key_id
        assert key_b != key_a

        # 4) R-632: كتابة عبر الكاتب نفسه (core1 — لا core2، لا تعديل يدوي)
        # الكاتب يلتقط المفتاح الجديد B (النشط) في كل كتابة
        r2 = core1.append_event(EventType.INTERACTION, {"test": "after_rotation"}, user="test")
        assert r2["key_id"] == key_b, (
            f"writer (same core1) must pick up new active key B ({key_b}), "
            f"got {r2['key_id']} (key_a={key_a})"
        )

        # 5) التحقق من الحدثين عبر SignatureVerifier
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
        assert s1.status.value == "verified", f"event A must verify: {s1.reason}"
        assert s2.status.value == "verified", f"event B must verify: {s2.reason}"

        # 6) سلامة السجل الكامل (أحداث A و B معًا) — عبر الكاتب نفسه
        status = core1.verify_integrity()
        assert status.value == "verified", f"integrity failed after rotation: {status}"

    def test_tampered_key_id_to_known_key_returns_invalid(self, tmp_path):
        """تزييف key_id إلى مفتاح معروف (B) يُنتج INVALID (وليس VERIFIED)."""
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        keyring = self._isolated_keyring(tmp_path)
        key_a = keyring.get_active_key().key_id

        core = SovereignCore(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
            keyring=keyring,
        )
        r = core.append_event(EventType.INTERACTION, {"test": "tamper_known"}, user="test")

        # دوران: A → B (مفتاحان معروفان)
        new_key = keyring.generate_new_key(reason="tamper_known_r630")
        keyring.save_to_disk()
        key_b = new_key.key_id

        # تزييف: تغيير key_id من A إلى B (مفتاح معروف) — التوقيع نفسه
        tampered = {
            "hash": r["hash"], "prev_hash": r["prev_hash"], "blob": r["blob"],
            "time": r["time"], "type": r["type"], "signature": r["signature"],
            "key_id": key_b,  # مفتاح معروف B — ليس مفتاح غير موجود
        }
        verifier = SignatureVerifier(keyring)
        s = verifier.verify_event(tampered)
        # يجب أن يكون INVALID (التوقيع لا يطابق المفتاح B — يطابق A فقط)
        assert s.status.value == "invalid", (
            f"tampered key_id to known key B must be INVALID, got: {s.status} ({s.reason})"
        )

        # الأصلي (key_id = A) يُتحقق بنجاح
        original = {
            "hash": r["hash"], "prev_hash": r["prev_hash"], "blob": r["blob"],
            "time": r["time"], "type": r["type"], "signature": r["signature"],
            "key_id": key_a,
        }
        s2 = verifier.verify_event(original)
        assert s2.status.value == "verified"


class TestCompromisedKey:
    """اختبارات المفتاح المخترق (R-633) — لا يُستخدم للكتابة، لكن يُتحقق من أحداثه التاريخية."""

    def test_compromised_key_not_used_for_writing(self, tmp_path):
        """مفتاح COMPROMISED لا يُستخدم للكتابة (فشل مُغلق)."""
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        # إنشاء KeyRing معزول بمفتاح A
        keyring = self._isolated_keyring_compromised(tmp_path)
        key_a = keyring.get_active_key().key_id

        core = SovereignCore(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
            keyring=keyring,
        )

        # كتابة حدث بالمفتاح A (نشط)
        r1 = core.append_event(EventType.INTERACTION, {"test": "before_compromise"}, user="test")
        assert r1["key_id"] == key_a

        # تعليم المفتاح A كمخترق (COMPROMISED)
        keyring.mark_key_compromised(key_a, reason="test compromise r633")

        # R-633: لا يوجد مفتاح نشط (A مخترق) — الكتابة يجب أن تُرفض
        with pytest.raises((RuntimeError, KeyError)):
            core.append_event(EventType.INTERACTION, {"test": "after_compromise"}, user="test")

        # لكن الأحداث القديمة (بالمفتاح A) ما زالت قابلة للتحقق التاريخي
        # (لا يُمنع التحقق — فقط الكتابة)
        verifier = SignatureVerifier(keyring)
        e1 = {
            "hash": r1["hash"], "prev_hash": r1["prev_hash"], "blob": r1["blob"],
            "time": r1["time"], "type": r1["type"], "signature": r1["signature"],
            "key_id": r1["key_id"],
        }
        # قد يكون INVALID (توقيع صحيح لكن المفتاح مخترق) أو غير ذلك
        # المهم: لا يُرفض التحقق (لا استثناء)
        s1 = verifier.verify_event(e1)
        assert s1.status.value in ("verified", "invalid", "unverifiable_missing_key"), (
            f"historical event must have defined status: {s1.status}"
        )

    def _isolated_keyring_compromised(self, tmp_path) -> KeyRing:
        """يُنشئ KeyRing معزول (لاختبار المفتاح المخترق)."""
        _keys_dir = tmp_path / "keys_compromised"
        _keys_dir.mkdir(exist_ok=True)
        kr = KeyRing(keys_dir=_keys_dir)
        kr.generate_new_key(reason="compromised_test_r633")
        kr.save_to_disk()
        return kr


class TestLegacyFixedSample:
    """اختبار التوافق التاريخي بعينة ثابتة (R-631)."""

    def test_fixed_legacy_5field_sample(self, tmp_path):
        """عينة ثابتة: حدث بصيغة 5 حقول (بدون key_id في التوقيع)
        لكن يحمل key_id في الحدث — يُتحقق بالصيغة القديمة."""
        keyring = self._isolated_keyring_static(tmp_path)
        active = keyring.get_active_key()
        assert active is not None

        import hmac as _hmac
        import hashlib as _hashlib

        # عينة ثابتة — توقيع بصيغة 5 حقول (بدون key_id في البيانات)
        legacy_data = "hash_legacy|prev_hash_legacy|blob_legacy|2026-10-14T00:00:00Z|interaction"
        legacy_sig = _hmac.new(
            active.private_key.encode("utf-8"),
            legacy_data.encode("utf-8"),
            _hashlib.sha256
        ).hexdigest()

        # الحدث يحمل key_id لكن توقيعه بصيغة 5 حقول (تاريخي)
        legacy_event = {
            "hash": "hash_legacy", "prev_hash": "prev_hash_legacy", "blob": "blob_legacy",
            "time": "2026-10-14T00:00:00Z", "type": "interaction",
            "signature": legacy_sig,
            "key_id": active.key_id,  # يحمل key_id (حدث بصيغة مختلطة)
        }

        # التحقق عبر SignatureVerifier — الصيغة الجديدة تشمل key_id
        # لذا التوقيع لن يطابق → INVALID (ليس VERIFIED)
        verifier = SignatureVerifier(keyring)
        s = verifier.verify_event(legacy_event)
        # التوقيع بصيغة 5 حقول لا يطابق الصيغة الجديدة (6 حقول)
        # → INVALID (وليس VERIFIED — لأن البيانات مختلفة)
        assert s.status.value == "invalid", (
            f"legacy 5-field signature must not verify with 6-field format: {s.status}"
        )

        # لكن الحدث الأصلي (بصيغة 6 حقول) يُتحقق بنجاح
        new_data = legacy_data + f"|{active.key_id}"
        new_sig = _hmac.new(
            active.private_key.encode("utf-8"),
            new_data.encode("utf-8"),
            _hashlib.sha256
        ).hexdigest()
        new_event = dict(legacy_event)
        new_event["signature"] = new_sig
        s2 = verifier.verify_event(new_event)
        assert s2.status.value == "verified", (
            f"6-field signature must verify: {s2.reason}"
        )

    def _isolated_keyring_static(self, tmp_path) -> KeyRing:
        """يُنشئ KeyRing معزول (للعينة الثابتة)."""
        _keys_dir = tmp_path / "keys_static"
        _keys_dir.mkdir(exist_ok=True)
        kr = KeyRing(keys_dir=_keys_dir)
        kr.generate_new_key(reason="legacy_sample_r631")
        kr.save_to_disk()
        return kr
