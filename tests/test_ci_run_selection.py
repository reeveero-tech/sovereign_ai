"""
R-682 — اختبار حتمي لمنطق اختيار تشغيل CI المرجعي (tests/ci_run_selection.py).

الحالة الحرجة المطلوبة صراحة (أمر المستشار): ثلاثة تشغيلات على SHA واحد —
1) المرجعي push (مكتمل/ناجح)، 2) operational (مكتمل/ناجح)، 3) verify-full
نفسه (قيد التنفيذ) — الاختيار يجب أن يقع على (1) افتراضيًا، وعلى المحدد
صراحة عند تحديده، ولا يقع أبدًا على قيد التنفيذ عند اشتراط الاكتمال.
"""
import json

import pytest

from ci_run_selection import select_ci_run

SHA = "a" * 40


def _three_runs_same_sha():
    """ثلاثة تشغيلات على SHA واحد: push ناجح، operational ناجح، verify قيد التنفيذ."""
    return [
        {"databaseId": 3003, "headSha": SHA, "status": "completed", "conclusion": "success",
         "event": "workflow_dispatch", "workflowName": "CI — Quality Gates (M4)"},  # verify-full نفسه
        {"databaseId": 3002, "headSha": SHA, "status": "completed", "conclusion": "success",
         "event": "workflow_dispatch", "workflowName": "CI — Quality Gates (M4)"},  # operational
        {"databaseId": 3001, "headSha": SHA, "status": "completed", "conclusion": "success",
         "event": "push", "workflowName": "CI — Quality Gates (M4)"},  # المرجعي
    ]


def test_default_prefers_push_run_not_dispatch_runs():
    run_id, run = select_ci_run(_three_runs_same_sha(), SHA)
    assert run_id == 3001
    assert run["event"] == "push"


def test_explicit_selection_wins_and_is_not_self_selection():
    # اختيار صريح للتشغيل المرجعي — لا يقع الاختيار على قيد التنفيذ
    run_id, _ = select_ci_run(_three_runs_same_sha(), SHA, explicit_run_id="3001")
    assert run_id == 3001


def test_explicit_mismatched_sha_rejected():
    other = {"databaseId": 3001, "headSha": "b" * 40, "status": "completed",
             "conclusion": "success", "event": "push", "workflowName": "CI — Quality Gates (M4)"}
    with pytest.raises(ValueError, match="لا يطابق HEAD SHA"):
        select_ci_run([other], SHA, explicit_run_id="3001")


def test_explicit_unknown_run_rejected():
    with pytest.raises(ValueError, match="غير موجود"):
        select_ci_run(_three_runs_same_sha(), SHA, explicit_run_id="9999")


def test_require_completed_rejects_in_progress_reference():
    runs = _three_runs_same_sha()
    # حتى لو كان المفضل push — قيد التنفيذ يُرفض عند اشتراط الاكتمال
    runs[2]["status"] = "in_progress"
    runs[2]["conclusion"] = None
    with pytest.raises(ValueError, match="غير مكتمل"):
        select_ci_run(runs, SHA, require_completed=True)


def test_foreign_workflow_rejected():
    runs = [{"databaseId": 4001, "headSha": SHA, "status": "completed",
             "conclusion": "success", "event": "push", "workflowName": "Some Other Workflow"}]
    with pytest.raises(ValueError, match="ليس من workflow ci.yml"):
        select_ci_run(runs, SHA)


def test_no_run_for_sha_rejected():
    with pytest.raises(ValueError, match="لا يوجد أي تشغيل CI"):
        select_ci_run(_three_runs_same_sha(), "c" * 40)


def test_cli_roundtrip():
    """verify.sh يستدعيها كأمر — اختبار السلوك من الطرفين (stdin/json → stdout)."""
    import os
    import subprocess
    import sys

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "tests/ci_run_selection.py", "--sha", SHA, "--require-completed"],
        input=json.dumps(_three_runs_same_sha()),
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3001"


def test_cli_rejects_self_selection():
    """حالة الخطأ الحقيقية من أول تشغيل verify-full: الاختيار الذاتي يُرفض."""
    import os
    import subprocess
    import sys

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runs = _three_runs_same_sha()
    # التشغيل 3003 قيد التنفيذ (verify-full نفسه) — تحديده صراحة مع اشتراط
    # الاكتمال يُرفض، ولا يقع عليه الاختيار الافتراضي أصلًا (ليس push)
    runs[0]["status"] = "in_progress"
    runs[0]["conclusion"] = None
    result = subprocess.run(
        [sys.executable, "tests/ci_run_selection.py", "--sha", SHA,
         "--explicit", "3003", "--require-completed"],
        input=json.dumps(runs),
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 1
    assert "غير مكتمل" in result.stderr
