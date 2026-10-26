"""R-782 — كسر قفل السجل تحت الإشباع يشعّب السلسلة (حادثة إنتاج: 11 كسرًا).

الفحص على الإنتاج (قراءة فقط، `forensics/R-782_ledger_breaks.txt`): غير سطر NUL المعروف
(R-763) وجدنا 11 كسرًا في 80,552 حدثًا، كلها في نوافذ إشباع المعالج (2026-10-25 13:15–13:29
حادثة R-768، و23:32، و02:47 قبل OOM 02:48:41):
- 3 تشعبات: توقيع صحيح لكن `prev_hash` يشير إلى حدث قبل 2–5 أسطر (كاتبان بنفس آخر تجزئة).
- 8 أحداث تجزئتها وتوقيعها لا يطابقان حقولها، و`prev_hash` المخزّن صحيح: حُسبت التجزئة على
  `_last_hash` قديم ثم خُزّن `_last_hash` بعد أن غيّره خيط آخر (ثلاث قراءات منفصلة).
السبب: `FileLock` يعدّ القفل «قديمًا» بعد 30ث فيحذفه خيط منتظر والمالك حي، ثم `__exit__` المالك
يحذف قفل غيره — فيدخل ثالث. المطلوب: قفل داخل العملية قبل الملف (خيوطنا لا تتنافس على الملف
ولا يكسر بعضها قفل بعض)، تحرير القفل لمالكه فقط، لا كسر لقفل عملية حية، وقراءة واحدة لآخر تجزئة.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

import backend.memory.core as core_mod
from backend.memory.core import FileLock, IntegrityStatus, SovereignCore
from backend.sovereign.keys import KeyRing


@pytest.fixture
def env(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-782 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(core_mod, "LOCK_FILE", sc / ".lock")

    def mk():
        return SovereignCore(
            log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
            index_file=sc / "index.json", meta_file=sc / "meta.json",
            integrity_file=sc / "integrity.json", keyring=kr)
    yield mk, sc
    shutil.rmtree(tmp, ignore_errors=True)


def _chain_breaks(log: Path):
    prev, breaks = "GENESIS", []
    for i, raw in enumerate(log.read_bytes().splitlines(), 1):
        e = json.loads(raw)
        if e["prev_hash"] != prev:
            breaks.append(i)
        prev = e["hash"]
    return breaks


def test_slow_holder_lock_is_not_broken_by_waiting_threads(env, monkeypatch):
    """حامل بطيء (إشباع) أطول من مهلة «القِدم» — المنتظرون لا يدخلون معه."""
    mk, sc = env
    core = mk()
    monkeypatch.setattr(FileLock, "STALE_AFTER_SECONDS", 0.3)
    real_put = core.blob_store.put

    def slow_put(*a, **kw):
        time.sleep(0.8)
        return real_put(*a, **kw)
    monkeypatch.setattr(core.blob_store, "put", slow_put)
    errors = []

    def worker(n):
        try:
            for k in range(2):
                core.append_event("test::r782", {"w": n, "k": k})
        except Exception as e:  # pragma: no cover — يُفحص أدناه
            errors.append(repr(e))
    ts = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    assert not errors, errors
    assert _chain_breaks(sc / "ledger.jsonl") == []
    assert core.verify_integrity(verbose=True) == IntegrityStatus.VERIFIED


def test_exit_does_not_remove_a_lock_it_no_longer_owns(tmp_path):
    p = tmp_path / ".lock"
    lk = FileLock(p, timeout=1.0)
    lk.__enter__()
    p.unlink()  # كسره غيرنا…
    p.write_text("424242 someone-else\n")  # …وأخذه
    lk.__exit__(None, None, None)
    assert p.exists() and "someone-else" in p.read_text()
    p.unlink()


def test_lock_of_live_other_process_is_not_broken(tmp_path, monkeypatch):
    monkeypatch.setattr(FileLock, "STALE_AFTER_SECONDS", 0.1)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        p = tmp_path / ".lock"
        p.write_text(f"{proc.pid} other-token\n")
        old = time.time() - 120
        os.utime(p, (old, old))
        with pytest.raises(TimeoutError):
            with FileLock(p, timeout=0.6):
                pass
        assert f"{proc.pid}" in p.read_text()
    finally:
        proc.kill()
        proc.wait()


def test_lock_left_by_dead_or_previous_incarnation_is_reclaimed(tmp_path):
    p = tmp_path / ".lock"
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    for owner in (dead.pid, os.getpid()):  # نفس pid بعد إعادة تشغيل الحاوية = بقايا
        p.write_text(f"{owner} stale-token\n")
        t0 = time.time()
        with FileLock(p, timeout=5.0):
            assert str(os.getpid()) in p.read_text()
        assert time.time() - t0 < 1.0
        assert not p.exists()


def test_sixty_threads_append_without_ledger_blocked(env):
    """٦.١.٥: لا `ledger_blocked` (TimeoutError) تحت 60 خيطًا، والسلسلة سليمة."""
    mk, sc = env
    core = mk()
    errors = []

    def worker(n):
        try:
            for k in range(3):
                core.append_event("test::r782", {"w": n, "k": k})
        except Exception as e:  # pragma: no cover
            errors.append(repr(e))
    ts = [threading.Thread(target=worker, args=(n,)) for n in range(60)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(120)
    assert not errors, errors[:3]
    lines = (sc / "ledger.jsonl").read_bytes().splitlines()
    assert len(lines) == 180
    assert _chain_breaks(sc / "ledger.jsonl") == []
