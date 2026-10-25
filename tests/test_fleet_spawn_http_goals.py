# -*- coding: utf-8 -*-
"""R-766 — `fleet.spawn` عبر `/tools/invoke` يفكك النص إلى حروف (كشفه التحضير للإثبات الحي ٥.١).

مدخلات `/tools/invoke` من نوع `Dict[str, str]`، فالأهداف تصل نصًا. كان المعالج
يستدعي `list(goals)` فيصير كل حرف عاملًا: «["أ","ب"]» → ~9 عمال بأهداف من حرف واحد
(تُرسل إلى العقل الحي على الإنتاج). الصحيح: قائمة JSON أو أسطر، وهدف واحد يبقى واحدًا.
"""
import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


@pytest.fixture
def spawn(monkeypatch):
    import app as app_mod
    import fleet

    seen = {}

    class FakeCoordinator:
        def __init__(self, registry, max_concurrency=4):
            seen["cap"] = max_concurrency

        def run(self, parts):
            seen["goals"] = [p["goal"] for p in parts]
            return {"status": "completed", "registered": len(parts)}

    monkeypatch.setattr(fleet, "FleetCoordinator", FakeCoordinator)
    monkeypatch.setattr(app_mod, "verify_api_key", lambda k: True)

    def call(goals, cap="2"):
        req = app_mod.ToolInvokeRequest(tool="fleet.spawn", api_key="k",
                                        inputs={"goals": goals, "max_concurrency": cap})
        out = asyncio.run(app_mod.tools_invoke(req))
        assert out.get("ok") is not False, out
        return seen
    return call


def test_json_list_string_becomes_goals(spawn):
    seen = spawn('["احسب درجة السيادة", "اعرض حالة الذاكرة"]')
    assert seen["goals"] == ["احسب درجة السيادة", "اعرض حالة الذاكرة"]
    assert seen["cap"] == 2


def test_newline_separated_goals(spawn):
    seen = spawn("هدف أول\n\n  هدف ثان  \n")
    assert seen["goals"] == ["هدف أول", "هدف ثان"]


def test_single_goal_is_not_split_into_characters(spawn):
    seen = spawn("اعرض حالة القرص")
    assert seen["goals"] == ["اعرض حالة القرص"]
