"""جولة مجلس المراجعين <1> — الأمان.

RED أولًا (قواعد الأمر الدائم): كل اختبار هنا يثبت فجوة أثبتها المجلس
بتشغيل فعلي (forensics/council/round-1/RAW_*.md) ثم يُغلق بإصلاح GREEN.
الاختبارات سلوكية: تعمل على شجرة الأساس 4bc5500 (تفشل بسبب السلوك
الأمني نفسه، لا بسبب أخطاء توقيع/واجهة) — تحقُّق RED أُعيد على شجرة
الأساس في worktree معزول وسُجل في PROCESSING.md.

القواعد: monkeypatch لكل ثابت وحدة يُعدَّل (لا تلوث للاختبارات اللاحقة)،
وتأكيدات محددة (اسم المسجّل + نص الرسالة المحقونة حرفيًا).
"""
import os
import sys
import json
import hashlib
import logging
import tempfile
import stat as statmod
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

MASTER_KEY = os.environ.get("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


# =====================================================================
# 1) عبارة الحارس الافتراضية (أمين 6.1 / بصير BAS-S03 / حكيم)
# =====================================================================

def test_master_guardian_rejects_missing_passphrase():
    """MasterGuardian بلا عبارة مرور يجب أن يرفض البناء (فشل مغلق) — لا عبارة افتراضية."""
    from guardian.master_guardian import MasterGuardian
    with pytest.raises(ValueError):
        MasterGuardian(guardian_dir=tempfile.mkdtemp())


def test_master_guardian_rejects_published_default_passphrase():
    """العبارة المنشورة CHANGE_ME_IMMEDIATELY لا تُقبل كعبارة سيد صالحة."""
    from guardian.master_guardian import MasterGuardian
    g = MasterGuardian(master_passphrase="real_random_passphrase_x9", guardian_dir=tempfile.mkdtemp())
    assert g.verify_master_code("CHANGE_ME_IMMEDIATELY") is False
    assert g.verify_master_code("real_random_passphrase_x9") is True


# =====================================================================
# 2) التفويض الذاتي في الحارس (أمين 6.2 / بصير BAS-S05 / حكيم)
# =====================================================================

def _guardian(tmp):
    from guardian.master_guardian import MasterGuardian
    return MasterGuardian(master_passphrase="round1_pass", guardian_dir=tmp)


def _checker_with_guardian(monkeypatch, tmp, T):
    """IntegrityChecker مربوط بالحارس — متوافق مع شجرة الأساس (fallback)."""
    import guardian.integrity_checker as ic
    monkeypatch.setattr(ic, "INTEGRITY_DB", T / "ib.json")
    monkeypatch.setattr(ic, "INTEGRITY_LOG", T / "il.jsonl")
    g = _guardian(str(T))
    try:
        return ic.IntegrityChecker(master_guardian=g), g
    except TypeError:
        # شجرة الأساس: المعامل غير موجود — السلوك القديم هو المفحوص
        return ic.IntegrityChecker(), g


def test_approve_changes_rejects_caller_supplied_hash(monkeypatch, tmp_path):
    """approve_changes لا يجوز أن تتحقق بتجزئة يمررها المستدعي نفسه."""
    checker, g = _checker_with_guardian(monkeypatch, str(tmp_path), tmp_path)
    token = "attacker-chosen"
    self_hash = hashlib.sha256(token.encode()).hexdigest()
    result = checker.approve_changes([], token, self_hash)
    assert result.get("success") is False, "التفويض الذاتي يجب أن يُرفض"


def test_approve_changes_accepts_correct_master_token(monkeypatch, tmp_path):
    """الجانب السليم: الرمز الصحيح (عبارة الحارس) يمر التحقق — الفشل المغلق
    لا يعطل التشغيل المصرّح به."""
    checker, g = _checker_with_guardian(monkeypatch, str(tmp_path), tmp_path)
    result = checker.approve_changes([], "round1_pass", None)
    assert result.get("success") is True, f"الرمز الصحيح رُفض: {result}"


def test_execute_approved_update_rejects_caller_hash(monkeypatch, tmp_path):
    """execute_approved_update لا يجوز أن تقبل تجزئة يمررها المستدعي نفسه."""
    import guardian.self_evolve as se
    monkeypatch.setattr(se, "EVOLUTION_LOG", tmp_path / "evo.jsonl")
    g = _guardian(str(tmp_path))
    ev = se.GuardianSelfEvolver(master_guardian=g)
    proposal = ev.propose_key_rotation()
    token = "attacker-chosen"
    self_hash = hashlib.sha256(token.encode()).hexdigest()
    result = ev.execute_approved_update(proposal["proposal_id"], token, self_hash)
    assert result.get("success") is False, "التفويض الذاتي يجب أن يُرفض"


# =====================================================================
# 3) تجاوز فحص كود السيد بمسارات مكافئة (أمين 6.3 / بصير BAS-S04 / حكيم)
# =====================================================================

@pytest.mark.parametrize("target", [
    "./backend/app.py",
    "frontend/../backend/app.py",
    "backend\\app.py",
])
def test_master_code_path_bypass_blocked(target):
    """المسارات المكافئة لمسار محمي يجب أن تُحجب — لا تجاوز بتمثيل مختلف للمسار."""
    g = _guardian(tempfile.mkdtemp())
    result = g.request_action("AI", "write_file", target=target)
    assert result["allowed"] is False, f"المسار {target!r} يجب أن يُحجب"


def test_execute_approved_update_accepts_correct_master_token(monkeypatch, tmp_path):
    """الجانب السليم: تنفيذ تحديث معتمد بالرمز الصحيح ينجح — ولا يُسقِط
    الفشلُ المغلق المسارَ المصرّح به."""
    import guardian.self_evolve as se
    monkeypatch.setattr(se, "EVOLUTION_LOG", tmp_path / "evo.jsonl")
    g = _guardian(str(tmp_path))
    ev = se.GuardianSelfEvolver(master_guardian=g)
    proposal = ev.propose_key_rotation()
    result = ev.execute_approved_update(proposal["proposal_id"], "round1_pass", None)
    assert result.get("success") is True, f"الرمز الصحيح رُفض: {result}"


def test_master_code_absolute_path_inside_repo_blocked():
    """المسار المطلق لملف داخل مجلد كود السيد يجب أن يُحجب."""
    import guardian.master_guardian as mg
    g = _guardian(tempfile.mkdtemp())
    root = Path(mg.__file__).resolve().parent.parent
    result = g.request_action("AI", "write_file", target=str(root / "backend" / "app.py"))
    assert result["allowed"] is False, "المسار المطلق لملف كود السيد يجب أن يُحجب"


# =====================================================================
# 4) رمز إعادة التفعيل (أمين 6.5 / بصير BAS-S08 / حكيم) — لا تسريب
# =====================================================================

def test_reactivation_code_not_logged_nor_persisted(monkeypatch, caplog, tmp_path):
    """رمز فك القفل: خارج كائن الحادثة العام (repr نظيف)، لا يُسجّل نصًا،
    ولا يُكتب في ev.jsonl ولا ملف القفل، ويُستخرج عبر القناة المصرّح بها
    (get_reactivation_code) وفك القفل به ينجح — قناة التسليم فعالة."""
    import guardian.emergency_breaker as eb
    em_dir = tmp_path / "em"
    monkeypatch.setattr(eb, "EMERGENCY_LOG_DIR", em_dir)
    monkeypatch.setattr(eb, "EMERGENCY_LOG_FILE", em_dir / "ev.jsonl")
    monkeypatch.setattr(eb, "LOCK_FILE", em_dir / "LOCK")
    monkeypatch.setattr(eb, "BACKUP_DIR", em_dir / "bk")
    # حارس مثبت — قناة تسليم الرمز تتطلب إثبات سلطة سيد (اعتراض المراجع)
    g = _guardian(str(tmp_path))
    with caplog.at_level(logging.CRITICAL, logger="guardian.emergency"):
        breaker = eb.EmergencyBreaker(master_guardian=g)
        incident = breaker.activate("round1-probe", "AI")
    # كائن الحادثة العام خالٍ من السر (لا حقل — repr/التسلسل/callbacks)
    assert not hasattr(incident, "reactivation_code"), \
        "الرمز لا يجوز أن يكون حقلًا في كائن الحادثة العام (repr/التسلسل/callbacks)"
    # القناة المصرّح بها: لا تسليم بلا سلطة سيد مثبتة — الرمز الخاطئ يُرفض
    assert breaker.get_reactivation_code(incident.incident_id, "wrong-token") is None, \
        "تسليم الرمز بدون سلطة سيد يجب أن يُرفض"
    assert breaker.get_reactivation_code(incident.incident_id, None) is None, \
        "تسليم الرمز بلا رمز سيد يجب أن يُرفض"
    # الرمز الصحيح (عبارة الحارس) يمر — التسليم للسلطة المثبتة فقط
    code = breaker.get_reactivation_code(incident.incident_id, "round1_pass")
    assert code, "قناة التسليم المصرّح بها (get_reactivation_code) يجب أن تعيد الرمز للسلطة المثبتة"
    assert code not in caplog.text, "رمز فك القفل ظهر نصًا في السجل — تسريب أمني"
    assert code not in repr(incident), "الرمز ظهر في repr الحادثة — تسريب"
    # الرمز ليس في السجل المحفوظ على القرص (ev.jsonl)
    if (em_dir / "ev.jsonl").exists():
        assert code not in (em_dir / "ev.jsonl").read_text(encoding="utf-8"), \
            "رمز فك القفل ظهر في سجل الحوادث المحفوظ — تسريب أمني"
    # ملف القفل يحمل التجزئة فقط — لا الرمز
    if (em_dir / "LOCK").exists():
        assert code not in (em_dir / "LOCK").read_text(encoding="utf-8"), \
            "رمز فك القفل ظهر نصًا في ملف القفل — تسريب أمني"
    # قناة التسليم فعالة: فك القفل بالرمز المسلَّم ينجح
    result = breaker.reactivate(code, incident_id=incident.incident_id)
    assert result.get("success") is True, "فك القفل بالرمز المسلَّم يجب أن ينجح"
    # الرمز لا يُستخرج بعد فك القفل (الحالة لم تعد LOCKED)
    assert breaker.get_reactivation_code(incident.incident_id, "round1_pass") is None


# =====================================================================
# 5) أذونات keyring.json والكتابة الذرية (بصير BAS-S01/S14 / أمين 3.1/3.2 / حكيم)
# =====================================================================

def test_keyring_file_permissions_0600_and_atomic(tmp_path, monkeypatch, caplog):
    """keyring.json يُكتب 0600 في دليل 0700، وفشل الاستبدال لا يتلف النسخة
    السابقة — مع تأكيد اسم المسجّل ونص الخطأ المحقون حرفيًا."""
    from backend.sovereign.keys.keyring import KeyRing
    keys_dir = tmp_path / "keys"
    ring = KeyRing(keys_dir=keys_dir)
    k1 = ring.generate_new_key("round1")
    assert ring.save_to_disk() is True
    ring_file = keys_dir / "keyring.json"
    mode = statmod.S_IMODE(ring_file.stat().st_mode)
    assert mode == 0o600, f"أذونات keyring.json = {oct(mode)} — يجب أن تكون 0600"
    dir_mode = statmod.S_IMODE(keys_dir.stat().st_mode)
    assert dir_mode == 0o700, f"أذونات دليل المفاتيح = {oct(dir_mode)} — يجب أن تكون 0700"

    # فشل الاستبدال (disk full محقون) لا يمحو المفتاح القديم — ويسجَّل
    # في المسجّل الصحيح برسالة الخطأ المحقونة نفسها
    before = ring_file.read_text()
    ring.generate_new_key("round1-second")
    with patch("os.replace", side_effect=OSError("disk full")) as replace_mock, \
         caplog.at_level(logging.ERROR, logger="sovereign.keys.keyring"):
        assert ring.save_to_disk() is False
    assert replace_mock.called, "الحقن لم يمر عبر os.replace — الاختبار ليس على المسار المقصود"
    assert ring_file.read_text() == before, "فشل الحفظ تلف النسخة السابقة — غير ذري"
    # المسجّل الصحيح + الرسالة المحقونة نصًا (لا len(records) > 0)
    keyring_errors = [r for r in caplog.records if r.name == "sovereign.keys.keyring"]
    assert keyring_errors, "لا رسالة خطأ في المسجّل الصحيح sovereign.keys.keyring"
    assert any("disk full" in r.getMessage() for r in keyring_errors), \
        "رسالة الخطأ المحقونة (disk full) غير موجودة في المسجّل"


def test_corrupt_keyring_load_fails_closed_and_blocks_overwrite(tmp_path):
    """سيناريو أمين 3.2 كاملًا: ملف تالف → التحميل يرفع → وحتى لو التقط
    المستدعي الاستثناء وواصل، الحفظ يُرفض والملف لا يُستبدل."""
    from backend.sovereign.keys.keyring import KeyRing
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    ring = KeyRing(keys_dir=keys_dir)
    k1 = ring.generate_new_key("round1")
    assert ring.save_to_disk() is True
    ring_file = keys_dir / "keyring.json"
    corrupted = (keys_dir / "keyring.json").read_text()[:-5]
    ring_file.write_text(corrupted)  # JSON مبتور

    # مستدعٍ يلتقط استثناء التحميل ويواصل (السلوك الذي حرسه المراجع)
    kr2 = KeyRing(keys_dir=keys_dir)
    with pytest.raises(ValueError):
        kr2.load_from_disk()
    # بعد الالتقاط: التوليد والحفظ يُرفضان — لا استبدال للملف التالف
    kr2.generate_new_key("after-corrupt")
    assert kr2.save_to_disk() is False, "الحفظ بعد فشل التحميل يجب أن يُرفض"
    assert ring_file.read_text() == corrupted, "الملف التالف استُبدل — المفاتيح القائمة ضاعت"
    # لا ملفات مؤقتة متبقية
    leftovers = [f for f in keys_dir.iterdir() if f.name.endswith(".tmp")]
    assert not leftovers, f"ملفات مؤقتة متبقية: {leftovers}"


# =====================================================================
# 6) سقوط XOR-DEV في محرك التشفير (أمين 5.1 / بصير BAS-S02 / حكيم)
# =====================================================================

def test_encryption_engine_no_xor_fallback():
    """غياب pycryptodome يجب أن يرفع فشلًا صريحًا — لا سقوط صامت إلى XOR."""
    import nexus.encryption.encryption_engine as ee
    with patch.object(ee, "HAS_PYCRYPTO", False), patch.object(ee, "AES", None):
        with pytest.raises(RuntimeError):
            ee.EncryptionEngine(master_key=os.urandom(32)).encrypt("x")


def test_decrypt_rejects_foreign_algorithm():
    """فك التشفير يجب أن يرفض مظروفًا معلنًا بخوارزمية غير معتمدة (وسم XOR-DEV)."""
    import dataclasses
    from nexus.encryption.encryption_engine import EncryptionEngine
    e = EncryptionEngine(master_key=os.urandom(32))
    payload = e.encrypt("hello")
    tampered = dataclasses.replace(payload, algorithm="XOR-DEV")
    assert e.decrypt(tampered) is None, "المحرك فك مظروفًا معلنًا XOR-DEV — يجب أن يرفضه"


# =====================================================================
# 7) مصادقة مسارات HTTP — قبل أي أثر جانبي (أمين 1.1-1.4 / بصير BAS-S09/S10 / حكيم)
# =====================================================================

def _app_client():
    from fastapi.testclient import TestClient
    from app import app
    return TestClient(app)


class _FakeOrch:
    """منسق اصطناعي حقيقي النتائج — لفحص الاستجابة الفعلية لا مجرد 200."""
    def __init__(self):
        self.calls = []
    def _record(self, name, *a, **k):
        self.calls.append((name, a, k))
    def run_cycle(self, input_data):
        self._record("run_cycle", input_data)
        return SimpleNamespace(
            success=True, cycle_id="cyc-round1-001",
            duration=0.01, decision="decision-round1",
        )
    def reset_all(self, preserve_session=False):
        self._record("reset_all", preserve_session)
        return True
    def reset_component(self, component):
        self._record("reset_component", component)
        return True
    def set_mode(self, mode):
        self._record("set_mode", mode)
        return True


def test_api_mutating_endpoints_require_key_before_side_effects(monkeypatch):
    """/api/run و/api/reset و/api/event و/api/mode/*: بلا مفتاح أو بمفتاح
    خاطئ → 401 والمنسق لا يُستدعى أصلًا. بالمفتاح الصحيح → المسار يعمل
    فعليًا (استجابة صحيحة مطابقة لنتيجة المنسق الاصطناعي). مفتاح غير-ASCII
    → 401 لا خطأ خادم (500)."""
    import api as api_module
    fake_orch = _FakeOrch()
    # جواس get_orch نفسه: يثبت عدم استدعائه قبل المصادقة (لا عملياته فقط)
    orch_spy = MagicMock(side_effect=lambda: fake_orch)
    monkeypatch.setattr(api_module, "get_orch", orch_spy)

    with _app_client() as client:
        cases = [
            ("post", "/api/run", {"event_type": "manual_run", "payload": {"k": "v"}}),
            ("post", "/api/reset", {"component": None, "preserve_data": False}),
            ("post", "/api/event", {"type": "system", "payload": {"x": 1}}),
            ("post", "/api/mode/normal", {}),
        ]
        for method, path, body in cases:
            # بلا مفتاح: 401 وget_orch نفسه لا يُستدعى (لا جلب للمنسق أصلًا)
            fake_orch.calls = []
            orch_spy.reset_mock()
            r = getattr(client, method)(path, json=body)
            assert r.status_code == 401, f"{path} بلا مفتاح أعاد {r.status_code} — يجب أن يرفض بـ401"
            orch_spy.assert_not_called(), f"{path}: get_orch استُدعي قبل المصادقة"
            assert fake_orch.calls == [], f"{path}: المنسق استُدعي قبل المصادقة — أثر جانبي بلا تصريح"
            # مفتاح خاطئ: 401 وget_orch لا يُستدعى
            fake_orch.calls = []
            orch_spy.reset_mock()
            r = getattr(client, method)(path, json={**body, "api_key": "wrong-key-1234567890"},
                                        headers={"X-API-Key": "wrong-key-1234567890"})
            assert r.status_code == 401, f"{path} بمفتاح خاطئ أعاد {r.status_code}"
            orch_spy.assert_not_called(), f"{path}: get_orch استُدعي بمفتاح خاطئ"
            assert fake_orch.calls == [], f"{path}: المنسق استُدعي بمفتاح خاطئ"
            # مفتاح صحيح: get_orch يُستدعى مرة واحدة والمسار يعمل فعليًا —
            # الاستجابة مطابقة لنتيجة المنسق
            fake_orch.calls = []
            orch_spy.reset_mock()
            r = getattr(client, method)(path, json={**body, "api_key": MASTER_KEY},
                                       headers={"X-API-Key": MASTER_KEY})
            assert r.status_code == 200, f"{path} بمفتاح صحيح أعاد {r.status_code}: {r.text[:200]}"
            orch_spy.assert_called_once(), f"{path}: get_orch لم يُستدعَ مرة واحدة بالمفتاح الصحيح"
            assert fake_orch.calls, f"{path}: المنسق لم يُستدعِ بالمفتاح الصحيح"
            data = r.json()
            if path == "/api/run":
                assert fake_orch.calls[0][0] == "run_cycle"
                passed_input = fake_orch.calls[0][1][0]
                assert passed_input["type"] == "manual_run" and passed_input["payload"] == {"k": "v"}, \
                    "المدخل المار للمنسق لا يطابق جسم الطلب"
                assert data["status"] == "success" and data["cycle_id"] == "cyc-round1-001", \
                    f"الاستجابة لا تطابق نتيجة المنسق: {data}"
            elif path == "/api/reset":
                assert fake_orch.calls[0][0] == "reset_all" and fake_orch.calls[0][1] == (False,), \
                    f"reset_all استُدعي بمعاملات غير متوقعة: {fake_orch.calls}"
                assert data["status"] == "success" and "تم إعادة تهيئة النظام بالكامل" in data["message"]
            elif path == "/api/event":
                assert fake_orch.calls[0][0] == "run_cycle"
                passed_input = fake_orch.calls[0][1][0]
                assert passed_input["type"] == "system" and passed_input["source"] == "api", \
                    f"المدخل المار للمنسق لا يطابق جسم الحدث: {passed_input}"
                assert data["status"] == "success" and data["cycle_id"] == "cyc-round1-001", \
                    f"الاستجابة لا تطابق نتيجة المنسق: {data}"
            elif path == "/api/mode/normal":
                assert fake_orch.calls == [("set_mode", ("normal",), {})], \
                    f"set_mode استُدعي بغير الوضع المطلوب: {fake_orch.calls}"
                assert data["status"] == "success" and data["mode"] == "normal"
        # مفتاح غير-ASCII: 401 لا 500 (compare_digest على بايتات UTF-8)
        r = client.post("/api/run", json={"event_type": "manual_run", "payload": {}, "api_key": "مفتاح-غير-آمن"})
        assert r.status_code == 401, f"مفتاح غير-ASCII أعاد {r.status_code} — يجب أن يكون رفضًا نظيفًا"


def test_security_log_requires_key():
    """/security/log يعيد سجل الأمان بلا مصادقة — يجب أن يطلب مفتاح السيد."""
    with _app_client() as client:
        r = client.get("/security/log")
        assert r.status_code == 401, f"/security/log بلا مفتاح أعاد {r.status_code}"
        r = client.get("/security/log", headers={"X-API-Key": MASTER_KEY})
        assert r.status_code != 401, "المفتاح الصحيح مرفوض"


def test_ws_sir_command_requires_master_key(monkeypatch):
    """/api/ws لا يعامل الرسائل كأوامر سيد دون مفتاح — والأمر المسلَّم بالمفتاح
    الصحيح يُعالج فعليًا (استجابة أمر من المنسق مطابقة)."""
    import api as api_module
    monkeypatch.setattr(api_module, "get_orch", lambda: _FakeOrch())
    with _app_client() as client:
        with client.websocket_connect("/api/ws") as ws:
            welcome = ws.receive_json()  # رسالة الترحيب الأولى
            assert welcome.get("type") == "welcome"
            ws.send_json({"type": "sir_command", "user_id": "u9", "session_id": "s9",
                          "payload": {"text": "echo hi"}})
            resp = ws.receive_json()
            assert resp.get("status") == "error", "أمر سيد عبر /api/ws بلا مفتاح يجب أن يُرفض"
            assert "master" in resp.get("error", "").lower() or "مفتاح" in resp.get("error", "")
            # بالمفتاح الصحيح: يُعالج كأمر سيد — استجابة أمر فعلية من المنسق
            ws.send_json({"type": "sir_command", "user_id": "u9", "session_id": "s9",
                          "payload": {"text": "echo hi"}, "master_key": MASTER_KEY})
            resp2 = ws.receive_json()
            assert resp2.get("type") == "command_response", \
                f"أمر سيد بالمفتاح الصحيح لم يُعالج: {resp2}"
            payload2 = resp2.get("payload", {})
            assert payload2.get("success") is True and payload2.get("cycle_id") == "cyc-round1-001", \
                f"استجابة الأمر لا تطابق نتيجة المنسق: {payload2}"
            assert payload2.get("command") == "echo hi"


# =====================================================================
# 8) الحدث المزوّر بمفتاح متقاعد (أمين 3.3 / بصير BAS-D03 / حكيم)
# =====================================================================

def test_forged_event_with_retired_key_is_invalid(tmp_path):
    """تزوير حدث منسوب لمفتاح RETIRED يجب أن يُصنّف INVALID لا UNVERIFIABLE —
    وحدث صحيح التوقيع بمفتاح RETIRED لا يُعاد VERIFIED (سياسة R-668 محفوظة)."""
    from backend.sovereign.keys.keyring import KeyRing
    from backend.sovereign.keys.verifier import SignatureVerifier
    from backend.sovereign.keys.rotation import KeyRotation

    kr = KeyRing(keys_dir=tmp_path / "keys")
    k1 = kr.generate_new_key("round1")
    kr.save_to_disk()
    v = SignatureVerifier(kr)
    ev = {
        "hash": "h1", "prev_hash": "p1", "blob": "b1",
        "time": "t1", "type": "x", "key_id": k1.key_id,
    }
    ev["signature"] = v._compute_signature(v.extract_event_data(ev), k1.private_key)
    forged = dict(ev, blob="EVIL")
    # قبل التدوير: التزوير يُكشف
    assert v.verify_event(forged).status.value == "invalid"
    # التدوير (المفتاح يصبح RETIRED مع بقاء مادته للتحقق التاريخي)
    rot = KeyRotation(kr, ledger_path=tmp_path / "ledger.jsonl")
    rot.rotate("round1")
    result = v.verify_event(forged)
    assert result.status.value == "invalid", (
        f"الحدث المزوّر بعد التدوير صُنّف {result.status.value} — التزوير يجب أن يُكشف ما دامت مادة المفتاح موجودة"
    )
    # الحدث الصحيح التوقيع بمفتاح RETIRED: ليس VERIFIED (سياسة R-668)
    ok_result = v.verify_event(ev)
    assert ok_result.status.value in ("unverifiable_missing_key",), (
        f"حدث صحيح التوقيع بمفتاح RETIRED صُنّف {ok_result.status.value} — يجب ألا يكون VERIFIED"
    )
