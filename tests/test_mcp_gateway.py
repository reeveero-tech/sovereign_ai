"""R-738 (بأمر المالك — «ألف أداة أو أكثر»): بوابة MCP — منظمومة آلاف الأدوات
بعقد واحد.

MCP (Model Context Protocol) هو معيار الصناعة الذي تتصل به آلاف خوادم
الأدوات (بحث، ملفات، قواعد بيانات، GitHub، بريد...). البوابة:
- تكتشف أدوات كل خادم (tools/list) وتسجلها في سجل R-729 ديناميكيًا
  باسم `mcp.<خادم>.<أداة>` — كل استدعاء بأثر TOOL_INVOKED.
- نقلان: stdio (عملية محلية) وhttp (خادم بعيد — JSON-RPC عبر POST).
- معطلة افتراضيًا (MCP_ENABLED) — لا اتصال ضمني أبدًا (المادة الدستورية).
"""

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import config

REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER = REPO_ROOT / "tests" / "helpers" / "fake_mcp_server.py"


def _enable_mcp(monkeypatch, servers):
    monkeypatch.setattr(config, "MCP_ENABLED", True)
    monkeypatch.setattr(config, "MCP_SERVERS", json.dumps(servers))


# ======================== النقل stdio ========================

def test_stdio_list_and_call(monkeypatch):
    import mcp_gateway
    _enable_mcp(monkeypatch, [{
        "name": "fake", "transport": "stdio",
        "command": "python3", "args": [str(HELPER)],
    }])
    client = mcp_gateway.McpServerHandle(
        {"name": "fake", "transport": "stdio",
         "command": "python3", "args": [str(HELPER)]})
    try:
        tools = client.list_tools()
        names = {t["name"] for t in tools}
        assert names == {"echo", "count"}
        assert tools[0]["input_schema"]["required"] == ["message"]
        out = client.call_tool("echo", {"message": "مرحبا"})
        assert out == "مرحبا"
        out2 = client.call_tool("count", {"text": "واحد اثنان ثلاثة"})
        assert out2 == "3"
    finally:
        client.close()


def test_stdio_unknown_tool_is_error(monkeypatch):
    import mcp_gateway
    client = mcp_gateway.McpServerHandle(
        {"name": "fake", "transport": "stdio",
         "command": "python3", "args": [str(HELPER)]})
    try:
        with pytest.raises(RuntimeError, match="فشل استدعاء"):
            client.call_tool("bogus", {})
    finally:
        client.close()


# ======================== النقل http ========================

def _make_http_mcp_server():
    """خادم MCP عبر HTTP: POST بجسد JSON-RPC — استجابة JSON-RPC واحدة."""
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            msg = json.loads(self.rfile.read(length))
            calls.append(msg)
            method = msg.get("method", "")
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05",
                          "capabilities": {"tools": {}},
                          "serverInfo": {"name": "http-fake", "version": "1"}}
            elif method == "tools/list":
                result = {"tools": [{
                    "name": "echo",
                    "description": "يعيد الرسالة",
                    "inputSchema": {"type": "object", "properties": {
                        "message": {"type": "string"}},
                        "required": ["message"]}}]}
            elif method == "tools/call":
                args = msg["params"].get("arguments", {})
                result = {"content": [{"type": "text",
                                       "text": args.get("message", "")}]}
            else:
                result = {}
            data = json.dumps({"jsonrpc": "2.0", "id": msg.get("id"),
                               "result": result}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, calls


def test_http_list_and_call(monkeypatch):
    import mcp_gateway
    server, _ = _make_http_mcp_server()
    try:
        client = mcp_gateway.McpServerHandle({
            "name": "remote", "transport": "http",
            "url": f"http://127.0.0.1:{server.server_address[1]}/mcp"})
        tools = client.list_tools()
        assert [t["name"] for t in tools] == ["echo"]
        assert client.call_tool("echo", {"message": "عن بُعد"}) == "عن بُعد"
    finally:
        server.shutdown()


# ======================== المزامنة مع السجل ========================

def test_sync_registers_mcp_tools_into_registry(monkeypatch):
    """الاكتشاف الديناميكي: أدوات MCP تُسجل كـ mcp.<خادم>.<أداة> — والاستدعاء
    عبر السجل يترك أثرًا سياديًا (نمط R-729)."""
    import mcp_gateway
    from tool_registry import ToolRegistry
    _enable_mcp(monkeypatch, [{
        "name": "fake", "transport": "stdio",
        "command": "python3", "args": [str(HELPER)],
    }])
    reg = ToolRegistry()
    registered = mcp_gateway.sync_into_registry(reg)
    try:
        assert "mcp.fake.echo" in registered
        assert "mcp.fake.count" in registered
        result = reg.invoke("mcp.fake.echo", caller="owner",
                            inputs={"message": "أثر سيادي"})
        assert result["ok"] is True
        assert result["result"] == "أثر سيادي"
        # المدخلات المعلنة من inputSchema
        spec = reg._tools["mcp.fake.echo"]
        assert "message" in spec.inputs
    finally:
        mcp_gateway.shutdown_synced()


def test_disabled_makes_no_connection(monkeypatch):
    """البوابة معطلة → لا اتصال ولا تسجيل (لا اتصال ضمني)."""
    import mcp_gateway
    from tool_registry import ToolRegistry
    monkeypatch.setattr(config, "MCP_ENABLED", False)
    monkeypatch.setattr(config, "MCP_SERVERS", json.dumps([{
        "name": "fake", "transport": "stdio",
        "command": "python3", "args": [str(HELPER)]}]))
    reg = ToolRegistry()
    registered = mcp_gateway.sync_into_registry(reg)
    assert registered == []
