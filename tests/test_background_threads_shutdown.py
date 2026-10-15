"""
R-682 (بنود ٥ و٦) — اختبارات سلوكية لإنهاء خيوط الخلفية.

الدليل الأول (RED قبل الإصلاح):
- جلسة كاملة (2026-10-16، 410 اختبارات، السجل الخام --log-file):
  244 سطر رفض توقيع R-626 في memory.core بمفتاح واحد معزول، وخطأ
  «--- Logging error ---» بعد نهاية الجلسة (خيط identity_core يكتب
  في ملف سجل مغلق) — راجع forensics/keyring_rejection_count.json
  وforensics/OPERATIONAL_TESTS.md.
- جلسة فرعية (tests/test_health.py فقط): 3 أخطاء «Logging error»
  بعد الملخص.

هذان الاختباران يثبتان GREEN بعد الإصلاح:
1) test_lifecycle_real_threads_stop_and_join — يشغّل خيوطًا فعلية
   (الخيوط مفعّلة — متغير التعطيل محذوف من بيئة العملية الفرعية)
   ويثبت أن stop_all_and_join توقفها وتنضم إليها (صفر خيوط متبقية).
   نجاح اختبار لأن الخيوط لم تبدأ أصلًا لا يثبت شيئًا — لذلك
   نتحقق أولًا أن الخيوط بدأت فعلًا (alive_before >= 1).
2) test_clean_session_no_logging_error_and_no_keyring_rejection —
   يشغّل جلسة pytest فرعية نظيفة ويثبت: لا «--- Logging error ---»
   في المخرجات، وصفر سطر رفض R-626 في السجل الكامل.
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(cmd, cwd, env):
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_lifecycle_real_threads_stop_and_join():
    """دورة حياة فعلية: خيوط تبدأ، ثم stop_all_and_join توقفها وتنضم إليها.

    تُشغَّل في عملية فرعية مع حذف متغير التعطيل كي تبدأ الخيوط فعلًا —
    بيئة مشابهة للإنتاج (المتغير غير مضبوط هناك).
    """
    script = textwrap.dedent(
        """
        import json, os, sys, tempfile, time

        # بيئة نظيفة معزولة — كالمُعدة في tests/conftest.py
        os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"
        data_root = tempfile.mkdtemp(prefix="lifecycle_bg_threads_")
        os.environ["SOVEREIGN_DATA_ROOT"] = data_root
        sys.path.insert(0, os.path.join(%r, "backend"))

        keys_dir = os.path.join(data_root, "keys")
        os.makedirs(keys_dir, exist_ok=True)
        from sovereign.keys import KeyRing
        kr = KeyRing(keys_dir=keys_dir)
        kr.generate_new_key(reason="lifecycle_r682")
        kr.save_to_disk()

        # إطلاق مكون حقيقي بخيوطه (IdentityCore — المصدر في الدليل الأول)
        from consciousness.identity_core import get_identity_core
        get_identity_core()

        from runtime import threads
        time.sleep(1.5)  # إعطاء الخيوط وقتًا لتعمل فعلًا
        alive_before = threads.active_count()
        # مهلة سخية: 57 خيطًا تتنافس على المعالج وتحتاج إنهاء دورتها الحالية
        remaining = threads.stop_all_and_join(timeout=30.0)
        alive_after = threads.active_count()
        print("LIFECYCLE_RESULT:" + json.dumps({
            "alive_before": alive_before,
            "remaining": remaining,
            "alive_after": alive_after,
        }))
        """
        % _REPO_ROOT
    )
    env = {k: v for k, v in os.environ.items()}
    env.pop("SOVEREIGN_DISABLE_BACKGROUND_THREADS", None)
    env.pop("SOVEREIGN_DATA_ROOT", None)  # السكربت ينشئ جذرًا خاصًا به
    result = _run([sys.executable, "-c", script], _REPO_ROOT, env)
    assert result.returncode == 0, (
        f"فشل السكربت الفرعي:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    line = [l for l in result.stdout.splitlines() if l.startswith("LIFECYCLE_RESULT:")]
    assert line, f"لم يُطبع سطر النتيجة:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    metrics = json.loads(line[0].split(":", 1)[1])

    # الدليل أن الخيوط بدأت فعلًا — وإلا فالاختبار نجاح زائف
    assert metrics["alive_before"] >= 1, (
        "لم تبدأ أي خيوط خلفية في العملية الفرعية — الاختبار لا يثبت شيئًا: "
        f"{metrics}"
    )
    # الدليل أن الإنهاء أوقفها كلها وانضم إليها
    assert metrics["remaining"] == 0, (
        f"خيوط لم تتوقف بعد stop_all_and_join: {metrics}"
    )
    assert metrics["alive_after"] == 0


def test_clean_session_no_logging_error_and_no_keyring_rejection(tmp_path):
    """جلسة اختبار نظيفة: لا «--- Logging error ---» بعد الملخص، وصفر رفض R-626.

    الجلسة الفرعية تشغّل tests/test_health.py وtests/test_loyalty_engine.py
    (المجموعة التي أظهرت الخطأ قبل الإصلاح — راجع OPERATIONAL_TESTS.md)
    مع التقاط السجل الكامل عبر --log-file.
    """
    log_file = tmp_path / "session_logs.txt"
    env = dict(os.environ)
    env["SOVEREIGN_DISABLE_BACKGROUND_THREADS"] = "1"  # كما تضبطه conftest
    env.pop("SOVEREIGN_DATA_ROOT", None)  # الجلسة الفرعية تنشئ جذرها المعزول
    result = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_health.py",
            "tests/test_loyalty_engine.py",
            "-q",
            f"--log-file={log_file}",
            "--log-file-level=INFO",
        ],
        _REPO_ROOT,
        env,
    )
    combined = result.stdout + result.stderr

    # الجلسة نفسها ناجحة
    assert result.returncode == 0, f"فشلت الجلسة الفرعية:\n{combined[-2000:]}"
    assert " failed" not in combined, f"اختبارات فاشلة في الجلسة الفرعية:\n{combined[-2000:]}"

    # البند ٥: لا رسالة «--- Logging error ---» بعد نهاية الجلسة
    assert "--- Logging error ---" not in combined, (
        "ظهرت رسالة «--- Logging error ---» بعد انتهاء الجلسة — "
        "خيط خلفي ما زال يكتب في ملف سجل مغلق"
    )

    # البند ٦: صفر سطر رفض توقيع R-626 في السجل الكامل
    rejection_lines = 0
    if log_file.exists():
        content = log_file.read_text(encoding="utf-8", errors="replace")
        rejection_lines = content.count("R-626")
    assert rejection_lines == 0, (
        f"رفض توقيع R-626 في جلسة نظيفة: {rejection_lines} سطر — "
        "خيط خلفي يوقّع بمفتاح غير موجود"
    )
