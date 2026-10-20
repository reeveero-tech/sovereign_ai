# -*- coding: utf-8 -*-
"""
R-703 — السجل التالف يُكتشف ويُسجَّل، ولا يُنفَّذ أي إجراء آلي قصوي.
ومعه توقيع الأوامر الخطيرة: HMAC-SHA256 كامل (256 بت) بمقارنة ثابتة الزمن.

العيب (OWNER_REQUIRED بند ١٥): `IntegrityStatus` تعداد نصي، فـ
`not IntegrityStatus.CORRUPTED` يساوي False. ثلاثة فحوص (instincts وwatcher و
drives) لم تكن ترى التلف أبدًا. إصلاح الفحص وحده كان سيطلق سلسلة آلية من
تخفٍّ بالمستوى 4، وبذرة phoenix، و`encrypt_blob` (وهي غير موجودة). أمر
المالك: كشف وتسجيل دون تحرك تلقائي.

ملاحظة صريحة عن «ثبات الزمن»: قياس زمن الساعة الجدارية لمقارنة سلسلتين
بطول 64 حرفًا لا يثبت شيئًا في CI، فالضجيج أكبر من الفرق بعدة رتب، والاختبار
سيتذبذب. لذلك الإثبات بنيوي. نثبت أن التحقق يمر بـ`hmac.compare_digest`
(دالة المكتبة القياسية الموثقة بأنها ثابتة الزمن)، وأن `==` لم يعد يحسم
النتيجة. وهو إثبات قابل للتكرار بلا تذبذب.
"""

import hashlib
import hmac
import logging
from unittest import mock

import pytest

from memory.core import IntegrityStatus
from memory.defense import automation_guard
from memory.biological.instincts import CognitiveInstincts
from memory.defense.watcher import MemoryWatcher
from memory.biological.drives import SovereignDrives
from memory.defense.ransomware import RansomwareDefense
from sovereign.controller import SovereignController


# ---------------------------------------------------------------- أدوات

class _FakeCore:
    def __init__(self, status):
        self.status = status
        self.appended = []

    def verify_integrity(self, verbose=False):
        return self.status

    def append_event(self, event_type=None, payload=None, **kw):
        self.appended.append((event_type, payload))

    def iterate_events(self, limit=None):
        return iter([{"blob": "b1", "user": "sov"}, {"blob": "b2"}])

    def get_payload(self, event):
        return {"user": "sov"}


class _Quiet:
    def get_status(self):
        return {"threat": {"level": 0}, "immune_status": "normal",
                "health_score": 1.0}


def _instincts(status):
    inst = CognitiveInstincts.__new__(CognitiveInstincts)
    inst.core = _FakeCore(status)
    inst.watcher = _Quiet()
    inst.immune = _Quiet()
    inst.stealth = mock.MagicMock(name="stealth")
    inst.ransom = mock.MagicMock(name="ransom")
    inst.dynamic = mock.MagicMock(name="dynamic")
    inst.sovereign_profile = None
    inst._get_sovereign_id = lambda: "sov"
    return inst


def _no_drastic_calls(inst):
    assert inst.stealth.set_stealth_level.call_count == 0, "تخفٍّ آلي نُفّذ"
    assert inst.ransom.create_phoenix_seed.call_count == 0, "بذرة phoenix آلية نُفّذت"
    assert inst.ransom.encrypt_blob.call_count == 0, "encrypt_blob آلي استُدعي"


@pytest.fixture(autouse=True)
def _fresh_guard():
    automation_guard._reset_for_tests()
    yield
    automation_guard._reset_for_tests()


def _messages(caplog, tag):
    return [r for r in caplog.records if tag in r.getMessage()]


# ---------------------------------------------------------------- الكشف

def test_instincts_detects_corrupted_ledger_and_logs(caplog):
    inst = _instincts(IntegrityStatus.CORRUPTED)
    with caplog.at_level(logging.WARNING):
        threats = inst._detect_threats_to_sovereign()
    assert any(t["type"] == "core_integrity_compromised" for t in threats), (
        "instincts لا يرى السجل التالف (not IntegrityStatus.CORRUPTED == False)"
    )
    assert _messages(caplog, "R-703 [INTEGRITY]"), "الكشف لم يُسجَّل"


def test_instincts_no_false_alarm_on_verified_or_partial():
    for st in (IntegrityStatus.VERIFIED, IntegrityStatus.PARTIAL):
        threats = _instincts(st)._detect_threats_to_sovereign()
        assert not any(t["type"] == "core_integrity_compromised" for t in threats), st


def test_watcher_detects_corrupted_ledger_and_logs(caplog):
    w = MemoryWatcher.__new__(MemoryWatcher)
    w.core = _FakeCore(IntegrityStatus.CORRUPTED)
    with caplog.at_level(logging.WARNING):
        anomaly = w._detect_integrity_attack()
    assert anomaly is not None, "watcher لا يرى السجل التالف"
    assert anomaly.type == "integrity_violation"
    assert _messages(caplog, "R-703 [INTEGRITY]")
    w.core = _FakeCore(IntegrityStatus.VERIFIED)
    assert w._detect_integrity_attack() is None


def test_drives_integrity_score_reflects_corruption(caplog):
    def survival(status):
        d = SovereignDrives.__new__(SovereignDrives)
        d.core = _FakeCore(status)
        d.watcher = _Quiet()
        d.homeostasis = _Quiet()
        d.drives = {}
        return d.update_survival_drive()

    with caplog.at_level(logging.WARNING):
        bad = survival(IntegrityStatus.CORRUPTED)
    good = survival(IntegrityStatus.VERIFIED)
    assert bad == pytest.approx(good + 0.4), (
        f"درجة السلامة لا تتأثر بالتلف (bad={bad}, good={good})"
    )
    assert _messages(caplog, "R-703 [INTEGRITY]")


# ------------------------------------------------- لا إجراء آلي قصوي

def test_corrupted_ledger_triggers_no_automated_drastic_action(caplog):
    """المسار الكامل: كشف التلف ثم الحماية ثم الأمن المطلق، بلا أي تنفيذ."""
    inst = _instincts(IntegrityStatus.CORRUPTED)
    with caplog.at_level(logging.WARNING):
        actions = inst.protect_sovereign()
        for a in actions:
            inst._execute_protection_action(a)
        inst.enforce_absolute_security()
        inst.protect_sovereign_privacy()
        inst.immortalize_sovereign()
    assert actions, "الكشف لم يولّد إجراء حماية (شرط مسبق للاختبار)"
    _no_drastic_calls(inst)
    inst.dynamic.working.clear_user.assert_not_called()
    assert all(a.status == "blocked" for a in actions)
    assert _messages(caplog, "R-703 [SAFETY]"), "المنع لم يُسجَّل"
    blocked = {b["source"] for b in automation_guard.blocked_actions()}
    assert {"instincts._execute_protection_action",
            "instincts.enforce_absolute_security",
            "instincts.protect_sovereign_privacy",
            "instincts.immortalize_sovereign"} <= blocked


def test_high_watcher_threat_triggers_no_automated_drastic_action():
    """المسار القائم قبل R-703 (تهديد ≥3 من الحارس) كان ينفذ التخفي وphoenix فعلًا."""
    inst = _instincts(IntegrityStatus.VERIFIED)
    inst.watcher = mock.MagicMock()
    inst.watcher.get_status.return_value = {"threat": {"level": 4}}
    actions = inst.protect_sovereign()
    for a in actions:
        inst._execute_protection_action(a)
    inst.enforce_absolute_security()
    assert actions, "تهديد الحارس لم يولّد إجراء (شرط مسبق)"
    _no_drastic_calls(inst)


def test_ransomware_threat_watch_creates_no_seed(caplog):
    r = RansomwareDefense.__new__(RansomwareDefense)
    r._active = True
    r.resurrection_level = 0
    r.watcher = mock.MagicMock()
    r.watcher.get_status.return_value = {"threat": {"level": 4}}
    r.create_phoenix_seed = mock.MagicMock(name="create_phoenix_seed")

    def stop(*a, **k):
        r._active = False

    with mock.patch("memory.defense.ransomware.threads.interruptible_sleep",
                    side_effect=stop), caplog.at_level(logging.WARNING):
        r._watch_for_threats()
    r.create_phoenix_seed.assert_not_called()
    assert any(b["source"] == "ransomware._watch_for_threats"
               for b in automation_guard.blocked_actions())


def test_controller_emergency_actions_blocked():
    c = SovereignController.__new__(SovereignController)
    stealth = mock.MagicMock()
    ransom = mock.MagicMock()
    with mock.patch("memory.defense.stealth.get_stealth_defense", return_value=stealth), \
         mock.patch("memory.defense.ransomware.get_ransomware_defense", return_value=ransom):
        c._execute_action({"action": "activate_maximum_protection", "target": "defense"})
        c._execute_action({"action": "create_emergency_backup", "target": "memory"})
    stealth.set_stealth_level.assert_not_called()
    ransom.create_phoenix_seed.assert_not_called()
    sources = [b["source"] for b in automation_guard.blocked_actions()]
    assert sources.count("controller._execute_action") == 2


def test_automation_flag_is_code_constant_not_env(monkeypatch):
    """إعادة التفعيل قرار مالك بالتزام صريح، ولا تتم من متغير بيئة."""
    assert automation_guard.AUTOMATED_DRASTIC_ACTIONS_ENABLED is False
    monkeypatch.setenv("AUTOMATED_DRASTIC_ACTIONS_ENABLED", "1")
    assert automation_guard.block_drastic_action("x", "test") is True


# ------------------------------------------- safety.py: توقيع الأوامر الخطيرة

def _guard():
    from safety import SafetyGuard
    return SafetyGuard.__new__(SafetyGuard)


def test_signature_is_full_256_bit_hmac():
    from sovereign.keys.derivation import derive_key
    g = _guard()
    sig = g.generate_signature("act-1")
    expected = hmac.new(derive_key("signing"), b"act-1", hashlib.sha256).hexdigest()
    assert len(sig) == 64, f"طول التوقيع {len(sig) * 4} بت، والمطلوب 256"
    assert sig == expected
    assert g._verify_signature(sig, "act-1") is True
    assert g._verify_signature(sig, "act-2") is False


def test_truncated_64_bit_signatures_rejected():
    from config import SOVEREIGN_KEY  # LEGACY-ROOT-KEY (read-only): اختبار رفض الصيغة القديمة
    from sovereign.keys.derivation import derive_key
    g = _guard()
    old_derived = hashlib.sha256(b"act-1" + derive_key("signing")).hexdigest()[:16]
    old_root = hashlib.sha256(f"act-1{SOVEREIGN_KEY}".encode()).hexdigest()[:16]
    assert g._verify_signature(old_derived, "act-1") is False
    assert g._verify_signature(old_root, "act-1") is False
    assert g._verify_signature(g.generate_signature("act-1")[:16], "act-1") is False


def test_verification_uses_constant_time_compare():
    g = _guard()
    sig = g.generate_signature("act-1")
    with mock.patch("safety.hmac.compare_digest", wraps=hmac.compare_digest) as cd:
        assert g._verify_signature(sig, "act-1") is True
        assert g._verify_signature("0" * 64, "act-1") is False
    assert cd.call_count >= 2, "التحقق لا يمر بـhmac.compare_digest"
    # إثبات أن compare_digest هو الحَكَم الفعلي، لا == في الخلفية
    with mock.patch("safety.hmac.compare_digest", return_value=False):
        assert g._verify_signature(sig, "act-1") is False
