"""R-797: الترقية الآلية لفروع التطوير الذاتي الخضراء (قرار المالك 2026-10-28).

يثبت على مستودع git حقيقي مؤقت مع remote عارٍ:
- فرع أخضر + CI أخضر على نفس البصمة ⇒ main يتقدم سريعًا إلى البصمة نفسها ⇒ نشر.
- CI أحمر ⇒ لا دفع؛ main تقدّم ⇒ stale بلا دفع؛ قاطع الدائرة بعد نشر فاشل ⇒ لا دفع.
- الترقية معطلة افتراضيًا (بلا SELFDEV_AUTO_PROMOTE='1').
- بوابة النشر تقبل CI بحدث push أو workflow_dispatch على نفس SHA ويبقى النشر يدويًا.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from tools import selfdev_ci  # noqa: E402
import self_develop as sd  # noqa: E402

ORIGINAL = "def add(a, b):\n    return a - b\n"
GOOD = {"file": "backend/calc.py", "summary": "إصلاح الجمع", "search": "    return a - b\n",
        "replace": "    return a + b\n", "test_name": "test_add",
        "test_code": "import calc\n\ndef test_add():\n    assert calc.add(2, 3) == 5\n"}


def _g(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    seed = tmp_path / "seed"
    (seed / "backend").mkdir(parents=True)
    for d in ("tools", "docs", "forensics"):
        (seed / d).mkdir()
    (seed / "backend" / "calc.py").write_text(ORIGINAL, encoding="utf-8")
    for f in ("gate_deletions.py", "gate_docs_sync.py"):
        shutil.copy(REPO_ROOT / "tools" / f, seed / "tools" / f)
    (seed / "docs" / "CHANGELOG.md").write_text("# C\n\n---\n## [R-1]\n", encoding="utf-8")
    (seed / "docs" / "PROJECT_STATE.md").write_text("# S\n", encoding="utf-8")
    (seed / "docs" / "ROADMAP_V6.md").write_text("# V6\n", encoding="utf-8")
    (seed / "docs" / "ROADMAP_ACTIVE.txt").write_text("docs/ROADMAP_V6.md\n", encoding="utf-8")
    (seed / "forensics" / "DELETED_LINES_AUDIT.md").write_text("# a\n", encoding="utf-8")
    _g(seed, "init", "-q", "-b", "main")
    for k, v in (("user.name", "t"), ("user.email", "t@example.com"), ("commit.gpgsign", "false")):
        _g(seed, "config", k, v)
    _g(seed, "add", "-A")
    _g(seed, "commit", "-q", "-m", "base")
    bare = tmp_path / "origin.git"
    _g(tmp_path, "clone", "-q", "--bare", str(seed), str(bare))
    work = tmp_path / "work"
    _g(tmp_path, "clone", "-q", str(bare), str(work))
    for k, v in (("user.name", "t"), ("user.email", "t@example.com"), ("commit.gpgsign", "false")):
        _g(work, "config", k, v)
    return work, bare


class FakeDisk:
    def __init__(self):
        self.rows = []

    def append_log(self, ns, payload):
        self.rows.append({"id": len(self.rows) + 1, "namespace": ns,
                          "payload": json.loads(json.dumps(payload))})
        return True

    def pull_log(self, ns, since_id=0, limit=1000):
        return [r for r in self.rows if r["namespace"] == ns and r["id"] > since_id][:limit]


def _disk_with_task():
    d = FakeDisk()
    d.append_log("selfdev", {"kind": "task", "task": {
        "id": "SD-feed0001", "source": "owner", "ref": None, "title": "add يطرح",
        "status": "drafted", "attempts": 1, "draft": dict(GOOD), "updated_at": 1}})
    return d


def _cycle(work, disk, ci="success", deploy="success", auto=True):
    calls = {"deploy": []}

    def dep(sha, repo):
        calls["deploy"].append(sha)
        return deploy
    rep = selfdev_ci.run_cycle(disk, work, base="origin/main", run_suite=False, push=False,
                               auto_promote=auto, wait_ci=lambda sha, repo: ci, deploy=dep)
    return rep, calls


def test_green_branch_fast_forwards_main_and_deploys(repo):
    work, bare = repo
    disk = _disk_with_task()
    rep, calls = _cycle(work, disk)
    sha = rep["processed"][0]["sha"]
    assert rep["auto_promotion"][0]["result"] == "promoted", rep
    assert _g(bare, "rev-parse", "main") == sha, "main لم يتقدم إلى البصمة نفسها"
    assert calls["deploy"] == [sha]
    last = disk.rows[-1]["payload"]
    assert last["result"] == "promoted" and last["deploy"] == "success"
    eng = sd.SelfDevEngine(brain=None, disk=disk)
    eng.tick()  # سحب نتائج CI (selfdev_ci) كما يفعل المجدول
    t = next(x for x in eng.status()["tasks"] if x["id"] == "SD-feed0001")
    assert t["status"] == "promoted" and t["ci"]["deploy"] == "success"


def test_red_ci_on_branch_never_touches_main(repo):
    work, bare = repo
    before = _g(bare, "rev-parse", "main")
    rep, calls = _cycle(work, _disk_with_task(), ci="failure")
    assert rep["auto_promotion"][0]["result"] == "red"
    assert _g(bare, "rev-parse", "main") == before and calls["deploy"] == []


def test_main_moved_means_stale_no_push(repo):
    work, bare = repo
    other = work.parent / "other"
    _g(work.parent, "clone", "-q", str(bare), str(other))
    for k, v in (("user.name", "o"), ("user.email", "o@example.com")):
        _g(other, "config", k, v)
    (other / "docs" / "PROJECT_STATE.md").write_text("# S2\n", encoding="utf-8")
    _g(other, "commit", "-qam", "moved")
    _g(other, "push", "-q", "origin", "main")
    moved = _g(bare, "rev-parse", "main")

    def wait_and_race(sha, repo_):
        return "success"
    disk = _disk_with_task()
    # الفرع يُبنى من origin/main المحلي القديم (لم يُجلب) ثم تجلب الترقية main المتقدم
    rep = selfdev_ci.run_cycle(disk, work, base="origin/main", run_suite=False,
                               auto_promote=True, wait_ci=wait_and_race,
                               deploy=lambda s, r: "success")
    assert rep["auto_promotion"][0]["result"] == "stale", rep
    assert _g(bare, "rev-parse", "main") == moved


def test_circuit_breaker_after_failed_auto_deploy(repo):
    work, bare = repo
    disk = _disk_with_task()
    disk.append_log("selfdev_ci", {"task_id": "SD-old", "result": "promoted",
                                   "deploy": "failure", "at": 1})
    before = _g(bare, "rev-parse", "main")
    rep, calls = _cycle(work, disk)
    assert rep["auto_promotion"][0]["result"] == "promote_skipped"
    assert "circuit_open" in rep["auto_promotion"][0]["reason"]
    assert _g(bare, "rev-parse", "main") == before and calls["deploy"] == []
    eng = sd.SelfDevEngine(brain=None, disk=disk)
    eng.tick()  # سحب نتائج CI (selfdev_ci) كما يفعل المجدول
    t = next(x for x in eng.status()["tasks"] if x["id"] == "SD-feed0001")
    assert t["status"] == "awaiting_promotion", "تخطي الترقية حُسب فشلًا"
    disk.append_log("selfdev_ci", {"task_id": None, "deploy": "reset", "result": "circuit_reset"})
    assert selfdev_ci.circuit_open([{"payload": r["payload"]} for r in disk.rows
                                    if r["namespace"] == "selfdev_ci"]) is None


def test_auto_promotion_off_by_default(repo):
    work, bare = repo
    before = _g(bare, "rev-parse", "main")
    rep, calls = _cycle(work, _disk_with_task(), auto=False)
    assert "auto_promotion" not in rep and _g(bare, "rev-parse", "main") == before
    src = (REPO_ROOT / "tools" / "selfdev_ci.py").read_text(encoding="utf-8")
    assert 'os.environ.get("SELFDEV_AUTO_PROMOTE") == "1"' in src


def test_workflows_wired_and_deploy_stays_manual():
    wf = (REPO_ROOT / ".github" / "workflows" / "self-develop.yml").read_text(encoding="utf-8")
    assert "SELFDEV_AUTO_PROMOTE: ${{ vars.SELFDEV_AUTO_PROMOTE }}" in wf
    assert "reset_circuit" in wf
    dep = (REPO_ROOT / ".github" / "workflows" / "deploy-fly.yml").read_text(encoding="utf-8")
    data = yaml.safe_load(dep)
    assert set(data.get("on", data.get(True)).keys()) == {"workflow_dispatch"}
    assert '.event == "push" or .event == "workflow_dispatch"' in dep
    assert '.conclusion == "success"' in dep
    src = (REPO_ROOT / "tools" / "selfdev_ci.py").read_text(encoding="utf-8")
    assert '"--is-ancestor", base, sha' in src, "الترقية ليست تقدمًا سريعًا فقط"
    assert "--force" not in src and "-f\", \"origin" not in src
