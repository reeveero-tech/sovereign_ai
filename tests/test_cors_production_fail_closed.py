"""D-034: فشل مغلق عند CORS_ORIGINS="*" أو "null" في الإنتاج.

قرار المالك D-034 (2026-10-17، docs/DECISIONS.md): «CORS_ORIGINS في الإنتاج
يجب أن يكون قائمة صريحة. لا `*` ولا `null`. إذا كان ENV=production
وCORS_ORIGINS="*" — التطبيق يرفض الإقلاع (fail-closed)».

قبل هذا الاختبار كان config.py يكتفي بـ warnings.warn (تحذير بلا منع) —
الفجوة أثبتها RED فعليًا: مسار الفشل المحقون كان يُقبل (returncode 0).

نمط العزل: نفس نمط tests/test_config_security.py — subprocess مع
SOVEREIGN_DATA_ROOT مؤقت، لا يُلمس مفتاح التشغيل الحقيقي.
"""

import os
import subprocess
import sys
import tempfile

# مفتاح اختباري طويل (>= 32) حتى يكون فشل الإقلاع — إن وقع — سببه CORS وحده
_TEST_SOVEREIGN_KEY = "cors_d034_test_key_0123456789abcdef0123456789"


def _run_config_boot(env):
    """استيراد config في عملية معزولة — محاكاة الإقلاع الفعلي."""
    command = [
        sys.executable,
        "-c",
        "import config; print('BOOT_OK')",
    ]
    return subprocess.run(
        command,
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
    )


def _isolated_env(environment, cors_origins=None):
    """بيئة معزولة: جذر بيانات مؤقت + مفتاح سيادة صالح عبر متغير البيئة."""
    tmp_root = tempfile.mkdtemp(prefix="sovereign_cors_d034_test_")
    tmp_data = os.path.join(tmp_root, "data")
    os.makedirs(tmp_data, exist_ok=True)

    env = os.environ.copy()
    env.pop("SOVEREIGN_KEY", None)
    env["SOVEREIGN_KEY"] = _TEST_SOVEREIGN_KEY
    env["AI_ENVIRONMENT"] = environment
    env["SOVEREIGN_DATA_ROOT"] = tmp_data
    if cors_origins is None:
        env.pop("CORS_ORIGINS", None)
    else:
        env["CORS_ORIGINS"] = cors_origins
    return env


def test_production_wildcard_cors_refuses_boot():
    """مسار الفشل المحقون: إنتاج + CORS_ORIGINS افتراضي ("*") = رفض إقلاع.

    D-034 حرفيًا: «إذا كان ENV=production وCORS_ORIGINS="*" — التطبيق يرفض
    الإقلاع (fail-closed)». التوكيد على الرسالة نصًا (لا مجرد returncode)
    ليثبت أن سبب الرفض هو CORS نفسه، لا سبب آخر.
    """
    result = _run_config_boot(_isolated_env("production"))

    assert result.returncode != 0, (
        f"production with wildcard CORS must refuse to boot, "
        f"got returncode 0 with output {result.stdout!r}"
    )
    combined = result.stderr + result.stdout
    assert "CORS" in combined, (
        f"rejection message must name CORS, got: {combined[-300:]!r}"
    )
    assert "D-034" in combined, (
        f"rejection message must reference decision D-034, got: {combined[-300:]!r}"
    )


def test_production_unset_cors_refuses_boot():
    """إنتاج بلا CORS_ORIGINS أصلًا: الافتراضي "*" — يرفض الإقلاع أيضًا.

    الغياب ليس تمريرًا صامتًا للنجمة: الافتراضي الخطير يُرفض كما لو كُتب
    نصًا.
    """
    result = _run_config_boot(_isolated_env("production", cors_origins=None))

    assert result.returncode != 0, (
        "production with unset CORS_ORIGINS (default '*') must refuse to boot"
    )
    combined = result.stderr + result.stdout
    assert "CORS" in combined, (
        f"rejection message must name CORS, got: {combined[-300:]!r}"
    )


def test_production_null_origin_refuses_boot():
    """مسار الفشل المحقون الثاني: أصل "null" في الإنتاج = رفض إقلاع.

    D-034: «لا `*` ولا `null`» — القيمة "null" يُصدرها بعض المتصفحات
    لطلبات العروض غير المتجانسة وتُستخدم للتحايل على سياسات الأصل.
    """
    result = _run_config_boot(_isolated_env("production", cors_origins="null"))

    assert result.returncode != 0, (
        "production with CORS_ORIGINS='null' must refuse to boot"
    )
    combined = result.stderr + result.stdout
    assert "CORS" in combined, (
        f"rejection message must name CORS, got: {combined[-300:]!r}"
    )


def test_production_explicit_cors_origins_boot():
    """المسار السليم: قائمة مصادر صريحة في الإنتاج = إقلاع طبيعي.

    الفشل المغلق لا يعطل التشغيل الصحيح — من يضبط قائمة صريحة يقلع.
    """
    result = _run_config_boot(
        _isolated_env("production", cors_origins="https://app.example.com")
    )

    assert result.returncode == 0, (
        f"production with explicit CORS origins must boot, "
        f"failed with: {(result.stderr + result.stdout)[-300:]!r}"
    )
    assert "BOOT_OK" in result.stdout


def test_development_wildcard_cors_boots():
    """التطوير مع "*" يبقى مقبولًا (تحذير لا رفض) — D-034 يقيد الإنتاج فقط."""
    result = _run_config_boot(_isolated_env("development"))

    assert result.returncode == 0, (
        f"development with wildcard CORS must boot, "
        f"failed with: {(result.stderr + result.stdout)[-300:]!r}"
    )
    assert "BOOT_OK" in result.stdout
