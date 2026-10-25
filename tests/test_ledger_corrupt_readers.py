"""R-766 — قرّاء السجل يتخطون السطر التالف (حادثة إنتاج حية 2026-10-25).

بعد R-765 أعلن `/health` على الإنتاج `degraded`: نحو 20 مكونًا (الوعي، الذاكرة
الديناميكية، ...) فشلت عند الإقلاع بـ«Expecting value: line 1 column 1». التتبع على
الآلة: `MemoryViews._load_from_core` → `SovereignCore.iterate_events` → `json.loads`
على سطر الكتابة الممزقة (NUL) المحفوظ شاهدًا منذ R-763. أصلح R-763 `_load_last_hash`
وإعادة بناء الفهرس لكنه فاته القرّاء: `iterate_events` (المساران) و`get_event`
و`get_event_by_sequence`. السياسة نفسها: السطر التالف يُتخطى ولا يُمس (إلحاقي).
"""
import shutil
import tempfile
from pathlib import Path

from backend.memory.core import SovereignCore
from backend.sovereign.keys import KeyRing


def _core_with_torn_line(tmp: Path):
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-766 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    mk = lambda: SovereignCore(  # noqa: E731
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr)
    core = mk()
    h1 = core.append_event("test::r766", {"n": 1})
    h2 = core.append_event("test::r766", {"n": 2})
    with open(sc / "ledger.jsonl", "ab") as f:  # كتابة ممزقة كما على الإنتاج
        f.write(b"\x00" * 2059 + b"\n")
    core = mk()  # إقلاع جديد فوق السطر التالف
    h3 = core.append_event("test::r766", {"n": 3})
    raw = (sc / "ledger.jsonl").read_bytes()
    return core, [h1, h2, h3], sc / "ledger.jsonl", raw


def _hash(h):
    return h if isinstance(h, str) else h.get("hash")


def test_iterate_events_skips_torn_line_both_paths():
    tmp = Path(tempfile.mkdtemp())
    try:
        core, hs, _, _ = _core_with_torn_line(tmp)
        fwd = [e["hash"] for e in core.iterate_events(reverse=False)]
        assert fwd == [_hash(h) for h in hs]
        rev = [e["hash"] for e in core.iterate_events(reverse=True)]
        assert rev == [_hash(h) for h in reversed(hs)]
        fast = [e["hash"] for e in core.iterate_events(reverse=True, limit=10)]
        assert fast == [_hash(h) for h in reversed(hs)]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_get_event_finds_event_after_torn_line():
    tmp = Path(tempfile.mkdtemp())
    try:
        core, hs, _, _ = _core_with_torn_line(tmp)
        assert core.get_event(_hash(hs[2]))["hash"] == _hash(hs[2])
        assert core.get_event("0" * 64) is None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_get_event_by_sequence_returns_none_on_torn_line():
    tmp = Path(tempfile.mkdtemp())
    try:
        core, hs, _, _ = _core_with_torn_line(tmp)
        assert core.get_event_by_sequence(0)["hash"] == _hash(hs[0])
        assert core.get_event_by_sequence(2) is None  # السطر التالف نفسه
        assert core.get_event_by_sequence(3)["hash"] == _hash(hs[2])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_readers_never_modify_the_torn_line():
    tmp = Path(tempfile.mkdtemp())
    try:
        core, hs, path, raw = _core_with_torn_line(tmp)
        list(core.iterate_events())
        list(core.iterate_events(reverse=True, limit=5))
        core.get_event(_hash(hs[2]))
        core.get_event_by_sequence(2)
        assert path.read_bytes() == raw and b"\x00" * 2059 in raw
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
