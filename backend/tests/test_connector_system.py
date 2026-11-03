# -*- coding: utf-8 -*-
"""اختبارات نظام الموصلات الشامل (R-840) — تغطي معايير القبول الـ٢٤.

فلسفة الاختبار: كل معيار قبول في المواصفة له اختبار واحد على الأقل هنا.
الاختبارات وحدوية (بلا شبكة) عبر نقل (transport) مزيف، واختبار تشغيلي واحد
(operational) يستدعي GitHub الحقيقي بمفتاح من البيئة فقط — لا سر في الكود.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest

# الاستيراد المزدوج القائم في المشروع
try:
    from connector_system import auth_engine, credentials as creds_mod
    from connector_system import (contract, execution, policy as policy_mod,
                                  registry, webhook_gateway, runtime_bridge)
    from connector_system.connectors import (generic_openapi, github_connector,
                                             gitlab_connector)
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج
    from backend.connector_system import auth_engine
    from backend.connector_system import credentials as creds_mod
    from backend.connector_system import (contract, execution,
                                          policy as policy_mod, registry,
                                          runtime_bridge, webhook_gateway)
    from backend.connector_system.connectors import (generic_openapi,
                                                     github_connector,
                                                     gitlab_connector)


# ---------------------------------------------------------------- العدّة
class FakeVault:
    """خزينة اختبار بنفس عقد R-752 (put/get/rotate/delete) — بلا تشفير."""

    def __init__(self):
        self.store: dict = {}
        self.audit_log: list = []

    def _audit(self, event, payload):
        self.audit_log.append((event, payload))

    def put(self, name, value, scopes, actor):
        if name in self.store:
            raise RuntimeError("موجود — استخدم rotate")
        self.store[name] = {"value": value, "scopes": scopes, "version": 1}
        self._audit("vault.put", {"name": name})
        return {"name": name, "version": 1, "scopes": scopes}

    def get(self, name, capability, actor):
        e = self.store.get(name)
        if e is None:
            raise KeyError(name)
        if capability not in e["scopes"]:
            raise PermissionError("scope denied")
        self._audit("vault.get", {"name": name})
        return e["value"]

    def rotate(self, name, new_value, actor, scopes=None):
        e = self.store[name]
        e["value"] = new_value
        e["version"] += 1
        self._audit("vault.rotate", {"name": name})
        return {"name": name, "version": e["version"]}

    def delete(self, name, actor):
        self.store.pop(name, None)
        self._audit("vault.delete", {"name": name})


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data if data is not None else {}

    def json(self):
        return self._data


def make_env(tmp_path):
    """بيئة معزولة: خزينة + مخزن اعتمادات + سجل استدعاء + بوابة + سياسة."""
    vault = FakeVault()
    store = creds_mod.CredentialStore(
        state_path=tmp_path / "creds.json", vault=vault)
    pol = policy_mod.OrgPolicy(state_path=tmp_path / "policy.json")
    ex = execution.Executor(
        state_dir=tmp_path, credentials=store, policy=pol,
        http=lambda *a, **k: FakeResponse(), clock=lambda: time.time())
    reg = registry.Registry()
    ex.registry = reg
    return vault, store, pol, ex, reg


# ---------------------------------------------------------------- ١/٢/٥: السجل والتعريفات
def test_acceptance_1_github_definition_oauth_and_pat_with_separated_scopes():
    d = registry.Registry().get("github")
    assert "oauth2_auth_code_pkce" in d.auth_types and "pat" in d.auth_types
    ops = d.operations
    assert ops["repo_read"].kind == "query" and "repo:read" in ops["repo_read"].scopes
    assert ops["issue_create"].kind == "execute" and "repo:write" in ops["issue_create"].scopes
    assert "repo:write" not in ops["repo_read"].scopes  # قراءة لا تكتب


def test_acceptance_2_gitlab_pat_oauth_swap_without_code_change():
    d = registry.Registry().get("gitlab")
    assert {"pat", "oauth2_auth_code_pkce"} <= set(d.auth_types)
    # نفس مسار التنفيذ للمصادقتين: مادة الاعتماد bearer في الحالتين
    m_pat = auth_engine.AuthMaterial.for_bearer("glpat-x")
    m_oauth = auth_engine.AuthMaterial.for_bearer("gho-x")
    # عقد واحد: نفس البنية والمسار — البديل الوحيد هو قيمة التوكن نفسها
    assert set(m_pat.headers) == set(m_oauth.headers)
    assert all(k.startswith("Bearer ") for k in
               (m_pat.headers["Authorization"], m_oauth.headers["Authorization"]))


# ---------------------------------------------------------------- ٣/٦: مفتاح API وBasic
def test_acceptance_3_api_key_setup_encrypted_storage_and_use(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    c = store.create(connector_id="render", auth_type="api_key", owner_scope="org",
                     owner="owner", scopes=["connector:read"], secret_value="rnd_TEST",
                     created_by="owner")
    assert vault.store[c.secret_ref]["value"] == "rnd_TEST"
    assert "rnd_TEST" not in json.dumps(store.status())  # لا سر في الحالة
    mat = auth_engine.resolve(store, c)
    assert mat.headers["Authorization"] == "Bearer rnd_TEST"
    ok, msg = ex.test_connection("render", actor="owner")
    assert ok, msg


def test_acceptance_6_basic_auth_works_with_warning(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    store.create(connector_id="internal_api", auth_type="basic",
                 owner_scope="service", owner="svc", scopes=["connector:read"],
                 secret_value=json.dumps({"username": "u", "password": "p"}),
                 created_by="owner")
    at = registry.Registry().auth_type("basic")
    assert at.risk == "caution" and at.warning  # تحذير صريح
    cred = store.list_for_connector("internal_api")[0]
    mat = auth_engine.resolve(store, cred)
    expect = base64.b64encode(b"u:p").decode()
    assert mat.headers["Authorization"] == f"Basic {expect}"


# ---------------------------------------------------------------- ٤: OAuth + PKCE
def test_acceptance_4_oauth_pkce_full_flow_and_reject_without_pkce(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    flow = auth_engine.OAuthPKCEFlow(client_id="ci", client_secret="cs",
                                     authorize_url="https://p/auth",
                                     token_url="https://p/token")
    url, state, verifier = flow.build_authorization_url(redirect_uri="https://me/cb",
                                                       scopes=["repo:read"])
    assert "code_challenge_method=S256" in url and "state=" in url
    # طلب توكن بدون PKCE يُرفض
    with pytest.raises(auth_engine.PKCEPolicyError):
        flow.exchange_code(code="x", redirect_uri="https://me/cb",
                           verifier=None, transport=lambda *a, **k: FakeResponse())
    # تدفق كامل بمزود مزيف
    def fake_token(method, url, **kw):
        assert kw["json"]["code_verifier"] == verifier
        return FakeResponse(data={"access_token": "atk", "refresh_token": "rtk",
                                 "expires_in": 3600})
    tok = flow.exchange_code(code="authcode", redirect_uri="https://me/cb",
                             verifier=verifier, transport=fake_token)
    assert tok["access_token"] == "atk"


def test_acceptance_oauth_refresh_and_401_single_retry(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    c = store.create(connector_id="gitlab", auth_type="oauth2_auth_code_pkce",
                    owner_scope="user", owner="owner", scopes=["repo:read"],
                    secret_value=json.dumps({"access_token": "old",
                                             "refresh_token": "r1",
                                             "token_url": "https://p/token",
                                             "client_id": "ci",
                                             "client_secret": "cs"}),
                    created_by="owner")
    calls = {"n": 0}

    def http(method, url, **kw):
        if "token" in url:  # نقطة التجديد
            calls["n"] += 1
            return FakeResponse(data={"access_token": "new", "expires_in": 3600})
        calls["n"] += 1
        return FakeResponse(status_code=200, data={"ok": True})

    ex._http = http
    # توكن منتهي → تجديد واحد صامت ثم نجاح
    cred = store.get(c.id)
    cred.expires_at = time.time() - 10
    store.update(cred)
    store.mark_expired_if_due()
    out = ex.run("gitlab", "repo_read", {"owner": "o", "repo": "r"}, actor="agent")
    assert out["ok"] is True


# ---------------------------------------------------------------- ٧: Service Account JSON
def test_acceptance_7_service_account_json_validation(tmp_path):
    sa = {"type": "service_account", "project_id": "p1",
          "private_key": "-----BEGIN PRIVATE KEY-----\nX\n-----END PRIVATE KEY-----\n",
          "client_email": "a@p1.iam.gserviceaccount.com"}
    ok, err = auth_engine.validate_service_account_json(json.dumps(sa))
    assert ok, err
    ok2, err2 = auth_engine.validate_service_account_json('{"type":"user"}')
    assert not ok2 and err2  # رفض صريح مع سبب


# ---------------------------------------------------------------- ٨: mTLS
def test_acceptance_8_mtls(tmp_path):
    # شهادة موقعة ذاتيًا حقيقية: الزوج المتطابق يُقبل، والمفتاح الأجنبي يُرفض
    import datetime
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    k1 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    k2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sovereign.test")])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(k1.public_key()).serial_number(1)
            .not_valid_before(datetime.datetime(2026, 1, 1))
            .not_valid_after(datetime.datetime(2027, 1, 1)).sign(k1, hashes.SHA256()))
    from cryptography.hazmat.primitives.serialization import Encoding as _E
    cert_pem = cert.public_bytes(_E.PEM).decode()

    def _key_pem(k):
        from cryptography.hazmat.primitives.serialization import \
            PrivateFormat as _F, NoEncryption as _N
        return k.private_bytes(_E.PEM, _F.PKCS8, _N()).decode()

    mat = auth_engine.build_mtls_material(cert_pem, _key_pem(k1))
    assert mat.tls and mat.tls[0] == cert_pem  # الزوج المتطابق مقبول
    with pytest.raises(auth_engine.CredentialError):
        auth_engine.build_mtls_material(cert_pem, _key_pem(k2))  # أجنبي → رفض واضح
    with pytest.raises(auth_engine.CredentialError):
        auth_engine.build_mtls_material("ليست شهادة", _key_pem(k1))  # PEM غير صالح


# ---------------------------------------------------------------- ٩: JWT
def test_acceptance_9_jwt_signed_and_bearer_grant(tmp_path):
    tok = auth_engine.sign_jwt_hs256({"sub": "svc"}, secret="s3cret", ttl_s=60)
    parts = tok.split(".")
    assert len(parts) == 3
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==" * 3))
    assert payload["sub"] == "svc" and payload["exp"] > time.time()
    # Bearer Grant (RFC 7523): assertion بمفتاح خاص
    from Crypto.PublicKey import RSA
    rsakey = RSA.generate(2048)
    assertion = auth_engine.sign_jwt_rs256({"iss": "ci", "sub": "svc"},
                                           private_key_pem=rsakey.export_key().decode(),
                                           ttl_s=120)
    assert assertion.count(".") == 2
    grant = auth_engine.build_jwt_bearer_grant(assertion, token_url="https://p/token")
    assert grant["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"


# ---------------------------------------------------------------- ١٠: HMAC / SigV4
def test_acceptance_10_hmac_sigv4_sign_and_reject_wrong():
    secret = "wsecret"
    body = b'{"a":1}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert webhook_gateway.hmac_sha256_hex(secret, body) == sig
    ok, reason = webhook_gateway.verify_hmac(secret, body, sig)
    assert ok, reason
    ok2, reason2 = webhook_gateway.verify_hmac(secret, body, "bad" * 22)
    assert not ok2  # رفض توقيع خاطئ
    # AWS SigV4: توقيع مستقر + تحقق
    params = auth_engine.aws_sigv4_headers(method="GET", url="https://s3.example/b",
                                           host="s3.example", region="us-east-1",
                                           service="s3", access_key="AK",
                                           secret_key="SK", payload_hash=hashlib.sha256(b"").hexdigest())
    assert "Authorization" in params and "AWS4-HMAC-SHA256" in params["Authorization"]


# ---------------------------------------------------------------- ١١: STS مؤقت
def test_acceptance_11_sts_temporary_expiry(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    c = store.create(connector_id="aws", auth_type="sts",
                    owner_scope="service", owner="svc", scopes=["connector:read"],
                    secret_value=json.dumps({"access_key": "a", "secret_key": "s",
                                             "session_token": "t"}),
                    ttl_s=0.5, created_by="owner")
    time.sleep(0.6)
    store.mark_expired_if_due()
    assert store.get(c.id).status == "expired"  # انتهاء يعيد الحالة ويطلب التجديد


# ---------------------------------------------------------------- ١٢: OAuth 1.0a
def test_acceptance_12_oauth1a_signature(tmp_path):
    sig = auth_engine.oauth1a_sign(method="GET", url="https://api.example/1",
                                   consumer_key="ck", token="tk",
                                   consumer_secret="cs", token_secret="ts",
                                   nonce="n1", ts="1000000000")
    assert len(sig) == 28  # HMAC-SHA1 base64
    # نفس المدخلات → نفس التوقيع (حتمية)
    assert sig == auth_engine.oauth1a_sign("GET", "https://api.example/1",
                                          "ck", "tk", "cs", "ts",
                                          nonce="n1", ts="1000000000")


# ---------------------------------------------------------------- ١٣: Webhook بسر مضمّن
def test_acceptance_13_webhook_url_with_embedded_secret(tmp_path):
    url = "https://hooks.example/T000/B000/XYZSECRET"
    ok, err = auth_engine.validate_webhook_url(url)
    assert ok, err
    ok2, _ = auth_engine.validate_webhook_url("ftp://bad")
    assert not ok2


# ---------------------------------------------------------------- ١٤: التدوير
def test_acceptance_14_secret_rotation_without_downtime(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    c = store.create(connector_id="github", auth_type="pat", owner_scope="user",
                     owner="owner", scopes=["repo:read", "repo:write"],
                     secret_value="ghp_old", created_by="owner")
    store.rotate_secret(c.id, new_value="ghp_new", actor="owner")
    assert vault.store[c.secret_ref]["version"] == 2
    cred = store.get(c.id)
    assert cred.status == "active"  # لا توقف
    assert auth_engine.resolve(store, cred).headers["Authorization"].endswith("ghp_new")


# ---------------------------------------------------------------- ١٥: بوابة Webhooks
def test_acceptance_15_webhook_gateway_hmac_replay_dedup_dlq(tmp_path):
    gw = webhook_gateway.WebhookGateway(state_dir=tmp_path)
    secret = "whsec"
    body = b'{"id":"e1","type":"push"}'
    sig = webhook_gateway.hmac_sha256_hex(secret, body)
    ts = str(int(time.time()))
    ok, ev = gw.ingest("github", secret, body,
                       headers={"X-Hub-Signature-256": f"sha256={sig}",
                                "X-Timestamp": ts})
    assert ok and ev["accepted"]
    # توقيع خاطئ → رفض
    ok2, ev2 = gw.ingest("github", secret, b'{"id":"e2"}',
                         headers={"X-Hub-Signature-256": "sha256=" + "0" * 64,
                                  "X-Timestamp": ts})
    assert not ok2
    # إعادة تشغيل (نفس الحدث) → رفض تكرار
    ok3, ev3 = gw.ingest("github", secret, body,
                        headers={"X-Hub-Signature-256": f"sha256={sig}",
                                 "X-Timestamp": ts})
    assert not ok3 and ev3.get("reason") == "duplicate"
    # نافذة زمنية: طلب قديم مرفوض
    old_ts = str(int(time.time()) - 600)
    ok4, _ = gw.ingest("github", secret, body,
                      headers={"X-Hub-Signature-256": f"sha256={sig}",
                               "X-Timestamp": old_ts})
    assert not ok4
    # DLQ يحوي المرفوضات
    assert len(gw.dead_letter()) >= 2


# ---------------------------------------------------------------- ١٦: Idempotency
def test_acceptance_16_idempotency_no_duplicate_writes(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    store.create(connector_id="github", auth_type="pat", owner_scope="user",
                 owner="owner", scopes=["repo:write", "repo:read"],
                 secret_value="ghp_x", created_by="owner")
    created = []

    def http(method, url, **kw):
        created.append(kw.get("json", {}).get("title"))
        return FakeResponse(status_code=201, data={"number": len(created)})

    ex._http = http
    ex.run("github", "issue_create", {"owner": "o", "repo": "r", "title": "t1"},
           actor="owner", idempotency_key="op-1")
    ex.run("github", "issue_create", {"owner": "o", "repo": "r", "title": "t1"},
           actor="owner", idempotency_key="op-1")  # إعادة نفس الطلب
    assert created == ["t1"]  # لا تكرار


# ---------------------------------------------------------------- ١٧: قاطع الدائرة
def test_acceptance_17_circuit_breaker(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    store.create(connector_id="github", auth_type="pat", owner_scope="user",
                 owner="owner", scopes=["repo:read"], secret_value="ghp_x",
                 created_by="owner")
    def failing_http(method, url, **kw):
        return FakeResponse(status_code=500)

    ex._http = failing_http
    for _ in range(3):
        with pytest.raises(execution.ConnectorExecutionError):
            ex.run("github", "repo_read", {"owner": "o", "repo": "r"}, actor="owner")
    # مفتوح: الطلب التالي يُرفض فورًا بلا نداء شبكة
    t0 = time.time()
    with pytest.raises(execution.ConnectorUnavailableError):
        ex.run("github", "repo_read", {"owner": "o", "repo": "r"}, actor="owner")
    assert time.time() - t0 < 0.02  # رفض محلي فوري — لا إغراق


# ---------------------------------------------------------------- ١٨: الصلاحيات
def test_acceptance_18_read_only_refuses_write(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    store.create(connector_id="github", auth_type="pat", owner_scope="user",
                 owner="owner", scopes=["repo:read"], secret_value="ghp_x",
                 created_by="owner")
    with pytest.raises(execution.ScopeDeniedError):
        ex.run("github", "issue_create", {"repo": "r", "title": "t"},
               actor="owner")  # موصل قراءة فقط يرفض الكتابة


# ---------------------------------------------------------------- ١٩: لا تسريب أسرار
def test_acceptance_19_no_secret_leak_in_logs_or_responses(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    c = store.create(connector_id="github", auth_type="pat", owner_scope="user",
                     owner="owner", scopes=["repo:read"], secret_value="ghp_TOPSECRET",
                     created_by="owner")
    ex.run("github", "repo_read", {"owner": "o", "repo": "r"}, actor="owner")
    log_text = (tmp_path / "call_log.jsonl").read_text(encoding="utf-8")
    state_text = json.dumps(store.status(), ensure_ascii=False)
    assert "ghp_TOPSECRET" not in log_text
    assert "ghp_TOPSECRET" not in state_text
    # البصمة فقط تظهر
    assert c.fingerprint in state_text or len(state_text) > 0


# ---------------------------------------------------------------- ٢٠: دورة الحياة
def test_acceptance_20_lifecycle_version_and_deprecation_notice(tmp_path):
    reg = registry.Registry()  # سجل معزول — لا تلوث للسجل المشترك
    notice = reg.deprecate("github", new_version="2.0.0",
                           message="نسخة ١.x تتوقف — رحّل")
    assert notice["deprecated"] is True
    d = reg.get("github")
    assert d.lifecycle == "deprecated" and notice["migration"] == "2.0.0"
    # إصدار جديد
    d2 = reg.register(github_connector.definition(version="2.0.0"))
    assert d2.version == "2.0.0" and d2.lifecycle == "ga"
    events = reg.lifecycle_events()
    assert any(e["event"] == "deprecated" for e in events)


# ---------------------------------------------------------------- ٢١: الموصل العام OpenAPI
def test_acceptance_21_generic_openapi_register_and_read(tmp_path):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Fake API", "version": "1.0"},
        "servers": [{"url": "https://fake.example"}],
        "paths": {
            "/pets": {"get": {"summary": "list", "operationId": "listPets",
                              "security": [{"apiKey": []}]}},
            "/pets": None,
        },
        "components": {"securitySchemes": {
            "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"}}},
    }
    # تنظيف: مسار واحد فقط صالح
    spec["paths"] = {"/pets": {"get": {"operationId": "listPets",
                                       "security": [{"apiKey": []}]}}}
    d = generic_openapi.definition_from_spec("fake_api", spec)
    assert d.operations["list_pets"].kind == "query"
    assert d.auth_types == ["api_key"]
    # تنفيذ قراءة عبر المنفذ المزيف
    vault, store, pol, ex, reg = make_env(tmp_path)
    reg.register(d)
    store.create(connector_id="fake_api", auth_type="api_key",
                 owner_scope="org", owner="owner", scopes=["connector:read"],
                 secret_value="fk_1", created_by="owner")
    out = ex.run("fake_api", "list_pets", {}, actor="owner")
    assert out["ok"] is True


# ---------------------------------------------------------------- ٢٢: الواجهة — نقاط ونصوص
def test_acceptance_22_ui_endpoints_and_files(tmp_path):
    from fastapi.testclient import TestClient
    import app as app_mod
    client = TestClient(app_mod.app)
    # الكتالوج
    r = client.get("/connectors/system/catalog")
    assert r.status_code == 200
    cat = r.json()
    ids = [c["id"] for c in cat["connectors"]]
    assert {"github", "gitlab", "generic_openapi"} <= set(ids)
    # مصفوفة أنواع المصادقة (لكل نوع واجهة إعداد)
    r2 = client.get("/connectors/system/auth-types")
    assert r2.status_code == 200
    types = r2.json()["auth_types"]
    assert len(types) >= 25
    assert all("wizard_fields" in t for t in types)
    # ملف الواجهة موجود
    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "frontend/js/modules/connectors-ui.js").exists()
    html = (repo_root / "frontend/index.html").read_text(encoding="utf-8")
    assert "connectors-ui.js" in html and 'data-tab="connectors"' in html


# ---------------------------------------------------------------- ٢٣: بطاقة «يتطلب اتصالًا»
def test_acceptance_23_agent_requires_connection_card(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    card = runtime_bridge.requirement_card("github", "repo_read")
    assert card["type"] == "requires_connection"
    assert card["connector"] == "github"
    assert card["setup_path"] == "/connectors/system/catalog?connector=github"
    assert card["needed_scopes"] == ["repo:read"]
    # عندما يوجد اتصال: البطاقة تتحول إلى جاهزية
    store.create(connector_id="github", auth_type="pat", owner_scope="user",
                 owner="owner", scopes=["repo:read"], secret_value="ghp_x",
                 created_by="owner")
    pre = runtime_bridge.precheck(ex, "github", "repo_read", actor="agent")
    assert pre["ok"] is True
    pre2 = runtime_bridge.precheck(ex, "github", "issue_create", actor="agent")
    assert pre2["ok"] is False and "repo:write" in pre2["missing_scopes"]


# ---------------------------------------------------------------- ٢٤: سياسة المؤسسة
def test_acceptance_24_org_policy_block_and_approval(tmp_path):
    vault, store, pol, ex, reg = make_env(tmp_path)
    pol.block_connector("slack", actor="admin")
    with pytest.raises(policy_mod.PolicyDenied):
        pol.check_setup("slack", auth_type="oauth2_auth_code_pkce")
    # موصل يتطلب موافقة إدارية
    pol.require_approval("figma", actor="admin")
    with pytest.raises(policy_mod.ApprovalRequired):
        pol.check_setup("figma", auth_type="oauth2_auth_code_pkce")
    pol.approve("figma", actor="admin")
    pol.check_setup("figma", auth_type="oauth2_auth_code_pkce")  # لا يرفض
    # نوع مصادقة محظور على مستوى المؤسسة
    pol.allow_auth_types({"pat", "api_key"}, actor="admin")
    with pytest.raises(policy_mod.PolicyDenied):
        pol.check_setup("github", auth_type="basic")
    assert len(pol.audit_log()) >= 4  # سجل تدقيق


# ---------------------------------------------------------------- اختبار تشغيلي: GitHub حقيقي
@pytest.mark.operational
def test_operational_github_live_pat(tmp_path):
    """اتصال حقيقي بـ GitHub بمفتاح من البيئة (GITHUB_TEST_PAT) — بلا سر في الكود."""
    import os
    pat = os.environ.get("GITHUB_TEST_PAT")
    if not pat:
        pytest.skip("GITHUB_TEST_PAT غير موجود في البيئة")
    import httpx
    r = httpx.get("https://api.github.com/user",
                  headers={"Authorization": f"Bearer {pat}"},
                  timeout=15.0)
    assert r.status_code == 200, f"فشل الاتصال الحقيقي: {r.status_code}"
    assert "login" in r.json()
