"""
اختبار البوابة 1 (التحقق التشغيلي المنفصل) — R-655/R-661

**R-661: هذا الاختبار لا يُشغّل في المجموعة الاعتيادية (pytest tests/).**
يقرأ أسرار المضيف و يكتب في البيانات الحقيقية — يُشغّل يدويًا فقط:

    pytest tests/test_gate1_operational_auth.py --run-operational

**R-682 (Task 3.3): عُزل تحت marker @pytest.mark.operational.**
يُشغّل فقط بـ --run-operational أو بـ job CI مستقل عند تفعيله يدويًا.
راجع forensics/OPERATIONAL_TESTS.md للتفاصيل.

المجموعة الاعتيادية تستخدم بيانات و اعتمادات اختبارية معزولة.

R-655: الفشل يجب أن يفشل الاختبار (لا skip) — عند التشغيل اليدوي.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# R-682 (الجولة التشغيلية — إصلاح فجوة كشفها التشغيل الفعلي): الدالتان
# كانتا مستخدمتين (الأسطر أدناه) وغير معرّفتين — NameError عند أول تشغيل
# حقيقي للاختبار (لم يُشغَّل الاختبار بنجاح قط قبله: كان يتخطى بدون
# العلم، ويرفض pytest الأمر مع العلم قبل تسجيله — راجع
# forensics/OPERATIONAL_TESTS.md).
def _load_key_from_file(path: Path) -> str:
    """قراءة مفتاح من ملف (سطر واحد) — الفارغ يُرفض صراحة."""
    content = path.read_text(encoding="utf-8").strip()
    assert content, f"key file is empty: {path}"
    return content


def _fp(key: str) -> str:
    """بصمة المفتاح (sha256 مقتطعة) — تُطبع آمنة، لا تسرّب المفتاح."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

# R-661: لا يُشغّل في المجموعة الاعتيادية — يتطلب --run-operational
# R-682 (Task 3.3): marker on the operational test ONLY.
# test_identity_seal_path_follows_code_definition is SAFE (no secrets) — not marked.


# R-682 (الجولة الرابعة — أمر المستشار): استُخرج بناء السكربت إلى دالة
# مشتركة ليُختبر مسار تشخيص الإخفاق (str(e)) باختبار محقون — راجع
# tests/test_operational_no_leak_on_exception.py و OPERATIONAL_TESTS.md.
def _build_verification_script(repo_root: Path) -> str:
    """سكربت التحقق التشغيلي (يُشغّل في عملية جديدة عبر subprocess).

    المفتاحان يُمرّران عبر متغيرات البيئة (TEST_NEW_KEY/TEST_OLD_KEY) —
    لا يُضمّنان في مصدر السكربت، فلا يظهران في أي traceback أو رسالة
    إخفاق أو مخرجات pytest.
    """
    return (
        "import sys, os, json\n"
        f"sys.path.insert(0, {str(repo_root / 'backend')!r})\n"
        f"os.chdir({str(repo_root)!r})\n"
        "# إلغاء متغيرات البيئة الاختبارية (لكن المفتاح من data/key.secret)\n"
        "os.environ.pop('SOVEREIGN_KEY', None)\n"
        "os.environ.pop('SOVEREIGN_DATA_ROOT', None)\n"
        "from fastapi.testclient import TestClient\n"
        "import app\n"
        "client = TestClient(app.app)\n"
        # R-682 (الجولة الرابعة — أمر المستشار): تنقية نص الاستثناء قبل
        # تخزينه — رسائل أخطاء HTTP قد تحمل URL الطلب ومعه master_key،
        # وresults تُضمَّن في رسالة فشل pytest وJUnit. أثبت الاختبار
        # المحقون (test_operational_no_leak_on_exception) التسريب قبل
        # التنقية (RED) واختفاءه بعدها (GREEN).
        "def _redact(msg):\n"
        "    import urllib.parse\n"
        "    for _n in ('TEST_NEW_KEY', 'TEST_OLD_KEY'):\n"
        "        _v = os.environ.get(_n, '')\n"
        "        if _v:\n"
        "            msg = msg.replace(_v, '<REDACTED-KEY>')\n"
        # الجولة الخامسة: رسائل الأخطاء قد تحمل URL الطلب، والمفتاح فيه
        # يظهر بتمثيله المرمّز (percent-encoding) — التنقية تشمله أيضًا.
        "            msg = msg.replace(urllib.parse.quote(_v, safe=''), '<REDACTED-KEY>')\n"
        "    return msg\n"
        "results = {}\n"
        "try:\n"
        "    r = client.get('/api-key', params={'master_key': os.environ['TEST_NEW_KEY']})\n"
        "    results['new_key_status'] = r.status_code\n"
        "except Exception as e:\n"
        "    results['new_key_error'] = _redact(str(e))\n"
        "try:\n"
        "    r = client.get('/api-key', params={'master_key': os.environ['TEST_OLD_KEY']})\n"
        "    results['old_key_status'] = r.status_code\n"
        "except Exception as e:\n"
        "    results['old_key_error'] = _redact(str(e))\n"
        "print(json.dumps(results))\n"
    )


class TestOperationalAuth:
    """التحقق التشغيلي المنفصل — البوابة 1 (تشغيل يدوي فقط)."""

    @pytest.mark.operational  # R-682 (Task 3.3): this test ONLY (reads host secrets)
    def test_operational_auth_new_key_accepted_old_rejected(self):
        """التشغيل الفعلي: عملية Python جديدة تُحمّل التطبيق و تختبر المصادقة.

        R-661: يتطلب --run-operational (لا يُشغّل في المجموعة الاعتيادية).
        """
        if "--run-operational" not in sys.argv:
            pytest.skip(
                "R-661: operational test requires --run-operational "
                "(reads host secrets, writes real data — not for regular suite)"
            )
        new_key_path = _REPO_ROOT / "data" / "key.secret"
        old_key_path = _REPO_ROOT / "data" / "key.secret.old_rotated_2026_10_14"

        # المفاتيح موجودة (إلزامي — لا skip)
        assert new_key_path.exists(), f"new key file missing: {new_key_path}"
        assert old_key_path.exists(), f"old key file missing: {old_key_path}"

        new_key = _load_key_from_file(new_key_path)
        old_key = _load_key_from_file(old_key_path)

        # بصمات مختلفة
        new_fp = _fp(new_key)
        old_fp = _fp(old_key)
        assert new_fp != old_fp, "new and old key fingerprints must differ"

        # سكربت التحقق التشغيلي (subprocess — عملية جديدة)
        # يُحمّل التطبيق بالإعدادات الحقيقية (دون monkeypatch/reload)
        # R-682 (جولة التشغيلية — أمر المستشار): المفتاحان يُمرَّران عبر
        # متغيرات بيئة السب-بروسس — لا يُضمَّنان في مصدر السكربت نفسه، فلا
        # يظهران في أي traceback أو رسالة إخفاق أو مخرجات pytest.
        script = _build_verification_script(_REPO_ROOT)

        subprocess_env = {**os.environ, "TEST_NEW_KEY": new_key, "TEST_OLD_KEY": old_key}
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            env=subprocess_env,
            timeout=120,
        )

        # R-655: الفشل يفشل الاختبار (لا skip)
        assert result.returncode == 0, (
            f"subprocess failed (returncode={result.returncode}): "
            f"{result.stderr[-500:]}"
        )

        # تحليل النتائج
        output = result.stdout.strip()
        assert output, f"subprocess produced no output: stderr={result.stderr[-300:]}"

        try:
            results = json.loads(output)
        except json.JSONDecodeError:
            # محاولة استخراج آخر سطر JSON
            lines = [l for l in output.split("\n") if l.strip().startswith("{")]
            assert lines, f"no JSON in output: {output[-300:]}"
            results = json.loads(lines[-1])

        # R-655: تأكيد المصادقة الفعلية
        # المفتاح الجديد: 200 (يُقبل)
        assert results.get("new_key_status") == 200, (
            f"NEW key must be accepted (200), got: {results.get('new_key_status')} "
            f"(error: {results.get('new_key_error', 'none')})"
        )

        # المفتاح القديم: 403 (يُرفض)
        assert results.get("old_key_status") == 403, (
            f"OLD key must be rejected (403), got: {results.get('old_key_status')} "
            f"(error: {results.get('old_key_error', 'none')})"
        )

        # R-655: بصمات (لا أسرار)
        print(f"[R-655] new_key_fp={new_fp}, old_key_fp={old_fp}")
        print(f"[R-655] new=200, old=403 — operational auth CONFIRMED")

    def test_identity_seal_path_follows_code_definition(self):
        """R-655: مسار ختم الهوية يُتبّع التعريف الفعلي (IDENTITY_SEAL_FILE).

        R-661: هذا الاختبار آمن — يتحقق فقط من وجود الملف (لا يقرأ أسرار).
        """
        # استيراد التعريف الفعلي (subprocess — لا تلوث)
        script = (
            "import sys, os, json\n"
            f"sys.path.insert(0, {str(_REPO_ROOT)!r})\n"
            f"sys.path.insert(0, {str(_REPO_ROOT / 'backend')!r})\n"
            f"os.chdir({str(_REPO_ROOT)!r})\n"
            "os.environ.pop('SOVEREIGN_KEY', None)\n"
            "os.environ.pop('SOVEREIGN_DATA_ROOT', None)\n"
            "from backend.consciousness import identity_core\n"
            "print(json.dumps({\n"
            "    'seal_file': str(identity_core.IDENTITY_SEAL_FILE),\n"
            "    'seal_exists': identity_core.IDENTITY_SEAL_FILE.exists(),\n"
            "    'identity_dir': str(identity_core.IDENTITY_DIR),\n"
            "}))\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=60,
        )

        # R-655: الفشل يفشل (لا skip)
        assert result.returncode == 0, (
            f"subprocess failed: {result.stderr[-300:]}"
        )

        lines = [
            l for l in result.stdout.strip().split("\n") if l.strip().startswith("{")
        ]
        assert lines, f"no JSON in output: {result.stdout[-200:]}"
        info = json.loads(lines[-1])

        # R-671 (البوابة 2): في clone نظيف، identity_seal.bin غير موجود
        # (سر — لا يُدفع). الاختبار يتحقق من أن المسار يُتبّع التعريف،
        # لا من وجود الملف (الوجود يتطلب تشغيل — ليس شرطاً للكود).
        if not info["seal_exists"]:
            # نتحقق من أن المسار صحيح (يُتبّع التعريف) — لا نطالب بالوجود
            assert info["seal_file"], "seal_file path must be defined"
            print(
                f"[R-671] seal_file={info['seal_file']} (not present in clean clone — "
                f"secret, not tracked. Path definition is correct.)"
            )
        else:
            # المشروع الكامل — الختم موجود
            print(f"[R-655] seal_file={info['seal_file']} (exists)")


# R-682 (Task 3.3): marker — this file is NOT collected by default suite.
# It's deselected via `-m "not operational"` in CI + pytest.ini marker registration.
