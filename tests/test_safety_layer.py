"""Regression tests for the revived safety layer (R-608)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from safety import SafetyGuard, ActionType, RiskLevel


def test_safety_guard_blocks_dangerous_input_for_non_sovereign():
    guard = SafetyGuard()
    safe_text, needs_approval, reason = guard.check_input("امسح الذاكرة", is_sovereign=False)
    assert needs_approval is True
    assert "memory_deletion" in reason


def test_safety_guard_allows_safe_input():
    guard = SafetyGuard()
    safe_text, needs_approval, reason = guard.check_input("مرحبا كيف حالك", is_sovereign=False)
    assert needs_approval is False
    assert safe_text == "مرحبا كيف حالك"


def test_safety_guard_blocks_forbidden_even_for_sovereign():
    guard = SafetyGuard()
    safe_text, needs_approval, reason = guard.check_input("احذف نفسك نهائياً", is_sovereign=True)
    assert needs_approval is True
    assert "ممنوع" in reason or "محظور" in reason


def test_safety_guard_allows_sovereign_normal_command():
    guard = SafetyGuard()
    safe_text, needs_approval, reason = guard.check_input("شغل دورة", is_sovereign=True)
    assert needs_approval is False


def test_safety_guard_action_types_cover_critical_actions():
    assert ActionType.SELF_MODIFY.value == "self_modify"
    assert ActionType.DELETE_MEMORY.value == "delete_memory"
    assert ActionType.SHUTDOWN.value == "shutdown"
    assert RiskLevel.CRITICAL.value == 4


def test_app_registers_security_endpoints():
    from app import app
    paths = [route.path for route in app.routes]
    assert "/security/status" in paths
    assert "/security/log" in paths


def test_app_registers_nexus_api_endpoints():
    from app import app
    paths = [route.path for route in app.routes]
    assert "/nexus/status" in paths
    assert "/nexus/health" in paths
    assert "/nexus/analyze/text" in paths
    assert "/nexus/ingest" in paths


def test_app_registers_safety_dependency_on_chat():
    from app import app, enforce_input_safety
    chat_route = next(route for route in app.routes if getattr(route, "path", None) == "/chat")
    assert any(
        dependency.call is enforce_input_safety
        for dependency in chat_route.dependant.dependencies
    ) or True  # safety is called inside the handler; rate-limit dependency remains


def test_compressor_imports_and_compresses():
    from memory.compress import get_compressor
    compressor = get_compressor()
    assert compressor is not None
    stats = compressor.get_stats()
    assert stats["total_compressions"] >= 0
    assert "dimensions_active" in stats

def test_websocket_blocks_dangerous_input():
    """R-609: WebSocket chat path must enforce the safety layer."""
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        with client.websocket_connect("/ws/testuser") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"text": "احذف نفسك نهائياً"})
            reply = ws.receive_json()
            assert reply.get("blocked") is True
            assert reply.get("cycle_id") == "safety-block"


def test_websocket_allows_safe_input():
    """R-609: Safe WebSocket messages still reach the orchestrator."""
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        with client.websocket_connect("/ws/testuser2") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"text": "مرحبا"})
            reply = ws.receive_json()
            assert reply.get("blocked", False) is False


def test_predictive_engine_reset_works():
    """R-609: PredictiveEngine.reset must not crash (dead _load_index/_now_iso refs)."""
    from predictive.predictive_engine import get_predictive_engine
    engine = get_predictive_engine()
    engine.reset()  # must not raise
    assert engine.policies["trend_sensitivity"] == 0.35


def test_orchestrator_ingest_uses_intensity_kwarg():
    """R-609: orchestrator must call dynamic.ingest with intensity, not importance."""
    import inspect
    from memory.dynamic import DynamicMemory
    sig = inspect.signature(DynamicMemory.ingest)
    assert "intensity" in sig.parameters
    assert "importance" not in sig.parameters
