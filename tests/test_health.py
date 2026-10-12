"""R-401: اختبارات الإقلاع والصحة"""
import os
os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

from fastapi.testclient import TestClient
from app import app


def _client():
    # with-block يشغّل lifespan (يضبط app.state.orchestrator)
    return TestClient(app)


def test_root_serves_html():
    """الجذر يعيد واجهة HTML"""
    with _client() as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")


def test_health():
    """/health يعيد حالة صحية"""
    with _client() as client:
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy"


def test_status():
    """/status يعيد حالة النظام"""
    with _client() as client:
        r = client.get("/status")
        assert r.status_code == 200
        data = r.json()
        assert "orchestrator" in data
        assert "components" in data


def test_components_nexus():
    """/components/nexus يعيد حالة NexusCore المدمجة"""
    with _client() as client:
        r = client.get("/components/nexus")
        assert r.status_code == 200
        data = r.json()
        assert data["nexus"]["loaded"] is True
        assert len(data["nexus"]["components"]) > 10


def test_components_consciousness():
    """/components/consciousness يعمل"""
    with _client() as client:
        r = client.get("/components/consciousness")
        assert r.status_code == 200
