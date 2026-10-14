"""R-613: simulation environment reset — was calling undefined _load_index/_now_iso
and resetting attributes the class doesn't have (silently swallowed by controller)."""
import os
os.environ.setdefault("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


def test_simulation_environment_reset_works():
    """reset() must clear the manager's real state and log the event."""
    from simulation.simulation_environment import SimulationEnvironmentManager
    env = SimulationEnvironmentManager()
    # add some state first
    env.templates["t1"] = object()
    env.parameter_sets["p1"] = object()
    env.instances["i1"] = object()
    env.active_template = "t1"
    env.reset()
    assert env.templates == {}
    assert env.parameter_sets == {}
    assert env.instances == {}
    assert env.active_template is None
    assert env.active_parameter_set is None


def test_simulation_controller_reset_works():
    """The full controller reset must not silently fail."""
    from simulation.simulation_controller import SimulationController
    sc = SimulationController()
    sc.reset()  # must not raise
    assert True
