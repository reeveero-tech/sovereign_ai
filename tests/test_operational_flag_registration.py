"""
اختبار تسجيل خيار --run-operational — R-682 (الجولة التشغيلية، إصلاح فجوة CI)

الفجوة (مُثبتة بالتشغيل الفعلي): الوظيفة التشغيلية في CI
(run 38789092766 على SHA 182949f) فشلت بخط:
    python -m pytest: error: unrecognized arguments: --run-operational
لأن العلم مذكور في pytest.ini والاختبار التشغيلي لكن لا يوجد conftest
يسجّله كخيار pytest معروف — فترفضه pytest قبل جمع أي اختبار، أي أن
الوظيفة التشغيلية مستحيلة النجاح بغضّ النظر عن وجود الأسرار.

هذا الاختبار (آمن — لا يقرأ أسرارًا ولا يشغّل الاختبار التشغيلي؛
--collect-only فقط) يُثبت أن العلم مسجّل وأن الاختبار التشغيلي
يُجمع فعلًا تحت -m operational.
"""

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_run_operational_flag_is_registered_and_collects_operational_test():
    """--run-operational خيار pytest معروف + الاختبار التشغيلي يُجمع تحته.

    RED (قبل الإصلاح): الخروج 4 مع 'unrecognized arguments' — راجع
    CI run 38789092766. GREEN (بعد الإصلاح): خروج 0 + معرّف الاختبار
    التشغيلي ظاهر في التجميع.
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "-m", "operational",
            "--run-operational",
            "--collect-only", "-q",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        timeout=180,
    )

    # الخروج 0 = الخيار مقبول (لا 'unrecognized arguments')
    assert result.returncode == 0, (
        f"pytest rejected --run-operational (exit={result.returncode}): "
        f"{result.stderr[-400:]}"
    )

    # الاختبار التشغيلي الوحيد يُجمع فعلًا تحت -m operational
    assert "test_operational_auth_new_key_accepted_old_rejected" in result.stdout, (
        "operational test not collected under -m operational --run-operational: "
        f"{result.stdout[-300:]}"
    )
