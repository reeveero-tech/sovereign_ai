# tests/test_nexus_lifecycle_integration.py
# اختبار تكامل حقيقي لدورة حياة NexusCore عبر FastAPI TestClient
# (يُغطي الملاحظات: بدء التشغيل، المحرك المشترك بين المنسق والمسارات،
#  حالة running، بقاء المكونات وحالتها، ثم الإيقاف)
#
# هذا ليس اختبار الدالة المساعدة فقط — بل يمر عبر دورة حياة FastAPI
# الفعلية (startup → requests → shutdown).

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """يشغل الخادم عبر TestClient — يُفعّل lifespan فعليًا"""
    from app import app  # noqa: E402 — بعد تثبيت المسار
    with TestClient(app) as c:
        yield c


def test_nexus_lifecycle_full_cycle_via_fastapi(client):
    """
    يتحقق من دورة حياة NexusCore الكاملة عبر FastAPI الحقيقي:
    1) بدء التشغيل (lifespan يُشغّل ensure_nexus_running_async)
    2) المحرك المشترك بين المنسق (orchestrator) والمسارات (/nexus/*)
    3) الحالة running (وليست initializing)
    4) بقاء المكونات وحالتها
    5) الإيقاف (lifespan shutdown)
    """
    # 1) الحالة بعد بدء التشغيل
    resp = client.get("/nexus/status")
    assert resp.status_code == 200, f"/nexus/status failed: {resp.status_code}"
    status = resp.json()
    assert status["state"] == "running", (
        f"nexus state should be 'running' after lifespan startup, got {status['state']!r}"
    )
    assert len(status["components"]) > 0, (
        f"components should be registered, got {len(status['components'])}"
    )

    # 2) المحرك المشترك بين المنسق والمسارات
    from orchestrator import get_orchestrator
    from nexus.core.engine import get_engine
    from backend.compat import ensure_nexus_running_async
    import asyncio

    orch = get_orchestrator()
    nexus_from_orchestrator = getattr(orch, "nexus", None)
    shared_engine = get_engine()
    assert nexus_from_orchestrator is not None, "orchestrator.nexus should be loaded"
    assert nexus_from_orchestrator is shared_engine, (
        "orchestrator.nexus should be the SAME engine instance as get_engine() "
        "(shared engine, not a separate instance)"
    )

    # 3) الحالة عبر طبقة التوافق (بعد lifespan — يجب أن تكون running)
    status_via_compat = asyncio.run(ensure_nexus_running_async())
    assert status_via_compat is not None
    assert getattr(status_via_compat, "_running", False) is True
    state_val = getattr(getattr(status_via_compat, "state", None), "value", None)
    assert state_val == "running"

    # 4) بقاء المكونات (47 على الأقل في التهيئة الكاملة)
    assert len(shared_engine.components) >= 40, (
        f"shared engine should have >=40 components, got {len(shared_engine.components)}"
    )

    # 5) الإيقاف — lifespan shutdown يُستدعى تلقائيًا عند الخروج من
    #    كتلة `with TestClient(app)`. لا نتحقق من stop() يدويًا لأنه
    #    سيُعطّل المحرك المشترك للاختبارات الأخرى.


def test_nexus_recommendations_via_http_after_lifespan(client):
    """يتحقق أن /nexus/recommendations/live يعمل بعد بدء التشغيل الفعلي"""
    resp = client.post(
        "/nexus/recommendations/live",
        json={"confidence": 0.3, "trend": "down", "anomaly_count": 10},
    )
    assert resp.status_code == 200, f"failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "error" not in data, f"unexpected error: {data.get('error')}"
    recs = data["recommendations"]
    assert len(recs) == 3, f"expected 3 recommendations, got {len(recs)}"
    # معرف المحرك يجب أن يكون حقيقيًا (وليس None)
    assert data["engine_id"] is not None, (
        f"engine_id should be the real engine id, got {data['engine_id']!r}"
    )


def test_nexus_recommendations_pending_via_http(client):
    """يتحقق أن /nexus/recommendations/pending يُعيد التوصيات المعلقة الفعلية"""
    # أولًا: توليد توصيات عبر live
    resp_gen = client.post(
        "/nexus/recommendations/live",
        json={"confidence": 0.3, "trend": "down", "anomaly_count": 10},
    )
    assert resp_gen.status_code == 200
    generated = resp_gen.json()["recommendations"]
    assert len(generated) == 3

    # ثانيًا: التوصيات المولدة يجب أن تظهر في /pending
    resp_pending = client.get("/nexus/recommendations/pending")
    assert resp_pending.status_code == 200
    pending_data = resp_pending.json()
    assert "error" not in pending_data, f"unexpected error: {pending_data.get('error')}"
    # التوصيات المولدة تُضاف إلى recommender.recommendations → تظهر في pending
    assert pending_data["pending_count"] >= 3, (
        f"pending_count should be >= 3 (generated recommendations), got {pending_data['pending_count']}"
    )
    assert len(pending_data["recommendations"]) >= 3
    # معرف المحرك الحقيقي
    assert pending_data["engine_id"] is not None


def test_nexus_and_guardian_endpoints_alive(client):
    """يتأكد أن كل نقاط النهاية المُحيَاة تعمل بعد دورة حياة حقيقية"""
    # nexus
    r1 = client.get("/nexus/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "healthy"

    # guardian (قراءة فقط)
    r2 = client.get("/guardian/status")
    assert r2.status_code == 200
    g = r2.json()
    assert g["guardian_modules_importable"] is True
    assert isinstance(g["emergency_flags"]["system_locked"], bool)
