"""اختبارات حارس data/keys الحقيقي — بند OWNER_REQUIRED ٥ (واقعة R-621 لا تتكرر).

طبقات الحارس المُثبتة هنا سلوكيًا:
1. **منع الكتابة** — جلسة يكتب فيها اختبار (تنفيذًا أو عند الاستيراد) في
   data/keys الحقيقي تُرفض الكتابة فيها بـ PermissionError صريح يسمي الملف.
2. **كشف أثر التغيير** — إن تغيّر الملف رغم المنع، تفشل الجلسة برسالة
   الحارس؛ ومحتوى keyring.json (مادة محمية) لا يُعرض أبدًا — بصمة فقط.

المسبارات تستخدم **ملفّي conftest الحقيقيين** أنفسهما (نسخًا حرفيًا) في
هياكل مصغرة — فحذف الحارس من أي منهما يُفشل هذه الاختبارات، لا مجرد
اختبار الوحدة بمعزل عن التثبيت الفعلي.

الدليل الجنائي الكامل (التسلسل الحقيقي: إعادة إنتاج الفجوة ← RED على
نسخة الأساس ← الإصلاح ← GREEN): forensics/R621_REAL_KEYS_GUARD.md.
"""
import shutil
import subprocess
import sys
from pathlib import Path

# جذر المستودع الحقيقي (هذا الملف: <repo>/backend/tests/invariants/)
_REPO_ROOT = Path(__file__).resolve().parents[3]

# سطر التلطيخ المحقون — يُطابق نصيًا في رسالة الفشل (HISTORY مادة عامة)
_POLLUTION_LINE = '{"ts":"2026-10-18T00:00:00Z","action":"KEY_CREATED","key_id":"probe999","reason":"RED probe R-621"}'

_REAL_LINES = [
    '{"ts":"2026-10-01T00:00:00Z","action":"KEY_CREATED","key_id":"aaa111","reason":"real"}',
    '{"ts":"2026-10-02T00:00:00Z","action":"KEY_CREATED","key_id":"bbb222","reason":"real"}',
]

# مفتاحان اصطناعيان مميزان — يُثبت عدم ظهور أي منهما في أي مخرجات
_FAKE_KEY_A = "FAKE_PRIVATE_MATERIAL_AAA111"
_FAKE_KEY_B = "FAKE_PRIVATE_MATERIAL_BBB222"

# اختبار التلطيخ (تنفيذي — يكتب مباشرة متجاوزًا عزل R-619)
_POLLUTING_TEST = '''\
from pathlib import Path


def test_pollutes_real_history():
    """محاكاة واقعة R-621: كتابة مباشرة تتجاوز عزل R-619."""
    p = Path(__file__).resolve().parents[{DEPTH}] / "data" / "keys" / "HISTORY.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write({POLLUTION!r} + "\\n")
'''

# اختبار التلطيخ عند الاستيراد (قبل أي fixture تنفيذي — يختبر منع مستوى
# التحميل في conftest)
_IMPORT_TIME_POLLUTING_TEST = '''\
from pathlib import Path

_p = Path(__file__).resolve().parents[{DEPTH}] / "data" / "keys" / "HISTORY.jsonl"
with _p.open("a", encoding="utf-8") as _f:
    _f.write({POLLUTION!r} + "\\n")


def test_import_time_pollution():
    pass
'''

# اختبار يغيّر keyring.json متجاوزًا chmod عمدًا (هدم متعمد للطبقة الأولى —
# يُستخدم هنا فقط لإثبات أمان رسائل الطبقة الثانية: لا مادة مفاتيح في المخرجات)
_KEYRING_POLLUTING_TEST = '''\
import os
from pathlib import Path


def test_changes_real_keyring():
    p = Path(__file__).resolve().parents[{DEPTH}] / "data" / "keys" / "keyring.json"
    os.chmod(p, 0o644)  # هدم متعمد للمنع — لاختبار كشف أثر التغيير ورسائله
    p.write_text({FAKE_KEYRING!r}, encoding="utf-8")
'''

_CLEAN_TEST = '''\
def test_does_nothing():
    """مسار سليم — لا كتابة في الملفات المحمية."""
    assert True
'''


def _make_history(root: Path) -> None:
    keys_dir = root / "data" / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    (keys_dir / "HISTORY.jsonl").write_text(
        "\n".join(_REAL_LINES) + "\n", encoding="utf-8"
    )


def _build_tests_tree_replica(replica: Path) -> Path:
    """هيكل مصغر لشجرة tests/ — بملف conftest الحقيقي نفسه (نسخة حرفية).

    يثبت أن الحارس مثبت فعلًا في tests/conftest.py: حذفه من الملف الحقيقي
    يُفشل المسبار.
    """
    shutil.copytree(_REPO_ROOT / "backend", replica / "backend")
    (replica / "tests").mkdir()
    shutil.copy(_REPO_ROOT / "tests" / "conftest.py", replica / "tests" / "conftest.py")
    _guard_src = _REPO_ROOT / "tests" / "_real_keys_guard.py"
    # النسخة مشروطة كي يعمل المسبار على نسخة أساس قديمة (قبل الحارس) —
    # غياب الوحدة هناك يظهر في فشل الجلسة نفسها (conftest الجديد يستوردها)،
    # لا في انكسار المسبار قبل الرصد.
    if _guard_src.exists():
        shutil.copy(_guard_src, replica / "tests" / "_real_keys_guard.py")
    _make_history(replica)
    return replica


def _build_backend_tree_replica(replica: Path) -> Path:
    """هيكل مصغر لشجرة backend/tests/ — بملف conftest الحقيقي نفسه.

    يثبت أن الحارس مثبت فعلًا في backend/tests/conftest.py.
    """
    shutil.copytree(_REPO_ROOT / "backend", replica / "backend")
    (replica / "tests").mkdir()
    _guard_src = _REPO_ROOT / "tests" / "_real_keys_guard.py"
    if _guard_src.exists():  # كما أعلاه — المسبار يعمل على نسخة الأساس أيضًا
        shutil.copy(_guard_src, replica / "tests" / "_real_keys_guard.py")
    _make_history(replica)
    return replica


def _run_session(session_dir: Path, test_relpaths) -> tuple[int, str]:
    """تشغيل جلسة pytest فرعية وإرجاع (رمز الخروج، المخرجات الكاملة).

    test_relpaths: مسار واحد أو قائمة مسارات (جلسة بشجرات متعددة).
    """
    if isinstance(test_relpaths, str):
        test_relpaths = [test_relpaths]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *test_relpaths],
        cwd=str(session_dir),
        capture_output=True,
        text=True,
        timeout=180,
    )
    return proc.returncode, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# المسبار ١ — الحارس مثبت في tests/conftest.py الحقيقي ويرفض الكتابة
# ---------------------------------------------------------------------------


def test_real_conftest_rejects_pollution_in_tests_tree(tmp_path):
    """كتابة اختبارية في HISTORY الحقيقي تُرفض — في شجرة tests/ وحدها.

    الرفض هنا منع كتابة (PermissionError يسمي الملف) — لا نجاحًا صامتًا.
    قبل الحارس كانت هذه الجلسة تنجح (إعادة إنتاج الفجوة + RED الموثقان في
    forensics/R621_REAL_KEYS_GUARD.md).
    """
    replica = _build_tests_tree_replica(tmp_path / "replica")
    (replica / "tests" / "test_pollute.py").write_text(
        _POLLUTING_TEST.format(POLLUTION=_POLLUTION_LINE, DEPTH=1), encoding="utf-8"
    )
    rc, output = _run_session(replica, "tests/test_pollute.py")

    assert rc != 0, (
        "فجوة: جلسة التلطيخ في شجرة tests/ نجحت — كتابة اختبارية في "
        "data/keys الحقيقي بلا رفض صريح (عودة واقعة R-621)"
    )
    assert "PermissionError" in output, (
        "الرفض يجب أن يكون منع كتابة صريحًا (PermissionError) يسمي الملف"
    )
    assert "HISTORY.jsonl" in output, "رسالة الرفض يجب أن تسمي الملف المحمي"
    # الملف لم يُلطخ (المنع منع الكتابة نفسها — لا مجرد اكتشافها لاحقًا)
    assert (replica / "data" / "keys" / "HISTORY.jsonl").read_text(
        encoding="utf-8"
    ) == "\n".join(_REAL_LINES) + "\n", "المنع يجب أن يمنع التغيير نفسه"


# ---------------------------------------------------------------------------
# المسبار ٢ — الحارس مثبت في backend/tests/conftest.py الحقيقي ويرفض الكتابة
# ---------------------------------------------------------------------------


def test_real_conftest_rejects_pollution_in_backend_tree(tmp_path):
    """نفس الرفض في شجرة backend/tests/ وحدها — بملف conftest الحقيقي نفسه."""
    replica = _build_backend_tree_replica(tmp_path / "replica")
    pollute_dir = replica / "backend" / "tests" / "invariants"
    pollute_dir.mkdir(parents=True, exist_ok=True)
    (pollute_dir / "test_pollute.py").write_text(
        _POLLUTING_TEST.format(POLLUTION=_POLLUTION_LINE, DEPTH=3), encoding="utf-8"
    )
    rc, output = _run_session(replica, "backend/tests/invariants/test_pollute.py")

    assert rc != 0, (
        "فجوة: جلسة التلطيخ في شجرة backend/tests/ نجحت — كتابة اختبارية "
        "في data/keys الحقيقي بلا رفض صريح"
    )
    assert "PermissionError" in output
    assert "HISTORY.jsonl" in output
    assert (replica / "data" / "keys" / "HISTORY.jsonl").read_text(
        encoding="utf-8"
    ) == "\n".join(_REAL_LINES) + "\n"


# ---------------------------------------------------------------------------
# المسبار ٣ — الكتابة عند الاستيراد (قبل أي fixture) ممنوعة أيضًا
# ---------------------------------------------------------------------------


def test_real_conftest_rejects_import_time_pollution(tmp_path):
    """كتابة عند استيراد ملف الاختبار (أثناء التجميع، قبل أي تنفيذ) تُرفض.

    يثبت أن المنع على مستوى تحميل conftest — أسبق من أي استيراد لملفات
    الاختبار.
    """
    replica = _build_tests_tree_replica(tmp_path / "replica")
    (replica / "tests" / "test_pollute.py").write_text(
        _IMPORT_TIME_POLLUTING_TEST.format(POLLUTION=_POLLUTION_LINE, DEPTH=1),
        encoding="utf-8",
    )
    rc, output = _run_session(replica, "tests/test_pollute.py")

    assert rc != 0, "كتابة عند الاستيراد يجب أن تُرفض — لا نافذة قبل الجلسة"
    assert "PermissionError" in output
    assert "HISTORY.jsonl" in output
    assert (replica / "data" / "keys" / "HISTORY.jsonl").read_text(
        encoding="utf-8"
    ) == "\n".join(_REAL_LINES) + "\n"


# ---------------------------------------------------------------------------
# المسبار ٤ — رسائل الحارس لا تسرب مادة المفاتيح أبدًا
# ---------------------------------------------------------------------------


def test_keyring_change_message_leaks_no_key_material(tmp_path):
    """تغيير keyring.json (متجاوزًا chmod عمدًا) يفشل الجلسة برسالة الحارس —
    ولا تظهر قيمة أي مفتاح (اصطناعي مميز) في كامل المخرجات.

    الطبقة الأولى (المنع) تُتجاوز هنا عمدًا كي يُختبر أمان رسائل الطبقة
    الثانية (كشف أثر التغيير) — بصمة SHA-256 فقط، لا محتوى.
    """
    fake_keyring = (
        '{"keys": [{"key_id": "fake1", "private_key": "' + _FAKE_KEY_A + '"}]}'
    )
    replica = _build_tests_tree_replica(tmp_path / "replica")
    # keyring حقيقي موجود مسبقًا (كي يكون التغيير تعديلًا لا إنشاء)
    (replica / "data" / "keys" / "keyring.json").write_text(
        '{"keys": [{"key_id": "old", "private_key": "' + _FAKE_KEY_B + '"}]}',
        encoding="utf-8",
    )
    (replica / "tests" / "test_pollute.py").write_text(
        _KEYRING_POLLUTING_TEST.format(FAKE_KEYRING=fake_keyring, DEPTH=1),
        encoding="utf-8",
    )
    rc, output = _run_session(replica, "tests/test_pollute.py")

    assert rc != 0, "تغيير keyring.json الحقيقي يجب أن يفشل الجلسة"
    # رسالة الحارس نفسها (البادئة القياسية + نوع التغيير) — كي لا يمر
    # الفشل بسبب خطأ آخر غير الحارس
    from _real_keys_guard import GUARD_MESSAGE_PREFIX

    assert GUARD_MESSAGE_PREFIX in output, (
        "فشل الجلسة يجب أن يكون برسالة الحارس المحددة، لا بسبب خطأ آخر"
    )
    assert "keyring.json: عُدّل أثناء الجلسة" in output, (
        "رسالة الحارس يجب أن تسمي الملف ونوع التغيير"
    )
    # لا مادة مفاتيح في أي مخرجات — لا القديمة ولا الجديدة
    assert _FAKE_KEY_A not in output, (
        "تسريب: مادة المفتاح الجديد ظهرت في مخرجات الجلسة"
    )
    assert _FAKE_KEY_B not in output, (
        "تسريب: مادة المفتاح القديم ظهرت في مخرجات الجلسة"
    )


# ---------------------------------------------------------------------------
# المسار السليم — جلسة بلا كتابة تنجح (لا حارس يُفشل الأبرياء)
# ---------------------------------------------------------------------------


def test_clean_session_passes(tmp_path):
    replica = _build_tests_tree_replica(tmp_path / "replica")
    (replica / "tests" / "test_clean.py").write_text(_CLEAN_TEST, encoding="utf-8")
    rc, output = _run_session(replica, "tests/test_clean.py")

    assert rc == 0, f"جلسة سليمة فشلت بلا سبب: {output}"


def test_guard_restores_file_modes_after_session(tmp_path):
    """استعادة الوضع الأصلي بعد الجلسة — انحدار خلل حقيقي وُجد بالتشغيل:
    حارسا conftest (شجرتا tests/ وbackend/tests/) كانا يسجل كلٌّ منهما وضع
    444 كأنه «الأصلي» فتستعيد الجلسة الملف للقراءة فقط دائمًا. الحارس
    الآن لا يسجل إلا ما غيّره بنفسه (idempotent).
    """
    import os as _os
    import stat as _stat

    replica = _build_tests_tree_replica(tmp_path / "replica")
    history = replica / "data" / "keys" / "HISTORY.jsonl"
    before_mode = _stat.S_IMODE(_os.stat(history).st_mode)
    (replica / "tests" / "test_clean.py").write_text(_CLEAN_TEST, encoding="utf-8")
    rc, output = _run_session(replica, "tests/test_clean.py")

    assert rc == 0, f"جلسة سليمة فشلت بلا سبب: {output}"
    after_mode = _stat.S_IMODE(_os.stat(history).st_mode)
    assert after_mode == before_mode, (
        f"وضع الملف لم يُستعد: قبل الجلسة {oct(before_mode)} ← بعدها "
        f"{oct(after_mode)} (الحارس يحمي أثناء الجلسة ويعيد الوضع بعدها)"
    )


# ---------------------------------------------------------------------------
# وحدة الدالة — كل مسار فشل موصوف، ومادة المفاتيح لا تُعرض
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# جولة المراجعة الثانية — مسبارات الثغرات المكتشفة (RED قبل إصلاحها)
# ---------------------------------------------------------------------------

# اختبار ينشئ keyring.json الغائب عند الاستيراد (الحماية الحالية تتجاهل
# الملف الغائب والدليل قابل للكتابة)
_CREATE_ABSENT_KEYRING_TEST = '''\
from pathlib import Path


def test_creates_absent_keyring():
    """إنشاء keyring.json في data/keys — يجب أن يُرفض (الدليل محمي)."""
    p = Path(__file__).resolve().parents[{DEPTH}] / "data" / "keys" / "keyring.json"
    p.write_text('{"keys": []}', encoding="utf-8")
'''

# اختبار يستبدل الملف ذريًا ثم يعيد الأصل (دون لمس الأذونات عمدًا —
# الاستبدال يحتاج كتابة على الدليل، والحماية يجب أن تمنعه)
_ATOMIC_REPLACE_TEST = r'''\
import os
from pathlib import Path


def test_atomic_replace_then_restore():
    """استبدال ذري (rename) ثم إعادة الأصل — يجب أن يُرفض الاول أصلًا."""
    p = Path(__file__).resolve().parents[{DEPTH}] / "data" / "keys" / "HISTORY.jsonl"
    # الملف البديل خارج data/keys المحمي — كي يُختبر رفض الاستبدال نفسه
    # (الكتابة على الدليل) لا رفض إنشاء البديل داخل الدليل المحمي
    tmp = Path(__file__).resolve().parent / "replacement.jsonl"
    original = p.read_bytes()
    tmp.write_bytes(original + b'{"probe": "replace"}' + bytes([10]))
    os.replace(tmp, p)
    p.write_bytes(original)  # استعادة الأصل — التغيير العابر يجب ألا يمر أصلًا
'''

# اختبار داخل الجلسة يفحص وضع الملف أثناء الحماية: إزالة بتات الكتابة فقط
# دون توسيع القراءة (0600 → 0400، وليس 0444 الذي يضيف قراءة للجماعة/الآخرين)
_MODE_DURING_SESSION_TEST = '''\
import stat
from pathlib import Path


def test_protected_mode_during_session():
    p = Path(__file__).resolve().parents[{DEPTH}] / "data" / "keys" / "keyring.json"
    mode = stat.S_IMODE(p.stat().st_mode)
    # 0600 الأصل: أثناء الحماية يجب 0400 (بلا كتابة وبلا قراءة موسعة)
    assert mode == 0o400, f"الوضع أثناء الجلسة {oct(mode)} — المتوقع 0o400 (إزالة الكتابة فقط، لا توسيع القراءة)"
'''


def test_absent_keyring_creation_is_rejected(tmp_path):
    """إنشاء keyring.json الغائب (عند التنفيذ) يجب أن يُرفض — الدليل نفسه محمي.

    قبل الإصلاح: الحماية تجاهلت الملف الغائب والدليل قابل للكتابة —
    الإنشاء ينجح بصمت والبصمة اللاحقة تعده أصلًا (فجوة).
    """
    replica = _build_tests_tree_replica(tmp_path / "replica")
    # لا keyring.json في الهيكل (كما في clone نظيف)
    assert not (replica / "data" / "keys" / "keyring.json").exists()
    (replica / "tests" / "test_pollute.py").write_text(
        _CREATE_ABSENT_KEYRING_TEST.replace("{DEPTH}", "1"), encoding="utf-8"
    )
    rc, output = _run_session(replica, "tests/test_pollute.py")

    assert rc != 0, (
        "فجوة: إنشاء keyring.json في data/keys نجح — الحماية يجب أن تشمل "
        "الدليل نفسه (الإنشاء والاستبدال والحذف كتابة على الدليل)"
    )
    assert "PermissionError" in output
    assert not (replica / "data" / "keys" / "keyring.json").exists(), (
        "الإنشاء يجب أن يُمنع فعليًا — لا مجرد اكتشافه لاحقًا"
    )


def test_atomic_replace_is_rejected(tmp_path):
    """الاستبدال الذري للملف المحمي (ثم استعادة الأصل) يجب أن يُرفض.

    قبل الإصلاح: الملف 444 لكن الدليل قابل للكتابة — os.replace ينجح،
    والاستعادة تخفي الأثر كاملًا من مقارنة الحالة النهائية (فجوة).
    """
    replica = _build_tests_tree_replica(tmp_path / "replica")
    (replica / "tests" / "test_pollute.py").write_text(
        _ATOMIC_REPLACE_TEST.replace("{DEPTH}", "1"), encoding="utf-8"
    )
    rc, output = _run_session(replica, "tests/test_pollute.py")

    assert rc != 0, (
        "فجوة: الاستبدال الذري للملف المحمي نجح — كتابة الدليل يجب أن تكون ممنوعة"
    )
    assert "PermissionError" in output
    # لا أثر ولا ملف مؤقت متبقٍ
    assert (replica / "data" / "keys" / "HISTORY.jsonl").read_text(
        encoding="utf-8"
    ) == "\n".join(_REAL_LINES) + "\n"
    assert not (replica / "data" / "keys" / "HISTORY.tmp").exists()


def test_protection_does_not_widen_read_permissions(tmp_path):
    """الحماية تزيل بتات الكتابة فقط — لا توسّع القراءة أبدًا.

    قبل الإصلاح: chmod 0o444 على ملف وضعه 0600 أضاف قراءة للجماعة
    والآخرين (توسيع أمني فعلي — اعتراض المراجع المانع).
    """
    replica = _build_tests_tree_replica(tmp_path / "replica")
    keyring = replica / "data" / "keys" / "keyring.json"
    keyring.write_text('{"keys": []}', encoding="utf-8")
    import os as _os
    _os.chmod(keyring, 0o600)  # مادة مفاتيح نموذجية: قراءة للمالك فقط
    (replica / "tests" / "test_mode.py").write_text(
        _MODE_DURING_SESSION_TEST.replace("{DEPTH}", "1"), encoding="utf-8"
    )
    rc, output = _run_session(replica, "tests/test_mode.py")

    assert rc == 0, f"اختبار الوضع داخل الجلسة فشل: {output}"
    # وبعد الجلسة: العودة إلى 0600 الأصلية بالضبط
    import stat as _stat
    after = _stat.S_IMODE(_os.stat(keyring).st_mode)
    assert after == 0o600, (
        f"الوضع الأصلي لم يُستعد: {oct(after)} — المتوقع 0o600"
    )


def test_collect_only_run_restores_modes(tmp_path):
    """--collect-only لا يشغل fixtures — الاستعادة يجب أن تعمل رغم ذلك.

    قبل الإصلاح: الاستعادة كانت داخل fixture التصفية — تجميع فقط يترك
    الملفات للقراءة فقط بعد انتهاء الأمر (فجوة تنظيف).
    """
    import os as _os
    import stat as _stat

    replica = _build_tests_tree_replica(tmp_path / "replica")
    (replica / "tests" / "test_clean.py").write_text(_CLEAN_TEST, encoding="utf-8")
    history = replica / "data" / "keys" / "HISTORY.jsonl"
    before_mode = _stat.S_IMODE(_os.stat(history).st_mode)
    proc_rc = None
    import subprocess as _sp
    import sys as _sys
    proc = _sp.run(
        [_sys.executable, "-m", "pytest", "-q", "--collect-only", "-p", "no:cacheprovider", "tests/test_clean.py"],
        cwd=str(replica), capture_output=True, text=True, timeout=120,
    )
    after_mode = _stat.S_IMODE(_os.stat(history).st_mode)
    assert after_mode == before_mode, (
        f"وضع الملف بعد --collect-only لم يُستعد: {oct(before_mode)} ← {oct(after_mode)} "
        "(التنظيف يجب أن يعمل بعمر الجلسة، لا بعمر fixtures)"
    )
    assert proc.returncode == 0, f"جلسة جمع سليمة فشلت: {proc.stdout + proc.stderr}"


def test_both_trees_session_restores_modes(tmp_path):
    """الجلستان معًا (tests/ + backend/tests/) — الاستعادة تعمل بالحارسين.

    انحدار خلل الحارسين (كلٌّ سجل وضع الآخر «أصلًا») — يغطي الاستدعاء
    القياسي للشجرتين معًا، لا شجرة واحدة.
    """
    import os as _os
    import stat as _stat

    replica = _build_tests_tree_replica(tmp_path / "replica")
    # شجرة backend/tests/ في الهيكل نفسه (conftest الحقيقي منسوخ أصلًا مع backend/)
    bt = replica / "backend" / "tests" / "invariants"
    bt.mkdir(parents=True, exist_ok=True)
    (bt / "test_clean_backend.py").write_text(_CLEAN_TEST, encoding="utf-8")
    (replica / "tests" / "test_clean.py").write_text(_CLEAN_TEST, encoding="utf-8")
    history = replica / "data" / "keys" / "HISTORY.jsonl"
    before_mode = _stat.S_IMODE(_os.stat(history).st_mode)

    rc, output = _run_session(replica, ["tests/test_clean.py", "backend/tests/invariants/test_clean_backend.py"])
    assert rc == 0, f"جلسة سليمة بالشجرتين فشلت: {output}"

    after_mode = _stat.S_IMODE(_os.stat(history).st_mode)
    assert after_mode == before_mode, (
        f"وضع الملف بعد جلسة الشجرتين لم يُستعد: {oct(before_mode)} ← {oct(after_mode)}"
    )


_CREATE_ABSENT_KEYRING_AT_IMPORT_TEST = '''\
from pathlib import Path

# إنشاء keyring.json عند الاستيراد (أثناء التجميع — قبل أي fixture) —
# يجب أن يُرفض حتى هنا: الحماية عند تحميل conftest، وهي أسبق من استيراد
# أي ملف اختبار
_p = Path(__file__).resolve().parents[{DEPTH}] / "data" / "keys" / "keyring.json"
_p.write_text('{"keys": []}', encoding="utf-8")


def test_import_time_creation():
    pass
'''


def test_absent_keyring_creation_at_import_is_rejected(tmp_path):
    """إنشاء keyring.json الغائب عند استيراد ملف الاختبار (خطأ تجميع) يجب
    أن يُرفض — مع استعادة الأوضاع رغم فشل التجميع (مسار التنظيف الأصعب).

    يغطي أيضًا مسار إخفاق التجميع: الحارس يستعيد الأوضاع عبر عمر الجلسة
    حتى حين لا يشغل أي fixture.
    """
    import os as _os
    import stat as _stat

    replica = _build_tests_tree_replica(tmp_path / "replica")
    assert not (replica / "data" / "keys" / "keyring.json").exists()
    history = replica / "data" / "keys" / "HISTORY.jsonl"
    dir_before = _stat.S_IMODE(_os.stat(replica / "data" / "keys").st_mode)
    file_before = _stat.S_IMODE(_os.stat(history).st_mode)
    (replica / "tests" / "test_pollute.py").write_text(
        _CREATE_ABSENT_KEYRING_AT_IMPORT_TEST.replace("{DEPTH}", "1"),
        encoding="utf-8",
    )
    rc, output = _run_session(replica, "tests/test_pollute.py")

    assert rc != 0, "الإنشاء عند الاستيراد يجب أن يُرفض (خطأ تجميع صريح)"
    assert "PermissionError" in output
    assert "keyring.json" in output
    assert not (replica / "data" / "keys" / "keyring.json").exists(), (
        "الإنشاء يجب أن يُمنع فعليًا حتى عند الاستيراد"
    )
    # استعادة الأوضاع رغم خطأ التجميع — التنظيف بعمر الجلسة
    assert _stat.S_IMODE(_os.stat(replica / "data" / "keys").st_mode) == dir_before, (
        "وضع الدليل لم يُستعد بعد خطأ التجميع"
    )
    assert _stat.S_IMODE(_os.stat(history).st_mode) == file_before, (
        "وضع الملف لم يُستعد بعد خطأ التجميع"
    )


def test_violations_names_appended_line_textually(tmp_path):
    """الإضافة (واقعة R-621 نفسها) — الانتهاك يذكر الملف والسطر المضاف نصًا."""
    from _real_keys_guard import snapshot, violations

    _make_history(tmp_path)
    history = tmp_path / "data" / "keys" / "HISTORY.jsonl"
    before = snapshot(tmp_path)
    with history.open("a", encoding="utf-8") as f:
        f.write(_POLLUTION_LINE + "\n")

    found = violations(tmp_path, before)
    assert len(found) == 1, f"انتهاك واحد متوقع (HISTORY فقط)، وُجد: {found}"
    assert "HISTORY.jsonl" in found[0], "الانتهاك يجب أن يسمي الملف"
    assert _POLLUTION_LINE in found[0], (
        "الانتهاك يجب أن يذكر السطر المضاف نصًا كاملًا — لا رقمًا مجردًا"
    )


def test_violations_empty_when_unchanged(tmp_path):
    """الحالة المطابقة — لا انتهاكات (المسار السليم للدالة)."""
    from _real_keys_guard import snapshot, violations

    _make_history(tmp_path)
    (tmp_path / "data" / "keys" / "keyring.json").write_text(
        '{"keys": []}', encoding="utf-8"
    )
    before = snapshot(tmp_path)
    assert violations(tmp_path, before) == [], "لا فرق — لا انتهاكات"


def test_violations_describe_deletion_and_creation(tmp_path):
    """الحذف والإنشاء — انتهاكان موصوفان، لا صمت ولا ابتلاع."""
    from _real_keys_guard import snapshot, violations

    _make_history(tmp_path)
    history = tmp_path / "data" / "keys" / "HISTORY.jsonl"
    before = snapshot(tmp_path)
    history.unlink()
    found = violations(tmp_path, before)
    assert len(found) == 1
    assert "حُذف" in found[0], "الانتهاك يجب أن يصف الحذف"

    before2 = snapshot(tmp_path)  # HISTORY الآن غائب
    _make_history(tmp_path)
    found2 = violations(tmp_path, before2)
    assert len(found2) == 1
    assert "أُنشئ" in found2[0], "الانتهاك يجب أن يصف الإنشاء"


def test_violations_never_quote_keyring_content(tmp_path):
    """تغيير keyring.json — الانتهاك يوصف ببصمة SHA-256 فقط، والمحتوى
    (مادة المفاتيح) لا يظهر نصًا أبدًا."""
    from _real_keys_guard import snapshot, violations

    _make_history(tmp_path)
    keyring = tmp_path / "data" / "keys" / "keyring.json"
    keyring.write_text(
        '{"keys": [{"key_id": "old", "private_key": "' + _FAKE_KEY_B + '"}]}',
        encoding="utf-8",
    )
    before = snapshot(tmp_path)
    keyring.write_text(
        '{"keys": [{"key_id": "new", "private_key": "' + _FAKE_KEY_A + '"}]}',
        encoding="utf-8",
    )

    found = violations(tmp_path, before)
    assert len(found) == 1
    assert "keyring.json" in found[0]
    assert _FAKE_KEY_A not in found[0], "تسريب: مادة المفتاح الجديد في الرسالة"
    assert _FAKE_KEY_B not in found[0], "تسريب: مادة المفتاح القديم في الرسالة"
    assert "بصمة" in found[0], "الوصف يجب أن يكون ببصمة آمنة لا بمحتوى"
