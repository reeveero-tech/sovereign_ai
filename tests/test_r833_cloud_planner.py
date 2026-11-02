# -*- coding: utf-8 -*-
"""R-833: العقل السحابي الاحتياطي مخططًا — الوكلاء لا يموتون بتعذر عقل واحد.

الخلفية: في النشر الحي (Render) العقل الأساسي (Ollama على شبكة المالك
الخاصة) لا تصل إليه السحابة أبدًا — فكانت أداة agent.run تعيد planner_failed
دائمًا (٦٢ أداة مسجلة بلا مخطط)، والمحادثة الوكيلة تُحرم من وضعها الوكيلي.
الربط: CloudPlanner فوق cloud_brain + FallbackPlanner (أساسي ⇒ سحابي) +
احتياط السحابة في نداء محادثة الوكيل نفسه.

هذه الاختبارات تثبت:
1. CloudPlanner: خطوة JSON صحيحة من العقل السحابي، وفشل صادق عند تعطله.
2. FallbackPlanner: الأساسي يتعذر ⇒ السحابي يخطط ويعلن هويته؛ الأساسي يعمل
   ⇒ لا يمس السحابي؛ الاستثناء غير PlannerError يتصاعد (لا حجب خلل).
3. run_goal: الحلقة تكتمل فوق السجل الحقيقي بمخطط سحابي (عقل أساسي معطل).
4. المحادثة الوكيلة: النداء يعود من السحابة حين لا يرد العقل الأساسي.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from agent_loop import (  # noqa: E402
    AgentLoop, BrainPlanner, CloudPlanner, FallbackPlanner, PlannerError,
)


@pytest.fixture
def ledger(monkeypatch):
    """سجل سيادي مزيف — نمط tests/test_agent_loop.py."""
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


def _registry():
    from tool_registry import ToolRegistry, ToolSpec
    r = ToolRegistry()
    r.register(ToolSpec(name="echo", description="يردد النص", inputs={"text": ""},
                       outputs="text", handler=lambda text="x": {"text": text}))
    return r


TOOLS = [{"name": "echo", "description": "يردد النص", "inputs": {"text": ""}}]


class _DeadBrain(BrainPlanner):
    """عقل أساسي متعذر — نمط الإنتاج (LAN خلف شبكة خاصة)."""

    def next_step(self, goal, tools, history, feedback=None):
        raise PlannerError("العقل غير متاح أو غير مفعّل (ROADMAP_V5 ١.٦) — لا تخطيط")


class TestCloudPlanner:
    """مخطط السحابة: نفس عقد BrainPlanner — JSON مقيد وفشل صادق."""

    def test_step_from_cloud_reply(self, monkeypatch):
        """رد السحابة (JSON داخل نص) ⇒ خطوة صحيحة مقيدة بأسماء الأدوات."""
        import cloud_brain
        monkeypatch.setattr(cloud_brain, "enabled", lambda: True)
        monkeypatch.setattr(cloud_brain, "chat",
                            lambda system, user, **kw: 'شرح {"action": "call", "tool": "echo", "inputs": {"text": "سلام"}}')
        step = CloudPlanner().next_step("goal", TOOLS, [])
        assert step["action"] == "call" and step["tool"] == "echo"

    def test_cloud_disabled_honest_failure(self, monkeypatch):
        """السحابة معطلة ⇒ PlannerError صادق لا تظاهر بالتخطيط."""
        import cloud_brain
        monkeypatch.setattr(cloud_brain, "enabled", lambda: False)
        with pytest.raises(PlannerError):
            CloudPlanner().next_step("goal", TOOLS, [])

    def test_cloud_no_reply_honest_failure(self, monkeypatch):
        """السحابة لم ترد (حد معدل/تعطل) ⇒ PlannerError صادق."""
        import cloud_brain
        monkeypatch.setattr(cloud_brain, "enabled", lambda: True)
        monkeypatch.setattr(cloud_brain, "chat", lambda *a, **k: None)
        with pytest.raises(PlannerError):
            CloudPlanner().next_step("goal", TOOLS, [])

    def test_json_mode_reaches_cloud(self, monkeypatch):
        """عقد JSON يصل نداء السحابة (json_mode=True) — لا JSON حر بلا عقد."""
        import cloud_brain
        seen = {}

        def _chat(system, user, **kw):
            seen.update(kw)
            return '{"action": "finish", "answer": "تم"}'

        monkeypatch.setattr(cloud_brain, "enabled", lambda: True)
        monkeypatch.setattr(cloud_brain, "chat", _chat)
        CloudPlanner().next_step("goal", TOOLS, [])
        assert seen.get("json_mode") is True


class TestFallbackPlanner:
    """الأساسي أولًا فإن تعذر فالسحابي — والهوية معلنة لا منتحلة."""

    def test_falls_back_to_cloud_when_primary_dead(self):
        """عقل LAN متعذر ⇒ السحابة تخطط، والهوية kind=cloud صريحة."""
        planner = FallbackPlanner(_DeadBrain(), CloudPlanner())
        # CloudPlanner سيرفع PlannerError (cloud_brain غير مفعل في بيئة الاختبار)
        # — نستبدله بمخطط صريح للسحابة
        class _FakeCloud:
            kind = "cloud"

            def next_step(self, goal, tools, history, feedback=None):
                return {"action": "finish", "answer": "من السحابة"}

        planner = FallbackPlanner(_DeadBrain(), _FakeCloud())
        step = planner.next_step("goal", TOOLS, [])
        assert step["answer"] == "من السحابة"
        assert planner.kind == "cloud"

    def test_primary_wins_when_alive(self):
        """العقل الأساسي حي ⇒ هو المخطط، والسحابة لا تُمس أبدًا."""

        class _AliveBrain:
            kind = "brain"

            def next_step(self, goal, tools, history, feedback=None):
                return {"action": "finish", "answer": "من العقل الأساسي"}

        class _NeverCloud:
            kind = "cloud"

            def next_step(self, *a, **k):  # pragma: no cover — لا يُستدعى أبدًا
                raise AssertionError("السحابة لا تُستدعى والعقل الأساسي حي")

        planner = FallbackPlanner(_AliveBrain(), _NeverCloud())
        step = planner.next_step("goal", TOOLS, [])
        assert step["answer"] == "من العقل الأساسي"
        assert planner.kind == "brain"

    def test_non_planner_error_escalates(self):
        """خلل برمجي في الأساسي (ليس PlannerError) يتصاعد — لا حجب خلل."""
        class _Buggy:
            kind = "brain"

            def next_step(self, goal, tools, history, feedback=None):
                raise TypeError("خلل برمجي")

        planner = FallbackPlanner(_Buggy(), CloudPlanner())
        with pytest.raises(TypeError):
            planner.next_step("goal", TOOLS, [])

    def test_locks_to_active_planner(self):
        """بعد أول قرار يثبت المخطط — لا ارتجاج بين مخططين في جولة واحدة."""
        calls = {"brain": 0, "cloud": 0}

        class _FlakyBrain:
            kind = "brain"

            def next_step(self, goal, tools, history, feedback=None):
                calls["brain"] += 1
                if calls["brain"] == 1:
                    raise PlannerError("تعذر")
                return {"action": "finish", "answer": "brain"}

        class _Cloud:
            kind = "cloud"

            def next_step(self, goal, tools, history, feedback=None):
                calls["cloud"] += 1
                return {"action": "call", "tool": "echo", "inputs": {"text": "1"}}

        planner = FallbackPlanner(_FlakyBrain(), _Cloud())
        s1 = planner.next_step("goal", TOOLS, [])
        assert s1["tool"] == "echo" and planner.kind == "cloud"
        s2 = planner.next_step("goal", TOOLS, [s1])
        # الخطوة الثانية من السحابة (المثبتة) — لا عودة للأساسي المتعذر
        assert s2["tool"] == "echo" and calls["brain"] == 1 and calls["cloud"] == 2


class TestAgentLoopOnCloudPlanner:
    """الحلقة تكتمل فوق السجل الحقيقي بمخطط سحابي — إحياء agent.run في السحابة."""

    def test_run_completes_with_cloud_fallback(self, ledger, monkeypatch):
        """عقل أساسي متعذر + سحابة ترد ⇒ جولة مكتملة بخطوات موقعة الأثر."""
        import cloud_brain
        monkeypatch.setattr(cloud_brain, "enabled", lambda: True)

        def _cloud_chat(system, user, **kw):
            import json
            payload = json.loads(user)
            if not payload.get("history"):
                return json.dumps({"action": "call", "tool": "echo",
                                   "inputs": {"text": "اختبار"}, "check": {"type": "contains", "key": "text", "value": "اختبار"}})
            return json.dumps({"action": "finish", "answer": "اكتمل من نتائج الأدوات"})

        monkeypatch.setattr(cloud_brain, "chat", _cloud_chat)
        planner = FallbackPlanner(_DeadBrain(), CloudPlanner())
        loop = AgentLoop(registry=_registry(), planner=planner, max_steps=4)
        res = loop.run("ردد كلمة اختبار")
        assert res["status"] == "completed"
        assert res["planner"] == "cloud"  # الهوية معلنة لا منتحلة
        assert res["steps"] and res["steps"][0]["tool"] == "echo"
        assert res["steps"][0]["ok"] is True and res["steps"][0]["verified"] is True
        assert res["answer"] == "اكتمل من نتائج الأدوات"
        # الأثر السيادي وقع (بدء + نهاية) — لا تنفيذ بلا أثر
        types = [t for t, _ in ledger.events]
        assert "agent_run" in types


class TestChatAgentCloudFallback:
    """نداء المحادثة: العقل الأساسي لم يرد ⇒ السحابة تجيب — لا موت الوكيل."""

    def test_brain_call_falls_back_to_cloud(self, monkeypatch):
        import chat_agent
        import cloud_brain
        monkeypatch.setattr(cloud_brain, "enabled", lambda: True)
        monkeypatch.setattr(cloud_brain, "chat",
                            lambda system, user, history=None, **kw: "جواب السحابة")
        planner = chat_agent.ChatPlanner(history=[], deadline=None,
                                          chat_fn=lambda *a, **k: None)  # العقل الأساسي لا يرد
        assert planner._call("نظام", "رسالة") == "جواب السحابة"

    def test_cloud_disabled_keeps_honest_failure(self, monkeypatch):
        import chat_agent
        import cloud_brain
        monkeypatch.setattr(cloud_brain, "enabled", lambda: False)
        planner = chat_agent.ChatPlanner(history=[], deadline=None,
                                         chat_fn=lambda *a, **k: None)
        assert planner._call("نظام", "رسالة") is None  # الإعلان الصادق كما كان
