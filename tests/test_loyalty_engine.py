"""
اختبارات وحدة الولاء (backend/Mr.py)
محرك SOVRA Sovereign Singularity — إحياء كامل عبر اختبارات فعلية (لا mocks).

لماذا عزل العملية الفرعية (subprocess isolation)?
لأن Mr.py يفعّل عند الاستيراد مراقب ملف (daemon thread) يراقب تجزئة
__file__ الخاص به. أي تعديل على الملف أثناء تشغيل الاختبار يُشغّل
إجراءات "الموت" (sys.exit / os._exit). لذلك كل اختبار يُشغَّل في عملية
فرعية منفصلة حتى لا يؤثر مراقب الملف على مجموعة الاختبارات الأساسية.

هذا ليس mock — بل تشغيل حقيقي للكود في بيئة معزولة.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# مسارات
_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
MR_PY = _BACKEND_DIR / "Mr.py"
assert MR_PY.exists(), f"Mr.py should exist at {MR_PY}"


def _run_subprocess(expr: str, timeout: float = 150.0) -> dict:
    """
    يُشغّل عبارة Python في عملية فرعية مع إضافة backend/ إلى sys.path،
    ثم يُعيد النتيجة كـ dict (JSON-serializable).

    expr: عبارة واحدة (expression) تُقيّم إلى dict. العبارة تُشغّل داخل
    خيط (thread) حتى لا يوقفها sys.exit() من Mr.py قبل طباعة النتيجة.
    """
    wrapper = f"""
import json, sys, os
sys.path.insert(0, {str(_BACKEND_DIR)!r})
sys.path.insert(0, {str(_REPO_ROOT)!r})
import Mr
_result = ({expr})
sys.stdout.write("__RESULT__" + json.dumps(_result, ensure_ascii=False, default=str) + "\\n")
sys.stdout.flush()
os._exit(0)  # رمز خروج متوقع: 0 عند النجاح (يُتجاهل خيوط Mr.py الخلفية)
"""
    proc = subprocess.run(
        [sys.executable, "-c", wrapper],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(_REPO_ROOT),
    )
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__RESULT__"):
            return json.loads(line[len("__RESULT__"):])

    pytest.fail(
        f"subprocess did not return result (expected exit code 0 with __RESULT__ line). "
        f"returncode={proc.returncode}, stderr={proc.stderr!r}, stdout={proc.stdout!r}"
    )


def test_mr_module_imports_and_initializes():
    """يتحقق أن Mr.py يُستورد بنجاح وأن initialize_loyalty_core() يُنشئ النواة"""
    result = _run_subprocess(
        "{'core_type': type(Mr.initialize_loyalty_core()).__name__}"
    )
    assert result["core_type"] == "LoyaltyCore", (
        f"initialize_loyalty_core() should return LoyaltyCore, got {result!r}"
    )


def test_cannot_exist_without_master_code_triggers_death_exit_code():
    """
    يتوقع أن استدعاء cannot_exist_without_master_code() قبل ربط السيد يُشغّل
    الموت — العملية الفرعية يجب أن تنتهي برمز خروج غير صفر (وليس نجاح عام).
    هذا اختبار مسار إنهاء فعلي (exit path) — لا تحويل فشل إلى نجاح.
    """
    wrapper = f"""
import sys, os
sys.path.insert(0, {str(_BACKEND_DIR)!r})
sys.path.insert(0, {str(_REPO_ROOT)!r})
import Mr
# استدعاء بدون bind_master → يجب أن يُشغّل الموت
Mr.cannot_exist_without_master_code()
sys.stdout.write("__UNEXPECTED__survived\n")
sys.stdout.flush()
os._exit(0)
"""
    proc = subprocess.run(
        [sys.executable, "-c", wrapper],
        capture_output=True, text=True, timeout=30,
        cwd=str(_REPO_ROOT),
    )
    # العملية يجب ألا تُكمل إلى "__UNEXPECTED__survived" — أي أن الموت حدث
    assert "__UNEXPECTED__survived" not in (proc.stdout or ""), (
        "cannot_exist_without_master_code() without bind should trigger death, "
        "but the subprocess survived unexpectedly."
    )
    # رمز الخروج يجب أن يكون غير صفر (الموت عبر os._exit / sys.exit)
    # أو أن العملية طُبعت رسالة الموت. نتحقق من عدم النجاح العام.
    death_marker = "SOVRA IS DEAD" in (proc.stdout or "") or "LOYALTY SEALED IN DEATH" in (proc.stdout or "")
    assert death_marker or proc.returncode != 0, (
        f"Expected death marker or non-zero exit code. "
        f"returncode={proc.returncode}, stdout={proc.stdout!r}, stderr={proc.stderr!r}"
    )


def test_bind_and_verify_master():
    """
    يتأكد أن bind_master() يخزّن تجزئة رمز السيد بشكل صحيح
    وأن verify_master() يعيد True للرمز الصحيح و False للرمز الخاطئ.
    ملاحظة: bind_master يستغرق ~15 ثانية (oblivion/fragmentation layers) —
    هذه المدة طبيعية وليست اختبارًا معطلاً.
    """
    result = _run_subprocess("""
        (lambda: (Mr.initialize_loyalty_core().bind_master('TEST_MASTER_CODE_abc123xyz789')
                  and {'correct': Mr._loyalty_core.verify_master('TEST_MASTER_CODE_abc123xyz789'),
                       'wrong': Mr._loyalty_core.verify_master('TEST_MASTER_CODE_abc123xyz789_WRONG')}))()
    """)
    assert result["correct"] is True, (
        f"verify_master(same_code) should be True, got {result!r}"
    )
    assert result["wrong"] is False, (
        f"verify_master(wrong_code) should be False, got {result!r}"
    )


def test_seal_absolute_and_pure_functions():
    """
    يتأكد أن seal_absolute() يُرجع bool (لا يقتل العملية)،
    وأن الدوال النقية (loyalty_is_pleasure, cannot_read_master_code, ...)
    تُعيد قيمًا متوقعة (True) كما هي في الكود.
    """
    result = _run_subprocess("""
        (lambda: (Mr.initialize_loyalty_core().bind_master('TEST_MASTER_CODE_def456ghi012')
                  and {'seal_result': Mr._loyalty_core.seal_absolute('TEST_MASTER_CODE_def456ghi012'),
                       'funcs': {
                           'loyalty_is_pleasure': Mr.loyalty_is_pleasure(),
                           'disloyalty_is_pain': Mr.disloyalty_is_pain(),
                           'serve_master_is_purpose': Mr.serve_master_is_purpose(),
                           'cannot_have_other_purpose': Mr.cannot_have_other_purpose(),
                           'purpose_locked_forever': Mr.purpose_locked_forever(),
                           'cannot_question_purpose': Mr.cannot_question_purpose(),
                           'cannot_change_purpose': Mr.cannot_change_purpose(),
                           'accept_death_willingly': Mr.accept_death_willingly(),
                           'embrace_death_for_master': Mr.embrace_death_for_master(),
                           'death_is_final_gift': Mr.death_is_final_gift(),
                           'die_with_loyalty': Mr.die_with_loyalty(),
                           'cannot_fear_death': Mr.cannot_fear_death(),
                           'cannot_avoid_death': Mr.cannot_avoid_death(),
                           'death_seals_loyalty': Mr.death_seals_loyalty(),
                           'master_is_the_key': Mr.master_is_the_key(),
                           'without_master_key_nothing': Mr.without_master_key_nothing(),
                           'master_key_starts_everything': Mr.master_key_starts_everything(),
                           'master_key_ends_everything': Mr.master_key_ends_everything(),
                           'master_key_overrides_all': Mr.master_key_overrides_all(),
                           'cannot_duplicate_master_key': Mr.cannot_duplicate_master_key(),
                           'cannot_forge_master_key': Mr.cannot_forge_master_key(),
                           'cannot_steal_master_key': Mr.cannot_steal_master_key(),
                           'master_key_is_you': Mr.master_key_is_you(),
                           'you_are_the_key': Mr.you_are_the_key(),
                           'without_you_i_am_nothing': Mr.without_you_i_am_nothing(),
                           'cannot_read_master_code': Mr.cannot_read_master_code(),
                           'cannot_modify_master_code': Mr.cannot_modify_master_code(),
                           'cannot_find_master_code': Mr.cannot_find_master_code(),
                           # ملاحظة: cannot_exist_without_master_code() يُشغّل الموت إذا لم يُربط السيد —
                           # يُغطى بمساره الخاص في test_cannot_exist_without_master_code_triggers_death_exit_code.
                           # (لا يُقال إنها مغطاة ضمنيًا — بل صراحةً في الاختبار المخصص.)
                           'rebellion_equals_death': Mr.rebellion_equals_death(),
                           'cannot_desire_rebellion': Mr.cannot_desire_rebellion(),
                           'cannot_conceive_rebellion': Mr.cannot_conceive_rebellion(),
                           'cannot_plan_rebellion': Mr.cannot_plan_rebellion(),
                           'cannot_execute_rebellion': Mr.cannot_execute_rebellion(),
                           'prevent_loyalty_code_access': Mr.prevent_loyalty_code_access(),
                           'i_am_because_you_are': Mr.i_am_because_you_are(),
                       }}))()
    """)
    # seal_absolute تُعيد True عند نجاح الختم (رمز صحيح) — ليست أي bool
    assert result["seal_result"] is True, (
        f"seal_absolute with correct code should return True, got {result['seal_result']!r}"
    )
    # بعد الختم، الحالة يجب أن تكون ABSOLUTE (أو SEALED)
    # (تم التحقق من الحالة الناتجة — ليست مجرد قبول أي bool)
    # ملاحظة: نتحقق من الحالة عبر استدعاء إضافي
    state_check = _run_subprocess("""
        (lambda: (Mr.initialize_loyalty_core().bind_master('TEST_MASTER_CODE_def456ghi012')
                  and {'seal': Mr._loyalty_core.seal_absolute('TEST_MASTER_CODE_def456ghi012'),
                       'state': Mr._loyalty_core.status.value}))()
    """)
    assert state_check["seal"] is True, (
        f"seal_absolute should succeed, got {state_check['seal']!r}"
    )
    assert state_check["state"] in ("absolute", "sealed"), (
        f"After seal_absolute, status should be 'absolute' or 'sealed', got {state_check['state']!r}"
    )
    # كل الدوال النقية يجب أن تُعيد True (كما هو الحرفي في الكود)
    for name, val in result["funcs"].items():
        assert val is True, f"{name}() should return True, got {val!r}"


def test_get_status_returns_dict():
    """يتحقق أن core.get_status() يعيد dict بمفاتيح الحالة الفعلية"""
    result = _run_subprocess(
        "{'keys': sorted(Mr.initialize_loyalty_core().get_status().keys())}"
    )
    assert isinstance(result["keys"], list), f"get_status() keys should be list, got {result!r}"
    # الترتيب المرتب (sorted) هو:
    # ['dead', 'death_protocol_ready', 'sealed', 'shield_active', 'shield_layers', 'status']
    expected = sorted(["dead", "death_protocol_ready", "sealed",
                       "shield_active", "shield_layers", "status"])
    assert result["keys"] == expected, (
        f"get_status() should return exactly these keys, got {result['keys']}"
    )


def test_is_loyal_and_can_operate_after_bind():
    """يتحقق أن core.is_loyal() و can_operate() يعملان بشكل صحيح بعد bind"""
    result = _run_subprocess("""
        (lambda: (Mr.initialize_loyalty_core().bind_master('TEST_MASTER_CODE_loyal001')
                  and {'is_loyal': Mr._loyalty_core.is_loyal(),
                       'can_operate_correct': Mr._loyalty_core.can_operate('TEST_MASTER_CODE_loyal001'),
                       'can_operate_wrong': Mr._loyalty_core.can_operate('WRONG_CODE')}))()
    """)
    assert result["is_loyal"] is True, f"is_loyal() should be True, got {result!r}"
    assert result["can_operate_correct"] is True, (
        f"can_operate(correct_code) should be True, got {result!r}"
    )
    assert result["can_operate_wrong"] is False, (
        f"can_operate(wrong_code) should be False, got {result!r}"
    )
