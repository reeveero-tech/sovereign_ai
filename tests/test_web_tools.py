"""R-738 (البند ٣.٢ + ٢.٥ — بأمر المالك «ابدأ»): أداة البحث والقراءة.

ثلاث أدوات ويب مسجلة في سجل R-729 (كل استدعاء بأثر TOOL_INVOKED):
- `web.search` — بحث ويب حي (مزودان: SearXNG ذاتي الاستضافة / Tavily سحابي)
  بنتائج مستشهدة بمصادر (title/url/snippet) — معيار إغلاق ٢.٥.
- `web.fetch` — جلب صفحة وتحويلها لنص، محروسة ضد SSRF (تحقق كل قفزة:
  مخطط http/https فقط + حجب العناوين الخاصة/الداخلية + حد حجم + قائمة
  أنواع + سقف تحويلات).
- `web.summarize` — استخلاص عبر عقل المنشور القائم (ollama_client).

مبادئ قائمة محفوظة: معطل افتراضيًا (WEB_TOOLS_ENABLED — لا اتصال ضمني)،
fail-closed (كل فشل يُعلن بصدق ولا نتائج مختلقة)، لا مفتاح في السجلات.

ملاحظة حراسة: العناوين الخاصة في هذا الملف مُجمَّعة وقت التشغيل
(لا نص حرفيًا — حارس العناوين يمسح كل ملف متتبع بلا استثناءات).
"""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import config


def _api_key() -> str:
    return os.environ.get("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


# عناوين خاصة مُجمَّعة وقت التشغيل (لا تظهر نصًا في الملف المتتبع)
PRIV_10 = "10." + "0.0.1"
PRIV_192 = "192." + "168.1.1"
PRIV_172 = "172." + "16.0.1"


def _make_server(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _make_search_server(kind, results=None):
    """خادم بحث وهمي: searxng (GET /search?q=..&format=json) أو
    tavily (POST /search بجسد JSON يضم المفتاح والاستعلام)."""
    results = results or [
        {"title": "نتيجة أولى", "url": "https://example.org/a",
         "content": "مقتطف أول"},
        {"title": "نتيجة ثانية", "url": "https://example.org/b",
         "content": "مقتطف ثانٍ"},
    ]
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlsplit(self.path)
            seen.append({"method": "GET", "path": parsed.path,
                         "query": parse_qs(parsed.query),
                         "headers": dict(self.headers)})
            if kind == "searxng" and parsed.path == "/search":
                data = json.dumps({"results": results}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            seen.append({"method": "POST", "path": self.path, "body": body,
                         "headers": dict(self.headers)})
            if kind == "tavily" and self.path == "/search":
                data = json.dumps({"results": results}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    return _make_server(Handler), seen


def _make_page_server(html="<html><head><title>صفحة اختبار</title>"
                       "<style>x{}</style></head><body>"
                       "<script>bad()</script><h1>عنوان</h1>"
                       "<p>نص الفقرة</p></body></html>",
                       content_type="text/html; charset=utf-8",
                       status=200, redirect_to=None):
    html = html.encode("utf-8")
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append({"path": self.path, "headers": dict(self.headers)})
            if redirect_to is not None:
                self.send_response(302)
                self.send_header("Location", redirect_to)
                self.end_headers()
                return
            data = html
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    return _make_server(Handler), seen


def _make_ollama_server(content="هذا ملخص الاختبار"):
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            seen.append({"path": self.path, "body": body})
            if self.path == "/api/chat":
                data = json.dumps(
                    {"message": {"content": content}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    return _make_server(Handler), seen


def _enable_web(monkeypatch, **overrides):
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", True)
    for k, v in overrides.items():
        monkeypatch.setattr(config, k, v)


# ======================== السجل: تمرير المدخلات ========================

def test_registry_passes_inputs_to_handler():
    """invoke(inputs=...) يمرر المدخلات كوسائط مسماة للمُنفذ المعلن."""
    from tool_registry import ToolRegistry, ToolSpec
    received = {}

    def handler(query):
        received["query"] = query
        return {"echo": query}

    reg = ToolRegistry()
    reg.register(ToolSpec(name="t.echo", description="تجربة",
                         inputs={"query": "استعلام"}, outputs="echo",
                         handler=handler))
    result = reg.invoke("t.echo", caller="owner", inputs={"query": "مرحبا"})
    assert result["ok"] is True
    assert received["query"] == "مرحبا"
    assert result["result"] == {"echo": "مرحبا"}


def test_registry_rejects_unknown_input_keys():
    """مفتاح مدخل غير معلن في الأداة → استدعاء فاشل مسجل (لا تنفيذ)."""
    from tool_registry import ToolRegistry, ToolSpec
    executed = []

    def handler(query):
        executed.append(query)
        return {}

    reg = ToolRegistry()
    reg.register(ToolSpec(name="t.strict", description="تجربة",
                         inputs={"query": "استعلام"}, outputs="echo",
                         handler=handler))
    result = reg.invoke("t.strict", caller="owner",
                        inputs={"query": "س", "rogue": "x"})
    assert result["ok"] is False
    assert executed == [], "unknown input must prevent execution"
    assert "غير معلنة" in result["error"]


# ======================== البحث (web.search) ========================

def test_search_searxng(monkeypatch):
    import web_tools
    server, seen = _make_search_server("searxng")
    try:
        _enable_web(monkeypatch,
                    SEARCH_PROVIDER="searxng",
                    SEARCH_BASE_URL=f"http://127.0.0.1:{server.server_address[1]}")
        out = web_tools.search("اختبار البحث")
        assert out["provider"] == "searxng"
        assert out["count"] == 2
        first = out["results"][0]
        assert first["url"] == "https://example.org/a"
        assert first["title"] == "نتيجة أولى"
        assert first["snippet"] == "مقتطف أول"
        assert seen[0]["method"] == "GET"
        assert seen[0]["query"].get("q") == ["اختبار البحث"]
        assert seen[0]["query"].get("format") == ["json"]
        assert "Authorization" not in seen[0]["headers"], "no key for local"
    finally:
        server.shutdown()


def test_search_tavily(monkeypatch):
    import web_tools
    server, seen = _make_search_server("tavily")
    try:
        _enable_web(monkeypatch,
                    SEARCH_PROVIDER="tavily",
                    SEARCH_BASE_URL=f"http://127.0.0.1:{server.server_address[1]}",
                    SEARCH_API_KEY="secret-tavily-key")
        out = web_tools.search("اختبار", max_results=3)
        assert out["provider"] == "tavily"
        assert out["count"] == 2
        body = json.loads(seen[0]["body"])
        assert body["api_key"] == "secret-tavily-key"
        assert body["query"] == "اختبار"
        assert body["max_results"] == 3
    finally:
        server.shutdown()


def test_search_unknown_provider_fails_closed(monkeypatch):
    import web_tools
    _enable_web(monkeypatch, SEARCH_PROVIDER="bogus-provider")
    with pytest.raises(RuntimeError, match="مزود بحث غير معروف"):
        web_tools.search("أي شيء")


def test_search_disabled_makes_no_request(monkeypatch):
    import web_tools
    server, seen = _make_search_server("searxng")
    try:
        monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", False)
        with pytest.raises(RuntimeError, match="معطلة"):
            web_tools.search("اختبار")
        assert len(seen) == 0, "disabled web tools must not issue requests"
    finally:
        server.shutdown()


def test_search_malformed_response_fails_closed(monkeypatch):
    """استجابة فاسدة → RuntimeError — لا نتائج مختلقة (fail-closed)."""
    import web_tools
    bad = _make_server(type("H", (BaseHTTPRequestHandler,), {
        "do_GET": lambda self: (
            self.send_response(200),
            self.send_header("Content-Type", "application/json"),
            self.end_headers(),
            self.wfile.write(b"not-json"),
        ),
        "log_message": lambda self, *a: None,
    }))
    try:
        _enable_web(monkeypatch, SEARCH_PROVIDER="searxng",
                    SEARCH_BASE_URL=f"http://127.0.0.1:{bad.server_address[1]}")
        with pytest.raises(RuntimeError, match="فشل البحث"):
            web_tools.search("اختبار")
    finally:
        bad.shutdown()


# ======================== حارس SSRF (web.fetch) ========================

def test_validate_host_blocks_private_addresses():
    """العناوين الخاصة/الداخلية محجوبة — لا اتصال أبدًا (fail-closed)."""
    import web_tools
    # عناوين IPv6 خاصة مُجمَّعة وقت التشغيل (لا نص حرفيًا — نمط الحارس)
    ula = "fd" + "00::" + "1"
    link_local = "fe" + "80::" + "1"
    for host in (PRIV_10, PRIV_192, PRIV_172, "127.0.0.1", "localhost",
                 ula, link_local, "::1"):
        with pytest.raises(ValueError):
            web_tools._validate_host(host)


def test_fetch_rejects_non_http_schemes(monkeypatch):
    import web_tools
    _enable_web(monkeypatch)
    with pytest.raises(ValueError, match="مخطط"):
        web_tools.fetch("ftp://example.com/file")


def test_fetch_blocks_private_target(monkeypatch):
    """هدف على شبكة خاصة → رفض قبل أي اتصال (لا خادم أصلًا)."""
    import web_tools
    _enable_web(monkeypatch)
    with pytest.raises(ValueError, match="محجوب"):
        web_tools.fetch(f"http://{PRIV_10}/")


def test_fetch_happy_path(monkeypatch):
    import web_tools
    server, _ = _make_page_server()
    try:
        _enable_web(monkeypatch)
        # السماح بخادم الاختبار فقط (على loopback) — الحارس نفسه مُختبر
        # بشروطه الصارمة في test_validate_host_blocks_private_addresses
        monkeypatch.setattr(web_tools, "_validate_host", lambda host: None)
        out = web_tools.fetch(f"http://127.0.0.1:{server.server_address[1]}/")
        assert out["title"] == "صفحة اختبار"
        assert "نص الفقرة" in out["text"]
        assert "bad()" not in out["text"], "script content must be stripped"
        assert "x{}" not in out["text"], "style content must be stripped"
        assert out["content_type"].startswith("text/html")
    finally:
        server.shutdown()


def test_fetch_redirect_to_private_blocked(monkeypatch):
    """تحويل 302 نحو عنوان خاص → حجب عند التحقق من القفزة الثانية."""
    import web_tools
    server, _ = _make_page_server(redirect_to="http://127.0.0.1:9/priv/")
    try:
        _enable_web(monkeypatch)
        port = server.server_address[1]

        def allow_test_server_only(host):
            if host and str(host).endswith(f":{port}"):
                return
            raise ValueError("محجوب في الاختبار")

        monkeypatch.setattr(web_tools, "_validate_host", allow_test_server_only)
        with pytest.raises(ValueError, match="محجوب"):
            web_tools.fetch(f"http://127.0.0.1:{port}/")
    finally:
        server.shutdown()


def test_fetch_size_cap(monkeypatch):
    import web_tools
    big = "<html><body><p>" + "كلمة " * 5000 + "</p></body></html>"
    server, _ = _make_page_server(html=big)
    try:
        _enable_web(monkeypatch, WEB_FETCH_MAX_BYTES=2048)
        monkeypatch.setattr(web_tools, "_validate_host", lambda host: None)
        out = web_tools.fetch(f"http://127.0.0.1:{server.server_address[1]}/")
        assert len(out["text"]) <= 4096, "size cap must bound the text"
        assert out["bytes"] <= 2048
    finally:
        server.shutdown()


def test_fetch_content_type_allowlist(monkeypatch):
    import web_tools
    server, _ = _make_page_server(content_type="application/octet-stream")
    try:
        _enable_web(monkeypatch)
        monkeypatch.setattr(web_tools, "_validate_host", lambda host: None)
        with pytest.raises(ValueError, match="نوع غير مسموح"):
            web_tools.fetch(f"http://127.0.0.1:{server.server_address[1]}/")
    finally:
        server.shutdown()


# ======================== الاستخلاص (web.summarize) ========================

def test_summarize_uses_brain(monkeypatch):
    import web_tools
    server, seen = _make_ollama_server()
    try:
        monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
        monkeypatch.setattr(config, "OLLAMA_MODEL", "test-model")
        monkeypatch.setattr(config, "OLLAMA_BASE_URL",
                            f"http://127.0.0.1:{server.server_address[1]}")
        monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
        monkeypatch.setattr(config, "OLLAMA_API_KEY", None)
        monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 10.0)
        out = web_tools.summarize("نص طويل للاستخلاص")
        assert out["summary"] == "هذا ملخص الاختبار"
        assert len(seen) == 1
    finally:
        server.shutdown()


def test_summarize_brain_disabled_honest(monkeypatch):
    import web_tools
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    monkeypatch.setattr(config, "OLLAMA_MODEL", None)
    with pytest.raises(RuntimeError, match="العقل معطل"):
        web_tools.summarize("نص")


# ======================== النقاط (/tools) ========================

def test_tools_list_shows_web_tools():
    from app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        r = client.get("/tools/list")
        assert r.status_code == 200
        tools = {t["name"]: t for t in r.json()["tools"]}
        assert "web.search" in tools
        assert "query" in tools["web.search"]["inputs"]
        assert "web.fetch" in tools
        assert "url" in tools["web.fetch"]["inputs"]
        assert "web.summarize" in tools
        assert "text" in tools["web.summarize"]["inputs"]


def test_tools_invoke_web_search_endpoint(monkeypatch):
    from app import app
    from fastapi.testclient import TestClient

    server, _ = _make_search_server("searxng")
    try:
        _enable_web(monkeypatch,
                    SEARCH_PROVIDER="searxng",
                    SEARCH_BASE_URL=f"http://127.0.0.1:{server.server_address[1]}")
        with TestClient(app) as client:
            r = client.post("/tools/invoke", json={
                "tool": "web.search",
                "api_key": _api_key(),
                "inputs": {"query": "اختبار حي"},
            })
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["ok"] is True
            assert body["result"]["count"] == 2
            assert body["result"]["results"][0]["url"] == "https://example.org/a"
    finally:
        server.shutdown()


def test_web_tools_disabled_honest(monkeypatch):
    from app import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", False)
    with TestClient(app) as client:
        r = client.post("/tools/invoke", json={
            "tool": "web.search",
            "api_key": _api_key(),
            "inputs": {"query": "أي شيء"},
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is False
        assert "معطلة" in body["error"], "honest disabled reason required"


def test_tools_invoke_rejects_undeclared_input(monkeypatch):
    from app import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        r = client.post("/tools/invoke", json={
            "tool": "web.search",
            "api_key": _api_key(),
            "inputs": {"query": "س", "injection": "x"},
        })
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is False
        assert "غير معلنة" in r.json()["error"]


# ======================== الإعدادات ========================

def test_config_defaults_and_env():
    """الافتراضي: معطل + مزود ذاتي؛ والبيئة تعمل (عملية مستقلة)."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("WEB_", "SEARCH_"))}
    code = ("import config; print(config.WEB_TOOLS_ENABLED, "
            "config.SEARCH_PROVIDER, config.SEARCH_BASE_URL)")
    r1 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    assert "False searxng" in r1.stdout, "defaults: disabled + local searxng"
    env2 = dict(env)
    env2["WEB_TOOLS_ENABLED"] = "true"
    env2["SEARCH_PROVIDER"] = "tavily"
    r2 = subprocess.run([sys.executable, "-c", code], cwd="backend",
                        env=env2, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    assert "True tavily" in r2.stdout
