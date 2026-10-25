# -*- coding: utf-8 -*-
"""R-751 (ROADMAP_V5 ١.١-ب — بأمر المالك 2026-10-25 «ابدأ وفق الخارطة»):
اختبار سلوكي لبوابة الحذف الموحدة (قرار المالك Issue #8: أي التزام يحذف
سطرًا بلا `# DELETION-JUSTIFIED` في نفس الالتزام يُرفض).

الفجوة المكتشفة 2026-10-25: البوابة كانت bash مضمنًا في CI يفحص رأس الدفعة
وحده (التزام حاذف بلا علامة يتبعه التزام بها يمر)، وحارس المحلي لا يطبقها.
هنا: أداة موحدة tools/gate_deletions.py بأوضاع SHA و--range و--staged
(hook commit-msg)، وقائمة «تبرير متأخر» صريحة مشروطة بمدخل تدقيق.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / "tools" / "gate_deletions.py"
MARK = "# DELETION-JUSTIFIED"


def _run(cwd, *args):
    return subprocess.run([sys.executable, str(GATE), *args],
                          capture_output=True, text=True, cwd=cwd)


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()


def _repo():
    repo = Path(tempfile.mkdtemp(prefix="gate_del_"))
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "user.email", "t@example.invalid")
    (repo / "a.txt").write_text("1\n2\n3\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


def _commit(repo, content, msg, rel="a.txt"):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def test_gate_exists():
    assert GATE.is_file()


def test_deletion_without_marker_rejected():
    repo = _repo()
    try:
        sha = _commit(repo, "1\n", "حذف بلا علامة")
        assert _run(str(repo), sha).returncode == 1
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_deletion_with_marker_in_message_passes():
    repo = _repo()
    try:
        sha = _commit(repo, "1\n", f"حذف\n\n{MARK} — سبب")
        r = _run(str(repo), sha)
        assert r.returncode == 0, r.stdout + r.stderr
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_marker_in_diff_content_passes():
    repo = _repo()
    try:
        _commit(repo, "1\n", "x", rel="b.txt")
        (repo / "a.txt").write_text("1\n", encoding="utf-8")
        (repo / "audit.md").write_text(f"{MARK} سبب\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "حذف مع مدخل تدقيق")
        sha = _git(repo, "rev-parse", "HEAD")
        assert _run(str(repo), sha).returncode == 0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_additions_only_pass():
    repo = _repo()
    try:
        sha = _commit(repo, "1\n2\n3\n4\n", "إضافة")
        assert _run(str(repo), sha).returncode == 0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_range_hides_unjustified_commit_rejected():
    """الفجوة نفسها: التزام حاذف بلا علامة يتبعه التزام بعلامة — يُرفض."""
    repo = _repo()
    try:
        base = _git(repo, "rev-parse", "HEAD")
        _commit(repo, "1\n2\n", "حذف بلا علامة")
        head = _commit(repo, "1\n", f"حذف مبرر\n\n{MARK} سبب")
        assert _run(str(repo), head).returncode == 0  # الرأس وحده يمر
        r = _run(str(repo), "--range", base, head)
        assert r.returncode == 1, r.stdout
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_range_all_compliant_passes():
    repo = _repo()
    try:
        base = _git(repo, "rev-parse", "HEAD")
        _commit(repo, "1\n2\n", f"a\n\n{MARK} x")
        head = _commit(repo, "1\n2\n9\n", "إضافة")
        assert _run(str(repo), "--range", base, head).returncode == 0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_staged_mode_with_message_file():
    """hook commit-msg: الحذف في الفهرس + رسالة بلا علامة → رفض قبل الإنشاء."""
    repo = _repo()
    try:
        (repo / "a.txt").write_text("1\n", encoding="utf-8")
        _git(repo, "add", "-A")
        msg = repo / ".msg"
        msg.write_text("حذف بلا علامة\n", encoding="utf-8")
        assert _run(str(repo), "--staged", str(msg)).returncode == 1
        msg.write_text(f"حذف\n\n{MARK} سبب\n", encoding="utf-8")
        assert _run(str(repo), "--staged", str(msg)).returncode == 0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_late_justified_requires_audit_entry():
    """قائمة التبرير المتأخر لا تُعفي إلا التزامًا له مدخل في سجل التدقيق."""
    repo = _repo()
    try:
        sha = _commit(repo, "1\n", "حذف بلا علامة")
        lj = repo / "forensics" / "DELETION_LATE_JUSTIFIED.txt"
        lj.parent.mkdir(parents=True, exist_ok=True)
        lj.write_text(f"{sha} تبرير متأخر\n", encoding="utf-8")
        audit = repo / "forensics" / "DELETED_LINES_AUDIT.md"
        audit.write_text("لا مدخل\n", encoding="utf-8")
        assert _run(str(repo), sha).returncode == 1  # بلا مدخل تدقيق
        audit.write_text(f"# سجل\n\n## {sha[:7]} — مدخل متأخر\n- {MARK} سبب\n", encoding="utf-8")
        r = _run(str(repo), sha)
        assert r.returncode == 0, r.stdout + r.stderr
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_merge_commit_skipped():
    repo = _repo()
    try:
        _git(repo, "checkout", "-q", "-b", "side")
        _commit(repo, "1\n2\n3\nside\n", "side")
        _git(repo, "checkout", "-q", "main")
        _commit(repo, "1\n2\n3\n", "m", rel="c.txt")
        _git(repo, "merge", "-q", "--no-edit", "side")
        sha = _git(repo, "rev-parse", "HEAD")
        assert _run(str(repo), sha).returncode == 0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_ci_and_commit_msg_hook_call_the_gate():
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "tools/gate_deletions.py --range" in ci
    hook = REPO_ROOT / ".githooks" / "commit-msg"
    assert hook.is_file()
    assert "gate_deletions.py" in hook.read_text(encoding="utf-8")
