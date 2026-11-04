# -*- coding: utf-8 -*-
"""R-850 (٦.٥.١): أول مهارات حقيقية — تقرير صحة / تلخيص سجل / موجز بحثي.

يغطي: عقد التقييم البنيوي (مسار/نوع/مفاتيح/غير فارغ) للقيم الحية، معايير
المؤلف الحتمية فقط، المفتاح الديناميكي بمدخل، نافذة السجل بلا حمولة،
الكتالوج (قراءة/اقتراح بلا تفعيل ذاتي) ونقاط الواجهة والمجموعة المجمّدة.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_skills import ctx, _manifest  # noqa: E402,F401  عدة R-757 نفسها


# ===================================================================== الحَكَم البنيوي
def test_r850_path_criteria_and_new_types():
    from evaluation.judge import check_deterministic as c
    out = {"a": {"b": [1, {"k": "v"}]}, "n": 3, "f": False, "s": ""}
    assert c({"id": "x", "type": "equals", "path": "a.b.1.k", "value": "v"}, out)["pass"]
    assert c({"id": "x", "type": "has_keys", "value": ["a", "n"]}, out)["pass"]
    assert not c({"id": "x", "type": "has_keys", "value": ["zz"]}, out)["pass"]
    assert c({"id": "x", "type": "non_empty", "path": "a.b"}, out)["pass"]
    assert not c({"id": "x", "type": "non_empty", "path": "s"}, out)["pass"]
    assert c({"id": "x", "type": "is_type", "path": "n", "value": "int"}, out)["pass"]
    assert not c({"id": "x", "type": "is_type", "path": "f", "value": "int"}, out)["pass"]
    assert c({"id": "x", "type": "is_type", "path": "f", "value": "bool"}, out)["pass"]
    miss = c({"id": "x", "type": "contains", "path": "a.q", "value": "v"}, out)
    assert miss["pass"] is False and miss["reason"] == "missing_path"


def test_r850_old_criteria_unchanged_without_path():
    from evaluation.judge import check_deterministic as c
    r = c({"id": "x", "type": "contains", "value": "طوكيو"}, {"p": ["طوكيو"]})
    assert r == {"id": "x", "type": "contains", "by": "app", "pass": True}


@pytest.mark.parametrize("bad", [
    {"id": "x", "type": "equals", "path": "a..b", "value": 1},
    {"id": "x", "type": "has_keys", "value": []},
    {"id": "x", "type": "has_keys", "value": "a"},
    {"id": "x", "type": "is_type", "value": "tuple"},
    {"id": "x", "type": "semantic", "path": "a", "text": "نص دلالي واضح"},
])
def test_r850_invalid_criteria_rejected(bad):
    from evaluation.judge import validate_criteria, CriterionError
    with pytest.raises(CriterionError):
        validate_criteria([bad])


# ===================================================================== المكتبة
def test_r850_author_criteria_case_evaluated(ctx):
    from skills import SkillLibrary
    reg, _, tmp = ctx
    lib = SkillLibrary(tmp / "skills", reg, durable=False)
    m = _manifest()
    m["output"] = {"v": "{{steps.1.product}}"}
    m["eval"]["cases"] = [
        {"inputs": {"a": 2, "b": 3}, "criteria": [
            {"id": "t", "type": "is_type", "path": "v", "value": "int"}]},
        {"inputs": {"a": 1, "b": 1}, "expect": {"v": 4}, "criteria": [
            {"id": "e", "type": "equals", "path": "v", "value": 4}]},
    ]
    lib.propose(m, actor="agent")
    ev = lib.evaluate("add_then_double", "1.0.0")
    assert ev["state"] == "evaluated" and ev["passed"] == 2
    assert ev["results"][0]["criteria"][0]["pass"] is True


def test_r850_author_criteria_failure_blocks(ctx):
    from skills import SkillLibrary
    reg, _, tmp = ctx
    lib = SkillLibrary(tmp / "skills", reg, durable=False)
    m = _manifest()
    m["eval"]["cases"] = [{"inputs": {"a": 2, "b": 3}, "criteria": [
        {"id": "t", "type": "is_type", "value": "str"}]}]
    lib.propose(m, actor="agent")
    assert lib.evaluate("add_then_double", "1.0.0")["state"] == "failed_eval"


def test_r850_semantic_and_empty_cases_rejected():
    import skills
    m = _manifest()
    m["eval"]["cases"] = [{"inputs": {"a": 1, "b": 1}, "criteria": [
        {"id": "s", "type": "semantic", "text": "نص دلالي واضح للحكم"}]}]
    with pytest.raises(skills.SkillError):
        skills.validate(m)
    m["eval"]["cases"] = [{"inputs": {"a": 1, "b": 1}}]
    with pytest.raises(skills.SkillError):
        skills.validate(m)


def test_r850_dynamic_key():
    import skills
    hist = [{"result": {"c": {"a": {"status": "ok"}}}}]
    assert skills._lookup("steps.0.c.$k", {"k": "a"}, hist) == {"status": "ok"}
    with pytest.raises(skills.SkillError):
        skills._lookup("steps.0.c.$k", {"k": "nope"}, hist)
    with pytest.raises(skills.SkillError):
        skills._lookup("steps.0.c.$k", {}, hist)


def test_r850_catalog_loads_three_valid():
    import skills
    cat = skills.load_catalog()
    assert [m["name"] for m in cat] == ["health_report", "ledger_digest", "research_brief"]
    for m in cat:
        assert all(not p.startswith(("skills.", "skill.", "agent.run", "tasks."))
                   for p in m["permissions"])
        assert len(m["eval"]["cases"]) >= 2


# ===================================================================== نافذة السجل
def test_r850_ledger_view_metadata_only():
    import ledger_view
    from evaluation.real_skills import FakeCore
    out = ledger_view.recent(FakeCore(), 4)
    assert out["count"] == 4 and out["chain_linked"] is True and out["chain_links"] == 3
    assert all(set(e) == {"time", "type", "hash"} for e in out["events"])
    assert "SIG" not in json.dumps(out) and "payload" not in json.dumps(out)


def test_r850_ledger_view_empty_core():
    import ledger_view

    class Empty:
        def iterate_events(self, reverse=False, limit=None):
            return iter(())
    out = ledger_view.recent(Empty(), 5)
    assert out["count"] == 0 and out["newest"] is None and out["chain_links"] == 0


# ===================================================================== الواجهة
def test_r850_catalog_endpoint_and_tools(ctx, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import app as app_mod
    import skills as skills_mod
    from tool_registry import get_registry
    reg, _, _ = ctx
    lib = skills_mod.SkillLibrary(tmp_path / "lib", reg, durable=False)
    monkeypatch.setattr(skills_mod, "get_library", lambda: lib)
    with TestClient(app_mod.app) as client:
        r = client.get("/skills/catalog")
        assert r.status_code == 200 and r.json()["count"] == 3
        assert {s["state"] for s in r.json()["skills"]} == {"not_proposed"}
        assert client.post("/skills/catalog/propose",
                           json={"name": "health_report"}).status_code == 401
        assert client.post("/skills/catalog/propose",
                           json={"name": "health_report",
                                 "api_key": f"k_{uuid.uuid4().hex}"}).status_code == 401
    names = {t["name"] for t in get_registry().list_tools()}
    assert {"ledger.recent", "skills.catalog"} <= names


def test_r850_catalog_propose_with_owner(ctx, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import app as app_mod
    import skills as skills_mod
    from evaluation.real_skills import _reg
    lib = skills_mod.SkillLibrary(tmp_path / "lib", _reg(), durable=False)
    monkeypatch.setattr(skills_mod, "get_library", lambda: lib)
    monkeypatch.setattr(app_mod, "verify_api_key", lambda k: True)
    with TestClient(app_mod.app) as client:
        r = client.post("/skills/catalog/propose",
                        json={"name": "ledger_digest", "api_key": f"k_{uuid.uuid4().hex}"})
        assert r.status_code == 200 and r.json()["state"] == "evaluated", r.text
        assert client.post("/skills/catalog/propose",
                           json={"name": "missing_skill", "api_key": "x"}).status_code == 400
    assert "skill.ledger_digest" not in {t["name"] for t in lib.registry.list_tools()}


def test_r850_ledger_tool_rejects_bad_limit():
    from fastapi.testclient import TestClient
    import app as app_mod
    from tool_registry import get_registry
    with TestClient(app_mod.app):
        res = get_registry().invoke("ledger.recent", caller="owner", inputs={"limit": 99})
        assert res["ok"] is False


# ===================================================================== المجموعة المجمّدة
def test_r850_suite_registered_and_green():
    from evaluation import suites
    s = suites.get("skills.catalog")
    assert s.floor == 1.0 and s.data_path.name == "real_skills_cases.json"
    assert suites.file_sha256(s.data_path) == \
        "bb15856045644baa8c6534ea266ecad33202937cda099ce1d4ea7f5cf5e794ab"
    r = s.runner(s.data_path)
    assert r["score"] == 1.0 and r["n"] == 18, r["failures"]
