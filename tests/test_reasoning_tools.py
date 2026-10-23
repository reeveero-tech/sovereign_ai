"""R-738 (بأمر المالك — ترسانة الاستدلال): محور الاستنتاج والاستخراج
والاستنباط والاستدلال والتنقيح.

كل أداة تعمل عبر عقل المنشور (ollama_client — بروتوكولاه R-736):
- reasoning.extract  — استخراج منظّم (نص → JSON بالحقول المطلوبة)
- reasoning.infer    — استنتاج (وقائع → استنتاجات صريحة)
- reasoning.deduce   — استنباط (سياق → فرضيات وما لم يُصرح به)
- reasoning.verify   — تنقيح (ادعاء × دليل → حكم مدعوم)
- reasoning.reason   — استدلال (سؤال × سياق → خطوات واستنتاج)

fail-closed: العقل معطل → خطأ صادق؛ استجابة فاسدة → خطأ لا مخرجات مختلقة.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import config


def _enable_brain(monkeypatch, base_url, model="test-model"):
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", model)
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", base_url)
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", "ollama")
    monkeypatch.setattr(config, "OLLAMA_API_KEY", None)
    monkeypatch.setattr(config, "OLLAMA_TIMEOUT_SECONDS", 10.0)


def _make_brain_server(content):
    """خادم ollama وهمي: POST /api/chat → {message:{content}}."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            seen.append({"path": self.path, "body": json.loads(body)})
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

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, seen


def test_extract_structured(monkeypatch):
    """الاستخراج المنظّم: نص → JSON بالحقول (حتى داخل سياج كود)."""
    import reasoning_tools
    reply = '{"الاسم": "المشروع السيادي", "الحالة": "قيد التطوير"}'
    server, _ = _make_brain_server(f"```json\n{reply}\n```")
    try:
        _enable_brain(monkeypatch, f"http://127.0.0.1:{server.server_address[1]}")
        out = reasoning_tools.extract(
            "المشروع السيادي قيد التطوير منذ 2026",
            schema="الاسم، الحالة")
        assert out["extraction"]["الاسم"] == "المشروع السيادي"
        assert out["extraction"]["الحالة"] == "قيد التطوير"
        assert out["fields"] == ["الاسم", "الحالة"]
    finally:
        server.shutdown()


def test_extract_malformed_fails_closed(monkeypatch):
    """رد غير JSON → خطأ صادق — لا استخراج مختلق."""
    import reasoning_tools
    server, _ = _make_brain_server("لا أستطيع فهم الطلب")
    try:
        _enable_brain(monkeypatch, f"http://127.0.0.1:{server.server_address[1]}")
        with pytest.raises(RuntimeError, match="فشل الاستخراج"):
            reasoning_tools.extract("نص", schema="حقول")
    finally:
        server.shutdown()


def test_infer(monkeypatch):
    import reasoning_tools
    server, seen = _make_brain_server("- استنتاج أول\n- استنتاج ثانٍ")
    try:
        _enable_brain(monkeypatch, f"http://127.0.0.1:{server.server_address[1]}")
        out = reasoning_tools.infer(["المشروع يتبع دستورًا صارمًا"])
        assert out["conclusions"] == ["استنتاج أول", "استنتاج ثانٍ"]
        body = seen[0]["body"]
        msgs = body["messages"]
        assert any("المشروع يتبع دستورًا" in m["content"] for m in msgs)
    finally:
        server.shutdown()


def test_deduce(monkeypatch):
    import reasoning_tools
    server, _ = _make_brain_server("- فرضية: الدستور يمنع الادعاء بلا دليل")
    try:
        _enable_brain(monkeypatch, f"http://127.0.0.1:{server.server_address[1]}")
        out = reasoning_tools.deduce("سؤال", context="سياق المشروع")
        assert out["hypotheses"][0].startswith("فرضية")
    finally:
        server.shutdown()


def test_verify(monkeypatch):
    import reasoning_tools
    server, _ = _make_brain_server("الحكم: مدعوم — الدليل يذكر ذلك نصًا")
    try:
        _enable_brain(monkeypatch, f"http://127.0.0.1:{server.server_address[1]}")
        out = reasoning_tools.verify("ادعاء الاختبار", evidence="الدليل يذكر ذلك")
        assert "مدعوم" in out["verdict"]
    finally:
        server.shutdown()


def test_reason(monkeypatch):
    import reasoning_tools
    server, _ = _make_brain_server("خطوة 1 ثم خطوة 2. الخلاصة: النتيجة")
    try:
        _enable_brain(monkeypatch, f"http://127.0.0.1:{server.server_address[1]}")
        out = reasoning_tools.reason("سؤال الاختبار", context="سياق")
        assert out["reasoning"].startswith("خطوة")
    finally:
        server.shutdown()


def test_all_fail_honest_when_brain_disabled(monkeypatch):
    """العقل معطل → كل أداة استدلال تعلن السبب بصدق (لا مخرجات مختلقة)."""
    import reasoning_tools
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    monkeypatch.setattr(config, "OLLAMA_MODEL", None)
    for fn, args in (
        (reasoning_tools.extract, ("نص", "حقول")),
        (reasoning_tools.infer, (["وقائع"],)),
        (reasoning_tools.deduce, ("س",)),
        (reasoning_tools.verify, ("ادعاء", "دليل")),
        (reasoning_tools.reason, ("سؤال",)),
    ):
        with pytest.raises(RuntimeError, match="العقل معطل"):
            fn(*args)
