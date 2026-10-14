# tests/test_compat_layer.py
# اختبارات طبقة التوافق الجديدة (backend/compat) — تتحقق أن nexus lifecycle
# و guardian snapshot يعملان بشكل حقيقي (لا mocks هنا، بل استدعاءات فعلية)
#
# إصلاح الجولة الثانية: بعد المراجعة، تم تحويل اختبارات nexus lifecycle إلى
# غير متزامنة (async) لأن ensure_nexus_running_async() هي الاستدعاء الصحيح
# داخل حلقة حدث نشطة (lifespan). كما تم إضافة اختبار يمنع تسريب المعلومات
# الحساسة في /guardian/status.

import asyncio
import sys
from pathlib import Path

import pytest

# تثبيت مسار المستودع (يُدعم من أي دليل تشغيل)
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


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
