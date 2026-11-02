"""R-838: النواة الدلالية متعددة اللغات — فهم أصيل بلا ترجمة وسيطة.

المكونات (حلقة واحدة لا مكونات معزولة):
- detector: كشف اللغة على مستوى المقطع + تقسيم تبديل الشيفرة.
- frame: المحلل الدلالي بعقد JSON الإلزامي (نية/كيانات/مراجع/علاقات/غموض).
- lexicon: المعجم المفاهيمي عبر اللغات (وحدات معنى مستقلة عن اللغة).
- entity_table: جدول الكيانات + محرك الإحالة والضمائر (عربي/إنجليزي).
- memory: الذاكرة الهرمية (عاملة/عرضية/دلالية/إجرائية) وسياساتها.
- validator: المدقق بعد التوليد + سجل التتبع المثبت للمسار.
- pipeline: حلقة العمل المتكاملة + توافق عكسي مع context_resolver.
"""
from .detector import detect, dominant_language  # noqa: F401
from .frame import analyze  # noqa: F401
from .entity_table import EntityTable  # noqa: F401
from .memory import HierarchicalMemory  # noqa: F401
from .pipeline import ConversationState, resolve  # noqa: F401
from .validator import validate_reply  # noqa: F401

__all__ = ["detect", "dominant_language", "analyze", "EntityTable",
           "HierarchicalMemory", "ConversationState", "resolve", "validate_reply"]
