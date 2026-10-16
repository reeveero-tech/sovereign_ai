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


def _all_http_routes():
    """استخراج كل المسارات المسجلة فعلًا من التطبيق (تصويب المراجع —
    الاعتراض 2: قائمة الخمسة الثابتة لا تثبت تغطية الجميع)."""
    routes = []
    for r in app_routes():
        methods = sorted(
            m for m in getattr(r, "methods", []) if m not in ("HEAD", "OPTIONS")
        )
        path = getattr(r, "path", None)
        if path is None:
            continue
        if not methods:
            continue  # websocket/محمولات ثابتة — موثقة في INVARIANT_LIMITS
        routes.append((methods, path))
    return routes


def app_routes():
    from app import app
    return app.routes


def _substitute_params(path: str) -> str:
    """تعويض معاملات المسار بقيم عينة صالحة."""
    import re
    return re.sub(r"\{([^}]+)\}", "test", path)


def test_all_registered_routes_respond(client):
    """Invariant (ROADMAP_V2 — المرحلة 3، البند 6): كل مسار HTTP مسجّل في
    FastAPI يُعيد رمزًا غير 500. يُستخرج المسار والطرق من التطبيق نفسه —
    لا قائمة يدوية. 422/400/403 (تحقق مدخلات/رفض مصادقة) مقبولة: ليست
    أخطاء خادم. الرفض المقصود سلوك صحيح لا فشل استجابة."""
    routes = _all_http_routes()
    assert len(routes) >= 40, (
        f"expected a real route surface, got only {len(routes)} routes"
    )

    failures = []
    for methods, path in routes:
        concrete = _substitute_params(path)
        for method in methods:
            if method == "GET":
                resp = client.get(concrete)
            elif method == "POST":
                resp = client.post(concrete, json={})
            else:
                # طريقة أخرى (PUT/DELETE...) — طلب بجسم فارغ مناسب
                resp = client.request(method, concrete, json={})
            if resp.status_code >= 500:
                failures.append((method, path, resp.status_code))

    assert len(failures) == 0, (
        f"Registered endpoints returning 5xx (dead/broken routes): {failures}"
    )


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


# DELETION-JUSTIFIED — R-683 (قرار المالك 2026-10-16): أُعيدت كتابة هذا
# الاختبار ليعكس عقد /sovereignty/score الجديد (المكونات الخمسة القابلة
# للقياس فقط) — تحديث اختبار ليعكس عقدًا جديدًا بقرار مالك، ليس تخفيفًا.
# مفصل في forensics/DELETED_LINES_AUDIT.md (جولة R-683).
_V2_EXPECTED_FIELDS = sorted([
    "files_reachable",
    "modules_tested",
    "compat_pending_sunset",
    "no_mocks_in_prod",
    "invariants_passing",
    "final_score",
    "ledger_components_note",
    "invariants_evidence",
    "inputs",
    "aggregation",
])

_V2_AGGREGATION_EXACT = (
    "final_score = mean(5 scored components) — documented choice; "
    "ROADMAP_V2 does not specify weights; not tunable to improve results"
)


def _assert_unit_number(v2, name):
    value = v2[name]
    assert type(value) is not bool, f"{name} must be numeric, got bool {value!r}"
    assert isinstance(value, (int, float)), f"{name} must be numeric, got {value!r}"
    assert value >= 0.0, f"{name} below 0: {value!r}"
    assert value <= 1.0, f"{name} above 1: {value!r}"


def test_sovereignty_score_reports_roadmap_v2(client):
    """R-683 (قرار المالك): /sovereignty/score يعرض عقد الدرجة الجديد —
    المكونات الخمسة القابلة للقياس فقط، بلا مكونات سجل ولا علم حد ولا
    نطاق ثقة، وaggregation يطابق mean(5) حرفيًا."""
    resp = client.get("/sovereignty/score")
    assert resp.status_code == 200, f"/sovereignty/score returned {resp.status_code}"

    data = resp.json()
    assert "roadmap_v2" in data, "route must expose the ROADMAP_V2 equation"
    v2 = data["roadmap_v2"]

    # قائمة الحقول بالضبط — لا زيادة ولا نقص
    assert sorted(v2.keys()) == _V2_EXPECTED_FIELDS, (
        f"roadmap_v2 fields mismatch: {sorted(v2.keys())}"
    )

    # الحقول الأربعة المحذوفة غائبة — تأكيد صريح لكل حقل
    assert "ledger_verified" not in v2, "ledger_verified must be removed"
    assert "ledger_anchored" not in v2, "ledger_anchored must be removed"
    assert "score_capped_by_missing_ledger" not in v2, (
        "score_capped_by_missing_ledger must be removed"
    )
    assert "confidence_range" not in v2, "confidence_range must be removed"

    # المكونات الخمسة أرقام بين 0 و1 — تأكيد صريح لكل مكون
    _assert_unit_number(v2, "files_reachable")
    _assert_unit_number(v2, "modules_tested")
    _assert_unit_number(v2, "compat_pending_sunset")
    _assert_unit_number(v2, "no_mocks_in_prod")
    _assert_unit_number(v2, "invariants_passing")

    # final_score = متوسط الخمسة بالضبط
    expected_final = round(
        (v2["files_reachable"] + v2["modules_tested"]
         + v2["compat_pending_sunset"] + v2["no_mocks_in_prod"]
         + v2["invariants_passing"]) / 5, 4)
    assert v2["final_score"] == expected_final, (
        f"final_score {v2['final_score']} != mean(5) {expected_final}"
    )

    # aggregation يساوي mean(5) حرفيًا
    assert v2["aggregation"] == _V2_AGGREGATION_EXACT, (
        f"aggregation mismatch: {v2['aggregation']!r}"
    )

    # الدليل معلوم الهوية — لا نجاح صامت بلا مصدر
    ev = v2["invariants_evidence"]
    assert "source" in ev, "invariants_evidence must declare source"
    assert "head_sha" in ev, "invariants_evidence must declare head_sha"
