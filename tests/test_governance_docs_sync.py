"""D-040 (R-722 — القاعدة الحاكمة بأمر المالك 2026-10-22): لا يُدفع عمل في
المستودع إلا بتحديث حالة المشروع ووثائقه وخارطة طريقه في نفس الالتزام —
لا في دفعة منفصلة.

الفرض: بوابة CI ترفض أي التزام يغيّر كودًا (backend/frontend/tools/tests/
التكوين) دون أن يغيّر وثائق المشروع (docs/ أو forensics/) في نفس الالتزام.
"""


import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# مسارات الكود (تغييرها «عمل» يستوجب توثيقًا)
_CODE_PREFIXES = (
    "backend/", "frontend/", "tools/", "tests/", ".github/",
    "fly.toml", "verify.sh", "requirements.txt", "pytest.ini",
)
# مسارات التوثيق (وجودها في الالتزام يبرر العمل)
_DOC_PREFIXES = ("docs/", "forensics/")


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
    """الالتزام الحالي يطيع القاعدة: أي كود مُغيَّر يقابله تحديث وثائق في
    نفس الالتزام (حارس انحدار لكل الالتزامات المستقبلية على مستوى HEAD)."""
    files = _head_commit_files()
    assert files, "لا يمكن قراءة ملفات HEAD — خلل في تنفيذ الحارس"
    code_files = [f for f in files if f.startswith(_CODE_PREFIXES)]
    doc_files = [f for f in files if f.startswith(_DOC_PREFIXES)]
    if code_files:
        assert doc_files, (
            f"D-040: الالتزام يغيّر كودًا ({code_files[:3]}...) بلا تحديث "
            "للوثائق في نفس الالتزام — القاعدة الحاكمة بأمر المالك"
        )
