"""R-739 (البند ٢.٢ — بأمر المالك «ابدأ»): عينان — تحليل الصور.

مدخل `/vision` (خارطة V4، القسم ٢): صورة → وصف نصي عبر نموذج متعدد
الوسائط (عقل المنشور — بروتوكولا R-736: ollama بمرآة base64 في
`images`، أو متوافق OpenAI بصورة data-URL في `image_url`).
المعيار في الخارطة: «اختبار: صورة → وصف نصي موثق».

مبادئ قائمة (R-704/R-736/R-737):
- معطل افتراضيًا (VISION_ENABLED) — لا اتصال ضمني.
- fail-closed: أي فشل → لا وصف مختلق، وسبب صادق في الاستجابة.
- لا مفتاح ولا محتوى صورة في السجلات (نوع الخطأ فقط).
- حد حجم صافٍ + قائمة أنواع صور مسموحة + حد معدل بحد /chat نفسه.
- `/vision/status` بلا أي سر (عنوان معقّم — نمط /brain/status و/stt/status).
"""

import base64
import io
import json
import os
import struct
import subprocess
import sys
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import config


def _make_png():
    """صورة PNG حقيقية صغيرة (8×8 أحمر) — ملف صورة صالح فعلًا."""
    width = height = 8
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))

    def chunk(ctype, data):
        return (struct.pack(">I", len(data)) + ctype + data
                + struct.pack(">I", zlib.crc32(ctype + data) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _make_brain_server(protocol="ollama", content="وصف الصورة: مربع أحمر"):
    """خادم عقل وهمي ببروتوكولي R-736 — يسجل الطلب الخام للتحقق
    من وصول الصورة (b64 في ollama / data-URL في openai)."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            seen.append({"path": self.path, "body": body,
                         "headers": dict(self.headers)})
            if protocol == "ollama" and self.path == "/api/chat":
                payload = {"message": {"content": content}}
            elif protocol == "openai" and self.path == "/chat/completions":
                payload = {"choices": [{"message": {"content": content}}]}
            else:
                self.send_response(404)
                self.end_headers()
                return
            data = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, seen


@pytest.fixture
def vision_enabled(monkeypatch):
    def _enable(base_url, model="llava", protocol="ollama", api_key=None,
                max_bytes=None):
        monkeypatch.setattr(config, "VISION_ENABLED", True)
        monkeypatch.setattr(config, "VISION_MODEL", model)
        monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
        monkeypatch.setattr(config, "OLLAMA_MODEL", "chat-model")
        monkeypatch.setattr(config, "OLLAMA_BASE_URL", base_url)
        monkeypatch.setattr(config, "OLLAMA_PROTOCOL", protocol)
        monkeypatch.setattr(config, "OLLAMA_API_KEY", api_key)
        monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 10.0)
        if max_bytes is not None:
            monkeypatch.setattr(config, "VISION_MAX_IMAGE_BYTES", max_bytes)
    return _enable


# ======================== العميل ========================

def test_client_ollama_protocol_sends_image(monkeypatch, vision_enabled):
    """بروتوكول ollama: الصورة تصل base64 في images — والوصف يعاد."""
    import vision_client
    png = _make_png()
    server, seen = _make_brain_server("ollama")
    try:
        vision_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        out = vision_client.describe(png, "image/png")
        assert out == "وصف الصورة: مربع أحمر"
        req = json.loads(seen[0]["body"])
        assert req["model"] == "llava"
        msg = req["messages"][-1]
        assert base64.b64encode(png).decode() in msg.get("images", []), (
            "image bytes must be sent base64-encoded in images[]")
    finally:
        server.shutdown()


def test_client_openai_protocol_sends_data_url(monkeypatch, vision_enabled):
    """بروتوكول openai: الصورة تصل data-URL داخل image_url."""
    import vision_client
    png = _make_png()
    server, seen = _make_brain_server("openai")
    try:
        vision_enabled(f"http://127.0.0.1:{server.server_address[1]}",
                      protocol="openai")
        out = vision_client.describe(png, "image/png")
        assert out == "وصف الصورة: مربع أحمر"
        req = json.loads(seen[0]["body"])
        content = req["messages"][-1]["content"]
        if isinstance(content, list):
            image_part = [p for p in content if p.get("type") == "image_url"]
            assert image_part, "image_url part required"
            url = image_part[0]["image_url"]["url"]
            assert url.startswith("data:image/png;base64,")
            assert base64.b64encode(png).decode() in url
        else:
            assert base64.b64encode(png).decode() in content, (
                "data URL with b64 image required")
    finally:
        server.shutdown()


def test_client_failures_return_none(monkeypatch, vision_enabled):
    """أي فشل (HTTP/بنية/نص فارغ) → None لا استثناء — fail-closed."""
    import vision_client
    server, _ = _make_brain_server("ollama")
    try:
        vision_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        # نص فارغ من العقل → None
        server2, _ = _make_brain_server("ollama", content="   ")
        try:
            vision_enabled(f"http://127.0.0.1:{server2.server_address[1]}")
            assert vision_client.describe(_make_png(), "image/png") is None
        finally:
            server2.shutdown()
    finally:
        server.shutdown()
    # خادم بعيد غير موجود → None (لا استثناء يصعد)
    vision_enabled("http://127.0.0.1:9")
    assert vision_client.describe(_make_png(), "image/png") is None


def test_disabled_makes_no_request(monkeypatch, vision_enabled):
    """الرؤية معطلة → لا طلب إطلاقًا (لا اتصال ضمني — نمط R-704)."""
    import vision_client
    server, seen = _make_brain_server("ollama")
    try:
        vision_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        config.VISION_ENABLED = False
        assert vision_client.describe(_make_png(), "image/png") is None
        assert len(seen) == 0, "disabled vision must not issue any request"
    finally:
        server.shutdown()


def test_config_defaults_and_env():
    """الافتراضي: معطلة + بلا نموذج رؤية؛ والبيئة تعمل (عملية مستقلة)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("VISION_")}
    code = ("import config; print(config.VISION_ENABLED, "
            "config.VISION_MODEL, config.VISION_MAX_IMAGE_BYTES)")
    r1 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    assert "False None 10485760" in r1.stdout, (
        "defaults: disabled + no vision model + 10MiB cap")
    env2 = dict(env)
    env2["VISION_ENABLED"] = "true"
    env2["VISION_MODEL"] = "llava"
    r2 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env2, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    assert "True llava" in r2.stdout


# ======================== نقطة /vision ========================

def test_vision_endpoint_describes(monkeypatch, vision_enabled):
    """النقطة الفعلية: صورة PNG حقيقية → وصف نصي (معيار إغلاق ٢.٢)."""
    from app import app as fastapi_app, vision_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_brain_server("ollama")
    try:
        vision_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        vision_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/vision", files={"file": ("shot.png",
                                                        _make_png(),
                                                        "image/png")})
            assert r.status_code == 200, r.text
            assert r.json() == {"description": "وصف الصورة: مربع أحمر"}, (
                "image → text description is the closure criterion of 2.2"
            )
    finally:
        server.shutdown()


def test_vision_endpoint_disabled_honest(monkeypatch, vision_enabled):
    """معطل → 503 بالسبب الصريح — لا نجاح كاذب ولا وصف مختلق (المادة ١)."""
    from app import app as fastapi_app, vision_rate_limiter
    from fastapi.testclient import TestClient

    vision_enabled("http://127.0.0.1:1")
    config.VISION_ENABLED = False
    vision_rate_limiter._requests.clear()
    with TestClient(fastapi_app) as client:
        r = client.post("/vision", files={"file": ("s.png", _make_png(),
                                                    "image/png")})
        assert r.status_code == 503, r.text
        assert r.json()["error"] == "vision_disabled"
        assert "reason" in r.json(), "honest reason required"


def test_vision_endpoint_rejects_oversize(monkeypatch, vision_enabled):
    """تجاوز حد الحجم → 413 — لا قراءة اعتباطية في الذاكرة."""
    from app import app as fastapi_app, vision_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_brain_server("ollama")
    try:
        vision_enabled(f"http://127.0.0.1:{server.server_address[1]}",
                       max_bytes=100)
        vision_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/vision", files={"file": ("big.png",
                                                       b"x" * 200,
                                                       "image/png")})
            assert r.status_code == 413, r.text
    finally:
        server.shutdown()


def test_vision_endpoint_rejects_wrong_content_type(monkeypatch, vision_enabled):
    """نوع غير صورة (text/plain) → 415 — قائمة أنواع صارمة."""
    from app import app as fastapi_app, vision_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_brain_server("ollama")
    try:
        vision_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        vision_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            r = client.post("/vision", files={"file": ("note.txt", b"hello",
                                                       "text/plain")})
            assert r.status_code == 415, r.text
    finally:
        server.shutdown()


def test_vision_status_no_secret_leak(monkeypatch, vision_enabled):
    """/vision/status: لا سر أبدًا — العنوان معقّم، والمفتاح لا يظهر."""
    from app import app as fastapi_app
    from fastapi.testclient import TestClient

    vision_enabled("http://owner:super-secret@127.0.0.1:11434?token=abc",
                   api_key="top-secret")
    with TestClient(fastapi_app) as client:
        r = client.get("/vision/status")
        assert r.status_code == 200
        for secret in ("super-secret", "top-secret", "token", "abc"):
            assert secret not in r.text, f"secret leaked: {secret}"
        data = r.json()
        assert data["enabled"] is True
        assert data["model"] == "llava"
        assert "11434" in r.text, "sanitized host+port must remain"


def test_vision_status_disabled_honest():
    """/vision/status معطلة: enabled=False — إفصاح صادق كامل."""
    from app import app as fastapi_app
    from fastapi.testclient import TestClient

    with TestClient(fastapi_app) as client:
        data = client.get("/vision/status").json()
        assert data["enabled"] is False


def test_vision_rate_limited(monkeypatch, vision_enabled):
    """تجاوز حد المعدل (حد /chat نفسه) → 429 مع Retry-After — لا باب مفتوح."""
    from app import app as fastapi_app, vision_rate_limiter
    from fastapi.testclient import TestClient

    server, _ = _make_brain_server("ollama")
    try:
        vision_enabled(f"http://127.0.0.1:{server.server_address[1]}")
        vision_rate_limiter._requests.clear()
        with TestClient(fastapi_app) as client:
            codes = []
            for _ in range(config.MAX_USER_MESSAGES_PER_MINUTE + 2):
                r = client.post("/vision", files={"file": ("s.png",
                                                            _make_png(),
                                                            "image/png")})
                codes.append(r.status_code)
            assert 429 in codes, "rate limit must eventually trigger"
            assert codes.count(200) <= config.MAX_USER_MESSAGES_PER_MINUTE
    finally:
        server.shutdown()
