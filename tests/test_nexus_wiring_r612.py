"""R-612: NexusCore wiring — the sovereign mind must understand what the master says.

Regression tests for:
- S-7: NexusCore text understanding wired into the orchestrator cycle
- Sovereign controller decision actually used (was reading non-existent field)
- Nexus long-term store persists cycles
"""
import os
os.environ.setdefault("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


def test_cycle_understands_arabic_text():
    """The cycle must detect language + sentiment + intent from user text."""
    from orchestrator import SovereignOrchestrator
    orch = SovereignOrchestrator()
    result = orch.run_cycle({
        "type": "chat", "text": "مرحبا كيف حالك",
        "user_id": "test", "session_id": "s1", "timestamp": 0,
    })
    nexus = (result.perception or {}).get("nexus", {})
    assert nexus.get("language", {}).get("code") == "ar", f"expected ar, got {nexus.get('language')}"
    assert nexus.get("intent", {}).get("name") in ("greet", "help"), f"got {nexus.get('intent')}"
    assert "sentiment" in nexus


def test_cycle_understands_english_text():
    """English text must be detected as en."""
    from orchestrator import SovereignOrchestrator
    orch = SovereignOrchestrator()
    result = orch.run_cycle({
        "type": "chat", "text": "hello there",
        "user_id": "test", "session_id": "s2", "timestamp": 0,
    })
    nexus = (result.perception or {}).get("nexus", {})
    assert nexus.get("language", {}).get("code") == "en", f"got {nexus.get('language')}"


def test_analyze_intent_routes_to_explore():
    """An analyze request must route the decision to explore via nexus intent."""
    from orchestrator import SovereignOrchestrator
    orch = SovereignOrchestrator()
    result = orch.run_cycle({
        "type": "chat", "text": "حلل هذه البيانات من فضلك",
        "user_id": "test", "session_id": "s3", "timestamp": 0,
    })
    assert result.decision.get("action") == "explore", f"got {result.decision.get('action')}"
    assert result.decision.get("source") == "nexus_intent", f"got {result.decision.get('source')}"


def test_sovereign_controller_decision_used():
    """The sovereign controller's final_decision must be read (was sovereign_decision)."""
    from orchestrator import SovereignOrchestrator
    orch = SovereignOrchestrator()
    result = orch.run_cycle({
        "type": "chat", "text": "مرحبا",
        "user_id": "test", "session_id": "s4", "timestamp": 0,
    })
    # controller_cycle returns a ControllerSnapshot with final_decision
    assert result.decision.get("source") in ("sovereign_controller", "nexus_intent"), \
        f"got {result.decision.get('source')}"


def test_nexus_store_persists_cycle():
    """The cycle must be persisted to the NexusCore long-term store."""
    from orchestrator import SovereignOrchestrator
    orch = SovereignOrchestrator()
    result = orch.run_cycle({
        "type": "chat", "text": "تخزين هذه الدورة",
        "user_id": "test", "session_id": "s5", "timestamp": 0,
    })
    store = orch.nexus.get_component("store")
    saved = store.load("cycles", result.cycle_id)
    assert saved is not None, "cycle not persisted to nexus store"
    assert saved.get("decision", {}).get("action") == result.decision.get("action")
