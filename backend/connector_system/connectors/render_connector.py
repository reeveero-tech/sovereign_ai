# -*- coding: utf-8 -*-
"""R-840: موصل Render — مفتاح API فقط (الطويل الذيل: SaaS بمفتاح)."""
from __future__ import annotations

from .. import execution
from ..contract import ConnectorDefinition, Operation

BASE = "https://api.render.com/v1"


def _call(material, http, method: str, url: str, **kw):
    headers = {"Accept": "application/json"}
    headers.update(material.headers)
    r = http(method, url, headers=headers, **kw)
    exc = execution.classify_http(r.status_code)
    if exc is not None:
        raise exc
    if r.status_code >= 400:
        raise execution.ConnectorExecutionError(f"Render HTTP {r.status_code}")
    return r


def services_list(material, inputs, http):
    r = _call(material, http, "GET", f"{BASE}/services")
    return {"ok": True,
            "services": [s.get("service", {}).get("name") for s in r.json() or []]}


def deploys_list(material, inputs, http):
    r = _call(material, http, "GET", f"{BASE}/services/{inputs['service_id']}/deploys")
    return {"ok": True, "deploys": [d.get("id") for d in r.json() or []]}


def definition(version: str = "1.0.0") -> ConnectorDefinition:
    return ConnectorDefinition(
        id="render", name="Render", version=version,
        description="إدارة خدمات Render — مفتاح API (قراءة أولًا)",
        icon="server", category="saas", platform_class="key_only",
        auth_types=["api_key"],
        operations={
            "services_list": Operation("services_list", "query",
                                        frozenset({"connector:read"}),
                                        "قائمة الخدمات", inputs={}),
            "deploys_list": Operation("deploys_list", "query",
                                       frozenset({"connector:read"}),
                                       "سجل النشر لخدمة",
                                       inputs={"service_id": "text"}),
            "test_connection": Operation("test_connection", "query",
                                        frozenset({"connector:read"}),
                                        "اختبار الاتصال", inputs={}),
        },
        handlers={"services_list": services_list, "deploys_list": deploys_list,
                  "test_connection": services_list},
        base_url=BASE, docs_url="https://api-docs.render.com/")
