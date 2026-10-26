"""R-777 (ROADMAP_V6 ٦.١.٢) — `simulation_history_list` محدود.

الدليل: قياس gc محلي بعد إصلاح مؤشر التكامل — `SimulationTrajectory` +3,710 بين 240ث و600ث
ولا تنقص. كل `SimulationSnapshot` يحمل دفعة بمساراتها كاملة، والقائمة لا قارئ لها ولا سقف،
بينما `simulation_history` المجاورة مقصوصة إلى 10.
"""
from backend.predictive.predictive_simulation import get_predictive_simulation


def test_simulation_snapshots_are_bounded():
    sim = get_predictive_simulation()
    for _ in range(25):
        sim.simulation_cycle(runs=3, steps=2)
    assert len(sim.simulation_history_list) <= 10, len(sim.simulation_history_list)
    assert len(sim.simulation_history) <= 10
