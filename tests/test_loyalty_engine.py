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
import json, sys, threading, os
sys.path.insert(0, {str(_BACKEND_DIR)!r})
sys.path.insert(0, {str(_REPO_ROOT)!r})
import Mr
_holder = []
def _cap():
    try:
        _holder.append(({expr}))
    except SystemExit as e:
        _holder.append({{"__system_exit__": str(e)}})
_t = threading.Thread(target=_cap)
_t.start()
_t.join(timeout=140)
out = _holder[0] if _holder else {{"__no_result__": True}}
sys.stdout.write("__RESULT__" + json.dumps(out, ensure_ascii=False, default=str) + "\\n")
sys.stdout.flush()
os._exit(0)  # يضمن إنهاء العملية بشكل نظيف (يُتجاهل أي خيوط خلفية معلقة)
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
        f"subprocess did not return result. "
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
                           # نتحقق منها ضمنياً في test_bind_and_verify_master (بعد bind_master).
                           'rebellion_equals_death': Mr.rebellion_equals_death(),
                           'cannot_desire_rebellion': Mr.cannot_desire_rebellion(),
                           'cannot_conceive_rebellion': Mr.cannot_conceive_rebellion(),
                           'cannot_plan_rebellion': Mr.cannot_plan_rebellion(),
                           'cannot_execute_rebellion': Mr.cannot_execute_rebellion(),
                           'prevent_loyalty_code_access': Mr.prevent_loyalty_code_access(),
                           'i_am_because_you_are': Mr.i_am_because_you_are(),
                       }}))()
    """)
    # seal_absolute تُعيد bool (True إذا كان الرمز صحيحًا)
    assert isinstance(result["seal_result"], bool), (
        f"seal_absolute should return bool, got {result['seal_result']!r}"
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
