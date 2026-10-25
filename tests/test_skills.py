# -*- coding: utf-8 -*-
"""R-757 (ROADMAP_V5 ٤.٢ + ٤.٣ — بأمر المالك 2026-10-25 «أسلمك المشروع»):
اكتساب المهارات.

المهارة = حزمة موثقة (اسم/إصدار/مصدر/أذونات/خطوات/حالات تقييم) — إجراء مركب
فوق أدوات مسجلة. دورة الاكتساب: اقتراح (بصمة محتوى) → تقييم آلي بحالات مرجعية
(الحلقة R-753 مقيدة بأذونات الحزمة) → موافقة المالك بأثر (لا تفعيل بلا تقييم
ناجح ولا بمحتوى تغير بعد التقييم) → أداة `skill.<اسم>` في السجل → تدوم عبر إعادة
تشغيل العملية (تُحمّل من القرص) → تراجع للإصدار السابق.
٤.٣: أداة مكتشفة (MCP) تُعلن «متاحة غير مُتعلمة» حتى تستخدمها مهارة مفعّلة.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    import memory.core as core_mod
    from tool_registry import ToolRegistry, ToolSpec

    class FC:
        def __init__(self):
            self.events, self.fail = [], False

        def append_event(self, t, p, user=None):
            if self.fail:
                raise RuntimeError("R-635: No active signing key available")
            self.events.append((str(t), p))
    fc = FC()
    monkeypatch.setattr(core_mod, "get_core", lambda: fc)
    reg = ToolRegistry()
    reg.register(ToolSpec(name="math.add", description="", inputs={"a": "", "b": ""},
                          outputs="sum", handler=lambda a, b: {"sum": int(a) + int(b)}))
    reg.register(ToolSpec(name="math.mul", description="", inputs={"a": "", "b": ""},
                          outputs="product", handler=lambda a, b: {"product": int(a) * int(b)}))
    reg.register(ToolSpec(name="mcp.fake.echo", description="", inputs={"message": ""},
                          outputs="", handler=lambda message: message))
    return reg, fc, tmp_path


def _manifest(version="1.0.0", expect=10, perms=("math.add", "math.mul")):
    return {
        "name": "add_then_double", "version": version,
        "source": "owner-authored (test)", "description": "(a+b)*2",
        "inputs": {"a": "عدد", "b": "عدد"},
        "permissions": list(perms),
        "steps": [
            {"tool": "math.add", "inputs": {"a": "{{a}}", "b": "{{b}}"},
             "check": {"type": "non_empty"}},
            {"tool": "math.mul", "inputs": {"a": "{{steps.0.sum}}", "b": 2},
             "check": {"type": "non_empty"}},
        ],
        "output": "{{steps.1.product}}",
        "eval": {"reference": "حساب يدوي", "cases": [
            {"inputs": {"a": 2, "b": 3}, "expect": expect},
            {"inputs": {"a": 0, "b": 0}, "expect": 0},
        ]},
    }


def _lib(ctx):
    from skills import SkillLibrary
    reg, _, tmp = ctx
    return SkillLibrary(tmp / "skills", reg)


def test_full_acquisition_cycle(ctx):
    reg, fc, _ = ctx
    lib = _lib(ctx)
    p = lib.propose(_manifest(), actor="agent")
    assert p["state"] == "proposed" and len(p["content_hash"]) == 64
    ev = lib.evaluate("add_then_double", "1.0.0")
    assert ev["passed"] == 2 and ev["total"] == 2 and ev["state"] == "evaluated"
    assert "skill.add_then_double" not in {t["name"] for t in reg.list_tools()}
    lib.approve("add_then_double", "1.0.0", actor="owner")
    assert "skill.add_then_double" in {t["name"] for t in reg.list_tools()}
    out = reg.invoke("skill.add_then_double", caller="owner", inputs={"a": 4, "b": 1})
    assert out["ok"] and out["result"]["output"] == 10
    kinds = [e[1].get("op") for e in fc.events if e[0] == "skill_lifecycle"]
    assert kinds[:3] == ["skill.propose", "skill.evaluate", "skill.approve"]


def test_failed_evaluation_blocks_approval(ctx):
    from skills import SkillError
    lib = _lib(ctx)
    lib.propose(_manifest(expect=11), actor="agent")       # مرجع لا يطابق
    ev = lib.evaluate("add_then_double", "1.0.0")
    assert ev["state"] == "failed_eval" and ev["passed"] == 1
    with pytest.raises(SkillError):
        lib.approve("add_then_double", "1.0.0", actor="owner")


def test_unevaluated_cannot_be_approved(ctx):
    from skills import SkillError
    lib = _lib(ctx)
    lib.propose(_manifest(), actor="agent")
    with pytest.raises(SkillError):
        lib.approve("add_then_double", "1.0.0", actor="owner")


def test_tampered_package_after_eval_refused(ctx):
    from skills import SkillError
    reg, _, tmp = ctx
    lib = _lib(ctx)
    lib.propose(_manifest(), actor="agent")
    lib.evaluate("add_then_double", "1.0.0")
    f = next((tmp / "skills").rglob("1.0.0.json"))
    d = json.loads(f.read_text(encoding="utf-8"))
    d["manifest"]["steps"][1]["inputs"]["b"] = 3             # تعديل بعد التقييم
    f.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(SkillError):
        lib.approve("add_then_double", "1.0.0", actor="owner")


def test_permissions_enforced_tool_outside_manifest(ctx):
    lib = _lib(ctx)
    m = _manifest(perms=("math.add",))                      # mul غير مأذون
    lib.propose(m, actor="agent")
    ev = lib.evaluate("add_then_double", "1.0.0")
    assert ev["state"] == "failed_eval" and ev["passed"] == 0


def test_invalid_manifest_rejected(ctx):
    from skills import SkillError
    lib = _lib(ctx)
    bad = _manifest()
    del bad["source"]
    with pytest.raises(SkillError):
        lib.propose(bad, actor="agent")
    bad2 = _manifest()
    bad2["steps"][0]["tool"] = "agent.run"
    with pytest.raises(SkillError):
        lib.propose(bad2, actor="agent")
    bad3 = _manifest()
    bad3["eval"]["cases"] = []
    with pytest.raises(SkillError):
        lib.propose(bad3, actor="agent")


def test_survives_process_restart_without_relearning(ctx):
    from skills import SkillLibrary
    from tool_registry import ToolRegistry
    reg, _, tmp = ctx
    lib = _lib(ctx)
    lib.propose(_manifest(), actor="agent")
    lib.evaluate("add_then_double", "1.0.0")
    lib.approve("add_then_double", "1.0.0", actor="owner")
    reg2 = ToolRegistry()                                     # «عملية جديدة»
    for t in ("math.add", "math.mul"):
        reg2.register(reg._tools[t])
    lib2 = SkillLibrary(tmp / "skills", reg2)
    loaded = lib2.load_active()
    assert loaded == ["skill.add_then_double"]
    out = reg2.invoke("skill.add_then_double", caller="owner", inputs={"a": 1, "b": 1})
    assert out["result"]["output"] == 4


def test_rollback_to_previous_version(ctx):
    reg, _, _ = ctx
    lib = _lib(ctx)
    lib.propose(_manifest(), actor="agent")
    lib.evaluate("add_then_double", "1.0.0")
    lib.approve("add_then_double", "1.0.0", actor="owner")
    m2 = _manifest(version="2.0.0")
    m2["output"] = "{{steps.0.sum}}"                         # سلوك مختلف
    m2["eval"]["cases"] = [{"inputs": {"a": 2, "b": 3}, "expect": 5}]
    lib.propose(m2, actor="agent")
    lib.evaluate("add_then_double", "2.0.0")
    lib.approve("add_then_double", "2.0.0", actor="owner")
    assert reg.invoke("skill.add_then_double", inputs={"a": 2, "b": 3})["result"]["output"] == 5
    r = lib.rollback("add_then_double", actor="owner")
    assert r["active"] == "1.0.0"
    assert reg.invoke("skill.add_then_double", inputs={"a": 2, "b": 3})["result"]["output"] == 10


def test_approval_fail_closed_without_ledger(ctx):
    from skills import SkillError
    reg, fc, _ = ctx
    lib = _lib(ctx)
    lib.propose(_manifest(), actor="agent")
    lib.evaluate("add_then_double", "1.0.0")
    fc.fail = True
    with pytest.raises(Exception):
        lib.approve("add_then_double", "1.0.0", actor="owner")
    assert "skill.add_then_double" not in {t["name"] for t in reg.list_tools()}


def test_discovered_tool_is_available_not_learned(ctx):
    """٤.٣: اكتشاف ≠ اكتساب."""
    lib = _lib(ctx)
    st = lib.status()
    disc = {d["tool"]: d for d in st["discovered"]}
    assert disc["mcp.fake.echo"]["learned"] is False
    m = _manifest(perms=("math.add", "math.mul", "mcp.fake.echo"))
    lib.propose(m, actor="agent")
    lib.evaluate("add_then_double", "1.0.0")
    lib.approve("add_then_double", "1.0.0", actor="owner")
    disc2 = {d["tool"]: d for d in lib.status()["discovered"]}
    assert disc2["mcp.fake.echo"]["learned"] is True


def test_skills_install_tool_registered_and_inventory_moves():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        names = {t["name"] for t in client.get("/tools/list").json()["tools"]}
        assert {"skills.install", "skills.status"} <= names
        caps = {c["id"]: c for c in client.get("/capabilities").json()["capabilities"]}
        assert caps["skill_acquisition"]["level"] != "missing"
        r = client.post("/skills/approve", json={"name": "x", "version": "1"})
        assert r.status_code == 401
