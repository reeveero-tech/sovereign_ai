"""جذر conftest — تسجيل خيار pytest الإضافي (R-682 الجولة التشغيلية).

الفجوة: العلم --run-operational مذكور في pytest.ini وفي
tests/test_gate1_operational_auth.py (شرط التشغيل اليدوي)، لكن لم
يسجّله أي conftest كخيار pytest معروف — لذا رفضته pytest بالكامل
('unrecognized arguments') قبل جمع أي اختبار، وفشلت الوظيفة التشغيلية
في CI (run 38789092766 على SHA 182949f) رغم توفر السرّين.

التسجيل هنا (جذر المستودع = rootdir conftest) لأن pytest يستدعي
pytest_addoption فقط على الـ conftests الابتدائية: conftest جذر
المستودع يُحمّل لأي استدعاء من جذر المستودع — بما فيه استدعاء
الوظيفة التشغيلية في CI بلا مسارات (python -m pytest -m operational
--run-operational). أما tests/conftest.py فلا يُحمّل قبل تحليل الخيارات
إلا عند تمرير tests/ كمسار — لا يصلح لتسجيل الخيار.

اختبار الانحدار: tests/test_operational_flag_registration.py
(RED قبل هذا الملف، GREEN بعده — راجع forensics/OPERATIONAL_TESTS.md).
"""


def pytest_addoption(parser):
    parser.addoption(
        "--run-operational",
        action="store_true",
        default=False,
        help=(
            "R-661/R-682: تشغيل اختبارات operational التشغيلية "
            "(تقرأ أسرار المضيف وتكتب بيانات حقيقية — يدويًا فقط)"
        ),
    )
