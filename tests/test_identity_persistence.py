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

os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

from consciousness.identity_core import (
    get_identity_core,
    IDENTITY_SEAL_FILE,
    IDENTITY_DIR,
)


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
    """المفتاح الدائم يُعاد استخدامه عبر عمليات تشغيل متعددة (الهوية لا تُنسى)."""
    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "development"

    secret_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "key.secret")
    if os.path.exists(secret_file):
        os.remove(secret_file)

    first = _run_config(env)
    second = _run_config(env)

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout.strip() == second.stdout.strip()
    assert len(first.stdout.strip()) >= 16

    if os.path.exists(secret_file):
        os.remove(secret_file)


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
