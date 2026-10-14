"""
اختبار invariants — البوابة 4: حماية توقيع المرساة v2 (R-664)

يختبر أن `verify_anchor` يرفض صراحةً سبع طرق للاعتداء على توقيع
المرساة v2. كل طريقة اختبار فرعي منفصل.

منهج TDD (RED → GREEN → LOCK):
- RED: هذا الاختبار يُشغّل و يجب أن يفشل (قبل الإصلاح)
- GREEN: أصلح أقل قدر ممكن من الكود ليمرّ الاختبار
- LOCK: شغّل الاختبار مرة أخرى — يجب أن يمرّ السبع حالات

السبع طرق للاعتداء:
1. توقيع عشوائي بطول صحيح (43 حرفًا base64url، لا يطابق مفتاحًا حقيقيًا)
2. توقيع صحيح بمفتاح مختلف (وقّع الجذر بمفتاح آخر، ثم حاول حقنه)
3. توقيع صحيح بصيغة خاطئة (base64 بدلاً من base64url)
4. مرساة بلا حقل `signature` أصلاً
5. مرساة بتوقيع فارغ (`"signature": ""`)
6. مرساة بتوقيع null (`"signature": null`)
7. مرساة بتوقيع مُعاد استخدامه (بدّل `merkle_root` فقط، احتفظ بالتوقيع القديم)

في كل حالة: `verify_anchor(anchor, ledger)` يجب أن يُعيد **رفضًا صريحًا**
(`root_verified = False` أو `signature_verified = False`)، لا استثناء
غير ملتقط، لا `None`، لا `True` بالخطأ.

R-664: الحماية — `anchor_batch` يجب أن يتحقق من صحة `signature`
قبل كتابة المرساة (لا يقبل توقيعًا تعسفيًا).
"""

import hashlib
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.sovereign.ledger.anchor import LedgerAnchor as AnchorManager
from backend.sovereign.keys.keyring import KeyRing, KeyStatus


class TestAnchorRejectsArbitrarySignature:
    """اختبارات البوابة 4 — رفض التوقيع التعسفي للمرساة v2."""

    def _setup(self, tmp_path):
        """يُنشئ ledger + KeyRing + مرساة صحيحة (للاعتداء عليها)."""
        # Ledger (3 أحداث اختبارية)
        ledger_path = tmp_path / "ledger.jsonl"
        anchors_path = tmp_path / "ledger.anchors.jsonl"
        events = [
            {"event_type": "test::event1", "payload": {"a": 1}},
            {"event_type": "test::event2", "payload": {"b": 2}},
            {"event_type": "test::event3", "payload": {"c": 3}},
        ]
        lines = []
        for ev in events:
            event_hash = hashlib.sha256(
                json.dumps(ev, sort_keys=True).encode()
            ).hexdigest()
            ev["hash"] = event_hash
            lines.append(json.dumps(ev, sort_keys=True))
        ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # KeyRing (مفتاح ACTIVE)
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir(exist_ok=True)
        keyring = KeyRing(keys_dir=keys_dir)
        key_rec = keyring.generate_new_key(reason="test gate4")
        key_id = key_rec.key_id
        test_key = key_rec.private_key

        manager = AnchorManager(
            ledger_path=ledger_path,
            anchors_path=anchors_path,
        )

        # مرساة صحيحة (v2)
        from backend.sovereign.ledger.anchor import compute_merkle_root
        batch_lines = lines[0:3]
        merkle_root = compute_merkle_root(batch_lines)
        event_count = len(batch_lines)
        sig_data = manager.compute_anchor_signature_data(
            0, 2, event_count, merkle_root, key_id
        )
        import hmac as _hmac
        import hashlib as _hashlib
        signature = _hmac.new(
            test_key.encode("utf-8"),
            sig_data.encode("utf-8"),
            _hashlib.sha256
        ).hexdigest()

        valid_anchor = {
            "anchor_id": "test_anchor_001",
            "batch_start": 0,
            "batch_end": 2,
            "event_count": event_count,
            "merkle_root": f"sha256:{merkle_root}",
            "reason": "TEST_GATE4",
            "key_id": key_id,
            "signature": signature,
            "anchored_at": "2026-10-14T00:00:00Z",
            "notes": "test anchor for gate4",
            "sig_format": "v2",
            "sig_data_v2": sig_data,
        }

        return {
            "manager": manager,
            "keyring": keyring,
            "key_id": key_id,
            "test_key": test_key,
            "merkle_root": merkle_root,
            "signature": signature,
            "valid_anchor": valid_anchor,
            "lines": lines,
        }

    def test_1_random_signature_correct_length_rejected(self, tmp_path):
        """الاعتداء 1: توقيع عشوائي بطول صحيح — يجب أن يُرفض.

        توقيع عشوائي (64 حرفًا hex — طول HMAC-SHA256).

        R-665: يفحص verify_anchor نفسه (وليس verify_anchor_detailed).
        المشكلة: verify_anchor يُعيد root_verified فقط — إذا كان الجذر
        صحيحًا، يُعيد True بالخطأ رغم فشل التوقيع. هذا هو الضعف (RED).
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = dict(setup["valid_anchor"])

        # توقيع عشوائي (64 حرفًا hex — طول HMAC-SHA256)
        fake_sig = secrets.token_hex(32)
        anchor["signature"] = fake_sig

        # R-665: فحص verify_anchor نفسه (tuple — العنصر الأول = root_verified)
        # إذا كان root صحيحًا لكن التوقيع فاشل — verify_anchor يُعيد True
        # بالخطأ (لا يفحص التوقيع). هذا يجب أن يُرفض.
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]  # العنصر الأول
        message = result[1]  # العنصر الثاني (سبب الرفض)

        # يجب أن يُرفض — success = False (التوقيع فاشل، المرساة غير صالحة)
        # حتى لو كان الجذر صحيحًا، التوقيع العشوائي يُرفض
        assert success is False, (
            f"verify_anchor must REJECT anchor with random signature — "
            f"but it returned success={success} (root_verified only). "
            f"This means verify_anchor only checks root, not signature! "
            f"(message: {message})"
        )
        # الرسالة يجب أن تُشير إلى الرفض (وليس القبول)
        assert "mismatch" in message.lower() or "reject" in message.lower() or "fail" in message.lower(), (
            f"verify_anchor message must indicate rejection — got: {message}"
        )

    def test_2_valid_signature_wrong_key_rejected(self, tmp_path):
        """الاعتداء 2: توقيع صحيح بمفتاح مختلف — يجب أن يُرفض.

        نُوقّع الجذر بمفتاح آخر (ليس في KeyRing)، ثم نحاول حقنه.
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = dict(setup["valid_anchor"])

        # مفتاح آخر (ليس في KeyRing)
        other_key = secrets.token_urlsafe(32)
        sig_data = manager.compute_anchor_signature_data(
            0, 2, 3, setup["merkle_root"], setup["key_id"]
        )
        import hmac as _hmac
        import hashlib as _hashlib
        other_sig = _hmac.new(
            other_key.encode("utf-8"),
            sig_data.encode("utf-8"),
            _hashlib.sha256
        ).hexdigest()

        # حقن التوقيع بالمفتاح الآخر (لكن key_id يُشير للمفتاح الحقيقي)
        anchor["signature"] = other_sig

        # R-665: فحص verify_anchor نفسه
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]
        message = result[1]
        assert success is False, (
            f"verify_anchor must REJECT signature from DIFFERENT key — "
            f"but returned success={success} (message: {message})"
        )

    def test_3_valid_signature_wrong_format_rejected(self, tmp_path):
        """الاعتداء 3: توقيع صحيح بصيغة خاطئة — يجب أن يُرفض.

        خذ توقيعًا صحيحًا (hex)، غيّر صيغته إلى base64.
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = dict(setup["valid_anchor"])

        # توقيع صحيح لكن بصيغة base64 (وليس hex)
        correct_sig = setup["signature"]
        # تحويل hex إلى base64
        import base64
        sig_bytes = bytes.fromhex(correct_sig)
        b64_sig = base64.b64encode(sig_bytes).decode()

        anchor["signature"] = b64_sig

        # R-665: فحص verify_anchor نفسه
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]
        message = result[1]
        assert success is False, (
            f"verify_anchor must REJECT signature in WRONG FORMAT — "
            f"but returned success={success} (message: {message})"
        )

    def test_4_missing_signature_field_rejected(self, tmp_path):
        """الاعتداء 4: مرساة بلا حقل `signature` — يجب أن يُرفض.

        احذف حقل `signature` من المرساة.
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = dict(setup["valid_anchor"])

        # حذف حقل signature (لكن لا نحذف المرساة نفسها — فقط في الذاكرة)
        anchor.pop("signature", None)

        # R-665: فحص verify_anchor نفسه
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]
        message = result[1]
        assert success is False, (
            f"verify_anchor must REJECT anchor WITHOUT signature — "
            f"but returned success={success} (message: {message})"
        )

    def test_5_empty_signature_rejected(self, tmp_path):
        """الاعتداء 5: توقيع فارغ (`""`) — يجب أن يُرفض."""
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = dict(setup["valid_anchor"])

        anchor["signature"] = ""

        # R-665: فحص verify_anchor نفسه
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]
        message = result[1]
        assert success is False, (
            f"verify_anchor must REJECT EMPTY signature — "
            f"but returned success={success} (message: {message})"
        )

    def test_6_null_signature_rejected(self, tmp_path):
        """الاعتداء 6: توقيع null — يجب أن يُرفض."""
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = dict(setup["valid_anchor"])

        anchor["signature"] = None

        # R-665: فحص verify_anchor نفسه
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]
        message = result[1]
        assert success is False, (
            f"verify_anchor must REJECT NULL signature — "
            f"but returned success={success} (message: {message})"
        )

    def test_7_reused_signature_with_different_root_rejected(self, tmp_path):
        """الاعتداء 7: توقيع مُعاد استخدامه مع جذر مختلف — يجب أن يُرفض.

        خذ مرساة موقّعة صحيحة، بدّل `merkle_root` فقط، احتفظ بالتوقيع القديم.
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = dict(setup["valid_anchor"])

        # جذر مختلف (عشوائي)
        fake_root = hashlib.sha256(b"different_root").hexdigest()
        anchor["merkle_root"] = f"sha256:{fake_root}"
        # التوقيع القديم (يُغطي الجذر الأصلي — ليس الجديد)

        # R-665: فحص verify_anchor نفسه
        # (توقيع قديم + جذر مختلف — يجب أن يُرفض الجذر و التوقيع)
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]
        message = result[1]
        # الجذر مختلف — root_verified = False → success = False
        assert success is False, (
            f"verify_anchor must REJECT reused signature with DIFFERENT root — "
            f"but returned success={success} (message: {message})"
        )

    def test_8_anchor_batch_rejects_arbitrary_signature(self, tmp_path):
        """الاعتداء 8 (إضافي): `anchor_batch` يجب أن يرفض توقيعًا تعسفيًا.

        R-664: الحماية — `anchor_batch` لا يجب أن يقبل توقيعًا تعسفيًا
        و يكتب المرساة. يجب أن يتحقق من صحة `signature` أولاً.

        هذا اختبار منفصل — يختبر مسار الإنشاء (وليس التحقق).
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]

        # توقيع تعسفي (عشوائي — ليس HMAC صحيح)
        fake_sig = secrets.token_hex(32)

        # محاولة إنشاء مرساة بتوقيع تعسفي (مع keyring — المفتاح موجود)
        result = manager.anchor_batch(
            batch_start=0,
            batch_end=2,
            key_id=setup["key_id"],
            signature=fake_sig,
            reason="TEST_GATE4_ATTACK",
            keyring=keyring,
        )

        # يجب أن يُرفض (يُعيد None) — لا يقبل توقيعًا تعسفيًا
        assert result is None, (
            f"anchor_batch must REJECT arbitrary signature — "
            f"but it created an anchor with fake signature. "
            f"This means arbitrary signatures are accepted!"
        )

    def test_10_anchor_batch_accepts_valid_signature(self, tmp_path):
        """ضابط إيجابي (الإنشاء): `anchor_batch` يجب أن يقبل توقيعًا صحيحًا.

        R-664: الحماية يجب ألا تُكسر التوقيع الصحيح — فقط التعسفي.
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]

        # توقيع صحيح (HMAC-SHA256 لبيانات v2 بالمفتاح الحقيقي)
        result = manager.anchor_batch(
            batch_start=0,
            batch_end=2,
            key_id=setup["key_id"],
            signature=setup["signature"],
            reason="TEST_GATE4_VALID",
            keyring=keyring,
        )

        # يجب أن ينجح (يُعيد المرساة) — التوقيع الصحيح يُقبل
        assert result is not None, (
            f"anchor_batch must ACCEPT valid signature — "
            f"but it returned None. This means the protection "
            f"is too strict (breaks valid signatures)!"
        )
        assert result["anchor_id"], "anchor must have anchor_id"
        assert result["sig_format"] == "v2"

    def test_11_anchor_batch_rejects_no_keyring(self, tmp_path):
        """R-664: `anchor_batch` بدون keyring — يجب أن يُرفض (fail-closed).

        إذا لم يُمرر keyring، لا يمكن التحقق — نُرفض.
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]

        # لا keyring — يجب أن يُرفض (fail-closed)
        result = manager.anchor_batch(
            batch_start=0,
            batch_end=2,
            key_id=setup["key_id"],
            signature=setup["signature"],
            reason="TEST_GATE4_NO_KEYRING",
            keyring=None,
        )

        # يجب أن يُرفض (يُعيد None) — لا keyring = لا تحقق = رفض
        assert result is None, (
            f"anchor_batch without keyring must be REJECTED (fail-closed) — "
            f"but it created an anchor. This means arbitrary signatures "
            f"are accepted when no keyring is provided!"
        )

    def test_12_random_signature_base64url_43_chars_rejected(self, tmp_path):
        """الاعتداء 12 (R-665): توقيع عشوائي 43 حرفًا base64url — يجب أن يُرفض.

        كما طلب المالك: «توقيع عشوائي بطول صحيح: 43 حرفاً base64url
        عشوائياً، لكنه لا يطابق مفتاحاً حقيقياً."
        """
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = dict(setup["valid_anchor"])

        # توقيع عشوائي (43 حرفًا base64url — تنسيق المفتاح، ليس التوقيع)
        fake_sig = secrets.token_urlsafe(32)  # 43 حرفًا base64url
        assert len(fake_sig) == 43, f"expected 43 chars, got {len(fake_sig)}"
        anchor["signature"] = fake_sig

        # R-665: فحص verify_anchor نفسه
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]
        message = result[1]
        assert success is False, (
            f"verify_anchor must REJECT 43-char base64url random signature — "
            f"but returned success={success} (message: {message})"
        )

    def test_9_valid_anchor_accepted(self, tmp_path):
        """ضابط إيجابي: مرساة صحيحة يجب أن تُقبل (signature_verified = True)."""
        setup = self._setup(tmp_path)
        manager = setup["manager"]
        keyring = setup["keyring"]
        anchor = setup["valid_anchor"]

        # R-665: فحص verify_anchor نفسه (ضابط إيجابي)
        result = manager.verify_anchor(anchor, keyring=keyring)
        success = result[0]
        message = result[1]
        assert success is True, (
            f"verify_anchor must ACCEPT valid anchor — "
            f"but returned success={success} (message: {message})"
        )
        # التفاصيل أيضاً (root + signature + trusted)
        detailed = manager.verify_anchor_detailed(anchor, keyring=keyring)
        assert detailed["root_verified"] is True
        assert detailed["signature_verified"] is True
        assert detailed["key_trusted"] is True
        assert detailed["trusted"] is True
