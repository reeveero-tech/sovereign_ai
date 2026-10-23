"""خادم MCP وهمي للاختبار (R-738) — JSON-RPC عبر stdin/stdout.

ينفذ الحد الأدنى من عقد MCP: initialize / notifications/initialized /
tools/list / tools/call. أداتان:
- echo  {message: string} → يعيد الرسالة
- count {text: string}  → يعيد عدد الكلمات

يُستخدم عبر: python tests/helpers/fake_mcp_server.py
"""

import json
import sys


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        msg_id = msg.get("id")
        method = msg.get("method", "")

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-mcp", "version": "1.0.0"},
            }
        elif method == "notifications/initialized":
            continue  # إشعار لا يُرد عليه
        elif method == "tools/list":
            result = {"tools": [
                {
                    "name": "echo",
                    "description": "يعيد الرسالة كما هي",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string",
                                        "description": "الرسالة"},
                        },
                        "required": ["message"],
                    },
                },
                {
                    "name": "count",
                    "description": "يعيد عدد كلمات النص",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "النص"},
                        },
                        "required": ["text"],
                    },
                },
            ]}
        elif method == "tools/call":
            params = msg.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "echo":
                result = {"content": [{"type": "text",
                                       "text": args.get("message", "")}]}
            elif name == "count":
                n = len((args.get("text") or "").split())
                result = {"content": [{"type": "text", "text": str(n)}]}
            else:
                result = {"isError": True,
                          "content": [{"type": "text", "text": "أداة مجهولة"}]}
        else:
            if msg_id is None:
                continue
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": "طريقة غير معروفة"},
            }, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        if msg_id is None:
            continue
        sys.stdout.write(json.dumps({
            "jsonrpc": "2.0", "id": msg_id, "result": result,
        }, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
