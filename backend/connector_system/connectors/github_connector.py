# -*- coding: utf-8 -*-
"""R-840: موصل GitHub — OAuth (PKCE) أو PAT، بنطاقات مفصولة قراءة/كتابة.

كل عملية تحدد نطاقاتها الدقيقة: قراءة المستودعات لا تمنح كتابة أبدًا.
المعالجات عقد واحد: (مادة الاعتماد، المدخلات، نداء http) — لا سر يُمرر.
"""
from __future__ import annotations

from .. import execution
from ..contract import ConnectorDefinition, Operation

BASE = "https://api.github.com"


def _call(material, http, method: str, url: str, **kw):
    headers = {"Accept": "application/vnd.github+json"}
    headers.update(material.headers)
    r = http(method, url, headers=headers, **kw)
    exc = execution.classify_http(r.status_code)
    if exc is not None:
        raise exc
    if r.status_code >= 400:
        raise execution.ConnectorExecutionError(f"GitHub HTTP {r.status_code}")
    return r


def repo_read(material, inputs, http):
    r = _call(material, http, "GET",
              f"{BASE}/repos/{inputs['owner']}/{inputs['repo']}")
    d = r.json()
    return {"ok": True, "repo": d.get("full_name"),
            "private": d.get("private"), "default_branch": d.get("default_branch")}


def repo_list(material, inputs, http):
    r = _call(material, http, "GET", f"{BASE}/user/repos", params={"per_page": 5})
    return {"ok": True, "repos": [x.get("full_name") for x in r.json()]}


def issue_create(material, inputs, http):
    r = _call(material, http, "POST",
              f"{BASE}/repos/{inputs['owner']}/{inputs['repo']}/issues",
              json={"title": inputs["title"],
                    "body": inputs.get("body", "")})
    d = r.json()
    return {"ok": True, "issue_number": d.get("number"), "url": d.get("html_url")}


def test_connection(material, inputs, http):
    r = _call(material, http, "GET", f"{BASE}/user")
    return {"ok": True, "login": r.json().get("login")}


def definition(version: str = "1.0.0") -> ConnectorDefinition:
    return ConnectorDefinition(
        id="github", name="GitHub", version=version,
        description="مستودعات GitHub — قراءة/كتابة ضمن نطاقات محددة (OAuth+PKCE أو PAT)",
        icon="github", category="dev", platform_class="oauth",
        auth_types=["oauth2_auth_code_pkce", "pat", "app_installation"],
        operations={
            "repo_read": Operation("repo_read", "query",
                                   frozenset({"repo:read"}),
                                   "قراءة بيانات مستودع", inputs={"owner": "text", "repo": "text"}),
            "repo_list": Operation("repo_list", "query",
                                   frozenset({"repo:read"}),
                                   "قائمة مستودعاتي", inputs={}),
            "issue_create": Operation("issue_create", "execute",
                                       frozenset({"repo:write"}), idempotent=True,
                                       description="فتح مشكلة — كتابة",
                                       inputs={"owner": "text", "repo": "text",
                                               "title": "text", "body": "text"}),
            "test_connection": Operation("test_connection", "query",
                                         frozenset({"repo:read"}),
                                         "اختبار الاتصال", inputs={}),
        },
        handlers={"repo_read": repo_read, "repo_list": repo_list,
                  "issue_create": issue_create, "test_connection": test_connection},
        base_url=BASE, docs_url="https://docs.github.com/rest")
