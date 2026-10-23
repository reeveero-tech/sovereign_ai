"""R-736 (البند ٢.١ — بأمر المالك «1+2+3+4»): البروتوكول الثاني للعقل.

خيار عقل سحابي/عام للمنشور على Fly (خارطة V4، القسم ٢): العميل كان يتحدث
بروتوكول Ollama فقط (POST {base}/api/chat). هذه الجولة تضيف البروتوكول
المتوافق مع OpenAI (POST {base}/chat/completions — Groq/OpenRouter/أي مزود
متوافق) بجانب القائم، بتحديد صريح: OLLAMA_PROTOCOL:

- "ollama" (الافتراضي): كما هو تمامًا — لا يتغير شيء للإعداد المحلي القائم.
- "openai": BASE_URL بادئة الإصدار كاملة (مثال Groq:
  https://api.groq.com/openai/v1 — مثال OpenRouter: https://openrouter.ai/api/v1)
  ويُلحق بها /chat/completions فقط — لا تكرار لمسار الإصدار.

المصادر الأربعة التي أمر بها المالك («1+2+3+4»):
- ١ (API متوافق OpenAI): هذا الملف يثبته.
- ٢ (نفق لخادم Ollama): البروتوكول القائم بتغيير BASE_URL فقط.
- ٣ (Ollama Cloud): https://ollama.com ببروتوكول Ollama ومفتاح Bearer
  (وثائق ollama.com الرسمية — نقطة /api/chat السحابية).
- ٤ (GPU على Fly): غير متاح — Fly أوقفت GPUs نهائيًا (2026-08-01) — يوثق
  في التقرير الجنائي لا في الكود.

المبادئ القائمة محفوظة: سقوط آمن للقوالب (None لا استثناء)، لا سر ولا
محتوى محادثة في السجلات (نوع الخطأ فقط)، لا اتصال ضمني (conftest يعطل
العقل في الاختبارات بالبناء)، والقيمة المجهولة للبروتوكول تُغلق المسار
(fail-closed) بلا أي طلب يخرج من العملية.
"""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import config
from sovereign_response import build_reply


def _make_fake_openai(content="رد من النموذج السحابي", status=200, raw_body=None):
    """خادم يحاكي مزودًا متوافقًا مع OpenAI — يسجل الطلبات ويعيد استجابة محكومة.

    لا يجيب إلا على مسار /chat/completions (404 لغيره) — مطابقة صارمة
    للعقد، فأي تسرب لمسار ollama (/api/chat) يُكشف فورًا بالاختبارات.
    """
    requests_seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            requests_seen.append({"path": self.path, "headers": dict(self.headers), "body": body})
            if not self.path.endswith("/chat/completions"):
                self.send_response(404)
                self.end_headers()
                return
            if status != 200:
                self.send_response(status)
                self.end_headers()
                return
            payload = raw_body if raw_body is not None else {
                "id": "chatcmpl-fake",
                "object": "chat.completion",
                "model": "fake",
                "choices": [
                    {"message": {"role": "assistant", "content": content},
                     "finish_reason": "stop"}
                ],
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
def openai_brain(monkeypatch):
    """تفعيل العقل ببروتوكول openai نحو خادم وهمي — يُستدعى بعد إنشائه."""
    def _enable(base_url, model="cloud-model", api_key=None, protocol="openai"):
        monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
        monkeypatch.setattr(config, "OLLAMA_MODEL", model)
        monkeypatch.setattr(config, "OLLAMA_BASE_URL", base_url)
        monkeypatch.setattr(config, "OLLAMA_API_KEY", api_key)
        monkeypatch.setattr(config, "OLLAMA_PROTOCOL", protocol)
        monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 10.0)
    return _enable


def _reset_last_outcome():
    """تصفير نتيجة الاستدعاء الأخير (حالة عملية عامة — عزل بين الاختبارات)."""
    import ollama_client
    ollama_client._LAST_OUTCOME = {"result": "none", "error": None}


def test_client_openai_request_and_parse(openai_brain):
    """العميل يرسل الطلب الصحيح لمسار /chat/completions ويعيد نص النموذج."""
    import ollama_client
    server, seen = _make_fake_openai(content="مرحبا من السحابة")
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}")
        reply = ollama_client.chat("أنت المساعد السيادي", "مرحبا")
        assert reply == "مرحبا من السحابة", "openai-protocol content must be returned"
        assert len(seen) == 1
        req = seen[0]
        assert req["path"].endswith("/chat/completions"), (
            "openai protocol must hit /chat/completions"
        )
        assert req["body"]["model"] == "cloud-model"
        assert req["body"]["stream"] is False, "non-streaming request required"
        assert req["body"]["messages"][0]["role"] == "system"
        assert req["body"]["messages"][-1]["content"] == "مرحبا"
        assert "Authorization" not in req["headers"], "no auth header without key"
    finally:
        server.shutdown()


def test_client_openai_bearer_when_key_set(openai_brain):
    """ترويسة الحامل تُرسل عند وجود مفتاح API (نمط خوادم التوثيق السحابية)."""
    import ollama_client
    server, seen = _make_fake_openai()
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}", api_key="secret-key")
        assert ollama_client.chat("sys", "hi") is not None
        auth = seen[0]["headers"].get("Authorization", "")
        assert auth == "Bearer secret-key"
    finally:
        server.shutdown()


def test_client_openai_base_url_with_version_path(openai_brain):
    """BASE_URL المنتهية بمسار إصدار (.../openai/v1) يُلحق بها /chat/completions
    مرة واحدة — لا تكرار لمسار الإصدار (عقد Groq/OpenRouter)."""
    import ollama_client
    server, seen = _make_fake_openai()
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}/openai/v1")
        assert ollama_client.chat("sys", "hi") is not None
        assert seen[0]["path"] == f"/openai/v1/chat/completions", (
            "version path must not be duplicated"
        )
    finally:
        server.shutdown()


def test_client_openai_failures_return_none(openai_brain):
    """أي فشل (خطأ HTTP / استجابة بلا choices / محتوى فارغ) → None لا استثناء."""
    import ollama_client
    # خطأ HTTP
    server, _ = _make_fake_openai(status=500)
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}")
        assert ollama_client.chat("sys", "hi") is None, "HTTP error must fall back"
    finally:
        server.shutdown()
    # استجابة فاسدة (بلا choices)
    server2, _ = _make_fake_openai(raw_body={"unexpected": "shape"})
    try:
        openai_brain(f"http://127.0.0.1:{server2.server_address[1]}")
        assert ollama_client.chat("sys", "hi") is None, "malformed response must fall back"
    finally:
        server2.shutdown()
    # محتوى فارغ
    server3, _ = _make_fake_openai(content="   ")
    try:
        openai_brain(f"http://127.0.0.1:{server3.server_address[1]}")
        assert ollama_client.chat("sys", "hi") is None, "blank content must fall back"
    finally:
        server3.shutdown()


def test_unknown_protocol_fails_closed(openai_brain):
    """قيمة بروتوكول غير معروفة → None بلا أي طلب يخرج من العملية (fail-closed)."""
    import ollama_client
    server, seen = _make_fake_openai()
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}", protocol="weird")
        assert ollama_client.chat("sys", "hi") is None, "unknown protocol must not execute"
        assert len(seen) == 0, "no request may leave the process on unknown protocol"
    finally:
        server.shutdown()


def test_disabled_makes_no_request(openai_brain):
    """العقل معطل → لا طلب إطلاقًا (لا اتصال ضمني — نمط R-704/R-720)."""
    import ollama_client
    server, seen = _make_fake_openai()
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}")
        config.OLLAMA_ENABLED = False
        assert ollama_client.chat("sys", "hi") is None
        assert len(seen) == 0, "disabled brain must not issue any request"
    finally:
        server.shutdown()


def test_build_reply_uses_openai_model(openai_brain):
    """build_reply يعيد نص النموذج عبر البروتوكول الجديد — مسار الرد كاملًا."""
    server, _ = _make_fake_openai(content="رد العقل السحابي الحي")
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}")
        reply = build_reply("greet", "مرحبا")
        assert reply == "رد العقل السحابي الحي", "cloud model reply must flow through build_reply"
    finally:
        server.shutdown()


def test_build_reply_falls_back_when_openai_down(openai_brain):
    """عطل المزود → القوالب القائمة كما هي (سقوط آمن مُثبت)."""
    openai_brain("http://127.0.0.1:1")  # منفذ ميت — رفض اتصال فوري
    reply = build_reply("greet", "مرحبا")
    assert reply, "fallback reply must be non-empty"
    assert reply.startswith("أهلاً بك"), "rule-engine template must be the fallback"


def test_chat_endpoint_uses_openai_model(openai_brain):
    """نقطة /chat الفعلية: نص النموذج السحابي يظهر في استجابة HTTP — دمج كامل."""
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_fake_openai(content="رد العقل السحابي عبر المحادثة")
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}")
        chat_rate_limiter._requests.clear()  # عزل حد المعدل بين الاختبارات
        with TestClient(fastapi_app) as client:
            r = client.post("/chat", json={"text": "مرحبا"})
            assert r.status_code == 200, r.text
            assert r.json()["reply"] == "رد العقل السحابي عبر المحادثة", (
                "cloud model text must reach the /chat HTTP response"
            )
    finally:
        server.shutdown()


def test_chat_endpoint_falls_back_when_openai_down(openai_brain):
    """نقطة /chat الفعلية: عطل المزود → رد احتياطي غير فارغ (لا فشل 500)."""
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient

    openai_brain("http://127.0.0.1:1")
    chat_rate_limiter._requests.clear()
    with TestClient(fastapi_app) as client:
        r = client.post("/chat", json={"text": "مرحبا"})
        assert r.status_code == 200, r.text
        assert r.json()["reply"], "fallback reply must remain on dead cloud brain"


def test_brain_status_reports_protocol_and_last_call(openai_brain):
    """/brain/status يعلن البروتوكول بصدق + مصدر الرد «المرصود» لا «المضبوط»
    (لا ادعاء نجاح قبل أول استدعاء فعلي) — بلا أي سر في المخرجات (نمط /api-key)."""
    import ollama_client
    from fastapi.testclient import TestClient
    from app import app

    server, _ = _make_fake_openai(content="رد حي")
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}")
        _reset_last_outcome()
        with TestClient(app) as client:
            r = client.get("/brain/status")
            assert r.status_code == 200
            data = r.json()
            assert data["enabled"] is True
            assert data["protocol"] == "openai"
            assert data["last_call"]["result"] == "none"
            # قبل أول استدلال ناجح: غير موثّق — لا انتحال (R-736 دقة)
            assert data["reply_source"] == "unverified"
            # بعد استدعاء ناجح: النتيجة ok والمصدر المرصود model
            assert ollama_client.chat("sys", "hi") == "رد حي"
            data2 = client.get("/brain/status").json()
            assert data2["last_call"]["result"] == "ok"
            assert data2["reply_source"] == "model"
    finally:
        server.shutdown()


def test_brain_status_reports_last_call_error(openai_brain):
    """فشل الاستدعاء يظهر في last_call بصدق (خطأ معلن لا نجاح كاذب)."""
    import ollama_client
    from fastapi.testclient import TestClient
    from app import app

    openai_brain("http://127.0.0.1:1")  # منفذ ميت
    assert ollama_client.chat("sys", "hi") is None
    with TestClient(app) as client:
        data = client.get("/brain/status").json()
        assert data["last_call"]["result"] == "error"
        assert data["last_call"].get("error"), "error class must be declared"
        assert data["reply_source"] == "templates-fallback"


def test_brain_status_protocol_ollama_default(openai_brain):
    """البروتوكول الافتراضي (ollama) يظل معلنًا كما كان — لا انحدار."""
    from fastapi.testclient import TestClient
    from app import app

    openai_brain("http://127.0.0.1:11434", protocol="ollama")
    _reset_last_outcome()
    with TestClient(app) as client:
        data = client.get("/brain/status").json()
        assert data["protocol"] == "ollama"
        assert data["reply_source"] == "unverified"


def test_config_protocol_default_and_env(tmp_path):
    """OLLAMA_PROTOCOL: الافتراضي "ollama"، ويُقرأ من البيئة/الملف بمعزل
    عن قواعد مفتاح السيد (نمط test_ollama_config — عملية مستقلة)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("OLLAMA_")}
    env["OLLAMA_ENV_FILE"] = str(tmp_path / "absent.env")
    code = "import config; print(config.OLLAMA_PROTOCOL)"
    r1 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    assert r1.stdout.strip() == "ollama", "default protocol must be ollama"
    env2 = dict(env)
    env2["OLLAMA_PROTOCOL"] = "openai"
    r2 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env2, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    assert r2.stdout.strip() == "openai", "env must override the protocol"


def test_brain_status_does_not_leak_url_credentials(openai_brain):
    """بيانات اعتماد داخل العنوان (مستخدم:كلمةسر@ أو استعلام رمز) لا تظهر
    في مخرجات /brain/status أبدًا — العنوان يُعرض معقّمًا (نمط لا-سر)."""
    from fastapi.testclient import TestClient
    from app import app

    openai_brain("http://owner:super-secret@127.0.0.1:11434/ollama?token=abc123")
    with TestClient(app) as client:
        r = client.get("/brain/status")
        assert r.status_code == 200
        for secret in ("owner", "super-secret", "token", "abc123"):
            assert secret not in r.text, f"credential fragment leaked: {secret}"
        assert "127.0.0.1:11434/ollama" in r.text, "sanitized host+path must remain"


def test_unknown_protocol_not_echoed_in_logs(openai_brain, caplog):
    """قيمة بروتوكول مجهولة لا يُصدى لها في السجلات (قد تحمل سرًا) —
    تصنيف ثابت فقط (unknown_protocol)."""
    import logging
    import ollama_client

    server, seen = _make_fake_openai()
    try:
        openai_brain(f"http://127.0.0.1:{server.server_address[1]}",
                     protocol="weird-secret-looking-value")
        with caplog.at_level(logging.WARNING, logger="sovereign.ollama"):
            assert ollama_client.chat("sys", "hi") is None
        assert len(seen) == 0
        assert "weird-secret-looking-value" not in caplog.text, (
            "raw protocol value must never be echoed in logs"
        )
        assert "unknown_protocol" in caplog.text
    finally:
        server.shutdown()


def test_brain_status_survives_malformed_port_url(openai_brain):
    """عنوان مضبوط بمنفذ مشوه (مثل :bad) لا يُسقط النقطة (لا 500) ولا
    يُصدى خامًا — تعريف آمن للخطأ (تصويب مراجعة R-736)."""
    from fastapi.testclient import TestClient
    from app import app

    openai_brain("https://example.invalid:bad/v1")
    with TestClient(app) as client:
        r = client.get("/brain/status")
        assert r.status_code == 200, "malformed port must not 500 the endpoint"
        data = r.json()
        assert data["enabled"] is True
        assert data["base_url"] == "<عنوان مضبوط غير قابل للعرض>"
        assert "bad/v1" not in r.text and "example.invalid" not in r.text
