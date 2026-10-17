"""R-614: اختبارات محرك الردود السيادي (S-9) + أمان مفتاح API (S-5)."""
import os
os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app import app

MASTER_KEY = "test_master_key_1234567890abcdef"


def _client():
    return TestClient(app)


# ============================================================
# S-5: /api-key لا يكشف المفتاح أبداً
# ============================================================

def test_api_key_never_leaks_secret():
    """حتى مع مفتاح السيد الصحيح، لا يُكشف المفتاح — فقط البصمة."""
    with _client() as client:
        r = client.get("/api-key", headers={"X-API-Key": MASTER_KEY})
        assert r.status_code == 200
        data = r.json()
        assert "api_key" not in data
        assert "fingerprint" in data
        assert len(data["fingerprint"]) == 16
        assert "persistent" in data
        assert "source" in data


def test_api_key_rejects_wrong_master():
    """مفتاح سيد خاطئ → 403."""
    with _client() as client:
        r = client.get("/api-key", headers={"X-API-Key": "wrong"})
        assert r.status_code == 403


def test_api_key_requires_master():
    """بدون مفتاح سيد → 403."""
    with _client() as client:
        r = client.get("/api-key")
        assert r.status_code == 403


# ============================================================
# S-9: محرك الردود السيادي — ردود مبنية على حالة حية
# ============================================================

def test_sovereign_response_gathers_evidence():
    """gather_evidence يعيد لقطة من الحالة الحية."""
    from sovereign_response import gather_evidence
    ev = gather_evidence()
    assert "timestamp" in ev
    # الحقول قد تكون None إذا لم تُحمَّل المكونات، لكن المفاتيح موجودة دائماً
    for key in ("memory", "predictive", "risk", "simulation", "sovereign", "consciousness"):
        assert key in ev


def test_sovereign_response_status_reply():
    """رد status مبني على أرقام حقيقية."""
    from sovereign_response import build_reply
    reply = build_reply("status", "ما حالة النظام؟")
    assert "حالة النظام" in reply
    # يجب أن يحتوي على أرقام حية (ذاكرة أو تنبؤ أو مخاطر)
    assert any(marker in reply for marker in ("الذاكرة", "التنبؤ", "المخاطر", "المحاكاة", "المتحكم"))


def test_sovereign_response_greet_reply():
    """رد تحية شخصي."""
    from sovereign_response import build_reply
    reply = build_reply("greet", "مرحبا")
    assert "أهلاً" in reply or "جاهز" in reply


def test_sovereign_response_alert_reply():
    """رد تنبيه — لا ينهار أبداً."""
    from sovereign_response import build_reply
    reply = build_reply("alert", "تنبيه")
    assert reply  # دائماً رد غير فارغ


def test_sovereign_response_help_reply():
    """رد مساعدة يذكر القدرات الحقيقية."""
    from sovereign_response import build_reply
    reply = build_reply("help", "مساعدة")
    assert "حالة النظام" in reply and "تحليل" in reply


def test_sovereign_response_never_raises():
    """build_reply لا يرمي استثناء لأي نية."""
    from sovereign_response import build_reply
    for intent in ("greet", "help", "status", "analyze", "forecast", "alert", "stop", "unknown_xyz"):
        reply = build_reply(intent, "اختبار")
        assert isinstance(reply, str) and reply