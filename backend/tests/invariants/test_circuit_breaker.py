# -*- coding: utf-8 -*-
"""
مدخل التوجيه (Circuit Breaker) — المرحلة ٢ من META_SYSTEM (R-687)

أمر المالك 2026-10-18: «مدخل يقرأ من سجل العزل ويرفض توجيه الطلبات
للمكونات المعزولة (يرجع خطأ محدد)، بينما تستمر بقية المكونات بالعمل».

يُختبر التطبيق الحي نفسه (TestClient على backend/app.py): المكوّن المعزول
يرجع 503 بجسم خطأ محدد (error=component_quarantined + اسم المكوّن)،
وبقية المكونات والمسارات غير المكوّنية تمر. الحارس المعزول (supervisor)
ممنوع استيراده في app.py — يُختبر في tests/test_supervisor_isolated.py.

تصميم العزل (تصويب بعد RED): لا monkeypatch لجذر البيانات إطلاقًا —
التطبيق يقلع على جذر الجلسة ومفتاحها المعروف (R-634) فيبقى سجل الجلسة
نظيفًا (حارس R-682 يفحص توقيع الأحداث في نهاية الجلسة). عزل كل اختبار
يتم باستعادة سجل العزل حوله: لقطة قبل (وجود + محتوى) ← استعادة بعد —
سجل الجلسة سقالة اختبار (جذر مؤقت) لا دليل جنائي؛ خاصية append-only
الإنتاجية محروسة بذاتها في test_quarantine_log.py على جذور معزولة.
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for _p in (str(_REPO_ROOT), str(_BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi.testclient import TestClient

from app import app  # noqa: E402
from backend.loyalty_log import append_entry, quarantine_log_path  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_session_quarantine_log():
    """عزل الاختبارات عن بعضها: لقطة لسجل عزل الجلسة قبل الاختبار ← استعادة
    بعده (حذف إن لم يكن موجودًا / إعادة المحتوى الأصلي إن كان) — يعمل حتى
    عند فشل الاختبار في منتصفه (finally)."""
    log = quarantine_log_path()
    existed = log.exists()
    original = log.read_text(encoding="utf-8") if existed else None
    yield
    if existed:
        log.write_text(original, encoding="utf-8")
    elif log.exists():
        log.unlink()


def test_quarantined_component_request_rejected():
    """الطلب لمكوّن معزول يُرفض بأمان: 503 + جسم خطأ محدد."""
    assert append_entry("quarantine", "خلل جسيم", component="predictive") is True
    with TestClient(app) as client:
        resp = client.get("/components/predictive")
        assert resp.status_code == 503, (
            f"المكوّن المعزول يجب أن يُرفض 503 — أعيد {resp.status_code}"
        )
        body = resp.json()
        assert body["error"] == "component_quarantined", f"جسم غير محدد: {body}"
        assert body["component"] == "predictive", f"اسم المكوّن مفقود: {body}"
        assert isinstance(body.get("detail"), str) and body["detail"], (
            f"تفصيل الخطأ مفقود: {body}"
        )


def test_other_components_pass_while_one_quarantined():
    """بينما مكوّن معزول: بقية المكونات تعمل — الأمر نصًّا."""
    append_entry("quarantine", "خلل جسيم", component="predictive")
    with TestClient(app) as client:
        for component in ("memory", "consciousness", "simulation"):
            resp = client.get(f"/components/{component}")
            assert resp.status_code == 200, (
                f"المكوّن غير المعزول {component} يجب أن يمر — "
                f"أعيد {resp.status_code}: {resp.text[:200]}"
            )


def test_non_component_routes_not_gated():
    """المدخل يعزل مكونات فقط: /health و/ (الواجهة) لا يُحجبان حتى مع
    وجود مكوّن معزول."""
    append_entry("quarantine", "خلل", component="consciousness")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 200


def test_release_restores_routing():
    """الرفع المصرح (سطر رفع في السجل) يعيد توجيه المكوّن — دورة كاملة."""
    append_entry("quarantine", "خلل", component="quantum")
    with TestClient(app) as client:
        assert client.get("/components/quantum").status_code == 503
        assert append_entry(
            "release", "رفع بتفويض السيد", component="quantum"
        ) is True
        resp = client.get("/components/quantum")
        assert resp.status_code == 200, (
            f"الرفع يجب أن يعيد التوجيه — أعيد {resp.status_code}: {resp.text[:200]}"
        )


def test_no_quarantine_all_components_pass():
    """بلا سجل عزل: كل المكونات تعمل (ضابط — لا حجب بلا سبب)."""
    with TestClient(app) as client:
        for component in (
            "consciousness", "memory", "predictive", "simulation",
            "sovereign", "quantum", "nexus", "defense",
        ):
            resp = client.get(f"/components/{component}")
            assert resp.status_code == 200, (
                f"بلا عزل يجب أن يمر {component} — أعيد {resp.status_code}"
            )
