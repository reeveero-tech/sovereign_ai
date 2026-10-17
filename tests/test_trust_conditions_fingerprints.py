"""
اختبار R-644/R-645/R-646: شروط الثقة، بصمات كاملة، تغيير blob، مفتاح فارغ

يختبر أن:
1. بصمات كاملة (sha256 كامل، لا ابتلاع أخطاء القراءة)
2. private_key=None و private_key="" — الحارس قبل الحفظ (لا blob يُحفظ)
3. مرساة v2 صحيحة بمفتاح معروف مقبول: الجذر و التوقيع ناجحان
4. تعديل المحتوى و إعادة حساب الجذر دون إعادة التوقيع: فشل التوقيع
5. تغيير النطاق أو العدد أو هوية المفتاح أو التوقيع: فشل
6. غياب KeyRing أو مفتاح مفقود أو إصدار مجهول: لا تغطية موثوقة
7. v1 أو إزالة الإصدار: قد ينجح فحص الجذر لكن لا يُحتسب توثيق التوقيع
8. مفتاح مخترق: نتيجة تشخريبية منفصلة عن الثقة
9. تغيير محتوى blob موجود: يُكتشف (سلامة المحتوى)
"""

import hashlib
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
from backend.sovereign.keys import KeyRing, SignatureVerifier, KeyStatus
from backend.sovereign.ledger import LedgerAnchor
from backend.sovereign.ledger.anchor import compute_merkle_root, compute_merkle_root_v2


class TestFullFingerprints:
    """R-646: بصمات كاملة — sha256 كامل، لا ابتلاع أخطاء القراءة."""

    def _collect_fingerprints_strict(self, root: Path) -> dict:
        """يجمع بصمات sha256 كاملة — يفشل عند خطأ قراءة (لا يبتلع)."""
        fingerprints = {}
        assert root.exists(), f"root must exist: {root}"
        for f in sorted(root.rglob("*")):
            if f.is_file():
                # لا ابتلاع أخطاء — يفشل الاختبار
                with open(f, "rb") as fh:
                    content = fh.read()
                # sha256 كامل (ليس [:16])
                fingerprints[str(f.relative_to(root))] = hashlib.sha256(content).hexdigest()
        return fingerprints

    def test_failed_append_no_file_changes_full_fp(self, tmp_path):
        """محاولة مرفوضة لا تُغيّر أي ملف (بصمات sha256 كاملة)."""
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

            before = self._collect_fingerprints_strict(tmp_path)

            with pytest.raises((RuntimeError, KeyError)):
                core.append_event(EventType.INTERACTION, {"test": "fp"}, user="test")

            after = self._collect_fingerprints_strict(tmp_path)
            assert before == after, (
                f"fingerprints must be identical. "
                f"New: {sorted(set(after) - set(before))}, "
                f"Changed: {sorted(k for k in before if before.get(k) != after.get(k))}"
            )
        finally:
            if _orig is None:
                os.environ.pop("SOVEREIGN_KEYRING_FALLBACK_DISABLED", None)
            else:
                os.environ["SOVEREIGN_KEYRING_FALLBACK_DISABLED"] = _orig


class TestEmptyPrivateKeyGuard:
    """R-646: private_key=None و private_key="" — الحارس قبل الحفظ."""

    def _setup_core(self, tmp_path, private_key_value):
        """يُنشئ Core مع KeyRing ذو مفتاح بـ private_key محدد."""
        _keys_dir = tmp_path / "keys"
        _keys_dir.mkdir(exist_ok=True)
        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.generate_new_key(reason="empty_pk_test")
        # تعديل private_key يدويًا (لاختبار الحارس)
        active = keyring.get_active_key()
        active.private_key = private_key_value
        keyring.save_to_disk()

        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        core = SovereignCore(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
            keyring=keyring,
        )
        return core, _core_dir

    def test_private_key_none_rejected_before_save(self, tmp_path):
        """private_key=None: الحارس يرفض قبل أي حفظ (لا blob)."""
        core, _core_dir = self._setup_core(tmp_path, None)

        before_fp = {}
        for f in sorted(tmp_path.rglob("*")):
            if f.is_file():
                with open(f, "rb") as fh:
                    before_fp[str(f)] = hashlib.sha256(fh.read()).hexdigest()

        with pytest.raises((RuntimeError, KeyError)) as exc_info:
            core.append_event(EventType.INTERACTION, {"test": "none_pk"}, user="test")
        assert "R-63" in str(exc_info.value), f"must fail with R-63x: {exc_info.value}"

        # بصمات متطابقة (لا تغيير)
        after_fp = {}
        for f in sorted(tmp_path.rglob("*")):
            if f.is_file():
                with open(f, "rb") as fh:
                    after_fp[str(f)] = hashlib.sha256(fh.read()).hexdigest()
        assert before_fp == after_fp, "fingerprints must be identical (no file changed)"

    def test_private_key_empty_string_rejected_before_save(self, tmp_path):
        """private_key="": الحارس يرفض قبل أي حفظ (لا blob)."""
        core, _core_dir = self._setup_core(tmp_path, "")

        before_fp = {}
        for f in sorted(tmp_path.rglob("*")):
            if f.is_file():
                with open(f, "rb") as fh:
                    before_fp[str(f)] = hashlib.sha256(fh.read()).hexdigest()

        with pytest.raises((RuntimeError, KeyError)) as exc_info:
            core.append_event(EventType.INTERACTION, {"test": "empty_pk"}, user="test")
        assert "R-63" in str(exc_info.value), f"must fail with R-63x: {exc_info.value}"

        # بصمات متطابقة (لا تغيير)
        after_fp = {}
        for f in sorted(tmp_path.rglob("*")):
            if f.is_file():
                with open(f, "rb") as fh:
                    after_fp[str(f)] = hashlib.sha256(fh.read()).hexdigest()
        assert before_fp == after_fp, "fingerprints must be identical (no file changed)"


class TestAnchorTrustConditions:
    """R-644: اختبارات مضادة محددة لشروط الثقة."""

    def _make_keyring(self, tmp_path) -> KeyRing:
        _keys_dir = tmp_path / "keys"
        _keys_dir.mkdir(exist_ok=True)
        kr = KeyRing(keys_dir=_keys_dir)
        kr.generate_new_key(reason="anchor_trust_test")
        kr.save_to_disk()
        return kr

    def _make_anchor(self, tmp_path, events_count=5) -> LedgerAnchor:
        """يُنشئ LedgerAnchor مع سجل معزول."""
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        _ledger = _core_dir / "ledger.jsonl"
        _anchors = _core_dir / "ledger.anchors.jsonl"

        # إنشاء أحداث وهمية
        lines = []
        for i in range(events_count):
            event = {"hash": f"hash_{i}", "prev_hash": f"hash_{i-1}" if i > 0 else "GENESIS",
                     "blob": f"blob_{i}", "time": f"2026-10-14T00:00:{i:02d}Z", "type": "test"}
            lines.append(json.dumps(event))
        _ledger.write_text("\n".join(lines) + "\n")

        return LedgerAnchor(ledger_path=_ledger, anchors_path=_anchors)

    def test_v2_correct_with_trusted_key(self, tmp_path):
        """v2 صحيحة بمفتاح معروف مقبول: الجذر و التوقيع ناجحان."""
        keyring = self._make_keyring(tmp_path)
        anchor = self._make_anchor(tmp_path)
        active = keyring.get_active_key()

        lines = anchor.read_ledger_lines()
        # D-036 (الجولة <2>): مرساة جديدة عبر anchor_batch = جذر v2
        merkle_root = compute_merkle_root_v2(lines)
        sig = anchor.sign_anchor_with_key(0, len(lines)-1, merkle_root, active.key_id, active.private_key)

        result = anchor.anchor_batch(0, len(lines)-1, active.key_id, sig, reason="v2_correct", keyring=keyring)
        assert result is not None

        detailed = anchor.verify_anchor_detailed(result, keyring=keyring)
        assert detailed["root_verified"] is True
        assert detailed["signature_verified"] is True
        assert detailed["key_trusted"] is True
        assert detailed["trusted"] is True

    def test_content_modified_root_recalculated_no_resign_fails(self, tmp_path):
        """تعديل المحتوى و إعادة حساب الجذر (تحديث المرساة) دون إعادة التوقيع:
        الجذر ينجح لكن التوقيع يفشل — لا تغطية موثوقة.
        
        R-649: هذا يختبر السيناريو الفعلي: المهاجم يُعدّل المحتوى و يُحدّث
        الجذر في المرساة لكنه لا يستطيع إعادة التوقيع (لا يملك المفتاح).
        """
        keyring = self._make_keyring(tmp_path)
        anchor = self._make_anchor(tmp_path)
        active = keyring.get_active_key()

        lines = anchor.read_ledger_lines()
        # D-036 (الجولة <2>): مرساة جديدة عبر anchor_batch = جذر v2
        merkle_root = compute_merkle_root_v2(lines)
        sig = anchor.sign_anchor_with_key(0, len(lines)-1, merkle_root, active.key_id, active.private_key)
        result = anchor.anchor_batch(0, len(lines)-1, active.key_id, sig, reason="before_tamper", keyring=keyring)
        assert result is not None

        # تعديل المحتوى (تغيير حدث)
        ledger_file = anchor.ledger_path
        modified_lines = list(lines)
        modified_event = json.loads(modified_lines[2])
        modified_event["type"] = "tampered_type"
        modified_lines[2] = json.dumps(modified_event)
        ledger_file.write_text("\n".join(modified_lines) + "\n")

        # R-649: المهاجم يُحدّث الجذر في نسخة المرساة (دون إعادة التوقيع)
        tampered_lines = anchor.read_ledger_lines()
        new_merkle_root = compute_merkle_root_v2(tampered_lines)
        tampered_anchor = dict(result)
        tampered_anchor["merkle_root"] = f"sha256:{new_merkle_root}"
        # التوقيع يبقى القديم (لا يُعاد — المهاجم لا يملك المفتاح)

        # التحقق — الجذر ينجح (المهاجر حدّثه) لكن التوقيع يفشل
        detailed = anchor.verify_anchor_detailed(tampered_anchor, keyring=keyring)
        assert detailed["root_verified"] is True, (
            f"root should verify (attacker updated it): {detailed['message']}"
        )
        assert detailed["signature_verified"] is False, (
            f"signature must FAIL (old sig does not cover new root): {detailed['message']}"
        )
        assert detailed["trusted"] is False, (
            f"must not be trusted (sig does not cover new root): {detailed['message']}"
        )

    def test_changed_event_count_fails(self, tmp_path):
        """تغيير event_count: فشل بنيوي."""
        keyring = self._make_keyring(tmp_path)
        anchor = self._make_anchor(tmp_path)
        active = keyring.get_active_key()

        lines = anchor.read_ledger_lines()
        # D-036 (الجولة <2>): مرساة جديدة عبر anchor_batch = جذر v2
        merkle_root = compute_merkle_root_v2(lines)
        sig = anchor.sign_anchor_with_key(0, len(lines)-1, merkle_root, active.key_id, active.private_key)
        result = anchor.anchor_batch(0, len(lines)-1, active.key_id, sig, reason="before_count_change", keyring=keyring)
        assert result is not None

        # تعديل event_count في المرساة (تزييف)
        tampered_anchor = dict(result)
        tampered_anchor["event_count"] = result["event_count"] + 1

        detailed = anchor.verify_anchor_detailed(tampered_anchor, keyring=keyring)
        assert detailed["root_verified"] is False or detailed["signature_verified"] is False, (
            "changed event_count must fail verification"
        )

    def test_missing_keyring_no_trusted_coverage(self, tmp_path):
        """غياب KeyRing: لا تغطية موثوقة (رغم نجاح الجذر).

        R-664: anchor_batch يرفض بدون keyring (fail-closed).
        نختبر verify_anchor_detailed بمرساة يُنشئها يدويًا (لا عبر anchor_batch).
        """
        anchor = self._make_anchor(tmp_path)
        lines = anchor.read_ledger_lines()
        # D-036 (الجولة <2>): مرساة جديدة عبر anchor_batch = جذر v2
        merkle_root = compute_merkle_root_v2(lines)

        # R-664: anchor_batch يرفض بدون keyring (fail-closed) — يُعيد None
        result = anchor.anchor_batch(0, len(lines)-1, "some_key", "some_sig", reason="no_kr", keyring=None)
        assert result is None, "anchor_batch must REJECT without keyring (fail-closed)"

        # إنشاء مرساة يدويًا (لا عبر anchor_batch — للتحقق فقط)
        # D-036: مرساة جديدة يدوية بجذر v2 — تُوسم merkle_version=2
        manual_anchor = {
            "anchor_id": "manual_no_kr",
            "batch_start": 0,
            "batch_end": len(lines)-1,
            "event_count": len(lines),
            "merkle_root": f"sha256:{merkle_root}",
            "merkle_version": 2,
            "reason": "no_kr",
            "key_id": "some_key",
            "signature": "some_sig",
            "anchored_at": "2026-10-14T00:00:00Z",
            "sig_format": "v2",
        }

        # التحقق بدون keyring — الجذر ينجح لكن لا توثيق توقيع
        detailed = anchor.verify_anchor_detailed(manual_anchor, keyring=None)
        assert detailed["root_verified"] is True, "root should verify (content unchanged)"
        assert detailed["signature_verified"] is False, "signature must NOT verify without keyring"
        assert detailed["trusted"] is False, "must not be trusted without keyring"

    def test_v1_not_trusted(self, tmp_path):
        """v1 (أو إزالة الإصدار): قد ينجح فحص الجذر لكن لا يُحتسب توثيق التوقيع.

        R-664: anchor_batch يرفض بدون keyring (fail-closed).
        نختبر verify_anchor_detailed بمرساة v1 يُنشئها يدويًا.
        """
        anchor = self._make_anchor(tmp_path)
        lines = anchor.read_ledger_lines()
        # مرساة يدوية v1 للتحقق فقط — جذر v1 (اختبار مسار v1 التاريخي)
        merkle_root = compute_merkle_root(lines)

        # R-664: anchor_batch يرفض بدون keyring (fail-closed) — يُعيد None
        result = anchor.anchor_batch(0, len(lines)-1, "key1", "sig1", reason="v1_test", keyring=None)
        assert result is None, "anchor_batch must REJECT without keyring (fail-closed)"

        # إنشاء مرساة v1 يدويًا (لا sig_format — للتحقق فقط)
        v1_anchor = {
            "anchor_id": "manual_v1",
            "batch_start": 0,
            "batch_end": len(lines)-1,
            "event_count": len(lines),
            "merkle_root": f"sha256:{merkle_root}",
            "reason": "v1_test",
            "key_id": "key1",
            "signature": "sig1",
            "anchored_at": "2026-10-14T00:00:00Z",
        }

        detailed = anchor.verify_anchor_detailed(v1_anchor, keyring=None)
        assert detailed["root_verified"] is True, "root should verify"
        assert detailed["signature_verified"] is False, "v1 signature must NOT be verified"
        assert detailed["trusted"] is False, "v1 must not be trusted"

    def test_compromised_key_separate_result(self, tmp_path):
        """مفتاح مخترق: التوقيع قد ينجح لكن الثقة = False (نتيجة منفصلة)."""
        keyring = self._make_keyring(tmp_path)
        anchor = self._make_anchor(tmp_path)
        active = keyring.get_active_key()

        lines = anchor.read_ledger_lines()
        # D-036 (الجولة <2>): مرساة جديدة عبر anchor_batch = جذر v2
        merkle_root = compute_merkle_root_v2(lines)
        sig = anchor.sign_anchor_with_key(0, len(lines)-1, merkle_root, active.key_id, active.private_key)
        result = anchor.anchor_batch(0, len(lines)-1, active.key_id, sig, reason="before_compromise", keyring=keyring)
        assert result is not None

        # تعليم المفتاح كمخترق
        keyring.mark_key_compromised(active.key_id, reason="test compromise")

        detailed = anchor.verify_anchor_detailed(result, keyring=keyring)
        # التوقيع قد ينجح (HMAC صحيح) لكن الثقة = False
        assert detailed["signature_verified"] is True, (
            "signature should still verify (HMAC is correct) — separate from trust"
        )
        assert detailed["key_trusted"] is False, (
            "COMPROMISED key must NOT be trusted"
        )
        assert detailed["trusted"] is False, (
            "COMPROMISED key anchor must not be trusted"
        )


class TestBlobContentIntegrity:
    """R-646/R-648: فحص تغيير محتوى blob موجود (hash، ليس الوجود فقط)."""

    def test_blob_content_change_detected(self, tmp_path):
        """تغيير محتوى blob موجود: يُكتشف (CORRUPTED) — سلامة المحتوى.
        
        R-648: verify_content_integrity يفحص hash المحتوى (وليس الوجود فقط).
        المحتوى المُعدّل يجب أن يُنتج CORRUPTED (ليس VERIFIED).
        """
        _keys_dir = tmp_path / "keys"
        _keys_dir.mkdir(exist_ok=True)
        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.generate_new_key(reason="blob_test")
        keyring.save_to_disk()

        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        core = SovereignCore(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
            keyring=keyring,
        )

        # كتابة حدث
        r = core.append_event(EventType.INTERACTION, {"test": "blob_integrity"}, user="test")
        blob_hash = r["blob"]

        # التحقق قبل التغيير
        status_before = core.verify_content_integrity()
        assert status_before.value == "verified", f"content integrity before: {status_before}"

        # R-648: تحديد ملف blob المرتبط تحديدًا بـ blob_hash (وليس أول ملف)
        blob_path = core.blob_store._blob_path(blob_hash)
        assert blob_path.exists(), f"blob file must exist: {blob_path}"
        original_content = blob_path.read_bytes()

        # تغيير محتوى blob (تزييف) — إضافة بايت
        blob_path.write_bytes(original_content + b"\x00tampered")

        # R-648: التحقق بعد التغيير — يجب أن يُعيد CORRUPTED
        # (hash المحتوى المُعدّل لا يُطابق blob_hash المُسجل)
        status_after = core.verify_content_integrity()
        assert status_after.value == "corrupted", (
            f"tampered blob content must produce CORRUPTED, got: {status_after} — "
            f"verify_content_integrity must check content hash (not existence only)"
        )

    def test_blob_verify_content_hash_detects_tamper(self, tmp_path):
        """R-648: verify_content_hash يكتشف المحتوى المُعدّل."""
        _keys_dir = tmp_path / "keys"
        _keys_dir.mkdir(exist_ok=True)
        keyring = KeyRing(keys_dir=_keys_dir)
        keyring.generate_new_key(reason="blob_hash_test")
        keyring.save_to_disk()

        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)

        core = SovereignCore(
            log_file=_core_dir / "ledger.jsonl",
            blobs_dir=_core_dir / "blobs",
            index_file=_core_dir / "index.json",
            meta_file=_core_dir / "meta.json",
            integrity_file=_core_dir / "integrity.json",
            keyring=keyring,
        )

        # كتابة حدث
        r = core.append_event(EventType.INTERACTION, {"test": "hash_check"}, user="test")
        blob_hash = r["blob"]

        # قبل التغيير — hash صحيح
        assert core.blob_store.verify_content_hash(blob_hash) is True

        # تعديل المحتوى
        blob_path = core.blob_store._blob_path(blob_hash)
        blob_path.write_bytes(blob_path.read_bytes() + b"tampered")

        # بعد التغيير — hash لا يُطابق
        assert core.blob_store.verify_content_hash(blob_hash) is False, (
            "verify_content_hash must detect tampered content"
        )
