# -*- coding: utf-8 -*-
"""R-790: الخبرة والمعرفة المكتسبة (٦.٩.١/٦.٩.٥) + المدير ينشئ الوكلاء بنفسه (٦.٩.٢)."""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import experience  # noqa: E402
from tool_registry import ToolRegistry, ToolSpec  # noqa: E402


@pytest.fixture
def exp_dir(tmp_path, monkeypatch):
    d = tmp_path / "experience"
    monkeypatch.setenv("SOVEREIGN_EXPERIENCE_DIR", str(d))
    return d


# ------------------------------------------------------------------ الخبرة
def test_record_and_recall_similar_goal(exp_dir):
    s = experience.get_store()
    s.record(source="chat", goal="كم حدثا في ذاكرتك الآن؟", status="completed",
             tools=["memory.stats"], steps=[{"tool": "memory.stats", "ok": True, "inputs": {}}])
    s.record(source="chat", goal="اكتب قصيدة عن البحر", status="completed", tools=[])
    got = s.recall("كم عدد الأحداث في الذاكرة")
    assert got and got[0]["tools"] == ["memory.stats"]
    assert all("البحر" not in (g["goal"] or "") for g in got)


def test_memory_survives_new_instance_and_is_append_only(exp_dir):
    """المادة ٨: الذاكرة لا تُفقد — نسخة جديدة (إعادة تشغيل) ترى كل ما سُجل."""
    a = experience.ExperienceStore(str(exp_dir))
    for i in range(5):
        a.record(source="chat", goal=f"هدف رقم {i}", status="completed")
    size_before = (exp_dir / "experience.jsonl").stat().st_size
    b = experience.ExperienceStore(str(exp_dir))
    assert b.stats()["experiences"] == 5
    b.record(source="chat", goal="هدف سادس", status="tool_failed", error="انقطاع")
    assert (exp_dir / "experience.jsonl").stat().st_size > size_before
    assert experience.ExperienceStore(str(exp_dir)).stats()["experiences"] == 6
    assert b.verify_chain()["intact"] is True


def test_corrupt_line_counted_never_drops_others(exp_dir):
    s = experience.ExperienceStore(str(exp_dir))
    s.record(source="chat", goal="أول", status="completed")
    with open(exp_dir / "experience.jsonl", "a", encoding="utf-8") as fh:
        fh.write("{نصف سطر تالف\n")
    s2 = experience.ExperienceStore(str(exp_dir))
    s2.record(source="chat", goal="ثالث", status="completed")
    st = s2.stats()
    assert st["experiences"] == 2 and st["corrupt_lines"] == {"experience": 1}
    assert "{نصف سطر تالف" in (exp_dir / "experience.jsonl").read_text(encoding="utf-8")


def test_chain_detects_tamper(exp_dir):
    s = experience.ExperienceStore(str(exp_dir))
    s.record(source="chat", goal="أ", status="completed")
    s.record(source="chat", goal="ب", status="completed")
    p = exp_dir / "experience.jsonl"
    lines = p.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0]); row["status"] = "forged"
    lines[0] = json.dumps(row, ensure_ascii=False)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert experience.ExperienceStore(str(exp_dir)).verify_chain()["intact"] is False


def test_tool_stats_from_real_steps(exp_dir):
    s = experience.get_store()
    s.record(source="w", goal="x", status="tool_failed",
             steps=[{"tool": "web.fetch", "ok": False, "error": "timeout"}])
    s.record(source="w", goal="y", status="completed",
             steps=[{"tool": "web.fetch", "ok": True}])
    st = s.tool_stats()["web.fetch"]
    assert st["calls"] == 2 and st["success_rate"] == 0.5 and st["last_error"] == "timeout"


def test_inputs_values_not_stored_only_keys(exp_dir):
    s = experience.get_store()
    s.record(source="chat", goal="g", status="completed",
             steps=[{"tool": "t", "ok": True, "inputs": {"api_key": "SECRET-123"}}])
    txt = (exp_dir / "experience.jsonl").read_text(encoding="utf-8")
    assert "SECRET-123" not in txt and "api_key" in txt


def test_knowledge_remember_recall_dedupe(exp_dir):
    s = experience.get_store()
    s.remember("مستودع sovereign_ai مكتوب بلغة Python", "https://github.com/reeveero-tech/sovereign_ai")
    again = s.remember("مستودع sovereign_ai مكتوب بلغة Python", "x")
    assert again.get("duplicate") is True
    got = s.recall_facts("بأي لغة كتب مستودع sovereign_ai")
    assert got and "Python" in got[0]["fact"] and got[0]["source"].startswith("https://")
    with pytest.raises(ValueError):
        s.remember("  ")


def test_lessons_text_contains_real_facts_only(exp_dir):
    experience.get_store().record(source="chat", goal="هل القرص ممتلئ", status="tool_failed",
                                  tools=["disk.status"], error="Permission denied")
    txt = experience.lessons_text("هل القرص ممتلئ الآن")
    assert "disk.status" in txt and "Permission denied" in txt and "tool_failed" in txt


# ------------------------------------------------------------------ المدير
def _registry(calls):
    r = ToolRegistry()

    def mem():
        calls.append("memory.stats")
        return {"total_events": 146186}

    def disk():
        calls.append("disk.status")
        return {"used_pct": 41}
    r.register(ToolSpec(name="memory.stats", description="إحصاء الذاكرة", inputs={},
                        outputs="total_events", handler=mem))
    r.register(ToolSpec(name="disk.status", description="حالة القرص", inputs={},
                        outputs="used_pct", handler=disk))
    r.register(ToolSpec(name="agent.manage", description="مدير", inputs={"goal": ""},
                        outputs="", handler=lambda goal: {}))
    return r


class FakeBrain:
    """عقل وهمي حتمي للاختبار: يرد بحسب المرحلة (تخطيط/توجيه/جواب/تجميع)."""

    def __init__(self, plan):
        self.plan = plan
        self.systems = []

    def __call__(self, system, user, **kw):
        self.systems.append(system)
        if "مدير وكلاء" in system:
            return json.dumps(self.plan, ensure_ascii=False)
        if "موجّه" in system:
            payload = json.loads(user)
            if payload.get("gathered_results"):
                return '{"tool":"none","inputs":{}}'
            msg = payload.get("message", "")
            tool = "memory.stats" if "ذاكرة" in msg else "disk.status"
            return json.dumps({"tool": tool, "inputs": {}})
        if "وكلاؤك" in system:
            agents = json.loads(user)["agents"]
            return "تجميع: " + " | ".join(str(a.get("answer")) for a in agents)
        payload = json.loads(user)
        return "نتيجة: " + payload["tool_results"][0]["result"]


def test_manager_creates_agents_itself_and_synthesizes(exp_dir):
    import manager
    calls = []
    reg = _registry(calls)
    brain = FakeBrain({"subtasks": [{"role": "ذاكرة", "goal": "اعرف عدد أحداث الذاكرة"},
                                    {"role": "قرص", "goal": "اعرف حالة القرص"}],
                       "reason": "جزآن مستقلان"})
    rep = manager.AgentManager(reg, chat_fn=brain, max_concurrency=2).run(
        "أعطني تقريرًا عن الذاكرة والقرص")
    assert rep["status"] == "completed", rep
    assert rep["agents_created"] == 2
    assert sorted(calls) == ["disk.status", "memory.stats"]
    assert "146186" in rep["answer"] and "41" in rep["answer"]
    st = experience.get_store().stats()
    assert st["by_source"].get("manager") == 1 and st["by_source"].get("worker") == 2


def test_worker_never_gets_manager_tools(exp_dir):
    import manager
    reg = _registry([])
    m = manager.AgentManager(reg, chat_fn=FakeBrain({"subtasks": []}))
    assert "agent.manage" not in m.worker_tools()
    assert set(m.worker_tools()) == {"memory.stats", "disk.status"}


def test_manager_plan_failure_is_honest(exp_dir):
    import manager
    rep = manager.AgentManager(_registry([]), chat_fn=lambda *a, **k: None).run("هدف")
    assert rep["status"] == "planner_failed" and rep["answer"] is None
    assert experience.get_store().stats()["by_status"].get("planner_failed") == 1


def test_manager_caps_agents_and_dedupes_roles(exp_dir):
    import manager
    plan = {"subtasks": [{"role": "a", "goal": f"اعرف حالة القرص {i}"} for i in range(9)]}
    m = manager.AgentManager(_registry([]), chat_fn=FakeBrain(plan), max_agents=3)
    out = m.plan("x", m.worker_tools())
    roles = [p["role"] for p in out["subtasks"]]
    assert len(roles) == 3 and len(set(roles)) == 3


def test_manager_learns_from_previous_run(exp_dir):
    """التخطيط التالي يرى وقائع التشغيل السابق — اكتساب خبرة فعلي."""
    import manager
    experience.get_store().record(source="manager", goal="تقرير عن الذاكرة والقرص",
                                  status="failed", tools=["disk.status"], error="disk timeout")
    brain = FakeBrain({"subtasks": [{"role": "ذاكرة", "goal": "اعرف عدد أحداث الذاكرة"}]})
    manager.AgentManager(_registry([]), chat_fn=brain).run("تقرير عن الذاكرة والقرص")
    plan_sys = [s for s in brain.systems if "مدير وكلاء" in s][0]
    assert "disk timeout" in plan_sys and "تجارب سابقة" in plan_sys


def test_manager_partial_when_one_agent_fails(exp_dir):
    import manager
    r = _registry([])
    r.register(ToolSpec(name="web.fetch", description="جلب", inputs={"url": ""}, outputs="",
                        handler=lambda url="": (_ for _ in ()).throw(RuntimeError("offline"))))

    class B(FakeBrain):
        def __call__(self, system, user, **kw):
            if "موجّه" in system and "الويب" in json.loads(user).get("message", "") \
                    and not json.loads(user).get("gathered_results"):
                return '{"tool":"web.fetch","inputs":{"url":"https://example.com"}}'
            return super().__call__(system, user, **kw)
    plan = {"subtasks": [{"role": "ذاكرة", "goal": "اعرف عدد أحداث الذاكرة"},
                         {"role": "ويب", "goal": "اقرأ صفحة الويب"}]}
    rep = manager.AgentManager(r, chat_fn=B(plan)).run("مهمة مركبة")
    assert rep["status"] == "partial"
    assert {a["role"]: a["status"] for a in rep["agents"]}["ويب"] == "tool_failed"


def test_chat_router_receives_lessons(exp_dir):
    import chat_agent
    experience.get_store().record(source="chat", goal="كم حدثا في ذاكرتك", status="completed",
                                  tools=["memory.stats"])
    seen = []

    def brain(system, user, **kw):
        seen.append(system)
        if "موجّه" in system:
            return '{"tool":"none","inputs":{}}'
        return "جواب"
    reg = _registry([])
    chat_agent.respond("كم حدثا في ذاكرتك الآن", registry=reg, chat_fn=brain)
    assert "memory.stats" in [s for s in seen if "موجّه" in s][0]
    assert experience.get_store().stats()["by_source"].get("chat") == 2


def test_app_registers_manager_and_experience_tools():
    import app  # noqa: F401
    from tool_registry import get_registry
    names = {t["name"] for t in get_registry().list_tools()}
    assert {"agent.manage", "experience.stats", "experience.recall",
            "knowledge.remember", "knowledge.recall"} <= names
    import chat_agent
    assert "agent.manage" not in chat_agent.CHAT_READ_TOOLS
    assert "knowledge.remember" not in chat_agent.CHAT_READ_TOOLS
    assert "experience.stats" in chat_agent.CHAT_READ_TOOLS


# ------------------------------------------------------------------ الأهداف والاستقلال (R-791)
class _FakeManager:
    def __init__(self, calls):
        self.calls = calls

    def run(self, task):
        self.calls.append(task)
        return {"status": "completed", "answer": f"أُنجز: {task}", "agents_created": 1,
                "run_id": "m1"}


def _goal_brain(decisions, reflect=None, checks=None):
    seq = list(decisions)
    chk = list(checks or [])
    seen = []

    def brain(system, user, **kw):
        seen.append((system, user))
        if "مدقق صارم" in system:
            return json.dumps(chk.pop(0) if chk else {"achieved": False, "missing": "?"},
                              ensure_ascii=False)
        if "ضع خطة" in system:
            return '{"plan":["افحص الصحة","لخص"]}'
        if "اقترح من 0" in system:
            return json.dumps(reflect or {"goals": []}, ensure_ascii=False)
        return json.dumps(seq.pop(0), ensure_ascii=False)
    brain.seen = seen
    return brain


def test_goal_lifecycle_plan_work_done_persisted(exp_dir):
    import goals
    calls = []
    brain = _goal_brain([{"decision": "work", "task": "افحص صحة النظام"},
                         {"decision": "done", "summary": "النظام سليم بحسب الفحص"}])
    eng = goals.GoalEngine(_registry([]), chat_fn=brain,
                           manager_factory=lambda tools: _FakeManager(calls))
    g = eng.goals.add("تأكد أن النظام سليم", priority=1)
    r1 = eng.work(g["id"])
    assert r1["status"] == "worked" and calls == ["افحص صحة النظام"]
    r2 = eng.work(g["id"])
    assert r2["status"] == "done"
    # إعادة تشغيل: الحالة تُعاد بناؤها من الأحداث الإلحاقية (المادة ٨)
    st = goals.GoalStore(experience.ExperienceStore(str(exp_dir))).state()[g["id"]]
    assert st["status"] == "done" and st["plan"] == ["افحص الصحة", "لخص"]
    assert st["runs"][0]["answer"] == "أُنجز: افحص صحة النظام"
    assert eng.work(g["id"])["status"] == "not_active"
    # القرار الثاني رأى ما أُنجز فعلًا
    assert "أُنجز: افحص صحة النظام" in brain.seen[-1][1]


def test_goal_blocked_and_exhausted_are_honest(exp_dir):
    import goals
    eng = goals.GoalEngine(_registry([]), chat_fn=_goal_brain(
        [{"decision": "blocked", "reason": "لا أداة لإرسال البريد"}]),
        manager_factory=lambda t: _FakeManager([]))
    g = eng.goals.add("أرسل بريدًا")
    assert eng.work(g["id"]) == {"status": "blocked", "goal_id": g["id"],
                                 "reason": "لا أداة لإرسال البريد"}
    eng2 = goals.GoalEngine(_registry([]), chat_fn=_goal_brain(
        [{"decision": "work", "task": "x"}] * 3), manager_factory=lambda t: _FakeManager([]),
        max_runs=2)
    g2 = eng2.goals.add("هدف طويل")
    eng2.work(g2["id"]); eng2.work(g2["id"])
    assert eng2.work(g2["id"])["status"] == "exhausted"


def test_reflect_proposes_self_goals_from_observations_with_cap_and_dedupe(exp_dir):
    import goals
    reg = _registry([])
    reg.register(ToolSpec(name="health.snapshot", description="صحة", inputs={}, outputs="",
                          handler=lambda: {"status": "degraded", "disk_used_pct": 97}))
    brain = _goal_brain([], reflect={"goals": [
        {"title": "شخّص سبب امتلاء القرص 97%", "why": "disk_used_pct 97", "priority": 1,
         "evidence": "disk_used_pct: 97"},
        {"title": "شخص سبب امتلاء القرص 97%", "why": "مكرر", "evidence": "97"}]})
    eng = goals.GoalEngine(reg, chat_fn=brain)
    out = eng.reflect()
    assert out["status"] == "reflected" and len(out["added"]) == 1
    g = eng.goals.state()[out["added"][0]["id"]]
    assert g["origin"] == "self" and g["priority"] == 1
    # الملاحظة الحقيقية وصلت العقل
    assert "97" in brain.seen[-1][1]


def test_autonomy_tick_prefers_work_then_reflects(exp_dir):
    import goals
    calls = []
    brain = _goal_brain([{"decision": "work", "task": "مهمة"}], reflect={"goals": []})
    reg = _registry([])
    loop = goals.AutonomyLoop(engine_factory=lambda: goals.GoalEngine(
        reg, chat_fn=brain, manager_factory=lambda t: _FakeManager(calls)), enabled=False)
    assert loop.run_once()["tick"] == "reflect"
    goals.GoalStore().add("هدف للمالك")
    out = loop.run_once()
    assert out["tick"] == "work" and out["status"] == "worked" and calls == ["مهمة"]
    assert loop.status()["ticks"] == 2


def test_autonomy_tools_exclude_external_and_owner_decisions(exp_dir):
    import goals
    reg = _registry([])
    for n in ("connector.mail.send", "proposals.decide", "goals.work"):
        reg.register(ToolSpec(name=n, description=n, inputs={}, outputs="", handler=lambda: {}))
    tools = goals.GoalEngine(reg, chat_fn=lambda *a, **k: None).tools()
    assert set(tools) == {"memory.stats", "disk.status"}


def test_autonomy_disabled_by_default_and_by_background_flag(monkeypatch):
    import goals
    monkeypatch.delenv("SOVEREIGN_AUTONOMY", raising=False)
    assert goals.build_from_env().enabled is False
    monkeypatch.setenv("SOVEREIGN_AUTONOMY", "1")
    monkeypatch.setenv("SOVEREIGN_DISABLE_BACKGROUND_THREADS", "1")
    lp = goals.build_from_env()
    assert lp.enabled is False and "BACKGROUND" in lp.reason


def test_app_registers_goal_tools():
    import app  # noqa: F401
    from tool_registry import get_registry
    names = {t["name"] for t in get_registry().list_tools()}
    assert {"goals.add", "goals.list", "goals.work", "autonomy.status", "autonomy.tick"} <= names
    import chat_agent
    assert "goals.list" in chat_agent.CHAT_READ_TOOLS
    assert "goals.add" not in chat_agent.CHAT_READ_TOOLS


# ------------------------------------------------------------------ R-790a / R-791a
def test_check_marks_goal_done_from_real_results(exp_dir):
    import goals
    eng = goals.GoalEngine(_registry([]), chat_fn=_goal_brain(
        [{"decision": "work", "task": "اعرف عدد أحداث الذاكرة"}],
        checks=[{"achieved": True, "summary": "في الذاكرة 148887 حدثًا"}]),
        manager_factory=lambda t: _FakeManager([]))
    g = eng.goals.add("كم حدثًا في الذاكرة")
    out = eng.work(g["id"])
    assert out["goal_status"] == "done" and out["check"]["achieved"] is True
    st = eng.goals.state()[g["id"]]
    assert st["status"] == "done" and "148887" in st["summary"]


def test_repeat_of_successful_task_is_prevented(exp_dir):
    import goals
    calls = []
    eng = goals.GoalEngine(_registry([]), chat_fn=_goal_brain(
        [{"decision": "work", "task": "شغّل memory.stats لمعرفة عدد الأحداث"},
         {"decision": "work", "task": "شغّل memory.stats لمعرفة عدد الأحداث الآن"}]),
        manager_factory=lambda t: _FakeManager(calls))
    g = eng.goals.add("هدف")
    eng.work(g["id"])
    out = eng.work(g["id"])
    assert out["status"] == "repeat_prevented" and len(calls) == 1
    assert eng.goals.state()[g["id"]]["runs"][-1]["status"] == "repeat_prevented"


def test_reflect_rejects_ungrounded_goal(exp_dir):
    import goals
    reg = _registry([])
    reg.register(ToolSpec(name="health.snapshot", description="صحة", inputs={}, outputs="",
                          handler=lambda: {"status": "healthy", "uptime": 3600}))
    brain = _goal_brain([], reflect={"goals": [
        {"title": "أعد ترتيب الأحداث في الذاكرة", "evidence": "الذاكرة مبعثرة 5000"}]})
    out = goals.GoalEngine(reg, chat_fn=brain).reflect()
    assert out["added"] == [] and out["rejected"][0]["reason"]


def test_grounded_requires_text_or_numbers_from_observations():
    import goals
    obs = '{"health.snapshot": "status: degraded\\ndisk_used_pct: 97"}'
    assert goals.grounded("disk_used_pct: 97", obs)
    assert goals.grounded("القرص 97 بالمئة", obs)
    assert not goals.grounded("القرص 88", obs)
    assert not goals.grounded("القرص ممتلئ", obs)


def test_plan_schema_constrains_tool_and_dedupes_same_tool(exp_dir):
    import manager
    sch = manager.plan_schema(3, ["memory.stats", "disk.status"])
    assert sch["properties"]["subtasks"]["items"]["properties"]["tool"]["enum"] == \
        ["disk.status", "memory.stats", "none"]
    plan = {"subtasks": [{"role": "a", "goal": "ذاكرة 1", "tool": "memory.stats"},
                         {"role": "b", "goal": "ذاكرة 2", "tool": "memory.stats"},
                         {"role": "c", "goal": "قرص", "tool": "disk.status"},
                         {"role": "d", "goal": "مخترعة", "tool": "invented.tool"}]}
    m = manager.AgentManager(_registry([]), chat_fn=FakeBrain(plan), max_agents=4)
    out = m.plan("x", m.worker_tools())
    assert [p["tool"] for p in out["subtasks"]] == ["memory.stats", "disk.status", "none"]
