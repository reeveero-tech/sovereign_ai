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
    # (التصفير بعد الإقلاع: تحقق توقيع نقطة الاستئناف عند الحمل ليس فحص أحداث)
    core2 = mk()
    calls["n"] = 0
    assert core2.verify_integrity() == IntegrityStatus.VERIFIED
    assert calls["n"] == 0, f"الإقلاع أعاد التحقق من {calls['n']} توقيعًا من البادئة المبصومة"


def test_resume_after_restart_verifies_only_new_tail(env):
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED

    core2 = mk()
    _append_verified(core2, 2)
    calls["n"] = 0  # بعد الإقلاع (تحقق توقيع النقطة ليس فحص أحداث)
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
    core2 = mk()
    calls["n"] = 0  # بعد الإقلاع (تحقق توقيع النقطة ليس فحص أحداث)
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


def test_forged_checkpoint_cannot_skip_prefix(env):
    """R-783a — حد الثقة الجديد: ملف على القرص ليس ذاكرة.

    هجوم مفترض: عبث بتوقيع حدث داخل البادئة (بلا كسر السلسلة — التجزئة لا تغطي
    التوقيع) + تزوير بصمة sha256 للبادئة المعبوثة داخل نقطة الاستئناف نفسها.
    نقطة غير موقعة كانت ستقبل هذا وتعلن VERIFIED؛ نقطة موقعة بمفتاح KeyRing
    تُكشف عند الحمل (توقيع الحمولة لا يطابق) ⇒ فحص كامل ⇒ CORRUPTED.
    """
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    assert checkpoint.exists()

    # العبث: تبديل حرف من توقيع السطر الثالث (سلسلة التجزئة تبقى سليمة)
    lines = log.read_bytes().splitlines(keepends=True)
    marker = b'"signature": "'
    idx = lines[2].find(marker)
    assert idx != -1
    pos = idx + len(marker)
    lines[2] = lines[2][:pos] + (b"0" if lines[2][pos:pos+1] != b"0" else b"1") + lines[2][pos+1:]
    log.write_bytes(b"".join(lines))

    # التزوير: إعادة حساب بصمة البادئة المعبوثة داخل نقطة الاستئناف (كأن كاتبها
    # خصم موثوق) — التوقيع على الحمولة هو ما يجب أن يكشفها
    import hashlib
    st = json.loads(checkpoint.read_text(encoding="utf-8"))
    st["sha256"] = hashlib.sha256(log.read_bytes()[:st["offset"]]).hexdigest()
    checkpoint.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

    calls["n"] = 0
    core2 = mk()
    assert core2.verify_integrity() == IntegrityStatus.CORRUPTED, (
        "نقطة مزورة كشفت عبث التوقيع — يجب أن يُعلن CORRUPTED")
    assert calls["n"] > 0, "نقطة مزورة جعلت الفحص يتخطى البادئة (ثقة عمياء)"


def test_checkpoint_missing_status_field_is_ignored(env):
    """R-783a — متانة: حذف حقل status فقط يجب أن يُتجاهل الملف لا أن ينهار الفحص."""
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    st = json.loads(checkpoint.read_text(encoding="utf-8"))
    del st["status"]
    checkpoint.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

    calls["n"] = 0
    core2 = mk()  # لا انهيار عند الإقلاع ولا عند الفحص
    assert core2.verify_integrity() == IntegrityStatus.VERIFIED
    assert calls["n"] == 5, f"الملف الناقص يجب أن يُتجاهل ويفحص كاملًا ({calls['n']} توقيعًا)"


def test_checkpoint_invalid_utf8_is_ignored(env):
    """R-783a — متانة: ملف غير UTF-8 يُتجاهل بصمت — لا انهيار إقلاع."""
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    checkpoint.write_bytes(b"\xff\xfe\x00\xfa\xfa\xfd\x00\x01")

    calls["n"] = 0
    core2 = mk()  # الإقلاع لا ينهار على ملف غير UTF-8
    assert core2.verify_integrity() == IntegrityStatus.VERIFIED
    assert calls["n"] == 5, f"الملف غير القابل للفك يجب أن يُتجاهل ({calls['n']} توقيعًا)"


def test_restart_with_fresh_keyring_preserves_memory(env):
    """R-783a — المادة ٨: استئناف حقيقي كإقلاع إنتاج — KeyRing جديد من القرص،
    والذاكرة (الأحداث والblobs) محفوظة كما هي بعد إعادة التشغيل."""
    mk, calls, log, checkpoint = env
    core = mk()
    _append_verified(core, 5)
    assert core.verify_integrity() == IntegrityStatus.VERIFIED
    events_before = core.index.data["events_count"]
    blobs_before = core.blob_store.count()
    # مسار مفاتيح الـ fixture من الكائن الأصلي (KeyRing محقون)
    keys_dir = core._keyring.keys_dir

    # إقلاع جديد: KeyRing يُحمّل من القرص (كالتشغيل الحقيقي) لا كائن مشترك
    kr2 = KeyRing(keys_dir=keys_dir)
    kr2.load_from_disk()
    tmp_dir = keys_dir.parent
    sc = tmp_dir / "sovereign_core"
    core2 = SovereignCore(
        log_file=sc / "ledger.jsonl", blobs_dir=sc / "blobs",
        index_file=sc / "index.json", meta_file=sc / "meta.json",
        integrity_file=sc / "integrity.json", keyring=kr2)
    assert core2.index.data["events_count"] == events_before, "الأحداث لم تُحفظ عبر الإقلاع"
    assert core2.blob_store.count() == blobs_before, "الblobs لم تُحفظ عبر الإقلاع"
    calls["n"] = 0  # بعد الإقلاع (تحقق توقيع النقطة ليس فحص أحداث)
    assert core2.verify_integrity() == IntegrityStatus.VERIFIED
    assert calls["n"] == 0, "الإقلاع بمفاتيح محملة من القرص أعاد التحقق من البادئة"
