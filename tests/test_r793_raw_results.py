# -*- coding: utf-8 -*-
"""R-793 (٦.٩.٧): المدقق يرى نتائج الأدوات الخام لا الجواب المُصاغ وحده.

حي 2026-10-27: قال الوكيل «22 سجلًا» والحقيقة total_events=152413.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from tool_registry import ToolRegistry, ToolSpec  # noqa: E402


@pytest.fixture
def exp_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_EXPERIENCE_DIR", str(tmp_path / "exp"))
    return tmp_path


def _reg():
    r = ToolRegistry()
    r.register(ToolSpec(name="memory.stats", description="x", inputs={}, outputs="",
                        handler=lambda: {}))
    return r


def test_digest_result_keeps_values_and_truncates():
    import fleet
    assert json.loads(fleet.digest_result({"total_events": 152413}))["total_events"] == 152413
    long = fleet.digest_result({"k": "x" * 5000})
    assert len(long) <= fleet.RAW_RESULT_CHARS + 1 and long.endswith("…")
    assert fleet.digest_result(object())  # غير قابل للتسلسل لا يرمي


def test_verifier_receives_raw_results_and_prompt_rule(exp_dir):
    import goals
    seen = []

    class Mgr:
        def run(self, task):
            return {"status": "completed", "answer": "عدد السجلات 22", "agents_created": 1,
                    "run_id": "m", "tools_used": ["memory.stats"],
                    "raw_results": [{"tool": "memory.stats",
                                     "result": json.dumps({"total_events": 152413})}]}

    def brain(system, user, **kw):
        seen.append((system, user))
        if "مدقق صارم" in system:  # يعمل كمدقق يقارن: الجواب يناقض الخام
            ok = "22" in user and "152413" not in user
            return json.dumps({"achieved": ok, "missing": "الجواب يناقض الخام"}, ensure_ascii=False)
        if "ضع خطة" in system:
            return '{"plan":[]}'
        return json.dumps({"decision": "work", "task": "memory.stats"}, ensure_ascii=False)

    eng = goals.GoalEngine(_reg(), chat_fn=brain, manager_factory=lambda t: Mgr())
    gid = eng.goals.add("اعرف عدد أحداث ذاكرتك")["id"]
    out = eng.work(gid)
    sys_prompt, user = [x for x in seen if "مدقق صارم" in x[0]][-1]
    assert "tool_results" in sys_prompt and "152413" in user
    assert out["check"]["achieved"] is False  # المدقق رأى الخام فرفض «22»
    run = eng.goals.state()[gid]["runs"][-1]
    assert run["raw_results"][0]["tool"] == "memory.stats"


def test_runs_without_raw_results_behave_as_before(exp_dir):
    import goals

    class Mgr:
        def run(self, task):
            return {"status": "completed", "answer": "ok", "agents_created": 1, "run_id": "m",
                    "tools_used": []}

    def brain(system, user, **kw):
        if "مدقق صارم" in system:
            assert "tool_results" not in user
            return '{"achieved": true, "summary": "تم"}'
        if "ضع خطة" in system:
            return '{"plan":[]}'
        return '{"decision": "work", "task": "t"}'

    eng = goals.GoalEngine(_reg(), chat_fn=brain, manager_factory=lambda t: Mgr())
    gid = eng.goals.add("هدف")["id"]
    assert eng.work(gid)["check"]["achieved"] is True
