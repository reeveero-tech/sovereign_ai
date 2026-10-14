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


def test_no_unsigned_ledger_events():
    """
    Invariant: كل حدث في اليدجر يجب أن يكون مصنّفًا (signed/anchored/unverifiable).
    لا حدث 'مجهول' بدون تصنيف.

    ملاحظة: يقرأ السجل الحقيقي (data/sovereign_core/ledger.jsonl) مباشرة —
    ليس السجل المعزول في SOVEREIGN_DATA_ROOT (راجع R-619).
    """
    # R-619: قراءة السجل الحقيقي مباشرة (وليس المعزول)
    _real_ledger = _REPO_ROOT / "data" / "sovereign_core" / "ledger.jsonl"
    if not _real_ledger.exists():
        pytest.skip("real ledger not found")

    # قراءة الأسطر مباشرة
    lines = []
    with open(_real_ledger, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                lines.append(line)

    if not lines:
        pytest.skip("real ledger is empty — nothing to verify")

    # تحميل KeyRing
    keyring = KeyRing()
    keyring.load_from_disk()
    verifier = SignatureVerifier(keyring)

    # R-619: المراسي — استخدام المسارات الحقيقية
    _real_anchors = _REPO_ROOT / "data" / "sovereign_core" / "ledger.anchors.jsonl"
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


def test_all_anchors_valid():
    """كل المراسي المسجلة يجب أن تكون مُتحقّقة (المحتوى لم يتغير)."""
    # R-619: استخدام المسارات الحقيقية مباشرة
    _real_ledger = _REPO_ROOT / "data" / "sovereign_core" / "ledger.jsonl"
    _real_anchors = _REPO_ROOT / "data" / "sovereign_core" / "ledger.anchors.jsonl"
    anchor = LedgerAnchor(ledger_path=_real_ledger, anchors_path=_real_anchors)
    anchors = anchor.list_anchors()

    if not anchors:
        pytest.skip("no anchors to verify")

    for a in anchors:
        ok, msg = anchor.verify_anchor(a)
        assert ok is True, (
            f"Anchor {a['anchor_id']} failed verification: {msg}"
        )


def test_anchored_coverage():
    """التغطية بالمراسي — كل الأحداث القديمة يجب أن تكون مُغطاة."""
    # R-619: قراءة السجل الحقيقي مباشرة
    _real_ledger = _REPO_ROOT / "data" / "sovereign_core" / "ledger.jsonl"
    if not _real_ledger.exists():
        pytest.skip("real ledger not found")

    lines = []
    with open(_real_ledger, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                lines.append(line)

    if not lines:
        pytest.skip("real ledger is empty")

    # R-619: استخدام المسارات الحقيقية للمراسي
    _real_anchors = _REPO_ROOT / "data" / "sovereign_core" / "ledger.anchors.jsonl"
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
