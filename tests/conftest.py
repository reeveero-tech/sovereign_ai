"""إعدادات الاختبارات — يضيف backend إلى مسار الاستيراد"""
import os
import sys

# مفتاح سيد ثابت للاختبارات — يجب تعريفه قبل استيراد config/app.
# (دون هذا، يولّد config.py مفتاحاً عشوائياً مؤقتاً عند أول استيراد،
#  فيفشل أي اختبار لاحق يقارن بالمفتاح المطلوب — راجع المرحلة 3)
if not os.environ.get("SOVEREIGN_KEY"):
    os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

# R-619: عزل عام — كل الاختبارات تكتب إلى جذر مؤقت، ليس data/ الحقيقي.
# (المشكلة: اختبارات TestClient(app) تُنشئ أحداثًا في السجل الحقيقي،
#  فنما السجل من 11,777 إلى 116,452+ حدثًا — تلوث الدليل الجنائي)
# الاستثناء: اختبارات معزولة بالفعل تُحدد SOVEREIGN_DATA_ROOT بنفسها.
if not os.environ.get("SOVEREIGN_DATA_ROOT"):
    import tempfile as _tempfile
    _test_data_root = _tempfile.mkdtemp(prefix="sovereign_test_data_")
    os.environ["SOVEREIGN_DATA_ROOT"] = _test_data_root

# R-634: إنشاء KeyRing معزول مع مفتاح نشط (في الجذر المعزول)
# — بديل fallback للحقيقي (R-621 معطل). هذا يضمن أن SovereignCore()
# في بيئة الاختبار يجد مفتاحًا نشطًا (فشل مُغلق يمنع الاختبارات
# التي تُنشئ أحداثًا).
# ملاحظة: المفتاح اختباري (ليس مفتاح تشغيل) — لا علاقة بالحقيقي.
try:
    _test_root = os.environ.get("SOVEREIGN_DATA_ROOT")
    if _test_root:
        from pathlib import Path as _Path
        _keys_dir = _Path(_test_root) / "keys"
        _keys_dir.mkdir(parents=True, exist_ok=True)
        _keyring_file = _keys_dir / "keyring.json"
        if not _keyring_file.exists():
            # إنشاء KeyRing معزول مع مفتاح نشط (اختباري)
            import sys as _sys
            _backend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
            if _backend not in _sys.path:
                _sys.path.insert(0, _backend)
            from sovereign.keys import KeyRing as _TestKeyRing
            _kr = _TestKeyRing(keys_dir=_keys_dir)
            _kr.generate_new_key(reason="test_env_r634")
            _kr.save_to_disk()
except Exception as _e:
    # لا نُفشل الاستيراد — الاختبارات المعزولة ستُنشئ مفاتيحها
    pass

# أضف backend إلى مسار الاستيراد (app.py يستورد orchestrator نسبياً)
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# أضف جذر المستودع (لـ nexus)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
