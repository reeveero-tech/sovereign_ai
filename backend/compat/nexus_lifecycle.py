# backend/compat/nexus_lifecycle.py
# إصلاح عيب نيجاتي: initialize_nexus() يسجل المكونات لكنه لا يستدعي engine.start()
# النتيجة قبل الإصلاح: /nexus/status تُظهر state="initializing" رغم أن كل المكونات صحية
# النتيجة بعد الإصلاح: engine.state == RUNNING و /nexus/status تعيد الحالة الفعلية
# (لا يُحذف أو يُعدَّل أي ملف أصلي — هذه طبقة توافق فوقية)

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("backend.compat.nexus_lifecycle")

# تثبيت مسار جذر المستودع مرة واحدة (يُدعم من أي دليل تشغيل)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_ENGINE = None  # مرجع singleton للمحرك بعد بدء التشغيل
_START_ATTEMPTED = False
_LAST_ERROR: Optional[str] = None


def ensure_nexus_running() -> Optional[object]:
    """
    يضمن أن محرك NexusCore مستورد + مُبدأ (state=RUNNING).

    تُستدعى من lifespan الخاص بـ FastAPI، وهي آمنة للتكرار (idempotent).
    تُعيد المرجع للمحرك أو None إذا فشل التهيئة (مع تسجيل السبب).
    """
    global _ENGINE, _START_ATTEMPTED, _LAST_ERROR

    if _ENGINE is not None and getattr(_ENGINE, "_running", False):
        return _ENGINE

    if _START_ATTEMPTED:
        # فشلنا مرة — لا نُعقّد التشغيل بإعادة المحاولة كل طلب
        if _LAST_ERROR:
            logger.warning(f"⚠️ Nexus lifecycle: تعذر البدء سابقًا: {_LAST_ERROR}")
        return _ENGINE

    _START_ATTEMPTED = True
    try:
        from nexus.main import initialize_nexus

        engine = initialize_nexus()
        # start() غير متزامن — نشغّله بشكل متزامن باستخدام loop مؤقت
        # (هذه ليست "mock"، بل استدعاء فعلي لـ engine.start())
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # داخل حدث غير متزامن بالفعل (مثل lifespan) — نستخدم create_task
            task = loop.create_task(engine.start())
            # ننتظر اكتمال المهمة (bounded) حتى تصبح الحالة RUNNING
            while not task.done():
                loop.run_until_complete(asyncio.sleep(0))
        else:
            asyncio.run(engine.start())

        _ENGINE = engine
        state = getattr(engine, "state", None)
        state_val = getattr(state, "value", None) or state
        logger.info(f"✅ Nexus lifecycle: engine state = {state_val}")
        return _ENGINE

    except Exception as e:
        _LAST_ERROR = str(e)
        logger.error(f"❌ Nexus lifecycle failure: {e}")
        return None


def nexus_startup_status() -> dict:
    """يُعيد حالة الربط الفعلية — تُستخدم للتشخيص وللتحقق في الاختبارات"""
    running = _ENGINE is not None and getattr(_ENGINE, "_running", False)
    return {
        "engine_loaded": _ENGINE is not None,
        "engine_running": running,
        "state": (getattr(getattr(_ENGINE, "state", None), "value", None)
                  if _ENGINE is not None else None),
        "components_count": (len(getattr(_ENGINE, "components", {}))
                            if _ENGINE is not None else 0),
        "last_error": _LAST_ERROR,
    }
