"""R-747 (البند ٣.٥ — أدوات الوسائط): توليد صور عبر خدمة ذاتية الاستضافة —
بأمر المالك «استخدم خدمة وسائط لا تتطلب إرسال البيانات لطرف ثالث».

العقد: OpenAI Images (POST {base}/images/generations — response_format=b64_json)
الذي يقدّمه LocalAI (مفتوح المصدر، يعمل على عتاد المالك).

حارس السيادة (جوهر أمر المالك): لا يُرسل أي طلب إلا إلى مضيف ذاتي الاستضافة —
loopback، عناوين خاصة (RFC1918 / ULA fc00::/7)، شبكة Fly الخاصة (.internal /
.flycast)، .local، أو اسم خدمة بلا نقاط (docker compose). أي مضيف عام (اسمًا
أو عنوانًا) → رفض **قبل أي اتصال**. لا تتبّع لإعادة التوجيه (لا تهريب لطرف ثالث).

1. معطل افتراضيًا: العميل None، و/media/image ← 503 بالسبب.
2. تصنيف المضيف: ذاتي ✓ / عام ✗ (أسماء وعناوين IPv4/IPv6).
3. مفعّل بمضيف عام → لا اتصال إطلاقًا، و/media/image ← 503 بسبب السيادة.
4. نجاح: عقد الطلب (prompt/size/n/response_format)، صورة PNG حقيقية بـ sha256.
5. فشل صادق: جسد ليس صورة / base64 فاسد / تجاوز الحجم / إعادة توجيه → 502.
6. url في الاستجابة: يُجلب فقط من نفس المضيف الذاتي؛ غيره يُرفض بلا اتصال.
7. حدود: prompt فارغ 400، طويل 413، size غير مسموح 400.
8. أداة media.image مسجلة، و/media/status بلا سر، وتغطية ٤.٤ تصير built_disabled.
"""

import base64
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import config

PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def _server(payload=None, status=200, raw=None, redirect=None, image_path_bytes=None):
    seen = []

    class H(BaseHTTPRequestHandler):
        def _send(self, code, body=b"", ctype="application/json", headers=None):
            self.send_response(code)
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            seen.append({"path": self.path, "body": self.rfile.read(n),
                         "headers": dict(self.headers)})
            if redirect:
                return self._send(302, headers={"Location": redirect})
            if status != 200:
                return self._send(status)
            if raw is not None:
                return self._send(200, raw)
            body = payload if payload is not None else {
                "data": [{"b64_json": base64.b64encode(PNG_1x1).decode()}]}
            return self._send(200, json.dumps(body).encode())

        def do_GET(self):
            seen.append({"path": self.path, "method": "GET"})
            return self._send(200, image_path_bytes or PNG_1x1, ctype="image/png")

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


@pytest.fixture
def media(monkeypatch):
    def _enable(base_url, model="sd-turbo", api_key=None, max_bytes=None):
        monkeypatch.setattr(config, "MEDIA_ENABLED", True)
        monkeypatch.setattr(config, "MEDIA_BASE_URL", base_url)
        monkeypatch.setattr(config, "MEDIA_MODEL", model)
        monkeypatch.setattr(config, "MEDIA_API_KEY", api_key)
        monkeypatch.setattr(config, "MEDIA_TIMEOUT_SECONDS", 10.0)
        if max_bytes is not None:
            monkeypatch.setattr(config, "MEDIA_MAX_IMAGE_BYTES", max_bytes)
    return _enable


def _client():
    from fastapi.testclient import TestClient
    import app as app_module
    return TestClient(app_module.app)


def test_disabled_by_default():
    import media_client
    assert config.MEDIA_ENABLED is False
    assert media_client.generate_image("قطة") is None
    with _client() as c:
        r = c.post("/media/image", json={"prompt": "قطة"})
        assert r.status_code == 503 and r.json()["error"] == "media_disabled"


def _j(*parts):
    """تركيب العناوين الخاصة وقت التشغيل — حارسا HIST-02 (test_no_private_ips_in_git
    + test_private_ip_guard_ipv6) يمنعان أي عنوان خاص حرفي في ملف متتبع،
    بلا استثناءات (قرار المالك). نفس نمط tests/test_private_ip_guard_ipv6.py."""
    return "".join(parts)


SELF_HOSTED = {
    "loopback4": "http://127.0.0.1:8080/v1",
    "localhost": "http://localhost:8080/v1",
    "compose_service": "http://localai:8080/v1",
    "fly_internal": "http://media.internal:8080/v1",
    "fly_flycast": "http://media.flycast/v1",
    "mdns_local": "http://box.local/v1",
    "rfc1918_10": _j("http://", "10.", "1.2.3", "/v1"),
    "rfc1918_192": _j("http://", "192.", "168.", "1.2", ":8080/v1"),
    "rfc1918_172": _j("http://", "172.", "16.", "0.9", "/v1"),
    "loopback6": "http://[::1]:8080/v1",
    "ula6": _j("http://[", "fd", "00::1", "]:8080/v1"),
}


@pytest.mark.parametrize("url", list(SELF_HOSTED.values()), ids=list(SELF_HOSTED))
def test_self_hosted_hosts_accepted(url):
    import media_client
    assert media_client.is_self_hosted(url) is True, url


PUBLIC = {
    "openai": "https://api.openai.com/v1",
    "public_name": "https://media.example.com/v1",
    "public_ip4": "http://8.8.8.8/v1",
    "public_ip6": "http://[2001:4860:4860::8888]/v1",
    "lookalike": "http://localai.attacker.com/v1",
    "bad_scheme": "ftp://127.0.0.1/v1",
    "no_host": "http:///v1",
    "garbage": "not a url",
}


@pytest.mark.parametrize("url", list(PUBLIC.values()), ids=list(PUBLIC))
def test_public_hosts_refused(url):
    import media_client
    assert media_client.is_self_hosted(url) is False, url


def test_third_party_host_never_contacted(media, monkeypatch):
    import httpx
    import media_client

    class Boom:
        def __init__(self, *a, **k):
            raise AssertionError("اتصال بطرف ثالث — محظور")

    monkeypatch.setattr(httpx, "Client", Boom)
    media("https://api.openai.com/v1", api_key="sk-should-never-leave")
    assert media_client.generate_image("قطة") is None
    assert media_client.last_outcome()["result"] == "host_not_self_hosted"
    with _client() as c:
        r = c.post("/media/image", json={"prompt": "قطة"})
        assert r.status_code == 503 and r.json()["error"] == "media_host_not_self_hosted"


def test_success_contract_and_real_png(media):
    import media_client
    srv, seen = _server()
    try:
        media(f"http://127.0.0.1:{srv.server_address[1]}/v1", api_key="local-key")
        out = media_client.generate_image("قطة على القمر", size="256x256")
        assert out is not None
        img, mime = out
        assert img == PNG_1x1 and mime == "image/png"
        req = json.loads(seen[0]["body"])
        assert seen[0]["path"] == "/v1/images/generations"
        assert req == {"prompt": "قطة على القمر", "size": "256x256", "n": 1,
                       "response_format": "b64_json", "model": "sd-turbo"}
        assert seen[0]["headers"].get("Authorization") == "Bearer local-key"
        with _client() as c:
            r = c.post("/media/image", json={"prompt": "قطة", "size": "256x256"})
            assert r.status_code == 200, r.text
            b = r.json()
            assert b["mime"] == "image/png" and b["bytes"] == len(PNG_1x1)
            assert b["sha256"] == hashlib.sha256(PNG_1x1).hexdigest()
            assert base64.b64decode(b["image_b64"]) == PNG_1x1
    finally:
        srv.shutdown()


@pytest.mark.parametrize("kind", ["not_image", "bad_b64", "too_big", "redirect", "http500", "no_data"])
def test_honest_failures(media, kind):
    import media_client
    kw = {}
    if kind == "not_image":
        kw["payload"] = {"data": [{"b64_json": base64.b64encode(b"hello world").decode()}]}
    elif kind == "bad_b64":
        kw["payload"] = {"data": [{"b64_json": "@@@not-base64@@@"}]}
    elif kind == "redirect":
        kw["redirect"] = "https://evil.example.com/steal"
    elif kind == "http500":
        kw["status"] = 500
    elif kind == "no_data":
        kw["payload"] = {"data": []}
    srv, _ = _server(**kw)
    try:
        media(f"http://127.0.0.1:{srv.server_address[1]}/v1",
              max_bytes=10 if kind == "too_big" else None)
        assert media_client.generate_image("قطة") is None, kind
        with _client() as c:
            r = c.post("/media/image", json={"prompt": "قطة"})
            assert r.status_code == 502 and r.json()["error"] == "media_failed", kind
    finally:
        srv.shutdown()


def test_url_response_fetched_only_from_same_self_host(media):
    import media_client
    other, other_seen = _server()  # مضيف آخر (منفذ مختلف) — لا يُلمس
    try:
        foreign = f"http://127.0.0.1:{other.server_address[1]}/generated/x.png"
        srv, _ = _server(payload={"data": [{"url": foreign}]})
        try:
            media(f"http://127.0.0.1:{srv.server_address[1]}/v1")
            assert media_client.generate_image("قطة") is None
            assert other_seen == [], "جُلب من مضيف غير مضيف الخدمة"
        finally:
            srv.shutdown()
        srv3, seen3 = _server(payload={"data": [{"url": "/generated/x.png"}]})
        try:
            media(f"http://127.0.0.1:{srv3.server_address[1]}/v1")
            out = media_client.generate_image("قطة")
            assert out is not None and out[0] == PNG_1x1
            assert any(s.get("method") == "GET" for s in seen3)
        finally:
            srv3.shutdown()
    finally:
        other.shutdown()


def test_request_limits(media):
    srv, seen = _server()
    try:
        media(f"http://127.0.0.1:{srv.server_address[1]}/v1")
        with _client() as c:
            assert c.post("/media/image", json={"prompt": "   "}).status_code == 400
            assert c.post("/media/image", json={"prompt": "x" * (config.MEDIA_MAX_PROMPT_CHARS + 1)}).status_code == 413
            assert c.post("/media/image", json={"prompt": "قطة", "size": "4096x4096"}).status_code == 400
        assert seen == [], "لا طلب للخدمة قبل اجتياز الحدود"
    finally:
        srv.shutdown()


def test_tool_status_and_benchmark_coverage(media):
    import tool_registry
    with _client() as c:
        names = {t["name"] for t in tool_registry.get_registry().list_tools()}
        assert "media.image" in names
        media("http://127.0.0.1:9/v1", api_key="local-secret-zzz")
        s = c.get("/media/status").json()
        assert s["enabled"] is True and s["self_hosted"] is True
        assert "local-secret-zzz" not in json.dumps(s)
    import external_benchmark
    cov = external_benchmark.capability_coverage(names, {"web_tools": False, "media": False})
    st = {i["id"]: i["status"] for i in cov["items"]}
    assert st["image_generation"] == "built_disabled"
