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

from backend.sovereign.keys import KeyRing, KeyRecord, KeyStatus


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


def _active_pointer_contradictions(keyring: KeyRing) -> list:
    """الجولة <2> (اعتراض المراجعين أمين وبصير): منطق فحص المؤشر النشط
    كمُساعد مشترك — يستخدمه الحارس الفعلي test_no_active_lost_keys
    والمسبار العدائي معًا، فلا يُختبر نسخة من المنطق بدل الحارس نفسه.

    الفحص القديم كان شرطًا ميتًا (status in ("LOST","COMPROMISED") and
    "active" in status.lower()) — مستحيل الحدوث لقيمة واحدة. الفحص الحقيقي
    المُكافئ للعقد: مؤشر المفتاح النشط لا يجوز أن يشير إلى مفتاح غير
    ACTIVE — المفتاح المفقود/المخترق لا يُوقّع ولا يُعاد كمفتاح نشط (R-633)."""
    contradictions = []
    all_keys = list(keyring._keys.values())

    active_id = keyring._active_key_id
    if active_id:
        active_rec = keyring._keys.get(active_id)
        if active_rec is None:
            contradictions.append(f"{active_id} (active_key_id dangling)")
        else:
            active_status = (
                active_rec.status.value
                if hasattr(active_rec.status, "value")
                else str(active_rec.status)
            )
            if active_status != "active":
                contradictions.append(
                    f"{active_id} (active_key_id → {active_status})"
                )

    # get_active_key لا يعيد أبدًا مفتاحًا غير ACTIVE (R-633)
    got_active = keyring.get_active_key()
    if got_active is not None:
        got_status = (
            got_active.status.value
            if hasattr(got_active.status, "value")
            else str(got_active.status)
        )
        if got_status != "active":
            contradictions.append(
                f"{got_active.key_id} (get_active_key returned {got_status})"
            )

    # إحصاء stats يجب أن يطابق الواقع — لا مفتاح مفقود/مخترق يُحسب نشطًا
    s = keyring.stats()
    expected_active = sum(
        1 for k in all_keys
        if (k.status.value if hasattr(k.status, "value") else str(k.status))
        == "active"
    )
    if s["active"] != expected_active:
        contradictions.append(
            f"stats()[active]={s['active']} != actual ACTIVE count "
            f"{expected_active}"
        )
    return contradictions


def test_no_active_lost_keys():
    """لا يوجد مفتاح LOST/COMPROMISED بحالة ACTIVE (تناقض خطير)."""
    keyring = KeyRing()
    keyring.load_from_disk()

    stats = keyring.stats()
    assert stats["total_keys"] > 0, (
        "KeyRing is empty — invariant violated (conftest must provision "
        "the isolated test keyring per R-634)"
    )

    contradictions = _active_pointer_contradictions(keyring)

    assert len(contradictions) == 0, (
        f"KeyRing contradictions (active pointer or active query pointing at "
        f"a non-ACTIVE key — a LOST/COMPROMISED key must never sign): "
        f"{contradictions}"
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


# الجولة <2> — قرار المالك R2-2: حد الجدّ (grandfathered boundary).
# الالتزام a90b481 (إغلاق الجولة <1>) هو نقطة بدء إنفاذ العقد الصارم —
# كل انتقال ابنه من نسله يُنفذ عليه الإلحاق بلا استثناء؛ ما قبله تاريخ
# أقدم من الحارس (واقعة إزالة التتبع ff8f80a→a4c3154 موثقة كاستثناء
# تاريخي بقرار المالك — لا تتكرر). إن لم يوجد حد الجدّ في المستودع
# (مستودع اختبار مؤقت) يُنفذ العقد كاملًا (لا جدّ).
_GUARD_BOUNDARY_SHA = "a90b4819e4ced24c2ce9ae68ae1b707a0a4709d6"


def _history_git_violations(repo_root, current_lines: list) -> list:
    """مقارنة HISTORY عبر Git (تصويب المراجع — الاعتراض 2 و6 + الجولة <2>):

    - مستودع سطحي = فشل صريح (قد يمر حذف ملتزم حديثًا بغياب HEAD~1).
    - فشل جلب لقطة موجودة فعلاً = فشل صريح لا تخطٍّ صامت.
    - الجولة <2> — إصلاح نجاحين زائفين (اعتراض المراجع أمين):
      (أ) الحذف أقدم من التزامين كان يمر (المقارنة ضد HEAD/HEAD~1 فقط).
      (ب) حذف-ثم-استعادة كان يمر (المقارنة ضد الحالة النهائية فقط).
    الحل: فحص الانتقالات الزمنية للأب←الابن عبر كل لقطات الملف — كل خطوة
    يجب أن تكون إلحاقًا خالصًا (الأب بادئة مرتبة كاملة للابن). الحذف
    انتهاك دائم حتى لو استُعيدت الأسطر لاحقًا، وحذف الملف كاملًا انتهاك
    صريح مسجل باسم «FILE DELETED». وأحدث لقطة تُقارن بشجرة العمل.
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

    # الجولة <2> (اعتراض المراجع بصير): انتقالات الأب/الابن الفعلية —
    # git log المتجاور ليس ضمان أبوّة، وتبسيط تاريخ الدمج قد يخفي فرعًا
    # كاملًا. نعدّد الالتزامات القابلة للوصول بلا تبسيط (--full-history)
    # مع آبائها الحقيقيين (rev-list --parents) ونفحص كل حافة أب←ابن:
    # الابن يجب أن يكون إلحاقًا خالصًا للأب. الوجود يُثبت من شجرة
    # الالتزام (ls-tree) لا من قابلية قراءة الكائن — تعذّرت القراءة مع
    # وجود المسار = فشل صريح لا تخطٍّ.
    rl = _git("rev-list", "--full-history", "--parents", "HEAD", "--",
             "data/keys/HISTORY.jsonl")
    if rl.returncode != 0:
        pytest.fail(f"git rev-list --parents for HISTORY.jsonl failed: {rl.stderr}")
    edges = []  # (child, parent) لكل أب فعلي لكل التزام لمس الملف
    seen_commits = set()
    for line in rl.stdout.split("\n"):
        parts = line.split()
        if not parts:
            continue
        child = parts[0]
        seen_commits.add(child)
        for parent in parts[1:]:
            edges.append((child, parent))
    if not seen_commits:
        pytest.fail(
            "no commits found touching HISTORY.jsonl — the file is tracked "
            "and must have at least one commit"
        )

    def _snapshot(sha):
        """لقطبة الملف في شجرة الالتزام — وجود من الشجرة، محتوى بالقراءة.
        يُعيد قائمة الأسطر أو None إن لم يكن الملف موجودًا في الشجرة."""
        tree = _git("ls-tree", sha, "--", "data/keys/HISTORY.jsonl")
        if tree.returncode != 0:
            pytest.fail(
                f"git ls-tree {sha} failed — explicit failure, no silent skip: "
                f"{tree.stderr}"
            )
        if not tree.stdout.strip():
            return None  # المسار غير موجود في شجرة هذا الالتزام
        show = _git("show", f"{sha}:data/keys/HISTORY.jsonl")
        if show.returncode != 0:
            pytest.fail(
                f"git show {sha}:data/keys/HISTORY.jsonl failed though ls-tree "
                f"confirms the path in the commit tree — explicit failure, "
                f"no silent skip: {show.stderr}"
            )
        return _history_lines(show.stdout)

    # وجود حد الجدّ في هذا المستودع؟ إن لم يوجد (مستودع اختبار مؤقت)
    # فلا جدّ — العقد يُنفذ كاملًا على كل التاريخ المتاح
    boundary_exists = _git("cat-file", "-e", _GUARD_BOUNDARY_SHA)
    grandfather = boundary_exists.returncode == 0

    def _is_grandfathered(child_sha: str) -> bool:
        """الابن حد الجدّ أو سلفه → تاريخ أقدم من الحارس (قرار R2-2)."""
        if not grandfather:
            return False
        r = _git("merge-base", "--is-ancestor", child_sha, _GUARD_BOUNDARY_SHA)
        return r.returncode == 0

    all_violations = []
    for child, parent in edges:
        if _is_grandfathered(child):
            continue  # قبل حد الجدّ — استثناء تاريخي موثق (R2-2)
        child_lines = _snapshot(child)
        parent_lines = _snapshot(parent)
        if child_lines is None:
            if parent_lines is not None:
                all_violations.append(
                    f"[{parent[:8]}→{child[:8]}] FILE DELETED — whole-file "
                    f"deletion is a permanent violation (append-only contract)"
                )
            continue
        if parent_lines is None:
            continue  # إنشاء الملف — مشروع
        v = _history_prefix_violations(parent_lines, child_lines)
        all_violations.extend([f"[{parent[:8]}→{child[:8]}] {x}" for x in v])

    # HEAD مقابل شجرة العمل — التغييرات غير الملتزمة تُكتشف فورًا
    head_lines = _snapshot("HEAD")
    if head_lines is not None:
        v = _history_prefix_violations(head_lines, current_lines)
        all_violations.extend([f"[vs HEAD] {x}" for x in v])
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
    """تصويب المراجع (الاعتراض 6) + الجولة <2>: الحارس يكتشف حذفًا/تعديلًا
    ملتزمًا فعلًا (لا دالة المقارنة وحدها) داخل مستودع Git مؤقت — والإضافة
    المشروعة تعبر.

    الجولة <2> — ملاحظة منهجية: التعديل الملتزم يبقى انتهاكًا دائمًا في
    التاريخ (كل لقطة أقدم تُقارن) — لذلك حالة الإلحاق المشروعة تُختبر في
    مستودع نظيف مستقل بلا انتهاكات سابقة، لا في تتابع بعد انتهاك مقصود."""
    import subprocess as _sp

    def _make_repo(base):
        repo = base / "repo"
        (repo / "data" / "keys").mkdir(parents=True)
        _sp.run(["git", "init", "-q"], cwd=str(repo), check=True)
        return repo

    def _commit(repo):
        _sp.run(["git", "add", "-A"], cwd=str(repo), check=True)
        _sp.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                "commit", "-q", "-m", "c"], cwd=str(repo), check=True)

    # (1) حذف ملتزم: إزالة السطر الثاني
    repo = _make_repo(tmp_path / "del")
    hist = repo / "data" / "keys" / "HISTORY.jsonl"
    hist.write_text('{"k": "a"}\n{"k": "b"}\n{"k": "c"}\n', encoding="utf-8")
    _commit(repo)
    hist.write_text('{"k": "a"}\n{"k": "c"}\n', encoding="utf-8")
    _commit(repo)
    current = _history_lines(hist.read_text(encoding="utf-8"))
    v_del = _history_git_violations(repo, current)
    assert any("DELETED" in x for x in v_del), (
        f"committed deletion must be caught: {v_del}"
    )

    # (2) تعديل ملتزم: تغيير السطر الأول
    repo = _make_repo(tmp_path / "mod")
    hist = repo / "data" / "keys" / "HISTORY.jsonl"
    hist.write_text('{"k": "a"}\n{"k": "b"}\n{"k": "c"}\n', encoding="utf-8")
    _commit(repo)
    hist.write_text('{"k": "A-TAMPERED"}\n{"k": "c"}\n', encoding="utf-8")
    _commit(repo)
    current = _history_lines(hist.read_text(encoding="utf-8"))
    v_mod = _history_git_violations(repo, current)
    assert any("MODIFIED" in x for x in v_mod), (
        f"committed modification must be caught: {v_mod}"
    )

    # (3) إلحاق مشروعة في مستودع نظيف: كل الأسطر القديمة تبقى + سطر جديد
    repo = _make_repo(tmp_path / "ok")
    hist = repo / "data" / "keys" / "HISTORY.jsonl"
    hist.write_text('{"k": "a"}\n{"k": "b"}\n', encoding="utf-8")
    _commit(repo)
    hist.write_text('{"k": "a"}\n{"k": "b"}\n{"k": "new"}\n', encoding="utf-8")
    _commit(repo)
    current = _history_lines(hist.read_text(encoding="utf-8"))
    v_ok = _history_git_violations(repo, current)
    assert v_ok == [], f"legitimate append must pass: {v_ok}"


def test_history_guard_catches_old_committed_deletion(tmp_path):
    """مسبار عدائي (الجولة <2>): حذف ملتزم قبل التزامين أو أكثر يجب ألا يمر.

    المقارنة السابقة كانت ضد HEAD وHEAD~1 فقط — حذف أقدم من ذلك كان يمر
    بصمت رغم أن العقد: HISTORY سجل إلحاقي لا يُحذف أبدًا. الإثبات: مستودع
    مؤقت — لقطة سليمة، حذف ملتزم، التزامان إضافيان لا يمسان الملف، ثم
    فحص انتهاكات: يجب أن يُكتشف الحذف القديم (لا أن يُقبل)."""
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

    # لقطة سليمة (3 أسطر)
    hist.write_text('{"k": "a"}\n{"k": "b"}\n{"k": "c"}\n', encoding="utf-8")
    _commit()
    # حذف السطر الثاني — ملتزم
    hist.write_text('{"k": "a"}\n{"k": "c"}\n', encoding="utf-8")
    _commit()
    # التزامان إضافيان لا يمسان HISTORY — الحذف صار أقدم من HEAD~1
    (repo / "x.txt").write_text("1", encoding="utf-8")
    _commit()
    (repo / "x.txt").write_text("2", encoding="utf-8")
    _commit()

    current = _history_lines(hist.read_text(encoding="utf-8"))
    violations = _history_git_violations(repo, current)
    assert any("DELETED" in v for v in violations), (
        f"deletion committed 3 commits ago must be caught — the invariant is "
        f"append-only FOREVER, not just vs HEAD/HEAD~1. Got: {violations}"
    )


def test_history_guard_catches_delete_then_restore(tmp_path):
    """مسبار عدائي (الجولة <2> — اعتراض المراجع أمين): حذف-ثم-استعادة يجب
    ألا يمر.

    المقارنة ضد الحالة النهائية وحدها كانت تقبل تاريخًا احتوى حذفًا فعليًا
    إذا استُعيدت الأسطر لاحقًا (كل اللقطات القديمة تبقى بادئات للنهائي).
    العقد: الإلحاق فقط في كل خطوة زمنية — الحذف انتهاك دائم حتى لو استُعيد.
    الإثبات: [a,b] ← [a] (حذف ملتزم) ← [a,b] (استعادة ملتزمة) — الحارس
    يجب أن يكشف انتهاك الانتقال، لا أن يقبل التاريخ كله."""
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

    # لقطة سليمة ثم حذف ملتزم ثم استعادة ملتزمة
    hist.write_text('{"k": "a"}\n{"k": "b"}\n', encoding="utf-8")
    _commit()
    hist.write_text('{"k": "a"}\n', encoding="utf-8")
    _commit()
    hist.write_text('{"k": "a"}\n{"k": "b"}\n', encoding="utf-8")
    _commit()

    current = _history_lines(hist.read_text(encoding="utf-8"))
    violations = _history_git_violations(repo, current)
    assert any("DELETED" in v for v in violations), (
        f"delete-then-restore must be caught as a permanent violation — "
        f"append-only is required at EVERY step, not just vs the final "
        f"state. Got: {violations}"
    )


def test_history_guard_catches_whole_file_deletion(tmp_path):
    """مسبار عدائي (الجولة <2> — اعتراض المراجع أمين): حذف الملف كاملًا ثم
    إعادة إنشائه بالمحتوى نفسه يجب ألا يمر كأن شيئًا لم يكن.

    في المقارنة السابقة، لقطات الالتزامات التي حذفت الملف كانت تُتخطى بصمت
    (فشل git show ← تخطٍّ) — فحذف الملف كاملًا ثم استعادته يمر. الحارس يجب
    أن يسجل انتهاك حذف عند الانتقال من لقطة فيها الملف إلى لقطة بلا ملف."""
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

    # إنشاء ← حذف كامل ملتزم ← إعادة إنشاء بنفس المحتوى
    content = '{"k": "a"}\n{"k": "b"}\n'
    hist.write_text(content, encoding="utf-8")
    _commit()
    hist.unlink()
    _commit()
    hist.write_text(content, encoding="utf-8")
    _commit()

    current = _history_lines(hist.read_text(encoding="utf-8"))
    violations = _history_git_violations(repo, current)
    assert any("DELETED" in v or "FILE DELETED" in v for v in violations), (
        f"whole-file deletion must be caught — restoring identical content "
        f"must not erase the violation from history. Got: {violations}"
    )


def test_no_active_lost_keys_catches_bad_active_pointer(tmp_path):
    """مسبار عدائي (الجولة <2> — اعتراض المراجع أمين): إصلاح الشرط الميت
    في test_no_active_lost_keys يحتاج RED خاصًا به — الحارس القديم كان يقبل
    مؤشرًا نشطًا يشير إلى مفتاح مفقود (الشرط القديم مستحيل الحدوث بطبيعته).

    الإثبات هنا مزدوج: (1) الشرط القديم نفسه لا يكشف الحالة السيئة (RED
    موثق بالتشغيل)، (2) الفحص الجديد يكشفها (GREEN). نبني KeyRing في الذاكرة
    بمؤشر نشط يشير إلى مفتاح LOST ثم نطبق منطق الفحصين."""
    keyring = KeyRing()
    # مفتاحان: واحد ACTIVE وواحد LOST — والمؤشر النشط يشير إلى المفقود
    import time as _time
    rec_active = KeyRecord(
        key_id="k-active", public_key="pub1", private_key="priv1",
        status=KeyStatus.ACTIVE, valid_from="2026-01-01T00:00:00Z",
        valid_until=None,
    )
    rec_lost = KeyRecord(
        key_id="k-lost", public_key="pub2", private_key="priv2",
        status=KeyStatus.LOST, valid_from="2026-01-01T00:00:00Z",
        valid_until=None,
    )
    keyring._keys = {"k-active": rec_active, "k-lost": rec_lost}
    keyring._active_key_id = "k-lost"  # الحالة السيئة: المؤشر يشير للمفقود

    # (1) RED الموثق: الشرط القديم الميت لا يكشف شيئًا أبدًا
    old_condition_detected = False
    for key in keyring._keys.values():
        status = key.status.value
        if status in ("LOST", "COMPROMISED") and "active" in status.lower():
            old_condition_detected = True
    assert not old_condition_detected, (
        "the OLD dead condition could never fire (a single status value is "
        "never both LOST/COMPROMISED and contains 'active') — if it fires, "
        "this documentation test is wrong"
    )

    # (2) GREEN: الفحص الجديد يكشف الحالة السيئة — عبر المساعد المشترك
    # نفسه الذي يستخدمه الحارس الفعلي test_no_active_lost_keys (لا نسخة)
    contradictions = _active_pointer_contradictions(keyring)
    assert contradictions == ["k-lost (active_key_id → lost)"], (
        f"new check must flag the bad active pointer: {contradictions}"
    )


def test_history_guard_catches_rewritten_same_count(tmp_path):
    """مسبار عدائي (الجولة <2> — اعتراض المراجع بصير): إعادة كتابة بنفس عدد
    الأسطر (تعديل بلا حذف ظاهر بالعدد) يجب أن تُكتشف — الحارس يقارن
    المحتوى لا العدد. [a,b] ← [x,y]: عدد الأسطر متطابق والمحتوى مغاير."""
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

    hist.write_text('{"k": "a"}\n{"k": "b"}\n', encoding="utf-8")
    _commit()
    # إعادة كتابة كاملة بنفس العدد — محتوى مغاير
    hist.write_text('{"k": "x"}\n{"k": "y"}\n', encoding="utf-8")
    _commit()

    current = _history_lines(hist.read_text(encoding="utf-8"))
    violations = _history_git_violations(repo, current)
    assert any("MODIFIED" in v for v in violations), (
        f"same-count rewrite must be caught as MODIFIED (content, not count, "
        f"is what the guard compares): {violations}"
    )


def test_history_guard_catches_branch_delete_with_merge(tmp_path):
    """مسبار عدائي (الجولة <2> — اعتراض المراجع بصير): حذف في فرع جانبي مع
    دمج --no-ff يجب ألا يختفي خلف تبسيط تاريخ المسار.

    السيناريو: الأساس [a,b] ← فرع جانبي يحذف b ثم يستعيد، الرئيسي يتقدم
    بملف غير ذي صلة، ثم دمج --no-ff والمحتوى النهائي يطابق الأساس. الحارس
    يجب أن يكشف انتهاك الحذف في الفرع رغم أن النتيجة النهائية سليمة —
    العقد إلحاقي في كل خطوة، والحذف انتهاك دائم حتى لو استُعيد."""
    import subprocess as _sp

    repo = tmp_path / "repo"
    (repo / "data" / "keys").mkdir(parents=True)
    hist = repo / "data" / "keys" / "HISTORY.jsonl"

    import os as _os
    _env = dict(_os.environ,
                GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def _git(*args):
        r = _sp.run(["git", *args], capture_output=True, text=True,
                    cwd=str(repo), env=_env)
        assert r.returncode == 0, f"git {args} failed: {r.stderr}"

    _git("init", "-q", "-b", "master")

    def _commit():
        _git("add", "-A")
        _git("commit", "-q", "-m", "c")

    hist.write_text('{"k": "a"}\n{"k": "b"}\n', encoding="utf-8")
    _commit()

    # فرع جانبي: حذف b ثم استعادته
    _git("checkout", "-q", "-b", "side")
    hist.write_text('{"k": "a"}\n', encoding="utf-8")
    _commit()
    hist.write_text('{"k": "a"}\n{"k": "b"}\n', encoding="utf-8")
    _commit()

    # الرئيسي: تقدم بملف غير ذي صلة
    _git("checkout", "-q", "master")
    (repo / "unrelated.txt").write_text("1", encoding="utf-8")
    _commit()

    # دمج --no-ff — المحتوى النهائي يطابق الأساس
    _git("merge", "--no-ff", "-q", "-m", "merge", "side")

    current = _history_lines(hist.read_text(encoding="utf-8"))
    assert current == ['{"k": "a"}', '{"k": "b"}'], (
        f"scenario setup: final content must equal base: {current}"
    )
    violations = _history_git_violations(repo, current)
    assert any("DELETED" in v for v in violations), (
        f"branch-side deletion must be caught despite --no-ff merge and "
        f"identical final content (full-history parent edges): {violations}"
    )


def test_active_pointer_red_green_on_real_guard():
    """مسبار RED→GREEN على الحارس الفعلي نفسه (الجولة <2> — اعتراضا
    المراجعين أمين وبصير وحكيم): إصلاح الشرط الميت في test_no_active_lost_keys
    يحتاج إثباتًا تعاقديًا — الحارس القديم (من الأساس a90b481) يُستدعى فعليًا
    ضد KeyRing سيئ فيقبل الحالة (RED المُشاهَد)، ثم الحارس الحالي يُستدعى
    ضد الحالة نفسها فيرفضها (GREEN المُشاهَد). لا نسخة من المنطق — الاستدعاء
    مباشر للدالتين الفعليتين: القديمة من مصدر الأساس عبر git، والجديدة
    من الوحدة المحملة."""
    import subprocess as _sp

    # الحالة السيئة: مؤشر نشط يشير إلى مفتاح LOST
    bad = KeyRing()
    rec_active = KeyRecord(
        key_id="k-active", public_key="pub1", private_key="priv1",
        status=KeyStatus.ACTIVE, valid_from="2026-01-01T00:00:00Z",
        valid_until=None,
    )
    rec_lost = KeyRecord(
        key_id="k-lost", public_key="pub2", private_key="priv2",
        status=KeyStatus.LOST, valid_from="2026-01-01T00:00:00Z",
        valid_until=None,
    )
    bad._keys = {"k-active": rec_active, "k-lost": rec_lost}
    bad._active_key_id = "k-lost"
    # الحارس يستدعي load_from_disk() — نجعلها no-op على الحالة المحقونة
    # حتى لا تمسحها بقراءة القرص (الحقن يبقى ساريًا للاستدعائين)
    bad.load_from_disk = lambda: None

    class _BadKeyRingFactory:
        """مصنع يعيد الحالة السيئة بدل قراءة القرص — حقن مباشر للحارس."""
        def __new__(cls, *args, **kwargs):
            return bad

    # (1) RED المُشاهَد: الحارس القديم نفسه (مصدر الأساس a90b481) يقبلها
    show = _sp.run(
        ["git", "show",
         "a90b481:backend/tests/invariants/test_keyring_immutability.py"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT),
    )
    assert show.returncode == 0, f"git show base source failed: {show.stderr}"
    old_src = show.stdout
    start = old_src.index("def test_no_active_lost_keys():")
    end = old_src.index("def _history_lines")
    old_func_src = old_src[start:end]
    ns = {"KeyRing": _BadKeyRingFactory}
    exec(compile(old_func_src, "<old guard from a90b481>", "exec"), ns)
    old_guard = ns["test_no_active_lost_keys"]
    old_guard()  # لا يرفع استثناءً — الحارس القديم قبل الحالة السيئة
    # لو وصل هنا: الحارس القديم قبل مؤشرًا نشطًا يشير إلى مفتاح LOST — RED

    # (2) GREEN المُشاهَد: الحارس الحالي نفسه يرفض الحالة نفسها
    import backend.tests.invariants.test_keyring_immutability as _mod
    original_keyring_cls = _mod.KeyRing
    _mod.KeyRing = _BadKeyRingFactory
    try:
        with pytest.raises(AssertionError) as excinfo:
            _mod.test_no_active_lost_keys()
        assert "k-lost" in str(excinfo.value), (
            f"current guard must name the lost key behind the active "
            f"pointer: {excinfo.value}"
        )
    finally:
        _mod.KeyRing = original_keyring_cls
