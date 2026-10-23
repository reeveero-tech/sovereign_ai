"""بوابة MCP — منظومة آلاف الأدوات القياسية بعقد واحد (R-738 — بأمر
المالك «اجمع حتى لو استطعت ألف أداة أو أكثر»).

MCP (Model Context Protocol) معيار الصنامة للاتصال بخوادم الأدوات: بحث،
ملفات، قواعد بيانات، GitHub، بريد، تنفيذ كود... آلاف الخوادم المتاحة
علنًا. البوابة:
- تنقلان: stdio (عملية محلية — JSON-RPC عبر الأسطر) وhttp (JSON-RPC عبر
  POST).
- تكتشف أدوات كل خادم (tools/list) وتسجلها ديناميكيًا في سجل R-729
  باسم `mcp.<خادم>.<أداة>` — كل استدعاء بأثر TOOL_INVOKED كأي أداة.
- معطلة افتراضيًا (MCP_ENABLED) — لا اتصال ضمني أبدًا؛ إعداد الخوادم
  بيد المالك (MCP_SERVERS بصيغة JSON).

فشل خادم واحد لا يُسقط الباقي: يُسجَّل تحذير صادق ويُتخطى (fail-closed
لذلك الخادم فقط).
"""

import json
import subprocess
import threading

import logging

logger = logging.getLogger("sovereign.mcp")

_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "sovereign-ai", "version": "1.0.0"}

# المقابض المفتوحة بعد المزامنة — للإغلاق النظيف
_SYNCED_HANDLES = []


class McpServerHandle:
    """مقبض خادم MCP واحد — نقل stdio أو http."""

    def __init__(self, server_config: dict):
        self.config = dict(server_config or {})
        self.name = str(self.config.get("name") or "mcp").strip()
        self.transport = str(self.config.get("transport") or "stdio").strip().lower()
        self._proc = None
        self._http_url = None
        self._next_id = 0
        self._initialized = False
        if self.transport not in ("stdio", "http"):
            raise ValueError(f"نقل غير مدعوم: {self.transport}")
        if self.transport == "http":
            self._http_url = str(self.config.get("url") or "").strip()
            if not self._http_url:
                raise ValueError("نقل http بلا url")

    # ---------------- JSON-RPC ----------------

    def _send_stdio(self, message: dict):
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _read_stdio_response(self, msg_id):
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("R-738 [MCP %s]: سطر غير JSON — تجاهل",
                               self.name)
                continue
            if msg.get("id") == msg_id:
                return msg
        raise RuntimeError("انقطاع قناة MCP — لا استجابة")

    def _rpc(self, method: str, params=None, notify=False):
        self._next_id += 1
        msg_id = self._next_id
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        if not notify:
            message["id"] = msg_id
        if self.transport == "stdio":
            self._ensure_proc()
            self._send_stdio(message)
            if notify:
                return None
            response = self._read_stdio_response(msg_id)
        else:
            if notify:
                self._http_post(message)
                return None
            response = self._http_post(message)
        if "error" in response:
            raise RuntimeError(
                f"فشل استدعاء MCP: {response['error'].get('message', 'خطأ')}")
        return response.get("result", {})

    def _http_post(self, message: dict):
        import httpx
        headers = {}
        api_key = self.config.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = httpx.post(self._http_url, json=message,
                          headers=headers, timeout=60.0)
        resp.raise_for_status()
        return resp.json()

    def _ensure_proc(self):
        if self._proc is not None:
            return
        command = self.config.get("command")
        if not command:
            raise ValueError("نقل stdio بلا command")
        self._proc = subprocess.Popen(
            [str(command)] + [str(a) for a in (self.config.get("args") or [])],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True,
            env=None, cwd=None)

    def _ensure_initialized(self):
        if self._initialized:
            return
        self._rpc("initialize", {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": _CLIENT_INFO,
        })
        self._rpc("notifications/initialized", notify=True)
        self._initialized = True

    # ---------------- عقد MCP ----------------

    def list_tools(self):
        self._ensure_initialized()
        result = self._rpc("tools/list")
        tools = []
        for t in result.get("tools", []):
            schema = t.get("inputSchema") or {}
            tools.append({
                "name": t.get("name") or "",
                "description": t.get("description") or "",
                "input_schema": schema,
            })
        return tools

    def call_tool(self, name: str, arguments: dict):
        self._ensure_initialized()
        result = self._rpc("tools/call", {"name": name,
                                          "arguments": dict(arguments or {})})
        if result.get("isError"):
            raise RuntimeError("فشل استدعاء أداة MCP — الخطأ معلن من الخادم")
        texts = [c.get("text", "") for c in result.get("content", [])
                 if isinstance(c, dict) and c.get("type") == "text"]
        if not texts:
            raise RuntimeError("فشل استدعاء أداة MCP — لا مخرجات نصية")
        return "\n".join(texts)

    def close(self):
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                # R-738: الإنهاء الودي فشل — قتل قسري صامت مقبول هنا:
                # لا شيء يُستمر بعده (المقبض مغلق) ولا نتائج تُدّعى
                try:
                    self._proc.kill()
                except Exception:
                    # R-738: العملية ماتت أصلًا — لا شيء متبقٍ للإغلاق
                    pass
            self._proc = None


def _parse_servers() -> list:
    import config
    raw = str(config.MCP_SERVERS or "[]").strip()
    try:
        servers = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("R-738 [MCP]: MCP_SERVERS ليس JSON صالحًا — تجاهل")
        return []
    if not isinstance(servers, list):
        logger.warning("R-738 [MCP]: MCP_SERVERS ليس قائمة — تجاهل")
        return []
    return servers


def sync_into_registry(registry) -> list:
    """اكتشاف أدوات كل خادم MCP وتسجيلها في سجل R-729 ديناميكيًا.

    يعيد قائمة أسماء الأدوات المسجلة (mcp.<خادم>.<أداة>). البوابة معطلة
    → لا اتصال ولا تسجيل (لا اتصال ضمني)."""
    import config
    from tool_registry import ToolSpec

    if not config.MCP_ENABLED:
        return []

    registered = []
    for server in _parse_servers():
        try:
            handle = McpServerHandle(server)
            tools = handle.list_tools()
        except Exception as e:
            logger.warning("R-738 [MCP]: فشل خادم (%s) — تخطٍ صادق",
                          type(e).__name__)
            continue
        _SYNCED_HANDLES.append(handle)
        for tool in tools:
            tname = tool["name"]
            if not tname:
                continue
            props = (tool["input_schema"] or {}).get("properties") or {}
            inputs = {str(k): str(v.get("description") or "")
                      for k, v in props.items()}
            def _handler(_h=handle, _t=tname, **kwargs):
                return _h.call_tool(_t, kwargs)

            full = f"mcp.{handle.name}.{tname}"
            registry.register(ToolSpec(
                name=full,
                description=str(tool["description"] or tname)[:200],
                inputs=inputs,
                outputs="مخرجات خادم MCP",
                handler=_handler))
            registered.append(full)
    if registered:
        logger.info("R-738 [MCP]: سُجلت %d أداة من بوابة MCP", len(registered))
    return registered


def shutdown_synced():
    """إغلاق كل المقابض المفتوحة — للاختبارات والإيقاف النظيف."""
    while _SYNCED_HANDLES:
        handle = _SYNCED_HANDLES.pop()
        try:
            handle.close()
        except Exception:
            # R-738: فشل إغلاق مقبض واحد لا يمنع إغلاق البقية — الحالة
            # مُسجلة في سجل الخادم عند اكتشافه
            pass
