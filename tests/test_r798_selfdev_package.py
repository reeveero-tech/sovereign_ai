"""R-798: حزمة التطوير الذاتي — مجسّات ⇒ محدد مواضع ⇒ عقل اقتراح ⇒ نواة ⇒ أهداف متعذرة.

المبادئ المثبتة:
- المجسّات تقرأ مخرجات تشغيلية حقيقية وتدمج الظاهرة نفسها من مصادر متعددة؛ مصدر معطوب
  يُعلن إشارة ولا يُسقط الجمع.
- محدد المواضع يصل لمعالج الأداة الحقيقي عبر inspect ويعلّم المحمي بأنه غير قابل للتعديل.
- عقل الاقتراح: ملف هدف خارج المواضع القابلة للتعديل أو code_fix بلا خطة ⇒ يُخفَّض إلى
  unresolved؛ بلا عقل لا يُختلق سبب جذري.
- النواة: أولوية بالتكرار، لا إعادة تحليل قبل المهلة ما لم يتغير الدليل، توجيه حقيقي.
- الأهداف المتعذرة: سُلّم توسيع ⇒ تفكيك ⇒ المالك، حل حقيقي فقط عند ترقية مهمة، دوام.
- الحزمة لا تملك مسار كتابة أو تنفيذ.
"""

import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import self_develop as sd  # noqa: E402
from selfdev import signals as S  # noqa: E402
from selfdev.locator import Locator  # noqa: E402
from selfdev.nucleus import Nucleus, priority  # noqa: E402
from selfdev.proposal_brain import ProposalBrain, validate  # noqa: E402
from selfdev.unmet import UnmetGoals  # noqa: E402


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
    (tmp_path / "backend" / "calc.py").write_text(
        "def compute_total(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "backend" / "safety.py").write_text("compute_total = 1\n", encoding="utf-8")
    return tmp_path


def _engine(tmp_path, disk=False):
    return sd.SelfDevEngine(repo_root=tmp_path, brain=None, disk=disk)


# ---------------- المجسّات ----------------
def test_signals_merge_same_phenomenon_across_sources():
    sources = {
        "scheduler": lambda: {"tasks": [{"name": "t", "tool": "calc.total", "runs": 2,
                                          "last_ok": False, "last_error": "ZeroDivisionError"}]},
        "tool_stats": lambda: {"calc.total": {"calls": 5, "success_rate": 0.2,
                                              "last_error": "ZeroDivisionError"}},
        "brain": lambda: {"result": "ok"},
        "goals": lambda: {"G1": {"status": "blocked", "title": "أرسل بريدًا", "why": "لا أداة"}},
        "defects": lambda: (_ for _ in ()).throw(RuntimeError("probe down")),
    }
    sigs, errors = S.gather(sources)
    keys = {s["key"] for s in sigs}
    assert "scheduled_task_failed:t" in keys and "selfmon:tool_failing:calc.total" in keys
    assert "goal_blocked:G1" in keys
    assert "defects" in errors and "selfdev:source_unavailable:defects" in keys
    assert not any(k == "brain_call_failed" for k in keys)
    dup = S.merge([S._sig("k", "a", "low", "t", "e1"), S._sig("k", "b", "high", "t", "e2",
                                                            kind_hint="code_fix")])
    assert len(dup) == 1 and dup[0]["origins"] == ["a", "b"] and dup[0]["severity"] == "high"
    assert dup[0]["kind_hint"] == "code_fix" and "e1" in dup[0]["evidence"] and "e2" in dup[0]["evidence"]


def test_proposals_signal_skips_suppressed_and_closed():
    items = [{"id": "P1", "defect_id": "d:1", "status": "proposed", "kind": "code_fix",
              "severity": "high", "title": "x", "evidence": "ev"},
             {"id": "P2", "defect_id": "d:2", "status": "suppressed"},
             {"id": "P3", "defect_id": "d:3", "status": "proposed", "defect_open": False}]
    sigs = S.from_proposals(items)
    assert [s["key"] for s in sigs] == ["d:1"] and sigs[0]["ref"] == "P1"


# ---------------- محدد المواضع ----------------
def test_locator_finds_real_tool_handler_and_marks_protected(tmp_path):
    repo = _repo(tmp_path)
    sys.path.insert(0, str(repo / "backend"))
    try:
        import importlib
        calc = importlib.import_module("calc")

        class Spec:
            handler = calc.compute_total

        class Reg:
            _tools = {"calc.total": Spec()}

        loc = Locator(repo_root=repo, registry_fn=lambda: Reg(), engine=_engine(repo))
        found = loc.locate({"key": "selfmon:tool_failing:calc.total", "title": "",
                            "evidence": "compute_total failing", "tools": ["calc.total"]})
        assert found[0]["file"] == "backend/calc.py" and found[0]["editable"] is True
        assert "معالج الأداة" in found[0]["why"]
        prot = [l for l in found if l["file"] == "backend/safety.py"]
        assert prot and prot[0]["editable"] is False
        assert "return a - b" in loc.snippet(found[0])
    finally:
        sys.path.remove(str(repo / "backend"))
        sys.modules.pop("calc", None)


# ---------------- عقل الاقتراح ----------------
def test_validate_downgrades_untrusted_brain_output():
    ok = validate({"route": "code_fix", "target_file": "backend/calc.py", "plan": ["بدّل الإشارة"],
                   "root_cause": "طرح بدل جمع", "confidence": 0.9}, ["backend/calc.py"])
    assert ok["route"] == "code_fix" and ok["target_file"] == "backend/calc.py"
    out = validate({"route": "code_fix", "target_file": "backend/safety.py", "plan": ["x"],
                    "root_cause": "r", "confidence": 2}, ["backend/calc.py"])
    assert out["route"] == "unresolved" and out["target_file"] is None
    assert "target_outside_editable:backend/safety.py" in out["validation_notes"]
    assert out["confidence"] == 1.0
    noplan = validate({"route": "code_fix", "target_file": "backend/calc.py", "plan": [],
                       "root_cause": "r", "confidence": 0.5}, ["backend/calc.py"])
    assert noplan["route"] == "unresolved"
    bad = validate({"route": "hack"}, [])
    assert bad["route"] == "unresolved" and "root_cause_empty" in bad["validation_notes"]


def test_proposal_brain_without_brain_does_not_invent_root_cause(tmp_path):
    repo = _repo(tmp_path)
    pb = ProposalBrain(None, Locator(repo_root=repo, engine=_engine(repo)))
    a = pb.analyze({"key": "k", "title": "compute_total", "evidence": "", "kind_hint": "code_fix",
                    "files_hint": ["backend/calc.py"]})
    assert a["brain"] is False and a["root_cause"] is None
    assert a["route"] == "code_fix" and a["target_file"] == "backend/calc.py"


def test_proposal_brain_sends_real_snippets_and_schema_enum(tmp_path):
    repo = _repo(tmp_path)
    seen = {}

    def brain(system, user, schema):
        seen["user"], seen["schema"] = user, schema
        return json.dumps({"root_cause": "طرح بدل جمع", "route": "code_fix",
                           "target_file": "backend/calc.py", "plan": ["a + b"],
                           "acceptance_test": "compute_total(2,3)==5", "confidence": 0.8})

    pb = ProposalBrain(brain, Locator(repo_root=repo, engine=_engine(repo)))
    a = pb.analyze({"key": "k", "title": "compute_total wrong", "evidence": "compute_total(2,3)=-1",
                    "kind_hint": "investigation", "severity": "high", "origins": ["x"]})
    assert "return a - b" in seen["user"]
    assert "backend/calc.py" in json.dumps(seen["schema"])
    assert "backend/safety.py" not in json.dumps(seen["schema"])
    assert a["route"] == "code_fix" and a["brain"] is True and pb.calls == 1


# ---------------- النواة ----------------
class StubBrain:
    def __init__(self, result):
        self.result, self.calls, self.failures, self.seen = result, 0, 0, []

    def analyze(self, sig):
        self.calls += 1
        self.seen.append(sig["key"])
        return dict(self.result)


def _nucleus(tmp_path, sources, result, disk=False):
    eng = _engine(tmp_path)
    unmet = UnmetGoals(eng, brain=None, disk=disk)
    brain = StubBrain(result)
    return Nucleus(sources, brain, eng, unmet, disk=disk), eng, unmet, brain


FIX = {"brain": True, "route": "code_fix", "target_file": "backend/calc.py",
       "plan": ["a + b"], "root_cause": "طرح بدل جمع", "acceptance_test": "2+3==5"}


def test_priority_grows_with_recurrence_and_severity():
    s = {"severity": "high", "kind_hint": "investigation"}
    assert priority(s, {"cycles": 4, "first_seen": 0}, 0) > priority(s, {"cycles": 1, "first_seen": 0}, 0)
    assert priority(s, {"cycles": 1}, 0) > priority(dict(s, severity="low"), {"cycles": 1}, 0)


def test_nucleus_routes_code_fix_to_engine_with_root_cause_and_hint(tmp_path):
    repo = _repo(tmp_path)
    src = {"tool_stats": lambda: {"calc.total": {"calls": 5, "success_rate": 0.0,
                                                 "last_error": "wrong"}}}
    nuc, eng, unmet, brain = _nucleus(repo, src, FIX)
    out = nuc.cycle(now=1000.0)
    tasks = eng.status()["tasks"]
    assert len(tasks) == 1 and tasks[0]["source"] == "nucleus"
    assert tasks[0]["files_hint"] == ["backend/calc.py"]
    assert out["cycle"]["routes"]["selfmon:tool_failing:calc.total"] == tasks[0]["id"]
    # نفس الدليل داخل المهلة ⇒ لا إعادة تحليل
    nuc.cycle(now=2000.0)
    assert brain.calls == 1
    # دليل تغيّر ⇒ إعادة تحليل
    src["tool_stats"] = lambda: {"calc.total": {"calls": 9, "success_rate": 0.1, "last_error": "x"}}
    nuc.cycle(now=3000.0)
    assert brain.calls == 2
    st = nuc.status()
    assert st["active_signals"][0]["cycles"] == 3 and st["journal"][-1]["root_cause"]


def test_nucleus_operational_and_blocked_goal_go_to_unmet(tmp_path):
    repo = _repo(tmp_path)
    src = {"brain": lambda: {"result": "error", "error": "timeout"},
           "goals": lambda: {"G1": {"status": "blocked", "title": "أرسل بريدًا", "why": "لا أداة"}}}
    op = dict(FIX, route="operational", target_file=None, plan=[])
    nuc, eng, unmet, brain = _nucleus(repo, src, op)
    nuc.max_analyses = 5
    nuc.cycle(now=1.0)
    goals = {g["origin"]: g for g in unmet.status()["goals"]}
    assert set(goals) == {"operational", "goal_blocked"}
    assert brain.seen == ["brain_call_failed"]  # الهدف المتعذر يُوجَّه بلا عقل
    assert eng.status()["tasks"] == []


def test_nucleus_low_severity_unresolved_is_observed_only(tmp_path):
    repo = _repo(tmp_path)
    src = {"defects": lambda: (_ for _ in ()).throw(RuntimeError("down"))}
    nuc, eng, unmet, _ = _nucleus(repo, src, dict(FIX, route="unresolved", target_file=None))
    out = nuc.cycle(now=1.0)
    assert out["cycle"]["routes"] == {"selfdev:source_unavailable:defects": "observed"}
    assert unmet.status()["goals"] == [] and eng.status()["tasks"] == []


def test_nucleus_reuses_existing_proposal_task(tmp_path):
    repo = _repo(tmp_path)
    props = [{"id": "P1", "defect_id": "d:1", "status": "proposed", "kind": "code_fix",
              "severity": "high", "title": "fix", "evidence": "ev"}]
    nuc, eng, unmet, _ = _nucleus(repo, {"proposals": lambda: props}, FIX)
    eng.ingest_proposals(props, now=0.0)
    nuc.cycle(now=1.0)
    assert len(eng.status()["tasks"]) == 1


def test_nucleus_journal_persists_and_rehydrates(tmp_path):
    repo = _repo(tmp_path)
    disk = FakeDisk()
    src = {"tool_stats": lambda: {"calc.total": {"calls": 5, "success_rate": 0.0}}}
    nuc, eng, unmet, brain = _nucleus(repo, src, FIX, disk=disk)
    nuc.cycle(now=10.0)
    nuc2 = Nucleus(src, brain, eng, unmet, disk=disk)
    nuc2.cycle(now=20.0)
    assert brain.calls == 1  # بعد إعادة الإقلاع لا يُعاد التحليل داخل المهلة
    assert any(r["namespace"] == "selfdev_nucleus" for r in disk.rows)


# ---------------- الأهداف المتعذرة ----------------
def _set(eng, tid, status, file=None, errors=None):
    t = eng._tasks[tid]
    t["status"] = status
    if file:
        t["draft"] = {"file": file}
    t["errors"] = errors or []


def test_unmet_ladder_widen_then_decompose_then_owner(tmp_path):
    repo = _repo(tmp_path)
    eng = _engine(repo)
    calls = []

    def brain(system, user, schema):
        calls.append(user)
        return json.dumps({"subtasks": [{"title": "جزء ١", "detail": "d", "file": "backend/calc.py"},
                                        {"title": "جزء ٢", "detail": "d", "file": ""}]})

    disk = FakeDisk()
    um = UnmetGoals(eng, brain=brain, disk=disk)
    first = eng.request("أصلح الجمع", "التفصيل", source="owner", ref="o1", now=0.0)
    _set(eng, first["id"], "exhausted", file="backend/calc.py", errors=["syntax"])
    um.cycle(now=1.0)  # مزامنة ⇒ هدف owner_request ⇒ توسيع
    g = um.status()["goals"][0]
    assert g["origin"] == "owner_request" and g["status"] == "retrying"
    assert g["strategies"][0]["strategy"] == "widen"
    widen = eng.get(g["strategies"][0]["tasks"][0])
    assert widen["exclude_files"] == ["backend/calc.py"] and widen["source"] == "unmet"
    _set(eng, widen["id"], "exhausted", file="backend/other.py", errors=["ci_failed"])
    um.cycle(now=2.0)  # فشل التوسيع ⇒ تفكيك بالعقل
    g = um.status()["goals"][0]
    assert g["strategies"][-1]["strategy"] == "decompose" and len(g["strategies"][-1]["tasks"]) == 2
    assert "backend/other.py" in g["files_tried"] and "ci_failed" in calls[0]
    subs = [eng.get(t) for t in g["strategies"][-1]["tasks"]]
    assert subs[0]["files_hint"] == ["backend/calc.py"]
    for t in subs:
        _set(eng, t["id"], "exhausted")
    um.cycle(now=3.0)
    um.cycle(now=4.0)  # بعد فشل التفكيك ⇒ المالك بتقرير صادق
    g = um.status()["goals"][0]
    assert g["status"] == "needs_owner" and "owner_report" in g
    # الدوام: نسخة جديدة تستعيد الحالة نفسها
    um2 = UnmetGoals(eng, brain=None, disk=disk)
    assert um2.status()["goals"][0]["status"] == "needs_owner"


def test_unmet_resolves_only_when_task_promoted(tmp_path):
    repo = _repo(tmp_path)
    eng = _engine(repo)
    um = UnmetGoals(eng, brain=None, disk=False)
    um.raise_goal("goal_blocked", "G1", "أرسل بريدًا", now=0.0)
    um.cycle(now=1.0)
    g = um.status()["goals"][0]
    tid = g["strategies"][0]["tasks"][0]
    um.cycle(now=2.0)
    assert um.status()["goals"][0]["status"] == "retrying"  # ما زال ينتظر — لا حل وهمي
    _set(eng, tid, "promoted")
    um.cycle(now=3.0)
    g = um.status()["goals"][0]
    assert g["status"] == "resolved" and g["resolution"] == "resolved_promoted"


def test_unmet_without_brain_decompose_escalates_honestly(tmp_path):
    eng = _engine(_repo(tmp_path))
    um = UnmetGoals(eng, brain=None, disk=False)
    um.raise_goal("repair_exhausted", "T1", "x", now=0.0)
    um.cycle(now=1.0)
    _set(eng, um.status()["goals"][0]["strategies"][0]["tasks"][0], "exhausted")
    um.cycle(now=2.0)
    g = um.status()["goals"][0]
    assert g["strategies"][-1] == dict(g["strategies"][-1], strategy="decompose",
                                       outcome="nothing_spawned")
    um.cycle(now=3.0)
    assert um.status()["goals"][0]["status"] == "needs_owner"


def test_signal_bound_goal_resolves_when_signal_disappears(tmp_path):
    eng = _engine(_repo(tmp_path))
    um = UnmetGoals(eng, brain=None, disk=False)
    um.raise_goal("operational", "brain_call_failed", "العقل", signal_key="brain_call_failed", now=0.0)
    um.cycle(active_keys={"brain_call_failed"}, now=1.0)
    assert um.status()["goals"][0]["status"] == "needs_owner"
    um.raise_goal("component_failure", "k", "t", signal_key="k", now=0.0)
    um.cycle(active_keys=set(), now=2.0)
    by = {g["origin"]: g for g in um.status()["goals"]}
    assert by["component_failure"]["resolution"] == "resolved_signal_gone"


def test_nucleus_raises_component_failure_when_fix_did_not_stick(tmp_path):
    repo = _repo(tmp_path)
    src = {"tool_stats": lambda: {"calc.total": {"calls": 5, "success_rate": 0.0}}}
    nuc, eng, unmet, _ = _nucleus(repo, src, FIX)
    out = nuc.cycle(now=0.0)
    tid = out["cycle"]["routes"]["selfmon:tool_failing:calc.total"]
    _set(eng, tid, "promoted")
    for i in range(1, 7):
        nuc.cycle(now=float(i))
    goals = unmet.status()["goals"]
    assert [g["origin"] for g in goals] == ["component_failure"]
    assert tid in goals[0]["detail"]


# ---------------- الحدود والربط ----------------
def test_package_has_no_write_or_exec_path():
    for path in sorted((REPO_ROOT / "backend" / "selfdev").glob("*.py")):
        names = set()
        for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Attribute):
                names.add(n.attr)
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                names.add(n.func.id)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                names.update(a.name for a in n.names)
                if isinstance(n, ast.ImportFrom) and n.module:
                    names.add(n.module)
        for forbidden in ("write_text", "write_bytes", "subprocess", "system", "unlink",
                          "rmtree", "exec", "eval", "Popen", "open", "shutil"):
            assert forbidden not in names, f"{path.name} يملك مسار {forbidden}"


def test_package_is_protected_from_self_modification():
    assert sd.is_protected("backend/selfdev/nucleus.py")
    assert not sd.is_allowed("backend/selfdev/unmet.py")


def test_wired_endpoints_tools_and_full_cycle(monkeypatch, tmp_path):
    monkeypatch.delenv("SOVEREIGN_SCHEDULER", raising=False)
    from fastapi.testclient import TestClient
    from app import app, _selfdev_tick_payload
    from selfdev import wiring
    eng = sd.SelfDevEngine(brain=None, disk=False)
    sd.reset_engine(eng)
    wiring.reset()
    monkeypatch.setattr(UnmetGoals, "_disk_client", lambda self: None)
    monkeypatch.setattr(Nucleus, "_disk_client", lambda self: None)
    try:
        with TestClient(app) as client:
            names = {t["name"] for t in client.get("/tools/list").json()["tools"]}
            assert {"selfdev.nucleus", "selfdev.unmet", "selfdev.tick"} <= names
            out = _selfdev_tick_payload()
            assert {"nucleus", "engine", "unmet", "tick", "status"} <= set(out)
            assert "error" not in out["nucleus"] and "error" not in out["unmet"]
            n = client.get("/selfdev/nucleus").json()
            assert n["engine"] == "R-798 nucleus" and n["cycles"] == 1
            assert set(n["sources"]) == set(S.COLLECTORS)
            u = client.get("/selfdev/unmet").json()
            assert u["engine"] == "R-798 unmet" and u["ladder"] == ["widen", "decompose", "owner"]
    finally:
        sd.reset_engine(None)
        wiring.reset()


def test_engine_candidates_honor_hints_and_exclusions(tmp_path):
    repo = _repo(tmp_path)
    (repo / "backend" / "other.py").write_text("def compute_total():\n    return 0\n", encoding="utf-8")
    eng = _engine(repo)
    t = eng.request("compute_total", "", source="nucleus", ref="k", now=0.0,
                    files_hint=["backend/other.py", "backend/safety.py"],
                    exclude_files=["backend/calc.py"])
    assert t["files_hint"] == ["backend/other.py"]  # المحمي لا يُرجَّح
    cands = eng.candidates(eng._tasks[t["id"]])
    assert cands[0] == "backend/other.py" and "backend/calc.py" not in cands
