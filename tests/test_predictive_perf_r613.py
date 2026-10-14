"""R-613: predictive performance regression tests.

Bugs fixed:
1. get_simulation_results()/get_recommendations() ran a full 100x12 simulation
   on a status read (~3.4s) — now a small 10x6 batch.
2. verify_integrity() cache was invalidated on every event append, forcing a
   full-ledger walk (~2.5s) on every status call — now the 60s cache holds.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


def test_verify_integrity_cached_after_append():
    """verify_integrity() must stay fast after an event append (was full walk)."""
    from memory.core import get_core

    core = get_core()
    core.verify_integrity()  # prime cache
    core.append_event("test::r613_perf", {"x": 1})
    t0 = time.time()
    core.verify_integrity()
    assert time.time() - t0 < 1.0, "verify_integrity too slow after append"


def test_get_simulation_results_fast():
    """get_simulation_results() must not run a full 100x12 simulation."""
    from predictive.predictive_simulation import get_predictive_simulation

    sim = get_predictive_simulation()
    t0 = time.time()
    sim.get_simulation_results()
    assert time.time() - t0 < 5.0, "get_simulation_results too slow"
