"""إعدادات الاختبارات — يضيف backend إلى مسار الاستيراد"""
import os
import sys

# أضف backend إلى مسار الاستيراد (app.py يستورد orchestrator نسبياً)
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# أضف جذر المستودع (لـ nexus)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
