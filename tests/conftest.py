"""إعدادات الاختبارات — يضبط البيئة قبل أي استيراد للنظام، ويغلق خيوط الخلفية بنهاية الجلسة"""
import os
import sys

import pytest

# R-682 (بند ٦): تعطيل خيوط الخلفية في بيئة الاختبار — يجب أن يُضبط قبل
# أي استيراد لوحدات النظام (تُفحص العلامة عند Thread.start()).
# السبب: خيط خلفي خارج عمر بيئته يوقّع بمفاتيح لم تعد في KeyRing
# (رفض R-626 — 244 سطر رفض في جلسة 2026-10-16) ويكتب بعد إغلاق
# ملفات السجل («--- Logging error ---»). دورة الحياة الحقيقية للخيوط
# تُختبر في tests/test_background_threads_shutdown.py عبر جلسة فرعية
# مع الخيوط مفعّلة.
os.environ["SOVEREIGN_DISABLE_BACKGROUND_THREADS"] = "1"

# مفتاح سيد ثابت للاختبارات — يجب تعريفه قبل استيراد config/app.
# (دون هذا، يولّد config.py مفتاحاً عشوائياً مؤقتاً عند أول استيراد،
#  فيفشل أي اختبار لاحق يقارن بالمفتاح المطلوب — راجع المرحلة 3)
if not os.environ.get("SOVEREIGN_KEY"):
    os.environ["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"

# R-619: عزل عام — كل الاختبارات تكتب إلى جذر مؤقت، ليس data/ الحقيقي.
# (المشكلة: اختبارات TestClient(app) تُنشئ أحداثًا في السجل الحقيقي،
#  فنما السجل من 11,777 إلى 116,452+ حدثًا — تلوث الدليل الجنائي)
# الاستثناء: اختبارات معزولة بالفعل تُحدد SOVEREIGN_DATA_ROOT بنفسها.
if not os.environ.get("SOVEREIGN_DATA_ROOT"):
    import tempfile as _tempfile
    _test_data_root = _tempfile.mkdtemp(prefix="sovereign_test_data_")
    os.environ["SOVEREIGN_DATA_ROOT"] = _test_data_root

# R-720: عقل Ollama معطل في الاختبارات بالبناء — مبدأ R-704 «لا اتصال ضمني
# في الاختبارات» كان محفوظًا بالصدفة (لا ملف .env)؛ بتفعيل المالك للعقل عبر
# backend/.env (خادم على شبكته المحلية) كان أي اختبار يمر في build_reply
# سيستدعي النموذج الحقيقي (بطيء + شبكي + يكسر عقود الردود المنظمة).
# المتغير البيئي يعلو على .env بحكم _ollama_env نفسها — فالتطبيق الفعلي
# يقرأ .env ويعمل عقله، والاختبارات معزولة. الحارس:
# tests/test_ollama_test_isolation.py
os.environ["OLLAMA_ENABLED"] = "false"

# R-719/R-721: عزل قرص Supabase عن الاختبارات — كان ضمنيًا في رأس ملف
# test_supabase_disk.py (setdefault) فانتقل إلى conftest ليكون صريحًا
# وبعيدًا عن ترتيب الاستيراد: أي إعداد حقيقي في .env لا يلمس الاختبارات.
# الحارس: tests/test_supabase_disk.py::test_cloud_disk_disabled_in_test_session
os.environ.setdefault("SUPABASE_ENV_FILE", "/nonexistent-R719.env")

# R-634: إنشاء KeyRing معزول مع مفتاح نشط (في الجذر المعزول)
# — بديل fallback للحقيقي (R-621 معطل). هذا يضمن أن SovereignCore()
# في بيئة الاختبار يجد مفتاحًا نشطًا (فشل مُغلق يمنع الاختبارات
# التي تُنشئ أحداثًا).
# ملاحظة: المفتاح اختباري (ليس مفتاح تشغيل) — لا علاقة بالحقيقي.
try:
    _test_root = os.environ.get("SOVEREIGN_DATA_ROOT")
    if _test_root:
        from pathlib import Path as _Path
        _keys_dir = _Path(_test_root) / "keys"
        _keys_dir.mkdir(parents=True, exist_ok=True)
        _keyring_file = _keys_dir / "keyring.json"
        if not _keyring_file.exists():
            # إنشاء KeyRing معزول مع مفتاح نشط (اختباري)
            import sys as _sys
            _backend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
            if _backend not in _sys.path:
                _sys.path.insert(0, _backend)
            from sovereign.keys import KeyRing as _TestKeyRing
            _kr = _TestKeyRing(keys_dir=_keys_dir)
            _kr.generate_new_key(reason="test_env_r634")
            _kr.save_to_disk()
except Exception as _e:
    # لا نُفشل الاستيراد — الاختبارات المعزولة ستُنشئ مفاتيحها
    pass

# أضف backend إلى مسار الاستيراد (app.py يستورد orchestrator نسبياً)
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# أضف جذر المستودع (لـ nexus)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# R-682 (الجولة التشغيلية الثالثة — تصويب): تسجيل خيار --run-operational هنا.
# كان مسجلًا في conftest.py بجذر المستودع (الالتزام 0c5143d) مع تعليل خاطئ
# («الاستدعاء بلا مسارات لا يحمّل tests/conftest.py قبل تحليل الخيارات») —
# اختُبر التجربة على pytest 9.1.1 (نفس إصدار CI) فظهر غير صحيح: التسجيل هنا
# يعمل للاستدعاء بلا مسارات ولمسارات. نُقل التسجيل إلى هنا وأُلغي ملف الجذر
# (راجع forensics/OPERATIONAL_TESTS.md — الجولة الثالثة).
def pytest_addoption(parser):
    parser.addoption(
        "--run-operational",
        action="store_true",
        default=False,
        help=(
            "R-661/R-682: تشغيل اختبارات operational التشغيلية "
            "(تقرأ أسرار المضيف وتكتب بيانات حقيقية — يدويًا فقط)"
        ),
    )


# R-682 (بند ٥): إنهاء منظم لخيوط الخلفية في نهاية جلسة pytest —
# إيقاف الأعلام ثم انضمام بانتظار محدود، قبل أن يغلق pytest ملفات
# الالتقاط، فلا يكتب خيط في ملف مغلق («--- Logging error ---").
# (الدفاع الأخير atexit داخل runtime/threads.py لا يكفي وحده لأنه
# قد يأتي بعد إغلاق الالتقاط — راجع forensics/OPERATIONAL_TESTS.md.)
@pytest.fixture(scope="session", autouse=True)
def _shutdown_background_threads():
    from runtime import threads as _threads

    yield
    remaining = _threads.stop_all_and_join(timeout=8.0)
    if remaining:
        raise RuntimeError(
            f"R-682: {remaining} خيط خلفي لم يتوقف بعد stop_all_and_join — "
            "خطر كتابة بعد إغلاق ملفات السجل"
        )

# حارس data/keys الحقيقي (بند OWNER_REQUIRED ٥ — واقعة R-621 لا تتكرر):
# **منع الكتابة** — عند تحميل هذا الملف (قبل أي استيراد لملفات الاختبار):
# الملفان المحميان (HISTORY.jsonl + keyring.json الحقيقيان) يصيران للقراءة
# فقط طوال الجلسة — أي محاولة كتابة (اختبارًا أو عند الاستيراد) تُرفض
# بـ PermissionError صريح يسمي الملف، وهذا يمنع أيضًا نمط «اكتب ثم استعد
# الأصل» الذي تفلت منه مقارنة الحالة النهائية. الوضعان يُستعادان عند
# التصفية، ثم **كشف أثر التغيير**: بصمة البايتات عند البدء تُقارن عند
# النهاية — أي تغيير متبقٍ يفشل الجلسة صراحة (محتوى keyring.json لا يُعرض
# أبدًا — بصمة SHA-256 فقط). (التجربة الكاملة RED→GREEN بالتشغيل:
# forensics/R621_REAL_KEYS_GUARD.md)
from _real_keys_guard import protect_real_keys, snapshot  # noqa: E402

_PROTECTED_MODES = protect_real_keys(_ROOT)
# البصمة عند التحميل — قبل أي استيراد لملفات الاختبار: التلوث وقت التجميع
# (استيراد ملف اختبار) يُقارن بأصلٍ قبله، لا بأصلٍ بعده
_GUARD_SNAPSHOT = snapshot(_ROOT)


def pytest_sessionfinish(session, exitstatus):
    """استعادة الأوضاع بعمر الجلسة نفسها — تعمل مع --collect-only ومع
    إخفاقات التجميع (fixtures لا تشغل هناك أصلًا)."""
    from _real_keys_guard import restore_real_keys

    restore_real_keys(_ROOT, _PROTECTED_MODES)


@pytest.fixture(scope="session", autouse=True)
def _guard_real_keys_untouched():
    from _real_keys_guard import assert_untouched

    yield
    assert_untouched(_ROOT, _GUARD_SNAPSHOT)


# R-682: حراسة نظافة مفاتيح سجل الجلسة — كل حدث في سجل الجذر المشترك يحمل
# key_id يجب أن يكون في keyring الجلسة. تمنع تلوث السجل المشترك بأحداث
# بمفاتيح معزولة (السبب الجذري لرفض R-626 المتبقي في تحقق السلامة).
# الجذر يُلتقط عند بدء الجلسة (قبل أي fixture وحدة يغيّر SOVEREIGN_DATA_ROOT).
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

    assert not offenders, (
        "R-682 — تلوث سجل الجلسة بأحداث بمفاتيح معزولة "
        f"({len(offenders)} حدثًا):\n" + "\n".join(offenders[:10]) +
        "\nالسبب الشائع: SovereignCore() بلا مسارات صريحة مع keyring معزول، "
        "أو KeyRotation بلا ledger_path — استخدم مسارات tmp_path صريحة."
    )

