# -*- coding: utf-8 -*-
"""
R-701 — سلامة السجل مع أكثر من كاتب: لا CORRUPTED زائف، لا VERIFIED قديم،
ولا إخفاء للاقتطاع.

ثلاثة عيوب مثبتة بالتشغيل (2026-10-20):

1. **CORRUPTED زائف بعد كاتب مشروع آخر:** `verify_integrity` يشترط أن تكون
   آخر تجزئة في الملف = `_last_hash` في ذاكرة هذه النسخة. بعد أن يُلحق كاتب
   آخر (KeyRotation بعد تصويب R-698، أو نسخة نواة أخرى) حدثًا موسلسلًا صحيحًا،
   تعلن النواة الحية السجل CORRUPTED حتى إلحاقها التالي.
2. **VERIFIED قديم بلا حد زمني:** ذاكرة نتيجة `verify_integrity` (غير
   verbose) تُعاد ما دامت `_last_hash` في الذاكرة لم تتغير — بلا مهلة. فتعديل
   سطر سابق في الملف لا يُكتشف عبر هذا المسار أبدًا ما دامت النسخة لم تُلحق.
3. **ارتداد أدخله تصويب R-698 (3ec945b) — إقرار:** مزامنة آخر تجزئة من القرص
   قبل الإلحاق كانت تقبل ملفًا *تراجع* (اقتُطعت آخر أحداثه)، فتبني عليه
   سلسلة سليمة ظاهريًا وتمحو دليل الاقتطاع. قبل 3ec945b كان الإلحاق على
   التجزئة القديمة يكسر السلسلة فيُكشف الاقتطاع. المزامنة الآن تقبل الملف
   *المتقدم* فقط (تجزئتنا المعروفة موجودة فيه)، وإلا تُبقي التجزئة القديمة
   (الدليل محفوظ) وتسجل R-701 [SECURITY].
"""

import json
from pathlib import Path

from backend.memory.core import SovereignCore, EventType, IntegrityStatus
from backend.sovereign.keys.keyring import KeyRing
from backend.sovereign.keys.rotation import KeyRotation


def _core(root: Path, kr) -> SovereignCore:
    sc = root / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    return SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json",
        sovereign_key="test_master_key_1234567890abcdef", keyring=kr,
    )


def _kr(tmp_path):
    kr = KeyRing(keys_dir=tmp_path / "keys")
    kr.generate_new_key(reason="r701")
    kr.save_to_disk()
    return kr


def _live(tmp_path, monkeypatch, n=2):
    data_root = tmp_path / "data"
    monkeypatch.setenv("SOVEREIGN_DATA_ROOT", str(data_root))
    kr = _kr(tmp_path)
    core = _core(data_root, kr)
    for i in range(n):
        core.append_event(EventType.INTERACTION, {"r701": i})
    return data_root, kr, core


def test_live_core_verify_integrity_after_external_rotation(tmp_path, monkeypatch):
    """(1) كاتب مشروع آخر (KeyRotation بالمسار الافتراضي) → النواة الحية تبقى
    VERIFIED بلا إلحاق منها (كان: CORRUPTED «آخر تجزئة غير متطابقة»)."""
    data_root, kr, core = _live(tmp_path, monkeypatch)
    assert core.verify_integrity(verbose=True) == IntegrityStatus.VERIFIED
    assert KeyRotation(kr).rotate(reason="r701-external") is not None
    assert core.verify_integrity(verbose=True) == IntegrityStatus.VERIFIED, (
        "النواة الحية أعلنت CORRUPTED بعد حدث مشروع من كاتب آخر"
    )


def test_cached_verify_integrity_is_time_bounded(tmp_path, monkeypatch):
    """(2) تعديل سطر سابق بعد التخزين المؤقت: بعد انقضاء المهلة (60 ثانية)
    يجب أن تُعاد المراجعة فتُكشف CORRUPTED — لا VERIFIED قديم أبدي."""
    data_root, kr, core = _live(tmp_path, monkeypatch, n=3)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED  # يُخزَّن
    lines = core.log_file.read_text(encoding="utf-8").splitlines()
    ev = json.loads(lines[0])
    ev["type"] = "tampered"
    lines[0] = json.dumps(ev, ensure_ascii=False)
    core.log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    core._integrity_cache["ts"] -= 61.0  # انقضت المهلة
    assert core.verify_integrity() == IntegrityStatus.CORRUPTED, (
        "ذاكرة التحقق أعادت VERIFIED لسجل مُعدَّل بعد انقضاء المهلة"
    )


def test_truncation_not_masked_by_resync(tmp_path, monkeypatch):
    """(3) اقتطاع آخر الأحداث ثم إلحاق من النواة الحية: الاقتطاع يجب أن يبقى
    مكشوفًا (CORRUPTED) — المزامنة لا تقبل ملفًا تراجع."""
    data_root, kr, core = _live(tmp_path, monkeypatch, n=3)
    lines = core.log_file.read_text(encoding="utf-8").splitlines()
    core.log_file.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
    # قبل الإلحاق: النواة تعرف حدثًا لم يعد في الملف → CORRUPTED
    assert core.verify_integrity(verbose=True) == IntegrityStatus.CORRUPTED
    core.append_event(EventType.INTERACTION, {"r701": "after-truncation"})
    fresh = _core(data_root, kr)
    assert fresh.verify_content_integrity() == IntegrityStatus.CORRUPTED, (
        "الاقتطاع مُحي: الإلحاق بُني على الذيل المقتطع فبدت السلسلة سليمة"
    )


def test_resync_still_accepts_advanced_ledger(tmp_path, monkeypatch):
    """عدم ارتداد لتصويب R-698: ملف تقدّم بكاتب مشروع → الإلحاق يبني عليه."""
    data_root, kr, core = _live(tmp_path, monkeypatch)
    other = _core(data_root, kr)
    other.append_event(EventType.RESPONSE, {"r701": "other-writer"})
    core.append_event(EventType.INTERACTION, {"r701": "live-after"})
    evs = [json.loads(l) for l in core.log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert evs[-1]["prev_hash"] == evs[-2]["hash"]
    assert _core(data_root, kr).verify_content_integrity() == IntegrityStatus.VERIFIED
    assert core.verify_integrity(verbose=True) == IntegrityStatus.VERIFIED
