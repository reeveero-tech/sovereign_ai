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


def _head_commit_files(repo_root: Path = REPO_ROOT):
    out = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        capture_output=True, text=True, cwd=str(repo_root),
    )
    files = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    if not files:
        # R-806: في checkout من GitHub لحدث pull_request يكون HEAD التزامَ دمج
        # بسيطًا (نتيجة الدمج تساوي رأس الـPR) فلا يُظهر git show أي فروق
        # مركّبة — كان الحارس يفشل ظلمًا تحت مسار PR بينما يعمل تحت push
        # (أول PR على المستودع كشفه حيًا: push نجح وpull_request فشل على
        # الالتزام نفسه). في التزام الدمج يكون رأس الـPR هو الوالد الثاني
        # (HEAD^2) — وهو الالتزام الذي يحمل الكود والوثائق معًا كما تقتضي
        # D-040؛ تحديد الوالد بالتسلسل لا بالتاريخ (تساوي التواريخ يقلب
        # الترتيب). وإن لم يكن دمجًا فآخر التزام غير دمج قابل للوصول.
        parents = subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        target = ""
        if len(parents.stdout.split()) > 2:  # التزام دمج: الوالد الثاني = رأس الـPR
            target = "HEAD^2"
        else:
            non_merge = subprocess.run(
                ["git", "rev-list", "--no-merges", "-n", "1", "HEAD"],
                capture_output=True, text=True, cwd=str(repo_root),
            )
            target = non_merge.stdout.strip()
        if target:
            out = subprocess.run(
                ["git", "show", "--name-only", "--format=", target],
                capture_output=True, text=True, cwd=str(repo_root),
            )
            files = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    return files


def test_head_commit_files_survive_trivial_merge_head(tmp_path):
    """R-806 — حارس D-040 لا ينهار تحت التزام دمج بسيط (سيناريو checkout
    من GitHub لحدث pull_request: نتيجة الدمج = رأس الـPR فلا فروق مركّبة).
    الدليل الحي: أول PR على المستودع — تشغيل push على الالتزام نفسه نجح
    وتشغيل pull_request فشل برسالة «لا يمكن قراءة ملفات HEAD»."""
    import subprocess as sp

    repo = tmp_path / "prsim"
    repo.mkdir()
    run = lambda *a: sp.run(
        ["git", *a], capture_output=True, text=True, cwd=str(repo), check=True
    )
    run("init", "-q")
    run("config", "user.name", "guardian-test")
    run("config", "user.email", "guardian-test@example.com")
    (repo / "base.txt").write_text("base", encoding="utf-8")
    run("add", "-A")
    run("commit", "-q", "-m", "base")
    base_branch = sp.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True, cwd=str(repo), check=True,
    ).stdout.strip()
    run("checkout", "-q", "-b", "pr")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-q", "-m", "pr head: code + docs")
    run("checkout", "-q", base_branch)
    run("merge", "--no-ff", "--no-edit", "pr")
    # إثبات السيناريو: HEAD التزام دمج وgit show عليه فارغ (كما في CI)
    plain = sp.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        capture_output=True, text=True, cwd=str(repo),
    )
    assert not plain.stdout.strip(), "السيناريو مكسور: الدمج ليس بسيطًا"
    # الحارس يحل الاحتياط: أول التزام غير دمج = رأس الـPR
    assert _head_commit_files(repo) == ["code.py"]


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
