"""D-034: فشل مغلق عند CORS_ORIGINS غير الصريح في الإنتاج.

قرار المالك D-034 (2026-10-17، docs/DECISIONS.md): «CORS_ORIGINS في الإنتاج
يجب أن يكون قائمة صريحة. لا `*` ولا `null`. إذا كان ENV=production
وCORS_ORIGINS="*" — التطبيق يرفض الإقلاع (fail-closed)».

جولة التصحيح (اعتراض المراجع الأول على الالتزام 2a52f02): الرفض يجب أن
يشمل النجمة/«null» داخل قائمة مختلطة (مثل `https://a.example,*`) والقائمة
الفارغة — لا القائمة النجمية الخالصة فقط. كما فُصل اختبار النجمة الصريح
عن اختبار الغياب، وصار التوكيد على رسالة الرفض كاملة نصًا + غياب BOOT_OK.

نمط العزل: نفس نمط tests/test_config_security.py — subprocess مع
SOVEREIGN_DATA_ROOT مؤقت، لا يُلمس مفتاح التشغيل الحقيقي.
"""

import os
import subprocess
import sys
import tempfile

# مفتاح اختباري طويل (>= 32) حتى يكون فشل الإقلاع — إن وقع — سببه CORS وحده
_TEST_SOVEREIGN_KEY = "cors_d034_test_key_0123456789abcdef0123456789"

# رسالة الرفض الحرفية — يجب أن تطابق نص القاعدة في backend/config.py
_REJECT_MSG = (
    "❌ CORS في الإنتاج (D-034): قائمة مصادر صريحة مطلوبة — "
    "لا \"*\" ولا \"null\" (ولو داخل قائمة) ولا قائمة فارغة. "
    "اضبط CORS_ORIGINS بقائمة صريحة "
    "(مثال: CORS_ORIGINS=https://app.example.com)"
)


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


def _assert_refusal(result):
    """توكيد موحد لمسار الرفض: رمز خروج فاشل + الرسالة كاملة نصًا + لا BOOT_OK."""
    assert result.returncode != 0, (
        f"expected boot refusal, got returncode 0 with output {result.stdout!r}"
    )
    combined = result.stderr + result.stdout
    assert _REJECT_MSG in combined, (
        f"expected exact rejection message {_REJECT_MSG!r}, "
        f"got: {combined[-400:]!r}"
    )
    assert "BOOT_OK" not in result.stdout, (
        "boot must not complete when CORS policy is violated"
    )


def test_production_wildcard_cors_refuses_boot():
    """مسار الفشل المحقون: إنتاج + نجمة صريحة = رفض إقلاع.

    D-034 حرفيًا: «إذا كان ENV=production وCORS_ORIGINS="*" — التطبيق يرفض
    الإقلاع (fail-closed)».
    """
    result = _run_config_boot(_isolated_env("production", cors_origins="*"))
    _assert_refusal(result)


def test_production_unset_cors_refuses_boot():
    """إنتاج بلا CORS_ORIGINS أصلًا: الافتراضي "*" — يرفض الإقلاع أيضًا.

    الغياب ليس تمريرًا صامتًا للنجمة: الافتراضي الخطير يُرفض كما لو كُتب
    نصًا. (منفصل عن اختبار النجمة الصريح — الحالة مختلفة: لا متغير أصلًا.)
    """
    result = _run_config_boot(_isolated_env("production", cors_origins=None))
    _assert_refusal(result)


def test_production_wildcard_inside_list_refuses_boot():
    """مسار الفشل المحقون (اعتراض المراجع): نجمة داخل قائمة مختلطة.

    `https://app.example.com,*` قائمة تحوي نجمة — تخالف نص D-034 («لا *»)
    رغم أنها ليست القائمة النجمية الخالصة. النجمة في أي موضع تُرفض.
    """
    for origins in ("https://app.example.com,*", "*,https://app.example.com"):
        result = _run_config_boot(_isolated_env("production", cors_origins=origins))
        _assert_refusal(result)


def test_production_null_origin_refuses_boot():
    """مسار الفشل المحقون: أصل "null" منفردًا في الإنتاج = رفض إقلاع.

    D-034: «لا `*` ولا `null`» — القيمة "null" يُصدرها بعض المتصفحات
    لطلبات العروض غير المتجانسة وتُستخدم للتحايل على سياسات الأصل.
    """
    result = _run_config_boot(_isolated_env("production", cors_origins="null"))
    _assert_refusal(result)


def test_production_null_inside_list_refuses_boot():
    """مسار الفشل المحقون (اعتراض المراجع): "null" داخل قائمة مختلطة.

    `https://app.example.com,null` — القيمة المحظورة داخل قائمة تُرفض
    مثلها مثل النجمة داخل قائمة.
    """
    result = _run_config_boot(
        _isolated_env("production", cors_origins="https://app.example.com,null")
    )
    _assert_refusal(result)


def test_production_empty_cors_origins_refuses_boot():
    """مسار الفشل المحقون (اعتراض المراجع): قائمة فارغة ليست قائمة صريحة.

    CORS_ORIGINS="" يقسم إلى [""] — ليست مصادر صريحة، تُرفض في الإنتاج.
    """
    result = _run_config_boot(_isolated_env("production", cors_origins=""))
    _assert_refusal(result)


def test_production_whitespace_padded_wildcard_refuses_boot():
    """النجمة بغلاف مسافات (`  *  `) تُرفض أيضًا — التجريد قبل الفحص.

    لولا التجريد لمررت `  *  ` كقائمة «صريحة» تخالف نص القرار.
    """
    result = _run_config_boot(_isolated_env("production", cors_origins="  *  "))
    _assert_refusal(result)


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
