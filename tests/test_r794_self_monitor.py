# -*- coding: utf-8 -*-
"""R-794 (٤.٦): المراقبة الذاتية الموسّعة — تقيس وتقترح فقط، لا تنفّذ."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import self_monitor as sm  # noqa: E402
import improvement_proposals as ip  # noqa: E402


def _ids(report):
    return {d["id"] for d in report["defects"]}


def _healthy_sources(**over):
    s = {
        "disk": lambda: {"state": "ok", "inodes_used_pct": 10.0, "bytes_used_pct": 20.0},
        "tool_stats": lambda: {"memory.stats": {"calls": 5, "ok": 5, "failed": 0,
                                                "success_rate": 1.0, "last_error": None}},
        "ledger_verify": lambda: {"ok": True, "checked": 3},
        "autonomy": lambda: {"enabled": True, "last": {"tick": "work"}},
        "goals": lambda: {},
        "proposals": lambda: [],
    }
    s.update(over)
    return s


def test_healthy_system_has_zero_defects():
    r = sm.SelfMonitor().run(_healthy_sources(), now=1.0)
    assert r["open_count"] == 0 and r["defects"] == []


def test_detects_real_problems_from_sources():
    srcs = _healthy_sources(
        disk=lambda: {"state": "critical", "inodes_used_pct": 99.0, "bytes_used_pct": 30.0},
        tool_stats=lambda: {"web.search": {"calls": 6, "ok": 1, "failed": 5,
                                           "success_rate": 0.167, "last_error": "timeout"}},
        ledger_verify=lambda: {"ok": False, "reason": "entry_hash لا يطابق المحتوى"},
        autonomy=lambda: {"enabled": True, "last": {"tick": "crashed", "error": "boom"}},
        goals=lambda: {"G-1": {"title": "هدف", "status": "active",
                               "runs": [{"status": "failed"}] * 3}},
    )
    ids = _ids(sm.SelfMonitor().run(srcs, now=1.0))
    assert {"selfmon:disk_critical", "selfmon:tool_failing:web.search",
            "selfmon:ledger_chain_broken", "selfmon:autonomy_crashed",
            "selfmon:goal_stuck:G-1"} <= ids


def test_disk_inode_trend_across_cycles():
    mon = sm.SelfMonitor()
    r = None
    for i, pct in enumerate((40.0, 46.0, 52.0)):
        r = mon.run(_healthy_sources(
            disk=lambda pct=pct: {"state": "ok", "inodes_used_pct": pct, "bytes_used_pct": 10.0}),
            now=float(i))
    assert "selfmon:disk_trend" in _ids(r)


def test_failing_source_is_declared_not_swallowed():
    def boom():
        raise RuntimeError("no store")
    r = sm.SelfMonitor().run(_healthy_sources(tool_stats=boom), now=1.0)
    assert "selfmon:source_unavailable:tool_stats" in _ids(r)
    assert r["vitals"]["errors"]["tool_stats"].startswith("RuntimeError")


def test_regression_when_implemented_proposal_defect_still_open():
    props = [{"id": "P-1", "status": "implemented", "defect_open": True,
              "defect_id": "component_unhealthy:x", "commit": "abc1234"}]
    r = sm.SelfMonitor().run(_healthy_sources(proposals=lambda: props), now=1.0)
    assert "selfmon:regression:P-1" in _ids(r)


def test_proposal_backlog_threshold():
    props = [{"id": f"P-{i}", "status": "proposed"} for i in range(sm.BACKLOG_AT)]
    r = sm.SelfMonitor().run(_healthy_sources(proposals=lambda: props), now=1.0)
    assert "selfmon:proposal_backlog" in _ids(r)


def test_findings_feed_proposals_without_touching_other_sources():
    book = ip.ProposalBook()
    book.ingest({"defects": [{"id": "component_unhealthy:db", "status": "open",
                              "severity": "high", "title": "t", "evidence": "e"}]}, now=1.0)
    rep = sm.SelfMonitor().run(_healthy_sources(
        disk=lambda: {"state": "critical", "inodes_used_pct": 99.0, "bytes_used_pct": 10.0}), now=2.0)
    created = book.ingest_scoped(rep, now=2.0, prefix="selfmon:")
    assert [c["defect_id"] for c in created] == ["selfmon:disk_critical"]
    assert created[0]["status"] == "proposed" and created[0]["kind"] == "owner_action"
    other = next(i for i in book.list() if i["defect_id"] == "component_unhealthy:db")
    assert other["defect_open"] is True  # مصدر آخر لم يُغلق خطأً
    # زوال العيب → يُغلق اقتراحه ضمن البادئة فقط
    book.ingest_scoped(sm.SelfMonitor().run(_healthy_sources(), now=3.0), now=3.0, prefix="selfmon:")
    mine = next(i for i in book.list() if i["defect_id"] == "selfmon:disk_critical")
    assert mine["defect_open"] is False
    assert next(i for i in book.list() if i["defect_id"] == "component_unhealthy:db")["defect_open"] is True


def test_module_is_propose_only_static_guard():
    code = open(os.path.join(ROOT, "backend", "self_monitor.py"), encoding="utf-8").read()
    # الوثيقة العلوية تذكر الحظر؛ نفحص الشيفرة بعدها فقط
    body = code.split('"""', 2)[2]
    for forbidden in ("subprocess", "os.system", "open(", "write_text", "Popen", "git ", "exec(", "eval("):
        assert forbidden not in body, f"مسار تعديل ذاتي محظور: {forbidden}"


def test_tool_scheduler_and_endpoint_wired(monkeypatch):
    import scheduler
    task = next(t for t in scheduler.build_from_env().tasks if t.name == "self_monitor")
    assert task.tool == "self.monitor"
    from fastapi.testclient import TestClient
    import app as app_module
    with TestClient(app_module.app) as client:
        assert client.get("/self/monitor").status_code == 200
        from tool_registry import get_registry
        assert "self.monitor" in {t["name"] for t in get_registry().list_tools()}
        out = get_registry().invoke("self.monitor", caller="test", inputs={})
        assert out.get("ok") is True, out
        rep = client.get("/self/monitor").json()["report"]
        assert rep is not None and "defects" in rep and "vitals" in rep
