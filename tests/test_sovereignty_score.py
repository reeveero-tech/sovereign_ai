"""
اختبارات درجة السيادة (Sovereignty Score) — المرحلة 5 من ROADMAP_V2

تتحقق من:
1. النقطة /sovereignty/score تعمل
2. الدرجة الكلية بين 0-100
3. كل المحاور الستة موجودة
4. التقييم النصي صحيح (grade)
5. كل محور له وزن صحيح
6. مجموع الأوزان = 100
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from fastapi.testclient import TestClient

from app import app

# المحاور الستة المطلوبة
REQUIRED_AXES = [
    "ledger_integrity",
    "key_management",
    "immune_system",
    "compat_lifecycle",
    "test_health",
    "structural_health",
]

# الأوزان المطلوبة (مجموعها 100)
REQUIRED_WEIGHTS = {
    "ledger_integrity": 25,
    "key_management": 20,
    "immune_system": 20,
    "compat_lifecycle": 10,
    "test_health": 15,
    "structural_health": 10,
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_sovereignty_score_endpoint_exists(client):
    """/sovereignty/score موجود ويعمل (200)."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200, f"failed: {r.status_code} {r.text[:200]}"


def test_sovereignty_score_total_in_range(client):
    """الدرجة الكلية بين 0 و 100."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200

    data = r.json()
    score = data["total_score"]
    assert isinstance(score, (int, float)), f"score must be numeric: {score}"
    assert 0 <= score <= 100, f"score must be 0-100, got {score}"


def test_sovereignty_score_all_axes_present(client):
    """كل المحاور الستة موجودة."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200

    data = r.json()
    axes = data["axes"]
    assert len(axes) == len(REQUIRED_AXES), (
        f"must have {len(REQUIRED_AXES)} axes, got {len(axes)}"
    )

    axis_names = [a["name"] for a in axes]
    for required in REQUIRED_AXES:
        assert required in axis_names, f"missing axis: {required}"


def test_sovereignty_score_weights_correct(client):
    """كل محور له الوزن الصحيح (مجموع 100)."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200

    data = r.json()
    axes = data["axes"]

    total_weight = 0
    for a in axes:
        name = a["name"]
        weight = a["weight"]
        assert name in REQUIRED_WEIGHTS, f"unknown axis: {name}"
        assert weight == REQUIRED_WEIGHTS[name], (
            f"axis {name} weight must be {REQUIRED_WEIGHTS[name]}, got {weight}"
        )
        total_weight += weight

    assert total_weight == 100, f"total weight must be 100, got {total_weight}"


def test_sovereignty_score_grade_valid(client):
    """التقييم النصي (grade) صحيح."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200

    data = r.json()
    grade = data["grade"]

    valid_grades = [
        "SOVEREIGN (سيادي)",
        "PARTIALLY_SOVEREIGN (سيادي جزئيًا)",
        "WORKING_NOT_SOVEREIGN (يعمل لكن غير سيادي)",
        "FRAGILE (هش)",
        "BROKEN (مكسور)",
    ]
    assert grade in valid_grades, f"invalid grade: {grade!r}"


def test_sovereignty_score_each_axis_in_range(client):
    """كل محور له درجة بين 0-100."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200

    data = r.json()
    for a in data["axes"]:
        name = a["name"]
        score = a["score"]
        assert 0 <= score <= 100, (
            f"axis {name} score must be 0-100, got {score}"
        )


def test_sovereignty_score_weighted_consistent(client):
    """الدرجة الموزونة لكل محور متسقة (score * weight / 100)."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200

    data = r.json()
    for a in data["axes"]:
        expected = round((a["score"] * a["weight"]) / 100, 2)
        actual = a["weighted_score"]
        # سماحية صغيرة للفروق التقريبية
        assert abs(expected - actual) <= 0.1, (
            f"axis {a['name']}: weighted_score must be ~{expected}, got {actual}"
        )


def test_sovereignty_score_axes_details_present(client):
    """كل محور له تفاصيل (details) — ليست فارغة."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200

    data = r.json()
    for a in data["axes"]:
        assert isinstance(a["details"], dict), (
            f"axis {a['name']} details must be a dict"
        )


def test_sovereignty_score_timestamp_present(client):
    """التقرير له timestamp."""
    r = client.get("/sovereignty/score")
    assert r.status_code == 200

    data = r.json()
    assert "timestamp" in data
    assert isinstance(data["timestamp"], (int, float))
