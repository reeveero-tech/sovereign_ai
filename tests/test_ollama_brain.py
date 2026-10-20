"""R-704: عقل Ollama المحلي — اختبارات العميل والدمج ونقطة /chat الفعلية.

التصميم: خادم HTTP اصطناعي يحاكي بروتوكول Ollama الرسمي
(POST /api/chat — stream:false — الاستجابة {message:{content}})،
لا اعتماد على خادم حقيقي: الحتمية كاملة والفشل محكوم.

المسارات المثبتة:
- العميل: طلب صحيح (النموذج/stream:false/ترويسة الحامل عند وجود مفتاح)،
  نجاح الاستجابة، والسقوط الآمن (None) عند الخطأ أو فساد الاستجابة.
- build_reply: نص النموذج يصل للرد عند التفعيل، والسقوط للقوالب عند العطل.
- نقطة /chat الفعلية: نص النموذج يظهر في استجابة HTTP، والسقوط يبقي ردًا.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import config
from sovereign_response import build_reply


def _make_fake_ollama(content="رد من النموذج الوهمي", status=200, raw_body=None):
    """خادم يحاكي Ollama — يسجل الطلبات ويعيد استجابة محكومة."""
    requests_seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            requests_seen.append({"path": self.path, "headers": dict(self.headers), "body": body})
            if status != 200:
                self.send_response(status)
                self.end_headers()
                return
            payload = raw_body if raw_body is not None else {
                "model": "fake",
                "message": {"role": "assistant", "content": content},
                "done": True,
            }
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, requests_seen


@pytest.fixture
def ollama_enabled(monkeypatch):
    """تفعيل العقل نحو خادم وهمي — يُستدعى بعد إنشائه لمعرفة المنفذ."""
    def _enable(base_url, model="fake-model", api_key=None):
        monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
        monkeypatch.setattr(config, "OLLAMA_MODEL", model)
        monkeypatch.setattr(config, "OLLAMA_BASE_URL", base_url)
        monkeypatch.setattr(config, "OLLAMA_API_KEY", api_key)
        monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 10.0)
    return _enable


def test_client_chat_success(ollama_enabled):
    """العميل يرسل الطلب الصحيح (النموذج، stream:false) ويعيد نص النموذج."""
    import ollama_client
    server, seen = _make_fake_ollama(content="مرحبا يا سيدي")
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        reply = ollama_client.chat("أنت المساعد السيادي", "مرحبا")
        assert reply == "مرحبا يا سيدي", "model content must be returned"
        assert len(seen) == 1
        req = seen[0]
        assert req["path"] == "/api/chat"
        assert req["body"]["model"] == "fake-model"
        assert req["body"]["stream"] is False, "non-streaming request required"
        assert req["body"]["messages"][0]["role"] == "system"
        assert req["body"]["messages"][-1]["content"] == "مرحبا"
        assert "Authorization" not in req["headers"], "no auth header without key"
    finally:
        server.shutdown()


def test_client_sends_bearer_when_key_set(ollama_enabled):
    """ترويسة الحامل تُرسل فقط عند وجود مفتاح API (لخوادم التوثيق)."""
    import ollama_client
    server, seen = _make_fake_ollama()
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}", api_key="secret-key")
        assert ollama_client.chat("sys", "hi") is not None
        auth = seen[0]["headers"].get("Authorization", "")
        assert auth == "Bearer secret-key"
    finally:
        server.shutdown()


def test_client_failure_returns_none(ollama_enabled):
    """أي فشل (خطأ HTTP / استجابة فاسدة / خادم ميت) → None لا استثناء."""
    import ollama_client
    # خطأ HTTP
    server, _ = _make_fake_ollama(status=500)
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        assert ollama_client.chat("sys", "hi") is None, "HTTP error must fall back"
    finally:
        server.shutdown()
    # استجابة فاسدة (بلا message)
    server2, _ = _make_fake_ollama(raw_body={"unexpected": "shape"})
    try:
        ollama_enabled(f"http://127.0.0.1:{server2.server_address[1]}")
        assert ollama_client.chat("sys", "hi") is None, "malformed response must fall back"
    finally:
        server2.shutdown()
    # خادم ميت (منفذ مرفوض فورًا)
    ollama_enabled("http://127.0.0.1:1")
    assert ollama_client.chat("sys", "hi") is None, "dead server must fall back"


def test_build_reply_uses_llm_when_enabled(ollama_enabled):
    """build_reply يعيد نص النموذج عند التفعيل — العقل جزء مسار الرد."""
    server, _ = _make_fake_ollama(content="رد العقل الاصطناعي الحي")
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        reply = build_reply("greet", "مرحبا")
        assert reply == "رد العقل الاصطناعي الحي", "LLM reply must flow through build_reply"
    finally:
        server.shutdown()


def test_build_reply_falls_back_when_ollama_down(ollama_enabled):
    """عطل الخادم → القوالب القائمة كما هي (سقوط آمن مُثبت)."""
    ollama_enabled("http://127.0.0.1:1")  # منفذ ميت — رفض اتصال فوري
    reply = build_reply("greet", "مرحبا")
    assert reply, "fallback reply must be non-empty"
    assert reply.startswith("أهلاً بك"), "rule-engine template must be the fallback"


def test_chat_endpoint_uses_llm(ollama_enabled):
    """نقطة /chat الفعلية: نص النموذج يظهر في استجابة HTTP — دمج كامل."""
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_fake_ollama(content="رد العقل عبر نقطة المحادثة")
    try:
        ollama_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        chat_rate_limiter._requests.clear()  # عزل حد المعدل بين الاختبارات
        with TestClient(fastapi_app) as client:
            r = client.post("/chat", json={"text": "مرحبا"})
            assert r.status_code == 200, r.text
            assert r.json()["reply"] == "رد العقل عبر نقطة المحادثة", (
                "model text must reach the /chat HTTP response"
            )
    finally:
        server.shutdown()


def test_chat_endpoint_falls_back_when_ollama_down(ollama_enabled):
    """نقطة /chat الفعلية: عطل الخادم → رد احتياطي غير فارغ (لا فشل 500)."""
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient

    ollama_enabled("http://127.0.0.1:1")
    chat_rate_limiter._requests.clear()
    with TestClient(fastapi_app) as client:
        r = client.post("/chat", json={"text": "مرحبا"})
        assert r.status_code == 200, r.text
        assert r.json()["reply"], "fallback reply must remain on dead Ollama"
