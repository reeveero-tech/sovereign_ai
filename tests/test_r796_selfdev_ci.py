"""R-796: منفّذ CI للتطوير الذاتي — RED→GREEN حقيقي على مستودع git مؤقت.

يثبت: الاختبار يُشغَّل فعلًا على الكود الأصلي ويجب أن يفشل، ثم ينجح بعد التعديل؛
الوثائق وتدقيق الحذف في نفس الالتزام وتجتاز البوابتين الحقيقيتين؛ مسودة لا تثبت العيب
أو ملف تغيّر ⇒ نتيجة حمراء/قديمة بسبب حرفي؛ لا دفع إلى main أبدًا؛ الترقية تُرصد فقط.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from tools import selfdev_ci  # noqa: E402

ORIGINAL = "def add(a, b):\n    return a - b\n"
GOOD = {"file": "backend/calc.py", "summary": "إصلاح الجمع", "search": "    return a - b\n",
        "replace": "    return a + b\n", "test_name": "test_add",
        "test_code": "import calc\n\ndef test_add():\n    assert calc.add(2, 3) == 5\n"}


def _g(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    (r / "backend").mkdir(parents=True)
    (r / "tools").mkdir()
    (r / "docs").mkdir()
    (r / "forensics").mkdir()
    (r / "backend" / "calc.py").write_text(ORIGINAL, encoding="utf-8")
    for f in ("gate_deletions.py", "gate_docs_sync.py"):
        shutil.copy(REPO_ROOT / "tools" / f, r / "tools" / f)
    (r / "docs" / "CHANGELOG.md").write_text("# CHANGELOG\n\n---\n## [R-1] قديم\n", encoding="utf-8")
    (r / "docs" / "PROJECT_STATE.md").write_text("# الحالة\n", encoding="utf-8")
    (r / "docs" / "ROADMAP_V6.md").write_text("# V6\n", encoding="utf-8")
    (r / "docs" / "ROADMAP_ACTIVE.txt").write_text("docs/ROADMAP_V6.md\n", encoding="utf-8")
    (r / "forensics" / "DELETED_LINES_AUDIT.md").write_text("# audit\n", encoding="utf-8")
    _g(r, "init", "-q", "-b", "main")
    _g(r, "config", "user.name", "t")
    _g(r, "config", "user.email", "t@example.com")
    _g(r, "config", "commit.gpgsign", "false")
    _g(r, "add", "-A")
    _g(r, "commit", "-q", "-m", "base")
    return r


def _task(draft=GOOD, attempts=1, tid="SD-abcd1234"):
    return {"id": tid, "source": "owner", "ref": None, "title": "add يطرح",
            "status": "drafted", "attempts": attempts, "draft": dict(draft), "updated_at": 1}


class FakeDisk:
    def __init__(self):
        self.rows = []

    def append_log(self, ns, payload):
        self.rows.append({"id": len(self.rows) + 1, "namespace": ns,
                          "payload": json.loads(json.dumps(payload))})
        return True

    def pull_log(self, ns, since_id=0, limit=1000):
        return [r for r in self.rows if r["namespace"] == ns and r["id"] > since_id][:limit]


def test_green_path_red_first_then_green_with_docs_and_audit(repo):
    res = selfdev_ci.process(_task(), repo, base="main", run_suite=False, push=False,
                             today="2026-10-28")
    assert res["result"] == "green", res
    assert res["red_rc"] != 0 and res["green_rc"] == 0
    assert res["branch"] == "work/selfdev-abcd1234-a1"
    files = _g(repo, "show", "--name-only", "--format=", "HEAD").splitlines()
    for f in ("backend/calc.py", "tests/selfdev/test_selfdev_abcd1234_a1.py",
              "docs/CHANGELOG.md", "docs/PROJECT_STATE.md", "docs/ROADMAP_V6.md",
              "forensics/DELETED_LINES_AUDIT.md"):
        assert f in files, f
    assert "return a + b" in (repo / "backend" / "calc.py").read_text(encoding="utf-8")
    audit = (repo / "forensics" / "DELETED_LINES_AUDIT.md").read_text(encoding="utf-8")
    assert "# DELETION-JUSTIFIED" in audit and "return a - b" in audit
    assert "# DELETION-JUSTIFIED" in _g(repo, "log", "-1", "--format=%B")
    ch = (repo / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert ch.index("SD-abcd1234 a1") < ch.index("[R-1]"), "المدخل ليس الأحدث"
    assert _g(repo, "rev-parse", "main") != res["sha"], "المنفّذ لمس main"


def test_test_passing_on_original_is_rejected_not_red_first(repo):
    d = dict(GOOD, test_code="import calc\n\ndef test_add():\n    assert calc.add(3, 0) == 3\n")
    res = selfdev_ci.process(_task(d), repo, base="main", run_suite=False)
    assert res["result"] == "red" and res["reason"].startswith("not_red_first")
    assert res["red_rc"] == 0


def test_fix_that_does_not_make_test_green_is_red(repo):
    d = dict(GOOD, replace="    return a * b\n")
    res = selfdev_ci.process(_task(d), repo, base="main", run_suite=False)
    assert res["result"] == "red" and res["reason"] == "not_green_after_fix"
    assert "log_tail" in res and res["log_tail"]


def test_stale_when_file_changed_since_draft(repo):
    d = dict(GOOD, search="    return a / b\n")
    res = selfdev_ci.process(_task(d), repo, base="main", run_suite=False)
    assert res["result"] == "stale"


def test_cycle_processes_once_and_detects_promotion(repo):
    disk = FakeDisk()
    disk.append_log("selfdev", {"kind": "task", "task": _task()})
    rep = selfdev_ci.run_cycle(disk, repo, base="main", run_suite=False, push=False)
    assert [p["result"] for p in rep["processed"]] == ["green"], rep
    rep2 = selfdev_ci.run_cycle(disk, repo, base="main", run_suite=False, push=False)
    assert rep2["processed"] == [], "نفس المحاولة اختُبرت مرتين"
    assert rep2["promoted"] == []
    sha = rep["processed"][0]["sha"]
    _g(repo, "checkout", "-q", "main")
    _g(repo, "merge", "-q", "--ff-only", sha)  # ترقية المالك (محاكاة)
    rep3 = selfdev_ci.run_cycle(disk, repo, base="main", run_suite=False, push=False)
    assert rep3["promoted"] == ["SD-abcd1234"]
    ci = [r["payload"] for r in disk.rows if r["namespace"] == "selfdev_ci"]
    assert ci[-1]["result"] == "promoted" and ci[-1]["sha"] == sha


def test_runner_never_pushes_main():
    src = (REPO_ROOT / "tools" / "selfdev_ci.py").read_text(encoding="utf-8")
    wf = (REPO_ROOT / ".github" / "workflows" / "self-develop.yml").read_text(encoding="utf-8")
    assert ":main" not in src and "HEAD:main" not in wf and "push origin main" not in wf
    assert '"push", "-q", "origin", f"{br}:{br}"' in src
    assert "work/selfdev-" in src
