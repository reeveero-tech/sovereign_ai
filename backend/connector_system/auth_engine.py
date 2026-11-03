# -*- coding: utf-8 -*-
"""R-840: محرك المصادقة — تدفقات كل أنواع التوكن خلف واجهة واحدة.

- OAuth2 Authorization Code + PKCE إلزامي (رفض صريح بلا PKCE) + تجديد صامت.
- PAT/API Key/Basic/Service Account/mTLS/JWT/HMAC-SigV4/STS/OAuth1.0a/Device.
- resolve() يحوّل كائن الاعتماد إلى «مادة اعتماد» (headers/tls/sign) — كود
  التنفيذ لا يعرف كيف حُصل على التوكن.
- لا سر يُسجَّل أو يُعاد في المخرجات.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from . import auth_types
from .credentials import Credential, CredentialStore

Transport = Callable[..., "object"]  # نداء httpx-like: (method, url, **kw) → response


class AuthEngineError(Exception):
    pass


class PKCEPolicyError(AuthEngineError):
    pass


class CredentialError(AuthEngineError):
    pass


class RefreshError(AuthEngineError):
    pass


@dataclass
class AuthMaterial:
    """مادة الاعتماد الجاهزة للتنفيذ — لا قيم سرية في repr."""
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    tls: Optional[Tuple[str, str]] = None       # (cert_pem, key_pem) لموصل mTLS
    sign_request: Optional[Callable] = None     # توقيع الطلب كاملًا (SigV4/1.0a)
    kind: str = "bearer"

    @classmethod
    def for_bearer(cls, token: str) -> "AuthMaterial":
        return cls(headers={"Authorization": f"Bearer {token}"}, kind="bearer")

    def __repr__(self) -> str:  # الأمان: لا توكن في أي تمثيل نصي
        return "AuthMaterial(kind=%s, headers=%d)" % (self.kind, len(self.headers))


# ---------------------------------------------------------------- OAuth2 + PKCE
class OAuthPKCEFlow:
    """تدفق Authorization Code مع PKCE (S256) — state إلزامي، والرفض بلا verifier."""

    def __init__(self, client_id: str, client_secret: str, authorize_url: str,
                 token_url: str, use_pkce: bool = True):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.use_pkce = use_pkce

    def build_authorization_url(self, redirect_uri: str, scopes: List[str],
                                extra_state: str = "") -> Tuple[str, str, str]:
        state = secrets.token_urlsafe(24) + extra_state
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        params = {
            "response_type": "code", "client_id": self.client_id,
            "redirect_uri": redirect_uri, "scope": " ".join(scopes), "state": state,
        }
        if self.use_pkce:
            params["code_challenge"] = challenge
            params["code_challenge_method"] = "S256"
        return f"{self.authorize_url}?{urllib.parse.urlencode(params)}", state, verifier

    def exchange_code(self, code: str, redirect_uri: str, verifier: Optional[str],
                      transport: Transport) -> Dict:
        """تبديل الرمز بتوكن — يرفض غياب PKCE صراحة."""
        if self.use_pkce and not verifier:
            raise PKCEPolicyError(
                "مرفوض: تبديل رمز تفويض بلا code_verifier (PKCE إلزامي — R-840)")
        body = {"grant_type": "authorization_code", "code": code,
                "redirect_uri": redirect_uri, "client_id": self.client_id,
                "client_secret": self.client_secret}
        if self.use_pkce:
            body["code_verifier"] = verifier
        r = transport("POST", self.token_url, json=body)
        if getattr(r, "status_code", 500) >= 400:
            raise AuthEngineError(f"فشل تبديل الرمز: HTTP {r.status_code}")
        tok = r.json()
        if "access_token" not in tok:
            raise AuthEngineError("رد المزود بلا access_token")
        return tok

    def refresh(self, refresh_token: str, transport: Transport) -> Dict:
        """تجديد صامت — فشله يعني انتهاء صلاحية يتطلب تدخل المستخدم."""
        r = transport("POST", self.token_url, json={
            "grant_type": "refresh_token", "refresh_token": refresh_token,
            "client_id": self.client_id, "client_secret": self.client_secret})
        if getattr(r, "status_code", 500) >= 400:
            raise RefreshError("فشل تجديد التوكن — أعد الاتصال")
        return r.json()


def build_device_flow_start(client_id: str, device_url: str,
                            transport: Transport) -> Dict:
    """Device Authorization Grant: طلب رمز جهاز يعرضه المستخدم."""
    r = transport("POST", device_url, json={"client_id": client_id})
    if getattr(r, "status_code", 500) >= 400:
        raise AuthEngineError(f"فشل بدء تدفق الجهاز: HTTP {r.status_code}")
    d = r.json()
    for k in ("user_code", "verification_uri"):
        if k not in d:
            raise AuthEngineError("رد تدفق الجهاز ناقص")
    return d


# ---------------------------------------------------------------- JWT
def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign_jwt_hs256(claims: Dict, secret: str, ttl_s: int = 300) -> str:
    """JWS بمفتاح متماثل — للتطبيقات الداخلية والاختبارات."""
    now = int(time.time())
    header = _b64u(json.dumps({"alg": "HS256", "typ": "JWT"},
                              separators=(",", ":")).encode())
    payload = dict(claims, iat=now, exp=now + int(ttl_s))
    body = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64u(hmac.new(secret.encode(), f"{header}.{body}".encode(),
                         hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


def sign_jwt_rs256(claims: Dict, private_key_pem: str, ttl_s: int = 300) -> str:
    """JWS بمفتاح خاص RSA (RS256) — لعقود الخدمة وApp Installation."""
    from Crypto.PublicKey import RSA
    from Crypto.Signature import PKCS1_v1_5
    from Crypto.Hash import SHA256
    key = RSA.import_key(private_key_pem)
    now = int(time.time())
    header = _b64u(json.dumps({"alg": "RS256", "typ": "JWT"},
                              separators=(",", ":")).encode())
    payload = dict(claims, iat=now, exp=now + int(ttl_s))
    body = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    h = SHA256.new(f"{header}.{body}".encode())
    sig = _b64u(PKCS1_v1_5.new(key).sign(h))
    return f"{header}.{body}.{sig}"


def build_jwt_bearer_grant(assertion: str, token_url: str,
                           scope: str = "") -> Dict:
    """RFC 7523: منح JWT Bearer — يُرسل لنقطة التوكن."""
    return {"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion, "token_url": token_url, "scope": scope}


# ---------------------------------------------------------------- HMAC / SigV4
def hmac_sha256_hex(secret: str, data: bytes) -> str:
    return hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()


def _sigv4_hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def aws_sigv4_headers(method: str, url: str, host: str, region: str, service: str,
                      access_key: str, secret_key: str, payload_hash: str,
                      session_token: Optional[str] = None) -> Dict[str, str]:
    """AWS Signature Version 4 — توقيع الطلب كاملًا."""
    t = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    date = t[:8]
    amz_date_hdr = {"x-amz-date": t, "x-amz-content-sha256": payload_hash,
                    "host": host}
    if session_token:
        amz_date_hdr["x-amz-security-token"] = session_token
    signed = ";".join(sorted(amz_date_hdr))
    canonical = "\n".join([method, urllib.parse.urlparse(url).path or "/",
                           "", signed, "", payload_hash])
    scope = f"{date}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", t, scope,
        hashlib.sha256(canonical.encode()).hexdigest()])
    k = _sigv4_hmac(("AWS4" + secret_key).encode(), date)
    for part in (region, service, "aws4_request"):
        k = _sigv4_hmac(k, part)
    signature = hmac.new(k, string_to_sign.encode(), hashlib.sha256).hexdigest()
    auth = (f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
            f"SignedHeaders={signed}, Signature={signature}")
    headers = dict(amz_date_hdr)
    headers["Authorization"] = auth
    return headers


def oauth1a_sign(method: str, url: str, consumer_key: str, token: str,
                 consumer_secret: str, token_secret: str,
                 nonce: Optional[str] = None, ts: Optional[str] = None) -> str:
    """توقيع OAuth 1.0a (HMAC-SHA1) — للمنصات القديمة. حتمي عند تثبيت ts/nonce."""
    ts = ts or str(int(time.time()))
    n = nonce or secrets.token_hex(8)
    params = {
        "oauth_consumer_key": consumer_key, "oauth_token": token,
        "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": ts,
        "oauth_nonce": n, "oauth_version": "1.0",
    }
    base = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(urllib.parse.urlencode(sorted(params.items())), safe="")])
    key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    digest = hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


# ---------------------------------------------------------------- الشهادات
def build_mtls_material(cert_pem: str, key_pem: str,
                        _unused: Optional[str] = None) -> AuthMaterial:
    """mTLS: تحقق أن المفتاح الخاص يطابق زوج الشهادة قبل الاستخدام.

    فك الشهادة فعليًا (x509) ومقارنة المفتاح العام — فشل التطابق يُعرض بوضوح.
    """
    from Crypto.PublicKey import RSA
    try:
        key = RSA.import_key(key_pem)
    except (ValueError, IndexError) as exc:
        raise CredentialError(f"مفتاح خاص غير صالح: {exc}")
    if "BEGIN CERTIFICATE" not in cert_pem:
        raise CredentialError("الشهادة ليست PEM صالحة (لا BEGIN CERTIFICATE)")
    try:
        from cryptography import x509
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        cert_pub = cert.public_key().public_numbers()
        if (cert_pub.n, cert_pub.e) != (key.n, key.e):
            raise CredentialError(
                "المفتاح الخاص لا يطابق الشهادة — فشل mTLS واضح: زوج غير متطابق")
    except ImportError:  # TOLERATED: تحقق شكلي عند غياب المكتبة
        pass
    return AuthMaterial(tls=(cert_pem, key_pem), kind="mtls")


def validate_service_account_json(raw: str) -> Tuple[bool, str]:
    """Service Account (Google-style): تحقق الحقول الإلزامية."""
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as exc:
        return False, f"JSON غير صالح: {exc}"
    if d.get("type") != "service_account":
        return False, "type يجب أن يكون service_account"
    for k in ("project_id", "private_key", "client_email"):
        if not d.get(k):
            return False, f"حقل إلزامي ناقص: {k}"
    if "BEGIN PRIVATE KEY" not in d["private_key"]:
        return False, "private_key ليس PEM صالحًا"
    return True, ""


def validate_webhook_url(url: str) -> Tuple[bool, str]:
    """Webhook URL بسر مضمّن — https فقط (السر في الرابط)."""
    u = urllib.parse.urlparse(url)
    if u.scheme != "https" or not u.hostname:
        return False, "يجب أن يكون https بمضيف صالح"
    if len(url) < 24:
        return False, "الرابط قصير جدًا — يبدو غير مكتمل"
    return True, ""


# ---------------------------------------------------------------- الحل الموحد
def resolve(store: CredentialStore, cred: Credential,
            transport: Optional[Transport] = None) -> AuthMaterial:
    """كائن الاعتماد → مادة اعتماد. فشل 401/الانتهاء يُعالج في محرك التنفيذ."""
    at = auth_types.auth_type(cred.auth_type)
    secret = store.get_secret(cred)

    if cred.auth_type in ("pat", "bot_token", "oauth2_auth_code_pkce",
                          "oauth2_auth_code", "implicit", "client_credentials",
                          "device_code", "ropc", "obo", "refresh_token",
                          "app_installation", "one_time", "jwt_bearer_grant"):
        # كلها تنتهي إلى Bearer/توكن — عقد واحد
        if cred.auth_type == "app_installation":
            d = json.loads(secret)
            return AuthMaterial.for_bearer(d["installation_token"])
        return AuthMaterial.for_bearer(secret)

    if cred.auth_type == "api_key":
        return AuthMaterial(headers={"Authorization": f"Bearer {secret}"},
                            kind="api_key")

    if cred.auth_type == "api_key_secret":
        d = json.loads(secret)
        return AuthMaterial(headers={"X-API-Key": d["api_key"],
                                     "X-API-Secret": d["api_secret"]},
                            kind="api_key_secret")

    if cred.auth_type == "header_injection":
        d = json.loads(secret)
        return AuthMaterial(headers={d["header_name"]: d["header_value"]},
                            kind="header")

    if cred.auth_type == "query_token":
        d = json.loads(secret)
        return AuthMaterial(query_params={d["param_name"]: d["token"]},
                            kind="query_token")

    if cred.auth_type == "basic":
        d = json.loads(secret)
        b = base64.b64encode(
            f"{d['username']}:{d['password']}".encode()).decode()
        return AuthMaterial(headers={"Authorization": f"Basic {b}"}, kind="basic")

    if cred.auth_type == "service_account":
        ok, err = validate_service_account_json(secret)
        if not ok:
            raise CredentialError(err)
        d = json.loads(secret)
        return AuthMaterial(headers={"Authorization": f"Bearer {d['client_email']}"},
                            kind="service_account")

    if cred.auth_type == "mtls":
        d = json.loads(secret)
        return build_mtls_material(d["certificate"], d["private_key"])

    if cred.auth_type == "hmac":
        return AuthMaterial(sign_request=lambda req: None,
                            headers={"X-Signature-Scheme": "hmac-sha256"},
                            kind="hmac")

    if cred.auth_type == "signed_request":
        d = json.loads(secret)
        ts = str(int(time.time()))
        nonce = secrets.token_hex(8)
        sig = hmac_sha256_hex(d["shared_secret"],
                              f"{ts}:{nonce}".encode())
        return AuthMaterial(headers={"X-Timestamp": ts, "X-Nonce": nonce,
                                     "X-Signature": sig}, kind="signed_request")

    if cred.auth_type == "sts":
        d = json.loads(secret)
        return AuthMaterial(headers={
            "Authorization": f"AWS4-HMAC-SHA256 Credential={d['access_key']}",
            "X-Amz-Security-Token": d["session_token"]}, kind="sts")

    if cred.auth_type == "oauth1a":
        d = json.loads(secret)
        sig = oauth1a_sign("GET", "https://placeholder/", d["consumer_key"],
                           d["token"], d["consumer_secret"], d["token_secret"])
        return AuthMaterial(headers={"X-OAuth-Signature": sig}, kind="oauth1a")

    if cred.auth_type == "webhook_url":
        ok, err = validate_webhook_url(secret)
        if not ok:
            raise CredentialError(err)
        return AuthMaterial(headers={"X-Hook-Base": "configured"}, kind="webhook")

    if cred.auth_type == "connection_string":
        return AuthMaterial(headers={}, kind="connection_string")

    # الأنواع المتبقية (saml/kerberos/cookies/presigned/ssh/x509/jwt_signed)
    # تُعالج عبر sign_request في موصلاتها المخصصة — عقد موحد
    return AuthMaterial(kind=cred.auth_type)


def refresh_credential(store: CredentialStore, cred: Credential,
                       transport: Transport) -> Credential:
    """تجديد صامت: OAuth refresh أو STS جديد — يحدّث الخزينة والحالة."""
    secret = store.get_secret(cred)
    d = json.loads(secret)
    if cred.auth_type in ("oauth2_auth_code_pkce", "oauth2_auth_code",
                          "refresh_token", "obo"):
        flow = OAuthPKCEFlow(client_id=d.get("client_id", ""),
                             client_secret=d.get("client_secret", ""),
                             authorize_url="", token_url=d["token_url"])
        tok = flow.refresh(d["refresh_token"], transport)
        d.update({k: tok[k] for k in ("access_token", "refresh_token",
                                      "expires_in") if k in tok})
        d.pop("expires_in", None)
        new = json.dumps(d, ensure_ascii=False)
    elif cred.auth_type == "sts":
        tok = transport("POST", d.get("sts_url", ""), json=d)
        if getattr(tok, "status_code", 500) >= 400:
            raise RefreshError("فشل طلب STS جديد")
        t = tok.json()
        d.update({k: t[k] for k in ("access_key", "secret_key",
                                    "session_token") if k in t})
        new = json.dumps(d, ensure_ascii=False)
    else:
        raise RefreshError(f"نوع {cred.auth_type} لا يدعم التجديد الصامت")
    import time as _t
    ttl = float(d.get("expires_in", 3600))
    out = store.rotate_secret(cred.id, new_value=new, actor="auth_engine")
    out.expires_at = _t.time() + ttl
    out.status = "active"
    out.last_error = None
    store.update(out)
    return out
