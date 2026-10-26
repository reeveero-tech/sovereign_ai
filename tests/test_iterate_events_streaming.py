"""R-775 (ROADMAP_V6 ٦.١.٢) — قراءة السجل الأمامية بحد تتدفق ولا تحمّل السجل كله.

الدليل (2026-10-26): الإنتاج قُتل OOM عند 02:48:41Z (RSS ~720MB من 1024MB قبلها). py-spy
محليًا على سجل 46,511 حدثًا: 38% من العينات في `gather_conscious_inputs` ← `iterate_events`
(`json.loads` لكل سطر). السبب: `iterate_events(limit=N)` بلا `reverse` كان يحلل **كل** أسطر
السجل إلى قائمة (عشرات MB مؤقتة لكل نداء) ثم يأخذ أول N؛ و16 موضعًا يناديه هكذا دوريًا.
ووعي «آخر حدث» في field.py كان يقرأ **أقدم** حدث (`limit=5` بلا `reverse`).

العقد المحفوظ: النتيجة نفسها والترتيب نفسه (الأقدم أولًا) — فقط بلا تحميل السجل.
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from backend.memory.core import SovereignCore
from backend.sovereign.keys import KeyRing

N = 300


@pytest.fixture
def core(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TELEMETRY_MIN_INTERVAL_SECONDS", "0")
    tmp = Path(tempfile.mkdtemp())
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-775 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    c = SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr)
    for i in range(N):
        c.append_event("test::r775", {"i": i})
    yield c
    shutil.rmtree(tmp, ignore_errors=True)


def _count_parses(core, monkeypatch):
    calls = [0]
    orig = SovereignCore._parse_ledger_line

    def counting(line):
        calls[0] += 1
        return orig(line)

    monkeypatch.setattr(SovereignCore, "_parse_ledger_line", staticmethod(counting))
    return calls


def _all_hashes(core):
    return [l.split('"hash": "', 1)[1][:64] for l in core.log_file.read_text().splitlines() if l.strip()]


def test_forward_limit_parses_only_what_it_returns(core, monkeypatch):
    calls = _count_parses(core, monkeypatch)
    got = list(core.iterate_events(limit=5))
    assert len(got) == 5
    assert calls[0] <= 5, f"حلّل {calls[0]} سطرًا لإرجاع 5 — يحمّل السجل كله"


def test_forward_limit_contract_unchanged_oldest_first_in_order(core):
    allh = _all_hashes(core)
    assert [e["hash"] for e in core.iterate_events(limit=7)] == allh[:7]
    assert [e["hash"] for e in core.iterate_events()] == allh


def test_forward_from_hash_streams_and_keeps_contract(core, monkeypatch):
    allh = _all_hashes(core)
    calls = _count_parses(core, monkeypatch)
    got = [e["hash"] for e in core.iterate_events(from_hash=allh[10], limit=3)]
    assert got == allh[11:14]
    assert calls[0] <= 14


def test_forward_iteration_is_a_snapshot_of_the_ledger_at_call_time(core):
    it = core.iterate_events()
    first = next(it)
    core.append_event("test::r775_late", {"late": True})
    rest = list(it)
    assert 1 + len(rest) == N
    assert all(e["type"] != "test::r775_late" for e in [first, *rest])


def test_corrupt_line_is_skipped_while_streaming(core):
    with open(core.log_file, "a", encoding="utf-8") as f:
        f.write("{partial-write\n")
    core.append_event("test::r775", {"i": "after"})
    assert len(list(core.iterate_events())) == N + 1


def test_consciousness_attention_focus_reads_the_latest_event(core, monkeypatch):
    from consciousness.field import ConsciousnessFieldEngine

    class Stub:
        def __getattr__(self, name):
            return lambda *a, **k: {}

    eng = ConsciousnessFieldEngine.__new__(ConsciousnessFieldEngine)
    for a in ("dynamic", "instincts", "drives", "archetypes", "watcher"):
        setattr(eng, a, Stub())
    eng.core = core
    core.append_event("test::r775_newest", {"newest": True})
    calls = _count_parses(core, monkeypatch)
    inputs = eng.gather_conscious_inputs()
    assert inputs["attention_focus"]["last_event_type"] == "test::r775_newest"
    assert calls[0] <= 50, f"حلّل {calls[0]} سطرًا لمعرفة آخر حدث"


def test_unknown_from_hash_falls_back_to_start_as_before(core):
    allh = _all_hashes(core)
    assert [e["hash"] for e in core.iterate_events(from_hash="0" * 64, limit=2)] == allh[:2]
