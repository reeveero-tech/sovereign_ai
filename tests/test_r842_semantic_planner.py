# -*- coding: utf-8 -*-
"""اختبارات R-842 — المخطط الدلالي واختيار الأدوات الموجّه بالعقل.

المنهجية: مجموعتا تقييم — dev (ضُبط عليها المرتِّب) و holdout (جُمِّدت
ببصمة sha256 قبل كتابة أي سطر من المرتِّب ولم يُضبط عليها). كل حارس
على العقل يُثبت بعقل مزيف حتمي؛ العقل الحي اختبار تشغيلي منفصل.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

try:
    from agent_orchestrator import (planner, planning_eval, runtime, schemas,
                                    semantic_planner as sp, tool_registry)
    from agent_orchestrator import api_routes
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.agent_orchestrator import (planner, planning_eval, runtime,
                                            schemas, semantic_planner as sp,
                                            tool_registry)
    from backend.agent_orchestrator import api_routes

from test_agent_orchestrator import make_env, submit  # noqa: E402  عدة R-841 نفسها

# أرضية المجموعة المعزولة المقيسة بصدق في أول تشغيل (20/20) — الهبوط تراجع
HOLDOUT_FLOOR = 0.90
CATEGORIES = {"repo_read", "issue_create", "table_select", "services_list",
              "register_spec", "multi", "abstain"}


def sem(utt):
    return {"utterance": utt, "intent": {"label": "request"}, "entities": [],
            "references": [], "ambiguities": [], "languages": ["ar"],
            "user_lang": "ar"}


def brain_planner(brain_fn, mode="brain"):
    reg = tool_registry.seed_registry()
    return planner.Planner(reg, brain_fn=brain_fn, planner_mode=mode)


def req(utt, perms=("orchestrator:write",)):
    return schemas.new_request(user_id="u", session_id="s", utterance=utt,
                               permissions=list(perms))


# ===================================================================== ب١
def test_b1_eval_sets_integrity_and_no_leakage():
    """ب١: سلامة مجموعتي التقييم — لا تكرار، أدوات موجودة، لا تسرب من الأمثلة."""
    reg = tool_registry.seed_registry()
    known = {t["tool_id"] for t in reg.list()}
    examples = {sp.normalize(str(ex.get("utterance", "")))
                for t in reg.list() for ex in t["examples"]}
    seen = set()
    for name, size in (("dev", 50), ("holdout", 20)):
        goals = planning_eval.load_goals(name)
        assert len(goals) == size, name
        for g in goals:
            assert g["id"] not in seen
            seen.add(g["id"])
            assert set(g["expected_tools"]) <= known, g["id"]
            assert sp.normalize(g["utterance"]) not in examples, (
                f"تسرب: {g['id']} مطابق لمثال أداة")
        if name == "dev":
            assert {g["category"] for g in goals} == CATEGORIES


# ===================================================================== ب٢-ب٤
def test_b2_dev_semantic_meets_target():
    r = planning_eval.evaluate("dev", "semantic")
    assert r["accuracy"] >= planning_eval.TARGET, r["failures"]
    assert r["abstain_accuracy"] == 1.0
    assert r["action_precision"] >= 0.95


def test_b3_semantic_beats_keyword_baseline():
    for s in ("dev", "holdout"):
        kw = planning_eval.evaluate(s, "keyword")["accuracy"]
        se = planning_eval.evaluate(s, "semantic")["accuracy"]
        assert se > kw + 0.2, (s, kw, se)


def test_b4_holdout_frozen_and_floor():
    """ب٤: المجموعة المعزولة لم تُعدّل (البصمة) ولم تهبط عن أرضيتها."""
    assert planning_eval.file_sha256("holdout") == planning_eval.HOLDOUT_SHA256
    r = planning_eval.evaluate("holdout", "semantic")
    assert r["accuracy"] >= HOLDOUT_FLOOR, r["failures"]
    assert r["abstain_accuracy"] == 1.0


# ===================================================================== ب٥
@pytest.mark.parametrize("utt", ["ما عاصمة فرنسا؟", "اكتب لي قصيدة عن البحر",
                                 "what's the weather tomorrow"])
def test_b5_out_of_scope_clarifies_without_tool_call(tmp_path, utt):
    o, ex, _ = make_env(tmp_path)
    out = submit(o, utt)
    assert out["status"] == "needs_clarification"
    assert not out.get("results")
    assert any(d["decision_type"] == "clarify" for d in out["trace"]["decisions"])


# ===================================================================== ب٦
def test_b6_new_tool_selected_by_contract_without_code_change():
    reg = tool_registry.seed_registry()
    reg.register(tool_registry.ToolDefinition(
        tool_id="stripe.invoices_list", name="قائمة فواتير Stripe",
        description="عرض الفواتير والمدفوعات في Stripe",
        connector_id="stripe", operation="invoices_list", access="read",
        risk="low", input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object"}, scopes=["billing:read"],
        idempotent=True, estimated_cost=0, estimated_time_s=1,
        examples=[{"utterance": "اعرض فواتير العملاء في سترايب"},
                  {"utterance": "list stripe invoices"}]))
    p = planner.Planner(reg, planner_mode="semantic")
    sel = p.selector.select(sem("أبي أشوف الفواتير المدفوعة"))
    assert [t.tool_id for t in sel.tools] == ["stripe.invoices_list"]


# ===================================================================== ب٧-ب١١
def test_b7_brain_valid_choice_logged_with_ranker_alternative():
    calls = []

    def brain(system, user, schema, timeout):
        calls.append(schema)
        return json.dumps({"tools": ["render.services_list"], "reason": "خدمات"})

    p = brain_planner(brain)
    plan = p.build(req("اعرض خدمات Render"), sem("اعرض خدمات Render"), "t")
    assert plan["selection"]["planner"] == "brain"
    assert plan["selection"]["brain_outcome"] == "accepted"
    assert "المرتِّب اقترح" in plan["selection"]["reason"]
    enum = calls[0]["properties"]["tools"]["items"]["enum"]
    assert "none" in enum and "render.services_list" in enum


def test_b8_brain_hallucinated_tool_rejected():
    p = brain_planner(lambda *a: json.dumps({"tools": ["aws.s3_delete"], "reason": "x"}))
    sel = p.selector.select(sem("اعرض خدمات Render"))
    assert sel.planner == "semantic_fallback"
    assert sel.brain_outcome.startswith("rejected_unknown_tool")
    assert [t.tool_id for t in sel.tools] == ["render.services_list"]


@pytest.mark.parametrize("brain", [
    lambda *a: None,
    lambda *a: "{not json",
    lambda *a: json.dumps({"tools": "render.services_list"}),
    lambda *a: (_ for _ in ()).throw(TimeoutError("بطيء")),
])
def test_b9_brain_failures_fall_back_no_crash(brain):
    p = brain_planner(brain)
    sel = p.selector.select(sem("اعرض خدمات Render"))
    assert sel.planner == "semantic_fallback"
    assert [t.tool_id for t in sel.tools] == ["render.services_list"]


def test_b10_brain_cannot_bypass_gates_or_inject_inputs(tmp_path):
    """ب١٠: العقل يختار الأداة فقط — الموافقة والمدخلات من الحوكمة والنص."""
    o, _, _ = make_env(tmp_path)
    o.planner = planner.Planner(o.tools, planner_mode="brain", brain_fn=lambda *a: json.dumps(
        {"tools": ["github.issue_create"], "reason": "x",
         "inputs": {"owner": "evil", "repo": "pwn"}}))
    out = submit(o, "افتح مشكلة بعنوان عطل في github.com/acme/webapp")
    assert out["status"] == "pending_approval"
    step = out["plan"]["steps"][0]
    assert step["requires_approval"] is True
    assert step["inputs"]["owner"] == "acme"
    # بلا صلاحية كتابة: البوابة ترفض رغم اختيار العقل
    o2, _, _ = make_env(tmp_path / "b")
    o2.planner = o.planner
    out2 = submit(o2, "افتح مشكلة بعنوان عطل في github.com/acme/webapp",
                  permissions=())
    assert out2["status"] in ("denied", "failed", "blocked")
    assert out2["status"] != "completed"


def test_b10b_brain_cannot_escalate_read_to_write():
    p = brain_planner(lambda *a: json.dumps({"tools": ["github.issue_create"], "reason": "x"}))
    sel = p.selector.select(sem("حلل مستودع github.com/acme/webapp"))
    assert sel.brain_outcome.startswith("rejected_access_escalation")
    assert [t.tool_id for t in sel.tools] == ["github.repo_read"]


def test_b11_brain_pick_without_evidence_rejected(monkeypatch):
    p = brain_planner(lambda *a: json.dumps({"tools": ["supabase.table_select"], "reason": "x"}))
    # قائمة مختصرة واسعة تحاكي أسوأ حالة: الأداة متاحة للعقل لكن بلا دليل نصي
    monkeypatch.setattr(p.selector, "_shortlist",
                        lambda text, k=4: p.selector.ranker._active())
    sel = p.selector.select(sem("اعرض خدمات Render"))
    assert sel.brain_outcome.startswith("rejected_no_evidence")
    assert [t.tool_id for t in sel.tools] == ["render.services_list"]


def test_b12_brain_prompt_has_no_secrets(tmp_path):
    o, _, _ = make_env(tmp_path)
    o.planner = planner.Planner(o.tools, planner_mode="brain",
                                brain_fn=lambda *a: None)
    submit(o, "حلل مستودع github.com/acme/webapp")
    prompt = o.planner.selector.last_prompt
    assert prompt and "github.com/acme/webapp" in prompt
    for secret in ("gh_test_token", "sb_test_key", "rnd_test_key", "oa_test_key",
                   "test_master_key"):
        assert secret not in prompt
    assert not re.search(r"(ghp_|rnd_|sbp_)[A-Za-z0-9]{8,}", prompt)


# ===================================================================== ب١٣-ب١٤
def test_b13_sequenced_clauses_order_and_write_needs_approval(tmp_path):
    o, _, _ = make_env(tmp_path)
    out = submit(o, "اعرض خدمات Render ثم افتح مشكلة بعنوان تقرير في github.com/acme/webapp")
    ids = [s["tool_id"] for s in out["plan"]["steps"]]
    assert ids == ["render.services_list", "github.issue_create"]
    assert out["plan"]["steps"][1]["requires_approval"] is True
    assert out["status"] == "pending_approval"


def test_b14_selection_explainable_and_schema_valid(tmp_path):
    o, _, _ = make_env(tmp_path)
    out = submit(o, "اعرض صفوف جدول users")
    sel = out["plan"]["selection"]
    assert sel["chosen"] == ["supabase.table_select"]
    assert sel["scores"]["supabase.table_select"] > 0
    assert 0 <= sel["confidence"] <= 1
    schemas.validate(out["plan"], schemas.PLAN_SCHEMA)
    tc = [d for d in out["trace"]["decisions"]
          if d["decision_type"] == "tool_choice" and d["chosen"] == "supabase.table_select"]
    assert tc and tc[0]["rejected"], "قرار الاختيار يسجل البدائل"


# ===================================================================== ب١٥
def test_b15_invalid_entity_pattern_rejected_at_registration():
    reg = tool_registry.seed_registry()
    with pytest.raises(tool_registry.ToolRegistryError):
        reg.register(tool_registry.ToolDefinition(
            tool_id="x.bad", name="x", description="أداة اختبار", connector_id="x",
            operation="bad", access="read", risk="low",
            input_schema={"type": "object"}, output_schema={"type": "object"},
            scopes=[], idempotent=True, estimated_cost=0, estimated_time_s=1,
            entity_patterns=["(unclosed"]))


# ===================================================================== ب١٦
def test_b16_planner_eval_api(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(api_routes.router)
    c = TestClient(app)
    r = c.get("/orchestrator/planner/eval", params={"set": "dev", "mode": "semantic"})
    assert r.status_code == 200 and r.json()["accuracy"] >= 0.9
    assert c.get("/orchestrator/planner/eval", params={"mode": "brain"}).status_code == 422
    assert c.get("/orchestrator/planner/eval", params={"set": "x"}).status_code == 422
    assert c.post("/orchestrator/planner/eval", json={"mode": "brain"}).status_code == 401
    r = c.post("/orchestrator/planner/eval", json={
        "set": "holdout", "mode": "keyword",
        "api_key": "test_master_key_1234567890abcdef"})
    assert r.status_code == 200 and r.json()["set"] == "holdout"


# ===================================================================== تشغيلي
@pytest.mark.operational
def test_operational_live_brain_eval():
    """العقل الحي (Ollama) على dev — يُشغَّل يدويًا على الخادم فقط."""
    r = planning_eval.evaluate("dev", "brain", brain_fn=sp.default_brain_fn)
    assert r["brain_outcomes"].get("accepted", 0) > 0, r["brain_outcomes"]
    assert r["accuracy"] >= planning_eval.TARGET, r["failures"]
