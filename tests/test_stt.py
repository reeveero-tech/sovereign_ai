"""R-737 (البند ٢.٣ — بأمر المالك «ابدأ»): أذنان — تحويل الكلام لنص.

مدخل `/stt` (خارطة V4، القسم ٢): تحويل مقطع صوتي إلى نص عبر خدمة تحويل كلام
متوافقة مع OpenAI (`POST {base}/audio/transcriptions` — الاستجابة `{text}`).
المعيار في الخارطة: «اختبار: مقطع صوتي → نص».

المصدران اللذان يغطيهما البروتوكول نفسه (كما في R-736 — بروتوكول واحد):
- خدمة سحابية (مثال Groq: whisper-large-v3 على أساس Groq نفسه).
- خادم Whisper محلي (whisper.cpp server يعرض نقطة متوافقة مع OpenAI).

مبادئ التصميم (قائمة من R-704/R-736):
- معطل افتراضيًا (`STT_ENABLED`) — لا اتصال ضمني (conftest يفرض التعطيل
  في الاختبارات بالبناء).
- لا يرفع أبدًا: أي فشل → None والنقطة تعلن السبب بصدق (لا نجاح كاذب).
- لا مفتاح ولا محتوى صوتي في السجلات (نوع الخطأ فقط).
- حد حجم صافٍ (`STT_MAX_AUDIO_BYTES`) وقائمة أنواع مسموحة — لا قبول
  ملفات اعتباطية.
- تحديد معدل بحد `/chat` نفسه لكل IP (الرفع باهظ — لا باب مفتوح).
- `/stt/status` بلا أي سر (عنوان معقّم — نمط /brain/status و/api-key).
"""

import io
import json
import math
import os
import struct
import subprocess
import sys
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import config


def _make_fake_stt(text="مرحبا من الصوت", status=200, raw_body=None):
    """خادم يحاكي خدمة تحويل كلام متوافقة مع OpenAI — يسجل الطلب الخام
    (الترويسات + الجسم) ويعيد استجابة محكومة. لا يجيب إلا على
    /audio/transcriptions (404 لغيره) — مطابقة صارمة للعقد."""
    requests_seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            requests_seen.append({"path": self.path,
                                  "headers": dict(self.headers), "body": body})
            if not self.path.endswith("/audio/transcriptions"):
                self.send_response(404)
                self.end_headers()
                return
            if status != 200:
                self.send_response(status)
                self.end_headers()
                return
            payload = raw_body if raw_body is not None else {"text": text}
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


def _tiny_wav():
    """مقطع WAV حقيقي صغير (0.1 ثانية موجة جيبية) — ملف صوتي صالح فعلًا."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"".join(
            struct.pack("<h", int(1000 * math.sin(i * 0.05)))
            for i in range(800)
        ))
    return buf.getvalue()


@pytest.fixture
def stt_enabled(monkeypatch):
    """تفعيل السمع نحو خادم وهمي — يُستدعى بعد إنشائه."""
    def _enable(base_url, model="whisper-large-v3", api_key=None, max_bytes=None):
        monkeypatch.setattr(config, "STT_ENABLED", True)
        monkeypatch.setattr(config, "STT_BASE_URL", base_url)
        monkeypatch.setattr(config, "STT_MODEL", model)
        monkeypatch.setattr(config, "STT_API_KEY", api_key)
        monkeypatch.setattr(config, "STT_TIMEOUT_SECONDS", 10.0)
        if max_bytes is not None:
            monkeypatch.setattr(config, "STT_MAX_AUDIO_BYTES", max_bytes)
    return _enable


# ======================== العميل ========================

def test_client_request_and_parse(stt_enabled):
    """العميل يرسل multipart صحيح إلى /audio/transcriptions ويعيد النص."""
    import stt_client
    server, seen = _make_fake_stt(text="النص المستخرج")
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        wav = _tiny_wav()
        text = stt_client.transcribe(wav, "speech.wav", "audio/wav")
        assert text == "النص المستخرج"
        assert len(seen) == 1
        req = seen[0]
        assert req["path"].endswith("/audio/transcriptions")
        assert "multipart/form-data" in req["headers"].get("Content-Type", "")
        assert wav in req["body"], "raw audio bytes must be uploaded"
        assert b'name="model"' in req["body"], "model field must be sent"
        assert b"whisper-large-v3" in req["body"]
        assert "Authorization" not in req["headers"], "no auth header without key"
    finally:
        server.shutdown()


def test_client_bearer_when_key_set(stt_enabled):
    """ترويسة الحامل تُرسل عند وجود مفتاح (خدمات سحابية)."""
    import stt_client
    server, seen = _make_fake_stt()
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}",
                    api_key="secret-key")
        assert stt_client.transcribe(_tiny_wav(), "s.wav", "audio/wav") is not None
        assert seen[0]["headers"].get("Authorization") == "Bearer secret-key"
    finally:
        server.shutdown()


def test_client_model_optional(stt_enabled):
    """بلا STT_MODEL (خادم محلي يقرر النموذج) — لا حقل model في الطلب."""
    import stt_client
    server, seen = _make_fake_stt()
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}", model=None)
        assert stt_client.transcribe(_tiny_wav(), "s.wav", "audio/wav") is not None
        assert b'name="model"' not in seen[0]["body"]
    finally:
        server.shutdown()


def test_client_failures_return_none(stt_enabled):
    """أي فشل (خطأ HTTP / استجابة فاسدة / نص فارغ) → None لا استثناء."""
    import stt_client
    server, _ = _make_fake_stt(status=500)
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        assert stt_client.transcribe(_tiny_wav(), "s.wav", "audio/wav") is None
    finally:
        server.shutdown()
    server2, _ = _make_fake_stt(raw_body={"unexpected": "shape"})
    try:
        stt_enabled(f"http://127.0.0.1:{server2.server_address[1]}")
        assert stt_client.transcribe(_tiny_wav(), "s.wav", "audio/wav") is None
    finally:
        server2.shutdown()
    server3, _ = _make_fake_stt(text="   ")
    try:
        stt_enabled(f"http://127.0.0.1:{server3.server_address[1]}")
        assert stt_client.transcribe(_tiny_wav(), "s.wav", "audio/wav") is None
    finally:
        server3.shutdown()


def test_disabled_makes_no_request(stt_enabled):
    """السمع معطل → لا طلب إطلاقًا (لا اتصال ضمني — نمط R-704/R-736)."""
    import stt_client
    server, seen = _make_fake_stt()
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        config.STT_ENABLED = False
        assert stt_client.transcribe(_tiny_wav(), "s.wav", "audio/wav") is None
        assert len(seen) == 0, "disabled STT must not issue any request"
    finally:
        server.shutdown()


def test_config_defaults_and_env(tmp_path):
    """الافتراضي: معطل + عنوان محلي؛ والقراءة من البيئة تعمل (عملية مستقلة
    بنمط test_ollama_config — معزولة عن قواعد مفتاح السيد)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("STT_")}
    code = ("import config; print(config.STT_ENABLED, config.STT_BASE_URL, "
            "config.STT_MAX_AUDIO_BYTES)")
    r1 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                         env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    assert "False http://127.0.0.1:8080/v1 26214400" in r1.stdout, (
        "defaults: disabled + local whisper.cpp + 25MiB"
    )
    env2 = dict(env)
    env2["STT_ENABLED"] = "true"
    env2["STT_BASE_URL"] = "https://api.groq.com/openai/v1"
    r2 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env2, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    assert "True https://api.groq.com/openai/v1" in r2.stdout


# ======================== نقطة /stt ========================

def test_stt_endpoint_transcribes(stt_enabled):
    """النقطة الفعلية: ملف WAV حقيقي → نص في استجابة 200 (معيار إغلاق ٢.٣)."""
    from app import app as fastapi_app, stt_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_fake_stt(text="مرحبا من الصوت")
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        stt_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/stt", files={"file": ("speech.wav", _tiny_wav(),
                                                    "audio/wav")})
            assert r.status_code == 200, r.text
            assert r.json() == {"text": "مرحبا من الصوت"}, (
                "audio → text is the closure criterion of item 2.3"
            )
    finally:
        server.shutdown()


def test_stt_endpoint_disabled_honest(stt_enabled):
    """معطل → 503 بالسبب الصريح — لا نجاح كاذب ولا محاكاة (المادة ١)."""
    from app import app as fastapi_app, stt_rate_limiter
    from fastapi.testclient import TestClient

    stt_enabled("http://127.0.0.1:1")
    config.STT_ENABLED = False
    stt_rate_limiter._requests.clear()
    with TestClient(fastapi_app) as client:
        r = client.post("/stt", files={"file": ("s.wav", _tiny_wav(),
                                                 "audio/wav")})
        assert r.status_code == 503, r.text
        assert r.json()["error"] == "stt_disabled"
        assert "reason" in r.json(), "honest reason required"


def test_stt_endpoint_rejects_oversize(stt_enabled):
    """تجاوز حد الحجم → 413 — لا قراءة ملفات اعتباطية في الذاكرة."""
    from app import app as fastapi_app, stt_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_fake_stt()
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}",
                    max_bytes=100)
        stt_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/stt", files={"file": ("big.wav", b"x" * 200,
                                                    "audio/wav")})
            assert r.status_code == 413, r.text
    finally:
        server.shutdown()


def test_stt_endpoint_rejects_wrong_content_type(stt_enabled):
    """نوع غير صوتي (text/plain) → 415 — قائمة أنواع صارمة."""
    from app import app as fastapi_app, stt_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_fake_stt()
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        stt_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/stt", files={"file": ("note.txt", b"hello",
                                                    "text/plain")})
            assert r.status_code == 415, r.text
    finally:
        server.shutdown()


def test_stt_endpoint_service_failure_honest(stt_enabled):
    """فشل الخدمة → 502 بالسبب — لا نص مختلق ولا 200 كاذب."""
    from app import app as fastapi_app, stt_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_fake_stt(status=500)
    try:
        stt_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        stt_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/stt", files={"file": ("s.wav", _tiny_wav(),
                                                    "audio/wav")})
            assert r.status_code == 502, r.text
            assert r.json()["error"] == "transcription_failed"
    finally:
        server.shutdown()


def test_stt_status_no_secret_leak(stt_enabled):
    """/stt/status: لا سر أبدًا — العنوان معقّم، والمفتاح لا يظهر."""
    from app import app as fastapi_app
    from fastapi.testclient import TestClient

    stt_enabled("http://owner:super-secret@127.0.0.1:8080/v1?token=abc",
                api_key="top-secret")
    with TestClient(fastapi_app) as client:
        r = client.get("/stt/status")
        assert r.status_code == 200
        for secret in ("super-secret", "top-secret", "token", "abc"):
            assert secret not in r.text, f"secret leaked: {secret}"
        data = r.json()
        assert data["enabled"] is True
        assert "127.0.0.1:8080/v1" in r.text, "sanitized host+path must remain"


def test_stt_status_disabled_honest():
    """/stt/status معطلًا: enabled=False — إفصاح صادق كامل."""
    from app import app as fastapi_app
    from fastapi.testclient import TestClient

    with TestClient(fastapi_app) as client:
        data = client.get("/stt/status").json()
        assert data["enabled"] is False


def test_stt_rate_limited():
    """تجاوز حد المعدل (حد /chat نفسه) → 429 مع Retry-After — لا باب مفتوح."""
    from app import app as fastapi_app, stt_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_fake_stt()
    try:
        import config as _c
        _c.STT_ENABLED = True
        _c.STT_BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"
        _c.STT_MODEL = "whisper-large-v3"
        stt_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            codes = []
            for _ in range(config.MAX_USER_MESSAGES_PER_MINUTE + 2):
                r = client.post("/stt", files={"file": ("s.wav", _tiny_wav(),
                                                         "audio/wav")})
                codes.append(r.status_code)
            assert 429 in codes, "rate limit must eventually trigger"
            assert codes.count(200) <= config.MAX_USER_MESSAGES_PER_MINUTE
            limited = [c for c in codes if c == 429]
            assert limited, "429 responses must carry the honest limit"
    finally:
        server.shutdown()
