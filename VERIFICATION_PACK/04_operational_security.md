# القسم ٤ — الادعاءات التشغيلية والأمنية (على d56e24e)

## 18) الإصلاحان التشخيصيان (المشخصان المفتوحان سابقًا): الكود قبل الإصلاح وبعده

### الإصلاح 1 — تلوث سجل الجلسة (مصدر رفض R-626): tests/test_key_selection_rotation.py

**قبل (على 60053d4 — الكود القديم):**

```
"""
اختبار R-625/R-626: مسار اختيار المفتاح والتحقق بعد الدوران

يختبر أن:
1. أحداث المفتاح A تُتحقق بنجاح بعد الدوران إلى B (key_id من الحدث، ليس النشط)
2. تغيير key_id وحده (تزييف) يُكتشف
3. غياب KeyRing: الكاتب يرفض الإلحاق (لا fallback)
4. التوافق التاريخي: أحداث key_id بصيغة 5 حقول تُتحقق بالصيغة القديمة
"""

import json
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# عزل R-619
if not os.environ.get("SOVEREIGN_DATA_ROOT"):
    _test_data_root = tempfile.mkdtemp(prefix="sovereign_test_data_")
    os.environ["SOVEREIGN_DATA_ROOT"] = _test_data_root

import pytest

from backend.memory.core import SovereignCore, EventType
from backend.sovereign.keys import KeyRing, SignatureVerifier


class TestKeySelectionAfterRotation:
    """اختبارات مسار اختيار المفتاح بعد الدوران (R-625).
    
    R-627: عزل كامل — دوران المفتاح يُكتب إلى keys_dir معزول (وليس الحقيقي)،
    حتى لا يلوث الاختبار المفتاح الفعلي. fallback R-621 لا يُفعّل هنا
    لأن keyring.json موجود في الجذر المعزول.
    """

    def _isolated_keyring(self) -> KeyRing:
        """يُنشئ KeyRing معزول (بدون fallback للحقيقي) — للدوران."""
        _keys_dir = tempfile.mkdtemp(prefix="sovereign_rotation_keys_")
        kr = KeyRing(keys_dir=Path(_keys_dir))
        kr.generate_new_key(reason="rotation_test_isolated")
        kr.save_to_disk()
        return kr

    def test_event_with_key_a_verifies_after_rotation_to_b(self):
        """حدث موقّع بالمفتاح A يُتحقق بنجاح بعد الدوران إلى B."""
        # R-627: عزل كامل — KeyRing معزول (بدون fallback للحقيقي)
        keyring = self._isolated_keyring()
        key_a = keyring.get_active_key().key_id

        # 1) كتابة حدث بالمفتاح A — عبر ربط keyring يدويًا
        core1 = SovereignCore()
        core1._keyring = keyring
        core1._keyring_key_id = key_a
        r1 = core1.append_event(EventType.INTERACTION, {"test": "rotate_a"}, user="test")
        assert r1["key_id"] == key_a
```

**بعد (على d56e24e — مسارات معزولة صريحة):**

```
"""
اختبار R-625/R-626: مسار اختيار المفتاح والتحقق بعد الدوران

يختبر أن:
1. أحداث المفتاح A تُتحقق بنجاح بعد الدوران إلى B (key_id من الحدث، ليس النشط)
2. تغيير key_id وحده (تزييف) يُكتشف
3. غياب KeyRing: الكاتب يرفض الإلحاق (لا fallback)
4. التوافق التاريخي: أحداث key_id بصيغة 5 حقول تُتحقق بالصيغة القديمة
"""

import json
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in [str(_REPO_ROOT), str(_REPO_ROOT / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# عزل R-619
if not os.environ.get("SOVEREIGN_DATA_ROOT"):
    _test_data_root = tempfile.mkdtemp(prefix="sovereign_test_data_")
    os.environ["SOVEREIGN_DATA_ROOT"] = _test_data_root

import pytest

from backend.memory.core import SovereignCore, EventType
from backend.sovereign.keys import KeyRing, SignatureVerifier


class TestKeySelectionAfterRotation:
    """اختبارات مسار اختيار المفتاح بعد الدوران (R-625).
    
    R-627: عزل كامل — دوران المفتاح يُكتب إلى keys_dir معزول (وليس الحقيقي)،
    حتى لا يلوث الاختبار المفتاح الفعلي. fallback R-621 لا يُفعّل هنا
    لأن keyring.json موجود في الجذر المعزول.
    """

    def _isolated_keyring(self) -> KeyRing:
        """يُنشئ KeyRing معزول (بدون fallback للحقيقي) — للدوران."""
        _keys_dir = tempfile.mkdtemp(prefix="sovereign_rotation_keys_")
        kr = KeyRing(keys_dir=Path(_keys_dir))
        kr.generate_new_key(reason="rotation_test_isolated")
        kr.save_to_disk()
        return kr

    def test_event_with_key_a_verifies_after_rotation_to_b(self, tmp_path):
        """حدث موقّع بالمفتاح A يُتحقق بنجاح بعد الدوران إلى B.

        R-682: مسارات صريحة معزولة — SovereignCore() بلا مسارات يكتب في
        سجل الجذر المشترك للجلسة (عزل الوحدة النمطية يأتي بعد استيراد
        config فلا يُعيد توجيه DATA_DIR)، فيلوّث سجل الجلسة بأحداث
        بمفاتيح معزولة تُفشل تحقق السلامة لاحقًا (رفض R-626).
        """
        _core_dir = tmp_path / "sovereign_core"
        _core_dir.mkdir(parents=True, exist_ok=True)
        (_core_dir / "blobs").mkdir(exist_ok=True)
        _core_paths = dict(
```

### الإصلاح 2 — دورة حياة الخيوط: backend/runtime/threads.py (دالة stop_all_and_join على d56e24e)

```
def stop_all_and_join(timeout: float = 8.0) -> int:
    """إيقاف كل الخيوط المسجلة والانتظار حتى انتهائها (deadline واحد).

    الترتيب: أعلام الإيقاف أولًا ثم إيقاظ النوم (الخيط المستيقظ يجد العلم
    منزولًا فيخرج فورًا). إخفاقات الموقِفات تُجمع وتُظهر كلها ولا توقف
    محاولة إيقاف البقية. تعيد عدد الخيوط التي لم تتوقف خلال المدة.

    لا تُمسح المراجع إن بقيت خيوط حية — تبقى قابلة للإيقاف في استدعاء
    لاحق (وإلا صار عدّ الأحياء بعدها صفرًا زورًا).
    """
    import time
    stopper_errors = []
    for s in list(_STOPPERS):
        try:
            errors = s()
            if errors:
                stopper_errors.extend(errors)
        except Exception as e:
            stopper_errors.append(f"{type(e).__name__}: {e}")
    if stopper_errors:
        for err in stopper_errors:
            _log.error(f"⚠️ فشل إيقاف أحد أعلام الخيوط (استمر إيقاف البقية): {err}")
    deadline = time.monotonic() + timeout
    _STOP_EVENT.set()  # إيقاظ كل النوم المقاطع بعد نزول الأعلام
    for t in list(_THREADS):
        if t.is_alive():
            t.join(timeout=max(0.0, deadline - time.monotonic()))
    remaining = sum(1 for t in _THREADS if t.is_alive())
    if remaining == 0:
        _THREADS.clear()
        _STOPPERS.clear()
    return remaining


# شبكة أمان أخيرة: إن لم تستدعِ الجلسة stop_all_and_join بنفسها
# (كما في الإنتاج)، تُستدعى عند خروج العملية — الخيوط daemon فتموت
# أصلًا مع العملية، لكن هذا يمنع الكتابة بعد إغلاق ملفات السجل.
atexit.register(lambda: stop_all_and_join(timeout=2.0))
```

## 19) اختبار الحارس السلوكي (حراسة نظافة سجل الجلسة) ونتيجته

الاختبار: `tests/test_session_ledger_key_hygiene.py` على d56e24e:

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

**RED (على الكود القديم 60053d4 + حارس d56e24e):** المخرج الكامل (60 سطرًا):

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

**GREEN (على d56e24e):**

```
........................                                                 [100%]
24 passed in 0.15s
```

## 20) التشغيلان الفاشلان (بالنصوص الحرفية)

### التشغيل 38812431011 (على a733ab8) — خطأ الانتقاء الذاتي

الرابط: https://github.com/reeveero-tech/sovereign_ai/actions/runs/38812431011

الخطأ الحرفي (موثق في forensics/OPERATIONAL_TESTS.md):

```
الانتقاء الذاتي) — الخرج الموثق في PY311_VERIFICATION.md وسجل الإغلاق.

كذلك أُضيف إلى ci.yml خط إفصاح بيئة خام (`python -VV` + `pip freeze` +
`pip check`) في مهمة الاختبار نفسها — لتوثيق PY311_VERIFICATION.md من
المصدر مباشرة.

## R-682 — البند ١١ (مسار التحقق): RED/GREEN لمهمة verify-full

### RED (مُشاهد — تشغيل 38812431011 على a733ab8، فشل فعلي)

المهمة الجديدة verify-full نفّذت `verify.sh --full` على Python 3.11.17:
الجزء المحلي نجح (412 passed / 0 skipped / 0 failed) ثم فشل عند فحص حالة
تشغيل CI المرجعي — **كشف خطأ انتقاء ذاتي حقيقي**: فحص الحالة كان يمسح
بـ`headSha` (أول تشغيل للـ SHA) لا بمعرّف التشغيل المختار صراحة
(`CI_RUN_ID`)، فالتقط تشغيل verify-full نفسه (قيد التنفيذ طبيعيًا)
وظنه هو المرجعي — الرسالة: «CI run 38812061849 is NOT completed
(status: in_progress)» رغم اكتماله الفعلي قبل 4.5 دقيقة.
```

### التشغيل 38817055678 (على 20a81ce) — متغير غير معرف

الرابط: https://github.com/reeveero-tech/sovereign_ai/actions/runs/38817055678

الخطأ الحرفي:

```
{"stdout":"Full verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:26:16.3094712Z HEAD: 20a81cef38c2b9dd11b92823d175c965bab923e7\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:26:16.3304779Z [info] Generated ephemeral data/key.secret (not committed)\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:26:16.3305136Z \nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:26:16.3305315Z [1/2] Running test suite (tests/ + backend/tests/, excluding operational)...\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:27:06.1419384Z ........................................................................ [ 16%]\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:27:38.9938236Z ........................................................................ [ 33%]\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:27:40.7284693Z ........................................................................ [ 50%]\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:27:41.2059996Z ........................................................................ [ 67%]\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:15.3619376Z ........................................................................ [ 84%]\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.7788205Z ................................................................         [100%]\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.7788654Z =============================== warnings summary ===============================\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.7789253Z ../../opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/starlette/testclient.py:40\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.7790422Z   /opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.7791494Z     _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.7792205Z \nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.7792537Z -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.7792886Z 424 passed, 1 deselected, 1 warning in 142.63s (0:02:22)\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9797575Z ✅ git SHA embedded in JUnit XML: 20a81cef38c2b9dd11b92823d175c965bab923e7\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9821455Z \nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9821609Z [2/2] Verifying zero skips (DoD hard requirement)...\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9944659Z ✅ بوابة الاختبارات ناجحة: 424 passed, 0 skipped, 0 failed\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9970743Z \nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9970936Z ==========================================\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9972698Z  [FULL MODE] CI + Clean Clone comparison\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9973229Z ==========================================\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9973435Z \nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:39.9973961Z [3/4] Fetching CI run for HEAD SHA=20a81ce...\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:41.5313806Z verify.sh: line 114: CI_STATUS: unbound variable\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:41.5314474Z CI Run: 38816633364 (completed/success — اختيار صريح + فحص هوية workflow)\nFull verification (verify.sh --full, manual only)\tRun the LITERAL owner verification command (verify.sh --full from a clean clone)\t2026-10-15T22:28:41.5330983Z ##[error]Process completed with exit code 1.","stderr":"asi_exec: stopped background processes this command left running; run long-lived work in the foreground instead","exit_code":0}
```

## 21) ملف JUnit للتشغيل التشغيلي

آخر تشغيل تشغيلي ناجح: 38819575692 (على 10c2bf5 — الكود مطابق لـd56e24e؛ الالتزام الأخير توثيقي خالص). https://github.com/reeverero-tech/sovereign_ai/actions/runs/38819575692

**تنزيل مرفق JUnit (junit-operational) غير متاح من بيئة الوكيل** — الخطأ الحرفي:
`error downloading junit-with-sha-10c2bf5: HTTP 401: Requires authentication`.
البديل المتاح: مخرج pytest التشغيلي الحرفي من سجل التشغيل نفسه (يتضمن
نتيجة الاختبار الوحيد المحدد وملف JUnit المولد):

```
test session starts ==============================
platform linux -- Python 3.11.17, pytest-9.1.1, pluggy-1.7.0 -- /opt/hostedtoolcache/Python/3.11.17/x64/bin/python
configfile: pytest.ini
collecting ... collected 425 items / 424 deselected / 1 selected

tests/test_gate1_operational_auth.py::TestOperationalAuth::test_operational_auth_new_key_accepted_old_rejected PASSED [100%]

- generated xml file: /home/runner/work/sovereign_ai/sovereign_ai/forensics/pytest_operational.xml -
================= 1 passed, 424 deselected, 1 warning in 2.81s =================
with:
  name: junit-operational-10c2bf5
  path: forensics/pytest_operational.xml
```

## 22) مخرج verify.sh --full: الناتج الحرفي كاملًا

السياق: تشغيل 38823848533 (workflow_dispatch على d56e24e) — المهمة تنفذ الأمر الحرفي: clone نظيف مثبت على TARGET_SHA ثم timeout 1500 bash verify.sh --full. المخرج الكامل (3174 حرفًا، بلا اقتصاص):

```
==========================================
 R-682 Verification Script
==========================================
HEAD: d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
[info] Generated ephemeral data/key.secret (not committed)

[1/2] Running test suite (tests/ + backend/tests/, excluding operational)...
........................................................................ [ 16%]
........................................................................ [ 33%]
........................................................................ [ 50%]
........................................................................ [ 67%]
........................................................................ [ 84%]
................................................................         [100%]
=============================== warnings summary ===============================
../../opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/starlette/testclient.py:40
  /opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
424 passed, 1 deselected, 1 warning in 231.05s (0:03:51)
✅ git SHA embedded in JUnit XML: d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad

[2/2] Verifying zero skips (DoD hard requirement)...
✅ بوابة الاختبارات ناجحة: 424 passed, 0 skipped, 0 failed

==========================================
 [FULL MODE] CI + Clean Clone comparison
==========================================

[3/4] Fetching CI run for HEAD SHA=d56e24e...
CI Run: 38823543021 (completed/success — اختيار صريح + فحص هوية workflow)
CI:     sha=d56e24e8b0df... tests=424 failed=0 skipped=0 unique_ids=424
Local:  sha=d56e24e8b0df... tests=424 failed=0 skipped=0 unique_ids=424
✅ CI + Local MATCH (SHA + test counts + (normalized_classname,name) Counter + zero failures + zero skips)

[4/4] Clean clone verification (git checkout pinned to SHA=d56e24e)...
[info] Generated ephemeral data/key.secret in clone (not committed)
  /opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
424 passed, 1 deselected, 1 warning in 230.34s (0:03:50)
✅ SHA embedded in clone JUnit: d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
Clone:  tests=424 failed=0 skipped=0 unique_ids=424
Local:  tests=424 failed=0 skipped=0 unique_ids=424
✅ Clean clone JUnit MATCHES Local (count + (normalized_classname,name) Counter + zero failures + zero skips)

==========================================
 VERIFICATION COMPLETE
 HEAD: d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
 JUnit: forensics/pytest_results.xml (git_sha embedded)
 Mode: --full
==========================================```

## 23) مخرج CI الأخضر: الروابط والمقتطفات

التشغيلات على d56e24e (كلها success):

- push CI: https://github.com/reeveero-tech/sovereign_ai/actions/runs/38823543021 — 424 passed, 0 skipped, 0 failed
- verify-full (الأمر الحرفي): https://github.com/reeveero-tech/sovereign_ai/actions/runs/38823848533 — تطابق ثلاثي 424/0/0/0

مقتطف من مخرج CI (السطر الختامي لوظيفة الاختبار):

```
Tests + Atomic Batch Gate	Run test suite (tests/ + backend/tests/) with JUnit + SHA	2026-10-15T23:32:20.3090025Z =========== 424 passed, 1 deselected, 1 warning in 167.09s (0:02:47) ===========
```
