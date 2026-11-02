"""R-838.3: ميزانية حية تتسع حين يفتح مزلاج العقل داخل الجولة — لا استسلام.

الدافع (لوحة مراقبة إنتاج 2026-11-03 00:02): «قم بتحليل المشروع واستكشافه
واعطني عنه تحليل مفصل https://github.com/chatboxai قم بتحليل كل مستودعات هذا
الرابط» — نفذ الوكيل web.fetch وweb.fetch وweb.search (لا github.repo) ثم
budget_exhausted بعد 174ث ولم يُكمل الجواب بصدق.

جذران:
- الميزانية كانت تُقاس مرة واحدة قبل الجولة: أول فشل للعقل الأساسي داخلها
  يفتح مزلاج R-821 بعد القياس، فيخطط السحابي (~45ث للنداء لحد المعدل)
  بميزانية 150ث فتنفد قبل الجواب.
- وصف أداة github.repo يُقتطع أمام الموجّه عند 140 حرفًا، فذِكر سرد حسابات
  GitHub (R-838.2) كان يقع بعد الاقتطاع — لا يراه العقل فيختار web.fetch.

المثبت هنا (لا شبكة — عقل بديل وساعة محقونة):
- AgentLoop بميزانية حية (max_seconds_fn) تكمل الجولة بعد توسعتها منتصفها.
- respond() يبني الميزانية الحية: تفتح المزلاج أثناء الجولة ⇒ تتسع فورًا
  وتظل لاصقة لا تنكمش إن أُغلق المزلاج لاحقًا.
- المسار السحابي البحت (العقل الأساسي معطل إعداديًا) يتوسع ابتداءً.
- وصف github.repo يُظهر سرد الحسابات داخل أول 140 حرفًا التي يراها الموجّه.
"""

import json
import time

import pytest


class FakeRegistry:
    def __init__(self):
        self.calls = []

    def list_tools(self):
        return [{"name": "web.fetch", "description": "قراءة أي رابط", "inputs": {"url": "u"},
                 "permission": "owner"},
                {"name": "github.repo", "description": "قراءة مستودع", "inputs": {"url": "u"},
                 "permission": "owner"}]

    def invoke(self, name, caller="chat", inputs=None):
        self.calls.append(name)
        return {"ok": True, "result": "بيانات", "error": None,
                "trace": {"result_fingerprint": "f"}}


class FakeBrain:
    """عقل بديل يعيد قرارات متتالية — كما في اختبارات R-789."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def __call__(self, system, user, **kw):
        self.seen.append(kw)
        if not self.replies:
            return None
        r = self.replies.pop(0)
        return r if (r is None or isinstance(r, str)) else json.dumps(r, ensure_ascii=False)


class SlowCloudPlanner:
    """مخطط مفتوح: كل قراءته للأدوات يحاكي نداء سحابيًا بطيئًا (الساعة المحقونة)."""

    def __init__(self):
        self.kind = "fake"
        self.accepts_feedback = False
        self.calls = 0

    def next_step(self, goal, tools, steps):
        self.calls += 1
        if self.calls == 1:
            return {"action": "call", "tool": "web.fetch", "inputs": {"url": "https://x"}}
        return {"action": "finish", "answer": "تم بعدها"}


def test_agent_loop_live_budget_completes_after_midrun_growth():
    """الجولة تكتمل بعد توسعة الميزانية منتصفها — بدونها تُستنفد بصدق (القديم)."""
    from agent_loop import AgentLoop

    # ساعة محقونة: كل قراءة تُقدّم الزمن 30ث — النداء السحابي البطيء محاكىً
    state = {"t": 0.0}

    def clock():
        state["t"] += 30.0
        return state["t"]

    # (١) القديم: ميزانية ثابتة 50 ⇒ الخطوة الثانية (60 > 50) تُستنفد بصدق
    res_old = AgentLoop(FakeRegistry(), SlowCloudPlanner(), max_steps=4,
                        max_seconds=50.0, clock=clock).run("هدف")
    assert res_old["status"] == "budget_exhausted"
    assert res_old["steps"]  # أداة نُفذت فعلًا قبل الاستنفاد

    # (٢) R-838.3: ميزانية حية — تتسع فور نجاح أول أداة (كأن المزلاج افتتح)
    reg = FakeRegistry()
    tool_ran = {"done": False}
    _invoke = reg.invoke

    def invoke(name, *a, **kw):
        out = _invoke(name, *a, **kw)
        tool_ran["done"] = True
        return out

    reg.invoke = invoke
    live = {"seconds": 50.0}
    state["t"] = 0.0

    def budget_fn():
        if tool_ran["done"]:  # المزلاج افتتح أثناء الجولة (بعد أول نتيجة)
            live["seconds"] = 300.0
        return live["seconds"]

    loop = AgentLoop(reg, SlowCloudPlanner(), max_steps=4,
                     max_seconds=50.0, clock=clock, max_seconds_fn=budget_fn)
    res = loop.run("هدف")
    assert res["status"] == "completed" and res["answer"] == "تم بعدها"


def test_respond_builds_live_budget_growing_with_latch(monkeypatch):
    """جذر علة الإنتاج: المزلاج مغلق عند القياس ويفتح داخل الجولة ⇒ تتسع الميزانية."""
    import agent_loop
    import chat_agent

    real_loop = agent_loop.AgentLoop
    captured = {}

    class RecordingLoop(real_loop):
        def __init__(self, registry, planner, **kw):
            captured.update(kw)
            super().__init__(registry, planner, **kw)

    monkeypatch.setattr(agent_loop, "AgentLoop", RecordingLoop)
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)

    import ollama_client
    latch = {"open": False}  # مغلق عند بدء الجولة — يفتح أثناءها (علة الإنتاج)
    monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda: latch["open"])

    out = chat_agent.respond("مرحبا", registry=FakeRegistry(),
                             chat_fn=FakeBrain([{"tool": "none", "inputs": {}}, "سلام"]))
    assert out["status"] == "completed"
    budget_fn = captured["max_seconds_fn"]
    assert budget_fn is not None and callable(budget_fn)
    # قبل فتح المزلاج: الميزانية الأصلية 150ث كما كانت
    assert budget_fn() == pytest.approx(150.0)
    # المزلاج يفتح أثناء الجولة (أول فشل للعقل الأساسي) ⇒ التوسعة فورية
    latch["open"] = True
    assert budget_fn() == pytest.approx(75.0 * chat_agent.MAX_STEPS)  # 300ث
    # التوسعة لاصقة: إغلاق المزلاج لاحقًا لا ينكمشها — الجولة أخذت نَفَسها
    latch["open"] = False
    assert budget_fn() == pytest.approx(300.0)


def test_cloud_only_round_expands_budget_upfront(monkeypatch):
    """العقل الأساسي معطل إعداديًا والسحابي هو المخطط ⇒ توسعة ابتدائية لا انتظار مزلاج."""
    import agent_loop
    import chat_agent

    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: False)
    import cloud_brain
    monkeypatch.setattr(cloud_brain, "enabled", lambda: True)

    def fake_cloud_chat(system, user, history=None, max_tokens=1400, json_mode=False):
        if json_mode:
            return '{"tool": "none", "inputs": {}}'
        return "جواب السحابة"

    monkeypatch.setattr(cloud_brain, "chat", fake_cloud_chat)

    real_loop = agent_loop.AgentLoop
    captured = {}

    class RecordingLoop(real_loop):
        def __init__(self, registry, planner, **kw):
            captured.update(kw)
            super().__init__(registry, planner, **kw)

    monkeypatch.setattr(agent_loop, "AgentLoop", RecordingLoop)

    out = chat_agent.respond("مرحبا", registry=FakeRegistry())  # بلا chat_fn — مسار الإنتاج
    assert out["status"] == "completed" and out["reply"] == "جواب السحابة"
    assert captured["max_seconds_fn"]() == pytest.approx(75.0 * chat_agent.MAX_STEPS)


def test_planner_accepts_callable_deadline():
    """ChatPlanner يقبل موعدًا حيًا (استدعاء) كما قبل floatًا — بلا انكسار للقديم."""
    import chat_agent

    seen = {}

    def chat_fn(system, user, **kw):
        seen.update(kw)
        return '{"tool": "none", "inputs": {}}'

    # حي: يُقرأ عند النداء (المستهلك المباشر للموعد هو _call)
    planner = chat_agent.ChatPlanner(deadline=lambda: time.monotonic() + 100, chat_fn=chat_fn)
    planner._call("س", "ص")
    assert 90.0 <= seen["timeout"] <= 100.5

    # ثابت كما كان: بلا انكسار للسلوك القديم
    seen.clear()
    planner2 = chat_agent.ChatPlanner(deadline=time.monotonic() + 100, chat_fn=chat_fn)
    planner2._call("س", "ص")
    assert 90.0 <= seen["timeout"] <= 100.5


def test_github_repo_description_shows_account_capability_to_router():
    """جذر اختيار web.fetch: أول 140 حرفًا التي يراها الموجّه تعلن سرد الحسابات."""
    import app  # noqa: F401 — الاستيراد يسجل الأدوات الحقيقية
    from tool_registry import get_registry

    spec = next(t for t in get_registry().list_tools() if t["name"] == "github.repo")
    visible = spec["description"][:140]  # اقتطاع الموجّه في agent_loop._tools
    assert "حساب" in visible and "مستودعاته" in visible, visible
    # وتعليمات النظام للمحادثة تعلنها أيضًا
    import chat_agent
    assert "تُسرد كل مستودعاتها" in chat_agent._CHAT_SYSTEM
