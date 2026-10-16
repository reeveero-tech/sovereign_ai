"""
Invariant: أرقام التوثيق تطابق التجميع الفعلي — لا أرقام من الذاكرة

(الأمر الدائم — قواعد التوثيق: «الأرقام في التوثيق تُطابق التجميع الفعلي
(--collect-only) — لا أرقام من الذاكرة»)

الحارس محصور في التقريرين الحاليين (PHASE1_STATUS.md وPHASE2_STATUS.md):
كل «N passed» موثق فيهما كدليل وظيفي يجب أن يطابق التجميع الفعلي
(--collect-only مع اشتراط رمز خروج صفر) للأمر الموثق نفسه بعد تحليله
بـshlex (النطاق والمرشحات محفوظان كما وثقها التقرير). مع مرشّح اختيار
(-k أو -m) يُعدّ المُختار (البسط) لا المقام — لأن «N passed» يعني ما
يُشغّل فعليًا.

سبب الإنشاء (2026-10-16): تقارير المرحلتين أدّعت «33 passed» بينما التجميع
الفعلي للأمر الموثق 50 — اكتشفها وكيل لاحق في مرحلة صفر. RED الفعلي المرصود
قبل التصويب (نص الفشل الحرفي من التشغيل):

    AssertionError: PHASE1_STATUS.md: العدد المُعلن في التوثيق 33 لا يطابق
    التشغيل الفعلي لنفس الأمر (50). قواعد التوثيق: الأرقام تُطابق التشغيل
    الفعلي — لا أرقام من الذاكرة.

ملاحظة نطاق: التقرران يدّعيان «passed» والفحص هنا ضد التجميع (--collect-only)
— لملفات التقريرين لا اختبارات معلّمة تُحذف ولا skips، فالمُجمَّع = الناجح
(50 = 50، مُثبت بالتشغيلين معًا في جولة 2026-10-16).
"""

import re
import shlex
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FORENSICS_DIR = _REPO_ROOT / "forensics"

# الحارس محصور في التقريرين الحاليين — أي تقرير حالة مرحلة جديد يُضاف
# للقائمة صراحة عند إنشائه (لا glob: منع تشغيل أوامر غير مقصودة).
_REQUIRED_REPORTS = ("PHASE1_STATUS.md", "PHASE2_STATUS.md")

# النمط المستهدف (كما في التقريرين):
#     $ python -m pytest <args...> -q
#     N passed
_CLAIM_PATTERN = re.compile(
    r"^\$\s+(python[^\n]*?-m\s+pytest[^\n]+)\n(\d+)\s+passed",
    re.MULTILINE,
)


def _extract_claims(text):
    """يستخرج من نص التقرير: [(الأمر الموثق، العدد المُعلن)]."""
    return [(m.group(1), int(m.group(2))) for m in _CLAIM_PATTERN.finditer(text)]


def _collect(command_line):
    """يشغّل الأمر الموثق بوضع التجميع فقط — يعيد (رمز الخروج، عدد المُختار).

    يُحلَّل الأمر بـshlex: يُحذف المُشغِّل (python -m pytest) والعلم -q
    (لا يؤثر في التجميع)، ويُحافظ على النطاق والمرشحات الأخرى كما وثقها
    التقرير، ثم يُضاف --collect-only. لا يُنفَّذ أي اختبار فعلي هنا.

    عدّ المُختار (البسط) لا المقام: مع مرشّح اختيار يخرج pytest بصيغة
    «6/16 tests collected (10 deselected)» — المُختار 6 وهو ما يعنيه
    «N passed» في التوثيق (ما يُشغّل فعليًا)، لا 16.
    """
    tokens = shlex.split(command_line)
    try:
        pytest_at = tokens.index("pytest")
    except ValueError:
        return 2, -1  # أمر غير قابل للتحليل — يُرفض
    args = [t for t in tokens[pytest_at + 1:] if t != "-q"]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *args, "--collect-only", "-q", "--no-header"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        return result.returncode, -1
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    # صيغة المرشّح: «N/M tests collected (K deselected)» → المُختار = N (البسط)
    m_filtered = re.search(r"(\d+)/(\d+)\s+tests?\s+collected\s+\((\d+)\s+deselected\)", tail)
    if m_filtered:
        return 0, int(m_filtered.group(1))
    m = re.search(r"(\d+)\s+tests?\s+collected", tail)
    if not m:
        return 1, -1
    return 0, int(m.group(1))


def _check_claim(name, command_line, claimed, collector=_collect):
    """يرفض: فشل التجميع / اختلاف العدد. يقبل: الحالة السليمة فقط."""
    returncode, collected = collector(command_line)
    assert returncode == 0, (
        f"{name}: فشل تجميع الأمر الموثق (رمز الخروج {returncode}) — لا يمكن "
        f"التحقق من العدد المُعلن. command: {command_line}"
    )
    assert collected == claimed, (
        f"{name}: العدد المُعلن في التوثيق {claimed} لا يطابق التجميع الفعلي "
        f"لنفس الأمر ({collected}). قواعد التوثيق: الأرقام تُطابق التجميع "
        f"الفعلي — لا أرقام من الذاكرة. command: {command_line}"
    )


def _read_report(name):
    path = FORENSICS_DIR / name
    assert path.is_file(), f"التقرير المطلوب غير موجود: {name}"
    return path.read_text(encoding="utf-8")


# --- إثبات سلوكي لمسارات الحارس (فشل محقون + مسار سليم) ---

def test_missing_claim_yields_no_claims():
    """نص بلا نمط ادعاء → لا ادعاءات (الغياب يُكشفه اختبار التقريرين أدناه)."""
    assert _extract_claims("لا نمط هنا\n50 passed\n") == []


def test_collection_failure_is_rejected():
    """فشل التجميع (رمز خروج غير صفر) يُرفض — لا نجاح صامت فوق أمر مكسور."""
    bogus = "python -m pytest tests/__no_such_file__.py -q"
    returncode, _ = _collect(bogus)
    assert returncode != 0, "الأمر المكسور يجب أن يفشل في التجميع فعليًا"
    try:
        _check_claim("SYNTHETIC.md", bogus, 0)
    except AssertionError as e:
        assert "فشل تجميع الأمر الموثق" in str(e)
    else:
        raise AssertionError("فشل التجميع يجب أن يُرفض برسالة صريحة")


def test_filtered_collection_counts_selected_not_total():
    """مع مرشّح اختيار: العدّ للمُختار (البسط) لا المقام — إثبات سلوكي حقيقي.

    الأمر يجمع بصيغة «6/16 tests collected (10 deselected)» — المطلوب 6
    (المُختار = ما يعنيه «N passed») لا 16.
    """
    returncode, collected = _collect(
        "python -m pytest tests/test_sovereign_keys.py tests/test_key_selection_rotation.py -k rotation -q"
    )
    assert returncode == 0
    assert collected == 6, (
        f"المرشّح يجب أن يُعطي المُختار (6) لا المقام (16) — حصلنا على {collected}"
    )


def test_count_mismatch_is_rejected():
    """اختلاف العدد (مُعلن 33 / مُجمَّع 50) يُرفض — هذا خطأ السلف المكتشف فعليًا."""
    stub = lambda command_line: (0, 50)  # noqa: E731 — حاقن تجميع ثابت
    try:
        _check_claim("SYNTHETIC.md", "python -m pytest tests/x.py -q", 33, collector=stub)
    except AssertionError as e:
        assert "لا يطابق التجميع الفعلي" in str(e) and "33" in str(e) and "50" in str(e)
    else:
        raise AssertionError("اختلاف العدد يجب أن يُرفض")


def test_healthy_case_is_accepted():
    """المطابقة (مُعلن = مُجمَّع) تُقبل — مسار سليم."""
    stub = lambda command_line: (0, 50)  # noqa: E731 — حاقن تجميع ثابت
    _check_claim("SYNTHETIC.md", "python -m pytest tests/x.py -q", 50, collector=stub)


# --- الحارس على التقريرين الفعليين ---

def test_required_reports_each_have_a_claim():
    """كل تقرير مطلوب يجب أن يُستخرج منه ادعاء — تغيّر النمط يُكشف لا يُتجاهل."""
    for name in _REQUIRED_REPORTS:
        claims = _extract_claims(_read_report(name))
        assert claims, (
            f"{name}: لم يُعثر على نمط «$ pytest ... \\n N passed» — "
            f"إما تغيّر النمط أو حُذف الدليل الوظيفي. حدّث الحارس صراحة."
        )


def test_phase_status_claimed_counts_match_reality():
    """كل «N passed» موثق في التقريرين = التجميع الفعلي للأمر الموثق نفسه."""
    for name in _REQUIRED_REPORTS:
        for command_line, claimed in _extract_claims(_read_report(name)):
            _check_claim(name, command_line, claimed)
