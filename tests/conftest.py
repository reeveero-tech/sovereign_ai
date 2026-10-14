"""إعدادات الاختبارات — يضيف backend إلى مسار الاستيراد"""
import os
import sys

# مفتاح سيد ثابت للاختبارات — يجب تعريفه قبل استيراد config/app.
# (دون هذا، يولّد config.py مفتاحاً عشوائياً مؤقتاً عند أول استيراد،
#  فيفشل أي اختبار لاحق يقارن بالمفتاح المطلوب — راجع المرحلة 3)
if not os.environ.get("SOVEREIGN_KEY"):
    os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

# أضف backend إلى مسار الاستيراد (app.py يستورد orchestrator نسبياً)
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# أضف جذر المستودع (لـ nexus)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
