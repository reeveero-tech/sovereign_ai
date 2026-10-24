"""R-743 (البند ٤.٣ — اكتشاف العيوب ذاتيًا): دورة بجدول تنتج تقرير عيوب.

معيار الإغلاق في الخارطة: «دورة تعمل بجدول وتنتج تقرير عيوب».
1. وحدة defect_scan حتمية: مصادر حقيقية → نتائج بأدلة، بلا تخمين.
2. قائمة عمل: العيب المتكرر لا يتضاعف (first_seen/last_seen/occurrences)،
   والعيب الزائل يُعلَّم resolved لا يُحذف (التاريخ لا يُمحى).
3. حالة سليمة = صفر عيوب مفتوحة (لا عيوب مختلقة).
4. الأداة defects.scan مسجلة، والمجدول يحمل مهمة self_defect_scan.
5. حلقة حقيقية: المجدول يشغّل الأداة عبر السجل → تقرير في /defects/report.
6. /defects/report قراءة فقط ولا سر، ويعلن بصدق إن لم تُشغَّل دورة.
"""

import importlib
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _healthy():
    return {"status": "healthy", "components": {
        "core": {"status": "healthy"}, "controller": {"status": "healthy"}}}


def _sched(ok=True, err=None):
    return {"enabled": True, "tasks": [{"name": "self_health_check",
            "last_ok": ok, "last_error": err, "runs": 1}]}


@pytest.fixture
def ds():
    import defect_scan
    importlib.reload(defect_scan)
    return defect_scan


def test_healthy_state_yields_no_open_defects(ds):
    wl = ds.DefectWorklist()
    report = wl.scan(health=_healthy(), scheduler=_sched(),
                     heartbeat={"active_alerts": 0}, now=100.0)
    assert report["open_count"] == 0, report
    assert report["defects"] == []


def test_unhealthy_component_is_defect_with_evidence(ds):
    h = _healthy()
    h["status"] = "degraded"
    h["components"]["core"] = {"status": "unhealthy", "error": "boom"}
    report = ds.DefectWorklist().scan(health=h, scheduler=_sched(),
                                      heartbeat={"active_alerts": 0}, now=1.0)
    ids = {d["id"] for d in report["defects"]}
    assert "component_unhealthy:core" in ids
    d = next(d for d in report["defects"] if d["id"] == "component_unhealthy:core")
    assert d["severity"] == "high" and d["evidence"], d


def test_scheduler_failure_is_defect(ds):
    report = ds.DefectWorklist().scan(
        health=_healthy(), scheduler=_sched(False, "RuntimeError: R-635: No active signing key"),
        heartbeat={"active_alerts": 0}, now=1.0)
    d = next(d for d in report["defects"]
             if d["id"] == "scheduled_task_failed:self_health_check")
    assert "R-635" in d["evidence"]


def test_supervisor_alerts_and_missing_heartbeat(ds):
    r1 = ds.DefectWorklist().scan(health=_healthy(), scheduler=_sched(),
                                  heartbeat={"active_alerts": 3}, now=1.0)
    assert any(d["id"] == "supervisor_alerts" for d in r1["defects"])
    r2 = ds.DefectWorklist().scan(health=_healthy(), scheduler=_sched(),
                                  heartbeat=None, now=1.0)
    d = next(d for d in r2["defects"] if d["id"] == "supervisor_heartbeat_missing")
    assert d["severity"] == "low"


def test_worklist_dedupes_and_resolves_without_deleting(ds):
    wl = ds.DefectWorklist()
    bad = _sched(False, "x")
    wl.scan(health=_healthy(), scheduler=bad, heartbeat={"active_alerts": 0}, now=10.0)
    r = wl.scan(health=_healthy(), scheduler=bad, heartbeat={"active_alerts": 0}, now=20.0)
    d = next(d for d in r["defects"] if d["id"].startswith("scheduled_task_failed"))
    assert d["occurrences"] == 2 and d["first_seen"] == 10.0 and d["last_seen"] == 20.0
    assert r["open_count"] == 1
    r = wl.scan(health=_healthy(), scheduler=_sched(), heartbeat={"active_alerts": 0}, now=30.0)
    d = next(d for d in r["defects"] if d["id"].startswith("scheduled_task_failed"))
    assert d["status"] == "resolved" and d["resolved_at"] == 30.0
    assert r["open_count"] == 0


def test_persistent_degraded_health_history(ds):
    """رصد تاريخ /health: التدهور في دورات متتالية يُرفع إلى عيب مستمر."""
    wl = ds.DefectWorklist()
    h = _healthy()
    h["status"] = "degraded"
    for t in range(ds.PERSISTENT_AFTER):
        r = wl.scan(health=h, scheduler=_sched(), heartbeat={"active_alerts": 0}, now=float(t))
    assert any(d["id"] == "health_degraded_persistent" for d in r["defects"])
    assert len(r["health_history"]) == ds.PERSISTENT_AFTER


def test_tool_and_scheduled_task_registered():
    import scheduler
    names = [t.name for t in scheduler.build_from_env().tasks]
    assert "self_defect_scan" in names
    tool = next(t for t in scheduler.build_from_env().tasks if t.name == "self_defect_scan").tool
    assert tool == "defects.scan"


def test_real_loop_scheduler_runs_scan_and_report_endpoint(monkeypatch):
    """حلقة حقيقية: المجدول → السجل → defects.scan → /defects/report."""
    from fastapi.testclient import TestClient
    import app as app_module
    with TestClient(app_module.app) as client:
        r0 = client.get("/defects/report")
        assert r0.status_code == 200
        import tool_registry
        assert any(t["name"] == "defects.scan"
                   for t in tool_registry.get_registry().list_tools())
        import scheduler
        sched = scheduler.Scheduler(
            [scheduler.ScheduledTask("self_defect_scan", "defects.scan", 1.0, next_due=0.0)],
            enabled=True)
        out = sched.run_due(now=10.0)
        assert out[0]["runs"] == 1 and out[0]["last_ok"] is True, out
        r = client.get("/defects/report").json()
        assert r["report"] is not None
        assert "open_count" in r["report"] and "defects" in r["report"]
        assert r["report"]["scans"] >= 1
        text = str(r).lower()
        for secret_word in ("api_key", "private_key", "service_role"):
            assert secret_word not in text
