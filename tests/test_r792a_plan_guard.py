# -*- coding: utf-8 -*-
"""R-792a: حارس الخطة ضد «تحقق» زائف + قيم القرص المحسوبة.

حي 2026-10-27 (G-3f02bde3): خطة النظام [memory.stats, disk.status]، نُفذ disk.status
وحده، وأعلن فحص العقل achieved=true فأُغلق الهدف دون عدد أحداث الذاكرة؛ وقرأ العقل
البايتات «86.3 GB من 105.3 GB» والحقيقة 8.63 من 10.53.
"""
import json
import os
import sys
import types

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
    for n in ("memory.stats", "disk.status"):
        r.register(ToolSpec(name=n, description=n, inputs={}, outputs="", handler=lambda: {}))
    return r


class _Mgr:
    def __init__(self, calls):
        self.calls = calls

    def run(self, task):
        self.calls.append(task)
        return {"status": "completed", "answer": f"نتيجة {task}", "agents_created": 1,
                "run_id": "m", "tools_used": [task]}


def _brain(tasks, seen):
    seq = list(tasks)

    def brain(system, user, **kw):
        seen.append((system, user))
        if "مدقق صارم" in system:   # العقل «متساهل» دائمًا — كما حيًا
            return json.dumps({"achieved": True, "summary": "تحقق"}, ensure_ascii=False)
        if "ضع خطة" in system:
            return '{"plan":["memory.stats","disk.status"]}'
        return json.dumps({"decision": "work", "task": seq.pop(0)}, ensure_ascii=False)
    return brain


def test_lenient_check_cannot_close_goal_while_plan_tools_unrun(exp_dir):
    import goals
    calls, seen = [], []
    eng = goals.GoalEngine(_reg(), chat_fn=_brain(["disk.status", "memory.stats"], seen),
                           manager_factory=lambda t: _Mgr(calls))
    gid = eng.goals.add("اعرف عدد أحداث ذاكرتك وحالة قرصك")["id"]
    out = eng.work(gid)
    assert out["check"]["achieved"] is False
    assert out["check"]["guard"] == "plan_tools_not_run" and "memory.stats" in out["check"]["missing"]
    g = eng.goals.state()[gid]
    assert g["status"] == "active" and g["runs"][0]["tools"] == ["disk.status"]
    # الخطوة التالية ترى ما بقي من خطتها، ثم يُغلق الهدف بعد التنفيذ الفعلي
    out2 = eng.work(gid)
    nxt = [u for s, u in seen if "plan_tools_not_run" in u][-1]
    assert json.loads(nxt)["plan_tools_not_run"] == ["memory.stats"]
    assert out2["check"]["achieved"] is True and eng.goals.state()[gid]["status"] == "done"
    assert calls == ["disk.status", "memory.stats"]


def test_legacy_runs_without_tools_field_are_not_judged(exp_dir):
    import goals
    eng = goals.GoalEngine(_reg(), chat_fn=lambda *a, **k: "{}")
    g = {"plan": ["memory.stats"], "runs": [{"task": "x", "status": "completed", "answer": "y"}]}
    assert eng.unrun_plan_tools(g) == []


def test_natural_language_plan_steps_are_not_guarded(exp_dir):
    import goals
    eng = goals.GoalEngine(_reg(), chat_fn=lambda *a, **k: "{}")
    g = {"plan": ["افحص الصحة", "disk.status"],
         "runs": [{"task": "x", "status": "completed", "answer": "y", "tools": ["disk.status"]}]}
    assert eng.unrun_plan_tools(g) == []


def test_manager_reports_tools_used(exp_dir):
    import manager
    rep = {"goal": "g", "status": "completed"}
    m = manager.AgentManager.__new__(manager.AgentManager)
    m.source = "manager"
    manager.AgentManager._finish(m, rep, [{"tools": ["disk.status"]}, {"tools": ["memory.stats",
                                                                               "disk.status"]}])
    assert rep["tools_used"] == ["disk.status", "memory.stats"]


def test_local_volume_gives_computed_gb_not_raw_bytes_only(monkeypatch, tmp_path):
    import app as app_mod
    live = types.SimpleNamespace(f_blocks=2571625, f_bavail=2107867, f_frsize=4096,
                                 f_files=645120, f_favail=317749)
    monkeypatch.setattr(os, "statvfs", lambda p: live)
    v = app_mod._local_volume_status(str(tmp_path))
    assert v["total_gb"] == 10.53 and v["free_gb"] == 8.63
    assert "محلي" in v["kind"]
