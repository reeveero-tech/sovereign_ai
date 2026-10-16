# backend/compat/nexus_lifecycle.py

# SUNSET_CRITERIA (المرحلة 4 من ROADMAP_V2 — نمط التين الخانق):
# معيار إزالة هذه الوحدة — تُنقل إلى backend/compat/_legacy/ (لا تُحذف أبدًا)
# عندما يتحقق: انظر backend/compat/__meta__.py → COMPAT_LIFECYCLE['nexus_lifecycle']
# إصلاح عيب نيجاتي: initialize_nexus() يسجل المكونات لكنه لا يستدعي engine.start()
# النتيجة قبل الإصلاح: /nexus/status تُظهر state="initializing" رغم أن كل المكونات صحية
# النتيجة بعد الإصلاح: engine.state == RUNNING و /nexus/status تعيد الحالة الفعلية
# (لا يُحذف أو يُعدَّل أي ملف أصلي — هذه طبقة توافق فوقية)

# إصلاح الجولة الثانية: طبقة التوافق السابقة استدعت loop.run_until_complete()
# داخل حلقة حدث نشطة، ففشلت بـ RuntimeError("This event loop is already running")
# وأعادت None من lifespan — رغم أن curl لاحقًا أظهر state=running (نتيجة غير حاسمة).
# هذا التنقيح يجعل عملية البدء غير متزامنة (async) بالكامل ويستخدم المحرك
# الموجود مسبقًا في orchestrator.nexus بدل استدعاء initialize_nexus() مجددًا
# (الاستدعاء الثاني يعيد تسجيل المكونات وقد يستبدل حالتها).

import asyncio
import logging

# الجولة الإنشائية 2026-10-16: تسجيل الاستدعاءات (المرحلة 4 — ROADMAP_V2)
from backend.compat.__meta__ import compat_tracked
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("backend.compat.nexus_lifecycle")

# تثبيت مسار جذر المستودع مرة واحدة (يُدعم من أي دليل تشغيل)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_ENGINE = None           # مرجع المحرك بعد نجاح البدء
_START_ERROR: Optional[str] = None
_LAST_START_TIME: float = 0.0


@compat_tracked("nexus_lifecycle")
async def start_nexus_engine(engine) -> bool:
    """
    يبدأ محرك NexusCore فعليًا (استدعاء حقيقي لـ engine.start()).
    يُعيد True إذا نجح البدء (الحالة صارت RUNNING)، أو False إذا فشل.
    """
    try:
        await engine.start()
        state = getattr(engine, "state", None)
        state_val = getattr(state, "value", None) or state
        logger.info(f"✅ Nexus lifecycle: engine state = {state_val}")
        return state_val == "running"
    except Exception as e:
        logger.error(f"❌ Nexus lifecycle start failure: {e}")
        return False


@compat_tracked("nexus_lifecycle")
async def ensure_nexus_running_async() -> Optional[object]:
    """
    يضمن أن محرك NexusCore مستورد + مُبدأ (state=RUNNING).

    هذا هو الاستدعاء الصحيح من lifespan الخاص بـ FastAPI (داخل حلقة حدث نشطة).
    يُعيد المرجع للمحرك أو None إذا فشل التهيئة (مع تسجيل السبب).

    ملاحظة مهمة: يستخدم المحرك المشترك في get_engine() — نفس المحرك الذي
    يستخدمه orchestrator.nexus و /nexus/* endpoints — حتى لا تُنشأ نسخة
    منفصلة تعيد تسجيل المكونات وتستبدل الحالة.

    إذا لم تكن المكونات مسجلة (engine فارغ)، يقوم بتهيئتها عبر
    initialize_nexus() (وهي المسؤولة عن تسجيل 47 مكونًا في get_engine()).
    """
    global _ENGINE, _START_ERROR, _LAST_START_TIME

    if _ENGINE is not None:
        # المحرك مُبدأ سابقًا — تحقق فقط من أنه ما زال يعمل
        if getattr(_ENGINE, "_running", False):
            return _ENGINE
        # المحرك مُوقف — أعد البدء (idempotent + يمكن إعادة التشغيل بعد الإيقاف)
        logger.info("🔄 Nexus lifecycle: engine stopped, restarting...")
    else:
        # أول تهيئة — احصل على المحرك المشترك
        try:
            from nexus.core.engine import get_engine
            _ENGINE = get_engine()
            logger.info(
                f"🔗 Nexus lifecycle: using shared engine "
                f"(id={getattr(_ENGINE, 'engine_id', '?')}, "
                f"components={len(getattr(_ENGINE, 'components', {}))})"
            )
        except Exception as e:
            _START_ERROR = str(e)
            logger.exception(f"R-682: Nexus lifecycle init failure — silently swallowing. exc={e}")
            return None

    # إذا كان المحرك فارغًا (لا مكونات مسجلة)، قم بتهيئة المكونات
    # (get_engine() يُنشئ محركًا فارغًا — initialize_nexus() هو من يسجل المكونات)
    if not getattr(_ENGINE, "components", {}):
        logger.info(
            "📦 Nexus lifecycle: engine has no components — "
            "initializing via initialize_nexus()..."
        )
        try:
            from nexus.main import initialize_nexus
            # initialize_nexus يُعيد نفس المحرك المشترك (get_engine())
            # ويُسجّل المكونات فيه
            initialized = initialize_nexus()
            if initialized is not _ENGINE:
                logger.warning(
                    "⚠️ Nexus lifecycle: initialize_nexus() returned a different "
                    "engine instance than get_engine() — replacing reference"
                )
                _ENGINE = initialized
            logger.info(
                f"✅ Nexus lifecycle: components initialized "
                f"({len(_ENGINE.components)} components)"
            )
        except Exception as e:
            _START_ERROR = str(e)
            logger.exception(f"R-682: Nexus lifecycle component init failure — silently swallowing. exc={e}")
            return None

    _LAST_START_TIME = asyncio.get_running_loop().time()
    ok = await start_nexus_engine(_ENGINE)
    if ok:
        _START_ERROR = None
        return _ENGINE
    _START_ERROR = "engine.start() did not reach RUNNING state"
    return None


@compat_tracked("nexus_lifecycle")
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
        "last_error": _START_ERROR,
        "last_start_time": _LAST_START_TIME,
    }


# توافق رجعي: الدالة المتزامنة القديمة تُستخدم فقط في الاختبارات التي
# تعمل خارج حلقة حدث. داخل حلقة نشطة يجب استخدام ensure_nexus_running_async().
@compat_tracked("nexus_lifecycle")
def ensure_nexus_running() -> Optional[object]:
    """
    نسخة متزامنة للتوافق — تُستخدم فقط عندما لا توجد حلقة حدث نشطة
    (مثل الاختبارات). داخل lifespan يجب استخدام ensure_nexus_running_async().
    """
    import asyncio as _asyncio
    try:
        loop = _asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        # حلقة نشطة — استدعاء النسخة غير المتزامنة عبر run_coroutine_threadsafe
        # أو ببساطة فشل واضح مع رسالة تفصيلية
        logger.error(
            "❌ ensure_nexus_running() called inside a running event loop. "
            "Use ensure_nexus_running_async() from async context (lifespan)."
        )
        return None
    return _asyncio.run(ensure_nexus_running_async())
