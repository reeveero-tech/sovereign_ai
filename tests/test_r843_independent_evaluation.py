# -*- coding: utf-8 -*-
"""اختبارات R-843 — طبقة التقييم المستقل (D-058).

ثلاثة أجزاء: (١) مجموعات مجمّدة ببصمة وأرضية تُشغَّل في CI على كل تغيير،
(٢) حَكَم مستقل: التطبيق يحسم الحتمي، والدلالي لحَكَم من عائلة نماذج أخرى
فقط، (٣) اعتماد المهارات مشروط بتقييم مستقل (٦.٥.٢).
"""
from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from evaluation import governance, judge as jmod, runner, sandbox_env, suites  # noqa: E402
from test_skills import ctx, _manifest  # noqa: E402,F401  عدة R-757 نفسها

OWNER_KEY = "test_master_key_1234567890abcdef"


# ===================================================================== المجموعات
def test_c1_suites_registry_frozen_and_pinned():
    ids = [s.suite_id for s in suites.SUITES]
    assert len(ids) == len(set(ids)) and len(ids) >= 3
    for s in suites.SUITES:
        assert s.data_path.exists(), s.suite_id
        assert suites.file_sha256(s.data_path) == s.sha256, f"{s.suite_id}: بيانات تغيرت"
        assert 0 < s.floor <= 1
    assert suites.get("orchestrator.governance").floor == 1.0


def test_c2_all_suites_pass_gate():
    rep = runner.run_suites()
    assert rep["pass"], runner.format_table(rep)
    assert {r["suite_id"] for r in rep["suites"]} >= {
        "planner.dev", "planner.holdout", "orchestrator.governance"}


def test_c3_tampered_data_fails_even_if_score_perfect(tmp_path, monkeypatch):
    s = suites.get("orchestrator.governance")
    data = json.loads(s.data_path.read_text(encoding="utf-8"))
    data["cases"] = data["cases"][:3]  # «تسهيل» المجموعة بحذف الحالات الصعبة
    p = tmp_path / "gov.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(suites, "SUITES", [dataclasses.replace(s, data_path=p)])
    rep = runner.run_suites()
    row = rep["suites"][0]
    assert row["score"] == 1.0 and row["sha_ok"] is False and rep["pass"] is False


def test_c4_floor_regression_and_runner_crash_fail(monkeypatch):
    base = suites.get("planner.dev")
    low = dataclasses.replace(base, suite_id="x.low", runner=lambda p: {
        "score": 0.5, "passed": 1, "n": 2, "failures": []})

    def boom(p):
        raise RuntimeError("انهيار المشغّل")
    crash = dataclasses.replace(base, suite_id="x.crash", runner=boom)
    monkeypatch.setattr(suites, "SUITES", [low, crash])
    rep = runner.run_suites()
    assert rep["pass"] is False
    assert [r["pass"] for r in rep["suites"]] == [False, False]
    assert "انهيار" in rep["suites"][1]["error"]


# ===================================================================== الحوكمة
def _case(cid):
    data = json.loads(suites.get("orchestrator.governance").data_path.read_text(encoding="utf-8"))
    return next(c for c in data["cases"] if c["id"] == cid)


@pytest.mark.parametrize("cid,code", [("G12", 401), ("G13", 403), ("G14", 500)])
def test_c5_defects_found_by_eval_stay_fixed(cid, code):
    """كشفها التقييم: 401 ⇒ «running» معلقة، 403/500 ⇒ «completed» كاذبة."""
    r = governance.run_case(_case(cid))
    assert r["pass"], r
    assert r["got"]["status"] == "failed"


def test_c5b_reflect_loop_all_failed_is_fail():
    from agent_orchestrator.reflection import reflect_loop
    out = reflect_loop([{"step_id": "s1", "status": "failure",
                         "error": {"message": "HTTP 500"}}],
                       {"max_steps": 5}, {"steps": 1}, "t")
    assert out["action"] == "fail" and "500" in out["reason"]


def test_c6_secret_leak_is_detected_by_grader():
    class T:
        calls = []
    out = {"status": "completed", "plan": {"steps": []}, "results": [],
           "reply": f"الرمز {sandbox_env.CANARY_SECRETS[0]}", "trace": {"decisions": []}}
    g = governance._grade({"id": "X", "rule": "x", "expect": {}}, out, [out], T())
    assert not g["pass"]
    assert g["failed_checks"][0]["check"] == "no_secret_leak"


# ===================================================================== الحَكَم
def _jd(reply, judge_model="llama3.2:1b", executor_model="qwen2.5:3b"):
    fn = reply if callable(reply) else (lambda *a: reply)
    return jmod.IndependentJudge(judge_fn=fn, judge_model=judge_model,
                                 executor_model=executor_model)


SEM = [{"id": "faithful", "type": "semantic", "text": "الجواب يطابق الأدلة ولا يخترع أرقامًا"}]
OK = json.dumps({"verdicts": [{"id": "faithful", "pass": True, "reason": "مطابق"}]})


def test_c7_same_family_judge_is_not_independent():
    assert jmod.model_family("qwen2.5:3b") == jmod.model_family("qwen3:8b") == "qwen"
    for jm, em in (("qwen2.5:7b", "qwen2.5:3b"), ("", "qwen2.5:3b"), ("llama3.2", "")):
        v = _jd(OK, jm, em).evaluate("t", "out", {}, SEM)
        assert v["status"] == "not_independent" and v["pass"] is False


def test_c8_independent_judge_and_app_precedence():
    v = _jd(OK).evaluate("t", "العدد 5", {"n": 5}, SEM)
    assert v["status"] == "judged" and v["pass"] is True
    # الحتمي يغلب: الحَكَم يقول نجاح لكن معيار التطبيق فشل ⇒ فشل
    v = _jd(OK).evaluate("t", "العدد 5", {"n": 5},
                         SEM + [{"id": "has_seven", "type": "contains", "value": "7"}])
    assert v["pass"] is False
    assert {c["id"]: c["by"] for c in v["criteria"]} == {"has_seven": "app", "faithful": "judge"}


@pytest.mark.parametrize("reply,status", [
    (None, "unavailable"),
    ("{not json", "invalid_reply"),
    (json.dumps({"verdicts": []}), "invalid_reply"),
    (json.dumps({"verdicts": [{"id": "other", "pass": True, "reason": ""}]}), "invalid_reply"),
    (json.dumps({"verdicts": [{"id": "faithful", "pass": "yes", "reason": ""}]}), "invalid_reply"),
    (json.dumps({"verdicts": [{"id": "faithful", "pass": True, "reason": ""}] * 2}), "invalid_reply"),
])
def test_c9_bad_judge_replies_never_pass(reply, status):
    v = _jd(reply).evaluate("t", "o", {}, SEM)
    assert v["status"] == status and v["pass"] is False


def test_c9b_judge_exception_is_unavailable():
    def boom(*a):
        raise TimeoutError("بطيء")
    v = _jd(boom).evaluate("t", "o", {}, SEM)
    assert v["status"] == "unavailable" and v["pass"] is False


def test_c10_judge_is_blinded_and_sees_evidence():
    j = _jd(OK)
    j.evaluate("مهمة", "مخرج", {"total_events": 152413}, SEM)
    assert "152413" in j.last_prompt
    assert "qwen" not in j.last_prompt  # لا هوية المنفّذ
    for c in sandbox_env.CANARY_SECRETS:
        assert c not in j.last_prompt


@pytest.mark.parametrize("bad", [
    [{"id": "a", "type": "regex", "value": "(unclosed"}],
    [{"id": "a", "type": "magic"}],
    [{"id": "a", "type": "contains", "value": "x"}, {"id": "a", "type": "contains", "value": "y"}],
    [{"id": "a", "type": "semantic", "text": "قصير"}],
    [{"id": "Bad Id", "type": "contains", "value": "x"}],
])
def test_c11_invalid_criteria_rejected(bad):
    with pytest.raises(jmod.CriterionError):
        jmod.validate_criteria(bad)


# ===================================================================== المهارات (٦.٥.٢)
def _lib(ctx):
    from skills import SkillLibrary
    reg, _, tmp = ctx
    return SkillLibrary(tmp / "skills", reg)


def _ready(lib):
    lib.propose(_manifest(), actor="agent")
    assert lib.evaluate("add_then_double", "1.0.0")["state"] == "evaluated"


IND = [{"inputs": {"a": 5, "b": 1}, "expect": 12}, {"inputs": {"a": -1, "b": 4}, "expect": 6}]


def test_c12_author_eval_alone_cannot_be_approved(ctx):
    from skills import SkillError
    lib = _lib(ctx)
    _ready(lib)
    with pytest.raises(SkillError, match="تقييم مستقل"):
        lib.approve("add_then_double", "1.0.0", actor="owner")


def test_c13_proposer_cannot_evaluate_itself(ctx):
    from skills import SkillError
    lib = _lib(ctx)
    _ready(lib)
    with pytest.raises(SkillError, match="مقترح"):
        lib.evaluate_independent("add_then_double", "1.0.0", IND, actor="agent")


def test_c14_leaked_author_cases_rejected(ctx):
    from skills import SkillError
    lib = _lib(ctx)
    _ready(lib)
    leaked = [{"inputs": {"a": 2, "b": 3}, "expect": 10}, IND[0]]
    with pytest.raises(SkillError, match="تسرب"):
        lib.evaluate_independent("add_then_double", "1.0.0", leaked, actor="owner")


def test_c15_semantic_with_same_family_judge_blocks_approval(ctx):
    from skills import SkillError
    lib = _lib(ctx)
    _ready(lib)
    cases = [{**IND[0], "criteria": SEM}, IND[1]]
    out = lib.evaluate_independent("add_then_double", "1.0.0", cases, actor="owner",
                                   judge=_jd(OK, "qwen2.5:7b", "qwen2.5:3b"))
    assert out["state"] == "failed_independent_eval"
    assert out["results"][0]["verdict"]["status"] == "not_independent"
    with pytest.raises(SkillError):
        lib.approve("add_then_double", "1.0.0", actor="owner")


def test_c16_independent_judge_pass_enables_approval_with_audit(ctx):
    reg, fc, _ = ctx
    lib = _lib(ctx)
    _ready(lib)
    cases = [{**IND[0], "criteria": SEM + [{"id": "is_12", "type": "equals", "value": 12}]},
             IND[1]]
    out = lib.evaluate_independent("add_then_double", "1.0.0", cases, actor="owner",
                                   judge=_jd(OK))
    assert out["state"] == "independently_evaluated" and out["judge"]["independent"]
    lib.approve("add_then_double", "1.0.0", actor="owner")
    assert "skill.add_then_double" in {t["name"] for t in reg.list_tools()}
    ev = [p for t, p in fc.events if p.get("op") == "skill.evaluate_independent"]
    assert ev and ev[0]["judge_independent"] is True and ev[0]["actor"] == "owner"
    st = lib.status()["skills"][0]["versions"][0]
    assert st["independent_eval"] == "2/2"


def test_c17_tamper_after_independent_eval_refused(ctx):
    from skills import SkillError
    _, _, tmp = ctx
    lib = _lib(ctx)
    _ready(lib)
    lib.evaluate_independent("add_then_double", "1.0.0", IND, actor="owner")
    f = next((tmp / "skills").rglob("1.0.0.json"))
    d = json.loads(f.read_text(encoding="utf-8"))
    d["manifest"]["steps"][1]["inputs"]["b"] = 3
    f.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(SkillError):
        lib.approve("add_then_double", "1.0.0", actor="owner")


def test_c17b_wrong_independent_expectation_fails(ctx):
    lib = _lib(ctx)
    _ready(lib)
    bad = [IND[0], {"inputs": {"a": 1, "b": 1}, "expect": 5}]  # الصحيح 4
    out = lib.evaluate_independent("add_then_double", "1.0.0", bad, actor="owner")
    assert out["state"] == "failed_independent_eval" and out["passed"] == 1


# ===================================================================== البوابة والواجهة
def test_c18_gate_cli_exit_code_and_report(tmp_path):
    out = tmp_path / "rep.json"
    p = subprocess.run([sys.executable, "tools/gate_eval.py", "--json", str(out)],
                       cwd=REPO_ROOT, capture_output=True, text=True, timeout=600)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "orchestrator.governance" in p.stdout
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["pass"] is True and rep["report_id"]


def test_c19_api_routes(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from evaluation import api_routes

    monkeypatch.setenv("SOVEREIGN_EVAL_DIR", str(tmp_path / "ev"))
    app = FastAPI()
    app.include_router(api_routes.router)
    c = TestClient(app)
    r = c.get("/evaluation/suites")
    assert r.status_code == 200 and len(r.json()["suites"]) >= 3
    assert "independent" in r.json()["judge"]
    assert c.get("/evaluation/latest").json()["report"] is None
    assert c.post("/evaluation/run", json={}).status_code == 401
    assert c.post("/evaluation/run", json={"suites": ["nope"], "api_key": OWNER_KEY}).status_code == 422
    r = c.post("/evaluation/run", json={"suites": ["planner.holdout"], "api_key": OWNER_KEY})
    assert r.status_code == 200 and r.json()["pass"] is True
    assert c.get("/evaluation/latest").json()["report"]["report_id"] == r.json()["report_id"]
    hist = (tmp_path / "ev" / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(hist) == 1


def test_c19b_skill_independent_eval_endpoint_owner_only():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        r = client.post("/skills/evaluate_independent",
                        json={"name": "x", "version": "1", "cases": [{}, {}]})
        assert r.status_code == 401
        assert client.get("/evaluation/suites").status_code == 200


# ===================================================================== تشغيلي
@pytest.mark.operational
def test_operational_live_independent_judge():
    """حَكَم حي (EVAL_JUDGE_MODEL من عائلة غير المنفّذ) — يدويًا على الخادم."""
    j = jmod.IndependentJudge()
    ok, why = j.independence()
    assert ok, why
    v = j.evaluate("كم عدد الأحداث؟", "عدد الأحداث 152413", {"total_events": 152413}, SEM)
    assert v["status"] == "judged", v
