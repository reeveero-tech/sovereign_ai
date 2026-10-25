"""R-762 — إنتاجية كتابة السجل السيادي وعدم حجب حلقة الأحداث.

الحادثة الحية (2026-10-25، بعد R-761): فور تفعيل مفتاح Ed25519 على الإنتاج
صارت ~20 حلقة خلفية تُلحق أحداثًا موقّعة فعلًا (كانت قبلها تُرفض fail-closed).
كل إلحاق كان يعيد كتابة index.json كاملًا (indent=2) → كلفة O(n) لكل حدث،
فتشبّعت وحدة المعالجة المشتركة وتوقف /health عن الاستجابة. و/ledger/verify
كان `async def` يتحقق من كل توقيع متزامنًا داخل حلقة uvicorn فيحجب كل الطلبات.

هذه الاختبارات تثبت:
1) الفهرس لا يُحفظ عند كل حدث (خنق زمني قابل للضبط)، ويُفرّغ صراحة عند flush.
2) فهرس متأخر عن السجل (انقطاع قبل flush) يُعاد بناؤه عند الإقلاع — لا فقد.
3) /ledger/verify دالة متزامنة (تُنفَّذ في مجمّع الخيوط لا في الحلقة)،
   والطلبات المتزامنة تتشارك حسابًا واحدًا (single-flight) بدل التراكم.
"""

import inspect
import json
import shutil
import tempfile
import threading
import time
from pathlib import Path

from backend.memory.core import SovereignCore, SovereignIndex
from backend.sovereign.keys import KeyRing


def _fresh_core(tmp: Path) -> SovereignCore:
    kr = KeyRing(keys_dir=tmp / "keys")
    kr.load_from_disk()
    kr.generate_new_ed25519_key(reason="R-762 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    return SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr,
    )


def test_index_not_rewritten_on_every_append(monkeypatch):
    """200 إلحاق ضمن نافذة الخنق ⇒ حفظات الفهرس أقل بكثير من 200."""
    monkeypatch.setenv("SOVEREIGN_INDEX_SAVE_INTERVAL", "60")
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _fresh_core(tmp)
        saves = []
        orig = SovereignIndex.save

        def counting_save(self):
            saves.append(1)
            return orig(self)

        monkeypatch.setattr(SovereignIndex, "save", counting_save)
        for i in range(200):
            core.append_event("test::r762", {"i": i})
        assert len(saves) <= 2, f"index saved {len(saves)} times for 200 appends"
        # الذاكرة متسقة دائمًا رغم الخنق
        assert core.index.data["events_count"] == sum(1 for _ in open(core.log_file))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_flush_persists_pending_index(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_INDEX_SAVE_INTERVAL", "60")
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _fresh_core(tmp)
        for i in range(25):
            core.append_event("test::r762", {"i": i})
        core.index.flush()
        on_disk = json.loads(core.index.index_file.read_text(encoding="utf-8"))
        assert on_disk["events_count"] == sum(1 for _ in open(core.log_file))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_stale_index_rebuilt_on_startup(monkeypatch):
    """فهرس على القرص أقدم من السجل (انقطاع قبل flush) ⇒ إعادة بناء عند الإقلاع."""
    monkeypatch.setenv("SOVEREIGN_INDEX_SAVE_INTERVAL", "0")
    tmp = Path(tempfile.mkdtemp())
    try:
        core = _fresh_core(tmp)
        for i in range(10):
            core.append_event("test::r762", {"i": i})
        idx = core.index.index_file
        stale = json.loads(idx.read_text(encoding="utf-8"))
        stale["events_count"] = 3  # محاكاة فهرس لم يُفرَّغ
        idx.write_text(json.dumps(stale), encoding="utf-8")
        ledger_count = sum(1 for _ in open(core.log_file))
        reopened = SovereignCore(
            log_file=core.log_file, blobs_dir=core.blob_store.blobs_dir,
            index_file=idx, meta_file=core.meta_file,
            integrity_file=core.integrity_file, keyring=core._keyring,
        )
        assert reopened.index.data["events_count"] == ledger_count
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_ledger_verify_is_sync_and_single_flight(monkeypatch):
    import app as app_module

    assert not inspect.iscoroutinefunction(app_module.ledger_verify), (
        "/ledger/verify must be a sync def (threadpool), not async (blocks the event loop)"
    )
    calls = []

    def slow_compute():
        calls.append(1)
        time.sleep(0.3)
        return {"ok": True, "n": len(calls)}

    monkeypatch.setattr(app_module, "_ledger_verify_compute", slow_compute)
    results = []
    threads = [threading.Thread(target=lambda: results.append(app_module.ledger_verify()))
               for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(5)
    assert len(results) == 5 and all(r["ok"] for r in results)
    assert len(calls) == 1, f"compute ran {len(calls)} times for 5 concurrent calls"
