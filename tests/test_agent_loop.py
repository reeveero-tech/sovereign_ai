# -*- coding: utf-8 -*-
"""R-753 (ROADMAP_V5 §٢: ٢.١ + ٢.٢ + ٢.٣ — بأمر المالك 2026-10-25 «أسلمك المشروع»):
حلقة الوكيل العامة: هدف → خطوة → تنفيذ عبر سجل الأدوات فقط → تحقق → استمرار
أو توقف صادق، بميزانيات وإلغاء وأثر إلزامي.

المخطِّط قابل للاستبدال: ScriptedPlanner (حتمي — بديل اختبار معلن، ليس ذكاءً)
وBrainPlanner (العقل الحي عبر ollama_client — معطل بلا ١.٦). هذه الاختبارات
تثبت آلية الحلقة لا ذكاء التخطيط.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


@pytest.fixture
def ledger(monkeypatch):
    """سجل سيادي مزيف يلتقط الأحداث (أو يرفض بنمط R-635 إن fail=True)."""
    import memory.core as core_mod

    class FakeCore:
        def __init__(self):
            self.events = []
            self.fail = False

        def append_event(self, event_type, payload, user=None):
            if self.fail:
                raise RuntimeError("R-635: No active signing key available")
            self.events.append((str(event_type), payload))
            return {}
    fc = FakeCore()
    monkeypatch.setattr(core_mod, "get_core", lambda: fc)
    return fc


def _registry(calls):
    from tool_registry import ToolRegistry, ToolSpec
    r = ToolRegistry()

    def add(a, b):
        calls.append("math.add")
        return {"sum": int(a) + int(b)}

    def boom():
        calls.append("boom")
        raise ConnectionError("upstream down")

    def echo(text):
        calls.append("echo")
        return {"text": text}

    r.register(ToolSpec(name="math.add", description="", inputs={"a": "", "b": ""},
                        outputs="sum", handler=add))
    r.register(ToolSpec(name="boom", description="", inputs={}, outputs="", handler=boom))
    r.register(ToolSpec(name="echo", description="", inputs={"text": ""},
                        outputs="text", handler=echo))
    return r


def _step(tool, inputs=None, check=None):
    return {"action": "call", "tool": tool, "inputs": inputs or {},
            "check": check or {"type": "ok"}}


def _run(steps, ledger, calls=None, **kw):
    from agent_loop import AgentLoop, ScriptedPlanner
    calls = [] if calls is None else calls
    loop = AgentLoop(registry=_registry(calls), planner=ScriptedPlanner(steps), **kw)
    return loop.run("هدف اختبار"), calls


def test_multi_step_goal_completes_with_verified_steps(ledger):
    res, calls = _run([
        _step("math.add", {"a": 2, "b": 3}, {"type": "key_equals", "key": "sum", "value": 5}),
        _step("echo", {"text": "تم"}, {"type": "contains", "key": "text", "value": "تم"}),
        {"action": "finish", "answer": "5"},
    ], ledger)
    assert res["status"] == "completed" and res["answer"] == "5"
    assert calls == ["math.add", "echo"]
    assert [s["verified"] for s in res["steps"]] == [True, True]
    kinds = [e[0] for e in ledger.events]
    assert kinds.count("tool_invoked") == 2           # كل خطوة بأثر
    assert kinds[0] == "agent_run" and kinds[-1] == "agent_run"
    assert ledger.events[-1][1]["phase"] == "finish"


def test_induced_mid_run_failure_stops_honestly(ledger):
    res, calls = _run([
        _step("math.add", {"a": 1, "b": 1}),
        _step("boom"),
        _step("echo", {"text": "لا يجب أن تُنفذ"}),
        {"action": "finish", "answer": "x"},
    ], ledger)
    assert res["status"] == "tool_failed"
    assert res["failed_step"] == 1 and "ConnectionError" in res["error"]
    assert calls == ["math.add", "boom"]              # الخطوة التالية لم تُنفذ
    assert res.get("answer") is None                   # لا ادعاء إنجاز


def test_corrupt_step_detected_and_not_built_upon(ledger):
    """٢.٢: ناتج لا يطابق الشرط يُكتشف ويُعلن ولا تُبنى عليه خطوة تالية."""
    res, calls = _run([
        _step("math.add", {"a": 2, "b": 2}, {"type": "key_equals", "key": "sum", "value": 5}),
        _step("echo", {"text": "بعده"}),
    ], ledger)
    assert res["status"] == "verification_failed" and res["failed_step"] == 0
    assert calls == ["math.add"]
    assert res["steps"][0]["verified"] is False


def test_step_budget_stops_cleanly(ledger):
    res, calls = _run([_step("echo", {"text": str(i)}) for i in range(10)],
                      ledger, max_steps=3)
    assert res["status"] == "budget_exhausted" and res["budget"] == "max_steps"
    assert len(calls) == 3


def test_time_budget_with_injected_clock(ledger):
    t = {"now": 0.0}

    def clock():
        t["now"] += 10.0
        return t["now"]
    res, calls = _run([_step("echo", {"text": str(i)}) for i in range(10)],
                      ledger, max_seconds=25, clock=clock)
    assert res["status"] == "budget_exhausted" and res["budget"] == "max_seconds"
    assert len(calls) < 10


def test_cancel_during_run_stops_loop_and_is_traced(ledger):
    from agent_loop import AgentLoop, ScriptedPlanner, CancelToken
    calls, token = [], CancelToken()
    reg = _registry(calls)
    orig = reg._tools["echo"].handler

    def echo_then_cancel(text):
        out = orig(text)
        if text == "1":
            token.cancel(by="owner")
        return out
    reg._tools["echo"].handler = echo_then_cancel
    loop = AgentLoop(registry=reg, planner=ScriptedPlanner(
        [_step("echo", {"text": str(i)}) for i in range(5)]), cancel=token)
    res = loop.run("هدف")
    assert res["status"] == "cancelled" and calls == ["echo", "echo"]
    assert any(e[0] == "agent_run" and e[1]["phase"] == "cancelled" and
               e[1].get("cancelled_by") == "owner" for e in ledger.events)


def test_unregistered_or_forbidden_tool_is_refused(ledger):
    res, calls = _run([_step("shell.exec", {"cmd": "rm -rf /"})], ledger)
    assert res["status"] == "invalid_step" and calls == []
    res2, calls2 = _run([_step("echo", {"text": "x"})], ledger, allowed_tools=["math.add"])
    assert res2["status"] == "invalid_step" and calls2 == []


def test_agent_cannot_invoke_itself(ledger):
    from agent_loop import AgentLoop, ScriptedPlanner
    from tool_registry import ToolSpec
    calls = []
    reg = _registry(calls)
    reg.register(ToolSpec(name="agent.run", description="", inputs={"goal": ""},
                          outputs="", handler=lambda goal: calls.append("agent.run")))
    res = AgentLoop(registry=reg, planner=ScriptedPlanner(
        [_step("agent.run", {"goal": "loop"})])).run("هدف")
    assert res["status"] == "invalid_step" and calls == []


def test_ledger_unavailable_blocks_before_any_tool(ledger):
    """لا أثر = لا تنفيذ: بلا توقيع لا يبدأ التشغيل ولا تُستدعى أداة."""
    ledger.fail = True
    res, calls = _run([_step("echo", {"text": "x"})], ledger)
    assert res["status"] == "ledger_blocked" and calls == []


def test_planner_exhausted_without_finish_is_not_success(ledger):
    res, _ = _run([_step("echo", {"text": "x"})], ledger)
    assert res["status"] == "planner_failed"


def test_brain_planner_parses_json_and_rejects_garbage(monkeypatch, ledger):
    import agent_loop
    import ollama_client
    replies = iter([
        json.dumps({"action": "call", "tool": "echo", "inputs": {"text": "hi"},
                    "check": {"type": "contains", "key": "text", "value": "hi"}}),
        "```json\n" + json.dumps({"action": "finish", "answer": "hi"}) + "\n```",
    ])
    monkeypatch.setattr(ollama_client, "chat", lambda s, u, timeout=None: next(replies))
    calls = []
    res = agent_loop.AgentLoop(registry=_registry(calls),
                               planner=agent_loop.BrainPlanner()).run("قل hi")
    assert res["status"] == "completed" and res["answer"] == "hi" and calls == ["echo"]

    monkeypatch.setattr(ollama_client, "chat", lambda s, u, timeout=None: "لا أعرف")
    res2 = agent_loop.AgentLoop(registry=_registry([]),
                                planner=agent_loop.BrainPlanner()).run("x")
    assert res2["status"] == "planner_failed"

    monkeypatch.setattr(ollama_client, "chat", lambda s, u, timeout=None: None)
    res3 = agent_loop.AgentLoop(registry=_registry([]),
                                planner=agent_loop.BrainPlanner()).run("x")
    assert res3["status"] == "planner_failed" and "العقل" in res3["error"]


def test_agent_run_tool_registered_and_inventory_moves():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        tools = {t["name"]: t for t in client.get("/tools/list").json()["tools"]}
        assert "agent.run" in tools and "goal" in tools["agent.run"]["inputs"]
        caps = {c["id"]: c for c in client.get("/capabilities").json()["capabilities"]}
        assert caps["agent_loop"]["level"] != "missing"
        assert caps["agent_loop"]["level"] != "enabled" or caps["brain"]["level"] == "enabled"
