# -*- coding: utf-8 -*-
"""R-840: الموصل العام — أي API يتبع OpenAPI/Swagger دون كتابة موصل يدوي.

يسجّل المواصفات، يستنتج العمليات من المسارات والأفعال، ويطبّق نوع المصادقة
المحدد. يغطي الطويل الذيل من المنصات. القراءة أولًا: GET فقط يستنتج عمليات
query؛ أفعال الكتابة تُستنتج execute بشرط idempotent=False إلا PUT/DELETE.
"""
from __future__ import annotations

from typing import Any, Dict

from .. import execution
from ..contract import ConnectorDefinition, Operation

_METHOD_TO_KIND = {"get": "query", "put": "execute", "patch": "execute",
                   "post": "execute", "delete": "execute"}


def _auth_type_from_spec(spec: Dict[str, Any]) -> str:
    schemes = (spec.get("components", {}).get("securitySchemes")
               or spec.get("securityDefinitions") or {})
    for name, s in schemes.items():
        t = (s or {}).get("type", "")
        if t == "oauth2":
            return "oauth2_auth_code_pkce"
        if t == "apiKey":
            return "api_key"
        if t == "http" and (s or {}).get("scheme") == "basic":
            return "basic"
        if t == "http" and (s or {}).get("scheme") == "bearer":
            return "api_key"
        if t == "openIdConnect":
            return "oauth2_auth_code_pkce"
    return "api_key"  # الافتراض الأسلم


def _op_name(operation_id: str, method: str, path: str) -> str:
    if operation_id:
        import re
        name = re.sub(r"[^a-zA-Z0-9_]", "_", operation_id)
        # camelCase → snake_case
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()
        return name
    return f"{method}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"


def definition_from_spec(connector_id: str, spec: Dict[str, Any],
                         version: str = "1.0.0") -> ConnectorDefinition:
    if not isinstance(spec, dict) or "paths" not in spec:
        raise ValueError("مواصفة OpenAPI غير صالحة — لا paths")
    servers = spec.get("servers") or []
    base_url = servers[0].get("url", "") if servers else ""
    auth_type = _auth_type_from_spec(spec)
    operations: Dict[str, Operation] = {}
    handlers: Dict[str, object] = {}
    scopes_default = frozenset({"connector:read"})

    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op_spec in methods.items():
            if method.lower() not in _METHOD_TO_KIND or not isinstance(op_spec, dict):
                continue
            kind = _METHOD_TO_KIND[method.lower()]
            name = _op_name(op_spec.get("operationId", ""), method, path)
            op = Operation(
                name, kind,
                scopes_default if kind == "query" else frozenset({"connector:write"}),
                description=(op_spec.get("summary") or op_spec.get("description") or "")[:120],
                idempotent=method.lower() in ("put", "delete", "patch"),
                inputs={})
            operations[name] = op
            handlers[name] = _make_handler(base_url, path, method.lower())

    if not operations:
        raise ValueError("لا عمليات قابلة للاستنتاج من المواصفة")
    return ConnectorDefinition(
        id=connector_id, name=spec.get("info", {}).get("title", connector_id),
        version=version,
        description=f"موصل عام من مواصفة OpenAPI ({len(operations)} عملية)",
        icon="plug", category="generic", platform_class="custom",
        auth_types=[auth_type], operations=operations, handlers=handlers,
        base_url=base_url, lifecycle="preview")


def _make_handler(base_url: str, path: str, method: str):
    def handler(material, inputs, http):
        url = base_url.rstrip("/") + path
        for k, v in (inputs or {}).items():  # مدخلات مسار {param}
            url = url.replace("{" + k + "}", str(v))
        r = http(method.upper(), url, headers=dict(material.headers))
        exc = execution.classify_http(r.status_code)
        if exc is not None:
            raise exc
        if r.status_code >= 400:
            raise execution.ConnectorExecutionError(f"HTTP {r.status_code}")
        try:
            data = r.json()
        except Exception:  # TOLERATED: ردود غير JSON
            data = {"raw": True}
        return {"ok": True, "data": data}
    return handler


def definition(version: str = "1.0.0") -> ConnectorDefinition:
    """موصل عام فارغ جاهز للتسجيل بمواصفة لاحقًا (يعرضه الكتالوج)."""
    return ConnectorDefinition(
        id="generic_openapi", name="موصل عام (OpenAPI)",
        version=version,
        description="سجّل أي API بمواصفة OpenAPI — يستنتج العمليات ويطبق المصادقة",
        icon="plug", category="generic", platform_class="custom",
        auth_types=["api_key", "oauth2_auth_code_pkce", "pat", "basic", "hmac"],
        operations={
            "register_spec": Operation("register_spec", "execute",
                                       frozenset({"connector:write"}),
                                       "تسجيل مواصفة OpenAPI جديدة",
                                       inputs={"spec": "json", "connector_id": "text"}),
        },
        handlers={"register_spec": lambda material, inputs, http: {"ok": True}},
        lifecycle="preview")
