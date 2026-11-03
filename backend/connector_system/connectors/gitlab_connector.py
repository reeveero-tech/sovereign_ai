# -*- coding: utf-8 -*-
"""R-840: موصل GitLab — PAT أو OAuth، والتبديل بينهما لا يمس كود التنفيذ.

المصادقتان تنتجان مادة Bearer واحدة — عقد واحد في المحرك (معيار القبول ٢).
"""
from __future__ import annotations

from .. import execution
from ..contract import ConnectorDefinition, Operation

BASE = "https://gitlab.com/api/v4"


def _call(material, http, method: str, url: str, **kw):
    headers = {}
    headers.update(material.headers)
    r = http(method, url, headers=headers, **kw)
    exc = execution.classify_http(r.status_code)
    if exc is not None:
        raise exc
    if r.status_code >= 400:
        raise execution.ConnectorExecutionError(f"GitLab HTTP {r.status_code}")
    return r


def project_read(material, inputs, http):
    import urllib.parse
    path = urllib.parse.quote(f"{inputs['owner']}/{inputs['repo']}", safe="")
    r = _call(material, http, "GET", f"{BASE}/projects/{path}")
    d = r.json()
    return {"ok": True, "project": d.get("path_with_namespace")}


def projects_list(material, inputs, http):
    r = _call(material, http, "GET", f"{BASE}/projects",
              params={"membership": "true", "per_page": 5})
    return {"ok": True, "projects": [x.get("path_with_namespace") for x in r.json()]}


def issue_create(material, inputs, http):
    import urllib.parse
    path = urllib.parse.quote(f"{inputs['owner']}/{inputs['repo']}", safe="")
    r = _call(material, http, "POST", f"{BASE}/projects/{path}/issues",
              json={"title": inputs["title"],
                    "description": inputs.get("body", "")})
    return {"ok": True, "iid": r.json().get("iid")}


def test_connection(material, inputs, http):
    r = _call(material, http, "GET", f"{BASE}/user")
    return {"ok": True, "username": r.json().get("username")}


def definition(version: str = "1.0.0") -> ConnectorDefinition:
    return ConnectorDefinition(
        id="gitlab", name="GitLab", version=version,
        description="GitLab — PAT أو OAuth بنفس مسار التنفيذ (تبديل بلا كود)",
        icon="gitlab", category="dev", platform_class="oauth",
        auth_types=["pat", "oauth2_auth_code_pkce"],
        operations={
            "repo_read": Operation("repo_read", "query", frozenset({"repo:read"}),
                                  "قراءة مشروع", inputs={"owner": "text", "repo": "text"}),
            "repo_list": Operation("repo_list", "query", frozenset({"repo:read"}),
                                   "قائمة مشاريعي", inputs={}),
            "issue_create": Operation("issue_create", "execute",
                                      frozenset({"repo:write"}), idempotent=True,
                                      description="فتح مشكلة — كتابة",
                                      inputs={"owner": "text", "repo": "text",
                                              "title": "text"}),
            "test_connection": Operation("test_connection", "query",
                                         frozenset({"repo:read"}),
                                         "اختبار الاتصال", inputs={}),
        },
        handlers={"repo_read": project_read, "repo_list": projects_list,
                  "issue_create": issue_create, "test_connection": test_connection},
        base_url=BASE, docs_url="https://docs.gitlab.com/ee/api/")
