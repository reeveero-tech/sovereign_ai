"""R-732 (البند ٣.٦ — بأمر المالك «تابع»): أداة الجدولة.

معيار الإغلاق: «مهمة مجدولة تُنفذ وتُسجل».

المبادئ المثبتة هنا:
- المجدول لا ينفذ إلا أدوات مسجلة في سجل R-729 (لا شيفرة حرة)، عبر
  ToolRegistry.invoke — فكل تشغيل يترك أثر tool_invoked موقعًا (caller=scheduler).
- معطل افتراضيًا ويقول ذلك بصدق مع السبب: كل تشغيل يُلحق حدثًا بالسجل السيادي
  الدائم في الإنتاج، فالتفعيل هناك قرار المالك (SOVEREIGN_SCHEDULER=1).
- fail-closed بلا انهيار: فشل أداة أو تعذر التوقيع يُسجل في الحالة ولا يوقف الحلقة.
- المادة ٨: التشغيل المجدول لا يمس أحداث الذاكرة السابقة ولا سلامة السلسلة.
"""

import os
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


def _api_key() -> str:
    return os.environ.get("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


def _client():
    from fastapi.testclient import TestClient
    from app import app
    return TestClient(app)


def _scheduler_events(limit=200):
    from memory.core import get_core
    core = get_core()
    out = []
    for event in core.iterate_events(reverse=True, limit=limit):
        if event.get("type") == "tool_invoked":
            payload = core.get_payload(event)
            if payload.get("caller") == "scheduler":
                out.append(payload)
    return out


def test_scheduler_disabled_by_default_and_says_why(monkeypatch):
    monkeypatch.delenv("SOVEREIGN_SCHEDULER", raising=False)
    with _client() as client:
        r = client.get("/scheduler/status")
        assert r.status_code == 200
        s = r.json()
        assert s["enabled"] is False
        assert s["running"] is False
        assert "SOVEREIGN_SCHEDULER" in s["reason"], "التعطيل بلا سبب معلن"
        names = [t["tool"] for t in s["tasks"]]
        assert "health.snapshot" in names, "المهمة المعلنة غير ظاهرة"
        assert all(t["runs"] == 0 for t in s["tasks"])


def test_scheduled_task_runs_and_is_ledgered(monkeypatch):
    """معيار الإغلاق: مهمة مجدولة تُنفذ فعلًا بحلقة الخلفية وتُسجل أثرًا موقعًا."""
    monkeypatch.setenv("SOVEREIGN_SCHEDULER", "1")
    monkeypatch.setenv("SOVEREIGN_SCHEDULER_INTERVAL", "1")
    before = len(_scheduler_events())
    with _client() as client:
        deadline = time.time() + 10
        task = None
        while time.time() < deadline:
            s = client.get("/scheduler/status").json()
            task = next(t for t in s["tasks"] if t["tool"] == "health.snapshot")
            if task["runs"] >= 1:
                break
            time.sleep(0.2)
        assert s["enabled"] is True and s["running"] is True
        assert task["runs"] >= 1, "المهمة المجدولة لم تُنفذ خلال 10 ثوانٍ"
        assert task["last_ok"] is True, task.get("last_error")
    events = _scheduler_events()
    assert len(events) > before, "لا أثر للتشغيل المجدول في السجل السيادي"
    # R-743: مهمتان مجدولتان الآن (health.snapshot + defects.scan) — نفس الفحص
    # محصورًا في أحداث المهمة المختبرة لا «آخر حدث أيًّا كان»
    events = [e for e in events if e["tool"] == "health.snapshot"]
    assert events, "لا أثر لتشغيل health.snapshot المجدول في السجل السيادي"
    latest = events[0]
    assert latest["tool"] == "health.snapshot" and latest["ok"] is True
    # الحالة تعكس السجل الحقيقي لا رقمًا داخليًا منفصلًا
    assert task["last_fingerprint"] in {e["result_fingerprint"] for e in events}


def test_scheduler_stops_on_shutdown(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_SCHEDULER", "1")
    monkeypatch.setenv("SOVEREIGN_SCHEDULER_INTERVAL", "1")
    from app import app
    with _client():
        sched = app.state.scheduler
        assert sched.running is True
    assert sched.running is False, "حلقة المجدول لم تتوقف مع إيقاف الخادم"


def test_scheduler_rejects_unregistered_tool_without_crashing():
    from scheduler import Scheduler, ScheduledTask
    sched = Scheduler([ScheduledTask(name="bogus", tool="no.such.tool", interval_seconds=1)], enabled=True)
    sched.run_due(now=time.time() + 5)
    t = sched.status()["tasks"][0]
    assert t["runs"] == 1 and t["last_ok"] is False
    assert "UnknownTool" in t["last_error"], "أداة غير مسجلة نُفذت أو فشلت بصمت"


def test_scheduler_fail_closed_on_signing_failure_and_keeps_going(monkeypatch):
    """تعذر توقيع السجل (R-635) يرفع RuntimeError في invoke — يُسجل في الحالة
    ولا يكسر الحلقة؛ التشغيل التالي يُحاول من جديد."""
    from scheduler import Scheduler, ScheduledTask
    import tool_registry

    calls = {"n": 0}

    class Boom:
        def invoke(self, name, caller="owner"):
            calls["n"] += 1
            raise RuntimeError("signing key unavailable")

    monkeypatch.setattr(tool_registry, "get_registry", lambda: Boom())
    sched = Scheduler([ScheduledTask(name="hs", tool="health.snapshot", interval_seconds=1)], enabled=True)
    now = time.time()
    sched.run_due(now=now + 2)
    sched.run_due(now=now + 4)
    t = sched.status()["tasks"][0]
    assert calls["n"] == 2, "الحلقة توقفت بعد أول فشل"
    assert t["last_ok"] is False and "RuntimeError" in t["last_error"]


def test_task_not_rerun_before_interval():
    from scheduler import Scheduler, ScheduledTask
    sched = Scheduler([ScheduledTask(name="bogus", tool="no.such.tool", interval_seconds=100)], enabled=True)
    now = time.time()
    sched.run_due(now=now + 101)
    sched.run_due(now=now + 102)  # قبل انقضاء الفاصل
    assert sched.status()["tasks"][0]["runs"] == 1


def test_scheduled_runs_preserve_memory(monkeypatch):
    """المادة ٨: التشغيل المجدول يُلحق فقط — الأحداث السابقة باقية والسلسلة سليمة."""
    from memory.core import get_core, IntegrityStatus
    from scheduler import Scheduler, ScheduledTask
    with _client():
        core = get_core()
        core.append_event("interaction", {"marker": "R-732-before"}, user="test")
        before = [e.get("hash") for e in core.iterate_events()]
        sched = Scheduler([ScheduledTask(name="hs", tool="health.snapshot", interval_seconds=1)], enabled=True)
        now = time.time()
        for k in range(3):
            sched.run_due(now=now + 2 * (k + 1))
        after = [e.get("hash") for e in core.iterate_events()]
        assert after[:len(before)] == before, "التشغيل المجدول غيّر أحداثًا سابقة"
        assert len(after) == len(before) + 3, "كل تشغيل يجب أن يُلحق حدثًا واحدًا بالضبط"
        assert core.verify_integrity() != IntegrityStatus.CORRUPTED


def test_status_has_no_secrets(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_SCHEDULER", "1")
    with _client() as client:
        r = client.get("/scheduler/status")
        assert r.status_code == 200, "النقطة غير موجودة — لا يُعد غياب السر نجاحًا"
        assert _api_key() not in r.text


def test_frontend_shows_scheduler_status():
    """الحالة مرئية للمالك من النقطة الفعلية (ربط حي — ١.٤)."""
    js = (REPO_ROOT / "frontend/js/modules/live-system-status.js").read_text(encoding="utf-8")
    assert "/scheduler/status" in js
