# backend/compat/guardian_api.py
# إحياء وحدات guardian/ (MasterGuardian, EmergencyBreaker, IntegrityChecker, SelfEvolver)
# المشكلة الأصلية: هذه الوحدات موجودة وكاملة لكنها غير مستدعاة من أي مدخل حي.
# الإصلاح (طبقة توافق — لا تعديل للأصل): تُزوّد لحظة حالة للقراءة فقط
# بحيث يصبح نظام الحارس مُتاحًا عبر /guardian/status دون أن يُفعّل EmergencyBreaker
# تلقائيًا (لأن هذا سيجمّد النظام أثناء التطوير).

import logging
import os
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


def _read_flag(path: Path) -> Optional[dict]:
    """يقرأ ملف علم/قفل الحارس إن وُجد — يُعيد None إذا لم يكن موجودًا"""
    try:
        if path.is_file():
            import json
            return {"present": True, "content": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as e:
        return {"present": True, "error": str(e)}
    return None


def guardian_status_snapshot() -> dict:
    """
    يُعيد لحظة حالة نظام الحارس (قراءة فقط — لا يُفعّل أي إجراء).
    يُستخدم لعرض /guardian/status والتشخيص دون المساس بحالة التشغيل.
    """
    try:
        # محاولة استيراد الحارس (اختياري — يفشل بسلام إذا وُجد خلل)
        from guardian import MasterGuardian, EmergencyBreaker, IntegrityChecker
        modules_ok = True
    except Exception as e:
        logger.warning(f"⚠️ Guardian import failed: {e}")
        modules_ok = False

    snapshot = {
        "guardian_modules_importable": modules_ok,
        "emergency_state": {
            "system_locked": _read_flag(_EMERGENCY_DIR / "SYSTEM_LOCKED.lock"),
            "ai_frozen": _read_flag(_EMERGENCY_DIR / "AI_FROZEN.flag"),
            "emergency_dir": str(_EMERGENCY_DIR),
        },
        "timestamp": time.time(),
    }
    return snapshot
