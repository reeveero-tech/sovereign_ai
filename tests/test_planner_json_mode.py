"""R-765 — مخطط العقل الحي: وضع JSON مقيَّد + محلّل يقرأ أول كائن.

الحادثة الحية (2026-10-25، بعد R-764): agent.run على الإنتاج بعقل qwen2.5:3b
فشل بـ«رد العقل JSON فاسد: Extra data» بعد 132 ث — النموذج كتب الكائن ثم
استرسل بشرح فيه أقواس أخرى، والمحلّل كان يلتقط من أول { إلى آخر } (جشع)،
والتوليد الطويل غير المقيّد استهلك المهلة. الإصلاح:
1) `_extract_json` يقرأ أول كائن JSON صالح (raw_decode) ويتجاهل ما بعده.
2) `ollama_client.chat(..., json_mode=True, max_tokens=N)`: Ollama `format: json`
   + `options.num_predict`، ومتوافق OpenAI `response_format: json_object`
   + `max_tokens`. المخطط يطلبه؛ بقية المستدعين بلا تغيير.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


def test_extract_first_object_ignores_trailing_prose():
    from agent_loop import _extract_json
    text = ('{"action":"finish","answer":"تم"}\n'
            'شرح: استخدمت {الأداة} لأن النتيجة {واضحة}.')
    assert _extract_json(text) == {"action": "finish", "answer": "تم"}


def test_extract_object_after_leading_prose_and_braces():
    from agent_loop import _extract_json
    text = 'سأفكر {قليلًا} ثم: {"action":"call","tool":"disk.status","inputs":{}} انتهى'
    assert _extract_json(text)["tool"] == "disk.status"


def test_extract_still_rejects_no_object():
    from agent_loop import _extract_json, PlannerError
    with pytest.raises(PlannerError):
        _extract_json("لا يوجد كائن هنا")


class _Capture:
    def __init__(self, content):
        self.content, self.payloads = content, []

    def client_factory(self, protocol):
        cap = self

        class _Resp:
            def raise_for_status(self):
                pass

            def json(self):
                if protocol == "openai":
                    return {"choices": [{"message": {"content": cap.content}}]}
                return {"message": {"content": cap.content}}

        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, json=None, headers=None):
                cap.payloads.append(json)
                return _Resp()

        return _Client


def _brain(monkeypatch, protocol):
    import config
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "m")
    monkeypatch.setattr(config, "OLLAMA_PROTOCOL", protocol)
    monkeypatch.setattr(config, "OLLAMA_BASE_URL", "http://brain.invalid")
    monkeypatch.setattr(config, "OLLAMA_API_KEY", None)


@pytest.mark.parametrize("protocol", ["ollama", "openai"])
def test_brain_planner_requests_constrained_json(monkeypatch, protocol):
    import httpx
    from agent_loop import BrainPlanner
    _brain(monkeypatch, protocol)
    cap = _Capture('{"action":"finish","answer":"ok"}')
    monkeypatch.setattr(httpx, "Client", cap.client_factory(protocol))
    step = BrainPlanner().next_step("هدف", [{"name": "disk.status"}], [])
    assert step == {"action": "finish", "answer": "ok"}
    p = cap.payloads[0]
    if protocol == "ollama":
        fmt = p.get("format")
        assert isinstance(fmt, dict), "Ollama: مخطط JSON مقيِّد لا نص حر"
        assert fmt["properties"]["tool"]["enum"] == ["disk.status"]
        assert fmt["properties"]["action"]["enum"] == ["call", "finish"]
        assert 0 < p.get("options", {}).get("num_predict", 0) <= 1024
    else:
        assert p.get("response_format") == {"type": "json_object"}
        assert 0 < p.get("max_tokens", 0) <= 1024


@pytest.mark.parametrize("protocol", ["ollama", "openai"])
def test_plain_chat_payload_unchanged(monkeypatch, protocol):
    import httpx
    import ollama_client
    _brain(monkeypatch, protocol)
    cap = _Capture("رد")
    monkeypatch.setattr(httpx, "Client", cap.client_factory(protocol))
    assert ollama_client.chat("sys", "hi") == "رد"
    p = cap.payloads[0]
    for k in ("format", "options", "response_format", "max_tokens"):
        assert k not in p, f"{k} must not leak into plain chat"


# ---------------------------------------------------------------------------
# R-765 (ب): تغذية راجعة تصحيحية — الحادثة الحية الثانية: بعد إصلاح JSON
# اخترع qwen2.5:3b اسم أداة («get_current_civil_degree») فتوقفت الحلقة فورًا.
# الحلقات الحقيقية تعيد سبب الرفض للنموذج ليصحح. الضمانات: الخطوة المرفوضة
# لا تُنفَّذ أبدًا، والمحاولات بسقف، والمخطط الحتمي بلا إعادة (سلوكه كما كان).
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_ledger(monkeypatch):
    import memory.core as core_mod

    class FakeCore:
        def __init__(self):
            self.events = []

        def append_event(self, event_type, payload, user=None):
            self.events.append((str(event_type), payload))
            return {}

    fc = FakeCore()
    monkeypatch.setattr(core_mod, "get_core", lambda: fc)
    return fc


def _echo_registry(calls):
    from tool_registry import ToolRegistry, ToolSpec
    r = ToolRegistry()

    def echo(text):
        calls.append("echo")
        return {"text": text}

    r.register(ToolSpec(name="echo", description="", inputs={"text": ""},
                        outputs="text", handler=echo))
    r.register(ToolSpec(name="agent.run", description="", inputs={"goal": ""},
                        outputs="", handler=lambda goal: calls.append("agent.run")))
    return r


class _FeedbackPlanner:
    kind = "brain"
    accepts_feedback = True

    def __init__(self, proposals):
        self.proposals, self.seen_feedback = list(proposals), []

    def next_step(self, goal, tools, history, feedback=None):
        self.seen_feedback.append([dict(f) for f in (feedback or [])])
        return self.proposals.pop(0)


def test_rejected_step_feeds_back_and_planner_corrects(fake_ledger):
    from agent_loop import AgentLoop
    calls = []
    planner = _FeedbackPlanner([
        {"action": "call", "tool": "get_current_civil_degree", "inputs": {}},
        {"action": "call", "tool": "echo", "inputs": {"text": "hi"},
         "check": {"type": "contains", "key": "text", "value": "hi"}},
        {"action": "finish", "answer": "hi"},
    ])
    res = AgentLoop(registry=_echo_registry(calls), planner=planner).run("قل hi")
    assert res["status"] == "completed" and res["answer"] == "hi"
    assert calls == ["echo"], "الخطوة المرفوضة لا تُنفَّذ"
    assert res["rejected_steps"] == 1
    assert "get_current_civil_degree" in planner.seen_feedback[1][0]["error"]


def test_retries_are_bounded_and_forbidden_tool_never_runs(fake_ledger):
    from agent_loop import AgentLoop
    calls = []
    bad = {"action": "call", "tool": "agent.run", "inputs": {"goal": "loop"}}
    planner = _FeedbackPlanner([dict(bad) for _ in range(10)])
    res = AgentLoop(registry=_echo_registry(calls), planner=planner,
                    max_invalid_retries=2).run("هدف")
    assert res["status"] == "invalid_step" and calls == []
    assert res["rejected_steps"] == 2 and len(planner.seen_feedback) == 3


def test_scripted_planner_still_stops_immediately(fake_ledger):
    from agent_loop import AgentLoop, ScriptedPlanner
    calls = []
    res = AgentLoop(registry=_echo_registry(calls), planner=ScriptedPlanner(
        [{"action": "call", "tool": "ghost", "inputs": {}}])).run("هدف")
    assert res["status"] == "invalid_step" and res["rejected_steps"] == 0 and calls == []


def test_brain_planner_sends_tool_names_and_rejections(monkeypatch):
    import json as _json
    import httpx
    from agent_loop import BrainPlanner
    _brain(monkeypatch, "ollama")
    cap = _Capture('{"action":"finish","answer":"ok"}')
    monkeypatch.setattr(httpx, "Client", cap.client_factory("ollama"))
    BrainPlanner().next_step("هدف", [{"name": "disk.status"}], [],
                             feedback=[{"rejected_step": "{}", "error": "أداة غير مسجلة: 'x'"}])
    user = _json.loads(cap.payloads[0]["messages"][-1]["content"])
    assert user["tool_names"] == ["disk.status"]
    assert user["rejected"][0]["error"].startswith("أداة غير مسجلة")


def test_json_mode_without_schema_uses_plain_json(monkeypatch):
    import httpx
    import ollama_client
    _brain(monkeypatch, "ollama")
    cap = _Capture("{}")
    monkeypatch.setattr(httpx, "Client", cap.client_factory("ollama"))
    ollama_client.chat("s", "u", json_mode=True)
    assert cap.payloads[0]["format"] == "json"
