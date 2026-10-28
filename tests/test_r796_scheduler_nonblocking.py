"""R-796: المجدول لا يحجب حلقة الحدث.

عيب حي مقيس (2026-10-28): مسبار /health كل 2ث على الإنتاج سجّل رد 82.06ث
(«11:18:10 200 82.058904») ثم 0.11ث — لأن Scheduler._loop كان يستدعي
run_due() متزامنًا داخل حلقة asyncio، وأداة مثل benchmark.run (ثلاث نداءات
للعقل ~30ث لكل منها) تجمّد الخادم كله (/health و/chat) أثناء تشغيلها.

المعيار: أثناء تشغيل مهمة مجدولة بطيئة تبقى الحلقة تستجيب (فجوة نبض قصيرة)
و status() يرد فورًا من خيط آخر (لا قفل ممسوك طوال تنفيذ الأداة).
"""

import asyncio
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

SLOW = 1.5


class _SlowRegistry:
    def __init__(self):
        self.calls = 0

    def invoke(self, name, caller=None, **kwargs):
        self.calls += 1
        time.sleep(SLOW)
        return {"ok": True, "error": None, "trace": {"result_fingerprint": "f" * 16}}


def _patch(monkeypatch):
    import tool_registry
    reg = _SlowRegistry()
    monkeypatch.setattr(tool_registry, "get_registry", lambda: reg)
    return reg


def test_event_loop_stays_responsive_during_slow_task(monkeypatch):
    from scheduler import Scheduler, ScheduledTask
    reg = _patch(monkeypatch)

    async def main():
        sched = Scheduler([ScheduledTask(name="slow", tool="slow.tool",
                                         interval_seconds=0.05)], enabled=True)
        sched.start()
        gaps = []
        last = time.monotonic()
        t_end = last + SLOW + 1.0
        while time.monotonic() < t_end:
            await asyncio.sleep(0.05)
            now = time.monotonic()
            gaps.append(now - last)
            last = now
        await sched.stop()
        return max(gaps)

    max_gap = asyncio.run(main())
    assert reg.calls >= 1, "المهمة لم تُشغَّل أصلًا"
    assert max_gap < 0.5, f"الحلقة حُجبت {max_gap:.2f}ث أثناء مهمة مجدولة (يجب < 0.5ث)"


def test_status_not_blocked_while_task_runs(monkeypatch):
    from scheduler import Scheduler, ScheduledTask
    _patch(monkeypatch)
    sched = Scheduler([ScheduledTask(name="slow", tool="slow.tool",
                                     interval_seconds=0.0)], enabled=True)
    for t in sched.tasks:
        t.next_due = 0
    th = threading.Thread(target=sched.run_due)
    th.start()
    time.sleep(0.2)
    t0 = time.monotonic()
    st = sched.status()
    elapsed = time.monotonic() - t0
    th.join()
    assert elapsed < 0.3, f"status() انتظر {elapsed:.2f}ث خلف تنفيذ الأداة"
    task = st["tasks"][0]
    assert task["running"] is True, "الحالة لا تعلن أن المهمة تعمل الآن"
    assert sched.status()["tasks"][0]["last_ok"] is True


def test_overlapping_run_due_is_skipped_not_doubled(monkeypatch):
    from scheduler import Scheduler, ScheduledTask
    reg = _patch(monkeypatch)
    sched = Scheduler([ScheduledTask(name="slow", tool="slow.tool",
                                     interval_seconds=0.0)], enabled=True)
    for t in sched.tasks:
        t.next_due = 0
    th = threading.Thread(target=sched.run_due)
    th.start()
    time.sleep(0.2)
    second = sched.run_due()
    th.join()
    assert second == [], "تشغيل متداخل نفّذ المهمة مرتين"
    assert reg.calls == 1
