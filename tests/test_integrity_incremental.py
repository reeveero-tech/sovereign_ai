"""R-768 — `verify_integrity` لا يعيد فحص السجل كله في كل استدعاء (حادثة إنتاج حية).

بعد R-766 عادت المكونات (الدوافع، الغرائز، المراقب) فصار المعالج مشبعًا: steal ≈91%
على shared-cpu-1x، و100% من نواة مخصصة. py-spy على الآلة: ~80% من العينات في
`verify_hex` ← `verify_integrity` ← `drives.update_survival_drive` وغيرها. السبب:
(١) نتيجة غير VERIFIED (هنا CORRUPTED بسبب سطر الكتابة الممزقة) لا تُخزَّن أبدًا، فكل
استدعاء يتحقق من كل التوقيعات؛ (٢) حتى VERIFIED يُعاد فحصه كاملًا كل 60ث — O(n) ينمو
مع السجل بلا حد.
المطلوب: كل نتيجة تُخزَّن للمهلة؛ وبعدها يُستأنف التحقق من آخر موضع متحقق منه ما دامت
بصمة البادئة (sha256) والمفاتيح لم تتغير — وأي تعديل في البادئة يفرض فحصًا كاملًا؛ و
`verbose=True` فحص كامل دائمًا.
"""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

import backend.sovereign.keys.ed25519_verifier as ed
from backend.memory.core import IntegrityStatus, SovereignCore
from backend.sovereign.keys import KeyRing


@pytest.fixture
def env(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-768 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    calls = {"n": 0}
    real = ed.verify_hex

    def counting(*a, **kw):
        calls["n"] += 1
        return real(*a, **kw)
    monkeypatch.setattr(ed, "verify_hex", counting)

    def mk():
        return SovereignCore(
            log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
            index_file=sc / "index.json", meta_file=sc / "meta.json",
            integrity_file=sc / "integrity.json", keyring=kr)
    yield mk, calls, sc / "ledger.jsonl"
    shutil.rmtree(tmp, ignore_errors=True)


def _expire(core):
    core._integrity_cache["ts"] -= 61.0


def test_corrupted_result_is_cached_within_ttl(env):
    mk, calls, log = env
    core = mk()
    core.append_event("test::r768", {"n": 1})
    core.append_event("test::r768", {"n": 2})
    with open(log, "ab") as f:
        f.write(b"\x00" * 2059 + b"\n")
    core = mk()
    assert core.verify_integrity() == IntegrityStatus.CORRUPTED
    calls["n"] = 0
    for _ in range(5):
        assert core.verify_integrity() == IntegrityStatus.CORRUPTED
    assert calls["n"] == 0, f"أعاد التحقق {calls['n']} توقيعًا داخل المهلة"


def test_unchanged_corrupted_prefix_not_reverified_after_ttl(env):
    mk, calls, log = env
    core = mk()
    core.append_event("test::r768", {"n": 1})
    core.append_event("test::r768", {"n": 2})
    with open(log, "ab") as f:
        f.write(b"\x00" * 2059 + b"\n")
    core = mk()
    core.append_event("test::r768", {"n": 3})
    assert core.verify_integrity() == IntegrityStatus.CORRUPTED
    calls["n"] = 0
    _expire(core)
    assert core.verify_integrity() == IntegrityStatus.CORRUPTED
    assert calls["n"] == 0


def test_after_ttl_only_new_events_are_verified(env):
    mk, calls, _ = env
    core = mk()
    for i in range(5):
        core.append_event("test::r768", {"n": i})
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    core.append_event("test::r768", {"n": 5})
    core.append_event("test::r768", {"n": 6})
    calls["n"] = 0
    _expire(core)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    assert calls["n"] == 2, f"تحقق من {calls['n']} توقيعًا بدل الحدثين الجديدين"


def test_prefix_tamper_forces_full_check(env):
    mk, calls, log = env
    core = mk()
    for i in range(4):
        core.append_event("test::r768", {"n": i})
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    lines = log.read_text(encoding="utf-8").splitlines()
    ev = json.loads(lines[1])
    ev["type"] = "tampered"
    lines[1] = json.dumps(ev, ensure_ascii=False)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    core.append_event("test::r768", {"n": 4})
    _expire(core)
    assert core.verify_integrity() == IntegrityStatus.CORRUPTED


def test_verbose_is_always_a_full_check(env):
    mk, calls, _ = env
    core = mk()
    for i in range(3):
        core.append_event("test::r768", {"n": i})
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    calls["n"] = 0
    assert core.verify_integrity(verbose=True) == IntegrityStatus.VERIFIED
    assert calls["n"] == 3


def test_partial_tail_failure_is_not_frozen(env):
    """حارس: سطر أخير بلا \\n (كاتب في منتصف الإلحاق) يُحكم عليه ولا يُبصم — حين يكتمل
    يُرى سليمًا بعد المهلة، لا CORRUPTED مجمدًا."""
    mk, calls, log = env
    core = mk()
    for i in range(3):
        core.append_event("test::r768", {"n": i})
    full = log.read_bytes()
    log.write_bytes(full[:-15])
    assert core.verify_integrity() == IntegrityStatus.CORRUPTED
    log.write_bytes(full)
    _expire(core)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
