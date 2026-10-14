# backend/compat/__meta__.py
# نمط التين الخانق (Strangler Fig) — طبقة توثيق lifecycle لطبقة التوافق
# (المرحلة 4 من ROADMAP_V2)
#
# الغرض: منح طبقة compat أفقاً — كل وحدة توافق لها معيار إزالة (sunset
# criteria) موثّق. أي وحدة بدون معيار = لا أفق = فشل الاختبار الثابت.
#
# القاعدة الصارمة: حتى بعد sunset، لا يُحذف الملف. يُنقل إلى
# backend/compat/_legacy/ ويُبقى. الدستور يمنع الحذف.
#
# القاعدة الثانية: أي وحدة compat جديدة يجب أن تُضاف هنا مع معيار
# إزالة واضح. الاختبار test_compat_sunset_criteria.py يفشل بدونها.

from datetime import datetime, timezone

# وقت إنشاء طبقة التوافق (أول التزام: 97ea6f1 — 2026-10-14)
_COMPAT_LAYER_CREATED = "2026-10-14T00:00:00Z"

# قاموس lifecycle لكل وحدة توافق
COMPAT_LIFECYCLE = {
    "nexus_lifecycle": {
        "created": _COMPAT_LAYER_CREATED,
        "reason": "initialize_nexus() لا يستدعي engine.start() — الحالة تبقى initializing",
        "target_replacement": "nexus/main.py:initialize_nexus",
        "sunset_criteria": (
            "engine.start() مُدمج مباشرة في initialize_nexus() في "
            "nexus/main.py + 30 يوماً بدون استدعاء لـ backend/compat/nexus_lifecycle.py"
        ),
        "call_count": 0,
        "status": "active",
    },
    "guardian_api": {
        "created": _COMPAT_LAYER_CREATED,
        "reason": "guardian/ (5 ملفات) غير مربوطة بأي مدخل حي — إحياء عبر /guardian/status",
        "target_replacement": "backend/app.py (نقطة /guardian/status مباشرة)",
        "sunset_criteria": (
            "guardian/ يُستورد مباشرة في backend/app.py + نقطة /guardian/status "
            "مُسجّلة بدون طبقة توافق + 30 يوماً بدون استدعاء لـ compat"
        ),
        "call_count": 0,
        "status": "active",
    },
    "nexus_recommendations": {
        "created": "2026-10-14T00:00:00Z",  # الالتزام 9c6eb3c
        "reason": (
            "GET /nexus/recommendations الأصلي يعيد قائمة فارغة ثابتة رغم أن "
            "RecommendationEngine مسجل — توليد توصيات فعلية"
        ),
        "target_replacement": "nexus/api_gateway/router.py:get_recommendations",
        "sunset_criteria": (
            "المسار الأصلي /nexus/recommendations يُعيد التوصيات الفعلية مباشرة "
            "من router.py + 30 يوماً بدون استدعاء لـ compat"
        ),
        "call_count": 0,
        "status": "active",
    },
    "nexus_router_compat": {
        "created": "2026-10-14T00:00:00Z",  # الالتزام 213b224
        "reason": (
            "Middleware يُصلح المسار الأصلي GET /nexus/recommendations "
            "(FastAPI يُطابق أول route مسجّل أولاً)"
        ),
        "target_replacement": "nexus/api_gateway/router.py:get_recommendations",
        "sunset_criteria": (
            "المسار الأصلي يُعيد توصيات فعلية بدون middleware + "
            "30 يوماً بدون استدعاء"
        ),
        "call_count": 0,
        "status": "active",
    },
}


def get_lifecycle_summary() -> dict:
    """يُعيد ملخص lifecycle لكل وحدة compat (للعرض في /compat/status)."""
    return {
        "total_modules": len(COMPAT_LIFECYCLE),
        "active": sum(1 for v in COMPAT_LIFECYCLE.values() if v["status"] == "active"),
        "pending_sunset": sum(1 for v in COMPAT_LIFECYCLE.values() if v["status"] == "pending_sunset"),
        "legacy_retained": sum(1 for v in COMPAT_LIFECYCLE.values() if v["status"] == "legacy_retained"),
        "modules": COMPAT_LIFECYCLE,
    }


def record_call(module_name: str) -> None:
    """يُسجّل استدعاءً لوحدة compat (يُستخدم من decorator @compat_tracked)."""
    if module_name in COMPAT_LIFECYCLE:
        COMPAT_LIFECYCLE[module_name]["call_count"] += 1


def compat_tracked(name: str):
    """
    Decorator يُسجّل عدد الاستدعاءات لوحدة compat.
    يُستخدم على كل دالة/كلاس في compat لقياس الاستخدام الفعلي.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            record_call(name)
            return func(*args, **kwargs)
        # الحفاظ على اسم الدالة الأصلية (لا حذف للواجهة)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__compat_tracked__ = name
        return wrapper
    return decorator
