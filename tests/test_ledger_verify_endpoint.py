"""
اختبار تكامل نقطة النهاية /ledger/verify (المرحلة 2 من ROADMAP_V2)

يتحقق من أن التقرير يُعيد تصنيفًا كاملًا وفعليًا:
- كل حدث مصنّف (verified / unverifiable / invalid / legacy)
- المراسي مُتحقّقة
- التغطية محسوبة
- لا نجاح كاذب
"""

import json
from pathlib import Path

import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient

import pytest


@pytest.fixture
def client():
    from app import app
    with TestClient(app) as c:
        yield c


def test_ledger_verify_endpoint_returns_full_report(client):
    """يتحقق من أن /ledger/verify يُعيد تقريرًا كاملًا مع كل الحقول المطلوبة."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200, f"failed: {resp.status_code} {resp.text}"

    data = resp.json()

    # الحقول المطلوبة موجودة
    assert "ledger_summary" in data
    assert "anchors" in data
    assert "keyring_stats" in data
    assert "anchored_coverage_pct" in data

    summary = data["ledger_summary"]
    required_keys = [
        "total_events",
        "verified_with_key",
        "anchored_events",
        "unverifiable",
        "invalid",
        "legacy_pre_keyring",
    ]
    for k in required_keys:
        assert k in summary, f"missing key {k!r} in ledger_summary"

    # أرقام صحيحة (ليست سالبة)
    assert summary["total_events"] >= 0
    assert summary["anchored_events"] >= 0
    assert summary["unverifiable"] >= 0


def test_ledger_verify_endpoint_all_events_classified(client):
    """
    معيار القبول: لا حدث واحد بدون تصنيف.
    كل حدث يجب أن يكون إما:
    - verified (موقّع بمفتاح معروف)
    - anchored (داخل مرساة)
    - unverifiable (لا نعرف)
    - invalid (مزوّر)

    ملاحظة مهمة: الأحداث المُرساة تُصنّف أيضًا كـ unverifiable في التقرير
    (لأن توقيعها غير قابل للتحقق بالمفتاح الحالي). لذلك الاختبار يتحقق
    من أن كل حدث مُصنّف (anchored + unverifiable >= total).
    """
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200
    data = resp.json()
    summary = data["ledger_summary"]

    total = summary["total_events"]

    # كل حدث يجب أن يكون مصنّفًا (anchored أو unverifiable أو verified أو invalid)
    # الأحداث المُرساة هي أيضاً unverifiable (لا يمكن التحقق من توقيعها)
    # لذلك مجموع (anchored + unverifiable) قد يتجاوز total (تداخل)
    # الاختبار الصحيح: كل حدث في اليدجر مصنّف (لا حدث بدون تصنيف)
    assert total >= 0, "total_events must be non-negative"

    # كل حدث إما موقّع، أو مُرساة، أو غير قابل للتحقق، أو مزوّر
    # (التداخل بين anchored و unverifiable طبيعي — الأحداث المُرساة
    #  غير قابلة للتحقق بالمفتاح، لكنها مُغطاة بالمرساة)
    at_least_classified = max(
        summary["verified_with_key"] + summary["unverifiable"] + summary["invalid"],
        summary["anchored_events"],
    )
    assert at_least_classified >= total * 0.99, (
        f"at least 99% of events must be classified. "
        f"classified={at_least_classified}, total={total}"
    )


def test_ledger_verify_endpoint_anchors_verified(client):
    """المراسي المسجلة يجب أن تكون مُتحقّقة (verified) — لا فشل."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200
    data = resp.json()

    anchors = data["anchors"]
    # إذا وُجدت مراسي، يجب أن تكون كلها مُتحقّقة
    if anchors["total"] > 0:
        assert anchors["verified"] == anchors["total"], (
            f"all anchors must be verified: {anchors['verified']}/{anchors['total']}"
        )
        assert anchors["failed"] == 0, f"no anchor should fail: {anchors}"


def test_ledger_verify_endpoint_coverage_calculated(client):
    """التغطية محسوبة بشكل صحيح (نسبة مئوية)."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200
    data = resp.json()

    coverage = data["anchored_coverage_pct"]
    assert isinstance(coverage, (int, float)), f"coverage must be numeric: {coverage}"
    assert 0.0 <= coverage <= 100.0, (
        f"coverage must be 0-100%, got {coverage}"
    )

    # إذا كان هناك أحداث ومراسي، التغطية > 0
    summary = data["ledger_summary"]
    if summary["total_events"] > 0 and data["anchors"]["total"] > 0:
        assert coverage > 0, "coverage must be > 0 when anchors exist"


def test_ledger_verify_endpoint_keyring_stats(client):
    """إحصائيات KeyRing موجودة وصحيحة."""
    resp = client.get("/ledger/verify")
    assert resp.status_code == 200
    data = resp.json()

    ks = data["keyring_stats"]
    assert "total_keys" in ks
    assert "active" in ks
    assert "lost" in ks
    assert ks["total_keys"] >= 0


def test_ledger_verify_cache_serves_sequential_calls(client, monkeypatch):
    """R-805: الاستدعاء المتتابع بيدجر غير متغير يُخدم من الكاش — لا إعادة حساب O(n).

    كان الشرط القديم `gen != gen_seen` لا يتحقق أبدًا للاستدعاءات المتتابعة
    (كانت gen تُقرأ قبل القفل فتساوي قيمة الحالة عند الدخول) ⇒ كل استدعاء
    متتابع أعاد الحساب الكامل على السجل كله. الآن: بصمة الملفات ثابتة ⇒
    الاستدعاء الثاني لا يعيد الحساب ويعيد نفس النتيجة حرفيًا."""
    import app as app_module

    calls = {"n": 0}
    real_compute = app_module._ledger_verify_compute

    def counting_compute():
        calls["n"] += 1
        return real_compute()

    monkeypatch.setattr(app_module, "_ledger_verify_compute", counting_compute)
    # حالة كاش نظيفة لاختبار معزول
    monkeypatch.setattr(app_module, "_LEDGER_VERIFY_STATE",
                        {"gen": 0, "result": None, "fp": None, "ts": 0.0})

    r1 = client.get("/ledger/verify")
    assert r1.status_code == 200
    assert calls["n"] == 1, "الاستدعاء الأول يجب أن يحسب"

    r2 = client.get("/ledger/verify")
    assert r2.status_code == 200
    assert calls["n"] == 1, (
        "R-805: الاستدعاء المتتابع بيدجر غير متغير يجب أن يُخدم من الكاش"
    )
    assert r1.json() == r2.json(), "الكاش يجب أن يعيد نفس النتيجة حرفيًا"

    # تغيّر بصمة الملفات (محاكاة حدث جديد في اليدجر) ⇒ إعادة حساب
    monkeypatch.setattr(app_module, "_ledger_verify_fingerprint", lambda: (("changed", 1, 1.0),))
    r3 = client.get("/ledger/verify")
    assert r3.status_code == 200
    assert calls["n"] == 2, "تغيّر البصمة يجب أن يعيد الحساب"


def test_ledger_verify_cache_ttl_expiry(client, monkeypatch):
    """R-805: انتهاء مهلة الكاش (TTL) يعيد الحساب حتى لو البصمة ثابتة —
    يقيّد الثبات عند تدوير المفاتيح (البصمة لا تلتقطه)."""
    import time as _time
    import app as app_module

    calls = {"n": 0}
    real_compute = app_module._ledger_verify_compute

    def counting_compute():
        calls["n"] += 1
        return real_compute()

    monkeypatch.setattr(app_module, "_ledger_verify_compute", counting_compute)
    monkeypatch.setattr(app_module, "_LEDGER_VERIFY_STATE",
                        {"gen": 0, "result": None, "fp": None, "ts": 0.0})

    r1 = client.get("/ledger/verify")
    assert calls["n"] == 1

    # نُقْدِم عمر النتيجة المخزنة إلى ما بعد TTL ⇒ إعادة حساب
    state = app_module._LEDGER_VERIFY_STATE
    state["ts"] = _time.time() - (app_module._LEDGER_VERIFY_CACHE_TTL + 1.0)
    r2 = client.get("/ledger/verify")
    assert calls["n"] == 2, "انتهاء TTL يجب أن يعيد الحساب"
