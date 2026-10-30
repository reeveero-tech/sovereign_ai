"""R-816 (أمر المالك «إحياء كل ما هو ميت»): عقد الولاء حي في النظام

backend/Mr.py (عقد الولاء المعقّم — R-686) كان غير مربوط بالنظام الحي
(أمر المالك: المرحلة ١). أمر الإحياء يوصله:
1. الإقلاع يهيئ العقد ويربطه بمادة مفتاح السيد المشتق (بلا خام — بصمة
   هاش فقط داخل العقد)، ومحاولة الربط المزدوج مستحيلة (يُربط فقط إذا
   كان بلا سيد — حارسة bind_master نفسها).
2. GET /loyalty/status — لقطة علنية صادقة (بلا أي سر).
3. POST /loyalty/release — رفع العزل للسيد وحده بمفتاحه، ورفع غير مصرح
   به يُرفض ويُسجل (401 قبل أي منطق عقد).
4. العقد عزل لا موت: أي خلل في الإحياء يُعلن ولا يكسر الإقلاع.
"""
import os
os.environ.setdefault("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")

from fastapi.testclient import TestClient
from app import app
from Mr import get_contract


def _client():
    # with-block يشغّل lifespan (يهيئ العقد ويربطه بالسيد — R-816)
    return TestClient(app)


def test_boot_binds_loyalty_to_master():
    """الإقلاع يربط عقد الولاء بالسيد — الحالة SEALED بعد دورة الحياة"""
    with _client() as client:
        s = get_contract().get_status()
        assert s["master_bound"] is True
        assert s["state"] in ("sealed", "quarantined"), s
        assert s["death_paths"] == 0


def test_loyalty_status_endpoint_honest():
    """/loyalty/status يعيد لقطة صادقة مطابقة لحالة العقد الفعلية"""
    with _client() as client:
        r = client.get("/loyalty/status")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        inner = data["data"]
        contract = get_contract().get_status()
        assert inner["state"] == contract["state"]
        assert inner["loyal"] == contract["loyal"]
        assert inner["master_bound"] == contract["master_bound"]
        assert inner["violations_count"] == contract["violations_count"]
        # لا سر في اللقطة: المفتاح الخام لا يظهر أبدًا
        assert os.environ.get("SOVEREIGN_KEY") not in r.text


def test_release_requires_owner_key():
    """رفع العزل محمي بمفتاح المالك — بلا مفتاح: 401 قبل أي منطق عقد"""
    with _client() as client:
        r = client.post("/loyalty/release", json={"decision": "محاولة بلا مفتاح"})
        assert r.status_code == 401
        # لم يُسجل أي انتهاك — الطلب رُفض على البوابة قبل العقد
        assert get_contract().get_status()["violations_count"] == 0


def test_release_with_owner_key_executes():
    """بمفتاح المالك الصحيح يُنفذ أمر الرفع (يُرفض بصدق إن لم يكن معزولًا)"""
    with _client() as client:
        from config import SOVEREIGN_KEY
        from sovereign.keys.derivation import derive_key_hex
        owner_key = derive_key_hex("api_auth")
        r = client.post(
            "/loyalty/release",
            json={"decision": "اختبار رفع إيجابي"},
            headers={"X-Sovereign-Key": owner_key},
        )
        assert r.status_code == 200
        data = r.json()
        # العقد ليس معزولًا في الاختبار ⇒ الرفض صادق لا صامت
        assert data["released"] is False
        assert data["state"] in ("sealed", "bound")


def test_double_bind_guard_survives_boot_reentry():
    """إعادة دخول دورة الحياة لا تربط مرتين — حارسة bind_master تعمل"""
    with _client() as client:
        first = get_contract().get_status()
        assert first["master_bound"] is True
    with _client() as client:  # إقلاع ثانٍ في العملية نفسها
        second = get_contract().get_status()
        assert second["master_bound"] is True
        # لا انتهاك ربط مزدوج — الربط الشرطي في الإقلاع يعمل
        kinds = [v.get("kind") for v in get_contract().get_violations()]
        assert "double_bind" not in kinds
