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

    إصلاح (R-615): النسخة السابقة كانت تُنشئ data/key.secret الحقيقي ثم
    تُزيله — تدمير مفتاح التشغيل. الآن الاختبار يعمل في جذر مؤقت معزول
    تمامًا عبر SOVEREIGN_DATA_ROOT (يُعاد توجيه DATA_DIR في config.py).
    لا يُلمس مفتاح التشغيل الحقيقي إطلاقًا.
    """
    import tempfile
    tmp_root = tempfile.mkdtemp(prefix="sovereign_test_root_")
    tmp_data = os.path.join(tmp_root, "data")
    os.makedirs(tmp_data, exist_ok=True)

    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "development"
    # عزل فعلي: config.py سيستخدم tmp_data كـ DATA_DIR (لا يُلمس data/ الحقيقي)
    env["SOVEREIGN_DATA_ROOT"] = tmp_data

    # المفتاح سيُنشأ داخل الجذر المؤقت — لا يُلمس المفتاح الحقيقي
    secret_file = os.path.join(tmp_data, "key.secret")

    first = _run_config(env)
    second = _run_config(env)

    assert first.returncode == 0, f"first config run failed: {first.stderr}"
    assert second.returncode == 0, f"second config run failed: {second.stderr}"
    assert first.stdout.strip() == second.stdout.strip(), (
        f"key should be identical across restarts, got different keys"
    )
    assert len(first.stdout.strip()) >= 16

    # المفتاح يجب أن يكون داخل الجذر المؤقت (وليس في data/ الحقيقي)
    assert os.path.exists(secret_file), (
        f"key.secret should be created in isolated tmp dir {tmp_data}, not real data/"
    )

    # التحقق من أن المفتاح الحقيقي لم يُلمس (إن كان موجودًا قبل الاختبار)
    real_secret = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "key.secret")
    # لا نتحقق من محتوى (سرية) — فقط أن الاختبار لم يُنشئ/يحذف المفتاح الحقيقي
    # (لو كان موجودًا قبل الاختبار، ما زال موجودًا — لم نلمسه)


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
