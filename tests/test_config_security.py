"""Security regression tests for sovereign-key configuration."""

import os
import subprocess
import sys


def _run_config(env):
    command = [
        sys.executable,
        "-c",
        "import config; print(config.SOVEREIGN_KEY)",
    ]
    return subprocess.run(
        command,
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
    )


def test_development_without_key_generates_persistent_key():
    """R-610: التطوير بدون مفتاح يولّد مفتاحاً دائماً يُحفظ في data/key.secret.

    الهوية السيادية (ختم الهوية + توقيعات السجل) يجب أن تستمر عبر إعادة التشغيل —
    لذلك المفتاح المولّد يُعاد استخدامه في التشغيل الثاني (نفس القيمة)،
    ولا يُستخدم أي مفتاح افتراضي معروف.
    """
    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "development"

    # تنظيف أي مفتاح دائم سابق لبدء حالة نظيفة
    secret_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "key.secret")
    if os.path.exists(secret_file):
        os.remove(secret_file)

    first = _run_config(env)
    second = _run_config(env)

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout.strip()
    assert second.stdout.strip()
    # R-610: المفتاح الدائم يُعاد استخدامه — نفس القيمة عبر عمليات التشغيل
    assert first.stdout.strip() == second.stdout.strip()
    assert "مفتاح_افتراضي_غير_آمن" not in first.stdout
    # المفتاح الدائم كُتب على القرص
    assert os.path.exists(secret_file)

    # تنظيف بعد الاختبار
    if os.path.exists(secret_file):
        os.remove(secret_file)


def test_production_without_key_fails_closed():
    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["AI_ENVIRONMENT"] = "production"

    result = _run_config(env)

    assert result.returncode != 0
    assert "لم يتم تعيين مفتاح السيد" in (result.stderr + result.stdout)
