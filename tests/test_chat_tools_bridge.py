"""R-787: جسر المحادثة ↔ أدوات المشروع.

الدافع (المالك 2026-10-27، بدليل محادثته الحية): «أخبرني عن قدراتك» ⇒ قائمة
عامة لا علاقة لها بالمشروع؛ «حلل https://github.com/reeveero-tech/sovereign_ai»
⇒ «لا أملك الوصول إلى الإنترنت»؛ ومن /console لا طريق للعودة إلى المحادثة.

المثبت هنا:
- سؤال القدرات ⇒ الجرد الحي (/capabilities) وأسماء الأدوات الفعلية تصل للعقل، و`tools_used` يعلنها.
- رابط GitHub ⇒ `web.fetch` يُستدعى عبر السجل (أثر `tool_invoked` بـ caller=chat) ومحتواه يصل للعقل.
- فشل الجلب ⇒ يُمرر للعقل نصًا صادقًا (لا محتوى مختلق) ويُعلن «فشل قراءة».
- رسالة عادية ⇒ لا أدوات ولا كتلة نتائج.
- تعليمات النظام تعلن الهوية: sovereign_ai، والنموذج عقل لغوي فقط.
- OLLAMA_NUM_CTX يضبط نافذة السياق فقط عند ضبطه.
- /console فيه رابط عودة إلى المحادثة؛ واجهة المحادثة تعرض الأدوات المستخدمة.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import config

ROOT = Path(__file__).resolve().parent.parent
CHAT_UI = ROOT / "frontend" / "chat" / "index.html"
LEGACY_UI = ROOT / "frontend" / "index.html"


def _fake_ollama():
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            seen.append(json.loads(self.rfile.read(n)))
            data = json.dumps({"message": {"role": "assistant", "content": "رد العقل"}, "done": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


@pytest.fixture
def brain(monkeypatch):
    srv, seen = _fake_ollama()
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "fake-model")
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    monkeypatch.setattr(config, "OLLAMA_API_KEY", None)
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama", raising=False)
    monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 10.0)
    monkeypatch.setattr(config, "OLLAMA_NUM_CTX", 0, raising=False)
    yield seen
    srv.shutdown()


def _client():
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient
    chat_rate_limiter._requests.clear()
    return TestClient(fastapi_app)


def _system_for(seen, text):
    calls = [b for b in seen if b.get("messages") and b["messages"][-1].get("content") == text]
    assert calls, "brain must be called with the current message"
    return calls[-1]["messages"][0]["content"]


GH_FAKE = {
    "https://api.github.com/repos/acme/demo": json.dumps({
        "full_name": "acme/demo", "description": "وصف-المستودع-المزيف-787",
        "language": "Python", "stargazers_count": 3, "size": 120,
        "created_at": "2026-01-01T00:00:00Z", "pushed_at": "2026-10-01T00:00:00Z",
        "default_branch": "main"}),
    "https://api.github.com/repos/acme/demo/languages": json.dumps({"Python": 900, "HTML": 100}),
    "https://api.github.com/repos/acme/demo/contents": json.dumps([
        {"name": "backend", "type": "dir"}, {"name": "docs", "type": "dir"},
        {"name": "README.md", "type": "file"}]),
    "https://api.github.com/repos/acme/demo/commits?per_page=6": json.dumps([
        {"sha": "abcdef1234", "commit": {"message": "R-999: التزام-مزيف\nتفاصيل",
                                         "author": {"date": "2026-10-02T00:00:00Z"}}}]),
    "https://raw.githubusercontent.com/acme/demo/main/README.md": "README-مزيف-787 نظام تجريبي",
    "https://raw.githubusercontent.com/acme/demo/main/docs/PROJECT_STATE.md": "حالة-مزيفة-787",
}


@pytest.fixture
def fake_web(monkeypatch):
    import web_tools
    fetched = []

    def fake_fetch(url, timeout=None):
        fetched.append(url)
        if url not in GH_FAKE:
            raise RuntimeError("404 غير موجود")
        return {"url": url, "title": "", "text": GH_FAKE[url], "content_type": "application/json", "bytes": 1}

    monkeypatch.setattr(web_tools, "fetch", fake_fetch)
    return fetched


@pytest.fixture
def ledger_spy(monkeypatch):
    from memory.core import get_core
    core = get_core()
    events = []
    orig = core.append_event

    def spy(event_type, payload, *a, **kw):
        events.append((event_type, dict(payload)))
        return orig(event_type, payload, *a, **kw)

    monkeypatch.setattr(core, "append_event", spy)
    return events


def test_capability_question_injects_live_inventory(brain):
    text = "أخبرني عن قدراتك"
    with _client() as c:
        r = c.post("/chat", json={"text": text})
    assert r.status_code == 200, r.text
    assert "جرد القدرات الحي" in r.json()["tools_used"]
    system = _system_for(brain, text)
    assert "جرد القدرات الحي لمشروع sovereign_ai" in system
    assert "web.fetch" in system and "health.snapshot" in system, "real registered tool names must reach the brain"
    assert "مبنية لكنها معطلة" in system or "مفعّلة" in system


def test_identity_declares_project_and_model_as_brain_only(brain):
    text = "مرحبا"
    with _client() as c:
        r = c.post("/chat", json={"text": text})
    assert r.status_code == 200
    system = _system_for(brain, text)
    assert "sovereign_ai" in system
    assert "«fake-model» هو عقلك اللغوي فقط" in system
    assert "لا تقل أبدًا إنك لا تستطيع الوصول" in system


def test_github_url_fetched_through_registry_with_signed_trace(brain, fake_web, ledger_spy):
    text = "قم بتحليل المشروع https://github.com/acme/demo تحليلًا دقيقًا"
    with _client() as c:
        r = c.post("/chat", json={"text": text})
    assert r.status_code == 200, r.text
    assert "قراءة GitHub: acme/demo" in r.json()["tools_used"]
    assert "https://api.github.com/repos/acme/demo" in fake_web
    system = _system_for(brain, text)
    for needle in ("وصف-المستودع-المزيف-787", "Python 90%", "backend/", "R-999: التزام-مزيف",
                   "README-مزيف-787", "حالة-مزيفة-787", "نتائج أدوات النظام (حقيقية، جُلبت الآن)"):
        assert needle in system, needle
    traces = [p for t, p in ledger_spy if t == "tool_invoked" and p.get("tool") == "web.fetch"]
    assert traces and all(p["caller"] == "chat" for p in traces), "every fetch must leave a tool_invoked trace"
    assert len(traces) == len(fake_web)


def test_fetch_failure_is_reported_not_invented(brain, monkeypatch):
    import web_tools

    def boom(url, timeout=None):
        raise RuntimeError("أدوات الويب معطلة — WEB_TOOLS_ENABLED بيد المالك")

    monkeypatch.setattr(web_tools, "fetch", boom)
    text = "اقرأ https://example.com/page"
    with _client() as c:
        r = c.post("/chat", json={"text": text})
    assert r.status_code == 200
    assert any(t.startswith("فشل قراءة") for t in r.json()["tools_used"])
    system = _system_for(brain, text)
    assert "فشلت فعليًا" in system and "WEB_TOOLS_ENABLED" in system


def test_plain_message_uses_no_tools(brain, fake_web):
    text = "اكتب لي خطة يومية للعمل"
    with _client() as c:
        r = c.post("/chat", json={"text": text})
    assert r.status_code == 200
    assert r.json()["tools_used"] == []
    assert fake_web == []
    assert "نتائج أدوات النظام (حقيقية، جُلبت الآن)" not in _system_for(brain, text)


def test_num_ctx_only_when_configured(brain, monkeypatch):
    import ollama_client
    ollama_client.chat("نظام", "س1")
    assert "num_ctx" not in (brain[-1].get("options") or {})
    monkeypatch.setattr(config, "OLLAMA_NUM_CTX", 8192, raising=False)
    ollama_client.chat("نظام", "س2")
    assert brain[-1]["options"]["num_ctx"] == 8192


def test_console_has_back_to_chat_link():
    with _client() as c:
        r = c.get("/console")
    assert r.status_code == 200
    assert 'id="r787-back-to-chat" href="/"' in r.text


def test_chat_ui_renders_tools_used_and_explains_buttons():
    html = CHAT_UI.read_text(encoding="utf-8")
    assert "data.tools_used" in html and "أدوات النظام المستخدمة" in html
    assert 'title="يمسح المحادثة الحالية' in html
    assert 'title="لوحة المراقبة القديمة' in html


def test_fly_enables_web_tools_and_context_window():
    toml = (ROOT / "fly.toml").read_text(encoding="utf-8")
    assert "WEB_TOOLS_ENABLED = 'true'" in toml
    assert "OLLAMA_NUM_CTX = '8192'" in toml
