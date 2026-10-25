"""R-763 — متانة السجل السيادي عند توقف الآلة (حادثة إنتاج حية 2026-10-25).

بعد نشر R-762 ظهر في سجل الإنتاج سطر من 2059 بايت NUL (كتابة ممزقة: أُوقفت الآلة
قبل وصول الصفحات المتسخة إلى القرص — الإلحاق بلا fsync، و`auto_stop_machines`
مفعّل)، وفُقدت ~4 أحداث، ثم انكسرت السلسلة: `_load_last_hash` يستسلم عند أول سطر
تالف ويرجع إلى الميتا التي كانت تشير إلى حدث مفقود.

هذه الاختبارات تثبت:
1) سطر السجل وملف blob يُثبَّتان بـfsync، وسطر السجل قبل كتابة الميتا.
2) سطر تالف (NUL) لا يُسقط آخر تجزئة إلى الميتا — آخر حدث سليم في السجل هو الحقيقة،
   والسطر التالف يبقى كما هو (إلحاقي — لا حذف).
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import backend.memory.core as core_mod
from backend.memory.core import SovereignCore
from backend.sovereign.keys import KeyRing


def _fresh_core(tmp: Path) -> SovereignCore:
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-763 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    return SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr,
    )


def _fd_path(fd: int) -> str:
    try:
        return os.readlink(f"/proc/self/fd/{fd}")
    except OSError:
        return f"fd:{fd}"


def test_ledger_line_fsynced_before_meta(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _fresh_core(tmp)
        seq = []
        real_fsync = os.fsync

        def rec_fsync(fd):
            seq.append(("fsync", _fd_path(fd)))
            return real_fsync(fd)

        monkeypatch.setattr(core_mod.os, "fsync", rec_fsync)
        real_meta = core._save_meta
        monkeypatch.setattr(core, "_save_meta", lambda: (seq.append(("meta", "")), real_meta())[1])
        core.append_event("test::r763", {"n": 1})
        ledger = str(core.log_file)
        ledger_sync = [i for i, (k, p) in enumerate(seq) if k == "fsync" and p == ledger]
        meta_at = [i for i, (k, _) in enumerate(seq) if k == "meta"]
        assert ledger_sync, f"ledger never fsynced: {seq}"
        assert meta_at and ledger_sync[0] < meta_at[0], f"meta written before ledger fsync: {seq}"
        blob_dir = str(core.blob_store.blobs_dir)
        assert any(k == "fsync" and p.startswith(blob_dir) for k, p in seq), f"blob not fsynced: {seq}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_torn_nul_line_does_not_fall_back_to_meta():
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _fresh_core(tmp)
        for i in range(5):
            core.append_event("test::r763", {"n": i})
        last_valid = core._last_hash
        with open(core.log_file, "ab") as f:
            f.write(b"\x00" * 2059 + b"\n")  # ما وُجد حرفيًا على الإنتاج
        meta = json.loads(core.meta_file.read_text(encoding="utf-8"))
        meta["last_hash"] = "f" * 64  # ميتا تشير إلى حدث مفقود
        core.meta_file.write_text(json.dumps(meta), encoding="utf-8")
        size_before = core.log_file.stat().st_size

        reopened = SovereignCore(
            log_file=core.log_file, blobs_dir=core.blob_store.blobs_dir,
            index_file=core.index.index_file, meta_file=core.meta_file,
            integrity_file=core.integrity_file, keyring=core._keyring,
        )
        assert reopened._last_hash == last_valid
        # السطر التالف لم يُحذف (إلحاقي فقط)
        assert core.log_file.stat().st_size == size_before
        ev = reopened.append_event("test::r763", {"after": "torn"})
        assert ev["prev_hash"] == last_valid
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_torn_line_does_not_force_rebuild_every_boot(monkeypatch):
    """بعد إعادة بناء واحدة تشمل السطر التالف لا يُعاد البناء مع كل إقلاع."""
    monkeypatch.setenv("SOVEREIGN_INDEX_SAVE_INTERVAL", "0")
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _fresh_core(tmp)
        for i in range(3):
            core.append_event("test::r763", {"n": i})
        with open(core.log_file, "ab") as f:
            f.write(b"\x00" * 64 + b"\n")
        kw = dict(log_file=core.log_file, blobs_dir=core.blob_store.blobs_dir,
                  index_file=core.index.index_file, meta_file=core.meta_file,
                  integrity_file=core.integrity_file, keyring=core._keyring)
        SovereignCore(**kw)  # إقلاع أول: إعادة بناء مبررة
        rebuilds = []
        orig = SovereignCore._rebuild_index
        monkeypatch.setattr(SovereignCore, "_rebuild_index",
                            lambda self: (rebuilds.append(1), orig(self))[1])
        SovereignCore(**kw)  # إقلاع ثانٍ: لا إعادة بناء
        assert rebuilds == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
