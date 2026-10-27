"""R-783 (ROADMAP_V6 ٦.١.١١) — نقطة استئناف التحقق دائمة عبر إعادة التشغيل.

R-768 جعل التحقق يستأنف من آخر موضع متحقق منه داخل العملية الحية، لكن نقطة
الاستئناف كانت في الذاكرة فقط ⇒ كل إقلاع يعيد فحص السجل كاملًا من الصفر
(80k حدث × 2.68ms ≈ 215ث معالج على الإنتاج — والتحقق الحي يقف عند أول كسر
فيوقف التحقق كله). المطلوب: البادئة المتحقق منها تُبصم على القرس بجانب
integrity.json (بصمة sha256 + بصمة المفاتيح + الحالة)، والإقلاع التالي
يستأنف منها فلا يعيد التحقق من البادئة المبصومة — مع بقاء الفحص الكامل
(verbose=True و/ledger/verify) كاملًا دائمًا.
الحد الصادق الموروث من R-768: الاستئناف لا يعيد التحقق من وجود blobs
البادئة؛ وأي تعديل في البادئة أو تغيّر المفاتيح يفرض فحصًا كاملًا.
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
    kr.generate_new_ed25519_key(reason="R-783 test")
    kr.save_to_disk()
    sc = tmp / "sovereign_core"
    (sc / "blobs").mkdir(parents=True, exist_ok=True)
    calls = {"n": 0}
    real = ed.verify_hex

    def counting(*a, **kw):
        calls["n"] += 1
        return real(*a, **kw)
    monkeypatch.setattr(ed, "verify_hex", counting)

    checkpoint = sc / "integrity_checkpoint.json"

    def mk():
        return SovereignCore(
            log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
            index_file=sc / "index.json", meta_file=sc / "meta.json",
            integrity_file=sc / "integrity.json", keyring=kr)
    yield mk, calls, sc / "ledger.jsonl", checkpoint
    shutil.rmtree(tmp, ignore_errors=True)


def _append_verified(core, n):
    for i in range(n):
        core.append_event("test::r783", {"n": i})


def test_boot_does_not_reverify_fingerprinted_prefix(env):
    """معيار إغلاق ٦.١.١١: الإقلاع على سجل سليم لا يعيد التحقق من البادئة المبصومة."""
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    assert checkpoint.exists(), "نقطة الاستئناف لم تُكتب على القرص"

    # إعادة تشغيل: كائن جديد على الحالة نفسها — الإقلاع يستأنف لا يعيد
    calls["n"] = 0
    core2 = mk()
    assert core2.verify_integrity() == IntegrityStatus.VERIFIED
    assert calls["n"] == 0, f"الإقلاع أعاد التحقق من {calls['n']} توقيعًا من البادئة المبصومة"


def test_resume_after_restart_verifies_only_new_tail(env):
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED

    core2 = mk()
    _append_verified(core2, 2)
    calls["n"] = 0
    assert core2.verify_integrity() == IntegrityStatus.VERIFIED
    assert calls["n"] == 2, f"تحقق من {calls['n']} توقيعًا والمتوقع 2 (الذيل الجديد فقط)"


def test_corrupted_prefix_result_survives_restart(env):
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    with open(log, "ab") as f:
        f.write(b"\x00" * 2059 + b"\n")
    assert core.verify_integrity() == IntegrityStatus.CORRUPTED

    # إعادة تشغيل: النتيجة نفسها بلا إعادة تحقق من البادئة (منطق R-768 عبر القرص)
    calls["n"] = 0
    core2 = mk()
    assert core2.verify_integrity() == IntegrityStatus.CORRUPTED
    assert calls["n"] == 0, f"أعاد التحقق من {calls['n']} توقيعًا بعد إعادة التشغيل"


def test_tampered_prefix_invalidates_disk_checkpoint(env):
    """حارس: بصمة البادئة على القرس ليست ثقة عمياء — أي تعديل يفرض فحصًا كاملًا."""
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    assert checkpoint.exists()

    # عبث بالبادئة: تعديل السطر الثالث (بعد حدثين متحققَين) — الفحص الكامل
    # يتحقق من توقيعي الحدثين السابقين ثم يفشل عن السطر المعبوث
    lines = log.read_bytes().splitlines(keepends=True)
    assert len(lines) >= 3
    assert b"test::r783" in lines[2]
    lines[2] = lines[2].replace(b"test::r783", b"test::r78x", 1)
    log.write_bytes(b"".join(lines))

    calls["n"] = 0
    core2 = mk()
    assert core2.verify_integrity() == IntegrityStatus.CORRUPTED
    assert calls["n"] > 0, "عبث بالبادئة لم يفرض فحصًا كاملًا — الثقة العمياء ممنوعة"


def test_invalid_checkpoint_file_is_ignored(env):
    """حارس: ملف نقطة استئناف تالف البنية يُتجاهل — فحص كامل صادق، لا انهيار."""
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    checkpoint.write_text("{ هذا ليس JSON", encoding="utf-8")

    calls["n"] = 0
    core2 = mk()
    assert core2.verify_integrity() == IntegrityStatus.VERIFIED
    assert calls["n"] == 5, f"تجاهل الملف التالف تطلب فحصًا كاملًا ({calls['n']} توقيعًا)"
