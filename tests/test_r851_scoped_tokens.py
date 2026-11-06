# -*- coding: utf-8 -*-
"""R-851 (٦.٧.٢): رموز محدودة النطاق — تكامل الواجهة.

المنطق نفسه مغطى بالمجموعة المجمّدة auth.scoped_tokens (20 حالة)؛ هنا: الربط
بالنقاط الحية — المفتاح الرئيسي يمر بكل شيء، الرمز بنطاقه فقط، والعمليات
الإدارية لا تقبل رمزًا أبدًا.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


@pytest.fixture
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app as app_mod
    import scoped_tokens
    events = []
    mgr = scoped_tokens.TokenManager(tmp_path, key=b"t" * 32, store=None,
                                     audit=lambda e, p: events.append((e, p)))
    monkeypatch.setattr(scoped_tokens, "_MGR", mgr)
    master = app_mod._derive_api_auth("api_auth")
    with TestClient(app_mod.app) as client:
        yield client, app_mod, mgr, master, events


def _issue(client, master, scopes, ttl=3600):
    r = client.post("/auth/tokens", json={"api_key": master, "scopes": scopes,
                                          "ttl_seconds": ttl, "label": "test"})
    assert r.status_code == 200, r.text
    return r.json()


def test_r851_issue_requires_master(env):
    client, _, mgr, master, events = env
    body = {"scopes": ["read"], "ttl_seconds": 3600}
    assert client.post("/auth/tokens", json=body).status_code == 401
    tok = _issue(client, master, ["read", "tools", "skills.approve"])["token"]
    # رمز بكل النطاقات المتاحة لا يصدر رمزًا (الإدارة للمفتاح الرئيسي وحده)
    assert client.post("/auth/tokens", json={**body, "api_key": tok}).status_code == 401
    assert client.post("/auth/tokens/revoke", json={"api_key": tok, "jti": "x"}).status_code == 401
    assert client.get("/auth/tokens", headers={"X-Sovereign-Key": tok}).status_code == 401
    assert [e for e, _ in events] == ["auth.token_issued"]


def test_r851_issue_validation(env):
    client, _, _, master, _ = env
    bad = client.post("/auth/tokens", json={"api_key": master, "scopes": ["admin"],
                                            "ttl_seconds": 3600})
    assert bad.status_code == 400
    assert client.post("/auth/tokens", json={"api_key": master, "scopes": ["read"],
                                             "ttl_seconds": 10}).status_code == 400


def test_r851_scope_enforced_on_live_endpoints(env):
    client, _, _, master, _ = env
    read = _issue(client, master, ["read"])["token"]
    h = {"X-Sovereign-Key": read}
    assert client.get("/brain/settings", headers=h).status_code == 200
    assert client.get("/ws/settings", headers=h).status_code == 200
    put = client.put("/brain/settings", headers=h, json={})
    assert put.status_code == 401
    inv = client.post("/tools/invoke", json={"tool": "health.snapshot", "inputs": {},
                                             "api_key": read})
    assert inv.status_code == 401
    tools = _issue(client, master, ["tools"])["token"]
    assert client.post("/tools/invoke", json={"tool": "health.snapshot", "inputs": {},
                                              "api_key": tools}).status_code == 200
    assert client.get("/brain/settings", headers={"X-Sovereign-Key": tools}).status_code == 401


def test_r851_master_only_endpoints_reject_tokens(env):
    client, _, _, master, _ = env
    import scoped_tokens
    tok = _issue(client, master, sorted(scoped_tokens.SCOPES))["token"]
    assert client.post("/sovereign/reset", json={"api_key": tok}).status_code in (401, 403, 422)
    assert client.get("/api-key", headers={"X-API-Key": tok}).status_code == 403
    assert client.get("/api-key-header", headers={"X-API-Key": tok}).status_code == 403
    r = client.post("/sovereign/command", json={"command": "get_status", "api_key": tok})
    assert r.status_code in (401, 403) or r.json().get("success") is False


def test_r851_revoke_is_immediate(env):
    client, _, _, master, events = env
    t = _issue(client, master, ["read"])
    h = {"X-Sovereign-Key": t["token"]}
    assert client.get("/brain/settings", headers=h).status_code == 200
    r = client.post("/auth/tokens/revoke", json={"api_key": master, "jti": t["jti"]})
    assert r.status_code == 200 and r.json()["revoked"] is True
    assert client.get("/brain/settings", headers=h).status_code == 401
    listed = client.get("/auth/tokens", headers={"X-Sovereign-Key": master}).json()["tokens"]
    assert listed[0]["state"] == "revoked" and "token" not in listed[0]
    assert ("auth.token_revoked", {"jti": t["jti"]}) in events


def test_r851_whoami_and_status(env):
    client, _, _, master, _ = env
    assert client.get("/auth/whoami", headers={"X-Sovereign-Key": master}).json()["kind"] == "master"
    t = _issue(client, master, ["chat"])
    who = client.get("/auth/whoami", headers={"X-Sovereign-Key": t["token"]}).json()
    assert who == {"valid": True, "jti": t["jti"], "scopes": ["chat"],
                   "exp": t["expires_at"], "kind": "scoped"}
    assert client.get("/auth/whoami", headers={"X-Sovereign-Key": "nope"}).status_code == 401
    st = client.get("/auth/status").json()
    assert st["tokens"]["active"] == 1 and "chat" in st["scopes"]
    assert t["token"].split(".")[2] not in str(st)


def test_r851_authorize_function(env):
    _, app_mod, mgr, master, _ = env
    tok = mgr.issue(["chat"], 3600)["token"]
    assert app_mod.authorize(master, "tools") is True
    assert app_mod.authorize(tok, "chat") is True
    assert app_mod.authorize(tok, "tools") is False
    assert app_mod.authorize("", "read") is False
    assert app_mod.authorize(None, "read") is False


def test_r851_no_key_still_rejected_everywhere(env):
    client, *_ = env
    assert client.get("/ws/settings").status_code == 401
    assert client.get("/brain/settings").status_code == 401
    assert client.post("/skills/sync", json={}).status_code == 401
    assert client.post("/tools/invoke", json={"tool": "health.snapshot",
                                              "inputs": {}}).status_code == 401


def test_r851_secret_rule_and_derivation_purpose():
    from secret_guard.catalog import RULES
    from sovereign.keys.derivation import PURPOSES
    assert "sovereign_scoped_token" in {r.id for r in RULES}
    assert "scoped_tokens" in PURPOSES


def test_r851_suite_registered_and_green():
    from evaluation import suites
    s = suites.get("auth.scoped_tokens")
    assert s.floor == 1.0 and s.data_path.name == "auth_tokens_cases.json"
    assert suites.file_sha256(s.data_path) == s.sha256
    r = s.runner(s.data_path)
    assert r["score"] == 1.0 and r["n"] == 20, r["failures"]
