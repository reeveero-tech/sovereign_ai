"""
اختبار عدم تسريب المفاتيح في مسار استثناء طلب المصادقة — R-682 (الجولة الرابعة)

أمر المستشار: تجربتا الجولة الثالثة (فشل السب-بروسس + فشل المصادقة 403)
لا تغطيان مسار **استثناء** طلب المصادقة — الكود ينسخ str(e) إلى النتائج
ثم يضعها في رسالة فشل الاختبار، ورسائل أخطاء HTTP قد تتضمن URL الطلب
ومعه معامل master_key.

الاختبار يحاكي الحالة الأسوأ بأمان (مفاتيح وهمية فقط، بلا أسرار حقيقية):
تطبيق ASGI وهمي يرفع استثناءً نصّه يحمل نص الاستعلام كاملًا (ومنه
master_key الوهمي)، ثم يُشغَّل السكربت الحقيقي نفسه
(_build_verification_script) في سب-بروسس، ونتحقق أن قيم المفاتيح
الوهمية لا تظهر في مخرجات السب-بروسس (stdout/stderr) — وهي مصدر
رسائل فشل pytest وJUnit في الأب.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from test_gate1_operational_auth import _build_verification_script

_REPO_ROOT = Path(__file__).resolve().parent.parent

_DUMMY_NEW = "DUMMY_injected_new_9f3a"
_DUMMY_OLD = "DUMMY_injected_old_7c1b"

_FAKE_APP = '''"""تطبيق وهمي — مسار يرفع استثناءً يحمل قيمة master_key في نصّه (لا يستورد التطبيق الحقيقي).

FastAPI حقيقي حتى يمر الطلب بمسار التشخيص الفعلي نفسه (استثناء من داخل
المسار يُعاد رفعه عبر TestClient) — راجع الجولة الرابعة في
OPERATIONAL_TESTS.md حيث أثبتت تجربة سابقة بمسار زائف (خطأ توقيع دالة)
اختبارًا أخضر زائفًا.
"""

from fastapi import FastAPI

_ap = FastAPI()


@_ap.get("/api-key")
def api_key(master_key: str = ""):
    raise RuntimeError(
        "connection failed while processing request query: master_key="
        + master_key
    )


app = _ap
'''


def test_auth_request_exception_path_does_not_leak_keys(tmp_path):
    """مسار الاستثناء: str(e) في النتائج يجب ألا يحمل قيمة أي مفتاح.

    RED (قبل التنقية): الاستثناء الوهمي يحمل master_key في نصه → يظهر
    في results['new_key_error'] → في رسالة فشل pytest وJUnit.
    GREEN (بعد التنقية): القيم الوهمية غائبة عن كل مخرجات السب-بروسس.
    """
    backend_dir = tmp_path / "backend"
    backend_dir.mkdir()
    (backend_dir / "app.py").write_text(_FAKE_APP, encoding="utf-8")

    script = _build_verification_script(tmp_path)
    subprocess_env = {
        **{k: v for k, v in os_environ().items()
           if k not in ("SOVEREIGN_KEY", "SOVEREIGN_DATA_ROOT")},
        "TEST_NEW_KEY": _DUMMY_NEW,
        "TEST_OLD_KEY": _DUMMY_OLD,
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=subprocess_env,
        timeout=120,
    )

    # السب-بروسس يعمل ويُنتج النتائج (الاستثناء مُلتقط لا قاتل)
    assert result.returncode == 0, (
        f"subprocess failed: {result.stderr[-400:]}"
    )
    lines = [l for l in result.stdout.strip().split("\n") if l.strip().startswith("{")]
    assert lines, f"no JSON in output: stdout={result.stdout[-200:]} stderr={result.stderr[-200:]}"
    results = json.loads(lines[-1])

    # الاستثناء مُلتقط في مسار الأخطاء (وليس في الحالات) — أي أننا في
    # المسار المطلوب اختباره فعلًا
    assert "new_key_error" in results or "old_key_error" in results, (
        f"expected the injected exception to be captured in error fields, "
        f"got: {results}"
    )

    # الاستثناء المحقون هو المُلتقط فعلًا (حارس ضد الأخضر الزائف: تجربة
    # سابقة التقطت خطأ توقيع دالة بدل الاستثناء المحقون)
    captured_errors = results.get("new_key_error", "") + results.get("old_key_error", "")
    assert "connection failed while processing request query" in captured_errors, (
        f"the injected exception was not the one captured — test is not on "
        f"the intended path, got: {results}"
    )

    # التحقق من التسريب: القيمتان الوهميتان غائبتان عن كل المخرجات
    combined = result.stdout + result.stderr
    assert _DUMMY_NEW not in combined, (
        f"LEAK: dummy NEW key value appeared in subprocess output: "
        f"{combined[-300:]}"
    )
    assert _DUMMY_OLD not in combined, (
        f"LEAK: dummy OLD key value appeared in subprocess output: "
        f"{combined[-300:]}"
    )


def os_environ():
    import os
    return dict(os.environ)
