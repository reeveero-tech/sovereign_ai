# -*- coding: utf-8 -*-
"""R-755 (علة مكتشفة أثناء R-754 — V5 §٤ بوابة الأدوات): مزامنة MCP عند إقلاع
التطبيق لم تعمل قط منذ R-738.

`backend/app.py` يستدعي `mcp_gateway.sync_into_registry(get_registry())` في
نطاق الوحدة، و`get_registry` لم يُستورد إلا داخل دوال — فكان NameError يُبتلع
بتحذير، ولا تُسجل أي أداة MCP عند الإقلاع حتى لو فعّلها المالك. اختبارات
البوابة نجحت لأنها تستدعي المزامنة مباشرة لا عبر الإقلاع.
الحارس: إقلاع حقيقي في عملية منفصلة بـMCP مفعّل → أدوات mcp.fake.* في السجل.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER = REPO_ROOT / "tests" / "helpers" / "fake_mcp_server.py"

SCRIPT = """
import json, sys
sys.path.insert(0, 'backend')
import app
from tool_registry import get_registry
names = sorted(t['name'] for t in get_registry().list_tools())
print(json.dumps([n for n in names if n.startswith('mcp.')]))
import mcp_gateway
mcp_gateway.shutdown_synced()
"""


def test_app_boot_registers_mcp_tools_when_enabled():
    env = dict(os.environ, MCP_ENABLED="true", MCP_SERVERS=json.dumps([{
        "name": "fake", "transport": "stdio",
        "command": sys.executable, "args": [str(HELPER)]}]))
    out = subprocess.run([sys.executable, "-c", SCRIPT], cwd=str(REPO_ROOT), env=env,
                         capture_output=True, text=True, timeout=90)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "تعذر تسجيل أدوات MCP" not in out.stderr
    mcp = json.loads(out.stdout.strip().splitlines()[-1])
    assert "mcp.fake.echo" in mcp and "mcp.fake.count" in mcp


def test_app_boot_without_mcp_registers_none():
    env = dict(os.environ, MCP_ENABLED="false")
    out = subprocess.run([sys.executable, "-c", SCRIPT], cwd=str(REPO_ROOT), env=env,
                         capture_output=True, text=True, timeout=90)
    assert out.returncode == 0, out.stderr[-2000:]
    assert json.loads(out.stdout.strip().splitlines()[-1]) == []
    assert "تعذر تسجيل أدوات MCP" not in out.stderr
