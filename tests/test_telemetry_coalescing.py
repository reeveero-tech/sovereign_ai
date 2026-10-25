"""R-771 — اللقطات الدورية تُدمج ولا تُغرق السجل (أصل حادثة R-770).

الإنتاج: 46,511 حدثًا خلال ~يوم، ~1 حدث/ث، معظمها لقطات حالة دورية لا يقرؤها أي كود
(`defense::full_mutation` كل ~0.3ث، `attention::snapshot`، `quantum::*`، `watcher::snapshot`...).
كل حدث موقّع + fsync + فهرس `by_hash` بلا حد ⇒ نمو بلا سقف في القرص والذاكرة.

السياسة: لكل نوع من `TELEMETRY_COALESCE_TYPES` حدث واحد على الأكثر كل
`SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS` (الافتراضي 300؛ 0 يعطّل). ما يُدمج لا يضيع
عدده: الحدث المكتوب التالي يحمل `_coalesced_since_last`. أي نوع خارج القائمة لا يتأثر.
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from backend.memory.core import SovereignCore, TELEMETRY_COALESCE_TYPES
from backend.sovereign.keys import KeyRing


@pytest.fixture
def core():
    tmp = Path(tempfile.mkdtemp())
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-771 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    c = SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr)
    yield c
    shutil.rmtree(tmp, ignore_errors=True)


def _types(core):
    return [e["type"] for e in core.iterate_events()]


def test_the_production_flooders_are_covered():
    for t in ("defense::full_mutation", "attention::snapshot", "quantum::transition_applied",
              "watcher::snapshot", "awareness::moment", "consciousness::moment"):
        assert t in TELEMETRY_COALESCE_TYPES


def test_periodic_snapshot_written_once_per_interval(core, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS", "300")
    for i in range(50):
        core.append_event("attention::snapshot", {"i": i})
    assert _types(core).count("attention::snapshot") == 1


def test_coalesced_count_is_carried_by_next_written_event(core, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS", "300")
    clock = [1000.0]
    monkeypatch.setattr("backend.memory.core.time.monotonic", lambda: clock[0])
    for i in range(10):
        core.append_event("watcher::snapshot", {"i": i})
    clock[0] += 301
    core.append_event("watcher::snapshot", {"i": 10})
    events = [e for e in core.iterate_events() if e["type"] == "watcher::snapshot"]
    assert len(events) == 2
    last = core.get_payload(events[-1])
    assert last["_coalesced_since_last"] == 9
    assert last["i"] == 10


def test_non_telemetry_events_never_coalesced(core, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS", "300")
    for i in range(5):
        core.append_event("chat::message", {"i": i})
    assert _types(core).count("chat::message") == 5


def test_interval_zero_disables_policy(core, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS", "0")
    for i in range(5):
        core.append_event("attention::snapshot", {"i": i})
    assert _types(core).count("attention::snapshot") == 5


def test_coalesced_call_returns_marker_not_hash(core, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS", "300")
    first = core.append_event("attention::snapshot", {"i": 0})
    second = core.append_event("attention::snapshot", {"i": 1})
    assert first.get("hash")
    assert second.get("coalesced") is True and second.get("hash") is None
