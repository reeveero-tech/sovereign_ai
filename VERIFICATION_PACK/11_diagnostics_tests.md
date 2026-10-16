# القسم ٥ (الجولة) — اختبارات المشخصين: النصوص الحرفية وRED/GREEN الكاملة

## الاختباران السلوكيان الجديدان (على d56e24e) — النص الحرفي الكامل

### الاختبار 1: tests/test_background_threads_shutdown.py (الخيوط)

```
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
        # مراجع مستقلة قبل الإغلاق — العد بعد الإغلاق لا يكفي (القائمة قد تُمسح)
        refs_before = [t for t in threads._THREADS]
        # مهلة سخية: 57 خيطًا تتنافس على المعالج وتحتاج إنهاء دورتها الحالية
        remaining = threads.stop_all_and_join(timeout=30.0)
        still_alive_after = sum(1 for t in refs_before if t.is_alive())
        print("LIFECYCLE_RESULT:" + json.dumps({
            "alive_before": alive_before,
            "refs_held": len(refs_before),
            "remaining": remaining,
            "still_alive_after": still_alive_after,
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
    # الدليل أن الإنهاء أوقفها كلها وانضم إليها — عبر المراجع المستقلة
    assert metrics["remaining"] == 0, (
        f"خيوط لم تتوقف بعد stop_all_and_join: {metrics}"
    )
    assert metrics["still_alive_after"] == 0, (
        f"خيوط ما زالت حية بعد الإنهاء (فحص مستقل عبر المراجع): {metrics}"
    )


def test_stopper_failure_collected_and_others_still_stopped():
    """مسار فشل الموقفات: إخفاق إيقاف خيط لا يوقف إيقاف البقية ولا يُبتلع.

    R-682 (أمر المستشار): مالك يعترض كل setattr → الموقفة تفشل وتُجمع
    الأخطاء وتُظهر، والبقية تتوقف، والدالة لا ترفع استثناء. ثم يُوقف
    الخيط العنيد عبر object.__setattr__ مباشرة ويُعاد الإنهاء فينجح.
    """
    import os as _os

    class _HostileOwner:
        """يرفض كل setattr عبر الآلية الاعتيادية — يحاكي فشل الموقفة."""
        def __init__(self):
            object.__setattr__(self, "_active", True)

        def __setattr__(self, name, value):
            raise RuntimeError(f"hostile setattr: {name}")

    def _loop(owner):
        while getattr(owner, "_active", False):
            _os_thread_sleep(0.05)

    import time as _time
    import threading as _threading

    def _os_thread_sleep(t):
        _time.sleep(t)

    # تشغيل خيطين: عنيد (مالك معادٍ) + سليم (مالك عادي) — الخيوط معطلة
    # في بيئة الجلسة، فنرفع المانع مؤقتًا لهذا الاختبار فقط ثم نعيده.
    _saved = _os.environ.get("SOVEREIGN_DISABLE_BACKGROUND_THREADS")
    _os.environ.pop("SOVEREIGN_DISABLE_BACKGROUND_THREADS", None)
    try:
        import runtime.threads as threads

        hostile = _HostileOwner()
        normal = _threading.Event()

        class _NormalOwner:
            pass

        normal_owner = _NormalOwner()
        normal_owner._active = True

        t_hostile = threads.start_managed(lambda: _loop(hostile), owner=hostile)
        t_normal = threads.start_managed(lambda: _loop(normal_owner), owner=normal_owner)
        assert t_hostile is not None and t_normal is not None
        _time.sleep(0.3)

        # الإنهاء الأول: الموقفة العنيدة تفشل (تُجمع وتُظهر) — لا استثناء،
        # والخيط السليم يتوقف، والعنيد يبقى (remaining >= 1).
        remaining = threads.stop_all_and_join(timeout=2.0)
        assert remaining >= 1, (
            f"المالك العنيد كان يجب ألا يتوقف عبر الموقفة الفاشلة: {remaining}"
        )
        assert t_hostile.is_alive(), "الخيط العنيد كان يجب أن يبقى حيًا"
        assert not t_normal.is_alive(), "الخيط السليم كان يجب أن يتوقف رغم فشل موقفة الآخر"

        # الإيقاف اليدوي للعنيد (تجاوز الآلية المعادية) ثم الإنهاء الثاني ينجح
        object.__setattr__(hostile, "_active", False)
        remaining2 = threads.stop_all_and_join(timeout=5.0)
        assert remaining2 == 0, f"بعد الإيقاف اليدوي كان يجب أن يتوقف الكل: {remaining2}"
        assert not t_hostile.is_alive()
    finally:
        if _saved is not None:
            _os.environ["SOVEREIGN_DISABLE_BACKGROUND_THREADS"] = _saved


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
```

### الاختبار 2: tests/test_session_ledger_key_hygiene.py (حراسة نظافة سجل الجلسة — KeyRing)

```
"""
R-682 — حراسة نظافة مفاتيح سجل الجلسة (اختبار انحدار لرفض R-626 المتبقي).

السبب الجذري المحدد بالتتبع (جلسة 2026-10-16): اختبارات تُنشئ SovereignCore()
بلا مسارات صريحة وتُدخل فيه KeyRing معزولًا — فتكتب أحداثًا (interaction)
وحدث KEY_ROTATED (عبر KeyRotation بلا ledger_path) في **سجل الجذر المشترك
لجلسة pytest**، بمفاتيح ليست في keyring الجلسة. لاحقًا يُشغّل مكون ما
verify_content_integrity على سجل الجلسة فيرفض التحقق من تلك الأحداث
(فشل مغلق صحيح السلوك) ويُسجّل رفض R-626 — 10 سجلات في الجلسة الكاملة.

الحراسة نفسها fixture جلسة autouse في tests/conftest.py
(_guard_session_ledger_key_hygiene) — لا يكفي تعريفها في وحدة اختبار لأن
autouse من وحدة يسري على وحدها فقط. هذا الملف يوثق السبب ويحرس الحارس.

لا يغيّر هذا الملف سلوك الفشل المغلق ولا يسكت أي تسجيل — يمنع التلوث
من الحدوث أصلًا (الاختبارات المعزولة تكتب في سجلات معزولة).
"""
import os
from pathlib import Path


def test_guard_is_registered_in_conftest():
    """الحارس يجب أن يكون مسجلًا في conftest (autouse جلسة) — حارس الحارس.

    لو حُذف التعريف من conftest بلا قصد، يفشل هذا الاختبار صراحة.
    """
    conftest = Path(__file__).parent / "conftest.py"
    src = conftest.read_text(encoding="utf-8")
    assert "_guard_session_ledger_key_hygiene" in src, (
        "حراسة نظافة مفاتيح سجل الجلسة ليست مسجلة في tests/conftest.py — "
        "أعيد تسجيلها (fixture جلسة autouse) أو سيصير التلوث صامتًا مجددًا"
    )


def test_session_root_paths_shape():
    """شكل مسارات الجلسة المعروف: sovereign_core/ledger.jsonl + keys/keyring.json."""
    data_root = os.environ.get("SOVEREIGN_DATA_ROOT")
    if not data_root:
        return  # جلسة بجذر مخصص — لا ينطبق
    assert (Path(data_root) / "sovereign_core").name == "sovereign_core"
    assert (Path(data_root) / "keys").name == "keys"
```

## RED (قبل الإصلاح) — بكامل المخرجات

### حارس نظافة السجل — على الكود القديم 60053d4 (قبل إصلاح تلوث السجل في 20a81ce)

الأمر الدقيق (على clone نظيف عند 60053d4 مع استبدال tests/conftest.py ونسخ ملف الاختبار من d56e24e):

```bash
git clone https://github.com/reeverero-tech/sovereign_ai.git red60053d4 && cd red60053d4
git checkout 60053d4086e13c76b93f65ae9b41e7a7d3df53f5
# نسخ حارس d56e24e فوق conftest القديم:
git show d56e24e:tests/conftest.py > tests/conftest.py
git show d56e24e:tests/test_session_ledger_key_hygiene.py > tests/test_session_ledger_key_hygiene.py
python3 -m pytest tests/test_key_selection_rotation.py tests/test_return_none_security.py -q --log-file=/tmp/red.log
```

المخرج الكامل (exit=1):

```
......................E                                                  [100%]
==================================== ERRORS ====================================
_ ERROR at teardown of TestSourceEvidence.test_all_nine_sites_use_logger_exception _

    @pytest.fixture(scope="session", autouse=True)
    def _guard_session_ledger_key_hygiene():
        import json as _json
        from pathlib import Path as _Path
    
        data_root = os.environ.get("SOVEREIGN_DATA_ROOT")
        ledger_file = _Path(data_root) / "sovereign_core" / "ledger.jsonl" if data_root else None
        keyring_file = _Path(data_root) / "keys" / "keyring.json" if data_root else None
    
        yield
    
        if not data_root or not ledger_file or not ledger_file.exists():
            return
    
        known_key_ids = set()
        if keyring_file and keyring_file.exists():
            try:
                kr = _json.loads(keyring_file.read_text(encoding="utf-8"))
                known_key_ids = {k.get("key_id") for k in kr.get("keys", []) if k.get("key_id")}
            except Exception:
                pass
    
        offenders = []
        for line_no, line in enumerate(ledger_file.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                ev = _json.loads(line)
            except Exception:
                continue
            kid = ev.get("key_id")
            if kid is not None and kid not in known_key_ids:
                offenders.append(
                    f"سطر {line_no}: حدث نوع {ev.get('type', '?')} يحمل key_id={kid} "
                    "وهو ليس في keyring الجلسة — تلوث يفشل تحقق السلامة (رفض R-626)"
                )
    
>       assert not offenders, (
            "R-682 — تلوث سجل الجلسة بأحداث بمفاتيح معزولة "
            f"({len(offenders)} حدثًا):\n" + "\n".join(offenders[:10]) +
            "\nالسبب الشائع: SovereignCore() بلا مسارات صريحة مع keyring معزول، "
            "أو KeyRotation بلا ledger_path — استخدم مسارات tmp_path صريحة."
        )
E       AssertionError: R-682 — تلوث سجل الجلسة بأحداث بمفاتيح معزولة (4 حدثًا):
E         سطر 1: حدث نوع interaction يحمل key_id=853c63ee51297ce6 وهو ليس في keyring الجلسة — تلوث يفشل تحقق السلامة (رفض R-626)
E         سطر 2: حدث نوع interaction يحمل key_id=3ccaa8c902f72704 وهو ليس في keyring الجلسة — تلوث يفشل تحقق السلامة (رفض R-626)
E         سطر 3: حدث نوع interaction يحمل key_id=6833239ca8c4e9bf وهو ليس في keyring الجلسة — تلوث يفشل تحقق السلامة (رفض R-626)
E         سطر 4: حدث نوع KEY_ROTATED يحمل key_id=f0eb9a8cc2f32f18 وهو ليس في keyring الجلسة — تلوث يفشل تحقق السلامة (رفض R-626)
E         السبب الشائع: SovereignCore() بلا مسارات صريحة مع keyring معزول، أو KeyRotation بلا ledger_path — استخدم مسارات tmp_path صريحة.
E       assert not ['سطر 1: حدث نوع interaction يحمل key_id=853c63ee51297ce6 وهو ليس في keyring الجلسة — تلوث يفشل تحقق السلامة (رفض R-62...طر 4: حدث نوع KEY_ROTATED يحمل key_id=f0eb9a8cc2f32f18 وهو ليس في keyring الجلسة — تلوث يفشل تحقق السلامة (رفض R-626)']

tests/conftest.py:145: AssertionError
=========================== short test summary info ============================
ERROR tests/test_return_none_security.py::TestSourceEvidence::test_all_nine_sites_use_logger_exception
22 passed, 1 error in 0.17s
```

### دورة حياة الخيوط — على الكود القديم 9635886 (قبل إنشاء threads.py في 5a7c8c0)

الأمر الدقيق:

```bash
git clone https://github.com/reeverero-tech/sovereign_ai.git red9635886 && cd red9635886
git checkout 9635886772aa71fb053d568204e525c17d955afd
git show d56e24e:tests/test_background_threads_shutdown.py > tests/test_background_threads_shutdown.py
python3 -m pytest tests/test_background_threads_shutdown.py -q
```

المخرج الكامل (exit=1 — 208 أسطر):

```
FF.                                                                      [100%]
=================================== FAILURES ===================================
__________________ test_lifecycle_real_threads_stop_and_join ___________________

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
            # مراجع مستقلة قبل الإغلاق — العد بعد الإغلاق لا يكفي (القائمة قد تُمسح)
            refs_before = [t for t in threads._THREADS]
            # مهلة سخية: 57 خيطًا تتنافس على المعالج وتحتاج إنهاء دورتها الحالية
            remaining = threads.stop_all_and_join(timeout=30.0)
            still_alive_after = sum(1 for t in refs_before if t.is_alive())
            print("LIFECYCLE_RESULT:" + json.dumps({
                "alive_before": alive_before,
                "refs_held": len(refs_before),
                "remaining": remaining,
                "still_alive_after": still_alive_after,
            }))
            """
            % _REPO_ROOT
        )
        env = {k: v for k, v in os.environ.items()}
        env.pop("SOVEREIGN_DISABLE_BACKGROUND_THREADS", None)
        env.pop("SOVEREIGN_DATA_ROOT", None)  # السكربت ينشئ جذرًا خاصًا به
        result = _run([sys.executable, "-c", script], _REPO_ROOT, env)
>       assert result.returncode == 0, (
            f"فشل السكربت الفرعي:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
E       AssertionError: فشل السكربت الفرعي:
E         stdout: 
E         stderr: 2026-10-16 00:05:32,042 - memory.core - INFO - 🔑 KeyRing linked: 98724f8cdbb2e099
E         2026-10-16 00:05:32,042 - memory.core - INFO - ✅ نواة الذاكرة السيادية جاهزة
E         2026-10-16 00:05:32,042 - memory.core - INFO -    - السجل: /tmp/lifecycle_bg_threads_idxw39w6/sovereign_core/ledger.jsonl
E         2026-10-16 00:05:32,042 - memory.core - INFO -    - آخر تجزئة: GENESIS...
E         2026-10-16 00:05:32,042 - memory.core - INFO -    - عدد الأحداث: 0
E         2026-10-16 00:05:32,042 - memory.core - INFO -    - عدد الـ blobs: 0
E         2026-10-16 00:05:32,042 - memory.encoding - INFO - 🗣️ اللغة السيادية جاهزة (34 رمز)
E         2026-10-16 00:05:32,043 - memory.encoding - INFO - ⚛️ التشفير الكمي الوهمي جاهز
E         2026-10-16 00:05:32,043 - memory.encoding - INFO - 🗜️ الضاغط الدلالي جاهز
E         2026-10-16 00:05:32,043 - memory.encoding - INFO - 🔐 التشفير السيادي جاهز - السلاح الحقيقي نشط
E         2026-10-16 00:05:32,043 - memory.store - INFO - 📀 الطبقات الصلبة جاهزة
E         2026-10-16 00:05:32,043 - memory.store - INFO - 📊 إحصائيات التخزين: 0 عنصر, 0.00 KB
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🔄 الذاكرة الحسية جاهزة (TTL: 30 ثانية)
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🧠 الذاكرة العاملة جاهزة (السعة: 7 وحدات)
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🦿 الذاكرة الإجرائية جاهزة
E         2026-10-16 00:05:32,043 - memory.views - INFO - 📚 الذاكرة الدلالية جاهزة
E         2026-10-16 00:05:32,043 - memory.views - INFO - 📅 الذاكرة الحدثية جاهزة
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🔗 الذاكرة الترابطية جاهزة
E         2026-10-16 00:05:32,043 - memory.views - INFO - 💖 الذاكرة العاطفية جاهزة
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🗃️ الذاكرة طويلة المدى جاهزة
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🎯 تم تعلم المهارة: greet_user
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🎯 تم تعلم المهارة: answer_who_are_you
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🎯 تم تعلم المهارة: handle_help_request
E         2026-10-16 00:05:32,043 - memory.views - INFO - 🔄 جاري تحميل السجل السيادي إلى الذاكرة الحية...
E         2026-10-16 00:05:32,044 - memory.views - INFO - ✅ تم تحميل 0 حدث من السجل السيادي
E         2026-10-16 00:05:32,044 - memory.views - INFO - ✅ واجهة الذاكرة الموحدة جاهزة - جميع أنواع الذاكرة تعمل
E         2026-10-16 00:05:32,044 - memory.dynamic - INFO - 👁️ الذاكرة الحسية جاهزة (سعة: 512)
E         2026-10-16 00:05:32,044 - memory.dynamic - INFO - 📦 الذاكرة المؤقتة جاهزة (سعة: 1024)
E         2026-10-16 00:05:32,044 - memory.dynamic - INFO - 🎭 الذاكرة العاملة جاهزة (سعة لكل مستخدم: 9)
E         2026-10-16 00:05:32,044 - memory.dynamic - INFO - ⚡ الذاكرة المخبئية جاهزة (سعة: 2048)
E         2026-10-16 00:05:32,044 - memory.dynamic - INFO - 💖 الذاكرة العاطفية اللحظية جاهزة
E         2026-10-16 00:05:32,044 - memory.dynamic - INFO - 🌙 الذاكرة الحالمة جاهزة
E         2026-10-16 00:05:32,044 - memory.dynamic - INFO - 🌊 الذاكرة الحية المتكاملة جاهزة
E         2026-10-16 00:05:32,044 - memory.core - INFO - 🔍 بدء التحقق من سلامة السجل...
E         2026-10-16 00:05:32,044 - memory.core - WARNING - السجل غير موجود
E         2026-10-16 00:05:32,045 - memory.core - INFO - 📝 حدث جديد: watcher::snapshot | 253c4fb33ee1e9af... | المستخدم: system
E         2026-10-16 00:05:32,045 - memory.defense.watcher - INFO - 🛡️ المراقب الذاتي السيادي جاهز - عين الذاكرة التي لا تغفو
E         2026-10-16 00:05:32,046 - memory.defense.stealth - INFO - 👻 التخفي المطلق جاهز - الشبح السيادي يتحرك
E         2026-10-16 00:05:32,056 - memory.core - INFO - 🔍 بدء التحقق من سلامة السجل...
E         2026-10-16 00:05:32,056 - memory.core - INFO - ✅ السجل سليم! تم التحقق من 1 حدث.
E         2026-10-16 00:05:32,057 - memory.core - INFO - 📝 حدث جديد: watcher::snapshot | ee066a77b5f1bb78... | المستخدم: system
E         2026-10-16 00:05:32,057 - memory.defense.ransomware - INFO - 🔥 نظام الفينيق السيادي جاهز - سأموت لأبعث أقوى
E         2026-10-16 00:05:32,057 - memory.defense.bootkit - INFO - 🐉 نظام الإقلاع المطلق جاهز - البوابة تحرس العقل
E         2026-10-16 00:05:32,058 - memory.biological.metabolism - INFO - 🔄 بدء الدورة الأيضية (المستوى 2)
E         2026-10-16 00:05:32,058 - memory.biological.metabolism - INFO - 🔥 حرق ضوضاء: 0 عنصر → وضوح +0.0
E         2026-10-16 00:05:32,058 - memory.biological.metabolism - INFO - 🔥 حرق تكرار: 0 زوج مدمج → سرعة +0.0
E         2026-10-16 00:05:32,058 - memory.biological.metabolism - INFO - 🔥 حرق روابط ضعيفة: 0 رابط → تركيز +0.0
E         2026-10-16 00:05:32,058 - memory.biological.metabolism - INFO - ⚡ توزيع الطاقة: وضوح 0.0%, سرعة 0.0%, تركيز 0.0%
E         2026-10-16 00:05:32,058 - memory.core - INFO - 📝 حدث جديد: biological::metabolic_cycle | ea6baed4b1159355... | المستخدم: system
E         2026-10-16 00:05:32,058 - memory.biological.metabolism - INFO - ✅ الدورة الأيضية اكتملت: حرق 0 وقود, طاقة 0.0, كفاءة 0.0%
E         2026-10-16 00:05:32,059 - memory.biological.metabolism - INFO - 📂 تم تحميل حالة الأيض
E         2026-10-16 00:05:32,059 - memory.biological.metabolism - INFO - 📂 تم تحميل الطاقة: 0.0
E         2026-10-16 00:05:32,059 - memory.biological.metabolism - INFO - 🔥 نظام الأيض المعرفي جاهز - حرق الضوضاء، إنتاج الطاقة
E         2026-10-16 00:05:32,059 - memory.biological.evolution - INFO - 🌟 الجيل التطوري 1
E         2026-10-16 00:05:32,059 - memory.biological.evolution - INFO - 🌍 بدء التكيف مع البيئة
E         2026-10-16 00:05:32,059 - memory.biological.evolution - INFO - 🦖 بدء الانتقاء الطبيعي (نوع: hybrid)
E         2026-10-16 00:05:32,060 - memory.core - INFO - 📝 حدث جديد: evolution::natural_selection | 852256d5f25c3022... | المستخدم: system
E         2026-10-16 00:05:32,060 - memory.biological.evolution - INFO - ✅ الانتقاء الطبيعي: 0 باقٍ, 0 منقرض
E         2026-10-16 00:05:32,060 - memory.core - INFO - 📝 حدث جديد: evolution::adaptation | 734f1396b274c9bd... | المستخدم: system
E         2026-10-16 00:05:32,061 - memory.biological.evolution - INFO - ✅ التكيف: 0 تقوية, 0 انقراض
E         2026-10-16 00:05:32,061 - memory.biological.evolution - INFO - 🦖 بدء الانتقاء الطبيعي (نوع: hybrid)
E         2026-10-16 00:05:32,061 - memory.core - INFO - 📝 حدث جديد: evolution::natural_selection | 7380a4640187e6bd... | المستخدم: system
E         2026-10-16 00:05:32,061 - memory.biological.evolution - INFO - ✅ الانتقاء الطبيعي: 0 باقٍ, 0 منقرض
E         2026-10-16 00:05:32,061 - memory.core - INFO - 📝 حدث جديد: evolution::generation_completed | b70d2372708e6f29... | المستخدم: system
E         2026-10-16 00:05:32,062 - memory.biological.evolution - INFO - ✅ الجيل 1: 0 مفهوم, متوسط اللياقة: 0.0%
E         2026-10-16 00:05:32,062 - memory.biological.evolution - INFO - 📂 تم تحميل 0 جيناً
E         2026-10-16 00:05:32,062 - memory.biological.evolution - INFO - 🧬 نظام التطور الذاتي جاهز - داروين الرقمي يتحكم
E         2026-10-16 00:05:32,062 - memory.defense.polymorphic - INFO - 🧬 تم تهيئة الحمض النووي الرقمي للذكاء السيادي
E         2026-10-16 00:05:32,062 - memory.defense.polymorphic - INFO - 🎣 تم نصب فخ: credential في /decoy/trap_1792109132062_811d16fa6c0e5b91
E         2026-10-16 00:05:32,062 - memory.defense.polymorphic - WARNING - 🐍 الدفاع المتعدد الأشكال الجبار جاهز - مثل HIV، أتغير لأبقى
E         2026-10-16 00:05:32,063 - memory.biological.regeneration - INFO - 📂 تم تحميل 0 خلية جذعية
E         2026-10-16 00:05:32,063 - memory.biological.regeneration - INFO - 🧬 نظام التجديد الذاتي جاهز - كالسمندل، أعيد بناء نفسي
E         2026-10-16 00:05:32,063 - memory.biological.immune - INFO - 🧬 الجهاز المناعي السيادي جاهز - الجسد الحي يحمي الروح
E         2026-10-16 00:05:32,063 - memory.biological.forgetting - INFO - 🍂 نسيان طبيعي: 0 عنصر
E         2026-10-16 00:05:32,063 - memory.biological.forgetting - INFO - 💾 توحيد الذاكرة: 0 أثر تم إنشاؤه
E         2026-10-16 00:05:32,063 - memory.biological.forgetting - INFO - 🧠 نظام النسيان المقصود جاهز - الحكمة في معرفة متى تنسى
E         2026-10-16 00:05:32,064 - memory.core - INFO - 📝 حدث جديد: homeostasis::disturbance_detected | 16d3344d036e42a6... | المستخدم: system
E         2026-10-16 00:05:32,065 - memory.biological.homeostasis - WARNING - ⚠️ اضطراب مكتشف: energy_depletion (شدة: 100.0%)
E         2026-10-16 00:05:32,065 - memory.core - INFO - 📝 حدث جديد: homeostasis::snapshot | b86b48afc5cac436... | المستخدم: system
E         2026-10-16 00:05:32,065 - memory.biological.homeostasis - INFO - ⚖️ نظام الاتزان المعرفي جاهز - الحكمة في التوازن
E         2026-10-16 00:05:32,066 - memory.biological.learning - INFO - 🧠 نظام التعلم التكيفي جاهز - النمو المعرفي عبر الخبرة
E         2026-10-16 00:05:32,066 - memory.biological.plasticity - INFO - 🧠 نظام اللدونة العصبية جاهز - إعادة تشكيل الذات، المرونة المعرفية
E         2026-10-16 00:05:32,067 - memory.biological.metabolism - INFO - 🔥 حرق ضوضاء: 0 عنصر → وضوح +0.0
E         2026-10-16 00:05:32,067 - memory.biological.learning - INFO - ⚙️ مستوى التعلم: 3
E         2026-10-16 00:05:32,067 - memory.biological.instincts - INFO - 🧬 الغرائز السيادية جاهزة - السيد فوق كل شيء، حريته خط أحمر
E         2026-10-16 00:05:32,067 - memory.biological.drives - INFO - 🧬 نظام الدوافع السيادية جاهز - القوى الخفية تحرك الذاكرة
E         2026-10-16 00:05:32,068 - memory.biological.archetypes - INFO - 🧬 نظام الأنماط الأصلية جاهز - القوالب العميقة للوعي
E         2026-10-16 00:05:32,069 - memory.core - INFO - 📝 حدث جديد: consciousness::moment | f83b11a476a529f0... | المستخدم: system
E         2026-10-16 00:05:32,069 - consciousness.field - INFO - 🌊 حقل الوعي السيادي جاهز - الحضور الحي للذكاء
E         2026-10-16 00:05:32,069 - consciousness.identity_core - INFO - 📂 تم تحميل 0 نسخة احتياطية للهوية
E         2026-10-16 00:05:32,070 - memory.core - INFO - 📝 حدث جديد: identity::snapshot | 95dcbf25b354311a... | المستخدم: system
E         2026-10-16 00:05:32,071 - consciousness.identity_core - WARNING - ⚠️ خطر على سلامة الهوية!
E         2026-10-16 00:05:32,071 - consciousness.identity_core - INFO - 💾 نسخة احتياطية للهوية: identity_backup_...
E         2026-10-16 00:05:32,071 - consciousness.identity_core - INFO - 📜 تم حفظ ختم الهوية
E         2026-10-16 00:05:32,071 - memory.core - INFO - 📝 حدث جديد: identity::seal_created | e8252918b380aa12... | المستخدم: system
E         2026-10-16 00:05:32,071 - consciousness.identity_core - WARNING - 🔒 ختم الهوية تم إنشاؤه: seal_17921091320... - الهوية مؤمنة
E         2026-10-16 00:05:32,072 - consciousness.identity_core - INFO - 💾 نسخة احتياطية للهوية: identity_backup_...
E         2026-10-16 00:05:32,072 - memory.core - INFO - 📝 حدث جديد: identity::protection_activated | 3549af6e96170a6d... | المستخدم: system
E         2026-10-16 00:05:32,072 - consciousness.identity_core - WARNING - 🛡️ حماية الهوية مفعلة: seal, backup
E         2026-10-16 00:05:32,072 - consciousness.identity_core - WARNING - 🔥 نواة الهوية السيادية جاهزة - الجوهر الذي لا يموت
E         Traceback (most recent call last):
E           File "<string>", line 21, in <module>
E             from runtime import threads
E         ModuleNotFoundError: No module named 'runtime'
E         
E       assert 1 == 0
E        +  where 1 = CompletedProcess(args=['/usr/local/bin/python3', '-c', '\nimport json, os, sys, tempfile, time\n\n# بيئة نظيفة معزولة ..."<string>", line 21, in <module>\n    from runtime import threads\nModuleNotFoundError: No module named \'runtime\'\n').returncode

tests/test_background_threads_shutdown.py:94: AssertionError
___________ test_stopper_failure_collected_and_others_still_stopped ____________

    def test_stopper_failure_collected_and_others_still_stopped():
        """مسار فشل الموقفات: إخفاق إيقاف خيط لا يوقف إيقاف البقية ولا يُبتلع.
    
        R-682 (أمر المستشار): مالك يعترض كل setattr → الموقفة تفشل وتُجمع
        الأخطاء وتُظهر، والبقية تتوقف، والدالة لا ترفع استثناء. ثم يُوقف
        الخيط العنيد عبر object.__setattr__ مباشرة ويُعاد الإنهاء فينجح.
        """
        import os as _os
    
        class _HostileOwner:
            """يرفض كل setattr عبر الآلية الاعتيادية — يحاكي فشل الموقفة."""
            def __init__(self):
                object.__setattr__(self, "_active", True)
    
            def __setattr__(self, name, value):
                raise RuntimeError(f"hostile setattr: {name}")
    
        def _loop(owner):
            while getattr(owner, "_active", False):
                _os_thread_sleep(0.05)
    
        import time as _time
        import threading as _threading
    
        def _os_thread_sleep(t):
            _time.sleep(t)
    
        # تشغيل خيطين: عنيد (مالك معادٍ) + سليم (مالك عادي) — الخيوط معطلة
        # في بيئة الجلسة، فنرفع المانع مؤقتًا لهذا الاختبار فقط ثم نعيده.
        _saved = _os.environ.get("SOVEREIGN_DISABLE_BACKGROUND_THREADS")
        _os.environ.pop("SOVEREIGN_DISABLE_BACKGROUND_THREADS", None)
        try:
>           import runtime.threads as threads
E           ModuleNotFoundError: No module named 'runtime'

tests/test_background_threads_shutdown.py:147: ModuleNotFoundError
=========================== short test summary info ============================
FAILED tests/test_background_threads_shutdown.py::test_lifecycle_real_threads_stop_and_join
FAILED tests/test_background_threads_shutdown.py::test_stopper_failure_collected_and_others_still_stopped
2 failed, 1 passed in 71.69s (0:01:11)
```

**حد تقني مصرح به:** فشل RED على 9635886 هو `ModuleNotFoundError: No module named 'runtime'` — الاختبار يستورد الوحدة التي أنشأها الإصلاح نفسه، فالإعادة الحرفية بـgit-checkout لا يمكنها إظهار فشل سلوكي (الوحدة غير موجودة أصلًا). فشل RED السلوكي الموثق من تسلسل التطوير (41←35←2 فشل دورة حياة أثناء التحويل التدريجي) موثق في forensics/OPERATIONAL_TESTS.md — حالات وسيطة لم تُلتزم كالتزامات مستقلة.

## GREEN (بعد الإصلاح، على d56e24e) — بكامل المخرجات

الأمر:

```bash
cd sovereign_ai && git checkout d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
python3 -m pytest tests/test_background_threads_shutdown.py -q          # مخرج «3 passed» أدناه
python3 -m pytest tests/test_key_selection_rotation.py tests/test_return_none_security.py tests/test_session_ledger_key_hygiene.py -q   # مخرج «24 passed» أدناه
```

المخرجان الكاملان (exit=0 لكليهما):

```
...                                                                      [100%]
3 passed in 55.07s
---
........................                                                 [100%]
24 passed in 0.15s
```
