"""
آلة حالة المفتاح (Key State Machine) — R-667 (البوابة 5)

العقد: docs/KEY_STATE_MACHINE.md
القاعدة الحاكمة: الحالة شيء صريح، ليس ضمنياً. مفتاح بلا حالة = فشل.

الحالات الخمس: ACTIVE, ROTATED, LOST, COMPROMISED, EXPIRED
الانتقالات المسموحة: 7
الانتقالات الممنوعة: 5+ (كل شيء خارج القاموس)
"""

from enum import Enum
from typing import Set, Dict


class KeyState(str, Enum):
    """حالات المفتاح — العقد في docs/KEY_STATE_MACHINE.md"""
    ACTIVE = "ACTIVE"
    ROTATED = "ROTATED"
    LOST = "LOST"
    COMPROMISED = "COMPROMISED"
    EXPIRED = "EXPIRED"


class KeyStateError(Exception):
    """خطأ صريح للانتقالات الممنوعة أو الاستخدام غير المسموح."""
    pass


class VerificationResult(str, Enum):
    """نتيجة التحقق — صريحة (ليست bool)."""
    VERIFIED = "VERIFIED"
    UNVERIFIABLE_MISSING_KEY = "UNVERIFIABLE_MISSING_KEY"
    UNVERIFIABLE_COMPROMISED = "UNVERIFIABLE_COMPROMISED"
    UNVERIFIABLE_EXPIRED = "UNVERIFIABLE_EXPIRED"
    UNVERIFIABLE_UNKNOWN_STATE = "UNVERIFIABLE_UNKNOWN_STATE"


# ============================================================
# الانتقالات المسموحة (7) — العقد
# ============================================================
ALLOWED_TRANSITIONS: Dict[KeyState, Set[KeyState]] = {
    KeyState.ACTIVE: {
        KeyState.ROTATED,
        KeyState.LOST,
        KeyState.COMPROMISED,
        KeyState.EXPIRED,
    },
    KeyState.ROTATED: {
        KeyState.EXPIRED,
    },
    KeyState.LOST: {
        KeyState.EXPIRED,
    },
    KeyState.COMPROMISED: {
        KeyState.EXPIRED,
    },
    KeyState.EXPIRED: set(),  # نهائي — لا انتقال
}


def transition(current: KeyState, target: KeyState) -> KeyState:
    """يُنفّذ انتقالًا — يرفع KeyStateError إذا كان ممنوعًا.

    كل انتقال غير موجود في ALLOWED_TRANSITIONS = ممنوع.
    """
    if not isinstance(current, KeyState):
        raise KeyStateError(f"current state must be KeyState, got {type(current).__name__}")
    if not isinstance(target, KeyState):
        raise KeyStateError(f"target state must be KeyState, got {type(target).__name__}")

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise KeyStateError(
            f"FORBIDDEN transition: {current.value} → {target.value}. "
            f"Allowed transitions from {current.value}: "
            f"{sorted(s.value for s in allowed) if allowed else 'NONE (terminal state)'}"
        )

    return target


def assert_usable_for_signing(state: KeyState) -> None:
    """يرفع استثناء إذا كانت الحالة لا تسمح بالتوقيع.

    يُسمح فقط: ACTIVE
    يُرفض صراحة: ROTATED, LOST, COMPROMISED, EXPIRED
    """
    if not isinstance(state, KeyState):
        raise KeyStateError(f"state must be KeyState, got {type(state).__name__}")

    if state != KeyState.ACTIVE:
        raise KeyStateError(
            f"{state.value} key cannot sign — only ACTIVE keys can sign"
        )


def assert_usable_for_verification(state: KeyState) -> VerificationResult:
    """يرفع استثناء إذا كانت الحالة لا تسمح بالتحقق.

    يُسمح: ACTIVE, ROTATED (تحقق تاريخي)
    يُرفض صراحة: LOST, COMPROMISED, EXPIRED (تُعاد نتيجة صريحة)
    """
    if not isinstance(state, KeyState):
        raise KeyStateError(f"state must be KeyState, got {type(state).__name__}")

    if state == KeyState.ACTIVE:
        return VerificationResult.VERIFIED
    elif state == KeyState.ROTATED:
        return VerificationResult.VERIFIED  # تحقق تاريخي — مسموح
    elif state == KeyState.LOST:
        raise KeyStateError(
            "LOST key cannot verify — UNVERIFIABLE_MISSING_KEY "
            "(we don't know, not forged)"
        )
    elif state == KeyState.COMPROMISED:
        raise KeyStateError(
            "COMPROMISED key cannot verify — UNVERIFIABLE_COMPROMISED"
        )
    elif state == KeyState.EXPIRED:
        raise KeyStateError(
            "EXPIRED key cannot verify — UNVERIFIABLE_EXPIRED"
        )
    else:
        raise KeyStateError(
            f"unknown state {state} — UNVERIFIABLE_UNKNOWN_STATE"
        )


def verification_result_for(state: KeyState) -> VerificationResult:
    """يُعيد نتيجة التحقق (صريحة — ليست bool).

    LOST → UNVERIFIABLE_MISSING_KEY (وليس False — الفرق جوهري)
    COMPROMISED → UNVERIFIABLE_COMPROMISED
    EXPIRED → UNVERIFIABLE_EXPIRED
    ACTIVE/ROTATED → VERIFIED
    """
    if not isinstance(state, KeyState):
        raise KeyStateError(f"state must be KeyState, got {type(state).__name__}")

    if state == KeyState.ACTIVE:
        return VerificationResult.VERIFIED
    elif state == KeyState.ROTATED:
        return VerificationResult.VERIFIED
    elif state == KeyState.LOST:
        return VerificationResult.UNVERIFIABLE_MISSING_KEY
    elif state == KeyState.COMPROMISED:
        return VerificationResult.UNVERIFIABLE_COMPROMISED
    elif state == KeyState.EXPIRED:
        return VerificationResult.UNVERIFIABLE_EXPIRED
    else:
        return VerificationResult.UNVERIFIABLE_UNKNOWN_STATE


def assert_explicit_state(state) -> KeyState:
    """يتحقق أن الحالة صريحة (ليست ضمنية).

    مفتاح بلا حالة = فشل — لا default، لا "ACTIVE ضمنياً".
    """
    if state is None:
        raise KeyStateError(
            "key has NO explicit state — implicit default is FORBIDDEN"
        )
    if not isinstance(state, KeyState):
        # يُحاول التحويل من str (مثل "ACTIVE")
        try:
            return KeyState(state)
        except ValueError:
            raise KeyStateError(
                f"invalid key state: {state!r} — must be one of "
                f"{[s.value for s in KeyState]}"
            )
    return state


# ============================================================
# R-668: ترجمة KeyStatus (keyring.py) → KeyState (state_machine.py)
# ============================================================

# RETIRED → ROTATED: مفتاح مُستبدل — تحقق تاريخي فقط، لا توقيع
KEYSTATUS_TO_KEYSTATE = {
    "ACTIVE": KeyState.ACTIVE,
    "RETIRED": KeyState.ROTATED,  # RETIRED = مُستبدل (تحقق تاريخي فقط)
    "LOST": KeyState.LOST,
    "COMPROMISED": KeyState.COMPROMISED,
    "EXPIRED": KeyState.EXPIRED,
}


def translate_status_to_state(status) -> KeyState:
    """يُترجم KeyStatus (keyring.py) إلى KeyState (state_machine.py).

    RETIRED → ROTATED (مُستبدل — تحقق تاريخي فقط)
    إذا وُجد حالة لا تُترجم → KeyStateError (فشل صريح).
    """
    if status is None:
        raise KeyStateError(
            "cannot translate None KeyStatus — key has no explicit state"
        )

    # KeyStatus قد يكون enum أو str
    status_str = status.value if hasattr(status, "value") else str(status)
    status_upper = status_str.upper()

    if status_upper not in KEYSTATUS_TO_KEYSTATE:
        raise KeyStateError(
            f"cannot translate KeyStatus {status_str!r} to KeyState — "
            f"valid statuses: {list(KEYSTATUS_TO_KEYSTATE.keys())}"
        )

    return KEYSTATUS_TO_KEYSTATE[status_upper]
