# -*- coding: utf-8 -*-
"""R-840c: اختبارات ملحق التدقيق — تحويل ادعاءات التقرير إلى براهين آلية.

كل اختبار هنا يقابل بندًا في docs/CONNECTOR_AUDIT_ADDENDUM.md:
- الكناري: حقن سر فريد عبر كل مسارات النظام والتأكد آليًا من غيابه في كل
  المخرجات (سجل الاستدعاء، ملف الحالة، ردود API، رفض Webhook، DLQ، سجل
  السياسة، نصوص الأخطاء المنقّاة).
- قاطع الدائرة: فتح بعد 3 إخفاقات ثم تعافٍ فعلي بعد فترة التهدئة (نصف
  مفتوح → نجاح → تصفير).
- الأنواع المهجورة: رفض صريح على مستوى API لا الوحدة فقط.
- سياسة المؤسسة: رفض 403 صريح (كان يسقط 500 — خلل كشفه التدقيق).
- بطاقة «يتطلب اتصالًا»: مسار API الحقيقي (424 + بطاقة).
- تشغيلي حي: GitHub عبر المنفذ نفسه (خزينة → حل → منفذ → موصل) بمفتاح
  من البيئة — لا سر في الكود أبدًا.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import pytest

# الاستيراد المزدوج القائم في المشروع
try:
    from connector_system import (auth_engine, credentials as creds_mod,
                                   execution, policy as policy_mod,
                                   webhook_gateway)
    from connector_system import get_system as _get_system
    import connector_system as _cs_pkg
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج
    from backend.connector_system import (auth_engine,
                                          credentials as creds_mod,
                                          execution,
                                          policy as policy_mod,
                                          webhook_gateway)
    from backend.connector_system import get_system as _get_system
    import backend.connector_system as _cs_pkg


# ---------------------------------------------------------------- العدّة
class AuditVault:
    """خزينة اختبار بعقد R-752 + status() لفحص vault_ready."""

    def __init__(self):
        self.store: dict = {}

    def status(self):
        return {"ok": True, "entries": len(self.store)}

    def put(self, name, value, scopes, actor):
        if name in self.store:
            raise RuntimeError("موجود — استخدم rotate")
        self.store[name] = {"value": value, "scopes": scopes, "version": 1}
        return {"name": name, "version": 1}

    def get(self, name, capability, actor):
        return self.store[name]["value"]

    def rotate(self, name, new_value, actor, scopes=None):
        self.store[name]["value"] = new_value
        self.store[name]["version"] += 1
        return {"name": name, "version": self.store[name]["version"]}

    def delete(self, name, actor):
        self.store.pop(name, None)


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data if data is not None else {}

    def json(self):
        return self._data


def make_audit_system(tmp_path):
    """نظام موصلات معزول (خزينة اختبار + دليل مؤقت) — للفحص عبر API."""
    vault = AuditVault()
    sys_obj = _cs_pkg.ConnectorSystem(data_dir=str(tmp_path), vault=vault)
    return vault, sys_obj


def _patch_system(monkeypatch, sys_obj):
    """توجيه get_system إلى نظام الاختبار — نقاط API تعمل عليه فعليًا."""
    monkeypatch.setattr(_cs_pkg, "get_system", lambda: sys_obj)


# ---------------------------------------------------------------- د: الكناري
def test_audit_canary_secret_never_in_any_output(tmp_path, monkeypatch):
    """حقن SECRET_CANARY عبر كل مسارات النظام — غيابه إلزامي في كل المخرجات."""
    from fastapi.testclient import TestClient
    import app as app_mod

    canary = "SECRET_CANARY_" + uuid.uuid4().hex
    vault, sys_obj = make_audit_system(tmp_path)
    _patch_system(monkeypatch, sys_obj)
    # نقل مزيف ناجح — اختبار الاتصال داخل /setup يمر بلا شبكة
    sys_obj.executor._http = lambda *a, **k: FakeResponse()
    client = TestClient(app_mod.app)

    # ١) الإعداد عبر API: السر يمر عبر المعالج والخزينة والاختبار
    r = client.post("/connectors/system/setup", json={
        "connector": "github", "auth_type": "pat",
        "fields": {"token": canary}, "scopes": ["repo:read"]})
    assert r.status_code == 200, r.text
    assert canary not in r.text

    # ٢) الحالة والسجلات عبر API — لا سر أبدًا
    assert canary not in client.get("/connectors/system/state").text
    assert canary not in client.get("/connectors/system/logs").text
    assert canary not in client.get("/connectors/system/catalog").text
    assert canary not in client.get("/connectors/system/auth-types").text

    # ٣) الملفات على القرص: سجل الاستدعاء وبيانات الاعتماد الوصفية
    log_text = (tmp_path / "connector_system" / "call_log.jsonl").read_text(
        encoding="utf-8")
    state_text = (tmp_path / "connector_system" / "credentials.json").read_text(
        encoding="utf-8")
    assert canary not in log_text
    assert canary not in state_text

    # ٤) سيناريو صدى المزود: استثناء نقل يحوي السر → يُنقّى قبل السجل والرفع
    def echoing_http(method, url, **kw):
        raise RuntimeError(f"provider error: Bearer {canary}")
    sys_obj.executor._http = echoing_http
    with pytest.raises(execution.ConnectorExecutionError) as ei:
        sys_obj.executor.run("github", "repo_read",
                             {"owner": "o", "repo": "r"}, actor="owner")
    assert canary not in str(ei.value)
    log_text2 = (tmp_path / "connector_system" / "call_log.jsonl").read_text(
        encoding="utf-8")
    assert canary not in log_text2
    assert "***" in log_text2  # الدليل: التنقية حدثت فعلًا

    # ٥) Webhook: سر التحقق نفسه كناري — رفض التوقيع الخاطئ لا يسرّبه
    c2 = sys_obj.credentials.create(
        connector_id="github", auth_type="hmac", owner_scope="service",
        owner="svc", scopes=["connector:read"], secret_value=canary,
        created_by="owner")
    assert c2.id
    r_wh = client.post("/connectors/system/webhooks/github",
                       content=b'{"id":"e1"}',
                       headers={"X-Hub-Signature-256": "sha256=" + "0" * 64,
                                "X-Timestamp": str(int(time.time()))})
    assert r_wh.status_code == 401
    assert canary not in r_wh.text
    dlq = sys_obj.webhooks.dead_letter()
    assert canary not in json.dumps(dlq, ensure_ascii=False)

    # ٦) سجل تدقيق السياسة — لا سر فيه أصلًا (تأكيد)
    sys_obj.policy.block_connector("slack", actor="admin")
    assert canary not in json.dumps(sys_obj.policy.audit_log(),
                                    ensure_ascii=False)

    # ٧) الخزينة وحدها تحوي السر — وهذا موضعها الصحيح الوحيد
    assert canary in json.dumps(vault.store, ensure_ascii=False)


# ---------------------------------------------------------------- هـ: القاطع
def test_audit_breaker_opens_then_recovers_after_cooldown(tmp_path):
    """القاطع: 3 إخفاقات → فتح → رفض فوري → تعافٍ فعلي بعد التهدئة."""
    vault = AuditVault()
    store = creds_mod.CredentialStore(state_path=tmp_path / "creds.json",
                                      vault=vault)
    pol = policy_mod.OrgPolicy(state_path=tmp_path / "policy.json")
    clock = {"now": 1000.0}
    ex = execution.Executor(
        state_dir=tmp_path, credentials=store, policy=pol,
        http=lambda *a, **k: FakeResponse(), clock=lambda: clock["now"])
    from connector_system import registry as _reg  # TOLERATED مزدوج
    ex.registry = _reg.Registry()
    store.create(connector_id="github", auth_type="pat", owner_scope="user",
                 owner="owner", scopes=["repo:read"], secret_value="ghp_x",
                 created_by="owner")

    def failing_http(method, url, **kw):
        return FakeResponse(status_code=500)
    ex._http = failing_http
    for _ in range(3):
        with pytest.raises(execution.ConnectorExecutionError):
            ex.run("github", "repo_read", {"owner": "o", "repo": "r"},
                   actor="owner")
    br = ex._breakers["github"]
    assert br.opened_at is not None  # مفتوح فعليًا

    # مفتوح → رفض محلي فوري بلا نداء شبكة
    t0 = time.time()
    with pytest.raises(execution.ConnectorUnavailableError):
        ex.run("github", "repo_read", {"owner": "o", "repo": "r"},
               actor="owner")
    assert time.time() - t0 < 0.05

    # التعافي: بعد فترة التهدئة (نصف مفتوح) يُسمح بمحاولة — نجاحها يصفّر
    clock["now"] += 61.0  # تجاوز cooldown_s=60
    ex._http = lambda *a, **k: FakeResponse()
    out = ex.run("github", "repo_read", {"owner": "o", "repo": "r"},
                 actor="owner")
    assert out["ok"] is True
    br2 = ex._breakers["github"]
    assert br2.opened_at is None and br2.failures == 0  # تصفير فعلي


# ---------------------------------------------------------------- ز: الأنواع الخطرة
def test_audit_deprecated_auth_types_rejected_at_setup_api(tmp_path, monkeypatch):
    """Implicit/ROPC/Query Token/Cookies: ممنوعة افتراضيًا على مستوى API."""
    from fastapi.testclient import TestClient
    import app as app_mod

    _, sys_obj = make_audit_system(tmp_path)
    _patch_system(monkeypatch, sys_obj)
    client = TestClient(app_mod.app)
    # موصل افتراضي يعلن الأنواع الخطرة — لإثبات فرع الرفض المهجور نفسه
    from connector_system.contract import ConnectorDefinition, Operation  # TOLERATED مزدوج
    sys_obj.registry.register(ConnectorDefinition(
        id="legacy_provider", name="Legacy", version="1.0.0",
        description="مزود قديم للسيناريو",
        auth_types=["implicit", "ropc", "query_token", "cookies_session"],
        operations={"ping": Operation("ping", "query", frozenset({"x:read"}))}))
    for dangerous in ("implicit", "ropc", "query_token", "cookies_session"):
        r = client.post("/connectors/system/setup", json={
            "connector": "legacy_provider", "auth_type": dangerous,
            "fields": {"client_id": "x", "token": "t", "param_name": "p",
                       "cookie_value": "c", "username": "u", "password": "p"},
            "scopes": ["x:read"]})
        assert r.status_code == 400, dangerous
        assert "مهجور" in r.text  # سبب الرفض الصريح: النوع مهجور
    # GitHub لا يعرض هذه الأنواع أصلًا — مزدوجة العزل
    r_github = client.post("/connectors/system/setup", json={
        "connector": "github", "auth_type": "implicit",
        "fields": {"client_id": "x"}, "scopes": ["repo:read"]})
    assert r_github.status_code == 400
    assert "غير مدعوم" in r_github.text
    # basic (caution): مسموح مع تحذير — والتحذير معلن في مصفوفة الأنواع
    types = client.get("/connectors/system/auth-types").json()["auth_types"]
    by_id = {t["id"]: t for t in types}
    for dangerous in ("implicit", "ropc", "query_token", "cookies_session"):
        assert by_id[dangerous]["risk"] == "deprecated"
        assert by_id[dangerous]["warning"]  # تحذير نصي صريح
    assert by_id["basic"]["risk"] == "caution" and by_id["basic"]["warning"]


def test_audit_ui_shows_warnings_for_risky_types():
    """الواجهة تعرض التحذير: صندوق wiz-warn + علامة الأنواع المهجورة."""
    repo_root = Path(__file__).resolve().parents[2]
    ui = (repo_root / "frontend/js/modules/connectors-ui.js").read_text(
        encoding="utf-8")
    assert "wiz-warn" in ui                 # صندوق التحذير في المعالج
    assert 't.risk === "deprecated"' in ui  # وسم ⚠️ للمهجور في القوائم
    assert "title='" in ui                  # التحذير كتلميح على الخيار


# ---------------------------------------------------------------- ح: السياسة
def test_audit_policy_denied_returns_403_not_500(tmp_path, monkeypatch):
    """موصل محظور: رفض 403 صريح عبر API (كان يسقط 500 — خلل R-840c المُصلح)."""
    from fastapi.testclient import TestClient
    import app as app_mod

    _, sys_obj = make_audit_system(tmp_path)
    _patch_system(monkeypatch, sys_obj)
    client = TestClient(app_mod.app)
    sys_obj.policy.block_connector("github", actor="admin")
    r = client.post("/connectors/system/setup", json={
        "connector": "github", "auth_type": "pat",
        "fields": {"token": "ghp_x"}, "scopes": ["repo:read"]})
    assert r.status_code == 403, r.text
    assert "محظور" in r.text
    r2 = client.post("/connectors/system/execute", json={
        "connector": "github", "operation": "repo_read",
        "inputs": {"owner": "o", "repo": "r"}})
    assert r2.status_code == 403
    # موصل يحتاج موافقة: لا يعمل قبلها، ويعمل بعدها
    sys_obj.policy.require_approval("gitlab", actor="admin")
    r3 = client.post("/connectors/system/setup", json={
        "connector": "gitlab", "auth_type": "pat",
        "fields": {"token": "glpat"}, "scopes": ["connector:read"]})
    assert r3.status_code == 403 and "موافقة" in r3.text
    sys_obj.policy.approve("gitlab", actor="admin")
    r4 = client.post("/connectors/system/setup", json={
        "connector": "gitlab", "auth_type": "pat",
        "fields": {"token": "glpat"}, "scopes": ["connector:read"]})
    assert r4.status_code == 422  # اجتاز السياسة — رفض لاحق لفشل اختبار الاتصال (نقل مزيف)
    assert "موافقة" not in r4.text and "محظور" not in r4.text


# ---------------------------------------------------------------- ط: بطاقة الوكيل
def test_audit_execute_without_connection_returns_424_card(tmp_path, monkeypatch):
    """بلا اتصال: /execute يعيد 424 + بطاقة «يتطلب اتصالًا» — مسار API الحقيقي."""
    from fastapi.testclient import TestClient
    import app as app_mod

    _, sys_obj = make_audit_system(tmp_path)
    _patch_system(monkeypatch, sys_obj)
    client = TestClient(app_mod.app)
    r = client.post("/connectors/system/execute", json={
        "connector": "github", "operation": "repo_read",
        "inputs": {"owner": "o", "repo": "r"}})
    assert r.status_code == 424
    detail = r.json()["detail"]
    card = detail["card"]
    assert card["type"] == "requires_connection"
    assert card["connector"] == "github"
    assert card["setup_path"] == "/connectors/system/catalog?connector=github"
    assert "repo:read" in card["needed_scopes"]


# ---------------------------------------------------------------- ج: تشغيل حي عبر المنفذ
@pytest.mark.operational
def test_operational_github_through_executor(tmp_path):
    """اتصال حي بـ GitHub عبر المنفذ نفسه (خزينة → حل → منفذ → موصل).

    يثبت المسار الكامل لا مجرد صلاحية التوكن: Executor.run → github connector.
    المفتاح من GITHUB_TEST_PAT في البيئة — لا سر في الكود.
    """
    import os
    pat = os.environ.get("GITHUB_TEST_PAT")
    if not pat:
        pytest.skip("GITHUB_TEST_PAT غير موجود في البيئة")
    vault = AuditVault()
    store = creds_mod.CredentialStore(state_path=tmp_path / "creds.json",
                                      vault=vault)
    pol = policy_mod.OrgPolicy(state_path=tmp_path / "policy.json")
    ex = execution.Executor(state_dir=tmp_path, credentials=store, policy=pol)
    from connector_system import registry as _reg  # TOLERATED مزدوج
    ex.registry = _reg.Registry()
    store.create(connector_id="github", auth_type="pat", owner_scope="user",
                 owner="owner", scopes=["repo:read"], secret_value=pat,
                 created_by="owner")
    out = ex.run("github", "test_connection", {}, actor="owner")
    assert out["ok"] is True
    assert out.get("login")  # مستخدم حقيقي من GitHub — لا إشارة زائفة
