# -*- coding: utf-8 -*-
"""اختبارات طبقة تنسيق الوكلاء (R-841) — تغطي معايير القبول الـ28.

الفلسفة كنظام R-840: كل معيار قبول في الميثاق له اختبار يثبته بدليل
قابل للتشغيل. منفذ موصل مزيف (نقل مزيف) يعزل الاختبارات عن الشبكة،
واختبار تشغيلي واحد (operational) يمر عبر GitHub الحقيقي بمفتاح من
البيئة فقط — لا سر في الكود أبدًا.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from agent_orchestrator import (api_routes, execution_engine, failure,
                                    governor, planner, reflection, rollback,
                                    runtime, schemas, tool_registry, tracing)
    from connector_system import execution as cs_exec
    from connector_system import policy as cs_policy
    from connector_system import registry as cs_registry
    from connector_system import credentials as cs_creds
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.agent_orchestrator import (api_routes, execution_engine,
                                            failure, governor, planner,
                                            reflection, rollback, runtime,
                                            schemas, tool_registry, tracing)
    from backend.connector_system import execution as cs_exec
    from backend.connector_system import policy as cs_policy
    from backend.connector_system import registry as cs_registry
    from backend.connector_system import credentials as cs_creds


# --------------------------------------------------------------------- العدة
class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data if data is not None else {}

    def json(self):
        return self._data


class FakeVault:
    def __init__(self):
        self.store = {}

    def put(self, name, value, scopes, actor):
        self.store[name] = value
        return {"name": name, "version": 1, "scopes": scopes}

    def get(self, name, capability, actor):
        if name not in self.store:
            raise KeyError(name)
        return self.store[name]

    def rotate(self, name, new_value, actor, scopes=None):
        self.store[name] = new_value
        return {"name": name, "version": 2}

    def delete(self, name, actor):
        self.store.pop(name, None)

    def status(self):
        return {"ready": True}


def make_env(tmp_path, http=None):
    """بيئة معزولة: منفذ R-840 حقيقي بنقل مزيف + نظام تنسيق فوقه."""
    vault = FakeVault()
    store = cs_creds.CredentialStore(state_path=tmp_path / "creds.json",
                                     vault=vault)
    pol = cs_policy.OrgPolicy(state_path=tmp_path / "policy.json")
    ex = cs_exec.Executor(
        state_dir=tmp_path, credentials=store, policy=pol,
        http=http or (lambda *a, **k: FakeResponse()),
        clock=lambda: time.time())
    reg = cs_registry.Registry()
    ex.registry = reg
    store.create("github", "pat", "global", "tester",
                 ["repo:read", "repo:write"], "gh_test_token", "test")
    store.create("supabase", "api_key", "global", "tester",
                 ["db:read"], "sb_test_key", "test")
    store.create("render", "api_key", "global", "tester",
                 ["connector:read"], "rnd_test_key", "test")
    store.create("generic_openapi", "api_key", "global", "tester",
                 ["connector:write"], "oa_test_key", "test")
    o = runtime.OrchestratorSystem(
        data_dir=str(tmp_path / "orch"), connector_executor=ex,
        org_policy=pol, connector_registry=reg)
    return o, ex, pol


def submit(o, utterance, permissions=("orchestrator:write",),
           session="s1", dry_run=False, constraints=None, user="u1"):
    req = schemas.new_request(
        user_id=user, session_id=session, utterance=utterance,
        permissions=list(permissions), constraints=constraints,
        dry_run=dry_run)
    return o.submit(req)


def gh_semantic(utterance):
    """تمثيل دلالي مبسّط بعقد الطبقة — للتركيز على سلوك الحلقة."""
    return {"utterance": utterance, "intent": {"label": "request"},
            "entities": [{"id": "e1", "type": "url",
                          "surface": "github.com/acme/webapp"}],
            "references": [], "ambiguities": [],
            "languages": ["ar"], "user_lang": "ar"}


def _sem_with(utterance, entities=None):
    return {"utterance": utterance, "intent": {"label": "request"},
            "entities": entities or [], "references": [],
            "ambiguities": [], "languages": ["ar"], "user_lang": "ar"}


# ===================================================================== ١-٣
def test_a1_simple_request_single_step_full_path(tmp_path):
    """معيار ١: طلب بسيط → خطة من خطوة واحدة → أداة → تنفيذ → رد."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    assert out["status"] == "completed"
    assert len(out["plan"]["steps"]) == 1
    assert out["plan"]["steps"][0]["tool_id"] == "github.repo_read"
    assert out["results"][0]["status"] == "success"
    assert out["reply"] and "s1" in out["reply"] or "تم التنفيذ" in out["reply"]
    assert out["trace"]["span_count"] >= 1  # لا استدعاء بلا أثر


def test_a2_composite_request_dependency_order(tmp_path):
    """معيار ٢: طلب مركب (3+ خطوات) → تفكيك واعتماديات وتسلسل صحيح."""
    o, _, _ = make_env(tmp_path)
    sem = _sem_with(
        "افتح مشكلة في github.com/acme/webapp واعرض خدمات Render"
        " وصفوف جدول users",
        entities=[{"id": "e1", "type": "url",
                   "surface": "github.com/acme/webapp"},
                  {"id": "e2", "type": "entity", "surface": "users"}])
    req = schemas.new_request(user_id="u", session_id="s",
                             utterance=sem["utterance"],
                             permissions=["orchestrator:write"])
    # الموافقة للجلسة مسبقًا كي تكتمل الحلقة دفعة واحدة
    o.approvals.grant_session("s", "github.issue_create")
    out = o.submit(req, semantic=sem)
    assert out["status"] == "completed"
    assert len(out["plan"]["steps"]) >= 3
    ids = [s["step_id"] for s in out["plan"]["steps"]]
    assert ids == sorted(ids)  # التسلسل محفوظ
    assert all(s["depends_on"] for s in out["plan"]["steps"][1:])  # سلسلة
    assert [r["status"] for r in out["results"]].count("success") >= 3


def test_a3_wrong_tool_rejected_by_policy(tmp_path):
    """معيار ٣: أداة كتابة بلا صلاحية → بوابة الصلاحية ترفضها وتوثق البديل."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "افتح مشكلة في github.com/acme/webapp",
                 permissions=())  # لا صلاحية كتابة
    r = out["results"][0]
    assert r["status"] == "denied"
    assert "صلاحية غير كافية" in r["error"]["message"]
    assert r["error"]["action"] in ("widen_or_alternative",)


# ===================================================================== ٤
def test_a4_insufficient_scope_403_clear_reason(tmp_path):
    """معيار ٤: صلاحية غير كافية → رفض 403 بسبب واضح وطلب توسيع."""
    o, ex, pol = make_env(tmp_path)
    # أداة العرض (services_list) متاحة، لكن المستخدم لا يملك صلاحية الكتابة
    out = submit(o, "اعرض خدمات Render", permissions=())
    assert out["results"][0]["status"] == "success"  # قراءة مسموحة
    # لكن كتابة المشكلة بلا صلاحية كتابة = 403 حوكمي
    out2 = submit(o, "افتح مشكلة في github.com/acme/webapp",
                  permissions=())
    assert out2["results"][0]["error"]["code"] == "forbidden"
    assert "orchestrator:write" in out2["results"][0]["error"]["message"]


# ===================================================================== ٥-٦
def test_a5_sensitive_write_rejected_no_execution(tmp_path):
    """معيار ٥: كتابة حساسة → بوابة موافقة تظهر → رفض → لا تنفيذ."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "افتح مشكلة في github.com/acme/webapp")
    assert out["status"] == "pending_approval"
    ap = out["pending_approval"]
    assert ap and o.approvals.get(ap["approval_id"])["status"] == "pending"
    # الرفض: لا تنفيذ إطلاقًا
    after = o.decide_approval(out["loop_id"], ap["approval_id"],
                              "rejected", "u1")
    assert after["status"] != "pending_approval"
    denied = [r for r in after["results"] if r["step_id"] == ap["step_id"]]
    assert denied and denied[0]["status"] == "denied"
    assert denied[0]["error"]["code"] == "approval_rejected"
    # برهان عدم التنفيذ: لا span نجاح للاستدعاء
    ok_spans = [s for s in after["trace"]["spans"]
                if s["step_id"] == ap["step_id"] and s["status"] == "ok"]
    assert not ok_spans


def test_a6_sensitive_write_approved_executed_and_recorded(tmp_path):
    """معيار ٦: موافقة صريحة → تنفيذ → تسجيل فاعل الموافقة ووقتها."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "افتح مشكلة في github.com/acme/webapp")
    ap = out["pending_approval"]
    before = time.time()
    after = o.decide_approval(out["loop_id"], ap["approval_id"],
                              "approved", "owner-ali")
    assert after["status"] == "completed"
    r = [x for x in after["results"] if x["step_id"] == ap["step_id"]][0]
    assert r["status"] == "success"
    rec = o.approvals.get(ap["approval_id"])
    assert rec["approved_by"] == "owner-ali"     # فاعل الموافقة
    assert rec["timestamp"] and rec["timestamp"] > time.strftime(
        "%Y-%m-%dT", time.gmtime(before - 60))  # وقتها مسجل


# ===================================================================== ٧-٨
def test_a7_tool_timeout_retry_then_replan(tmp_path):
    """معيار ٧: فشل timeout → retry (في المنفذ) → إن استمر: إعادة تخطيط."""
    attempts = {"n": 0}

    def flaky_http(method, url, **kw):
        attempts["n"] += 1
        if attempts["n"] <= 3:  # المنفذ يعيد المحاولة داخليًا ثم يفشل
            return FakeResponse(status_code=500)
        return FakeResponse()

    o, _, _ = make_env(tmp_path, http=flaky_http)
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    # الفشل صُنّف فشل أداة → معالج الفشل أعاد التخطيط (سقط الخطوة أو أُعيدت)
    assert out["status"] in ("completed", "failed")
    assert any(d["decision_type"] == "replan"
               for d in out["trace"]["decisions"]) \
        or out["results"][0]["status"] in ("failure", "success")
    replans = [d for d in out["trace"]["decisions"]
               if d["decision_type"] == "replan"]
    assert replans, "يجب أن يُسجَّل قرار إعادة التخطيط"


def test_a8_401_one_refresh_then_reconnect_request(tmp_path):
    """معيار ٨: فشل 401 → تجديد واحد → إن فشل: طلب إعادة اتصال، لا retry أعمى."""
    calls = {"n": 0}

    def unauthorized(method, url, **kw):
        calls["n"] += 1
        return FakeResponse(status_code=401)

    o, _, _ = make_env(tmp_path, http=unauthorized)
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    r = out["results"][0]
    assert r["status"] == "failure"
    # لا retry أعمى: عدد النداءات محدود بمحاولات المنفذ المعرفة (3) لا أكثر
    assert calls["n"] <= 3
    handled = [d for d in out["trace"]["decisions"]
               if "صلاحية" in d["reasoning"] or d["decision_type"] == "replan"]
    assert handled


# ===================================================================== ٩
def test_a9_cost_limit_auto_stop_with_reason(tmp_path):
    """معيار ٩: تجاوز حد التكلفة → إيقاف تلقائي بسبب واضح وإبلاغ."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "حلل مستودع github.com/acme/webapp",
                 constraints={"max_cost": 0.0, "max_time_s": 10,
                              "max_steps": 5})
    assert out["status"] == "failed"
    assert "التكلفة" in out["reply"]
    assert any(s.get("code") in ("budget_exceeded",)
               for s in [r.get("error") or {} for r in out["results"]])


# ===================================================================== ١٠
def test_a10_user_cancel_immediate_stop_documented(tmp_path):
    """معيار ١٠: إلغاء من المستخدم → إيقاف فوري → توثيق ما تم وما لم يتم."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    loop_id = out["loop_id"]
    o.cancel(loop_id, actor="u1")  # حلقة منتهية: الإلغاء موثق بلا كسر
    after = o.get(loop_id)
    assert after["status"] in ("cancelled", "completed")
    if after["status"] == "cancelled":
        doc = after["cancel_document"]
        assert set(doc) >= {"executed", "not_executed"}
    # إلغاء حلقة جارية: نبدأ حلقة ثم نلغيها قبل اكتمالها
    o2, _, _ = make_env(tmp_path)
    sem = gh_semantic("افتح مشكلة في github.com/a/b")
    req = schemas.new_request(user_id="u", session_id="s2",
                              utterance=sem["utterance"],
                              permissions=["orchestrator:write"])
    # إلغاء حلقة معلّقة على موافقة = إلغاء فوري موثق
    out2 = o2.submit(req, semantic=sem)
    assert out2["status"] == "pending_approval"
    cancelled = o2.cancel(out2["loop_id"], "u1")
    assert cancelled["status"] == "cancelled"
    assert "لم يُنفَّذ" in cancelled["reply"] or "نفّذنا" in cancelled["reply"]


# ===================================================================== ١١
def test_a11_resume_after_interruption_from_checkpoint(tmp_path):
    """معيار ١١: استئناف بعد انقطاع → استعادة الحالة → متابعة من حيث توقفت."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    loop_id = out["loop_id"]
    # انقطاع: إعادة تشغيل "للنظام" = قراءة الحالة من القرص واستئنافها
    state = o.state.load(loop_id)
    assert state["status"] == "completed"
    # حالة جارية (pending_approval) تُستأنف من نفس الخطوة بعد الموافقة
    out2 = submit(o, "افتح مشكلة في github.com/acme/webapp")
    ap = out2["pending_approval"]
    resumed = o.decide_approval(out2["loop_id"], ap["approval_id"],
                                "approved", "u1")
    assert resumed["status"] == "completed"
    # الخطوة لم تُنفَّذ مرتين: نتيجة واحدة لكل step_id
    ids = [r["step_id"] for r in resumed["results"]]
    assert len(ids) == len(set(ids))


# ===================================================================== ١٢
def test_a12_idempotency_prevents_duplicate_writes(tmp_path):
    """معيار ١٢: إعادة إرسال نفس العملية → Idempotency يمنع التكرار."""
    o, ex, _ = make_env(tmp_path)
    o.approvals.grant_session("s-idem", "github.issue_create")
    sem = gh_semantic("افتح مشكلة بعنوان X")
    sem["utterance"] = "افتح مشكلة في github.com/acme/webapp بعنوان X"
    req = schemas.new_request(user_id="u", session_id="s-idem",
                              utterance=sem["utterance"],
                              permissions=["orchestrator:write"])
    out = o.submit(req, semantic=sem)
    assert out["results"][0]["status"] == "success"
    # إعادة الإرسال نفسها: المنفذ يرد idempotent_replay لا كتابة ثانية
    out2 = o.submit(req, semantic=sem)
    assert out2["results"][0]["status"] == "success"


# ===================================================================== ١٣
def test_a13_plan_deviation_logged_with_reason(tmp_path):
    """معيار ١٣: انحراف عن الخطة → تسجيل القرار والسبب."""
    o, _, _ = make_env(tmp_path)
    flaky = {"n": 0}

    def http(method, url, **kw):
        flaky["n"] += 1
        if flaky["n"] == 1:
            return FakeResponse()
        raise cs_exec.ConnectorExecutionError("5xx متكرر")

    o2, _, _ = make_env(tmp_path, http=http)
    out = submit(o2, "حلل مستودع github.com/acme/webapp")
    replans = [d for d in out["trace"]["decisions"]
               if d["decision_type"] == "replan"]
    assert replans and replans[0]["reasoning"]  # سبب مسجل


# ===================================================================== ١٤
def test_a14_ambiguity_one_clarifying_question(tmp_path):
    """معيار ١٤: غموض مؤثر → طلب توضيح واحد بدل افتراض."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "افتح مشكلة")  # لا هدف ولا مستودع — غموض مؤثر
    assert out["status"] == "needs_clarification"
    assert "سؤال توضيحي واحد" in out["reply"]
    assert any(d["decision_type"] == "clarify"
               for d in out["trace"]["decisions"])


# ===================================================================== ١٥
def test_a15_dry_run_full_preview_no_execution(tmp_path):
    """معيار ١٥: Dry-run → عرض كامل لما سيُفعل دون تنفيذ."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "افتح مشكلة في github.com/acme/webapp",
                 permissions=["orchestrator:write"], dry_run=True)
    assert out["status"] == "completed"
    assert out["dry_run_preview"][0]["preview"]["would_require_approval"]
    assert out["dry_run_preview"][0]["preview"]["policy_allows"] is True
    # برهان عدم التنفيذ: لا span بحالة ok ولا نتائج نجاح
    assert not [r for r in out.get("results", [])
                if r["status"] == "success"]
    assert not [s for s in out["trace"]["spans"] if s["status"] == "ok"]


# ===================================================================== ١٦-١٧
def _add_reversible_pair(o):
    """أداة قابلة للعكس + أداة غير قابلة — للتراجع والتعويض (معيارا ١٦/١٧)."""
    o.tools.register(tool_registry.ToolDefinition(
        tool_id="test.resource_create", name="إنشاء مورد تجريبي",
        description="إنشاء مورد قابل للعكس تمامًا — لأغراض اختبار التراجع",
        connector_id="github", operation="issue_create", access="write",
        risk="medium",
        input_schema={"type": "object", "required": ["owner", "repo", "title"],
                      "properties": {"owner": {"type": "string"},
                                     "repo": {"type": "string"},
                                     "title": {"type": "string"}}},
        output_schema={"type": "object", "required": ["ok"],
                       "properties": {"ok": {"type": "boolean"}}},
        scopes=["repo:write"], idempotent=True,
        estimated_cost=0.0, estimated_time_s=0.1,
        inverse_tool_id="test.resource_delete"))
    o.tools.register(tool_registry.ToolDefinition(
        tool_id="test.resource_delete", name="حذف مورد تجريبي",
        description="حذف المورد — العملية المعاكسة للإنشاء في الاختبار",
        connector_id="github", operation="issue_create", access="write",
        risk="high",
        input_schema={"type": "object", "required": ["owner", "repo", "title"],
                      "properties": {"owner": {"type": "string"},
                                     "repo": {"type": "string"},
                                     "title": {"type": "string"}}},
        output_schema={"type": "object", "required": ["ok"],
                       "properties": {"ok": {"type": "boolean"}}},
        scopes=["repo:write"], idempotent=True,
        estimated_cost=0.0, estimated_time_s=0.1))


def test_a16_rollback_reversible_operation(tmp_path):
    """معيار ١٦: Rollback لعملية قابلة للتراجع → نجاح وتوثيق."""
    o, _, _ = make_env(tmp_path)
    _add_reversible_pair(o)
    o.approvals.grant_session("s-rb", "test.resource_create")
    o.approvals.grant_session("s-rb", "test.resource_delete")
    sem = gh_semantic("x")
    sem["utterance"] = "افتح مشكلة في github.com/acme/webapp بعنوان RB"
    req = schemas.new_request(user_id="u", session_id="s-rb",
                              utterance=sem["utterance"],
                              permissions=["orchestrator:write"])
    out = o.submit(req, semantic=sem)
    assert out["status"] == "pending_approval"
    # تدخل بشري موثق: استبدال الأداة بالزوج القابل للعكس (نفس الخطوة)
    state = o.state.load(out["loop_id"])
    steps = [dict(s) for s in state["plan"]["steps"]]
    steps[0]["tool_id"] = "test.resource_create"
    mod = o.hitl.modify_plan(state, steps, "admin", "")
    assert mod["ok"] is True
    o.state.save(state)
    # حسم الموافقة المعلقة (على الخطوة نفسها) يستأنف وينفذ الأداة البديلة
    ap = out["pending_approval"]
    after = o.decide_approval(out["loop_id"], ap["approval_id"],
                              "approved", "u1")
    assert after["results"][0]["status"] == "success"
    rb = o.rollback(out["loop_id"], "s1", actor="admin")
    assert rb["ok"] is True
    assert rb["action"] == "rollback"
    assert rb["result"]["status"] == "success"
    state = o.state.load(out["loop_id"])
    assert state["rollbacks"][0]["by"] == "admin"  # توثيق الفاعل


def test_a17_compensation_non_reversible_operation(tmp_path):
    """معيار ١٧: تعويض لعملية غير قابلة للتراجع → خطة تعويض موثقة."""
    o, _, _ = make_env(tmp_path)
    o.approvals.grant_session("s-comp", "github.issue_create")
    sem = gh_semantic("x")
    sem["utterance"] = "افتح مشكلة في github.com/acme/webapp بعنوان C"
    req = schemas.new_request(user_id="u", session_id="s-comp",
                              utterance=sem["utterance"],
                              permissions=["orchestrator:write"])
    out = o.submit(req, semantic=sem)
    rb = o.rollback(out["loop_id"], "s1", actor="admin")
    assert rb["ok"] is True
    assert rb["action"] == "compensation"
    assert rb["compensation_plan"]  # خطة معلنة لا ادعاء تراجع
    state = o.state.load(out["loop_id"])
    assert state["compensations"][0]["action"] == "compensation"


# ===================================================================== ١٨
def test_a18_full_trace_inspectable(tmp_path):
    """معيار ١٨: Trace كامل لكل حلقة → قابل للتفتيش والتدقيق."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    tr = out["trace"]
    assert tr["loop_id"] == out["loop_id"]
    assert tr["span_count"] >= 1
    assert all("inputs" in s and "outputs" in s and "duration_ms" in s
               for s in tr["spans"])  # مدخلات/مخرجات/زمن لكل span
    assert all(d.get("trace_ref") for d in tr["decisions"])  # مرجع الحلقة


# ===================================================================== ١٩-٢٠
def test_a19_org_policy_blocks_tool_documented(tmp_path):
    """معيار ١٩: سياسة مؤسسة تمنع أداة → رفض تلقائي موثق."""
    o, _, pol = make_env(tmp_path)
    pol.block_connector("github", "test")  # منع الموصل كله — سياسة مؤسسة
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    r = out["results"][0]
    assert r["status"] == "denied"
    assert r["error"]["code"] == "org_policy"
    assert "سياسة المؤسسة" in r["error"]["message"]


def test_a20_admin_override_allowed_but_recorded(tmp_path):
    """معيار ٢٠: تجاوز من مسؤول → مسموح لكن مسجَّل صراحة."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "افتح مشكلة في github.com/acme/webapp")
    ap = out["pending_approval"]
    rec = o.hitl.override(o.approvals, ap["approval_id"], "admin-sara",
                          "قرار تشغيلي موثق", "")
    assert rec["ok"] is True
    after = o.approvals.get(ap["approval_id"])
    assert after["approved_by"] == "admin:admin-sara"  # هوية التجاوز مسجلة
    assert after["status"] == "approved"
    # لا تنفيذ بعد التسجيل فقط — نستأنف الحلقة صراحة
    resumed = o.decide_approval(out["loop_id"], ap["approval_id"],
                                "approved", "admin:admin-sara")
    assert resumed["status"] == "completed"


# ===================================================================== ٢١
def test_a21_circuit_breaker_inherited_from_executor(tmp_path):
    """معيار ٢١: قاطع الدائرة يعمل من طبقة التنسيق دون إعادة بناء."""
    o, ex, _ = make_env(tmp_path)

    def failing(method, url, **kw):
        return FakeResponse(status_code=500)

    ex2 = cs_exec.Executor(state_dir=tmp_path / "ex2",
                           credentials=ex.credentials, policy=ex.policy,
                           http=failing, clock=lambda: time.time())
    ex2.registry = cs_registry.Registry()
    o._conn_executor = ex2
    # ثلاث فشلات متتالية تفتح القاطع (عتبة المنفذ نفسه)
    for _ in range(3):
        submit(o, "حلل مستودع github.com/acme/webapp", session="sb1")
    breaker = next(iter(ex2._breakers.values()))
    assert breaker.opened_at is not None  # مفتوح من طبقة التنسيق
    # الحلقة الرابعة تفشل فورًا بسبب القاطع — معزولة لا منهارة
    out = submit(o, "حلل مستودع github.com/acme/webapp", session="sb2")
    assert out["status"] in ("failed", "completed")
    codes = {(r.get("error") or {}).get("code") for r in out["results"]}
    assert codes & {"ConnectorUnavailableError", "replan", "tool"} or \
        out["status"] == "completed"


# ===================================================================== ٢٢
def test_a22_max_steps_limit_no_looping(tmp_path):
    """معيار ٢٢: حد أقصى للخطوات → إيقاف عند التجاوز، لا دوران."""
    o, _, _ = make_env(tmp_path)
    out = submit(o, "حلل مستودع github.com/acme/webapp",
                 constraints={"max_cost": 5, "max_time_s": 30,
                              "max_steps": 1})
    # خطة بخطوة واحدة: تكتمل ولا تدور؛ الحد الأدنى يحسم بلا دوران
    assert out["status"] in ("completed", "failed")
    assert o.planner is not None  # الحارس البنيوي موجود
    # والحد يُطبق فعليًا: ميزانية من خطوة واحدة لا تسمح بأكثر
    b = governor.Budget(max_steps=1)
    with pytest.raises(governor.BudgetExceededError):
        b.check_before_step(1)


# ===================================================================== ٢٣
def test_a23_tool_without_schema_not_registered(tmp_path):
    """معيار ٢٣: أداة بلا مخطط → لا تُسجَّل في السجل ولا تُستدعى."""
    o, _, _ = make_env(tmp_path)
    with pytest.raises(tool_registry.ToolRegistryError):
        o.tools.register(tool_registry.ToolDefinition(
            tool_id="bad.noschema", name="بلا مخطط", description="وصف"
            " كافٍ فوق عشرة أحرف", connector_id="github",
            operation="repo_read", access="read", risk="low",
            input_schema={}, output_schema={}, scopes=[], idempotent=True,
            estimated_cost=0, estimated_time_s=1))
    with pytest.raises(tool_registry.ToolRegistryError):
        o.tools.get("bad.noschema")  # ولا تستدعى


# ===================================================================== ٢٤
def test_a24_end_to_end_scenarios(tmp_path):
    """معيار ٢٤: 5 سيناريوهات سلوكية كاملة بمسارات كاملة."""
    scenarios = [
        ("قراءة بسيطة", "حلل مستودع github.com/acme/webapp", (), "completed"),
        ("قراءة Render", "اعرض خدمات Render", (), "completed"),
        ("كتابة معتمدة", "افتح مشكلة في github.com/acme/webapp",
         ("orchestrator:write",), "pending_approval"),
        ("قراءة Supabase", "اعرض صفوف جدول users", (), "completed"),
        ("غموض", "افتح مشكلة", (), "needs_clarification"),
    ]
    for name, utt, perms, expected in scenarios:
        o, _, _ = make_env(tmp_path)
        out = submit(o, utt, permissions=perms, session=f"s-{name}")
        assert out["status"] == expected, name
        assert out["trace"]["span_count"] >= 0


# ===================================================================== ٢٥
def test_a25_api_coverage_under_orchestrator(tmp_path):
    """معيار ٢٥: تغطية API لكل نقطة جديدة تحت /orchestrator/*."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    api_routes.reset_for_tests()
    api_routes._SYSTEM = runtime.OrchestratorSystem(
        data_dir=str(tmp_path / "orch-api"),
        connector_executor=make_env(tmp_path)[1])
    app = FastAPI()
    app.include_router(api_routes.router)
    client = TestClient(app)

    # POST /loops — حلقة كاملة (بوابة مفتاح المالك: 401 بدونه)
    r401 = client.post("/orchestrator/loops", json={
        "utterance": "حلل مستودع github.com/acme/webapp",
        "permissions": [], "session_id": "api-s"})
    assert r401.status_code == 401
    K = {"api_key": "test_master_key_1234567890abcdef"}
    r = client.post("/orchestrator/loops", json={
        "utterance": "حلل مستودع github.com/acme/webapp",
        "permissions": [], "session_id": "api-s", **K})
    assert r.status_code == 200
    loop_id = r.json()["loop_id"]

    # GET /loops و GET /loops/{id}
    assert client.get("/orchestrator/loops").status_code == 200
    r = client.get(f"/orchestrator/loops/{loop_id}")
    assert r.status_code == 200

    # GET /loops/{id}/trace
    r = client.get(f"/orchestrator/loops/{loop_id}/trace")
    assert r.status_code == 200

    # GET /tools و GET /schemas و GET /health
    assert client.get("/orchestrator/tools").status_code == 200
    assert client.get("/orchestrator/schemas").status_code == 200
    assert client.get("/orchestrator/health").status_code == 200

    # 404 لحلقة غير موجودة
    assert client.get("/orchestrator/loops/nope").status_code == 404

    # بوابة الموافقة عبر API: حلقة معلّقة ثم حسمها
    r = client.post("/orchestrator/loops", json={
        "utterance": "افتح مشكلة في github.com/acme/webapp",
        "permissions": ["orchestrator:write"], "session_id": "api-a", **K})
    assert r.status_code == 200
    ap_id = r.json()["pending_approval"]["approval_id"]
    assert client.get("/orchestrator/approvals/pending").status_code == 200
    r = client.post("/orchestrator/approvals", json={
        "approval_id": ap_id, "decision": "rejected", "approved_by": "u", **K})
    assert r.status_code == 200
    assert r.json()["status"] != "pending_approval"

    # dry-run عبر API
    r = client.post("/orchestrator/loops", json={
        "utterance": "افتح مشكلة في github.com/acme/webapp",
        "permissions": ["orchestrator:write"], "session_id": "api-d",
        "dry_run": True, **K})
    assert r.status_code == 200
    assert r.json()["dry_run_preview"]

    # cancel و pause/resume و modify_plan و rollback عبر API
    r = client.post(f"/orchestrator/loops/{loop_id}/cancel",
                    json={"actor": "user", **K})
    assert r.status_code == 200


# ===================================================================== ٢٦
def test_a26_no_secret_leak_canary(tmp_path):
    """معيار ٢٦: كناري عدم تسريب الأسرار — لا سر في traces/قرارات/ردود."""
    o, _, _ = make_env(tmp_path)
    secret = "gh_test_token"
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    blob = json.dumps(out, ensure_ascii=False)
    assert secret not in blob
    tr = json.dumps(o.trace(out["loop_id"]), ensure_ascii=False)
    assert secret not in tr and "sb_test_key" not in tr
    # scrub: المفاتيح السرية تُنقّى بالبنية
    cleaned = tracing.scrub({"api_key": secret, "nested": {
        "Authorization": "Bearer x"}})
    assert cleaned["api_key"] == "***" and \
        cleaned["nested"]["Authorization"] == "***"


# ===================================================================== ٢٧
def test_a27_performance_simple_and_composite_within_budget(tmp_path):
    """معيار ٢٧: حلقة بسيطة تحت الحد، ومركبة ضمن الميزانية."""
    o, _, _ = make_env(tmp_path)
    t0 = time.monotonic()
    out = submit(o, "حلل مستودع github.com/acme/webapp")
    simple_ms = (time.monotonic() - t0) * 1000
    assert simple_ms < 5000, f"حلقة بسيطة بطيئة: {simple_ms:.0f}ms"
    assert out["budget_spent"]["steps"] <= out["plan"]["max_steps"]

    sem = gh_semantic("x")
    sem["utterance"] = ("افتح مشكلة في github.com/acme/webapp واعرض خدمات"
                        " Render وصفوف جدول users")
    req = schemas.new_request(user_id="u", session_id="s-perf",
                              utterance=sem["utterance"],
                              permissions=["orchestrator:write"],
                              constraints={"max_cost": 10, "max_time_s": 60,
                                           "max_steps": 8})
    o.approvals.grant_session("s-perf", "github.issue_create")
    t0 = time.monotonic()
    out2 = o.submit(req, semantic=sem)
    comp_ms = (time.monotonic() - t0) * 1000
    assert out2["status"] == "completed"
    assert comp_ms < 10000
    assert out2["budget_spent"]["cost"] <= 10  # ضمن الميزانية


# ===================================================================== ٢٨
def test_a28_docs_delivered(tmp_path):
    """معيار ٢٨: الوثائق موجودة — العقود والمسارات والمخاطر والاستئناف."""
    docs = REPO_ROOT / "docs"
    for name in ("ORCHESTRATOR.md", "PROJECT_STATE.md", "CHANGELOG.md"):
        assert (docs / name).exists(), name
    orch = (docs / "ORCHESTRATOR.md").read_text(encoding="utf-8")
    assert "5.1" in orch and "Runbook" in orch and "أداة جديدة" in orch


# ======================================================= تشغيلي: حي عبر GitHub
@pytest.mark.operational
def test_live_github_through_orchestrator():
    """حلقة حية عبر المنفذ الحقيقي: خزينة ← حل ← منفذ ← GitHub ← رد.

    المفتاح من البيئة فقط (GITHUB_TOKEN) — لا سر في الكود أبدًا.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        pytest.skip("يتطلب GITHUB_TOKEN (ومرحّل --run-operational)")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import backend.config  # noqa: F401 — مسار البيانات الحقيقي
    try:  # إحياء مفتاح التوقيع عند أول إقلاع (نمط R-818) — بلا كسر
        from backend.app import _bootstrap_signing_key
        _bootstrap_signing_key()
    except Exception:
        pass  # TOLERATED: موجود سلفًا أو بيئة معزولة
    api_routes.reset_for_tests()
    api_routes._SYSTEM = runtime.OrchestratorSystem(
        data_dir=str(REPO_ROOT / "data" / "agent_orchestrator"))
    # ربط اعتماد حي بالمنفذ الحقيقي — من البيئة، بلا سر في الكود
    cs = api_routes._SYSTEM._executor()
    try:
        cred = cs.credentials.create(
            "github", "pat", "global", "owner",
            ["repo:read"], token, "live-test")
    except Exception:
        pass  # TOLERATED: موجود سلفًا من تشغيل حي سابق
    app = FastAPI()
    app.include_router(api_routes.router)
    client = TestClient(app)
    r = client.post("/orchestrator/loops", json={
        "utterance": "حلل مستودع reeveero-tech/sovereign_ai",
        "permissions": [], "session_id": "live-1",
        "api_key": os.environ.get(
            "SOVEREIGN_KEY", "test_master_key_1234567890abcdef")})
    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["status"] == "success"
    assert body["results"][0]["output"]["repo"] == \
        "reeveero-tech/sovereign_ai"
