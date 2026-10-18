"""conftest لـ backend/tests — نفس الإعداد البيئي لـ tests/conftest.py

السبب: انتقلت اختبارات invariants الستة (المرحلة 3 من ROADMAP_V2) إلى
backend/tests/invariants/ وفق مسار ROADMAP — وبلا هذا الإعداد، اختبار
entrypoints (TestClient(app)) سيكتب في data/ الحقيقية (جريمة R-619).

الفرق الوحيد عن tests/conftest.py: لا تسجيل لخيار --run-operational هنا —
مسجل هناك، وتسجيله مرتين يكسر pytest بخطأ option-already-added عند تشغيل
المسارين معًا (وهو الاستدعاء القياسي في verify.sh). اختبارات operational
كلها في tests/ — لا أثر لهذا الحذف هنا.

تصويب المراجعة (الجولة الإنشائية — الاعتراض 5): اشتقاق المسارات من موضع
هذا الملف نفسه — الملف في <repo>/backend/tests/، إذًا:
  backend = <repo>/backend  (مستويان أعلى)
  repo    = <repo>          (ثلاثة مستويات أعلى)
(الصيغة السابقة أنتجت <repo>/backend/backend ومسارًا جذريًا خاطئًا —
اكتشفه المراجع؛ أخطاء الاستيراد كانت محجوبة بسبق تحميل tests/conftest.py)
"""
import os
import sys

# هذا الملف: <repo>/backend/tests/conftest.py
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))        # <repo>/backend/tests
_BACKEND_DIR = os.path.dirname(_THIS_DIR)                     # <repo>/backend
_REPO_ROOT = os.path.dirname(_BACKEND_DIR)                    # <repo>

# R-682 (بند ٦): تعطيل خيوط الخلفية في بيئة الاختبار — قبل أي استيراد.
os.environ["SOVEREIGN_DISABLE_BACKGROUND_THREADS"] = "1"

# مفتاح سيد ثابت للاختبارات — قبل استيراد config/app.
if not os.environ.get("SOVEREIGN_KEY"):
    os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

# R-619: عزل عام — كل الاختبارات تكتب إلى جذر مؤقت، ليس data/ الحقيقي.
if not os.environ.get("SOVEREIGN_DATA_ROOT"):
    import tempfile as _tempfile
    os.environ["SOVEREIGN_DATA_ROOT"] = _tempfile.mkdtemp(
        prefix="sovereign_test_data_"
    )

# R-634: إنشاء KeyRing معزول مع مفتاح نشط (في الجذر المعزول) — يضمن
# KeyRing() الافتراضي يجد مفاتيح. (تصويب المراجع: فشل التجهيز لا يُبتلع —
# اختبارات invariants تفشل صراحة بدل عمل بصمت بلا مفاتيح)
try:
    from pathlib import Path as _Path
    _keys_dir = _Path(os.environ["SOVEREIGN_DATA_ROOT"]) / "keys"
    _keys_dir.mkdir(parents=True, exist_ok=True)
    if not (_keys_dir / "keyring.json").exists():
        if _BACKEND_DIR not in sys.path:
            sys.path.insert(0, _BACKEND_DIR)
        from sovereign.keys import KeyRing as _TestKeyRing
        _kr = _TestKeyRing(keys_dir=_keys_dir)
        _kr.generate_new_key(reason="test_env_r634_backend")
        _kr.save_to_disk()
except Exception as _provision_error:
    # لا ابتلاع صامت: الجذر المعزول بلا keyring يعني فشلًا صريحًا لاحقًا في
    # invariants (KeyRing is empty — invariant violated). نرفع التحذير بصوت
    # عالٍ ويبقى مسار الفشل الصريح في الاختبارات نفسها.
    import warnings as _warnings
    _warnings.warn(
        f"backend/tests/conftest: isolated test KeyRing provisioning FAILED "
        f"({type(_provision_error).__name__}: {_provision_error}) — invariant "
        "tests that need keys will fail explicitly (no silent pass)"
    )

# مسارات الاستيراد (app.py يستورد orchestrator نسبيًا)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
# وحدة حارس data/keys الحقيقية (واقعة R-621) — في tests/ بجذر المستودع
_TESTS_DIR = os.path.join(_REPO_ROOT, "tests")
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)


# R-682 (بند ٥): إنهاء منظم لخيوط الخلفية في نهاية جلسة pytest.
import pytest


@pytest.fixture(scope="session", autouse=True)
def _shutdown_background_threads():
    from runtime import threads as _threads

    yield
    remaining = _threads.stop_all_and_join(timeout=8.0)
    if remaining:
        raise RuntimeError(
            f"R-682: {remaining} خيط خلفي لم يتوقف بعد stop_all_and_join — "
            "خطر كتابة بعد إغلاق ملفات السجل"
        )


# حارس data/keys الحقيقي (بند OWNER_REQUIRED ٥ — واقعة R-621 لا تتكرر):
# نفس حارس tests/conftest.py — **منع الكتابة** عند تحميل هذا الملف (قبل أي
# استيراد لملفات الاختبار): الملفان المحميان للقراءة فقط طوال الجلسة —
# أي محاولة كتابة تُرفض بـ PermissionError صريح (يمنع أيضًا «اكتب ثم
# استعد الأصل»)، والوضعان يُستعادان عند التصفية ثم **كشف أثر التغيير**
# بمقارنة بصمة البايتات (محتوى keyring.json لا يُعرض أبدًا — بصمة فقط).
# (التجربة الكاملة RED→GREEN بالتشغيل: forensics/R621_REAL_KEYS_GUARD.md)
from _real_keys_guard import protect_real_keys, snapshot  # noqa: E402

_PROTECTED_MODES = protect_real_keys(_REPO_ROOT)
# البصمة عند التحميل — قبل أي استيراد لملفات الاختبار (كما في tests/conftest.py)
_GUARD_SNAPSHOT = snapshot(_REPO_ROOT)


def pytest_sessionfinish(session, exitstatus):
    """استعادة الأوضاع بعمر الجلسة نفسها — تعمل مع --collect-only ومع
    إخفاقات التجميع (fixtures لا تشغل هناك أصلًا)."""
    from _real_keys_guard import restore_real_keys

    restore_real_keys(_REPO_ROOT, _PROTECTED_MODES)


@pytest.fixture(scope="session", autouse=True)
def _guard_real_keys_untouched():
    from _real_keys_guard import assert_untouched

    yield
    assert_untouched(_REPO_ROOT, _GUARD_SNAPSHOT)
