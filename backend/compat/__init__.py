# backend/compat/__init__.py
# طبقة التوافق — تجميع طبقات الربط والترابط بين المكونات
# الغرض: إحياء المكونات اليتيمة وربطها بمداخل فعلية دون تعديل الكود الأصلي
# تُستخدم من backend/app.py (lifespan) و tests/
from .nexus_lifecycle import ensure_nexus_running, nexus_startup_status
from .guardian_api import guardian_status_snapshot

__all__ = ["ensure_nexus_running", "nexus_startup_status", "guardian_status_snapshot"]
