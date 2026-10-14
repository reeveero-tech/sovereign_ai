"""R-401: اختبارات نقاط API والمصادقة"""
import os
os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

from fastapi.testclient import TestClient
from app import app

MASTER_KEY = "test_master_key_1234567890abcdef"


def _client():
    return TestClient(app)


def test_api_key_requires_master_key():
    """/api-key يرفض بدون مفتاح السيد"""
    with _client() as client:
        r = client.get("/api-key")
        assert r.status_code == 403


def test_api_key_with_master_key():
    """/api-key يعيد بصمة المفتاح (لا المفتاح نفسه) مع مفتاح السيد الصحيح"""
    with _client() as client:
        r = client.get("/api-key", params={"master_key": MASTER_KEY})
        assert r.status_code == 200
        data = r.json()
        # R-614/S-5: لا يُكشف المفتاح أبداً — فقط البصمة ومصدر الثبات
        assert "api_key" not in data
        assert "fingerprint" in data
        assert len(data["fingerprint"]) == 16
        assert "persistent" in data


def test_api_key_wrong_master_key():
    """/api-key يرفض مفتاح سيد خاطئ"""
    with _client() as client:
        r = client.get("/api-key", params={"master_key": "wrong_key"})
        assert r.status_code == 403


def test_orchestrator_cycle_requires_api_key():
    """/orchestrator/cycle يرفض بدون api_key"""
    with _client() as client:
        r = client.post("/orchestrator/cycle", json={})
        assert r.status_code == 401


def test_orchestrator_cycle_with_api_key():
    """/orchestrator/cycle يعمل مع api_key"""
    with _client() as client:
        r = client.post("/orchestrator/cycle", json={"api_key": MASTER_KEY})
        assert r.status_code == 200
        data = r.json()
        assert "success" in data


def test_sovereign_command_requires_api_key():
    """/sovereign/command يرفض بدون api_key (422 تحقق)"""
    with _client() as client:
        r = client.post("/sovereign/command", json={"command": "get_status"})
        assert r.status_code == 422


def test_sovereign_command_wrong_api_key():
    """/sovereign/command يرفض api_key خاطئ (401)"""
    with _client() as client:
        r = client.post("/sovereign/command", json={"command": "get_status", "api_key": "wrong"})
        assert r.status_code == 401


def test_sovereign_command_with_api_key():
    """/sovereign/command يعمل مع api_key"""
    with _client() as client:
        r = client.post("/sovereign/command", json={"command": "get_status", "api_key": MASTER_KEY})
        assert r.status_code == 200
