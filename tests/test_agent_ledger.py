"""
اختبارات سجل أفعال الوكيل (Agent Ledger) — المرحلة 6 من ROADMAP_V2

تتحقق من:
1. AgentLedger يُنشئ ملف السجل
2. record_action يُسجّل فعلًا صحيحًا
3. read_actions يُعيد الأفعال
4. get_stats يُعيد إحصائيات صحيحة
5. verify_integrity يتحقق من النزاهة
6. السجل إلحافي (لا حذف)
7. نقطة /agent/ledger تعمل
"""

import json
import tempfile
from pathlib import Path

import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from fastapi.testclient import TestClient

from backend.sovereign.agent_ledger import (
    AgentLedger,
    AgentAction,
    ACTION_TYPES,
)


@pytest.fixture
def isolated_ledger():
    """يُنشئ AgentLedger مع ملف مؤقت معزول (لا يُلمس data/ الحقيقي)."""
    tmp_dir = tempfile.mkdtemp(prefix="sovereign_agent_ledger_test_")
    ledger_path = Path(tmp_dir) / "agent_ledger.jsonl"

    ledger = AgentLedger(ledger_path=ledger_path)
    return ledger


# ============================================================
# اختبارات AgentLedger (باستخدام ملفات مؤقتة معزولة)
# ============================================================

def test_agent_ledger_creates_file(isolated_ledger):
    """AgentLedger يُنشئ ملف السجل إذا لم يوجد."""
    assert isolated_ledger.ledger_path.exists(), (
        "ledger file must be created"
    )


def test_record_action_creates_valid_action(isolated_ledger):
    """record_action يُسجّل فعلًا صحيحًا."""
    action = isolated_ledger.record_action(
        action_type="FEATURE_ADDED",
        description="Test feature",
        files_affected=["test.py"],
        tests_added=5,
        tests_passed=5,
        commit_hash="abc123",
    )

    assert action.action_id is not None
    assert len(action.action_id) == 16  # sha256 first 16 chars
    assert action.action_type == "FEATURE_ADDED"
    assert action.description == "Test feature"
    assert action.files_affected == ["test.py"]
    assert action.tests_added == 5
    assert action.tests_passed == 5
    assert action.commit_hash == "abc123"
    assert action.result == "success"
    assert action.timestamp > 0


def test_read_actions_returns_recorded(isolated_ledger):
    """read_actions يُعيد الأفعال المُسجّلة."""
    # تسجيل 3 أفعال
    for i in range(3):
        isolated_ledger.record_action(
            action_type="FILE_CREATED",
            description=f"Test file {i}",
            files_affected=[f"file_{i}.py"],
        )

    actions = isolated_ledger.read_actions()
    assert len(actions) == 3

    # ترتيب زمني
    timestamps = [a.timestamp for a in actions]
    assert timestamps == sorted(timestamps), "actions must be sorted by time"


def test_get_stats_correct(isolated_ledger):
    """get_stats يُعيد إحصائيات صحيحة."""
    # تسجيل أفعال متنوعة
    isolated_ledger.record_action(
        action_type="FEATURE_ADDED",
        description="Feature 1",
        files_affected=["a.py", "b.py"],
        tests_added=3,
        tests_passed=3,
        commit_hash="hash1",
    )
    isolated_ledger.record_action(
        action_type="BUG_FIXED",
        description="Bug 1",
        files_affected=["c.py"],
        tests_added=2,
        tests_passed=2,
    )
    isolated_ledger.record_action(
        action_type="TEST_ADDED",
        description="Test 1",
        files_affected=["test_x.py"],
        tests_added=1,
        tests_passed=1,
    )

    stats = isolated_ledger.get_stats()

    assert stats["total_actions"] == 3
    assert stats["by_type"]["FEATURE_ADDED"] == 1
    assert stats["by_type"]["BUG_FIXED"] == 1
    assert stats["by_type"]["TEST_ADDED"] == 1
    assert stats["total_files_affected"] == 4  # 2+1+1
    assert stats["total_tests_added"] == 6  # 3+2+1
    assert stats["total_tests_passed"] == 6
    assert stats["total_commits"] == 1  # فقط hash1


def test_verify_integrity_valid(isolated_ledger):
    """verify_integrity ينجح للسجل السليم."""
    isolated_ledger.record_action(
        action_type="FEATURE_ADDED",
        description="Valid action",
    )

    result = isolated_ledger.verify_integrity()
    assert result["valid"] is True
    assert result["total_lines"] == 1
    assert result["unique_ids"] == 1
    assert len(result["issues"]) == 0


def test_append_only_never_deletes(isolated_ledger):
    """
    القاعدة الصارمة: السجل إلحافي — لا يُحذف منه سطر أبدًا.
    تسجيل فعل جديد لا يُحذف الأفعال السابقة.
    """
    # تسجيل 5 أفعال
    for i in range(5):
        isolated_ledger.record_action(
            action_type="FILE_CREATED",
            description=f"Action {i}",
        )

    # قراءة عدد الأسطر
    content1 = isolated_ledger.ledger_path.read_text(encoding="utf-8")
    lines1 = [l for l in content1.split("\n") if l.strip()]
    assert len(lines1) == 5

    # تسجيل فعل جديد (سادس)
    isolated_ledger.record_action(
        action_type="FILE_CREATED",
        description="Action 5",
    )

    # التحقق أن عدد الأسطر زاد (لم يُحذف شيء)
    content2 = isolated_ledger.ledger_path.read_text(encoding="utf-8")
    lines2 = [l for l in content2.split("\n") if l.strip()]
    assert len(lines2) == 6, (
        f"append-only violated: expected 6 lines, got {len(lines2)}"
    )


def test_action_types_valid():
    """ACTION_TYPES تحتوي الأنواع المطلوبة."""
    required_types = [
        "FILE_CREATED",
        "FILE_MODIFIED",
        "TEST_ADDED",
        "COMMIT_CREATED",
        "FEATURE_ADDED",
        "BUG_FIXED",
    ]
    for rt in required_types:
        assert rt in ACTION_TYPES, f"missing action type: {rt}"


def test_unknown_action_type_becomes_other(isolated_ledger):
    """نوع فعل غير معروف يُحوّل إلى OTHER (لا يفشل)."""
    action = isolated_ledger.record_action(
        action_type="UNKNOWN_TYPE_XYZ",
        description="Unknown type test",
    )

    assert action.action_type == "OTHER"


def test_get_actions_by_type(isolated_ledger):
    """get_actions_by_type يُعيد أفعال نوع معين فقط."""
    isolated_ledger.record_action(action_type="FEATURE_ADDED", description="F1")
    isolated_ledger.record_action(action_type="BUG_FIXED", description="B1")
    isolated_ledger.record_action(action_type="FEATURE_ADDED", description="F2")

    features = isolated_ledger.get_actions_by_type("FEATURE_ADDED")
    bugs = isolated_ledger.get_actions_by_type("BUG_FIXED")

    assert len(features) == 2
    assert len(bugs) == 1
    assert all(a.action_type == "FEATURE_ADDED" for a in features)


def test_get_recent_actions(isolated_ledger):
    """get_recent_actions يُعيد آخر N فعل."""
    for i in range(10):
        isolated_ledger.record_action(
            action_type="FILE_CREATED",
            description=f"Action {i}",
        )

    recent = isolated_ledger.get_recent_actions(limit=3)
    assert len(recent) == 3

    # آخر 3 أفعال (7, 8, 9)
    descriptions = [a.description for a in recent]
    assert descriptions == ["Action 7", "Action 8", "Action 9"]


# ============================================================
# اختبارات نقطة النهاية /agent/ledger
# ============================================================

@pytest.fixture(scope="module")
def client():
    from app import app
    with TestClient(app) as c:
        yield c


def test_agent_ledger_endpoint_exists(client):
    """/agent/ledger موجود ويعمل (200)."""
    r = client.get("/agent/ledger")
    assert r.status_code == 200, f"failed: {r.status_code} {r.text[:200]}"


def test_agent_ledger_endpoint_returns_report(client):
    """/agent/ledger يُعيد تقريرًا كاملًا."""
    r = client.get("/agent/ledger")
    assert r.status_code == 200

    data = r.json()
    assert "stats" in data
    assert "integrity" in data
    assert "recent_actions" in data
    assert "ledger_path" in data


def test_agent_ledger_endpoint_stats(client):
    """إحصائيات السجل صحيحة (total_actions > 0)."""
    r = client.get("/agent/ledger")
    assert r.status_code == 200

    data = r.json()
    stats = data["stats"]

    # السجل يجب أن يحتوي أفعالًا (سجلنا 6 أفعال)
    assert stats["total_actions"] > 0, (
        "agent ledger must have recorded actions"
    )
    assert "by_type" in stats
    assert "total_tests_added" in stats
