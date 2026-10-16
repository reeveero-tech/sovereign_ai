"""conftest لـ backend/tests — نفس الإعداد البيئي لـ tests/conftest.py

السبب: انتقلت اختبارات invariants الستة (المرحلة 3 من ROADMAP_V2) إلى
backend/tests/invariants/ وفق مسار ROADMAP — وبلا هذا الإعداد، اختبار
entrypoints (TestClient(app)) سيكتب في data/ الحقيقية (جريمة R-619).

الفرق الوحيد عن tests/conftest.py: لا تسجيل لخيار --run-operational هنا —
مسجل هناك، وتسجيله مرتين يكسر pytest بخطأ option-already-added عند تشغيل
المسارين معًا (وهو الاستدعاء القياسي في verify.sh). اختبارات operational
كلها في tests/ — لا أثر لهذا الحذف هنا.
"""
import os
import sys

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
# KeyRing() الافتراضي يجد مفاتيح (فشل مُغلق يمنع الاختبارات المُنشئة أحداثًا).
try:
    _test_root = os.environ.get("SOVEREIGN_DATA_ROOT")
    if _test_root:
        from pathlib import Path as _Path
        _keys_dir = _Path(_test_root) / "keys"
        _keys_dir.mkdir(parents=True, exist_ok=True)
        _keyring_file = _keys_dir / "keyring.json"
        if not _keyring_file.exists():
            _backend = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "backend",
            )
            if _backend not in sys.path:
                sys.path.insert(0, _backend)
            from sovereign.keys import KeyRing as _TestKeyRing
            _kr = _TestKeyRing(keys_dir=_keys_dir)
            _kr.generate_new_key(reason="test_env_r634_backend")
            _kr.save_to_disk()
except Exception:
    # لا نُفشل الاستيراد — الاختبارات المعزولة ستُنشئ مفاتيحها
    pass

# مسارات الاستيراد (app.py يستورد orchestrator نسبيًا)
_BACKEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"
)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


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
