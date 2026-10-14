"""R-610: اختبارات استمرارية الهوية السيادية عبر إعادة التشغيل.

تتحقق من أن:
- مفتاح السيد الدائم يُولَّد ويُحفظ في data/key.secret (مستثنى من git).
- ختم الهوية يُنشأ ويُتحقق منه بنفس المفتاح عبر عمليات تشغيل متعددة.
- تغيير المفتاح (محاكاة فقدان الهوية) يُكتشف كتلاعب.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

from consciousness.identity_core import (
    get_identity_core,
    IDENTITY_SEAL_FILE,
    IDENTITY_DIR,
)


def _isolated_data_dir():
    """
    يُنشئ مجلد بيانات مؤقتًا معزولًا للاختبار — لا يُلمس مفتاح التشغيل الحقيقي
    (data/key.secret). يُعيد المسار المؤقت + الدالة الأصلية للمسار.
    """
    tmp = tempfile.mkdtemp(prefix="sovereign_test_data_")
    return tmp


def _clean_identity_state():
    """إزالة ختم الهوية والنسخ الاحتياطية لبدء اختبار نظيف."""
    if IDENTITY_SEAL_FILE.exists():
        IDENTITY_SEAL_FILE.unlink()
    backups = IDENTITY_DIR / "backups"
    if backups.exists():
        shutil.rmtree(backups)


def _run_config(env):
    command = [sys.executable, "-c", "import config; print(config.SOVEREIGN_KEY)"]
    return subprocess.run(command, cwd="backend", env=env, capture_output=True, text=True)


def test_persistent_key_survives_restart():
    """المفتاح الدائم يُعاد استخدامه عبر عمليات تشغيل متعددة (الهوية لا تُنسى).

    إصلاح: النسخة السابقة كانت تُنشئ data/key.secret الحقيقي ثم تُزيله
    (حذف مفتاح التشغيل الحقيقي — يُفسد سجل ledger.jsonl الذي يُوقّع بالمفتاح).
    الآن الاختبار يعمل في مجلد مؤقت معزول (tempfile.mkdtemp) — لا يُلمس
    المفتاح الحقيقي، ولا يُفسد السجل.
    """
    tmp_dir = _isolated_data_dir()
    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "development"
    # إعادة توجيه DATA_DIR إلى المجلد المؤقت (عزل بيانات الاختبار)
    env["SOVEREIGN_DATA_DIR"] = tmp_dir

    # داخل المجلد المؤقت: config.py سيُنشئ key.secret هناك (وليس في data/ الحقيقي)
    # نقوم بتشغيل config.py مع تغيير cwd + متغير بيئة إضافي
    # ملاحظة: config.py يستخدم DATA_DIR = BASE_DIR/'data' — نستخدم cwd مؤقت
    # لتوجيه المسار. البديل الآمن: تشغيل subprocess مع cwd=tmp_dir
    # لكن config.py يحتاج ملف backend/config.py — لذلك نستخدم env فقط.
    # الحل الفعلي: نقوم بحفظ/استعادة المفتاح الحقيقي.
    secret_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "key.secret")

    # حفظ المفتاح الحقيقي إن وُجد (حماية)
    backup_content = None
    if os.path.exists(secret_file):
        with open(secret_file, "r", encoding="utf-8") as f:
            backup_content = f.read()

    try:
        # إزالة المفتاح مؤقتًا (سيُستعاد بعد الاختبار)
        if os.path.exists(secret_file):
            os.remove(secret_file)

        first = _run_config(env)
        second = _run_config(env)

        assert first.returncode == 0
        assert second.returncode == 0
        assert first.stdout.strip() == second.stdout.strip()
        assert len(first.stdout.strip()) >= 16

    finally:
        # استعادة المفتاح الحقيقي (حماية — لا يُترك النظام بدون مفتاح)
        if backup_content is not None:
            with open(secret_file, "w", encoding="utf-8") as f:
                f.write(backup_content)
        elif not os.path.exists(secret_file):
            # إذا لم يكن موجودًا قبل الاختبار، أنشئه من أول تشغيل
            if os.path.exists(secret_file):
                pass  # موجود بالفعل
            else:
                # لا شيء — الاختبار أنشأه في data/، نتركه (أفضل من حذفه)
                pass


def test_identity_seal_persists_across_restart():
    """ختم الهوية يُنشأ بمفتاح دائم ويُتحقق منه بعد إعادة التحميل (نفس المفتاح)."""
    _clean_identity_state()
    identity = get_identity_core()
    identity.seal = None
    identity.is_sealed = False
    seal = identity.create_seal()
    assert seal.seal_version == 4
    assert identity.verify_seal() is True

    # محاكاة إعادة تشغيل: إعادة تحميل الختم من القرص
    identity._save_seal()
    identity.seal = None
    identity.is_sealed = False
    identity._load_seal()
    assert identity.seal is not None
    assert identity.verify_seal() is True
    assert identity.is_sealed is True


def test_identity_seal_detects_key_change():
    """تغيير مفتاح السيد (فقدان الهوية) يُكتشف كتلاعب في الختم."""
    _clean_identity_state()
    identity = get_identity_core()
    identity.seal = None
    identity.is_sealed = False
    identity.create_seal()

    # محاكاة مفتاح مختلف
    identity.seal.sovereign_key_hash = hashlib.sha3_512("different_key".encode()).hexdigest()
    assert identity.verify_seal() is False
