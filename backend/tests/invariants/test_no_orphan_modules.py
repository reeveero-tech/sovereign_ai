"""
Invariant 1: لا وحدات يتيمة (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل ملف .py في backend/ و guardian/ و nexus/ إما:
- مستدعى من ملف آخر (import)
- نقطة دخول معروفة (main, __init__, CLI)
- مُدرج في INVENTORY.py (أرشيف موثق)

إذا وُجد ملف يتيم جديد (غير مُدرج في الجرد الحالي)، الاختبار يفشل.
"""

import ast
import sys
from pathlib import Path

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

# نقاط الدخول المعروفة (ليست يتيمة)
KNOWN_ENTRY_POINTS = {
    "main.py",                       # نقطة تشغيل رئيسية
    "backend/app.py",               # تطبيق FastAPI (يُستورد من main و start.sh)
    "backend/config.py",            # إعدادات (يُستورد من app)
    "backend/Mr.py",                # محرك الولاء (يُستورد من اختبارات)
    "nexus/main.py",               # نقطة تشغيل nexus
    "start.sh",                     # سكربت تشغيل (ليس .py)
}

# الجولة <2> — إصلاح مصفّي واسع: نقاط دخول السكربتات اليدوية صارت قائمة
# صريحة قابلة للتدقيق — لا تعفوًا لكل scripts/ (أي سكربت جديد غير مستورد
# وغير مُدرج = يتيم يُكشف). القائمة القديمة كانت تخفي أي يتيم يُزرع هناك
# (مسبار عدائي مُثبت: test_guard_catches_stray_script).
SCRIPT_ENTRY_POINTS = {
    "scripts/verify_new_key.py",
    "scripts/verify_operational_auth.py",
}

# الجولة <2> (اعتراض المراجع بصير): ملفات تُحمّل ديناميكيًا عبر
# importlib.spec_from_file_location — الحافة الاستاتيكية غير مرئية
# لمحلل الاستيراد، فتُوثّق صراحة مع مواقع التحميل (قرار توثيقي لا إعفاء
# مجلد — أي ملف آخر يجب أن يكون مستوردًا استاتيكيًا).
DYNAMIC_LOADED_MODULES = {
    "tests/fixtures/synthetic_ledger.py": (
        "tests/test_ledger_anchor.py, tests/test_synthetic_fixture.py, "
        "backend/tests/invariants/test_no_unsigned_ledger_events.py "
        "(importlib.spec_from_file_location)"
    ),
}

# الملفات المسموح أن تكون أرشيفية (مُدرجة في INVENTORY.py)
ARCHIVED_FILES = {
    "archive/root_strays/encryption.py",
    "archive/root_strays/investigation.py",
    "archive/root_strays/IDs.js",
    "archive/root_strays/Fff.txt",
    "archive/root_strays/attached_assets_create1_prompt.txt",
    "archive/root_strays/attached_assets_create2_prompt.txt",
    "archive/root_strays/dockerignore_duplicate",
    "archive/root_strays/infrastructure_Dockerfile_empty",
    "archive/root_strays/infrastructure_requirements_empty",
    "archive/root_strays/INVENTORY.py",
}


def _get_live_python_files() -> list:
    """يُعيد كل ملفات Python الحية — الاستثناءات مثبتة بالمسار لا بسلسلة:

    الجولة <2> — إصلاح مصفّي واسع: الاستثناء السابق كان "أي مسار يحتوي
    السلسلة" فيخفي أي ملف يسمى نفسه بها (مسبار عدائي مُثبت:
    test_guard_catches_stray_named_like_backup). النطاق المشروع الوحيد هو
    شجرة النسخ الاحتياطية المؤجلة بأمر المالك — تُستثنى ببادئة مسار
    مثبتة، والـ__pycache__ و.git مقاطع مسار لا سلاسل."""
    def _is_excluded(rel: str) -> bool:
        parts = rel.split("/")
        if "__pycache__" in parts:
            return True
        if rel == ".git" or rel.startswith(".git/") or "/.git/" in rel:
            return True
        # النطاق المؤجل بأمر المالك (OWNER_REQUIRED البند ٤) — بادئة مثبتة
        if rel.startswith("guardian/data/emergency/"):
            return True
        return False

    live = []
    for p in _REPO_ROOT.rglob("*.py"):
        rel = str(p.relative_to(_REPO_ROOT))
        if _is_excluded(rel):
            continue
        live.append(rel)
    return sorted(live)


def _is_pytest_collectable(rel: str, live_files: list = None) -> bool:
    """الجولة <2> (اعتراض المراجع بصير): نقطة الدخول الاختبارية تُثبت بنمط
    جمع pytest الفعلي — لا إعفاء مجلد كامل. أي ملف آخر داخل مجلدات
    الاختبارات يجب أن يكون مستوردًا.

    conftest.py (R-682): يُعفى فقط إن كان في سلسلة أدلة ملف اختباري
    يجمعه pytest فعلًا (rootdir chain) — conftest شارد في دليل بلا اختبارات
    ليس نقطة دخول ويُكشف. «أي ملف آخر داخل مجلدات الاختبارات» يشمل
    غير المطابق لأنماط الجمع (test_*.py / *_test.py)."""
    name = Path(rel).name
    if name == "conftest.py":
        if live_files is None:
            return True  # توافق — الاستدعاءات الخارجية بلا قائمة الملفات
        d = str(Path(rel).parent)
        for f in live_files:
            fname = Path(f).name
            if f.startswith(d + "/") and (
                (fname.startswith("test_") and fname.endswith(".py"))
                or fname.endswith("_test.py")
            ):
                return True
        return False
    return (
        (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
    )


def _reachable_from_roots(live_files: list, imported_by: dict) -> set:
    """الجولة <2> (اعتراض المراجع بصير): تحليل الوصول من نقاط الدخول.

    الحارس السابق كان يقيس «له مستورِد» — فزوج ملفات يستورد أحدهما الآخر
    بلا أي نقطة وصول كان يُقبل. الوحدة الحية المشروعة يجب أن تكون قابلة
    للوصول من جذر معروف: نقطة دخول معلومة، أو ملف اختباري يجمعه pytest،
    أو conftest في سلسلة أدلة اختبار فعلية. الأرشيف الموثق ليس جذرًا.
    """
    roots = set()
    for f in live_files:
        if f in KNOWN_ENTRY_POINTS or f in SCRIPT_ENTRY_POINTS:
            roots.add(f)
        elif _is_pytest_collectable(f, live_files):
            roots.add(f)
    # عكس الخريطة: imported_by[target] = مستوردو target —
    # للوصول نحتاج حواف المستورد ← مستورداته (من يستورد من)
    imports_of = {}
    for target, importers in imported_by.items():
        for imp in importers:
            imports_of.setdefault(imp, []).append(target)
    reach = set()
    stack = list(roots)
    while stack:
        cur = stack.pop()
        if cur in reach:
            continue
        reach.add(cur)
        for target in imports_of.get(cur, []):
            if target not in reach:
                stack.append(target)
    return reach


def _build_import_graph(live_files: list) -> dict:
    """يبني خريطة الاستيراد (من يستورد من).

    الجولة <2> — إصلاح آلية إخفاء: المطابقة السابقة كانت تقبل أقصر لاحقة
    للاسم المستورد مع أي ملف يحمل الاسم — فأي استيراد من أي ملف يُصنّف
    يتيمًا بمثابة «مستورد» (مسبار عدائي مُثبت:
    test_guard_does_not_mark_orphan_imported_via_nonrelative_import).
    المطابقة الآن بالمسارات المحددة فقط:
    (1) المسار الكامل للاستيراد من جذر المستودع
    (2) المسار مسبوقًا بـ backend/ (الاستيراد من داخل backend بلا سابقة)
    (3) نسبي لمجلد المستورد — للاستيرادات النسبية الحقيقية فقط
        (ImportFrom بمستوى level >= 1) — لا غير النسبية أبدًا
    لا مطابقة لاحقة أقصر إطلاقًا: import a.b.c لا يُطابق c.py في أي مكان.
    """
    imported_by = {}
    live_set = set(live_files)

    def _try(path: str, importer: str) -> bool:
        """محاولة مطابقة مسار وحدة — وحدة أو حزمة (__init__.py).

        الجولة <2>: الاستيراد الحزمي (import a.b) يستهدف a/b/__init__.py
        إن لم تكن a/b.py وحدة — بدونه تنقطع سلاسل الوصول عند حدود الحزم
        ويظهر كل ملف داخل الحزم كيتيم زائف."""
        if path in live_set and path != importer:
            imported_by.setdefault(path, []).append(importer)
            return True
        pkg = path[:-3] + "/__init__.py"  # a/b.py → a/b/__init__.py
        if pkg in live_set and pkg != importer:
            imported_by.setdefault(pkg, []).append(importer)
            return True
        return False

    def _match(parts: tuple, importer: str, file_dir: str, allow_relative: bool):
        if allow_relative:
            # الجولة <2> (اعتراض المراجع أمين): الاستيراد النسبي يُحل في
            # نطاقه النسبي وحده — لا يُجرب المسار المطلق ولا سابقة backend/،
            # وإلا خُفي أي ملف جذري يشارك اسم وحدة مستوردة نسبيًا.
            if file_dir:
                _try(file_dir + "/" + "/".join(parts) + ".py", importer)
            return
        rel_path = "/".join(parts) + ".py"
        if _try(rel_path, importer):
            return
        if _try("backend/" + rel_path, importer):
            return
        # الجولة <2> (اعتراض المراجع بصير): حل مجاور لمجلد المستورد
        # (sys.path-adjacent — pytest يُدخل مجلد الاختبارات في sys.path):
        # الاستيراد بالاسم الكامل من مجلد المستورد. الاسم كامل لا لاحقة،
        # فلا يُخفي هذا الحل أي يتيم بعيد — مجرد مطابقة مسار نظام الاستيراد
        # الفعلي (from ci_run_selection import ... داخل tests/).
        if file_dir:
            _try(file_dir + "/" + rel_path, importer)

    for f in live_files:
        try:
            src = (_REPO_ROOT / f).read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            continue

        file_dir = str(Path(f).parent)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    _match(tuple(a.name.split(".")), f, file_dir,
                           allow_relative=False)
            elif isinstance(node, ast.ImportFrom):
                is_relative = (node.level or 0) >= 1
                # من مستوى أعلى (from .. import x): اتجاه المجلد الأعلى
                up_dir = file_dir
                if is_relative and node.level and node.level > 1:
                    for _ in range(node.level - 1):
                        up_dir = str(Path(up_dir).parent)
                if node.module:
                    _match(tuple(node.module.split(".")), f, up_dir,
                           allow_relative=is_relative)
                for a in node.names:
                    base = tuple(node.module.split(".")) if node.module else ()
                    _match(base + (a.name,), f, up_dir,
                           allow_relative=is_relative)

    return imported_by


def test_no_orphan_modules():
    """
    Invariant: كل ملف .py حي يجب أن يكون إما مستوردًا، نقطة دخول،
    أو مُدرجًا في الأرشيف الموثق (INVENTORY.py).
    """
    live_files = _get_live_python_files()
    imported_by = _build_import_graph(live_files)

    # الجولة <2> (اعتراض المراجع بصير): التحول من «له مستورِد» إلى
    # «قابل للوصول من جذر معروف» — نقطة دخول معلومة أو اختبار يجمعه
    # pytest أو conftest. زوج الاستيراد المتبادل المعزول صار يُكشف.
    reach = _reachable_from_roots(live_files, imported_by)

    orphans = []
    for f in live_files:
        if f in reach:
            continue  # قابل للوصول من جذر — ليس يتيمًا
        if f in KNOWN_ENTRY_POINTS or f in SCRIPT_ENTRY_POINTS:
            continue  # نقطة دخول معلومة (جذر في التحليل أيضًا)
        if f in DYNAMIC_LOADED_MODULES:
            continue  # تحميل ديناميكي موثق — الحافة معلنة صراحة
        if f in ARCHIVED_FILES:
            continue  # أرشيف موثق بالاسم — لا إعفاء مجلد كامل (الجولة <2>)
        if Path(f).name == "__init__.py":
            continue  # ملف حزمة Python بالاسم المطابق تمامًا
        orphans.append(f)

    # القاعدة: لا يتيم جديد (غير مُدرج في الأرشيف المعروف)
    # الملفات اليتيمة الموجودة حاليًا (قبل إصلاحها) — تُوثّق هنا
    # حتى لا نُفشل الاختبار قبل إصلاحها (سنجعلها تُصنّف بشكل متدرج)
    CURRENTLY_KNOWN_ORPHANS = {
        # هذه ملفات موجودة حاليًا لكنها غير مربوطة مباشرة (يتم إصلاحها تدريجيًا)
        # — الاختبار يفشل فقط إذا ظهر يتيم جديد
    }

    new_orphans = [o for o in orphans if o not in CURRENTLY_KNOWN_ORPHANS]

    if new_orphans:
        pytest.fail(
            f"Found {len(new_orphans)} NEW orphan modules (not imported, "
            f"not entry points, not archived). "
            f"Orphans: {new_orphans[:10]}..."
        )


def test_inventory_documented():
    """كل ملف في archive/ يجب أن يكون موثقًا في INVENTORY.py."""
    inventory_file = _REPO_ROOT / "archive" / "root_strays" / "INVENTORY.py"
    assert inventory_file.exists(), (
        "INVENTORY.py must exist to document archived files"
    )

    inventory_src = inventory_file.read_text(encoding="utf-8")

    # كل ملف في archive/ يجب أن يكون مذكورًا في INVENTORY
    archive_files = [
        str(p.relative_to(_REPO_ROOT))
        for p in (_REPO_ROOT / "archive").rglob("*")
        if p.is_file() and p.suffix in (".py", ".js", ".txt", "")
    ]
    for af in archive_files:
        if af.endswith("INVENTORY.py"):
            continue
        basename = Path(af).name
        assert basename in inventory_src, (
            f"Archived file {af!r} must be documented in INVENTORY.py"
        )


def test_guard_flags_stray_conftest_outside_root(tmp_path):
    """R-682 (الجولة التشغيلية الثالثة — أمر المستشار): اختبار سلوكي للحارس.

    ملف غير مستورد باسم conftest.py في مسار غير الجذر يجب ألا يفلت من
    الحارس بمجرد تسميته — الحارس لا يعفي الاسم، بل نموذج نقاط الدخول
    المعروف (وهذا سبب إلغاء استثناء الاسم العريض الذي أُدخل في 0c5143d).
    الإثبات: تشغيل الحارس نفسه كسب-بروسس مع ملف تجريبي موجود ثم بعد إزالته.
    """
    import shutil
    import subprocess

    probe_dir = _REPO_ROOT / "_orphan_probe_tmp"
    probe = probe_dir / "conftest.py"
    probe_dir.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        "# probe — stray conftest outside repo root; not loaded by pytest\n",
        encoding="utf-8",
    )
    cmd = [
        sys.executable, "-m", "pytest",
        "backend/tests/invariants/test_no_orphan_modules.py::test_no_orphan_modules",
        "-q", "--no-header",
    ]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(_REPO_ROOT), timeout=180,
        )
        # مع الملف اليتيم: الحارس يفشل ويذكره بالاسم والمسار
        assert r.returncode != 0, (
            "guard must FAIL while a stray conftest.py exists outside root"
        )
        assert "_orphan_probe_tmp/conftest.py" in r.stdout, (
            f"stray probe must be named in the failure output: {r.stdout[-300:]}"
        )
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)

    # بعد الإزالة: الحارس يعود أخضر (لا أثر للملف التجريبي)
    r2 = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(_REPO_ROOT), timeout=180,
    )
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )


# ============================================================
# الجولة <2> — مسبارات عدائية (RED قبل الإصلاح): ثلاث آليات
# إخفاء مُثبتة بالتشغيل — الحارس كان ينجح مع ملفات يتيمة مزروعة.
# ============================================================

def _run_orphan_guard():
    """تشغيل الحارس نفسه كسب-بروسس — الحقيقة ما يُقاس بالتشغيل لا بالقراءة."""
    import subprocess
    cmd = [
        sys.executable, "-m", "pytest",
        "backend/tests/invariants/test_no_orphan_modules.py::test_no_orphan_modules",
        "-q", "--no-header",
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(_REPO_ROOT), timeout=180,
    )


def test_guard_catches_stray_script():
    """مسبار عدائي (الجولة <2>): سكربت يتيم داخل scripts/ يجب ألا يُخفى.

    القاعدة السابقة كانت تعفي كل ما يبدأ بـ scripts/ — مصفٍّ واسع يخفي أي
    يتيم يُزرع هناك. الإثبات: زرع ملف غير مستورد داخل scripts/ ثم تشغيل
    الحارس — يجب أن يفشل ويذكره بالاسم والمسار."""
    probe = _REPO_ROOT / "scripts" / "_orphan_probe_stray_script.py"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("# stray orphan probe — not imported anywhere\n",
                     encoding="utf-8")
    try:
        r = _run_orphan_guard()
        assert r.returncode != 0, (
            "guard must FAIL while a stray unimported script exists in scripts/"
        )
        assert "_orphan_probe_stray_script.py" in r.stdout, (
            f"stray script must be named in failure output: {r.stdout[-300:]}"
        )
    finally:
        probe.unlink(missing_ok=True)
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )


def test_guard_catches_stray_named_like_backup():
    """مسبار عدائي (الجولة <2>): ملف يتيم يحتوي emergency_backups في مساره
    (خارج نطاق النسخ الاحتياطية المؤجل بأمر المالك) يجب ألا يُخفى.

    القاعدة السابقة استثنت أي مسار يحتوي السلسلة emergency_backups أينما
    وقعت — مصفٍّ واسع يخفي أي ملف يسمى نفسه بها. النطاق المشروع الوحيد
    هو شجرة guardian/data/emergency/ (بند مؤجل بأمر المالك)."""
    probe = _REPO_ROOT / "backend" / "_orphan_probe_emergency_backups_helper.py"
    probe.write_text("# stray orphan probe — name contains emergency_backups\n",
                    encoding="utf-8")
    try:
        r = _run_orphan_guard()
        assert r.returncode != 0, (
            "guard must FAIL while a stray file named like a backup exists "
            "outside the owner-deferred backup tree"
        )
        assert "_orphan_probe_emergency_backups_helper.py" in r.stdout, (
            f"stray must be named in failure output: {r.stdout[-300:]}"
        )
    finally:
        probe.unlink(missing_ok=True)
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )


def test_guard_does_not_mark_orphan_imported_via_nonrelative_import():
    """مسبار عدائي (الجولة <2>): استيراد غير نسبي (import a.b.c) لا يجعل
    ملفًا يتيمًا يشارك الاسم «مستوردًا».

    القاعدة السابقة قبلت مطابقة اللاحقة القصيرة للاستيراد مع أي ملف يحمل
    الاسم الأخير — آلية إخفاء: أي استيراد من أي ملف يُصنّف اليتم بمثابة
    مستورد. الإثبات: مستورد + وحدة يتيمة بنفس اسم استيراد غير موجود الهدف."""
    import shutil
    probe_dir = _REPO_ROOT / "_orphan_probe_suffix_tmp"
    probe_dir.mkdir(parents=True, exist_ok=True)
    importer = probe_dir / "importer_probe.py"
    orphan = probe_dir / "orphan_probe_module.py"
    importer.write_text("import guardian.orphan_probe_module\n",
                        encoding="utf-8")
    orphan.write_text("# orphan — must NOT be counted as imported\n",
                      encoding="utf-8")
    try:
        r = _run_orphan_guard()
        assert r.returncode != 0, (
            "guard must FAIL while an orphan matched only via a non-relative "
            "import suffix exists"
        )
        assert "orphan_probe_module.py" in r.stdout, (
            f"orphan must be named in failure output: {r.stdout[-300:]}"
        )
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )


def test_guard_relative_import_resolves_only_relative():
    """مسبار عدائي (الجولة <2> — اعتراض المراجع أمين): الاستيراد النسبي
    (from . import target) يجب أن يُحل في نطاقه النسبي وحده — لا يجوز أن
    يُحتسب ملف جذري يحمل الاسم نفسه «مستوردًا» عبر المسار المطلق.

    البنية: ملف اختباري قابل للجمع (جذر وصول) يستورد نسبيًا tests/target.py
    — واليتيم المزروع هو target.py في جذر المستودع. الحارس يجب أن يُسمي
    اليتيم الجذري تحديدًا ولا يُسمي الهدف النسبي المشروع."""
    import shutil
    root_orphan = _REPO_ROOT / "target.py"
    legit_target = _REPO_ROOT / "tests" / "target.py"
    importer = _REPO_ROOT / "tests" / "test_probe_rel_import.py"
    legit_target.parent.mkdir(parents=True, exist_ok=True)
    importer.write_text("from . import target\n", encoding="utf-8")
    legit_target.write_text("# legit relative target\n", encoding="utf-8")
    root_orphan.write_text("# root orphan — must NOT be counted as imported\n",
                          encoding="utf-8")
    try:
        r = _run_orphan_guard()
        assert r.returncode != 0, (
            "guard must FAIL while a root orphan shares a relative import's "
            "module name (absolute fallback for relative imports)"
        )
        # اليتيم الجذري المزروع تحديدًا يجب أن يُسمّى — لا أن يُحجب خلف
        # فشل سببه ملفات أخرى
        assert "'target.py'" in r.stdout, (
            f"ROOT orphan target.py must be named exactly: {r.stdout[-400:]}"
        )
        # الهدف النسبي المشروع لا يُسَمّى يتيمًا — استورده المستورد نسبيًا
        # من جذر قابل للوصول (الملف الاختباري يجمعه pytest)
        assert "'tests/target.py'" not in r.stdout, (
            f"legitimate relative target must not be flagged: {r.stdout[-400:]}"
        )
    finally:
        shutil.rmtree(_REPO_ROOT / "tests" / "_probe_cleanup_marker",
                      ignore_errors=True)
        importer.unlink(missing_ok=True)
        legit_target.unlink(missing_ok=True)
        root_orphan.unlink(missing_ok=True)
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )


def test_guard_catches_stray_double_underscore_init():
    """مسبار عدائي (الجولة <2> — اعتراض المراجع أمين): ملف غير مستورد اسمه
    يحتوي __init_.py كلاحقة (مثل probe__init__.py) ليس ملف حزمة — يجب أن
    يُكشف، لا أن يُعفى بمصفّي اللاحقة الواسع endswith(\"__init__.py\")."""
    probe = _REPO_ROOT / "backend" / "_orphan_probe__init__.py"
    probe.write_text("# stray orphan — name merely ends with __init__.py\n",
                     encoding="utf-8")
    try:
        r = _run_orphan_guard()
        assert r.returncode != 0, (
            "guard must FAIL while a stray file whose name ends with "
            "__init__.py exists (it is not a package file)"
        )
        assert "_orphan_probe__init__.py" in r.stdout, (
            f"stray must be named in failure output: {r.stdout[-300:]}"
        )
    finally:
        probe.unlink(missing_ok=True)
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )


def _plant_and_run_guard(rel_path, content, expected_name):
    """زرع ملف مؤقت وتشغيل الحارس — يُعيد نتيجة التشغيل الخام."""
    probe = _REPO_ROOT / rel_path
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(content, encoding="utf-8")
    try:
        return _run_orphan_guard()
    finally:
        probe.unlink(missing_ok=True)


def test_guard_catches_unreferenced_test_helper():
    """مسبار عدائي (الجولة <2> — اعتراض المراجع بصير): ملف داخل tests/ لا
    يجمعه pytest (لا يطابق test_*.py ولا conftest.py) وليس مستوردًا — ليس
    نقطة دخول اختبارية. إعفاء المجلد كاملاً مصفٍّ واسع يخفيه."""
    r = _plant_and_run_guard(
        "tests/unreferenced_helper_probe.py",
        "# not collected by pytest, not imported — a real orphan\n",
        "unreferenced_helper_probe.py",
    )
    assert r.returncode != 0, (
        "guard must FAIL while an unreferenced non-collected helper exists "
        "in tests/ (prefix exemption is too wide)"
    )
    assert "unreferenced_helper_probe.py" in r.stdout, (
        f"orphan must be named in failure output: {r.stdout[-300:]}"
    )
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, f"guard must pass after cleanup: {r2.stdout[-300:]}"


def test_guard_catches_unreferenced_backend_test_helper():
    """مسبار عدائي (الجولة <2> — اعتراض المراجع بصير): نفس الفجوة داخل
    backend/tests/ — الملف ليس اختبارًا يجمعه pytest ولا مستوردًا."""
    r = _plant_and_run_guard(
        "backend/tests/unreferenced_helper_probe.py",
        "# not collected by pytest, not imported — a real orphan\n",
        "unreferenced_helper_probe.py",
    )
    assert r.returncode != 0, (
        "guard must FAIL while an unreferenced non-collected helper exists "
        "in backend/tests/ (prefix exemption is too wide)"
    )
    assert "unreferenced_helper_probe.py" in r.stdout, (
        f"orphan must be named in failure output: {r.stdout[-300:]}"
    )
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, f"guard must pass after cleanup: {r2.stdout[-300:]}"


def test_guard_catches_unlisted_archive_file():
    """مسبار عدائي (الجولة <2> — اعتراض المراجع بصير): ملف داخل archive/
    غير مُدرج في ARCHIVED_FILES (الجرد الموثق) — إعفاء المجلد كاملاً يتجاوز
    الجرد ويخفيه. الأرشيف المشروع هو المُدرج بالاسم فقط."""
    r = _plant_and_run_guard(
        "archive/unlisted_orphan_probe.py",
        "# not in the documented ARCHIVED_FILES inventory — a real orphan\n",
        "unlisted_orphan_probe.py",
    )
    assert r.returncode != 0, (
        "guard must FAIL while an unlisted file exists in archive/ (the "
        "directory-wide exemption bypasses the documented inventory)"
    )
    assert "unlisted_orphan_probe.py" in r.stdout, (
        f"orphan must be named in failure output: {r.stdout[-300:]}"
    )
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, f"guard must pass after cleanup: {r2.stdout[-300:]}"


def test_guard_catches_mutual_import_pair():
    """مسبار عدائي (الجولة <2> — اعتراض المراجع بصير): ملفان يستورد أحدهما
    الآخر ولا تصل إليهما أي نقطة دخول — الحارس الحالي يقيس «له مستورِد»
    لا «قابل للوصول من نقطة دخول». الزوج المعزول وحدة ميتة يجب كشفها."""
    import shutil
    probe_a = _REPO_ROOT / "_orphan_probe_pair_a.py"
    probe_b = _REPO_ROOT / "_orphan_probe_pair_b.py"
    probe_a.write_text("import _orphan_probe_pair_b\n", encoding="utf-8")
    probe_b.write_text("import _orphan_probe_pair_a\n", encoding="utf-8")
    try:
        r = _run_orphan_guard()
        assert r.returncode != 0, (
            "guard must FAIL while a mutually-importing pair with NO entry "
            "point exists (reachability, not mere importership)"
        )
        assert "_orphan_probe_pair_a.py" in r.stdout, (
            f"dead pair must be named in failure output: {r.stdout[-300:]}"
        )
    finally:
        probe_a.unlink(missing_ok=True)
        probe_b.unlink(missing_ok=True)
    r2 = _run_orphan_guard()
    assert r2.returncode == 0, f"guard must pass after cleanup: {r2.stdout[-300:]}"
