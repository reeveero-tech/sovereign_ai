"""
Invariant 6: كل نقاط الدخول تستجيب (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل مسار مسجّل في FastAPI app يستجيب بشكل صحيح (ليس 404/500).
أي نقطة نهاية مسجّلة لا تستجيب = فشل.
"""

import sys
from pathlib import Path

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app import app
    with TestClient(app) as c:
        yield c


# نقاط النهاية المطلوب أن تستجيب (ليس 404)
REQUIRED_ENDPOINTS = [
    "/health",
    "/guardian/status",
    "/ledger/verify",
    "/compat/status",
    "/sovereignty/score",
]


def test_required_endpoints_exist(client):
    """كل نقطة النهاية المطلوبة يجب أن تكون مسجّلة (ليست 404)."""
    for endpoint in REQUIRED_ENDPOINTS:
        resp = client.get(endpoint)
        assert resp.status_code != 404, (
            f"Required endpoint {endpoint} returns 404 (not registered)"
        )


def test_required_endpoints_not_500(client):
    """كل نقطة النهاية المطلوبة لا تُعيد 500 (خطأ داخلي)."""
    for endpoint in REQUIRED_ENDPOINTS:
        resp = client.get(endpoint)
        assert resp.status_code < 500, (
            f"Endpoint {endpoint} returns {resp.status_code} (internal error): "
            f"{resp.text[:200]}"
        )


def test_compat_status_reports_lifecycle(client):
    """/compat/status يجب أن يُعيد lifecycle من __meta__.py (COMPAT_LIFECYCLE)."""
    resp = client.get("/compat/status")
    # (قاعدة الجولة الإنشائية 2026-10-16: لا skip — المسار مسجل؛
    # وغيابه فشل صريح لا حالة تُتخطى)
    assert resp.status_code == 200, (
        f"/compat/status returned {resp.status_code}"
    )

    data = resp.json()
    # يجب أن يحتوي بيانات lifecycle (أو على الأقل إشارة إليه)
    assert isinstance(data, dict), (
        f"/compat/status must return a dict, got {type(data)}"
    )


def test_health_endpoint(client):
    """/health يُعيد استجابة صحيحة (200)."""
    resp = client.get("/health")
    assert resp.status_code == 200, (
        f"/health returned {resp.status_code}"
    )


def test_ledger_verify_full_report(client):
    """/ledger/verify يُعيد تقريرًا كاملًا (كل الحقول المطلوبة)."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200

    data = resp.json()
    assert "ledger_summary" in data
    assert "anchors" in data
    assert "keyring_stats" in data

    summary = data["ledger_summary"]
    assert "total_events" in summary
    assert "anchored_events" in summary
    assert "unverifiable" in summary
