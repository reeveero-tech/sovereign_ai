"""
Invariant 2: لا أحداث بدون تصنيف في اليدجر (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل حدث في ledger.jsonl إما:
- موقّع بمفتاح في KeyRing (VERIFIED)
- داخل نطاق مرساة موثقة (ANCHORED)
- مُصنّف كـ UNVERIFIABLE_MISSING_KEY (LEGACY_PRE_KEYRING)

أي حدث لا ينتمي لأي من الثلاثة = فشل.
"""

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from backend.sovereign.ledger import LedgerAnchor
from backend.sovereign.keys import KeyRing, SignatureVerifier, VerificationStatus


# R-682 (Task 3.1): synthetic ledger fixture — replaces 45MB runtime data dependency.
# (استيراد مباشر — لا يعتمد على tests/__init__.py لأنه يكسر جمع backend/tests)
import importlib.util as _ilu
_synthetic_path = _REPO_ROOT / "tests" / "fixtures" / "synthetic_ledger.py"
_spec = _ilu.spec_from_file_location("synthetic_ledger", str(_synthetic_path))
_sl_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_sl_mod)
build_synthetic_ledger = _sl_mod.build_synthetic_ledger


@pytest.fixture
def synthetic_ledger(tmp_path):
    """Build a small signed ledger + anchors + keys in tmp_path."""
    return build_synthetic_ledger(tmp_path / "data")


def test_no_unsigned_ledger_events(synthetic_ledger):
    """
    Invariant: كل حدث في اليدجر يجب أن يكون مصنّفًا (signed/anchored/unverifiable).
    لا حدث 'مجهول' بدون تصنيف.

    R-682 (Task 3.1): uses synthetic_ledger fixture instead of 45MB runtime data.
    """
    _real_ledger = synthetic_ledger["ledger"]
    _real_anchors = synthetic_ledger["anchors"]
    _keys_dir = synthetic_ledger["keys_dir"]

    # قراءة الأسطر مباشرة
    lines = []
    with open(_real_ledger, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                lines.append(line)

    assert lines, "fixture: empty ledger"

    # تحميل KeyRing (من الـ fixture dir — ليس من data/keys الحقيقي)
    keyring = KeyRing(keys_dir=_keys_dir)
    keyring.load_from_disk()
    verifier = SignatureVerifier(keyring)

    anchor = LedgerAnchor(ledger_path=_real_ledger, anchors_path=_real_anchors)

    # الأحداث المُغطاة بالمراسي
    anchors_list = anchor.list_anchors()
    anchored_events = set()
    for a in anchors_list:
        for i in range(a["batch_start"], a["batch_end"] + 1):
            anchored_events.add(i)

    # فحص كل حدث
    unclassified = []
    for i, line in enumerate(lines):
        try:
            event = json.loads(line)
        except Exception:
            # حدث غير قابل للقراءة (JSON تالف) — غير مصنّف
            unclassified.append((i, "invalid_json"))
            continue

        # تصنيف الحدث
        result = verifier.verify_event(event)
        status = result.status

        if status == VerificationStatus.VERIFIED:
            continue  # موقّع — مصنّف
        elif status == VerificationStatus.UNVERIFIABLE_MISSING_KEY:
            continue  # غير قابل للتحقق (مفتاح فُقد أو LEGACY) — مصنّف
        elif status == VerificationStatus.INVALID:
            # مزوّر — مصنّف لكنه خطير (يجب أن يكون 0)
            unclassified.append((i, "INVALID (tampered)"))
            continue
        else:
            unclassified.append((i, f"unknown_status:{status}"))

    # كل حدث يجب أن يكون مصنّفًا (أي حالة معروفة)
    # الحدث الوحيد غير المقبول هو INVALID (تزوير) — يجب أن يكون 0
    invalid_events = [u for u in unclassified if "INVALID" in u[1] or "invalid_json" in u[1]]
    assert len(invalid_events) == 0, (
        f"Found {len(invalid_events)} INVALID/unparseable events "
        f"(possible tampering or corruption): {invalid_events[:5]}"
    )

    # الأحداث غير المصنّفة (بدون أي حالة) يجب أن تكون 0
    truly_unclassified = [u for u in unclassified if "unknown_status" in u[1]]
    assert len(truly_unclassified) == 0, (
        f"Found {len(truly_unclassified)} events with no classification: "
        f"{truly_unclassified[:5]}"
    )


def test_all_anchors_valid(synthetic_ledger):
    """كل المراسي المسجلة يجب أن تكون مُتحقّقة (المحتوى لم يتغير).

    R-682 (Task 3.1): uses synthetic_ledger fixture.
    """
    _real_ledger = synthetic_ledger["ledger"]
    _real_anchors = synthetic_ledger["anchors"]
    _keys_dir = synthetic_ledger["keys_dir"]

    anchor = LedgerAnchor(ledger_path=_real_ledger, anchors_path=_real_anchors)
    anchors = anchor.list_anchors()

    assert anchors, "fixture: no anchors to verify"

    # R-682: تحميل KeyRing من الـ fixture dir
    from backend.sovereign.keys.keyring import KeyRing as _KeyRing
    real_keyring = _KeyRing(keys_dir=_keys_dir)
    real_keyring.load_from_disk()
    if not real_keyring._keys:
        real_keyring = None

    for a in anchors:
        # التفاصيل — لتمييز v1 (لا توقيع) من v2 (مع توقيع)
        detailed = anchor.verify_anchor_detailed(a, keyring=real_keyring)
        # الجذر يجب أن ينجح (المحتوى لم يتغير)
        assert detailed["root_verified"] is True, (
            f"Anchor {a['anchor_id']} root failed: {detailed['message']}"
        )
        # v2: التوقيع يجب أن يُتحقق (إذا وُجد keyring)
        if a.get("sig_format") == "v2" and real_keyring is not None:
            assert detailed["signature_verified"] is True, (
                f"Anchor {a['anchor_id']} v2 signature failed: {detailed['message']}"
            )
        # v1: التوقيع لا يُوثّق (موثق في REPORT_V2.md — ليست موثوقة تشفيريًا)
        if a.get("sig_format") != "v2":
            # v1 — لا توقيع v2، لا نطلب توثيق التوقيع
            pass


def test_anchored_coverage(synthetic_ledger):
    """التغطية بالمراسي — كل الأحداث القديمة يجب أن تكون مُغطاة.

    R-682 (Task 3.1): uses synthetic_ledger fixture.
    """
    _real_ledger = synthetic_ledger["ledger"]
    _real_anchors = synthetic_ledger["anchors"]

    lines = []
    with open(_real_ledger, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                lines.append(line)

    assert lines, "fixture: empty ledger"

    anchor = LedgerAnchor(ledger_path=_real_ledger, anchors_path=_real_anchors)
    anchors = anchor.list_anchors()
    anchored_events = set()
    for a in anchors:
        for i in range(a["batch_start"], a["batch_end"] + 1):
            anchored_events.add(i)

    # التغطية يجب أن تكون عالية (> 90% للأحداث القديمة)
    coverage = len(anchored_events) / len(lines)
    assert coverage > 0.9, (
        f"Anchored coverage too low: {coverage:.2%} "
        f"({len(anchored_events)}/{len(lines)} events)"
    )
