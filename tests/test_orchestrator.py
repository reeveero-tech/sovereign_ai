"""R-738 (بأمر المالك — «اجعل هناك من يرتب عملها»): المنسّق.

`research.run(goal)` — المنسّق الذي يرتب أدوات البحث والقراءة والاستخلاص
والاستدلال حسب الهدف: بحث ← جلب المصادر ← استخراج الحقائق ← استدلال
وتوليف ← تقرير مستشهد بالمصادر. كل خطوة تُنفذ عبر سجل R-729 (أثر
TOOL_INVOKED إلزامي لكل استدعاء — لا خطوة بلا أثر).
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config

REPO_ROOT = Path(__file__).resolve().parent.parent

# استيراد app يسجل أدوات السجل مرة واحدة (المنسّق يستدعي عبر السجل)
import sys as _sys
_sys.path.insert(0, str(REPO_ROOT / "backend"))
import app as _app  # noqa: F401


def _api_key() -> str:
    return os.environ.get("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


def _make_server(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _make_research_stack(page_text="المشروع السيادي يتبع دستورًا يمنع الادعاء "
                            "بلا دليل مُتحقق. النشر بيد المالك وحده."):
    """الكومة الكاملة: بحث + صفحة + عقل — كلها وهمية وصارمة العقد.

    نتائج البحث تشير إلى خادم الصفحة الوهمي نفسه (لا طلب خارجي أبدًا
    في الاختبارات)."""

    class PageHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = ("<html><head><title>مصدر أول</title></head><body><p>"
                    + page_text + "</p></body></html>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    page = _make_server(PageHandler)
    page_url = f"http://127.0.0.1:{page.server_address[1]}/a"

    class SearchHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            results = {"results": [
                {"title": "مصدر أول", "url": page_url,
                 "content": "مقتطف"}]}
            data = json.dumps(results).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    class BrainHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            prompt = body["messages"][0]["content"]
            # الرد حسب نوع الطلب (استخراج JSON أو استدلال نصي)
            if "JSON" in prompt or "استخرج" in prompt:
                content = json.dumps(
                    {"حقيقة": "الدستور يمنع الادعاء بلا دليل"},
                    ensure_ascii=False)
            else:
                content = "الخلاصة: المشروع يتبع دستورًا صارمًا."
            data = json.dumps({"message": {"content": content}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    search = _make_server(SearchHandler)
    page = _make_server(PageHandler)
    brain = _make_server(BrainHandler)
    return search, page, brain


def _enable_all(monkeypatch, search, page, brain):
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", True)
    monkeypatch.setattr(config, "SEARCH_PROVIDER", "searxng")
    monkeypatch.setattr(config, "SEARCH_BASE_URL",
                        f"http://127.0.0.1:{search.server_address[1]}")
    monkeypatch.setattr(config, "SEARCH_MAX_RESULTS", 5)
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "test-model")
    monkeypatch.setattr(config, "OLLAMA_BASE_URL",
                        f"http://127.0.0.1:{brain.server_address[1]}")
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
    monkeypatch.setattr(config, "OLLAMA_API_KEY", None)
    monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 10.0)
    monkeypatch.setattr(config, "RESEARCH_MAX_SOURCES", 2)
    import web_tools
    monkeypatch.setattr(web_tools, "_validate_host", lambda host: None)


def test_research_run_full_pipeline(monkeypatch):
    """المنسّق كاملًا: هدف → بحث ← قراءة ← استخراج ← استدلال ← تقرير
    مستشهد + أثر سيادي لكل خطوة."""
    import research_orchestrator as orchestrator
    search, page, brain = _make_research_stack()
    try:
        _enable_all(monkeypatch, search, page, brain)
        out = orchestrator.run_research("دستور المشروع السيادي")
        assert out["ok"] is True
        assert out["goal"] == "دستور المشروع السيادي"
        # المصادر مستشهدة
        assert out["sources"][0]["url"].startswith("http://127.0.0.1:")
        # كل خطوة موثقة
        steps = {s["step"] for s in out["steps"]}
        assert {"web.search", "web.fetch", "reasoning.extract",
                "reasoning.reason"} <= steps
        assert all(s["ok"] for s in out["steps"])
        # التقرير النهائي من الاستدلال
        assert "الخلاصة" in out["report"]
    finally:
        for s in (search, page, brain):
            s.shutdown()


def test_research_run_honest_failure_without_brain(monkeypatch):
    """عقل معطل → فشل صادق مسجل — لا تقرير مختلق."""
    import research_orchestrator as orchestrator
    search, page, brain = _make_research_stack()
    try:
        _enable_all(monkeypatch, search, page, brain)
        monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
        monkeypatch.setattr(config, "OLLAMA_MODEL", None)
        out = orchestrator.run_research("أي هدف")
        assert out["ok"] is False
        assert any(not s["ok"] for s in out["steps"])
        assert "العقل معطل" in out["error"]
    finally:
        for s in (search, page, brain):
            s.shutdown()


def test_research_run_honest_failure_without_web(monkeypatch):
    """أدوات الويب معطلة → فشل صادق (لا اتصال ضمني)."""
    import research_orchestrator as orchestrator
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", False)
    out = orchestrator.run_research("أي هدف")
    assert out["ok"] is False
    assert "معطلة" in out["error"]


def test_research_registered_and_invokable(monkeypatch):
    """الأداة مسجلة كـ research.run وتُستدعى عبر /tools/invoke (بمفتاح
    المالك) — والنتيجة كما هي من الدالة."""
    from app import app
    from fastapi.testclient import TestClient

    search, page, brain = _make_research_stack()
    try:
        _enable_all(monkeypatch, search, page, brain)
        with TestClient(app) as client:
            listed = client.get("/tools/list").json()["tools"]
            assert any(t["name"] == "research.run" for t in listed)
            r = client.post("/tools/invoke", json={
                "tool": "research.run",
                "api_key": _api_key(),
                "inputs": {"goal": "دستور المشروع"},
            })
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["ok"] is True
            assert body["result"]["ok"] is True
            assert body["result"]["sources"]
    finally:
        for s in (search, page, brain):
            s.shutdown()
