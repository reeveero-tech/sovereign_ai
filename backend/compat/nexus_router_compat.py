# backend/compat/nexus_router_compat.py

# SUNSET_CRITERIA (المرحلة 4 من ROADMAP_V2 — نمط التين الخانق):
# معيار إزالة هذه الوحدة — تُنقل إلى backend/compat/_legacy/ (لا تُحذف أبدًا)
# عندما يتحقق: انظر backend/compat/__meta__.py → COMPAT_LIFECYCLE['nexus_router_compat']
# إصلاح المسار الأصلي GET /nexus/recommendations (R-615)
#
# المشكلة: المسار الأصلي في nexus/api_gateway/router.py يعيد قائمة فارغة
# ثابتة {"recommendations": [], "note": "Register engine first"} — رغم أن
# RecommendationEngine مسجل فعلاً كمكوّن 'recommender'. عملاء المسار الأصلي
# لا يحصلون على أي توصيات.
#
# الحل (طبقة توافق — لا تعديل للأصل): يُسجّل route جديد لنفس المسار
# الأصلي GET /nexus/recommendations يُعيد التوصيات المعلقة الفعلية من
# المكوّن المشترك. لا يُحذف أو يُعدّل الملف الأصلي.
#
# ملاحظة مهمة: FastAPI يسمح بتسجيل عدة routes لنفس المسار — آخر route
# مسجّل يُطابق أولاً. لذلك هذا المسار الجديد سيُطابق قبل المسار الأصلي
# (المسجل في nexus/api_gateway/router.py)، مما يُصلح المسار الأصلي فعليًا
# دون تعديل الملف الأصلي.

import logging
from typing import Optional

logger = logging.getLogger("backend.compat.nexus_router_compat")

from fastapi import APIRouter

# router بنفس prefix الأصلي — سيُسجّل بعد الأصلي ليُطابق أولاً
compat_router = APIRouter(prefix="/nexus", tags=["NexusCore"])


@compat_router.get("/recommendations")
def get_recommendations_original_path():
    """
    إصلاح المسار الأصلي GET /nexus/recommendations — يُعيد التوصيات
    المعلقة الفعلية من RecommendationEngine المسجل (recommender).
    (لا يُعدّل الملف الأصلي — هذه طبقة توافق تُسجّل بعد الأصلي.)
    """
    from backend.compat.nexus_recommendations import get_pending_recommendations

    result = get_pending_recommendations()
    # يحافظ على الواجهة الأصلية (recommendations + note) لكن بمحتوى فعلي
    if "error" in result:
        # المكوّن غير مسجل — يُعيد الواجهة الأصلية مع السبب
        return {
            "recommendations": [],
            "note": result["error"],
            "engine_id": result.get("engine_id"),
        }
    return {
        "recommendations": result["recommendations"],
        "note": "pending recommendations from live RecommendationEngine component",
        "engine_id": result.get("engine_id"),
        "pending_count": result.get("pending_count", 0),
    }


def register_compat_router(app) -> bool:
    """
    يُسجّل router التوافق على التطبيق — يُستدعى من backend/app.py بعد
    تسجيل NexusRouter الأصلي.

    ملاحظة مهمة: FastAPI يُطابق أول route مسجّل أولاً (وليس آخره) — لذلك
    مجرد تسجيل route جديد لنفس المسار لا يكفي. لذلك نستخدم middleware
    يُعيد التوجيه: إذا كان المسار /nexus/recommendations والاستجابة هي
    الاستجابة الثابتة الفارغة، نُعيد التوصيات الفعلية.
    (لا يُحذف أو يُعدّل الملف الأصلي — هذه طبقة توافق فوقية.)
    """
    try:
        # 1) تسجيل router التوافق (للمسارات الجديدة إن لزم)
        app.include_router(compat_router)

        # 2) middleware يُصلح المسار الأصلي فعليًا:
        #    إذا كان GET /nexus/recommendations والاستجابة هي القائمة الثابتة
        #    الفارغة، نُعيد التوصيات المعلقة الفعلية بدلها.
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import JSONResponse
        import json as _json

        _ORIGINAL_EMPTY_NOTE = "Register engine first"

        class FixOriginalRecommendationsMiddleware(BaseHTTPMiddleware):
            """
            يُصلح المسار الأصلي GET /nexus/recommendations — إذا كانت
            الاستجابة هي القائمة الفارغة الثابتة (التي تُعيد 'Register
            engine first' رغم أن المحرك مسجل)، نُعيد التوصيات الفعلية.
            """

            async def dispatch(self, request, call_next):
                response = await call_next(request)
                # فقط للمسار الأصلي GET /nexus/recommendations
                if (request.method == "GET"
                        and request.url.path.rstrip("/") == "/nexus/recommendations"):
                    # قراءة الاستجابة (stream) — نستخدم body_iterator
                    try:
                        body = b""
                        async for chunk in response.body_iterator:
                            body += chunk
                        try:
                            data = _json.loads(body)
                        except Exception:
                            data = None

                        # إذا كانت الاستجابة هي القائمة الفارغة الثابتة
                        if (isinstance(data, dict)
                                and data.get("note") == _ORIGINAL_EMPTY_NOTE
                                and data.get("recommendations") == []):
                            # نُعيد التوصيات الفعلية بدلاً منها
                            from backend.compat.nexus_recommendations import get_pending_recommendations
                            fixed = get_pending_recommendations()
                            if "error" not in fixed:
                                new_body = _json.dumps({
                                    "recommendations": fixed["recommendations"],
                                    "note": "pending recommendations from live RecommendationEngine component",
                                    "engine_id": fixed.get("engine_id"),
                                    "pending_count": fixed.get("pending_count", 0),
                                }, ensure_ascii=False, default=str).encode("utf-8")
                                return JSONResponse(
                                    content=_json.loads(new_body.decode("utf-8")),
                                    status_code=200,
                                )
                        # إعادة الاستجابة الأصلية (تم استهلاكها — نُعيدها)
                        from starlette.responses import Response as _Resp
                        return _Resp(
                            content=body,
                            status_code=response.status_code,
                            media_type=response.media_type,
                            headers=dict(response.headers),
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ recommendations middleware error: {e}")
                        return response
                return response

        app.add_middleware(FixOriginalRecommendationsMiddleware)
        logger.info("✅ Nexus recommendations compat middleware registered "
                    "(original GET /nexus/recommendations now returns live pending)")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to register compat router: {e}")
        return False
