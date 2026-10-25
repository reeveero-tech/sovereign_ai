"""R-769 — `verify_integrity` فحص واحد في وقت واحد (قطيع متزاحم حي بعد R-768).

بعد نشر R-768 بقي معالج الإنتاج مشبعًا (steal ≈91%)، وpy-spy أظهر `_verify_walk` من
`drives`/`watcher` معًا: عند الإقلاع لا ذاكرة بعد، فكل خيط يبدأ الفحص الكامل نفسه
بالتوازي، والفحص على معالج مخنوق يستغرق دقائق فتتراكم خيوط جديدة قبل أن يُخزَّن أي
نتيجة. المطلوب: خيط واحد يفحص، والبقية تنتظر وتأخذ النتيجة المخزنة.
"""
import shutil
import tempfile
import threading
import time
from pathlib import Path

import backend.sovereign.keys.ed25519_verifier as ed
from backend.memory.core import IntegrityStatus, SovereignCore
from backend.sovereign.keys import KeyRing


def test_concurrent_callers_share_one_walk(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    try:
        kr = KeyRing(keys_dir=tmp / "keys")
        kr.load_from_disk()
        kr.generate_new_ed25519_key(reason="R-769 test")
        kr.save_to_disk()
        sc = tmp / "sovereign_core"
        (sc / "blobs").mkdir(parents=True, exist_ok=True)
        core = SovereignCore(
            log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
            index_file=sc / "index.json", meta_file=sc / "meta.json",
            integrity_file=sc / "integrity.json", keyring=kr)
        for i in range(3):
            core.append_event("test::r769", {"n": i})
        calls = {"n": 0}
        lock = threading.Lock()
        real = ed.verify_hex

        def slow(*a, **kw):
            with lock:
                calls["n"] += 1
            time.sleep(0.05)  # معالج مخنوق
            return real(*a, **kw)
        monkeypatch.setattr(ed, "verify_hex", slow)

        start = threading.Barrier(6)
        results = []

        def caller():
            start.wait()
            results.append(core.verify_integrity())
        threads = [threading.Thread(target=caller) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        assert results == [IntegrityStatus.VERIFIED] * 6
        assert calls["n"] == 3, f"{calls['n']} تحقق توقيع لستة متصلين بدل فحص واحد (3)"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
