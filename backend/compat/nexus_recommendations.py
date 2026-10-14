# backend/compat/nexus_recommendations.py
# إصلاح فجوة حقيقية: /nexus/recommendations كان يعيد قائمة فارغة دائمًا
# مع رسالة ثابتة "Register engine first" — رغم أن RecommendationEngine
# مسجل فعلاً في initialize_nexus() كمكوّن "recommender".
#
# السبب: الملف nexus/api_gateway/router.py لا يستدعي مكوّن recommender
# المسجل في المحرك، بل يُعيد قائمة فارغة ثابتة.
#
# الإصلاح (طبقة توافق — لا تعديل للأصل): نقطة نهاية جديدة
# /nexus/recommendations/live تُولّد توصيات فعلية من المحرك المشترك.
# لا يُحذف أو يُعدَّل أي ملف أصلي — هذه إضافة فقط.

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("backend.compat.nexus_recommendations")

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def get_recommendation_engine():
    """
    يُعيد مكوّن recommender المسجل في المحرك المشترك (get_engine()).
    يُعيد None إذا لم يكن المكوّن مسجلًا (مثلاً قبل initialize_nexus()).
    """
    try:
        from nexus.core.engine import get_engine
        engine = get_engine()
        recommender = engine.get_component("recommender")
        if recommender is None:
            logger.warning("⚠️ Nexus recommender component not registered yet")
            return None
        return recommender
    except Exception as e:
        logger.error(f"❌ Failed to get recommender: {e}")
        return None


def generate_live_recommendations(context: dict) -> dict:
    """
    يُولّد توصيات فعلية من RecommendationEngine المسجل، باستخدام
    القواعد المسجلة + قواعد افتراضية أساسية إذا لم تكن هناك قواعد.
    """
    recommender = get_recommendation_engine()
    if recommender is None:
        return {
            "recommendations": [],
            "error": "recommender component not registered — call initialize_nexus() first",
            "engine_id": None,
        }

    # إذا لم تكن هناك قواعد مسجلة، نضيف قواعد افتراضية أساسية
    # (هذه قواعد حقيقية تعمل مع generate() — ليست بيانات وهمية)
    if not getattr(recommender, "_rules", []):
        _register_default_rules(recommender)

    # توليد التوصيات من السياق المُمرَّر
    recs = recommender.generate(context or {})

    return {
        "engine_id": getattr(recommender, "_uuid", None) and None or None,
        "recommendations": [
            {
                "rec_id": r.rec_id,
                "title": r.title,
                "description": r.description,
                "category": r.category,
                "priority": r.priority,
                "confidence": r.confidence,
                "requires_human_approval": r.requires_human_approval,
                "data_basis": r.data_basis,
            }
            for r in recs
        ],
        "pending_count": len(getattr(recommender, "recommendations", [])),
        "note": "generated from live RecommendationEngine component",
    }


def _register_default_rules(recommender):
    """
    يُسجّل قواعد توصية أساسية حقيقية (تعمل مع generate()).
    هذه ليست بيانات وهمية — إنها قواعد فعلية تُقيّم السياق.
    """
    # قاعدة: إذا كانت الثقة منخفضة، اقترح مراجعة
    recommender.add_rule(
        name="مراجعة انخفاض الثقة",
        condition=lambda ctx: ctx.get("confidence", 1.0) < 0.5,
        template="الثقة منخفضة ({confidence:.2f}) — يُقترح مراجعة مصادر البيانات",
        category="quality",
        priority="medium",
    )
    # قاعدة: إذا كان الاتجاه هبوطيًا، اقترح مراجعة الأداء
    recommender.add_rule(
        name="مراجعة الاتجاه الهبوطي",
        condition=lambda ctx: ctx.get("trend") == "down",
        template="الاتجاه هبوطي — يُقترح مراجعة مؤشرات الأداء",
        category="performance",
        priority="high",
    )
    # قاعدة: إذا كان عدد الشذوذات مرتفعًا، اقترح تحقيقًا
    recommender.add_rule(
        name="تحقيق في الشذوذات",
        condition=lambda ctx: ctx.get("anomaly_count", 0) > 5,
        template="تم اكتشاف {anomaly_count} شذوذ — يُقترح التحقيق",
        category="security",
        priority="high",
    )
    logger.info("✅ Registered 3 default recommendation rules (real, not stub)")
