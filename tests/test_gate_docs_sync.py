# -*- coding: utf-8 -*-
"""R-748 (بأمر المالك 2026-10-24 — «القاعدة الحاكمة»): اختبار سلوكي لحارس
D-040 المقوى. القاعدة الحرفية للمالك: «لا دفع إلى المستودع ولا عمل فيه إلا
بتوثيق … تحدث خارطة الطريق وحالة المشروع ووثائقه بما تم عمله … معه في نفس
الدفعة لا بعدها».

الحارس القديم كان يقبل أي ملف تحت docs/ أو forensics/ — حتى لو لم تُحدَّث
خارطة الطريق ولا حالة المشروع ولا سجل التغييرات. هذا الاختبار يفرض المعنى
الحرفي: تغيير كود ⇒ في نفس الالتزام تحديث docs/PROJECT_STATE.md و
docs/CHANGELOG.md وخارطة الطريق النشطة (docs/ROADMAP*.md).

الاختبار سلوكي من الطرفين: مستودع git مؤقت حقيقي يُبنى في /tmp (خارج الشجرة
— نمط البيئة الموثق)، ثم يُستدعى الحارس tools/gate_docs_sync.py كعملية مستقلة
(كما تستدعيه CI والـ pre-commit) وتُفحص رموز الخروج.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / "tools" / "gate_docs_sync.py"

# نفس بادئات «الكود» المعتمدة في بوابة CI (اتحاد قائمتي الدفع والـ PR)
CODE_PREFIXES = (
    "backend/", "frontend/", "tools/", "tests/", ".github/", "nexus/",
    "guardian/", "main.py", "start.sh", "Dockerfile",
    "fly.toml", "verify.sh", "requirements.txt", "pytest.ini",
)


def _run_gate(cwd: str, *args: str) -> subprocess.CompletedProcess:
    """استدعاء الحارس كما تستدعيه CI — عملية مستقلة، لا استيراد مباشر."""
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        capture_output=True, text=True, cwd=cwd,
    )


def _commit_all(repo: Path, msg: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=repo, check=True)


def _make_repo() -> Path:
    repo = Path(tempfile.mkdtemp(prefix="gate_docs_sync_"))
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    # هوية محلية للمستودع المؤقت — لا حاجة لأي هوية خارجية
    subprocess.run(
        ["git", "config", "user.name", "gate-tester"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "gate-tester@example.invalid"],
        cwd=repo, check=True)
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _commit_all(repo, "init")
    return repo


def _write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


DOCS_OK = {
    "docs/PROJECT_STATE.md": "الحالة محدثة\n",
    "docs/CHANGELOG.md": "مدخل جديد\n",
    "docs/ROADMAP_V5.md": "خارطة محدثة\n",
}


def test_gate_file_exists():
    """الحارس موجود في tools/ (تسلسل البناء: الالتزام الذري يدفعه مع اختباره)."""
    assert GATE.is_file(), f"الحارس مفقود: {GATE}"


def test_code_with_all_three_docs_passes(tmp_repo=None):
    repo = _make_repo()
    try:
        _write(repo, "backend/app.py", "x = 1\n")
        for rel, text in DOCS_OK.items():
            _write(repo, rel, text)
        _commit_all(repo, "code + full docs")
        r = _run_gate(str(repo), "HEAD")
        assert r.returncode == 0, r.stderr
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_code_with_unrelated_doc_only_fails():
    """كود + ملف docs/ غير مطلوب لا يكفي — القاعدة الحرفية للمالك."""
    repo = _make_repo()
    try:
        _write(repo, "backend/app.py", "x = 1\n")
        _write(repo, "docs/API.md", "توثيق عام\n")
        _commit_all(repo, "code + unrelated doc")
        r = _run_gate(str(repo), "HEAD")
        assert r.returncode == 1
        # الرسالة تسمي كل مفقود — لا رسالة غامضة
        assert "docs/PROJECT_STATE.md" in (r.stdout + r.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_code_missing_changelog_fails():
    repo = _make_repo()
    try:
        _write(repo, "tests/test_x.py", "def test_x(): pass\n")
        _write(repo, "docs/PROJECT_STATE.md", "حالة\n")
        _write(repo, "docs/ROADMAP_V5.md", "خارطة\n")
        _commit_all(repo, "code + state + roadmap, no changelog")
        r = _run_gate(str(repo), "HEAD")
        assert r.returncode == 1
        assert "docs/CHANGELOG.md" in (r.stdout + r.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_code_missing_roadmap_fails():
    repo = _make_repo()
    try:
        _write(repo, "tools/x.py", "pass\n")
        _write(repo, "docs/PROJECT_STATE.md", "حالة\n")
        _write(repo, "docs/CHANGELOG.md", "سجل\n")
        _commit_all(repo, "code + state + changelog, no roadmap")
        r = _run_gate(str(repo), "HEAD")
        assert r.returncode == 1
        assert "ROADMAP" in (r.stdout + r.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_docs_only_change_passes():
    """دفعة وثائق بلا كود — مسموحة (نمط مداخل «تسليم» القائمة)."""
    repo = _make_repo()
    try:
        for rel, text in DOCS_OK.items():
            _write(repo, rel, text)
        _commit_all(repo, "docs only")
        r = _run_gate(str(repo), "HEAD")
        assert r.returncode == 0, r.stderr
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_staged_mode_rejects_code_without_docs():
    """وضع pre-commit: الفهرس (ما سيُلتزم) يُفحص قبل إنشاء الالتزام."""
    repo = _make_repo()
    try:
        _write(repo, "backend/app.py", "x = 1\n")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        r = _run_gate(str(repo), "--staged")
        assert r.returncode == 1
        assert "docs/PROJECT_STATE.md" in (r.stdout + r.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_staged_mode_passes_with_full_docs():
    repo = _make_repo()
    try:
        _write(repo, "backend/app.py", "x = 1\n")
        for rel, text in DOCS_OK.items():
            _write(repo, rel, text)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        r = _run_gate(str(repo), "--staged")
        assert r.returncode == 0, r.stderr
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_merge_commit_skipped():
    """الالتزامات الدمجية تُفحص بمعايير خاصة عند وقوعها — نفس سلوك البوابة القائمة."""
    repo = _make_repo()
    try:
        _write(repo, "backend/app.py", "x = 1\n")
        _commit_all(repo, "code on main")
        subprocess.run(["git", "checkout", "-q", "-b", "side"], cwd=repo, check=True)
        _write(repo, "backend/other.py", "y = 2\n")
        _commit_all(repo, "code on side")
        subprocess.run(["git", "checkout", "-q", "main"], cwd=repo, check=True)
        # تقدم على main نفسه كي لا يكون الدمج fast-forward — التزام دمجي حقيقي
        _write(repo, "backend/main_side.py", "z = 3\n")
        _commit_all(repo, "code on main")
        subprocess.run(
            ["git", "merge", "-q", "--no-edit", "side"], cwd=repo, check=True)
        r = _run_gate(str(repo), "HEAD")
        assert r.returncode == 0, r.stderr
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_ci_and_hook_call_the_gate():
    """التطبيق الواحد: ci.yml (دفعًا وPR) وpre-commit يستدعيان الحارس نفسه."""
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    hook = (REPO_ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    # الخطوة تحتفظ بالاسم الحرفي الذي يفحصه اختبار test_governance_docs_sync
    assert "reject code changes without docs update in the same commit" in ci
    assert "tools/gate_docs_sync.py" in ci
    assert "tools/gate_docs_sync.py" in hook
