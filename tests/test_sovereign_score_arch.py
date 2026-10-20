"""البند المعماري (تدقيق 2026-10-20، البند ٣) — مسح واحد لكل طلب.

R-711 (ب-٢-أ): compute_sovereignty_score_v2 كان يستدعي
mocks_outside_tests_count() مرتين في الطلب الواحد وكل استدعاء يمسح
شجرة المستودع كاملة — مسح مزدوج بلا كاش. المطلوب: استدعاء واحد،
دون أي تغيير في دلالات العدادات (القيم المرجعة كما هي).
"""

from backend.sovereign.primitives import Primitives
from backend.sovereign.score import compute_sovereignty_score_v2


def _instrument_mocks_scan():
    """تلفّ عدّاد الاستدعاءات حول المسح الثقيل — يُستعاد الأصل دائمًا."""
    calls = {"count": 0, "value": None}
    original = Primitives.mocks_outside_tests_count

    def counting(self):
        calls["count"] += 1
        value = original(self)
        calls["value"] = value
        return value

    return original, counting, calls


def test_v2_mocks_scan_exactly_once():
    """RED→GREEN (R-711): المسح الثقيل يُستدعى مرة واحدة فقط لكل حساب.

    قبل الإصلاح: استدعاءان (المتغير no_mocks + مدخل inputs) — الاختبار
    يفشل. بعد الإصلاح: استدعاء واحد — ينجح.
    """
    original, counting, calls = _instrument_mocks_scan()
    Primitives.mocks_outside_tests_count = counting
    try:
        compute_sovereignty_score_v2()
    finally:
        Primitives.mocks_outside_tests_count = original

    assert calls["count"] == 1, (
        f"مسح mocks_outside_tests_count نُفِّذ {calls['count']} مرة في الطلب "
        "الواحد — المطلوب مرة واحدة (مسح مزدوج بلا كاش — بند ٣ من التدقيق)"
    )


def test_v2_mocks_counter_semantics_unchanged():
    """دلالات العدادات لا تتغير: القيمة المرصودة تظهر كما هي في الرد.

    القيمة نفسها التي أعادها المسح تظهر في inputs.mocks_outside_tests_count،
    وno_mocks_in_prod يتسق معها (1 إذا صفر وإلا 0) — قبل الإصلاح وبعده.
    """
    original, counting, calls = _instrument_mocks_scan()
    Primitives.mocks_outside_tests_count = counting
    try:
        result = compute_sovereignty_score_v2()
    finally:
        Primitives.mocks_outside_tests_count = original

    observed = calls["value"]
    assert result["inputs"]["mocks_outside_tests_count"] == observed, (
        "القيمة في الرد لا تطابق القيمة المرصودة من المسح — دلالة العداد تغيرت"
    )
    expected_no_mocks = 1 if observed == 0 else 0
    assert result["no_mocks_in_prod"] == expected_no_mocks, (
        "no_mocks_in_prod لا يتسق مع قيمة المسح — دلالة العداد تغيرت"
    )
