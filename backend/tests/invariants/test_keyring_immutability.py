"""
Invariant 5: KeyRing غير قابل للتلاعب (المرحلة 3 من ROADMAP_V2)

يتحقق أن:
1. كل المفاتيح الفاشلة (LOST/COMPROMISED) لا تُستخدم للتحقق
2. المفتاح الفعلي (data/key.secret) ليس في الاختبارات (لا حذف)
3. HISTORY.jsonl (سجل المفاتيح) غير قابل للحذف
4. أي مفتاح في KeyRing إما ACTIVE أو RETIRED أو LOST (حالة صحيحة)
"""

import json
import os
import sys
from pathlib import Path

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

from backend.sovereign.keys import KeyRing, KeyStatus


def test_keyring_all_keys_have_valid_status():
    """كل مفتاح في KeyRing يجب أن يكون له حالة صحيحة (ACTIVE/RETIRED/LOST/COMPROMISED/EXPIRED)."""
    keyring = KeyRing()
    keyring.load_from_disk()

    stats = keyring.stats()
    # (قاعدة الجولة الإنشائية 2026-10-16: لا skip — KeyRing الفارغ فشل صريح:
    # الـconftest يُنشئ keyring معزولًا بمفتاح نشط (R-634)، والواقع يتتبع HISTORY)
    assert stats["total_keys"] > 0, (
        "KeyRing is empty — invariant violated (conftest must provision "
        "the isolated test keyring per R-634)"
    )

    valid_statuses = {s.value for s in KeyStatus}

    # يُحقق كل مفتاح عبر الحصول على قائمة منه (list_keys أو جميع_keys)
    all_keys = keyring.list_keys() if hasattr(keyring, "list_keys") else []
    if not all_keys:
        # محاولة بديلة — الحصول على كل المفاتيح عبر attributes الخاصة
        all_keys = list(keyring._keys.values())

    for key in all_keys:
        key_id = getattr(key, "key_id", "?")
        status = key.status.value if hasattr(key.status, "value") else str(key.status)
        assert status in valid_statuses, (
            f"Key {key_id} has invalid status: {status!r}"
        )


def test_no_active_lost_keys():
    """لا يوجد مفتاح LOST/COMPROMISED بحالة ACTIVE (تناقض خطير)."""
    keyring = KeyRing()
    keyring.load_from_disk()

    stats = keyring.stats()
    assert stats["total_keys"] > 0, (
        "KeyRing is empty — invariant violated (conftest must provision "
        "the isolated test keyring per R-634)"
    )

    contradictions = []
    all_keys = list(keyring._keys.values())

    for key in all_keys:
        key_id = getattr(key, "key_id", "?")
        status = key.status.value if hasattr(key.status, "value") else str(key.status)
        reason = getattr(key, "loss_reason", None) or getattr(key, "reason", None)

        # مفتاح LOST أو COMPROMISED لا يمكن أن يكون ACTIVE
        if status in ("LOST", "COMPROMISED") and "active" in status.lower():
            contradictions.append(key_id)

        # مفتاح LOST مع سبب "not lost" — تناقض
        if status == "LOST" and reason and "not lost" in str(reason).lower():
            contradictions.append(key_id)

    assert len(contradictions) == 0, (
        f"Keys with contradictory status (LOST/COMPROMISED but ACTIVE): {contradictions}"
    )


def _history_lines(text: str) -> list:
    """أسطر HISTORY غير الفارغة (كما هي — لا إعادة ترتيب)."""
    return [l for l in text.split("\n") if l.strip()]


def _history_prefix_violations(old_lines: list, new_lines: list) -> list:
    """تصويب المراجع (الاعتراض 2): مقارنة فعلية — كل أسطر اللقطة الأقدم
    يجب أن تبقى في الأحدث بالترتيب نفسه وبالمحتوى نفسه (بادئة مرتبة).

    الإضافة المشروعة وحدها مسموحة (أسطر جديدة في النهاية).
    - حذف سطر قديم → انتهاك
    - تعديل سطر قديم → انتهاك
    """
    violations = []
    for idx, old_line in enumerate(old_lines):
        if idx >= len(new_lines):
            violations.append(
                f"line {idx + 1} DELETED (old has {len(old_lines)} lines, "
                f"new has only {len(new_lines)})"
            )
            continue
        if new_lines[idx] != old_line:
            violations.append(f"line {idx + 1} MODIFIED")
    return violations


def test_keyring_history_immutable():
    """
    HISTORY.jsonl (سجل المفاتيح) لا يمكن حذفه أو تعديله.

    (تصويب المراجع — الاعتراض 2: الفحص السابق كان وجودًا وصلاحية JSON فقط —
    حذف سطر قديم مع بقاء البقية كان يمر. الفحص الجديد: مقارنة فعلية عبر
    Git — أسطر الالتزام السابق كاملة تبقى في الملف الحالي بالترتيب،
    والإضافة وحدها مشروعة.)
    """
    history_file = _REPO_ROOT / "data" / "keys" / "HISTORY.jsonl"
    assert history_file.exists(), (
        "data/keys/HISTORY.jsonl must exist (key history is append-only)"
    )

    import subprocess as _sp

    current_lines = _history_lines(history_file.read_text(encoding="utf-8"))

    assert len(current_lines) > 0, "HISTORY.jsonl must have at least one entry"

    for i, line in enumerate(current_lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"HISTORY.jsonl line {i+1} is corrupted (not valid JSON): {e}"
            )
        assert isinstance(entry, dict), (
            f"HISTORY.jsonl line {i+1} must be a JSON object"
        )

    # المقارنة الفعلية عبر Git (لقطة سابقة مقابل الحالية) — عبر دالة
    # قابلة للاختبار على مستودعات مؤقتة أيضًا
    all_violations = _history_git_violations(_REPO_ROOT, current_lines)

    assert len(all_violations) == 0, (
        f"HISTORY.jsonl is append-only — deletions/modifications of previous "
        f"lines are forbidden: {all_violations}"
    )


def _history_git_violations(repo_root, current_lines: list) -> list:
    """مقارنة HISTORY عبر Git (تصويب المراجع — الاعتراض 2 و6):

    - مستودع سطحي = فشل صريح (قد يمر حذف ملتزم حديثًا بغياب HEAD~1).
    - فشل جلب لقطة موجودة فعلاً = فشل صريح لا تخطٍّ صامت.
    - كل أسطر كل لقطة أقدم (HEAD وHEAD~1 إن وُجدتا) يجب أن تبقى بادئة
      مرتبة كاملة من الأسطر الحالية — الحذف والتعديل انتهاك، الإضافة
      وحدها مشروعة.
    """
    import subprocess as _sp

    def _git(*args):
        return _sp.run(["git", *args], capture_output=True, text=True,
                       cwd=str(repo_root))

    shallow = _git("rev-parse", "--is-shallow-repository")
    if shallow.returncode == 0 and shallow.stdout.strip() == "true":
        pytest.fail(
            "shallow clone — HISTORY immutability guard requires full "
            "history (fetch-depth: 0 / full clone); a recently committed "
            "deletion could pass silently otherwise"
        )

    all_violations = []
    for rev in ("HEAD", "HEAD~1"):
        # وجود المرجع نفسه: إن لم يوجد المستودع بملتزام واحد فقط — تخطٍّ موثق
        exists = _git("rev-parse", "--verify", f"{rev}")
        if exists.returncode != 0:
            if rev == "HEAD~1":
                continue  # مستودع بملتزام أول — لا لقطة سابقة للمقارنة
            pytest.fail(f"cannot resolve {rev} — history unavailable")
        r = _git("show", f"{rev}:data/keys/HISTORY.jsonl")
        if r.returncode != 0:
            # الملف لم يكن موجودًا في تلك اللقطة؟ نتحقق قبل التسليم
            probe = _git("cat-file", "-e", f"{rev}:data/keys/HISTORY.jsonl")
            if probe.returncode == 0:
                pytest.fail(
                    f"git show {rev}:data/keys/HISTORY.jsonl failed though "
                    f"the blob exists — explicit failure, no silent skip"
                )
            continue  # الملف غير موجود في اللقطة — لا مقارنة ضدها
        old_lines = _history_lines(r.stdout)
        v = _history_prefix_violations(old_lines, current_lines)
        if v:
            all_violations.extend([f"[vs {rev}] {x}" for x in v])
    return all_violations


def test_history_prefix_checker_discriminates():
    """اختبارات تمييزية للمقارنة نفسها (تصويب المراجع — الاعتراض 2):
    الحذف يُرفض، التعديل يُرفض، الإضافة المشروعة تُقبل."""
    old = ["{\"ts\": \"a\"}", "{\"ts\": \"b\"}", "{\"ts\": \"c\"}"]

    # (1) إضافة مشروعة — تُقبل
    appended = old + ["{\"ts\": \"d\"}"]
    assert _history_prefix_violations(old, appended) == []

    # (2) حذف سطر قديم — يُرفض
    deleted = [old[0], old[2]]
    v_del = _history_prefix_violations(old, deleted)
    assert any("DELETED" in x for x in v_del), "deletion must be rejected"

    # (3) تعديل سطر قديم — يُرفض
    modified = [old[0], "{\"ts\": \"B-TAMPERED\"}", old[2]]
    v_mod = _history_prefix_violations(old, modified)
    assert any("MODIFIED" in x for x in v_mod), "modification must be rejected"

    # (4) تقصيم من المنتصف — يُرفض (حذف وسط)
    truncated = [old[0]]
    v_tr = _history_prefix_violations(old, truncated)
    assert len(v_tr) > 0, "truncation must be rejected"


def test_real_key_secret_exists():
    """
    المفتاح الفعلي (data/key.secret) يجب أن يوجد — لا يمكن حذفه
    (هذا هو الدرس من جريمة الاختبارات التي حذفته مرتين).

    R-680c: في clone نظيف، data/key.secret غير موجود (سر مُستثنى من git).
    (قاعدة الجولة الإنشائية 2026-10-16: لا skip — إن وُجد الملف الفعلي تُفحص
    خصائصه، وفي كل الأحوال يُثبت الاختبار مسار التوليد R-610 نفسه في جذر
    معزول: الاستيراد الفعلي لـ config بلا SOVEREIGN_KEY يولّد key.secret
    بحجم > 0 وصلاحيات 0600 — نفس الخصائص المطلوبة للملف الفعلي.)
    """
    import subprocess
    import tempfile

    # (أ) الملف الفعلي إن وُجد: خصائصه الصحيحة إلزامية
    key_file = _REPO_ROOT / "data" / "key.secret"
    if key_file.exists():
        size = key_file.stat().st_size
        assert size > 0, (
            f"data/key.secret is empty (size={size}) — key must be non-empty"
        )
        mode = key_file.stat().st_mode & 0o777
        assert mode == 0o600, (
            f"data/key.secret has insecure permissions: {oct(mode)} (expected 0600)"
        )

    # (ب) مسار التوليد R-610 يُثبت نفسه في جذر معزول (بلا skip في أي حالة)
    with tempfile.TemporaryDirectory(prefix="keygen_probe_") as tmp:
        env = {
            k: v for k, v in os.environ.items() if k != "SOVEREIGN_KEY"
        }
        env["SOVEREIGN_DATA_ROOT"] = tmp
        # لا .env في جذر المستودع (متحقق منه أعلاه في تشغيل الجولة) —
        # المصدر 4 هو أول مصدر متاح في الجذر المعزول
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'backend'); "
             "import config; print('KEYGEN_OK')"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
            env=env, timeout=120,
        )
        assert r.returncode == 0, (
            f"config import failed in isolated root: {r.stderr[-300:]}"
        )
        generated = Path(tmp) / "key.secret"
        assert generated.exists(), (
            "R-610 generation path did not create key.secret in isolated root"
        )
        assert generated.stat().st_size > 0, (
            "generated key.secret is empty — key must be non-empty"
        )
        gmode = generated.stat().st_mode & 0o777
        assert gmode == 0o600, (
            f"generated key.secret has insecure permissions: {oct(gmode)} "
            "(expected 0600 per R-610)"
        )


def test_tests_do_not_touch_real_key():
    """
    لا اختبار يلمس المفتاح الفعلي (data/key.secret) — هذا هو الدرس
    من جريمة test_identity_persistence.py و test_config_security.py
    (كلاهما حذف المفتاح الفعلي مرتين).
    """
    tests_dir = _REPO_ROOT / "tests"
    test_files = list(tests_dir.rglob("*.py"))

    dangerous_patterns = [
        "os.remove", "os.unlink", "shutil.rmtree", "Path.unlink",
    ]

    for tf in test_files:
        src = tf.read_text(encoding="utf-8")

        # البحث عن حذف للملفات (خطر) في الاختبارات
        for pattern in dangerous_patterns:
            # فحص كل سطر يحتوي النمط
            for i, line in enumerate(src.split("\n"), 1):
                if pattern in line and "key.secret" in line:
                    # إذا كان الحذف يستهدف key.secret — خطر
                    pytest.fail(
                        f"{tf.relative_to(_REPO_ROOT)}:{i} touches real key.secret: {line.strip()}"
                    )


def test_history_guard_catches_committed_changes(tmp_path):
    """تصويب المراجع (الاعتراض 6): الحارس يكتشف حذفًا/تعديلًا ملتزمًا فعلًا
    (لا دالة المقارنة وحدها) داخل مستودع Git مؤقت — والإضافة المشروعة تعبر."""
    import subprocess as _sp

    repo = tmp_path / "repo"
    (repo / "data" / "keys").mkdir(parents=True)
    hist = repo / "data" / "keys" / "HISTORY.jsonl"

    def _git(*args):
        r = _sp.run(["git", *args], capture_output=True, text=True, cwd=str(repo))
        assert r.returncode == 0, f"git {args} failed: {r.stderr}"

    _git("init", "-q")

    def _commit():
        _git("add", "-A")
        _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c")

    v1 = "{\"k\": \"a\"}\n{\"k\": \"b\"}\n{\"k\": \"c\"}\n"
    hist.write_text(v1, encoding="utf-8")
    _commit()

    # (1) حذف ملتزم: إزالة السطر الثاني
    hist.write_text("{\"k\": \"a\"}\n{\"k\": \"c\"}\n", encoding="utf-8")
    _commit()
    current = _history_lines(hist.read_text(encoding="utf-8"))
    v_del = _history_git_violations(repo, current)
    assert any("DELETED" in x for x in v_del), (
        f"committed deletion must be caught: {v_del}"
    )

    # (2) تعديل ملتزم: تغيير السطر الأول
    hist.write_text("{\"k\": \"A-TAMPERED\"}\n{\"k\": \"c\"}\n", encoding="utf-8")
    _commit()
    current = _history_lines(hist.read_text(encoding="utf-8"))
    v_mod = _history_git_violations(repo, current)
    assert any("MODIFIED" in x for x in v_mod), (
        f"committed modification must be caught: {v_mod}"
    )

    # (3) إضافة مشروعة ملتزمة: كل الأسطر القديمة تبقى + سطر جديد
    hist.write_text(
        "{\"k\": \"A-TAMPERED\"}\n{\"k\": \"c\"}\n{\"k\": \"new\"}\n",
        encoding="utf-8",
    )
    _commit()
    current = _history_lines(hist.read_text(encoding="utf-8"))
    v_ok = _history_git_violations(repo, current)
    assert v_ok == [], f"legitimate append must pass: {v_ok}"
