# -*- coding: utf-8 -*-
"""R-758 (ROADMAP_V5 §٥: ٥.١ + ٥.٢ + ٥.٣ — بأمر المالك 2026-10-25 «أسلمك المشروع»):
أسطول الوكلاء.

التمييز الإلزامي: **مسجّل** (طُلب) / **قابل للتشغيل** (ضمن سقف التزامن والموارد)
/ **متزامن فعلًا** (يعمل الآن معًا — يُقاس بعداد حي لا يُحسب). الموجات جدولة
مشروعة؛ إنشاء كائنات فارغة ليس أسطولًا: كل عامل حلقة R-753 تستدعي أدوات فعلًا.
"""

import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


@pytest.fixture
def ledger(monkeypatch):
    import memory.core as core_mod

    class FC:
        def __init__(self):
            self.events, self.fail = [], False
            self.lock = threading.Lock()

        def append_event(self, t, p, user=None):
            if self.fail:
                raise RuntimeError("R-635: No active signing key available")
            with self.lock:
                self.events.append((str(t), p))
    fc = FC()
    monkeypatch.setattr(core_mod, "get_core", lambda: fc)
    return fc


def _registry(flaky=None):
    from tool_registry import ToolRegistry, ToolSpec
    r = ToolRegistry()
    flaky = flaky if flaky is not None else {}
    lock = threading.Lock()

    def work(n, ms=5):
        time.sleep(int(ms) / 1000.0)                      # عبء I/O حقيقي (انتظار)
        return {"n": int(n), "sq": int(n) * int(n)}

    def sometimes(n):
        with lock:
            left = flaky.get(int(n), 0)
            if left > 0:
                flaky[int(n)] = left - 1
                raise ConnectionError(f"عطل مُفتعل للعامل {n}")
        return {"n": int(n)}
    r.register(ToolSpec(name="work", description="", inputs={"n": "", "ms": ""},
                        outputs="", handler=work))
    r.register(ToolSpec(name="sometimes", description="", inputs={"n": ""},
                        outputs="", handler=sometimes))
    return r


def _part(i, tool="work", ms=5):
    inputs = {"n": i, "ms": ms} if tool == "work" else {"n": i}
    return {"role": f"w{i}", "goal": f"جزء {i}", "planner": {"kind": "scripted", "steps": [
        {"action": "call", "tool": tool, "inputs": inputs,
         "check": {"type": "key_equals", "key": "n", "value": i}},
        {"action": "finish", "answer": i}]}}


def test_worker_runs_stops_and_delivers_with_trace(ledger):
    from fleet import Worker
    w = Worker("w1", _part(7)["goal"], _part(7)["planner"], registry=_registry())
    res = w.run()
    assert res["status"] == "completed" and res["answer"] == 7
    ops = [e[1]["op"] for e in ledger.events if e[0] == "fleet_event"]
    assert ops == ["worker.spawn", "worker.result"]


def test_worker_stop_cancels_cleanly(ledger):
    from fleet import Worker
    steps = [{"action": "call", "tool": "work", "inputs": {"n": i, "ms": 30},
              "check": {"type": "ok"}} for i in range(50)]
    w = Worker("slow", "g", {"kind": "scripted", "steps": steps}, registry=_registry())
    t = threading.Thread(target=w.run)
    t.start()
    time.sleep(0.1)
    w.stop(by="owner")
    t.join(5)
    assert not t.is_alive() and w.result["status"] == "cancelled"
    assert any(e[1]["op"] == "worker.stop" for e in ledger.events if e[0] == "fleet_event")


def test_coordinator_distributes_and_aggregates(ledger):
    from fleet import FleetCoordinator
    fc = FleetCoordinator(_registry(), max_concurrency=4)
    rep = fc.run([_part(i) for i in range(12)])
    assert rep["registered"] == 12 and rep["completed"] == 12 and rep["failed"] == []
    assert sorted(r["answer"] for r in rep["results"]) == list(range(12))
    assert 1 <= rep["measured_peak_concurrency"] <= 4


def test_failed_worker_rescheduled_and_reported_honestly(ledger):
    from fleet import FleetCoordinator
    flaky = {3: 1, 5: 5}                  # 3 يفشل مرة ثم ينجح؛ 5 يفشل دائمًا
    fc = FleetCoordinator(_registry(flaky), max_concurrency=3, max_retries=2)
    rep = fc.run([_part(i, tool="sometimes") for i in range(8)])
    assert rep["completed"] == 7
    assert [f["role"] for f in rep["failed"]] == ["w5"]
    assert rep["failed"][0]["attempts"] == 3
    assert rep["retried"]["w3"] == 1
    assert rep["status"] == "partial"                    # لا ادعاء اكتمال كامل


def test_ledger_unavailable_blocks_spawn(ledger):
    from fleet import FleetCoordinator
    ledger.fail = True
    rep = FleetCoordinator(_registry(), max_concurrency=2).run([_part(i) for i in range(3)])
    assert rep["completed"] == 0 and rep["status"] == "blocked"


def test_concurrency_is_measured_not_assumed(ledger):
    """التزامن الفعلي يُقاس بعداد حي: بسقف 10 وعبء 50ms → الذروة المقيسة 10."""
    from fleet import FleetCoordinator
    rep = FleetCoordinator(_registry(), max_concurrency=10).run(
        [_part(i, ms=50) for i in range(30)])
    assert rep["measured_peak_concurrency"] == 10
    assert rep["waves_min"] == 3


@pytest.mark.parametrize("n,cap", [(10, 10), (100, 50)])
def test_scale_measurement_report(ledger, n, cap):
    from fleet import measure_scale
    rep = measure_scale(n, max_concurrency=cap, work_ms=20, registry=_registry())
    assert rep["registered"] == n and rep["completed"] == n
    assert rep["measured_peak_concurrency"] <= cap
    for k in ("wall_s", "rss_mb_peak", "cpu_count", "mem_total_mb",
              "failures", "throughput_per_s", "environment"):
        assert k in rep


def test_fleet_spawn_tool_registered_and_inventory_moves():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        tools = {t["name"]: t for t in client.get("/tools/list").json()["tools"]}
        assert "fleet.spawn" in tools
        caps = {c["id"]: c for c in client.get("/capabilities").json()["capabilities"]}
        assert caps["agent_fleet"]["level"] != "missing"


def test_scale_report_cli_measures_real_runs(tmp_path):
    """٥.٣: الأداة تُشغَّل كعملية مستقلة وتكتب أرقامًا مقيسة لا مفترضة."""
    import json
    import subprocess
    out = tmp_path / "scale.json"
    proc = subprocess.run([sys.executable, str(REPO_ROOT / "tools" / "fleet_scale_report.py"),
                           str(out)], cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout[-500:] + proc.stderr[-500:]
    doc = json.loads(out.read_text(encoding="utf-8"))
    runs = doc["runs"]
    assert [r["registered"] for r in runs] == [10, 100, 1000, 1000, 1000, 1000]
    assert all(r["completed"] == r["registered"] for r in runs)
    assert all(r["measured_peak_concurrency"] <= r["runnable_concurrency_cap"] for r in runs)
    assert runs[-1]["measured_peak_concurrency"] > 100      # تزامن فعلي واسع مقيس
    assert doc["limits"] and "Fly" in " ".join(doc["limits"])
