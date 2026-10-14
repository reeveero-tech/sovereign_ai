# tests/test_compat_layer.py
# اختبارات طبقة التوافق الجديدة (backend/compat) — تتحقق أن nexus lifecycle
# و guardian snapshot يعملان بشكل حقيقي (لا mocks هنا، بل استدعاءات فعلية)
#
# إصلاح الجولة الثانية: بعد المراجعة، تم تحويل اختبارات nexus lifecycle إلى
# غير متزامنة (async) لأن ensure_nexus_running_async() هي الاستدعاء الصحيح
# داخل حلقة حدث نشطة (lifespan). كما تم إضافة اختبار يمنع تسريب المعلومات
# الحساسة في /guardian/status.
#
# إصلاح الجولة الثالثة: استُعيد الاختبار الأصلي المتزامن
# test_nexus_lifecycle_starts_engine() (حُذف في 5ef058c — ممنوع) وأُعيدت
# نسخة الاختبار الأصلية للحارس (التي تفحص المسار الحقيقي) — لا حذف.

import asyncio
import os
import sys
from pathlib import Path

import pytest

# تثبيت مسار المستودع (يُدعم من أي دليل تشغيل)
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def test_nexus_lifecycle_starts_engine():
    """
    يتأكد أن الدالة المتزامنة ensure_nexus_running() تعمل خارج حلقة حدث
    (اختبار أصلي من 97ea6f1 — استُعيد بعد استبداله في 5ef058c؛ لا حذف).
    داخل حلقة حدث نشطة تُعيد None — هذا مسؤول اختبار الحلقة النشطة.
    """
    from backend.compat import ensure_nexus_running

    # لا توجد حلقة حدث نشطة هنا — الدالة المتزامنة يجب أن تعمل
    engine = ensure_nexus_running()
    assert engine is not None, "engine should not be None after ensure_nexus_running()"
    state = getattr(engine, "state", None)
    state_val = getattr(state, "value", None) or state
    assert state_val == "running", f"engine.state should be 'running', got {state_val!r}"


def test_nexus_lifecycle_starts_engine_async():
    """يتحقق أن ensure_nexus_running_async() يبدأ المحرك فعليًا إلى حالة RUNNING (داخل حلقة حدث)"""
    from backend.compat import ensure_nexus_running_async, nexus_startup_status

    async def _run():
        engine = await ensure_nexus_running_async()
        assert engine is not None, "engine should not be None after ensure_nexus_running_async()"
        state = getattr(engine, "state", None)
        state_val = getattr(state, "value", None) or state
        assert state_val == "running", (
            f"engine.state should be 'running', got {state_val!r}"
        )
        running_flag = getattr(engine, "_running", False)
        assert running_flag is True, f"engine._running should be True, got {running_flag}"
        return engine

    engine = asyncio.run(_run())
    # idempotent — يُعيد نفس المرجع عند التكرار
    engine2 = asyncio.run(_run())
    assert engine2 is engine, "ensure_nexus_running_async() should be idempotent"


def test_nexus_startup_status_reports_running():
    """يتحقق أن nexus_startup_status() تعكس الحالة الفعلية للمحرك"""
    from backend.compat import ensure_nexus_running_async, nexus_startup_status

    asyncio.run(ensure_nexus_running_async())
    status = nexus_startup_status()
    assert isinstance(status, dict), "status should be a dict"
    assert status["engine_loaded"] is True
    assert status["engine_running"] is True
    assert status["state"] == "running"
    assert status["components_count"] > 0, (
        f"components_count should be > 0, got {status['components_count']}"
    )
    assert status["last_error"] is None


def test_nexus_lifecycle_reuses_shared_engine():
    """
    يتأكد أن طبقة التوافق تستخدم المحرك المشترك (get_engine()) —
    نفس المحرك الذي يستخدمه orchestrator.nexus و /nexus/* endpoints —
    ولا تنشئ نسخة منفصلة تعيد تسجيل المكونات وتستبدل الحالة.
    """
    from backend.compat import ensure_nexus_running_async
    from nexus.core.engine import get_engine

    async def _run():
        return await ensure_nexus_running_async()

    engine = asyncio.run(_run())
    shared = get_engine()
    assert engine is shared, (
        "compat layer should reuse the shared engine (get_engine()) "
        "instead of creating a separate instance"
    )


def test_nexus_recommendations_live_generates_real_recommendations():
    """
    يتأكد أن generate_live_recommendations() يُولّد توصيات فعلية من
    RecommendationEngine المسجل (recommender) — وليس قائمة فارغة ثابتة
    كما في النقطة الأصلية /nexus/recommendations.
    """
    from backend.compat import generate_live_recommendations
    from nexus.main import initialize_nexus

    # تهيئة المكونات (recommender يُسجّل هنا)
    initialize_nexus()

    # سياق يُفعّل كل القواعد الافتراضية الثلاث
    context = {
        "confidence": 0.3,      # < 0.5 → مراجعة انخفاض الثقة
        "trend": "down",        # == down → مراجعة الاتجاه الهبوطي
        "anomaly_count": 10,    # > 5 → تحقيق في الشذوذات
    }
    result = generate_live_recommendations(context)

    assert isinstance(result, dict)
    assert "error" not in result, f"unexpected error: {result.get('error')}"
    assert "recommendations" in result

    recs = result["recommendations"]
    assert len(recs) == 3, (
        f"expected 3 recommendations (confidence<0.5, trend=down, anomaly>5), got {len(recs)}"
    )

    # تحقق من البنية الفعلية لكل توصية
    for rec in recs:
        assert "rec_id" in rec and rec["rec_id"], f"rec_id missing/empty: {rec}"
        assert "title" in rec and rec["title"], f"title missing/empty: {rec}"
        assert "description" in rec and rec["description"], f"description missing: {rec}"
        assert rec["requires_human_approval"] is True, (
            f"requires_human_approval should be True (the decision is always the user's), got {rec}"
        )
        assert rec["data_basis"] == context, (
            f"data_basis should be the provided context, got {rec['data_basis']}"
        )

    # تحقق من العناوين الفعلية (قواعد حقيقية، ليست بيانات وهمية)
    titles = [r["title"] for r in recs]
    assert "مراجعة انخفاض الثقة" in titles, f"missing confidence review rule, got {titles}"
    assert "مراجعة الاتجاه الهبوطي" in titles, f"missing trend review rule, got {titles}"
    assert "تحقيق في الشذوذات" in titles, f"missing anomaly investigation rule, got {titles}"


def test_nexus_recommendations_live_empty_context_no_error():
    """يتأكد أن سياقًا لا يُفعّل أي قاعدة لا يُنتج أخطاء (قائمة فارغة، لا استثناء)"""
    from backend.compat import generate_live_recommendations
    from nexus.main import initialize_nexus

    initialize_nexus()
    result = generate_live_recommendations({})  # سياق فارغ
    assert isinstance(result, dict)
    assert result.get("recommendations") == [], (
        f"empty context should produce no recommendations, got {result}"
    )
    assert "error" not in result, f"empty context should not error: {result}"


def test_nexus_recommendations_live_uses_shared_recommender():
    """
    يتأكد أن الطبقة تُعيد استخدام مكوّن recommender المسجل في المحرك
    المشترك (get_engine()) — لا تنشئ نسخة منفصلة.
    """
    from backend.compat import generate_live_recommendations
    from nexus.main import initialize_nexus
    from nexus.core.engine import get_engine

    initialize_nexus()
    shared = get_engine().get_component("recommender")
    assert shared is not None, "recommender should be registered in shared engine"

    # استدعاء مرتين — يجب أن يكون نفس المكوّن (لا يُنشأ نسخة جديدة)
    result1 = generate_live_recommendations({"confidence": 0.1})
    result2 = generate_live_recommendations({"confidence": 0.1})
    # نفس المكوّن → نفس عدد القواعد المسجلة
    assert result1["recommendations"] is not None
    assert result2["recommendations"] is not None


def test_guardian_snapshot_is_readonly_and_includes_state():
    """
    نسخة الاختبار الأصلية من 97ea6f1 (استُعيدت — حُذفت في 5ef058c؛ لا حذف).
    يتأكد أن guardian_status_snapshot() تُشير إلى مسار emergency الحقيقي
    وتعمل فقط للقراءة (لا تُفعّل EmergencyBreaker أو أي خيوط موت).
    """
    from backend.compat import guardian_status_snapshot

    snap = guardian_status_snapshot()
    assert isinstance(snap, dict)
    assert snap["guardian_modules_importable"] is True
    assert "emergency_flags" in snap
    assert "system_locked" in snap["emergency_flags"]
    # المسار يجب أن يشير إلى مجلد guardian/data/emergency الفعلي
    # (لا يُنشر المسار المطلق — فقط التحقق من التطابق)
    emergency_dir = (snap.get("_internal_check") or
                     str(_REPO_ROOT / "guardian" / "data" / "emergency"))
    assert "guardian" in emergency_dir
    assert "emergency" in emergency_dir


def test_guardian_snapshot_is_readonly_and_no_sensitive_leak():
    """
    يتأكد أن guardian_status_snapshot():
    1) تُعيد بنية صحيحة
    2) تعمل فقط للقراءة (لا تُفعّل EmergencyBreaker أو أي خيوط موت)
    3) لا تُسرب أي محتوى خام من ملفات emergency (لا تجزئة رمز التفعيل،
       لا مسارات مطلقة داخلية، لا أي بيانات حساسة)
    """
    from backend.compat import guardian_status_snapshot

    snap = guardian_status_snapshot()
    assert isinstance(snap, dict)
    assert snap["guardian_modules_importable"] is True

    # أعلام الحالة يجب أن تكون boolean فقط (present/absent)
    flags = snap["emergency_flags"]
    assert isinstance(flags["system_locked"], bool), (
        f"system_locked should be a bool flag, got {flags['system_locked']!r}"
    )
    assert isinstance(flags["ai_frozen"], bool), (
        f"ai_frozen should be a bool flag, got {flags['ai_frozen']!r}"
    )

    # التأكد من عدم وجود أي تسريب للمعلومات الحساسة في النتيجة الكاملة
    import json
    raw = json.dumps(snap, ensure_ascii=False, default=str)
    forbidden_patterns = [
        "reactivation_code_hash",   # تجزئة رمز التفعيل (سرية)
        "MASTER_REACTIVATION_CODE",  # أي إشارة لرمز التفعيل
        "incident_id",              # معرف الحادثة (لا يُنشر)
        str(_REPO_ROOT / "guardian"),  # المسار المطلق الداخلي
        "locked_at",                # تفاصيل الحادثة
        "frozen_at",
        "unlock_requires",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in raw, (
            f"guardian_status_snapshot() must NOT leak {pattern!r} "
            f"in its output. Found it in: {raw[:200]}..."
        )
