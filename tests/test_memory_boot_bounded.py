"""R-770 — إقلاع الذاكرة الحية محدود بسعتها (حادثة إنتاج حية 2026-10-25/26).

آلة الإنتاج (shared-cpu-1x، 512MB) قُتلت بنفاد الذاكرة (exit 137، oom_killed=true)
بعد نحو دقيقتين من كل إقلاع منذ 2026-10-25T17:18Z، فتوقف `/health` كليًا. القياس
على الآلة: السجل 46,511 حدثًا (23.7MB)، وRSS للعملية 238→323MB أثناء الإقلاع ثم القتل.
السبب: `MemoryViews._load_from_core` يمر على **كل** السجل (`iterate_events` كاملًا في
قائمة)، ويفك حمولة كل حدث، ويضع الحمولة الخام لكل حدث في الذاكرة الحسية بتوقيت
«الآن» فلا تتبدد قبل TTL — بينما الذاكرة الحدثية تحتفظ أصلًا بآخر `max_size` فقط.

الإصلاح يحفظ السلوك: يُحمَّل آخر `max_size` حدث فقط (ما كانت الحدثية ستبقيه حرفيًا)
بالترتيب نفسه، والحسية لا تُملأ إلا بما يقع زمنه الحقيقي داخل نافذة TTL. السجل نفسه لا يُمس.
"""
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.memory.core import SovereignCore
from backend.memory.views import (
    EpisodicMemoryStore, LongTermMemory, MemoryViews, SensoryMemory,
)
from backend.sovereign.keys import KeyRing


def _core(tmp: Path) -> SovereignCore:
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-770 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    return SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr)


def _views(core, cap: int) -> MemoryViews:
    """MemoryViews بلا مفرد عام وبسعة حدثية صغيرة (المسار نفسه: `_load_from_core`)."""
    mv = MemoryViews.__new__(MemoryViews)
    mv.core = core
    mv.sensory = SensoryMemory()
    mv.long_term = LongTermMemory()
    mv.long_term.episodic = EpisodicMemoryStore(max_size=cap)
    return mv


def _hash(h):
    return h if isinstance(h, str) else h.get("hash")


class _CountingCore:
    def __init__(self, core):
        self._core = core
        self.payload_calls = 0

    def __getattr__(self, name):
        return getattr(self._core, name)

    def get_payload(self, event):
        self.payload_calls += 1
        return self._core.get_payload(event)


def test_boot_decodes_at_most_episodic_capacity():
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _core(tmp)
        for i in range(20):
            core.append_event("test::r770", {"n": i})
        counting = _CountingCore(core)
        mv = _views(counting, cap=5)
        mv._load_from_core()
        assert counting.payload_calls <= 5, counting.payload_calls
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_boot_episodic_keeps_exactly_the_same_tail_in_order():
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _core(tmp)
        hs = [_hash(core.append_event("test::r770", {"n": i})) for i in range(20)]
        mv = _views(core, cap=5)
        mv._load_from_core()
        assert mv.long_term.episodic._timeline == hs[-5:]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_boot_does_not_flood_sensory_with_old_events():
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _core(tmp)
        for i in range(20):
            core.append_event("test::r770", {"n": i})
        mv = _views(core, cap=50)
        # أحداث السجل عمرها الحقيقي أقدم من نافذة الحسية: لا تُعاد «حاضرًا»
        old = (datetime.now(timezone.utc) - timedelta(seconds=mv.sensory._ttl + 60)).isoformat()
        real_iter = core.iterate_events

        def aged(*a, **kw):
            for e in real_iter(*a, **kw):
                yield {**e, "time": old}
        mv.core = _CountingCore(core)
        mv.core.iterate_events = aged
        mv._load_from_core()
        assert len(mv.sensory._items) == 0
        assert len(mv.long_term.episodic._timeline) == 20  # الحدثية كما هي
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_boot_sensory_keeps_genuinely_recent_events():
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _core(tmp)
        for i in range(3):
            core.append_event("test::r770", {"n": i})
        mv = _views(core, cap=50)
        mv._load_from_core()
        assert len(mv.sensory._items) == 3  # أحداث الآن داخل النافذة فعلًا
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
