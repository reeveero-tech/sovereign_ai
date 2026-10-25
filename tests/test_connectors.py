# -*- coding: utf-8 -*-
"""R-756 (ROADMAP_V5 ٤.١ — بأمر المالك 2026-10-25 «أسلمك المشروع»): عقد الموصل
المعزول.

قالب موصل واحد: مصادقة مملوكة (السر في الخزينة R-752 بنطاق `connector:<اسم>`)،
أذونات نطاقية لكل فعل (منحة المالك)، انتهاء صلاحية وتجديد ورفض آمن، **سحب
تفويض فوري** (يُفحص عند كل استدعاء)، فحص صحة، عزل فشل (قاطع دائرة لكل موصل)،
وأثر `connector_call` لكل استدعاء. أول موصل حقيقي: إشعار webhook (HTTP POST
بـBearer) — يُختبر حيًا ضد خادم HTTP محلي معزول (لا مصدر خارجي).
"""

import base64
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

TOKEN = "tok-test-0123456789"  # قيمة اختبار — ليست سرًا حقيقيًا


class _Src:
    """مصدر خارجي وهمي معزول: يسجل الطلبات، ويمكن جعله يفشل."""

    def __init__(self):
        self.requests, self.fail = [], False
        src = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                src.requests.append({"auth": self.headers.get("Authorization"),
                                     "idem": self.headers.get("Idempotency-Key"),
                                     "body": json.loads(body or b"{}")})
                code = 500 if src.fail else (401 if self.headers.get("Authorization")
                                             != f"Bearer {TOKEN}" else 200)
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"accepted": true}' if code == 200 else b'{}')

            def do_GET(self):
                self.send_response(500 if src.fail else 200)
                self.end_headers()

            def log_message(self, *a):
                pass
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/hook"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


@pytest.fixture
def env(tmp_path):
    from sovereign.secrets_vault import SecretsVault
    from connectors import ConnectorHub, webhook_connector
    events = []
    vault = SecretsVault(tmp_path / "v.json",
                         base64.b64encode(os.urandom(32)).decode(),
                         audit=lambda e, p: events.append((e, p)))
    src = _Src()
    hub = ConnectorHub(vault=vault, state_path=tmp_path / "grants.json",
                       audit=lambda e, p: events.append((e, p)),
                       failure_threshold=2, cooldown_s=60)
    hub.register(webhook_connector("notify", url=src.url, allow_loopback=True))
    vault.put("connector.notify", TOKEN, scopes=["connector:notify"], actor="owner")
    yield hub, vault, src, events
    src.close()


def test_owned_auth_and_scoped_permission(env):
    from connectors import PermissionDenied
    hub, _, src, events = env
    with pytest.raises(PermissionDenied):            # لا منحة = لا فعل
        hub.call("notify", "send", {"text": "x"})
    assert src.requests == []
    hub.grant("notify", ["send"], actor="owner")
    out = hub.call("notify", "send", {"text": "مرحبا"})
    assert out["ok"] is True and src.requests[-1]["auth"] == f"Bearer {TOKEN}"
    assert src.requests[-1]["body"]["text"] == "مرحبا"
    assert TOKEN not in json.dumps(events, ensure_ascii=False)   # لا سر في الأثر
    assert TOKEN not in json.dumps(out, ensure_ascii=False)
    assert any(e[0] == "connector.call" for e in events)


def test_action_outside_grant_refused(env):
    from connectors import PermissionDenied
    hub, _, src, _ = env
    hub.grant("notify", ["health"], actor="owner")
    with pytest.raises(PermissionDenied):
        hub.call("notify", "send", {"text": "x"})
    assert src.requests == []


def test_revocation_cuts_next_call_immediately(env):
    from connectors import PermissionDenied
    hub, _, src, events = env
    hub.grant("notify", ["send"], actor="owner")
    hub.call("notify", "send", {"text": "1"})
    hub.revoke("notify", actor="owner")
    with pytest.raises(PermissionDenied):
        hub.call("notify", "send", {"text": "2"})
    assert len(src.requests) == 1
    assert any(e[0] == "connector.revoke" for e in events)


def test_revocation_persists_across_hub_restart(env, tmp_path):
    from connectors import ConnectorHub, PermissionDenied, webhook_connector
    hub, vault, src, _ = env
    hub.grant("notify", ["send"], actor="owner")
    hub.revoke("notify", actor="owner")
    hub2 = ConnectorHub(vault=vault, state_path=tmp_path / "grants.json",
                        audit=lambda e, p: None)
    hub2.register(webhook_connector("notify", url=src.url, allow_loopback=True))
    with pytest.raises(PermissionDenied):
        hub2.call("notify", "send", {"text": "x"})


def test_expired_grant_refused_safely(env):
    from connectors import PermissionDenied
    hub, _, src, _ = env
    hub.grant("notify", ["send"], actor="owner", ttl_s=-1)   # منتهية فورًا
    with pytest.raises(PermissionDenied):
        hub.call("notify", "send", {"text": "x"})
    assert src.requests == []
    hub.renew("notify", ttl_s=3600, actor="owner")
    assert hub.call("notify", "send", {"text": "y"})["ok"] is True


def test_rotated_credential_used_and_bad_credential_fails_closed(env):
    hub, vault, src, _ = env
    hub.grant("notify", ["send"], actor="owner")
    vault.rotate("connector.notify", "wrong-token", actor="owner")
    out = hub.call("notify", "send", {"text": "x"})
    assert out["ok"] is False and "401" in out["error"]
    vault.rotate("connector.notify", TOKEN, actor="owner")
    assert hub.call("notify", "send", {"text": "x"})["ok"] is True


def test_missing_credential_refused_without_request(env, tmp_path):
    from connectors import ConnectorHub, CredentialError, webhook_connector
    hub, vault, src, _ = env
    hub.register(webhook_connector("other", url=src.url, allow_loopback=True))
    hub.grant("other", ["send"], actor="owner")
    with pytest.raises(CredentialError):
        hub.call("other", "send", {"text": "x"})
    assert src.requests == []


def test_source_failure_isolated_by_breaker(env):
    from connectors import ConnectorUnavailable
    hub, _, src, _ = env
    hub.grant("notify", ["send"], actor="owner")
    src.fail = True
    assert hub.call("notify", "send", {"text": "1"})["ok"] is False
    assert hub.call("notify", "send", {"text": "2"})["ok"] is False
    n = len(src.requests)
    with pytest.raises(ConnectorUnavailable):          # القاطع مفتوح: لا طلب
        hub.call("notify", "send", {"text": "3"})
    assert len(src.requests) == n
    assert hub.status()["connectors"]["notify"]["breaker"] == "open"


def test_one_failing_connector_does_not_affect_another(env):
    from connectors import webhook_connector
    hub, vault, src, _ = env
    dead = webhook_connector("dead", url="http://127.0.0.1:9/hook", allow_loopback=True,
                             timeout_s=0.5)
    hub.register(dead)
    vault.put("connector.dead", TOKEN, scopes=["connector:dead"], actor="owner")
    hub.grant("dead", ["send"], actor="owner")
    hub.grant("notify", ["send"], actor="owner")
    assert hub.call("dead", "send", {"text": "x"})["ok"] is False
    assert hub.call("notify", "send", {"text": "x"})["ok"] is True


def test_health_check(env):
    hub, _, src, _ = env
    hub.grant("notify", ["health"], actor="owner")
    assert hub.call("notify", "health", {})["ok"] is True
    src.fail = True
    assert hub.call("notify", "health", {})["ok"] is False


def test_idempotency_key_forwarded(env):
    hub, _, src, _ = env
    hub.grant("notify", ["send"], actor="owner")
    hub.call("notify", "send", {"text": "x", "idempotency_key": "task1:0"})
    assert src.requests[-1]["idem"] == "task1:0"


def test_ssrf_guard_on_webhook_url():
    from connectors import webhook_connector
    with pytest.raises(ValueError):
        webhook_connector("x", url="http://127.0.0.1:8080/h")       # loopback ممنوع افتراضيًا
    with pytest.raises(ValueError):
        webhook_connector("x", url="file:///etc/passwd")


def test_registry_exposes_connector_actions_and_status_tool(tmp_path):
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        names = {t["name"] for t in client.get("/tools/list").json()["tools"]}
        assert "connectors.status" in names
        caps = {c["id"]: c for c in client.get("/capabilities").json()["capabilities"]}
        assert caps["connectors"]["level"] != "missing"
        assert TOKEN not in client.get("/connectors/status").text


def test_grant_and_revoke_endpoints_require_owner_key():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        for path in ("/connectors/grant", "/connectors/revoke"):
            r = client.post(path, json={"connector": "notify", "actions": ["send"]})
            assert r.status_code == 401
            r = client.post(path, json={"connector": "notify", "actions": ["send"],
                                        "api_key": "wrong"})
            assert r.status_code == 401
