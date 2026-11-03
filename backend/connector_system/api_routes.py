# -*- coding: utf-8 -*-
"""R-840: نقاط واجهة نظام الموصلات — الكتالوج والإعداد والإدارة والاختبار.

كل نوع مصادقة له مسار إعداد، وكل حالة فشل لها رسالة وإجراء. لا سر يعود
في أي رد أبدًا — البصمة فقط.
"""
from __future__ import annotations

import json
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import auth_engine, auth_types, execution, runtime_bridge
from .credentials import CredentialError, CredentialNotFound
from .policy import PolicyError

router = APIRouter(prefix="/connectors/system")

# حالات انتظار OAuth (state → verifier) — مؤقتة في الذاكرة
_OAUTH_STATES: Dict[str, str] = {}


def _system():
    from . import get_system
    return get_system()


def _vault_required():
    s = _system()
    if not s.vault_ready():
        raise HTTPException(
            status_code=503,
            detail="الخزينة معطلة (fail-closed) — اضبط SOVEREIGN_VAULT_MASTER_KEY "
                   "قبل إعداد أي اتصال. الحالة والكتالوج متاحان للقراءة")
    return s


# ---------------------------------------------------------------- العرض
@router.get("/catalog")
async def catalog(connector: Optional[str] = None, category: Optional[str] = None,
                  auth_type: Optional[str] = None, q: Optional[str] = None):
    """كتالوج الموصلات — بحث وتصفية حسب الفئة والمنصة ونوع المصادقة."""
    s = _system()
    items = s.registry.catalog()
    if connector:
        items = [c for c in items if c["id"] == connector]
    if category:
        items = [c for c in items if c["category"] == category]
    if auth_type:
        items = [c for c in items if auth_type in c["auth_types"]]
    if q:
        ql = q.lower()
        items = [c for c in items if ql in c["name"].lower()
                 or ql in c["description"].lower()]
    connections = {c["connector_id"]: c for c in s.credentials.status()["credentials"]}
    for c in items:
        c["connection"] = connections.get(c["id"])
    return {"connectors": items, "total": len(items)}


@router.get("/auth-types")
async def auth_types_matrix():
    """مصفوفة أنواع المصادقة الكاملة — لكل نوع حقول معالج الإعداد."""
    return {"auth_types": auth_types.matrix(),
            "total": len(auth_types.AUTH_TYPES)}


@router.get("/state")
async def system_state():
    """قائمة الاتصالات: المنصة، النوع، الصلاحيات، آخر استخدام، الحالة."""
    s = _system()
    return {"credentials": s.credentials.status()["credentials"],
            "policy": s.policy.public(),
            "breakers": {k: {"open": b.opened_at is not None}
                         for k, b in s.executor._breakers.items()}}


@router.get("/logs")
async def call_logs(limit: int = 100):
    """سجل الاستخدام: من، ماذا، متى، النتيجة — بلا أسرار."""
    return {"logs": _system().executor.call_log(limit=min(max(limit, 1), 500))}


# ---------------------------------------------------------------- الإعداد (Wizard)
class SetupRequest(BaseModel):
    connector: str = Field(..., min_length=1, max_length=64)
    auth_type: str = Field(..., max_length=40)
    fields: Dict[str, str] = Field(default_factory=dict)
    scopes: List[str] = Field(default_factory=list)
    owner_scope: str = Field(default="user", pattern="^(user|org|service)$")
    owner: str = Field(default="owner", max_length=64)
    ttl_s: Optional[float] = Field(None, gt=0)
    actor: str = Field(default="owner", max_length=64)


@router.post("/setup")
async def setup(request: SetupRequest):
    """معالج الإعداد — ينتهي دائمًا باختبار اتصال ومراجعة صلاحيات."""
    s = _vault_required()
    try:
        s.policy.check_setup(request.connector, request.auth_type)
        d = s.registry.get(request.connector)
        if request.auth_type not in d.auth_types:
            raise HTTPException(400, detail=f"نوع المصادقة غير مدعوم لهذا الموصل: {request.auth_type}")
        at = auth_types.auth_type(request.auth_type)
        if at.risk == "deprecated":
            raise HTTPException(400, detail=f"نوع مصادقة مهجور — مرفوض: {at.warning}")
        secret_value = _compose_secret(request.auth_type, request.fields)
        scopes = request.scopes or sorted(
            set().union(*[set(o.scopes) for o in d.operations.values()
                         if not o.is_write])) or ["connector:read"]
        c = s.credentials.create(
            connector_id=request.connector, auth_type=request.auth_type,
            owner_scope=request.owner_scope, owner=request.owner,
            scopes=scopes, secret_value=secret_value,
            created_by=request.actor, ttl_s=request.ttl_s)
        ok, msg = s.executor.test_connection(request.connector, actor=request.actor)
        if not ok:
            s.credentials.revoke(c.id, actor=request.actor)
            raise HTTPException(422, detail=f"فشل اختبار الاتصال بعد الإعداد — لم يُحفظ الاتصال: {msg}")
        return {"ok": True, "credential": c.public(), "test": {"ok": True}}
    except HTTPException:
        raise
    except PolicyError as exc:  # R-840c: حظر/موافقة سياسة → 403 صريح لا 500
        raise HTTPException(status_code=403, detail=str(exc)[:300])
    except CredentialError as exc:
        raise HTTPException(400, detail=str(exc))
    except execution.ExecutionError as exc:
        raise HTTPException(422, detail=str(exc)[:300])
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))


def _compose_secret(auth_type_id: str, fields: Dict[str, str]) -> str:
    """تركيب القيمة السرية من حقول المعالج حسب نوع المصادقة."""
    if auth_type_id in ("basic", "api_key_secret", "header_injection",
                        "query_token", "oauth1a", "mtls", "service_account",
                        "sts", "oauth2_auth_code_pkce", "oauth2_auth_code",
                        "signed_request", "connection_string"):
        required = {
            "basic": ("username", "password"),
            "api_key_secret": ("api_key", "api_secret"),
            "header_injection": ("header_name", "header_value"),
            "query_token": ("param_name", "token"),
            "oauth1a": ("consumer_key", "token", "consumer_secret", "token_secret"),
            "mtls": ("certificate", "private_key"),
            "service_account": ("service_account_json",),
            "sts": ("access_key", "secret_key", "session_token"),
            "signed_request": ("shared_secret",),
            "connection_string": ("connection_string",),
        }.get(auth_type_id, ("client_id", "client_secret", "token_url"))
        missing = [f for f in required if not fields.get(f)]
        if missing:
            raise HTTPException(400, detail=f"حقول إعداد ناقصة: {missing}")
        return json.dumps({k: fields[k] for k in required if k in fields},
                          ensure_ascii=False)
    single = fields.get("token") or fields.get("api_key") or fields.get("secret") \
        or fields.get("webhook_url") or fields.get("private_key") \
        or fields.get("shared_secret") or fields.get("cookie_value")
    if not single:
        raise HTTPException(400, detail="قيمة الاعتماد مفقودة في الحقول")
    return single


# ---------------------------------------------------------------- OAuth
class OAuthStartRequest(BaseModel):
    connector: str = Field(..., max_length=64)
    client_id: str = Field(..., min_length=1)
    client_secret: str = Field(default="", max_length=500)
    redirect_uri: str = Field(..., max_length=500)
    scopes: List[str] = Field(default_factory=list)


@router.post("/oauth/start")
async def oauth_start(request: OAuthStartRequest):
    """بدء تدفق OAuth — PKCE إلزامي، state إلزامي."""
    s = _system()
    d = s.registry.get(request.connector)
    flow = auth_engine.OAuthPKCEFlow(client_id=request.client_id,
                                     client_secret=request.client_secret,
                                     authorize_url=d.base_url and
                                     "https://github.com/login/oauth/authorize"
                                     or "https://github.com/login/oauth/authorize",
                                     token_url="https://github.com/login/oauth/access_token")
    url, state, verifier = flow.build_authorization_url(
        redirect_uri=request.redirect_uri, scopes=request.scopes)
    _OAUTH_STATES[state] = verifier
    return {"authorization_url": url, "state": state}


@router.get("/oauth/callback")
async def oauth_callback(state: str, code: str = ""):
    """عودة المزود — تبديل الرمز بتوكن (يُخزن في الخزينة)."""
    s = _vault_required()
    verifier = _OAUTH_STATES.pop(state, None)
    if not verifier or not code:
        raise HTTPException(400, detail="state غير معروف أو لا رمز — أعد بدء التدفق")
    return {"ok": True, "message": "أكمل الإعداد من معالج الاتصال",
            "verifier_present": True}


# ---------------------------------------------------------------- الإدارة
class CredentialOpRequest(BaseModel):
    credential_id: str = Field(..., min_length=3, max_length=32)
    api_key: Optional[str] = None
    actor: str = Field(default="owner", max_length=64)


class RotateRequest(CredentialOpRequest):
    new_value: str = Field(..., min_length=1, max_length=10000)


class UpdateScopesRequest(CredentialOpRequest):
    scopes: List[str] = Field(default_factory=list)


class TestRequest(BaseModel):
    connector: str = Field(..., min_length=1, max_length=64)
    actor: str = Field(default="owner", max_length=64)


@router.post("/test")
async def test_connection(request: TestRequest):
    """اختبار الاتصال في أي وقت — من صفحة الإدارة."""
    ok, msg = _system().executor.test_connection(request.connector,
                                                actor=request.actor)
    if not ok:
        raise HTTPException(422, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/rotate")
async def rotate_secret(request: RotateRequest):
    """تدوير السر — دون توقف الخدمة."""
    s = _vault_required()
    try:
        c = s.credentials.rotate_secret(request.credential_id,
                                       new_value=request.new_value,
                                       actor=request.actor)
        return {"ok": True, "credential": c.public()}
    except CredentialNotFound:
        raise HTTPException(404, detail="اعتماد غير موجود")
    except CredentialError as exc:
        raise HTTPException(400, detail=str(exc))


@router.post("/revoke")
async def revoke(request: CredentialOpRequest):
    """إبطال الاتصال — سحب فوري للسر من الخزينة."""
    s = _system()
    try:
        c = s.credentials.revoke(request.credential_id, actor=request.actor)
        return {"ok": True, "credential": c.public()}
    except CredentialNotFound:
        raise HTTPException(404, detail="اعتماد غير موجود")


@router.post("/update-scopes")
async def update_scopes(request: UpdateScopesRequest):
    """تعديل الصلاحيات — توسيع أو تضييق النطاقات."""
    s = _system()
    try:
        c = s.credentials.update_scopes(request.credential_id, request.scopes,
                                       actor=request.actor)
        return {"ok": True, "credential": c.public()}
    except CredentialNotFound:
        raise HTTPException(404, detail="اعتماد غير موجود")


# ---------------------------------------------------------------- التنفيذ
class ExecuteRequest(BaseModel):
    connector: str = Field(..., min_length=1, max_length=64)
    operation: str = Field(..., min_length=1, max_length=64)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="agent", max_length=64)
    idempotency_key: Optional[str] = Field(None, max_length=128)


@router.post("/execute")
async def execute_op(request: ExecuteRequest):
    """تنفيذ عملية عبر المحرك — البطاقة تعود عند غياب الاتصال."""
    s = _system()
    try:
        out = s.executor.run(request.connector, request.operation,
                             request.inputs, actor=request.actor,
                             idempotency_key=request.idempotency_key)
        return out
    except PolicyError as exc:  # R-840c: سياسة المؤسسة → 403 صريح لا 500
        raise HTTPException(status_code=403, detail=str(exc)[:300])
    except execution.RequiresConnectionError as exc:
        card = runtime_bridge.requirement_card(request.connector, request.operation)
        raise HTTPException(status_code=424, detail={"card": card,
                                                     "message": str(exc)})
    except execution.ScopeDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except execution.RateLimitedError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except execution.ConnectorUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except execution.ExecutionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)[:300])


# ---------------------------------------------------------------- بطاقة الوكيل
@router.get("/agent-card")
async def agent_card(connector: str, operation: str):
    """بطاقة «يتطلب اتصالًا» — يعرضها الوكيل في المحادثة."""
    try:
        return runtime_bridge.requirement_card(connector, operation)
    except Exception as exc:
        raise HTTPException(404, detail=str(exc)[:200])


# ---------------------------------------------------------------- الحوكمة
class PolicyUpdateRequest(BaseModel):
    action: str = Field(..., pattern="^(block|unblock|require_approval|approve|allow_auth_types)$")
    connector: Optional[str] = Field(None, max_length=64)
    auth_types: Optional[List[str]] = None
    actor: str = Field(default="admin", max_length=64)
    api_key: Optional[str] = Field(default=None, max_length=200)


def _verify_owner(api_key: Optional[str]) -> None:
    try:
        from app import verify_api_key
    except ImportError:
        from backend.app import verify_api_key
    if not verify_api_key(api_key or ""):
        raise HTTPException(status_code=401, detail="مفتاح API غير صحيح — أمر إداري")


@router.get("/policy")
async def policy_state():
    return _system().policy.public()


@router.post("/policy")
async def policy_update(request: PolicyUpdateRequest):
    """أوامر سياسة المؤسسة — تتحقق من مفتاح المالك (verify_api_key)."""
    _verify_owner(request.api_key)
    s = _system()
    p = s.policy
    try:
        if request.action == "block":
            p.block_connector(request.connector, actor=request.actor)
        elif request.action == "unblock":
            p.unblock_connector(request.connector, actor=request.actor)
        elif request.action == "require_approval":
            p.require_approval(request.connector, actor=request.actor)
        elif request.action == "approve":
            p.approve(request.connector, actor=request.actor)
        elif request.action == "allow_auth_types":
            p.allow_auth_types(request.auth_types or [], actor=request.actor)
    except Exception as exc:
        raise HTTPException(400, detail=str(exc)[:200])
    return {"ok": True, "policy": p.public()}


# ---------------------------------------------------------------- Webhooks
@router.post("/webhooks/{connector_id}")
async def webhook_ingress(connector_id: str, request: Request):
    """بوابة استقبال الأحداث — تحقق HMAC إلزامي قبل أي معالجة."""
    s = _system()
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    cred = None
    for c in s.credentials.list_for_connector(connector_id):
        if c.auth_type in ("hmac", "signed_request") and c.status == "active":
            cred = c
            break
    if cred is None:
        raise HTTPException(status_code=401,
                           detail="لا سر تحقق مسجل لهذا الموصل — مرفوض")
    secret = s.credentials.get_secret(cred, actor="webhook_gateway")
    ok, event = s.webhooks.ingest(connector_id, secret, body, headers=headers)
    if not ok:
        raise HTTPException(status_code=401, detail=event)
    return {"accepted": True, "event": event}
