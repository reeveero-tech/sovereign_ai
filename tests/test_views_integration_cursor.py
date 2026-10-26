"""R-777 (ROADMAP_V6 ٦.١.٢) — خلفية تكامل الذاكرة لا تعيد معالجة الأحداث نفسها كل ثانية.

الدليل (2026-10-26، قياس محلي بـgc على سجل 46,511 حدثًا): 55,000 `SensoryItem` حية بينما
TTL الحسية 30ث ومعدل الأحداث الحقيقي أقل من حدث/ث. السبب في `_background_integration`:
يمشي الأحداث من الأحدث إلى الأقدم ويضع `last_hash = event.hash` لكل حدث، فينتهي المؤشر عند
**أقدم** حدث في الدفعة؛ الدورة التالية تعيد كل ما بعده — حسية + payload من القرص +
`procedural.execute` + `long_term.consolidate` — حتى 1000 حدث كل ثانية بلا نهاية.
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from backend.memory.core import SovereignCore
from backend.memory.views import MemoryViews
from backend.sovereign.keys import KeyRing


@pytest.fixture
def core(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS", "0")
    tmp = Path(tempfile.mkdtemp())
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-777 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    c = SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr)
    for i in range(10):
        c.append_event("test::old", {"i": i})
    yield c
    shutil.rmtree(tmp, ignore_errors=True)


class _Sensory:
    def __init__(self):
        self.added = []

    def add(self, event_hash, event_type, payload, user=None):
        self.added.append(event_hash)


class _Null:
    def __getattr__(self, name):
        return lambda *a, **k: None


class _Stop:
    """يسمح بعدد محدد من الدورات ثم يوقف الحلقة؛ بين الدورات ينفذ خطوة من السيناريو."""

    def __init__(self, steps):
        self.steps = list(steps)

    def is_set(self):
        return False

    def wait(self, _t):
        if not self.steps:
            return True
        self.steps.pop(0)()
        return False


def _views(core, steps):
    v = MemoryViews.__new__(MemoryViews)
    v.core = core
    v.sensory = _Sensory()
    v.working = _Null()
    v.procedural = _Null()
    v.long_term = _Null()
    v._bg_stop = _Stop(steps)
    return v


def test_each_new_event_is_integrated_exactly_once(core):
    new = []

    def burst(n):
        def f():
            for i in range(n):
                new.append(core.append_event("test::new", {"n": i})["hash"])
        return f

    # الدورة 1 بلا جديد؛ ثم 3 أحداث؛ ثم دورتان بلا جديد؛ ثم حدثان؛ ثم دورة بلا جديد.
    v = _views(core, [burst(3), lambda: None, lambda: None, burst(2), lambda: None])
    v._background_integration()
    assert sorted(v.sensory.added) == sorted(new), (
        f"{len(v.sensory.added)} إضافة لـ{len(new)} أحداث جديدة — مكررات: "
        f"{len(v.sensory.added) - len(set(v.sensory.added))}")


def test_integration_is_chronological_within_a_batch(core):
    new = []

    def burst():
        for i in range(4):
            new.append(core.append_event("test::new", {"n": i})["hash"])

    v = _views(core, [burst, lambda: None])
    v._background_integration()
    assert v.sensory.added == new  # الأقدم أولًا كما وقعت
