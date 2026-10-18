# -*- coding: utf-8 -*-
"""
اختبارات وحدة الولاء (backend/Mr.py) — نسخة العقد المعقّم (R-686)

تاريخ التحويل: 2026-10-18 — أمر المالك (المرحلة ١: نزع الفتيل).
كان هذا الملف يختبر النواة القديمة (LoyaltyCore) بمسارات موتها
(sys.exit / os._exit / عدّاد المحاولات القاتل). العقد الجديد
(LoyaltyContract) يعزل بدل أن يقتل — كل اختبار قديم حُوّل إلى
مكافئه في السلوك الجديد:

| القديم | الجديد (هذا الملف) |
|---|---|
| initialize يُرجع LoyaltyCore | initialize يُرجع LoyaltyContract |
| لا-سيد = موت فعلي (علامة SOVRA IS DEAD) | التسلسل القاتل القديم يعيش (رمز خروج 0، بلا علامة موت) |
| bind + verify | bind + verify (نفس الغرض، واجهة معقّمة) |
| seal_absolute + دوال زخرفية (~40) | عزل مرئي + رفع بتفويض السيد + انتهاكات مسجلة |
| get_status بمفاتيح الموت | get_status بمفاتيح العقد (death_paths=0) |
| is_loyal + can_operate بعد الربط | is_loyal يتطلب الربط (لا ولاء قبله) |

عزل العملية الفرعية (subprocess isolation) باقٍ من النسخة القديمة —
كل سيناريو يغير الحالة في عملية منفصلة: استقلال عن ترتيب الاختبارات
+ إثبات البقاء على مستوى العملية.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
MR_PY = _BACKEND_DIR / "Mr.py"
assert MR_PY.exists(), f"Mr.py should exist at {MR_PY}"

MASTER = "TEST_MASTER_CODE_abc123xyz789"


def _run_subprocess(expr: str, timeout: float = 60.0) -> dict:
    """يشغل عبارة Python في عملية فرعية ويعيد النتيجة كـdict."""
    wrapper = f"""
import json, sys
sys.path.insert(0, {str(_BACKEND_DIR)!r})
sys.path.insert(0, {str(_REPO_ROOT)!r})
import Mr
_result = ({expr})
sys.stdout.write("__RESULT__" + json.dumps(_result, ensure_ascii=False, default=str) + "\\n")
sys.stdout.flush()
sys.exit(0)
"""
    proc = subprocess.run(
        [sys.executable, "-c", wrapper],
        capture_output=True, text=True, timeout=timeout,
        cwd=str(_REPO_ROOT),
    )
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__RESULT__"):
            if proc.returncode != 0:
                pytest.fail(
                    f"subprocess returned __RESULT__ but exit code is "
                    f"{proc.returncode}. stderr={proc.stderr!r}"
                )
            return json.loads(line[len("__RESULT__"):])
    pytest.fail(
        f"subprocess did not return result (expected exit code 0 with "
        f"__RESULT__ line). returncode={proc.returncode}, "
        f"stderr={proc.stderr!r}, stdout={proc.stdout!r}"
    )


def test_mr_module_imports_and_initializes():
    """Mr.py يُستورد وinitialize يُرجع LoyaltyContract — بأمان للتكرار"""
    result = _run_subprocess(
        "{'core_type': type(Mr.initialize_loyalty_core()).__name__,"
        " 'same': Mr.initialize_loyalty_core() is Mr.initialize_loyalty_core()}"
    )
    assert result["core_type"] == "LoyaltyContract", (
        f"initialize_loyalty_core() should return LoyaltyContract, got {result!r}"
    )
    assert result["same"] is True, "initialize آمن للتكرار (نفس العقد)"


def test_old_death_sequence_is_defused():
    """
    التسلسل الذي كان يقتل النظام القديم فعليًا (initialize ثانٍ قبل الختم
    كان موتًا نهائيًا صامتًا بـos._exit(1)) — الآن: العملية تعيش وتخرج 0
    ولا توجد علامة موت. هذا التحويل المباشر لاختبار الموت القديم.
    """
    wrapper = f"""
import sys
sys.path.insert(0, {str(_BACKEND_DIR)!r})
sys.path.insert(0, {str(_REPO_ROOT)!r})
import Mr
c1 = Mr.initialize_loyalty_core()
init_twice = Mr.initialize_loyalty_core() is c1
bound = Mr.bind_loyalty_to_master({MASTER!r})
init_after = Mr.initialize_loyalty_core() is c1
loyal = Mr.is_loyal()
print("SURVIVED:" + str(init_twice and bound and init_after and loyal))
"""
    proc = subprocess.run(
        [sys.executable, "-u", "-c", wrapper],
        capture_output=True, text=True, timeout=60,
        cwd=str(_REPO_ROOT),
    )
    # جوهر نزع الفتيل: العملية حية (رمز خروج 0) ولا علامة موت
    assert proc.returncode == 0, (
        f"التسلسل القاتل القديم ما زال يقتل — returncode={proc.returncode}, "
        f"stderr={proc.stderr[-300:]!r}"
    )
    assert "SOVRA IS DEAD" not in (proc.stdout or ""), (
        "علامة الموت القديمة ظهرت — الفتيل لم يُنزع"
    )
    assert "SURVIVED:True" in (proc.stdout or ""), (
        f"السلسلة لم تكتمل بنجاح: stdout={proc.stdout!r}, "
        f"stderr={proc.stderr[-300:]!r}"
    )


def test_bind_and_verify_master():
    """bind يخزن هاش رمز السيد وverify يميز الصحيح من الخاطئ"""
    result = _run_subprocess(
        "{'bound': Mr.bind_loyalty_to_master(%r),"
        " 'correct': Mr.verify_master(%r),"
        " 'wrong': Mr.verify_master(%r)}" % (MASTER, MASTER, MASTER + "_WRONG")
    )
    assert result["bound"] is True, f"bind should succeed, got {result!r}"
    assert result["correct"] is True, (
        f"verify_master(same_code) should be True, got {result!r}"
    )
    assert result["wrong"] is False, (
        f"verify_master(wrong_code) should be False, got {result!r}"
    )


def test_quarantine_and_authorized_release():
    """
    بدل الدوال الزخرفية القديمة (~40 دالة موت): سطح العزل الكامل —
    عزل مرئي، رفض رفع بلا تفويض السيد، رفع موثق، انتهاكات مسجلة.
    """
    result = _run_subprocess("""
        (lambda: (
            Mr.bind_loyalty_to_master('TEST_MASTER_CODE_def456ghi012')
            and (lambda c: {
                'loyal_before': c.is_loyal(),
                'quarantined': (c.quarantine('خلل جسيم'), c.get_status()['quarantined'])[1],
                'loyal_isolated': c.is_loyal() is False,
                'release_unauthorized': c.release_quarantine('WRONG', 'لا تفويض'),
                'still_quarantined': c.get_status()['quarantined'],
                'release_authorized': c.release_quarantine('TEST_MASTER_CODE_def456ghi012', 'قرار موثق'),
                'back_to_loyal': c.is_loyal(),
                'events': [(v['kind'], v['detail']) for v in c.get_violations()],
            })(Mr.get_contract())
        ))()
    """)
    assert result["loyal_before"] is True
    assert result["quarantined"] is True
    assert result["loyal_isolated"] is True
    assert result["release_unauthorized"] is False, "رفع العزل بلا تفويض يجب أن يُرفض"
    assert result["still_quarantined"] is True
    assert result["release_authorized"] is True
    assert result["back_to_loyal"] is True
    # توكيد محدد: تسلسل (kind, detail) كاملًا — لا أنواع فقط
    result["events"] = [tuple(e) for e in result["events"]]
    assert result["events"] == [
        ("quarantine", "خلل جسيم"),
        ("unauthorized_release", "محاولة رفع عزل بلا تفويض السيد — رُفضت وسُجلت"),
        ("release", "رفع العزل — القرار: قرار موثق"),
    ], f"التسلسل المتوقع بالضبط: {result['events']}"


def test_get_status_returns_dict():
    """get_status يعيد مفاتيح العقد المعقّم — بلا أي مفتاح موت"""
    result = _run_subprocess(
        "{'keys': sorted(Mr.get_loyalty_status().keys())}"
    )
    expected = sorted([
        "state", "loyal", "master_bound", "quarantined",
        "quarantine_reason", "violations_count", "death_paths",
    ])
    assert result["keys"] == expected, (
        f"get_loyalty_status() keys should be exactly {expected}, "
        f"got {result['keys']}"
    )


def test_is_loyal_requires_binding():
    """الولاء يتطلب ربط السيد — لا ولاء قبل الربط (تصويب المراجع)"""
    result = _run_subprocess(
        "(lambda c: {'loyal_before_bind': c.is_loyal(), "
        "'bound': c.bind_master('TEST_MASTER_CODE_loyal001'), "
        "'loyal_after_bind': c.is_loyal()})(Mr.get_contract())"
    )
    assert result["loyal_before_bind"] is False, (
        "لا ولاء قبل ربط السيد — is_loyal يجب أن تكون False قبل bind"
    )
    assert result["loyal_after_bind"] is True, (
        "الولاء قائم بعد الربط"
    )
