# -*- coding: utf-8 -*-
"""R-840: موصل Supabase — مفتاح خدمة واسع (يُطلب أقل صلاحية عند الإمكان)."""
from __future__ import annotations

import urllib.parse

from .. import execution
from ..contract import ConnectorDefinition, Operation


def _call(material, http, method: str, url: str, **kw):
    headers = {}
    headers.update(material.headers)
    r = http(method, url, headers=headers, **kw)
    exc = execution.classify_http(r.status_code)
    if exc is not None:
        raise exc
    if r.status_code >= 400:
        raise execution.ConnectorExecutionError(f"Supabase HTTP {r.status_code}")
    return r


def _base(inputs):
    return inputs.get("base_url", "https://placeholder.supabase.co")


def table_select(material, inputs, http):
    table = urllib.parse.quote(inputs["table"], safe="")
    r = _call(material, http, "GET",
              f"{_base(inputs)}/rest/v1/{table}?select=*&limit=5")
    rows = r.json()
    return {"ok": True, "rows": rows if isinstance(rows, list) else []}


def test_connection(material, inputs, http):
    r = _call(material, http, "GET", f"{_base(inputs)}/rest/v1/")
    return {"ok": True}


def definition(version: str = "1.0.0") -> ConnectorDefinition:
    return ConnectorDefinition(
        id="supabase", name="Supabase", version=version,
        description="قاعدة بيانات Supabase — مفتاح خدمة (REST)",
        icon="database", category="database", platform_class="key_only",
        auth_types=["api_key", "connection_string"],
        operations={
            "table_select": Operation("table_select", "query",
                                      frozenset({"db:read"}),
                                      "قراءة جدول (٥ صفوف)",
                                      inputs={"table": "text", "base_url": "url"}),
            "test_connection": Operation("test_connection", "query",
                                         frozenset({"db:read"}),
                                         "اختبار الاتصال",
                                         inputs={"base_url": "url"}),
        },
        handlers={"table_select": table_select, "test_connection": test_connection},
        base_url="", docs_url="https://supabase.com/docs/reference/api")
