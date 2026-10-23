"""R-740 (البند ٢.٤ — بأمر المالك «ابدأ»): صوت — نطق الردود (TTS).

مدخل `/tts` (خارطة V4، القسم ٢): نص → مقطع صوتي عبر خدمة نطق متوافقة
مع OpenAI (POST {base}/audio/speech — الاستجابة بايتات صوت ثنائية).
البروتوكول القياسي يغطي: خدمة سحابية (Groq playai-tts / OpenAI) وخادمًا
محليًا متوافقًا (piper/kokoro بغلاف متوافق OpenAI).

مبادئ قائمة (R-704/R-736/R-737/R-739):
- معطل افتراضيًا (TTS_ENABLED) — لا اتصال ضمني.
- fail-closed: أي فشل → لا صوت مختلق، وسبب صادق في الاستجابة.
- لا مفتاح ولا نص في السجلات (نوع الخطأ فقط).
- حد طول نص صافٍ + حد معدل بحد /chat نفسه.
- `/tts/status` بلا أي سر (عنوان معقّم).
"""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import config


def _make_speech_server(audio=b"FAKE-MP3-AUDIO-BYTES",
                        content_type="audio/mpeg", status=200, raw_json=None):
    """خادم نطق وهمي: POST /audio/speech → بايتات صوت (عقد OpenAI speech)."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            seen.append({"path": self.path, "body": body,
                         "headers": dict(self.headers)})
            if not self.path.endswith("/audio/speech"):
                self.send_response(404)
                self.end_headers()
                return
            if status != 200:
                self.send_response(status)
                self.end_headers()
                return
            if raw_json is not None:
                data = json.dumps(raw_json).encode()
                ctype = "application/json"
            else:
                data = audio
                ctype = content_type
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, seen


@pytest.fixture
def tts_enabled(monkeypatch):
    def _enable(base_url, model="playai-tts", api_key=None, voice=None,
                max_chars=None):
        monkeypatch.setattr(config, "TTS_ENABLED", True)
        monkeypatch.setattr(config, "TTS_MODEL", model)
        monkeypatch.setattr(config, "TTS_BASE_URL", base_url)
        monkeypatch.setattr(config, "TTS_API_KEY", api_key)
        monkeypatch.setattr(config, "TTS_VOICE", voice)
        monkeypatch.setattr(config, "TTS_TIMEOUT_SECONDS", 10.0)
        if max_chars is not None:
            monkeypatch.setattr(config, "TTS_MAX_TEXT_CHARS", max_chars)
    return _enable


# ======================== العميل ========================

def test_client_speaks_and_sends_contract(tts_enabled):
    """العميل يرسل عقد OpenAI speech ويعيد بايتات الصوت مع نوعها."""
    import tts_client
    server, seen = _make_speech_server()
    try:
        tts_enabled(f"http://127.0.0.1:{server.server_address[1]}",
                    api_key="secret-tts-key", voice="onyx")
        out = tts_client.speak("مرحبا بك")
        assert out is not None
        audio, ctype = out
        assert audio == b"FAKE-MP3-AUDIO-BYTES"
        assert ctype.startswith("audio/")
        req = json.loads(seen[0]["body"])
        assert req["model"] == "playai-tts"
        assert req["input"] == "مرحبا بك"
        assert req["voice"] == "onyx"
        assert seen[0]["headers"].get("Authorization") == "Bearer secret-tts-key"
    finally:
        server.shutdown()


def test_client_voice_optional(tts_enabled):
    """بلا TTS_VOICE — لا حقل voice في الطلب (الخادم المحلي يقرر)."""
    import tts_client
    server, seen = _make_speech_server()
    try:
        tts_enabled(f"http://127.0.0.1:{server.server_address[1]}",
                    voice=None)
        assert tts_client.speak("نص") is not None
        assert "voice" not in json.loads(seen[0]["body"])
    finally:
        server.shutdown()


def test_client_failures_return_none(tts_enabled):
    """أي فشل (HTTP/جسد غير صوتي) → None لا استثناء — fail-closed."""
    import tts_client
    server, _ = _make_speech_server(status=500)
    try:
        tts_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        assert tts_client.speak("نص") is None
    finally:
        server.shutdown()
    server2, _ = _make_speech_server(raw_json={"text": "ليس صوتًا"})
    try:
        tts_enabled(f"http://127.0.0.1:{server2.server_address[1]}")
        assert tts_client.speak("نص") is None, "non-audio body must be rejected"
    finally:
        server2.shutdown()


def test_disabled_makes_no_request(tts_enabled):
    """النطق معطل → لا طلب إطلاقًا (لا اتصال ضمني — نمط R-704)."""
    import tts_client
    server, seen = _make_speech_server()
    try:
        tts_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        config.TTS_ENABLED = False
        assert tts_client.speak("نص") is None
        assert len(seen) == 0, "disabled TTS must not issue any request"
    finally:
        server.shutdown()


def test_config_defaults_and_env():
    """الافتراضي: معطل + بلا نموذج؛ والبيئة تعمل (عملية مستقلة)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("TTS_")}
    code = ("import config; print(config.TTS_ENABLED, config.TTS_MODEL, "
            "config.TTS_MAX_TEXT_CHARS)")
    r1 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    assert "False None 2000" in r1.stdout, "defaults: disabled + no model + cap"
    env2 = dict(env)
    env2["TTS_ENABLED"] = "true"
    env2["TTS_MODEL"] = "playai-tts"
    r2 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env2, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    assert "True playai-tts" in r2.stdout


# ======================== نقطة /tts ========================

def test_tts_endpoint_speaks(tts_enabled):
    """النقطة الفعلية: نص → مقطع صوتي (معيار إغلاق ٢.٤ — النصف الأول)."""
    from app import app as fastapi_app, tts_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_speech_server()
    try:
        tts_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        tts_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/tts", json={"text": "هذا رد مُنطق"})
            assert r.status_code == 200, r.text
            assert r.content == b"FAKE-MP3-AUDIO-BYTES", (
                "text → audio segment is the closure criterion of item 2.4"
            )
            assert r.headers["content-type"].startswith("audio/")
    finally:
        server.shutdown()


def test_tts_endpoint_disabled_honest(tts_enabled):
    """معطل → 503 بالسبب الصريح — لا نجاح كاذب ولا صوت مختلق (المادة ١)."""
    from app import app as fastapi_app, tts_rate_limiter
    from fastapi.testclient import TestClient

    tts_enabled("http://127.0.0.1:1")
    config.TTS_ENABLED = False
    tts_rate_limiter._requests.clear()
    with TestClient(fastapi_app) as client:
        r = client.post("/tts", json={"text": "نص"})
        assert r.status_code == 503, r.text
        assert r.json()["error"] == "tts_disabled"
        assert "reason" in r.json(), "honest reason required"


def test_tts_endpoint_rejects_empty_and_oversize(tts_enabled):
    """نص فارغ → 400؛ وتجاوز حد الطول → 413 — لا نطق اعتباطي."""
    from app import app as fastapi_app, tts_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_speech_server()
    try:
        tts_enabled(f"http://127.0.0.1:{server.server_address[1]}",
                    max_chars=10)
        tts_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r0 = client.post("/tts", json={"text": "   "})
            assert r0.status_code == 400, r0.text
            r = client.post("/tts", json={"text": "ن" * 50})
            assert r.status_code == 413, r.text
    finally:
        server.shutdown()


def test_tts_endpoint_service_failure_honest(tts_enabled):
    """فشل الخدمة → 502 بالسبب — لا صوت مختلق ولا 200 كاذب."""
    from app import app as fastapi_app, tts_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_speech_server(status=500)
    try:
        tts_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        tts_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/tts", json={"text": "نص"})
            assert r.status_code == 502, r.text
            assert r.json()["error"] == "tts_failed"
    finally:
        server.shutdown()


def test_tts_status_no_secret_leak(tts_enabled):
    """/tts/status: لا سر أبدًا — العنوان معقّم، والمفتاح لا يظهر."""
    from app import app as fastapi_app
    from fastapi.testclient import TestClient

    tts_enabled("http://owner:super-secret@127.0.0.1:8880/v1?token=abc",
                api_key="top-secret")
    with TestClient(fastapi_app) as client:
        r = client.get("/tts/status")
        assert r.status_code == 200
        for secret in ("super-secret", "top-secret", "token", "abc"):
            assert secret not in r.text, f"secret leaked: {secret}"
        data = r.json()
        assert data["enabled"] is True
        assert data["model"] == "playai-tts"
        assert "8880" in r.text, "sanitized host+port must remain"


def test_tts_status_disabled_honest():
    """/tts/status معطلًا: enabled=False — إفصاح صادق كامل."""
    from app import app as fastapi_app
    from fastapi.testclient import TestClient

    with TestClient(fastapi_app) as client:
        data = client.get("/tts/status").json()
        assert data["enabled"] is False


def test_tts_rate_limited(tts_enabled):
    """تجاوز حد المعدل (حد /chat نفسه) → 429 — لا باب مفتوح."""
    from app import app as fastapi_app, tts_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_speech_server()
    try:
        tts_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        tts_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            codes = []
            for _ in range(config.MAX_USER_MESSAGES_PER_MINUTE + 2):
                r = client.post("/tts", json={"text": "نص"})
                codes.append(r.status_code)
            assert 429 in codes, "rate limit must eventually trigger"
            assert codes.count(200) <= config.MAX_USER_MESSAGES_PER_MINUTE
    finally:
        server.shutdown()
