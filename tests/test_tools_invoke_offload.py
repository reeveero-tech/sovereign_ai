"""R-764 — /tools/invoke لا يحجب حلقة الأحداث (تمهيد العقل الحي ١.٦).

قبل تفعيل العقل على الإنتاج: أدوات الاستدلال (reason.*) وحلقة الوكيل
(agent.run) والمهام المتينة تستدعي العقل HTTP بمهلة حتى OLLAMA_TIMEOUT_SECONDS.
كان /tools/invoke `async def` ينفّذ الأداة متزامنًا داخل حلقة uvicorn، فأي
استدلال يحجب كل الطلبات — ومنها /health — طوال مدته (صنف حادثة R-762).
الإثبات: أداة بطيئة تُنفَّذ خارج خيط الحلقة، والحلقة تبقى حرّة أثناءها.
"""

import asyncio
import os
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


def test_tools_invoke_runs_tool_off_the_event_loop(monkeypatch):
    import app as app_mod
    import tool_registry

    seen = {}

    class SlowRegistry:
        def invoke(self, name, caller="owner", inputs=None):
            seen["thread"] = threading.get_ident()
            time.sleep(0.6)  # استدلال عقل بطيء (محاكاة)
            return {"tool": name, "ok": True}

    monkeypatch.setattr(tool_registry, "get_registry", lambda: SlowRegistry())
    monkeypatch.setattr(app_mod, "verify_api_key", lambda k: True)
    req = app_mod.ToolInvokeRequest(tool="reason.slow", api_key="k", inputs={})

    async def scenario():
        loop_thread = threading.get_ident()
        ticks = []

        async def heartbeat():  # يمثّل /health أثناء الاستدلال
            for _ in range(5):
                ticks.append(time.monotonic())
                await asyncio.sleep(0.05)

        hb = asyncio.create_task(heartbeat())
        t0 = time.monotonic()
        result = await app_mod.tools_invoke(req)
        await hb
        return loop_thread, ticks, t0, result

    loop_thread, ticks, t0, result = asyncio.run(scenario())
    assert result == {"tool": "reason.slow", "ok": True}
    assert seen["thread"] != loop_thread, "الأداة نُفّذت داخل خيط حلقة الأحداث"
    # الحلقة حرّة: نبضات القلب كلها تمت قبل انتهاء الأداة (0.6 ث)
    assert ticks and ticks[-1] - t0 < 0.5, f"الحلقة حُجبت: آخر نبضة بعد {ticks[-1]-t0:.2f}ث"
