"""
اختبار invariants — البوابة 5: آلة حالة المفتاح (R-667)

يختبر أن آلة حالة المفتاح تُطبّق العقد في docs/KEY_STATE_MACHINE.md:
- الحالات الخمس: ACTIVE, ROTATED, LOST, COMPROMISED, EXPIRED
- الانتقالات المسموحة (7) و الممنوعة (5+)
- التوقيع مسموح فقط لـ ACTIVE
- التحقق التاريخي مسموح لـ ACTIVE و ROTATED

منهج TDD (RED → GREEN → LOCK):
- RED: هذا الاختبار يُشغّل و يجب أن يفشل (قبل الإصلاح)
- GREEN: أصلح أقل قدر ممكن من الكود ليمرّ الاختبار
- LOCK: شغّل الاختبار مرة أخرى — يجب أن يمرّ الحالات الـ12
"""

import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.sovereign.keys.state_machine import (
    KeyState,
    KeyStateError,
    VerificationResult,
    ALLOWED_TRANSITIONS,
    transition,
    assert_usable_for_signing,
    assert_usable_for_verification,
    verification_result_for,
    assert_explicit_state,
    translate_status_to_state,
    KEYSTATUS_TO_KEYSTATE,
)
from backend.sovereign.keys.keyring import KeyStatus


class TestKeyStateTransitions:
    """اختبارات البوابة 5 — آلة حالة المفتاح."""

    # ============================================================
    # الحالات 1-5: التوقيع و التحقق
    # ============================================================

    def test_1_signing_with_lost_key_fails_explicitly(self):
        """التوقيع بمفتاح LOST: يجب أن يفشل صراحة.

        لا استثناء غير ملتقط، لا False بصمت.
        رسالة: `KeyStateError: LOST key cannot sign`.
        """
        with pytest.raises(KeyStateError) as exc_info:
            assert_usable_for_signing(KeyState.LOST)

        # الرسالة يجب أن تُشير إلى LOST + cannot sign
        error_msg = str(exc_info.value)
        assert "LOST" in error_msg, f"error message must mention LOST: {error_msg}"
        assert "cannot sign" in error_msg, f"error must say 'cannot sign': {error_msg}"

    def test_2_verification_with_lost_key_returns_unverifiable(self):
        """التحقق بمفتاح LOST: يجب أن يُعيد UNVERIFIABLE_MISSING_KEY.

        ليس False — الفرق جوهري:
        - UNVERIFIABLE_MISSING_KEY = "لا نعرف" (المفتاح مفقود)
        - False = "مزوّر" (التوقيع خاطئ)
        """
        result = verification_result_for(KeyState.LOST)
        assert result == VerificationResult.UNVERIFIABLE_MISSING_KEY, (
            f"LOST key verification must return UNVERIFIABLE_MISSING_KEY, "
            f"got {result} — False would mean 'forged', "
            f"UNVERIFIABLE_MISSING_KEY means 'we don't know'"
        )

    def test_3_signing_with_expired_key_fails(self):
        """التوقيع بمفتاح EXPIRED: يفشل صراحة."""
        with pytest.raises(KeyStateError) as exc_info:
            assert_usable_for_signing(KeyState.EXPIRED)

        error_msg = str(exc_info.value)
        assert "EXPIRED" in error_msg
        assert "cannot sign" in error_msg

    def test_4_signing_with_compromised_key_fails(self):
        """التوقيع بمفتاح COMPROMISED: يفشل صراحة."""
        with pytest.raises(KeyStateError) as exc_info:
            assert_usable_for_signing(KeyState.COMPROMISED)

        error_msg = str(exc_info.value)
        assert "COMPROMISED" in error_msg
        assert "cannot sign" in error_msg

    def test_5_signing_with_rotated_key_fails(self):
        """التوقيع بمفتاح ROTATED: يفشل صراحة (تحقق تاريخي فقط)."""
        with pytest.raises(KeyStateError) as exc_info:
            assert_usable_for_signing(KeyState.ROTATED)

        error_msg = str(exc_info.value)
        assert "ROTATED" in error_msg
        assert "cannot sign" in error_msg

    def test_6_verification_with_rotated_key_succeeds(self):
        """التحقق بمفتاح ROTATED: ينجح (تحقق تاريخي)."""
        result = verification_result_for(KeyState.ROTATED)
        assert result == VerificationResult.VERIFIED, (
            f"ROTATED key verification must succeed (historical), got {result}"
        )

    # ============================================================
    # الحالات 7-10: الانتقالات الممنوعة
    # ============================================================

    def test_7_transition_expired_to_active_fails(self):
        """الانتقال EXPIRED → ACTIVE: يفشل صراحة (لا عودة من النهاية)."""
        with pytest.raises(KeyStateError) as exc_info:
            transition(KeyState.EXPIRED, KeyState.ACTIVE)

        error_msg = str(exc_info.value)
        assert "EXPIRED" in error_msg
        assert "ACTIVE" in error_msg
        assert "FORBIDDEN" in error_msg or "forbidden" in error_msg.lower()

    def test_8_transition_lost_to_active_fails(self):
        """الانتقال LOST → ACTIVE: يفشل صراحة."""
        with pytest.raises(KeyStateError) as exc_info:
            transition(KeyState.LOST, KeyState.ACTIVE)

        error_msg = str(exc_info.value)
        assert "LOST" in error_msg
        assert "ACTIVE" in error_msg

    def test_9_transition_rotated_to_active_fails(self):
        """الانتقال ROTATED → ACTIVE: يفشل صراحة."""
        with pytest.raises(KeyStateError) as exc_info:
            transition(KeyState.ROTATED, KeyState.ACTIVE)

        error_msg = str(exc_info.value)
        assert "ROTATED" in error_msg
        assert "ACTIVE" in error_msg

    def test_10_transition_compromised_to_active_fails(self):
        """الانتقال COMPROMISED → ACTIVE: يفشل صراحة."""
        with pytest.raises(KeyStateError) as exc_info:
            transition(KeyState.COMPROMISED, KeyState.ACTIVE)

        error_msg = str(exc_info.value)
        assert "COMPROMISED" in error_msg
        assert "ACTIVE" in error_msg

    # ============================================================
    # الحالات 11-12: الحالة الصريحة
    # ============================================================

    def test_11_key_without_explicit_state_fails(self):
        """مفتاح بلا حالة صريحة: يفشل عند التحميل.

        لا default، لا "ACTIVE ضمنياً".
        """
        with pytest.raises(KeyStateError) as exc_info:
            assert_explicit_state(None)

        error_msg = str(exc_info.value)
        assert "NO explicit state" in error_msg or "no explicit state" in error_msg.lower(), (
            f"error must mention missing explicit state: {error_msg}"
        )

    def test_12_active_to_expired_then_use_fails(self):
        """الانتقال ACTIVE → EXPIRED ثم استخدامه: يفشل بشكل صحيح.

        EXPIRED نهائي — لا يُستخدم لأي شيء.
        """
        # الانتقال مسموح (ACTIVE → EXPIRED)
        new_state = transition(KeyState.ACTIVE, KeyState.EXPIRED)
        assert new_state == KeyState.EXPIRED

        # استخدام المفتاح بعد EXPIRED — يجب أن يفشل
        with pytest.raises(KeyStateError):
            assert_usable_for_signing(new_state)

        # التحقق — يُعيد UNVERIFIABLE_EXPIRED
        result = verification_result_for(new_state)
        assert result == VerificationResult.UNVERIFIABLE_EXPIRED

    # ============================================================
    # حالات إضافية (ضوابط إيجابية و انتقالات مسموحة)
    # ============================================================

    def test_13_active_key_can_sign(self):
        """ضابط إيجابي: مفتاح ACTIVE يُستخدم للتوقيع."""
        # لا يرفع استثناء
        assert_usable_for_signing(KeyState.ACTIVE)

    def test_14_active_key_can_verify(self):
        """ضابط إيجابي: مفتاح ACTIVE يُستخدم للتحقق."""
        result = verification_result_for(KeyState.ACTIVE)
        assert result == VerificationResult.VERIFIED

    def test_15_allowed_transitions_active(self):
        """الانتقالات المسموحة من ACTIVE (4 انتقالات)."""
        allowed = ALLOWED_TRANSITIONS[KeyState.ACTIVE]
        assert KeyState.ROTATED in allowed
        assert KeyState.LOST in allowed
        assert KeyState.COMPROMISED in allowed
        assert KeyState.EXPIRED in allowed

    def test_16_expired_is_terminal(self):
        """EXPIRED نهائي — لا انتقال مسموح."""
        allowed = ALLOWED_TRANSITIONS[KeyState.EXPIRED]
        assert len(allowed) == 0, f"EXPIRED must be terminal, got {allowed}"

    def test_17_compromised_to_rotated_fails(self):
        """الانتقال COMPROMISED → ROTATED: ممنوع صريحًا."""
        with pytest.raises(KeyStateError):
            transition(KeyState.COMPROMISED, KeyState.ROTATED)

    def test_18_verification_compromised_returns_unverifiable(self):
        """التحقق بمفتاح COMPROMISED: يُعيد UNVERIFIABLE_COMPROMISED."""
        result = verification_result_for(KeyState.COMPROMISED)
        assert result == VerificationResult.UNVERIFIABLE_COMPROMISED

    def test_19_verification_expired_returns_unverifiable(self):
        """التحقق بمفتاح EXPIRED: يُعيد UNVERIFIABLE_EXPIRED."""
        result = verification_result_for(KeyState.EXPIRED)
        assert result == VerificationResult.UNVERIFIABLE_EXPIRED

    def test_20_invalid_state_string_rejected(self):
        """حالة غير صالحة (str) تُرفض صراحة."""
        with pytest.raises(KeyStateError):
            assert_explicit_state("INVALID_STATE")

    def test_21_valid_state_string_converted(self):
        """حالة صالحة (str) تُحوّل إلى KeyState."""
        state = assert_explicit_state("ACTIVE")
        assert state == KeyState.ACTIVE

    def test_22_expired_to_any_fails(self):
        """EXPIRED → أي حالة (كلها): تفشل صراحة."""
        for target in [KeyState.ACTIVE, KeyState.ROTATED, KeyState.LOST, KeyState.COMPROMISED]:
            with pytest.raises(KeyStateError):
                transition(KeyState.EXPIRED, target)

    # ============================================================
    # R-668: ترجمة KeyStatus ↔ KeyState
    # ============================================================

    def test_23_key_status_translates_to_key_state(self):
        """ترجمة KeyStatus (keyring.py) → KeyState (state_machine.py).

        RETIRED → ROTATED (مُستبدل — تحقق تاريخي فقط).
        كل حالة يجب أن تُترجم — إذا وُجد حالة لا تُترجم، فشل صريح.
        """
        # كل حالات KeyStatus تُترجم
        for status_name, expected_state in [
            ("ACTIVE", KeyState.ACTIVE),
            ("RETIRED", KeyState.ROTATED),
            ("LOST", KeyState.LOST),
            ("COMPROMISED", KeyState.COMPROMISED),
            ("EXPIRED", KeyState.EXPIRED),
        ]:
            # ترجمة من str
            result = translate_status_to_state(status_name)
            assert result == expected_state, (
                f"{status_name} must translate to {expected_state}, got {result}"
            )

            # ترجمة من enum
            from backend.sovereign.keys.keyring import KeyStatus as _KS
            enum_val = getattr(_KS, status_name)
            result2 = translate_status_to_state(enum_val)
            assert result2 == expected_state

    def test_24_untranslatable_status_fails(self):
        """حالة لا تُترجم → فشل صريح (KeyStateError)."""
        with pytest.raises(KeyStateError) as exc_info:
            translate_status_to_state("INVALID_STATUS")

        error_msg = str(exc_info.value)
        assert "cannot translate" in error_msg
        assert "INVALID_STATUS" in error_msg

    def test_25_none_status_fails(self):
        """حالة None → فشل صريح (لا default)."""
        with pytest.raises(KeyStateError):
            translate_status_to_state(None)

    def test_26_keyring_keys_translate_to_key_state(self, tmp_path):
        """كل مفتاح يُحمّل من keyring.json تُترجم حالته إلى KeyState.

        إذا وُجد مفتاح بحالة لا تُترجم → فشل صريح.
        """
        from backend.sovereign.keys.keyring import KeyRing
        keys_dir = tmp_path / "keys"
        keys_dir.mkdir()
        keyring = KeyRing(keys_dir=keys_dir)
        key_rec = keyring.generate_new_key(reason="test translate")

        # ترجمة حالة المفتاح
        state = translate_status_to_state(key_rec.status)
        assert state == KeyState.ACTIVE

        # مفتاح RETIRED → ROTATED
        key_rec.status = KeyStatus.RETIRED
        state2 = translate_status_to_state(key_rec.status)
        assert state2 == KeyState.ROTATED

        # مفتاح COMPROMISED → COMPROMISED
        key_rec.status = KeyStatus.COMPROMISED
        state3 = translate_status_to_state(key_rec.status)
        assert state3 == KeyState.COMPROMISED
