"""
اختبارات مرساة اليدجر (Merkle Anchoring) — المرحلة 2 من ROADMAP_V2

تتحقق من:
1. compute_merkle_root — بناء شجرة Merkle صحيحة
2. verify_merkle_root — التحقق من الجذر (أي تغيير يُكشف)
3. LedgerAnchor.anchor_batch — إنشاء مرساة لنطاق
4. LedgerAnchor.verify_anchor — التحقق من مرساة (فشل عند التلاعب)
5. مرساة لنطاق الأحداث القديمة الفعلية (11,777 حدثًا)
"""

import json
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
import sys
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.sovereign.ledger import (
    LedgerAnchor,
    compute_merkle_root,
    verify_merkle_root,
    hash_leaf,
)


# ============================================================
# اختبارات Merkle الأساسية
# ============================================================

def test_merkle_root_empty_raises():
    """قائمة فارغة يجب أن ترفع خطأ (لا يمكن حساب جذر لقائمة فارغة)."""
    with pytest.raises(ValueError):
        compute_merkle_root([])


def test_merkle_root_single_line():
    """سطر واحد — الجذر هو تجزئة السطر نفسه."""
    line = '{"test": "event"}'
    root = compute_merkle_root([line])
    expected = hash_leaf(line)
    assert root == expected


def test_merkle_root_deterministic():
    """نفس الأسطر تُنتج نفس الجذر دائمًا (حتمية)."""
    lines = ['{"a": 1}', '{"b": 2}', '{"c": 3}', '{"d": 4}']
    root1 = compute_merkle_root(lines)
    root2 = compute_merkle_root(lines)
    assert root1 == root2, "Merkle root must be deterministic"


def test_merkle_root_detects_any_change():
    """
    الجوهر: أي تغيير في أي بايت في أي سطر يُغيّر الجذر بالكامل.
    هذا هو ما يجعل التلاعب مستحيلًا دون كشف.
    """
    original_lines = [
        '{"hash": "abc", "prev_hash": "xyz"}',
        '{"hash": "def", "prev_hash": "abc"}',
        '{"hash": "ghi", "prev_hash": "def"}',
    ]
    original_root = compute_merkle_root(original_lines)

    # التحقق الأصلي ينجح
    assert verify_merkle_root(original_lines, original_root) is True

    # تغيير حرف واحد في السطر الثاني → الجذر يتغير → التحقق يفشل
    tampered_lines = list(original_lines)
    tampered_lines[1] = tampered_lines[1].replace("def", "deX")  # تغيير حرف
    tampered_root = compute_merkle_root(tampered_lines)
    assert tampered_root != original_root, (
        "changing one byte must change the Merkle root"
    )
    # التحقق بالجذر الأصلي على الأسطر المُعدّلة يجب أن يفشل
    assert verify_merkle_root(tampered_lines, original_root) is False


def test_merkle_root_odd_count():
    """عدد فردي من الأسطر — يُكرر الأخير (لا ينهار)."""
    lines = ['{"a": 1}', '{"b": 2}', '{"c": 3}']  # 3 أسطر (فردي)
    root = compute_merkle_root(lines)
    assert len(root) == 64  # sha256 hex


# ============================================================
# اختبارات LedgerAnchor (باستخدام ملفات مؤقتة معزولة)
# ============================================================

@pytest.fixture
def isolated_anchor():
    """يُنشئ LedgerAnchor مع ملفات مؤقتة معزولة (لا يُلمس data/ الحقيقي)."""
    tmp_dir = tempfile.mkdtemp(prefix="sovereign_anchor_test_")

    ledger_path = Path(tmp_dir) / "ledger.jsonl"
    anchors_path = Path(tmp_dir) / "ledger.anchors.jsonl"

    # إنشاء أحداث اختبارية
    events = []
    for i in range(10):
        events.append(json.dumps({
            "hash": f"hash_{i}",
            "prev_hash": f"hash_{i-1}" if i > 0 else "genesis",
            "blob": f"blob_{i}",
            "time": f"2026-10-14T00:00:{i:02d}Z",
            "type": "test_event",
            "signature": f"sig_{i}",
        }))
    ledger_path.write_text("\n".join(events) + "\n", encoding="utf-8")

    anchor = LedgerAnchor(ledger_path=ledger_path, anchors_path=anchors_path)
    return anchor, events


def test_anchor_batch_creates_anchor(isolated_anchor):
    """anchor_batch يُنشئ مرساة صحيحة لنطاق محدد."""
    anchor, events = isolated_anchor

    result = anchor.anchor_batch(
        batch_start=0,
        batch_end=9,
        key_id="test_key_id_12345",
        signature="test_anchor_signature",
        reason="TEST_BATCH",
    )

    assert result is not None, "anchor_batch must return an anchor record"
    assert result["batch_start"] == 0
    assert result["batch_end"] == 9
    assert result["event_count"] == 10
    assert result["merkle_root"].startswith("sha256:")
    assert result["key_id"] == "test_key_id_12345"
    assert result["reason"] == "TEST_BATCH"
    assert len(result["anchor_id"]) == 16


def test_verify_anchor_success(isolated_anchor):
    """التحقق من مرساة صحيحة ينجح (المحتوى لم يتغير)."""
    anchor, events = isolated_anchor

    # إنشاء مرساة
    anchor.anchor_batch(0, 9, "key1", "sig1", "TEST")

    # التحقق — يجب أن ينجح
    anchors_list = anchor.list_anchors()
    assert len(anchors_list) == 1
    ok, msg = anchor.verify_anchor(anchors_list[0])
    assert ok is True, f"verification must succeed: {msg}"


def test_verify_anchor_detects_tampering(isolated_anchor):
    """
    الجوهر (المرحلة 2): أي تعديل على أي حدث في النطاق المُرسى
    يُكشف فورًا (Merkle root يتغير).
    """
    anchor, events = isolated_anchor

    # إنشاء مرساة للنطاق [0, 9]
    anchor.anchor_batch(0, 9, "key1", "sig1", "TEST")
    anchors_list = anchor.list_anchors()
    original_anchor = anchors_list[0]

    # التحقق الأصلي ينجح
    ok_before, _ = anchor.verify_anchor(original_anchor)
    assert ok_before is True

    # التلاعب: تغيير حدث واحد (الحدث 5)
    lines = anchor.read_ledger_lines()
    tampered_event = json.loads(lines[5])
    tampered_event["hash"] = "TAMPERED_HASH"
    lines[5] = json.dumps(tampered_event, ensure_ascii=False)
    anchor.ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # التحقق بعد التلاعب يجب أن يفشل
    ok_after, msg = anchor.verify_anchor(original_anchor)
    assert ok_after is False, (
        "tampering must be detected (Merkle root changed)"
    )
    assert "mismatch" in msg.lower() or "modified" in msg.lower()


def test_verify_anchor_out_of_range(isolated_anchor):
    """مرساة بنطاق يتجاوز اليدجر تُعاد كفاشلة (وليس نجاحًا كاذبًا)."""
    anchor, events = isolated_anchor

    # محاولة إنشاء مرساة لنطاق غير صالح
    result = anchor.anchor_batch(0, 999, "key1", "sig1", "TEST")
    assert result is None, "out-of-range anchor must return None"

    # إنشاء مرساة صالحة ثم حذف أحداث (اختصار اليدجر)
    anchor.anchor_batch(0, 9, "key1", "sig1", "TEST")
    anchors_list = anchor.list_anchors()

    # تقصير اليدجر (إزالة أحداث) — النطاق لم يعد صالحًا
    lines = anchor.read_ledger_lines()
    anchor.ledger_path.write_text("\n".join(lines[:5]) + "\n", encoding="utf-8")

    ok, msg = anchor.verify_anchor(anchors_list[0])
    assert ok is False, "shortened ledger must fail verification"


def test_list_anchors(isolated_anchor):
    """list_anchors يُعيد كل المراسي المسجلة."""
    anchor, events = isolated_anchor

    # لا مراسي في البداية
    assert anchor.list_anchors() == []

    # إنشاء مرساة
    anchor.anchor_batch(0, 4, "key1", "sig1", "BATCH1")
    anchors = anchor.list_anchors()
    assert len(anchors) == 1

    # إنشاء مرساة ثانية (نطاق مختلف)
    anchor.anchor_batch(5, 9, "key1", "sig2", "BATCH2")
    anchors = anchor.list_anchors()
    assert len(anchors) == 2
    assert anchors[0]["reason"] == "BATCH1"
    assert anchors[1]["reason"] == "BATCH2"


def test_full_report(isolated_anchor):
    """full_report يُعيد تقريرًا شاملًا صحيحًا."""
    anchor, events = isolated_anchor

    # إنشاء مرساة تغطي كل الأحداث
    anchor.anchor_batch(0, 9, "key1", "sig1", "FULL_COVERAGE")

    report = anchor.full_report()
    assert report["total_events"] == 10
    assert report["total_anchors"] == 1
    assert report["anchored_events_count"] == 10
    assert report["anchored_coverage_pct"] == 100.0
    assert report["anchors_verified"] == 1
    assert report["anchors_failed"] == 0


# ============================================================
# اختبار المرساة الفعلية للبيانات الحقيقية (11,777 حدثًا)
# ============================================================

def test_anchor_real_ledger_data():
    """
    اختبار حقيقي: حساب Merkle root لكل الأحداث الفعلية في ledger.jsonl
    (11,777 حدثًا فاشلة التوقيع). يتحقق أن:
    1. الجذر يُحسب بنجاح
    2. الجذر حتمي (نفس النتيجة مرتين)
    3. التحقق ينجح (المحتوى لم يتغير)
    4. تعديل حدث واحد يُكشف
    """
    real_ledger = _REPO_ROOT / "data" / "sovereign_core" / "ledger.jsonl"
    if not real_ledger.exists():
        pytest.skip(f"real ledger not found: {real_ledger}")

    lines = []
    with open(real_ledger, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                lines.append(line)

    total = len(lines)
    assert total > 0, "real ledger must have events"

    # حساب الجذر مرتين (حتمية)
    root1 = compute_merkle_root(lines)
    root2 = compute_merkle_root(lines)
    assert root1 == root2, "Merkle root must be deterministic for real data"
    assert len(root1) == 64, "sha256 hex must be 64 chars"

    # التحقق ينجح
    assert verify_merkle_root(lines, root1) is True

    # تعديل حدث واحد (في نسخة) → يُكشف
    tampered = list(lines)
    tampered[0] = tampered[0] + "x"  # تغيير بايت واحد
    tampered_root = compute_merkle_root(tampered)
    assert tampered_root != root1, (
        "modifying one event in real ledger must change the root"
    )
