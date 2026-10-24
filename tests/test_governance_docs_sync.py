"""D-040 (R-722 — القاعدة الحاكمة بأمر المالك 2026-10-22؛ تعزيز R-748
بأمر المالك 2026-10-24 «القاعدة الحاكمة»): لا يُدفع عمل في المستودع إلا
بتحديث حالة المشروع وسجل تغييراته وخارطة طريقه النشطة في نفس الالتزام —
لا في دفعة منفصلة.

الفرض: بوابة CI ترفض أي التزام يغيّر كودًا (backend/frontend/tools/tests/
التكوين) دون أن يغيّر الثلاثة الحرفية: docs/PROJECT_STATE.md و
docs/CHANGELOG.md وdocs/ROADMAP*.md — في نفس الالتزام. (التنفيذ الموحد:
tools/gate_docs_sync.py واختباره السلوكي tests/test_gate_docs_sync.py.)
"""


import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# مسارات الكود (تغييرها «عمل» يستوجب توثيقًا)
_CODE_PREFIXES = (
    "backend/", "frontend/", "tools/", "tests/", ".github/", "nexus/",
    "guardian/", "main.py", "start.sh", "Dockerfile",
    "fly.toml", "verify.sh", "requirements.txt", "pytest.ini",
)
# الوثائق الثلاثة المطلوبة حرفيًا بأمر المالك (R-748 — المعنى المقوى)
_REQUIRED_DOCS = ("docs/PROJECT_STATE.md", "docs/CHANGELOG.md")
_ROADMAP_GLOB = "docs/ROADMAP*.md"


def _head_commit_files():
    out = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def test_ci_enforces_docs_sync_with_code_changes():
    """بوابة CI يجب أن تحتوي فحص D-040 — تغيير كود بلا وثائق في نفس
    الالتزام يُرفض (لا دفعة منفصلة)."""
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "reject code changes without docs update in the same commit" in text, (
        "بوابة D-040 مفقودة من ci.yml — القاعدة الحاكمة غير مفروضة"
    )


def test_head_commit_follows_docs_sync_rule():
    """الالتزام الحالي يطيع القاعدة الحرفية (R-748): أي كود مُغيَّر يقابله
    تحديث الثلاثة — الحالة والسجل والخارطة — في نفس الالتزام (حارس انحدار
    لكل الالتزامات المستقبلية على مستوى HEAD)."""
    import fnmatch

    files = _head_commit_files()
    assert files, "لا يمكن قراءة ملفات HEAD — خلل في تنفيذ الحارس"
    code_files = [f for f in files if f.startswith(_CODE_PREFIXES)]
    if code_files:
        missing = [d for d in _REQUIRED_DOCS if d not in files]
        if not [f for f in files if fnmatch.fnmatch(f, _ROADMAP_GLOB)]:
            missing.append(_ROADMAP_GLOB)
        assert not missing, (
            f"D-040 (R-748): الالتزام يغيّر كودًا ({code_files[:3]}...) دون "
            f"تحديث المطلوب حرفيًا في نفس الالتزام: {missing} — القاعدة "
            "الحاكمة بأمر المالك"
        )
