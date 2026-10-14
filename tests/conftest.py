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

# أضف backend إلى مسار الاستيراد (app.py يستورد orchestrator نسبياً)
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# أضف جذر المستودع (لـ nexus)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
