# backend/compat/guardian_api.py

# SUNSET_CRITERIA (المرحلة 4 من ROADMAP_V2 — نمط التين الخانق):
# معيار إزالة هذه الوحدة — تُنقل إلى backend/compat/_legacy/ (لا تُحذف أبدًا)
# عندما يتحقق: انظر backend/compat/__meta__.py → COMPAT_LIFECYCLE['guardian_api']
# إحياء وحدات guardian/ (MasterGuardian, EmergencyBreaker, IntegrityChecker, SelfEvolver)
# المشكلة الأصلية: هذه الوحدات موجودة وكاملة لكنها غير مستدعاة من أي مدخل حي.
# الإصلاح (طبقة توافق — لا تعديل للأصل): تُزوّد لحظة حالة للقراءة فقط
# بحيث يصبح نظام الحارس مُتاحًا عبر /guardian/status دون أن يُفعّل EmergencyBreaker
# تلقائيًا (لأن هذا سيجمّد النظام أثناء التطوير).
#
# إصلاح الجولة الثانية (ملاحظات المراجعة): كانت النسخة الأولى تعيد محتويات
# ملفات القفل الخام (بما فيها reactivation_code_hash والمسارات المطلقة الداخلية).
# هذا تسريب معلومات حساسة عبر نقطة نهاية عامة. النسخة الحالية تُعيد فقط
# أعلام حالة تشخيصية غير حساسة (present / locked / frozen) دون أي محتوى خام.

import logging
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("backend.compat.guardian_api")

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_EMERGENCY_DIR = _REPO_ROOT / "guardian" / "data" / "emergency"


def _flag_present(path: Path) -> bool:
    """
    يتحقق فقط من وجود ملف علم/قفل الحارس — لا يقرأ محتواه.
    (لا يُعيد reactivation_code_hash أو أي بيانات حساسة)
    """
    try:
        return path.is_file()
    except Exception as e:
        logger.warning(f"⚠️ Guardian flag check failed for {path.name}: {e}")
        return False


def guardian_status_snapshot() -> dict:
    """
    يُعيد لحظة حالة نظام الحارس (قراءة فقط — لا يُفعّل أي إجراء).
    تُستخدم لعرض /guardian/status والتشخيص دون المساس بحالة التشغيل.
    لا تُعيد أي محتوى خام من ملفات emergency — فقط أعلام الحضور.
    """
    try:
        # محاولة استيراد الحارس (اختياري — يفشل بسلام إذا وُجد خلل)
        from guardian import MasterGuardian, EmergencyBreaker, IntegrityChecker
        modules_ok = True
    except Exception as e:
        logger.warning(f"⚠️ Guardian import failed: {e}")
        modules_ok = False

    # أعلام تشخيصية فقط — لا محتوى خام، لا مسارات مطلقة، لا تجزئات
    snapshot = {
        "guardian_modules_importable": modules_ok,
        "emergency_flags": {
            # فقط present/absent — لا يُعاد أي محتوى الملف
            "system_locked": _flag_present(_EMERGENCY_DIR / "SYSTEM_LOCKED.lock"),
            "ai_frozen": _flag_present(_EMERGENCY_DIR / "AI_FROZEN.flag"),
        },
        "note": "read-only diagnostic snapshot; no raw emergency file contents are exposed",
        "timestamp": time.time(),
    }
    return snapshot
