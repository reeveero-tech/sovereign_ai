"""R-796: محرك التطوير الذاتي — مهام حقيقية → مسودة كود+اختبار → تحقق → CI → ترقية.

المبادئ المثبتة:
- لا إجابة مزروعة: المسودة من العقل (مزيّف حتمي هنا)، وكل رفض بسبب حرفي.
- الحدود: مسارات محمية/خارج المسموح مرفوضة، search يجب أن يظهر مرة واحدة، النتيجة
  تُحلل نحويًا، الاختبار يستورد الوحدة ويحوي assert وبلا رموز خطرة.
- الإنتاج لا يكتب ملفًا: المحرك لا يملك أي مسار كتابة (حارس ثابت).
- الدوام: كل تغيير حالة يُلحق بـ disk_log ويُستعاد بعد إعادة الإقلاع.
- الربط: الاقتراحات (code_fix/approved) والأهداف المتعذرة تصير مهامًا؛ نتائج CI تحرك الحالة.
"""

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import self_develop as sd  # noqa: E402

ORIGINAL = "def add(a, b):\n    return a - b\n"


class FakeDisk:
    def __init__(self):
        self.rows = []

    def append_log(self, ns, payload):
        self.rows.append({"id": len(self.rows) + 1, "namespace": ns,
                          "payload": json.loads(json.dumps(payload))})
        return True

    def pull_log(self, ns, since_id=0, limit=1000):
        return [r for r in self.rows if r["namespace"] == ns and r["id"] > since_id][:limit]


def _repo(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "calc.py").write_text(ORIGINAL, encoding="utf-8")
    (tmp_path / "backend" / "safety.py").write_text("X = 1\n", encoding="utf-8")
    return tmp_path


GOOD = {"summary": "إصلاح الجمع", "search": "    return a - b\n",
        "replace": "    return a + b\n", "test_name": "test_add",
        "test_code": "import calc\n\ndef test_add():\n    assert calc.add(2, 3) == 5\n"}


def _brain(draft=GOOD, file="backend/calc.py"):
    calls = []

    def brain(system, user, schema):
        calls.append(schema)
        if "keywords" in schema.get("properties", {}):
            assert file in schema["properties"]["file"]["enum"] or file == "x"
            return json.dumps({"file": file, "keywords": ["add"]})
        return json.dumps(draft)
    brain.calls = calls
    return brain


def test_validate_rejects_protected_and_outside_paths():
    d = dict(GOOD, file="backend/safety.py")
    assert any(e.startswith("path_not_allowed") for e in sd.validate_draft(d, "X = 1\n"))
    for bad in ("tools/gate_deletions.py", ".github/workflows/ci.yml", "data/x.py",
                "docs/a.py", "backend/self_develop.py", "../etc/passwd.py", "fly.toml"):
        assert not sd.is_allowed(bad), bad
    assert sd.is_allowed("backend/calc.py")


def test_validate_requires_unique_search_valid_syntax_and_real_test():
    base = dict(GOOD, file="backend/calc.py")
    assert sd.validate_draft(base, ORIGINAL) == []
    assert "search_occurs_0_times" in sd.validate_draft(dict(base, search="nope"), ORIGINAL)
    assert any(e.startswith("result_syntax_error")
               for e in sd.validate_draft(dict(base, replace="    return (a +\n"), ORIGINAL))
    assert "test_without_assert" in sd.validate_draft(
        dict(base, test_code="import calc\n\ndef test_add():\n    calc.add(1, 2)\n"), ORIGINAL)
    assert "test_does_not_reference_module" in sd.validate_draft(
        dict(base, test_code="def test_add():\n    assert 1 == 1\n"), ORIGINAL)
    assert any(e.startswith("test_forbidden_token") for e in sd.validate_draft(
        dict(base, test_code="import calc, subprocess\n\ndef test_add():\n    assert calc\n"),
        ORIGINAL))
    assert "forbidden_token:subprocess" in sd.validate_draft(
        dict(base, replace="    import subprocess\n    return a + b\n"), ORIGINAL)
    assert "no_change" in sd.validate_draft(dict(base, replace=base["search"]), ORIGINAL)


def test_tick_drafts_valid_change_and_persists(tmp_path):
    disk = FakeDisk()
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path), brain=_brain(), disk=disk)
    t = eng.request("دالة add في calc تطرح بدل أن تجمع", "calc.add(2,3) يعيد -1")
    out = eng.tick(now=100.0)
    assert out["status"] == "drafted", out
    assert out["file"] == "backend/calc.py"
    st = eng.status()
    task = next(x for x in st["tasks"] if x["id"] == t["id"])
    assert task["status"] == "drafted" and task["summary"] == "إصلاح الجمع"
    assert "test_code" not in json.dumps(st) and "return a + b" not in json.dumps(st), \
        "الحالة العامة تسرّب الشيفرة"
    persisted = [r["payload"]["task"] for r in disk.rows if r["namespace"] == "selfdev"]
    assert persisted[-1]["draft"]["replace"] == "    return a + b\n"
    # الإنتاج لم يكتب شيئًا
    assert (tmp_path / "backend" / "calc.py").read_text(encoding="utf-8") == ORIGINAL


def test_invalid_draft_retries_with_feedback_then_exhausts(tmp_path):
    bad = dict(GOOD, search="لا يوجد")
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path), brain=_brain(bad), disk=False)
    eng.request("add يطرح في calc", "")
    statuses = [eng.tick(now=float(i))["status"] for i in range(sd.MAX_ATTEMPTS + 1)]
    assert statuses[:sd.MAX_ATTEMPTS - 1] == ["invalid"] * (sd.MAX_ATTEMPTS - 1)
    assert statuses[sd.MAX_ATTEMPTS - 1] == "exhausted"
    assert statuses[-1] == "idle", "مهمة مستنفدة أعيدت محاولتها"


def test_no_brain_is_declared_not_faked(tmp_path):
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path), brain=None, disk=False)
    eng.request("add يطرح في calc")
    out = eng.tick()
    assert out["status"] == "brain_unavailable"
    assert eng.status()["brain"] is False
    assert eng.status()["counts"]["pending"] == 1


def test_rehydrate_after_restart_and_ci_results_drive_state(tmp_path):
    disk = FakeDisk()
    repo = _repo(tmp_path)
    eng = sd.SelfDevEngine(repo_root=repo, brain=_brain(), disk=disk)
    t = eng.request("add يطرح في calc")
    eng.tick(now=1.0)
    # «إعادة إقلاع»: محرك جديد بنفس القرص
    eng2 = sd.SelfDevEngine(repo_root=repo, brain=_brain(), disk=disk)
    assert eng2.status()["counts"]["drafted"] == 1
    disk.append_log("selfdev_ci", {"task_id": t["id"], "attempt": 1, "result": "red",
                                   "reason": "not_red_first", "log_tail": "1 passed", "at": 2.0})
    eng2.tick(now=3.0)
    task = next(x for x in eng2.status()["tasks"] if x["id"] == t["id"])
    assert task["status"] == "drafted" and task["attempts"] == 2, "لم تُعد الصياغة بعد RED"
    disk.append_log("selfdev_ci", {"task_id": t["id"], "attempt": 2, "result": "green",
                                   "branch": "work/selfdev-x", "sha": "a" * 40, "at": 4.0})
    eng2.tick(now=5.0)
    task = next(x for x in eng2.status()["tasks"] if x["id"] == t["id"])
    assert task["status"] == "awaiting_promotion"
    assert task["ci"]["branch"] == "work/selfdev-x"
    disk.append_log("selfdev_ci", {"task_id": t["id"], "attempt": 2, "result": "promoted",
                                   "sha": "a" * 40, "at": 6.0})
    eng2.tick(now=7.0)
    assert next(x for x in eng2.status()["tasks"] if x["id"] == t["id"])["status"] == "promoted"


def test_proposals_become_tasks_but_suppressed_do_not(tmp_path):
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path), brain=None, disk=False)
    props = [
        {"id": "P-1", "kind": "code_fix", "status": "proposed", "title": "أداة تفشل",
         "recommendation": "r", "evidence": "e", "defect_open": True},
        {"id": "P-2", "kind": "investigation", "status": "approved", "title": "موافق",
         "recommendation": "r", "evidence": "e", "defect_open": True},
        {"id": "P-3", "kind": "code_fix", "status": "suppressed", "title": "محجوب",
         "defect_open": True},
        {"id": "P-4", "kind": "investigation", "status": "proposed", "title": "تحقيق"},
        {"id": "P-5", "kind": "code_fix", "status": "proposed", "title": "مغلق",
         "defect_open": False},
    ]
    assert eng.ingest_proposals(props) == 2
    assert eng.ingest_proposals(props) == 0, "تكرار الاستيعاب أنشأ مهام مكررة"
    refs = {t["ref"] for t in eng.status()["tasks"]}
    assert refs == {"P-1", "P-2"}


def test_engine_has_no_write_or_exec_path():
    tree = ast.parse((REPO_ROOT / "backend" / "self_develop.py").read_text(encoding="utf-8"))
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute):
            names.add(n.attr)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            names.add(n.func.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                names.add(a.name)
            if isinstance(n, ast.ImportFrom) and n.module:
                names.add(n.module)
    for forbidden in ("write_text", "write_bytes", "subprocess", "system", "unlink",
                      "rmtree", "exec", "eval", "Popen", "open", "shutil"):
        assert forbidden not in names, f"المحرك يملك مسار {forbidden} — الإنتاج يجب ألا يكتب"


def test_wired_tools_endpoint_scheduler_and_capability(monkeypatch):
    monkeypatch.delenv("SOVEREIGN_SCHEDULER", raising=False)
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        names = {t["name"] for t in client.get("/tools/list").json()["tools"]}
        assert {"selfdev.tick", "selfdev.request", "selfdev.status"} <= names
        r = client.get("/selfdev/status")
        assert r.status_code == 200 and r.json()["engine"] == "R-796"
        tasks = [t["tool"] for t in client.get("/scheduler/status").json()["tasks"]]
        assert "selfdev.tick" in tasks
        caps = {c["id"] for c in client.get("/capabilities").json()["capabilities"]}
        assert "self_development" in caps


def test_blocked_goal_creates_selfdev_task(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_EXPERIENCE_DIR", str(tmp_path / "exp"))
    import goals
    from tool_registry import ToolRegistry

    class _Mgr:
        def run(self, *a, **k):
            return {}

    def brain(system, user, **kw):
        if "ضع خطة" in system:
            return '{"plan":["أرسل"]}'
        return json.dumps({"decision": "blocked", "reason": "لا أداة لإرسال البريد"},
                          ensure_ascii=False)

    eng = sd.SelfDevEngine(brain=None, disk=False)
    sd.reset_engine(eng)
    try:
        ge = goals.GoalEngine(ToolRegistry(), chat_fn=brain, manager_factory=lambda t: _Mgr())
        g = ge.goals.add("أرسل بريدًا للعميل")
        assert ge.work(g["id"])["status"] == "blocked"
        tasks = eng.status()["tasks"]
        assert len(tasks) == 1 and tasks[0]["source"] == "goal" and tasks[0]["ref"] == g["id"]
        assert "أرسل بريدًا للعميل" in tasks[0]["title"]
    finally:
        sd.reset_engine(None)
