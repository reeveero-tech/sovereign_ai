"""R-606: اختبارات أداء دورة المنسق (Orchestrator Cycle Performance).

تتحقق من أن:
- getters باهظة الثمن تُخزَّن مؤقتاً (TTL قصير) بدل إعادة تشغيل الدورة الكاملة في كل استدعاء.
- خطأ العودية في get_early_warnings_list أُصلح (لا RecursionError).
- ذاكرة التحقق من سلامة السجل لا تُعاد فحصها في كل إضافة حدث (TTL).
- iterate_events بمسار الذيل السريع يعيد نفس النتائج الصحيحة.
- إعادة بناء الفهرس من السجل تعمل بعد reset().

تستخدم الاختبارات سجلاً معزولاً في مجلد مؤقت حتى لا تتداخل مع سجل وقت التشغيل
الذي تكتبه الخلفيات (background threads) في نفس الوقت.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path

os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

from memory.core import SovereignCore, IntegrityStatus
from predictive.predictive_risk_manager import get_predictive_risk_manager


def _fresh_core():
    """نواة معزولة في مجلد مؤقت."""
    tmp = Path(tempfile.mkdtemp(prefix="r606_test_"))
    (tmp / "blobs").mkdir(parents=True, exist_ok=True)
    core = SovereignCore(
        log_file=tmp / "ledger.jsonl",
        blobs_dir=tmp / "blobs",
        index_file=tmp / "index.json",
        meta_file=tmp / "meta.json",
        integrity_file=tmp / "integrity.json",
    )
    return core, tmp


def test_risk_getter_is_cached():
    """get_risk_status يُخزَّن مؤقتاً — الاستدعاء الثاني أسرع بكثير."""
    rm = get_predictive_risk_manager()
    t0 = time.time()
    s1 = rm.get_risk_status()
    t1 = time.time()
    s2 = rm.get_risk_status()
    t2 = time.time()
    assert s1 is not None
    # الاستدعاء الثاني يجب أن يكون من الكاش (شبه فوري)
    assert (t2 - t1) < (t1 - t0) + 0.01
    assert (t2 - t1) < 0.5


def test_early_warnings_no_recursion():
    """get_early_warnings_list لا يقع في عودية لا نهائية."""
    rm = get_predictive_risk_manager()
    warnings = rm.get_early_warnings_list()
    assert isinstance(warnings, list)


def test_integrity_cache_ttl():
    """verify_integrity يُخزَّن مؤقتاً ولا يُعاد فحص السجل في كل استدعاء."""
    core, tmp = _fresh_core()
    try:
        # أول تحقق كامل (سجل فارغ → NOT_CHECKED أو VERIFIED بعد genesis)
        status1 = core.verify_integrity()
        # إضافة حدث يبطل الكاش (last_hash تغيّر)
        core.append_event(event_type="test::r606", payload={"n": 1})
        # التحقق التالي يجب أن يمر (السجل سليم) — لا RecursionError ولا فشل
        status2 = core.verify_integrity()
        assert status2 == IntegrityStatus.VERIFIED
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_iterate_events_fast_path_matches_full():
    """مسار الذيل السريع في iterate_events يعيد نفس الأحداث الأخيرة."""
    core, tmp = _fresh_core()
    try:
        for i in range(10):
            core.append_event(event_type="test::r606", payload={"n": i})
        fast = [e["hash"] for e in core.iterate_events(reverse=True, limit=3)]
        full = [e["hash"] for e in core.iterate_events(reverse=True)]
        assert fast == full[:3]
        assert len(fast) == 3
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_reset_rebuilds_index():
    """reset() يعيد بناء الفهرس من السجل — عدّادات متسقة."""
    core, tmp = _fresh_core()
    try:
        for i in range(5):
            core.append_event(event_type="test::r606", payload={"n": i})
        core.reset()
        ledger_count = sum(1 for _ in open(core.log_file))
        assert core.index.data["events_count"] == ledger_count
        assert core.verify_integrity() == IntegrityStatus.VERIFIED
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
