# -*- coding: utf-8 -*-
"""
حارس AST — منع مسارات الموت في كل الكود القابل للتشغيل (R-686)

أمر المالك (المرحلة ١): «حارس AST: أضف حارس الـ AST الذي يمنع أي كود
مستقبلي من إعادة إدخال مسارات الموت، وتأكد أنه يغطي كل الكود القابل
للتشغيل وليس مجلد الحارس فقط».

نطاق الحارس:
- كل ملفات Python القابل للتشغيل — لا استثناء مجلد بالاسم إلا إن كان
  بلا كود (اختبار نزاهة يؤكد أن المجلدات المستثناة صفرية .py):
  guardian/*.py تُفحص فعلًا (يُستثنى guardian/data — بيانات).
- الحظر شامل كل أشكال إدخال الإنهاء:
  1. استدعاء exit/_exit على أي كائن (Attribute) — لكن الإعفاء لنقاط
     الدخول مقصور على sys.exit تحديدًا (استدعاء على الكائن sys) —
     ليس أي Attribute اسمه exit.
  2. الاستيراد المباشر باسم مستعار (from sys import exit as x) —
     الاستيراد نفسه مخالفة.
  3. الإسناد بأشكاله الثلاثة: عادي (x = sys.exit)، المُعلَّق
     (x: object = sys.exit)، وإسناد هدفه خاصية (os.exit = os._exit) —
     الإسناد مخالفة بذاته.
  4. استدعاء الاسم المجرد (exit) أو المُسند إليه دالة إنهاء.
  5. السلسلة القاتلة القديمة في أي كود حي.
- قائمة السماح غير قابلة للتقادم: كل ملف فيها يوجد ويستخدم sys.exit
  فعلًا (إثبات AST — لا بحث نصي يقبل تعليقًا).
- عدائية ذاتية: الكاشف يُختبر بعينات معطوبة لا تُنفذ — يشمل عينات
  RED التي كشفت ثغرات النسخة الأولى (الإسناد المعلّق، وإسناد خاصية
  داخل ملف مسموح) — ويجب أن يسمي المخالفة ومسارها.
"""

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

# أجزاء ليست كودًا قابلًا للتشغيل — الاختبار النهائي يؤكد أنها صفرية .py
# (باستثناء tests: مجلد الحارس نفسه — عينات الحراس وحدها فيه).
EXCLUDE_PARTS = {
    "tests", "node_modules", "nexus_data", "data", "docs",
    "forensics", "__pycache__", ".git", "archive", "r685_shelved",
}

# نقاط الدخول: يُسمح لها بـsys.exit تحديدًا (خروج نظيف) — لا أكثر.
EXIT_ALLOWED_ENTRY_POINTS = {
    "main.py",
    "scripts/verify_operational_auth.py",
    "scripts/verify_new_key.py",
    "tools/action_log.py",
}

BANNED_STRING = "max_tamper_attempts"
BANNED_NAMES = {"exit", "_exit"}


def _iter_runnable_files():
    """كل ملفات Python القابل للتشغيل — يفحص guardian/*.py أيضًا."""
    for path in sorted(_REPO_ROOT.rglob("*.py")):
        rel = path.relative_to(_REPO_ROOT)
        parts = set(rel.parts)
        if "guardian" in parts and rel.parts[rel.parts.index("guardian") + 1] == "data":
            continue
        if parts & EXCLUDE_PARTS:
            continue
        if path.name == Path(__file__).name:
            continue
        yield rel, path


def _is_exit_value(value) -> bool:
    """قيمة الإسناد دالة إنهاء؟ (Attribute مثل sys.exit أو Name مجرد)"""
    return (
        (isinstance(value, ast.Attribute) and value.attr in BANNED_NAMES)
        or (isinstance(value, ast.Name) and value.id in BANNED_NAMES)
    )


def _is_allowed_entry_exit(call: ast.Call) -> bool:
    """المسموح في نقاط الدخول: sys.exit تحديدًا — لا أي .exit آخر."""
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "exit"
        and isinstance(func.value, ast.Name)
        and func.value.id == "sys"
    )


def _scan_file(rel: Path, source: str):
    """يعيد قائمة مخالفات (وصف، سطر) في ملف واحد."""
    is_entry_point = rel.as_posix() in EXIT_ALLOWED_ENTRY_POINTS
    violations = []
    if BANNED_STRING in source:
        violations.append((
            f"السلسلة القاتلة القديمة ممنوعة: {BANNED_STRING}", 0,
        ))
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return violations + [(f"SyntaxError (لا يمكن تدقيقه): {exc}", exc.lineno)]

    # القاعدة الجذرية (جولة المراجع الرابعة): مرجع دالة الإنهاء نفسه
    # مخالفة أينما ورد — قراءة os._exit أو sys.exit أو exit كمرجع (وليس
    # ضمن الاستدعاء المشروع الوحيد sys.exit(...) في نقطة دخول موثقة).
    # هذا يغطي الإسناد بأسمائه البريئة (holder.stop = os._exit) لأن
    # المرجع في قيمة الإسناد يُكشف. (حد معلوم: تحليل AST الساكن لا يمنع
    # كل تنفيذ ديناميكي — الحارس حارس توكيد قوي لا إثبات استحالة.)
    allowed_exit_refs = set()
    if is_entry_point:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_allowed_entry_exit(node):
                allowed_exit_refs.add(id(node.func))

    def check_assign_targets(targets, value, lineno):
        if _is_exit_value(value):
            for target in targets:
                if isinstance(target, ast.Name):
                    violations.append((
                        f"إسناد دالة الإنهاء إلى اسم: {target.id} = ...exit...",
                        lineno,
                    ))
                elif isinstance(target, ast.Attribute) and target.attr in BANNED_NAMES:
                    violations.append((
                        f"إسناد إلى خاصية إنهاء: {target.attr} = دالة إنهاء (تحييل)",
                        lineno,
                    ))

    for node in ast.walk(tree):
        # 1) الاستيراد المباشر باسم مستعار: from sys import exit as x
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in BANNED_NAMES:
                    violations.append((
                        f"استيراد مباشر لدالة الإنهاء باسم مستعار: "
                        f"from ... import {alias.name} as {alias.asname or alias.name}",
                        node.lineno,
                    ))

        # 2) الإسناد بكل أشكاله: Assign / AnnAssign / هدفه Name أو Attribute
        elif isinstance(node, ast.Assign):
            check_assign_targets(node.targets, node.value, node.lineno)
        elif isinstance(node, ast.AnnAssign):
            check_assign_targets([node.target], node.value, node.lineno)

        # 3) مرجع دالة الإنهاء نفسه — أينما ورد (خاصية أو اسم مجرد)
        elif isinstance(node, ast.Attribute) and node.attr in BANNED_NAMES:
            if id(node) not in allowed_exit_refs:
                violations.append((
                    f"مرجع دالة الإنهاء (مسار إنهاء) عبر خاصية: {node.attr}",
                    node.lineno,
                ))
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            violations.append((
                f"مرجع دالة الإنهاء (مسار إنهاء) بالاسم المجرد: {node.id}",
                node.lineno,
            ))

    return violations


def _collect_offenders():
    """يجمع مخالفات كل الكود القابل للتشغيل — كعبارات rel:line — وصف."""
    offenders = []
    files = list(_iter_runnable_files())
    assert len(files) > 100, (
        f"الحارس يجب أن يغطي كل الكود القابل للتشغيل — وجد {len(files)} ملفًا فقط"
    )
    for rel, path in files:
        source = path.read_text(encoding="utf-8", errors="replace")
        for desc, line in _scan_file(rel, source):
            offenders.append(f"{rel}:{line} — {desc}")
    return offenders, files


def test_no_exit_calls_outside_entry_points():
    """أي استدعاء/استيراد/إسناد لدالة إنهاء ممنوع خارج نقاط الدخول."""
    offenders, files = _collect_offenders()
    assert not offenders, (
        "مسارات إنهاء ممنوعة موجودة (R-686 — أمر المالك):\n  "
        + "\n  ".join(offenders)
    )
    # guardian ليس مستثنى بالاسم — يجب أن يكون ضمن المفحوصين
    scanned = {str(rel) for rel, _ in files}
    assert any(r.startswith("guardian/") for r in scanned), (
        "ملفات guardian/*.py يجب أن تُفحص — لا استثناء مجلد كامل فيه كود"
    )


def test_no_max_tamper_attempts_anywhere():
    """السلسلة القاتلة القديمة ممنوعة في أي كود قابل للتشغيل."""
    offenders = []
    for rel, path in _iter_runnable_files():
        source = path.read_text(encoding="utf-8", errors="replace")
        if BANNED_STRING in source:
            offenders.append(str(rel))
    assert not offenders, (
        f"السلسلة القاتلة القديمة ({BANNED_STRING}) موجودة في: {offenders} — "
        "ممنوعة في كل الكود الحي"
    )


def test_entry_point_allowlist_is_honest():
    """قائمة السماح غير قابلة للتقادم — بإثبات AST لا بحث نصي."""
    for entry in EXIT_ALLOWED_ENTRY_POINTS:
        path = _REPO_ROOT / entry
        assert path.exists(), (
            f"نقطة الدخول الموثقة غير موجودة: {entry} — حدّث القائمة أو الملف"
        )
        source = path.read_text(encoding="utf-8", errors="replace")
        # إثبات AST: استدعاء sys.exit حقيقي موجود في الكود
        tree = ast.parse(source)
        has_real_sys_exit = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "exit"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "sys"
            for node in ast.walk(tree)
        )
        assert has_real_sys_exit, (
            f"نقطة الدخول {entry} لا تستدعي sys.exit فعلًا (إثبات AST) — "
            "قائمة سماح متقادمة"
        )
        # ولا يجوز أن يحتوي ما هو ممنوع حتى في نقاط الدخول
        violations = _scan_file(Path(entry), source)
        assert not violations, (
            f"نقطة الدخول {entry} تحوي مسار إنهاء ممنوعًا: {violations}"
        )


def test_excluded_dirs_contain_no_runnable_code():
    """نزاهة الاستثناءات: كل مجلد مستثنى (غير مجلد الحارس) صفري .py."""
    for part in EXCLUDE_PARTS - {"tests"}:
        excluded_py = list(_REPO_ROOT.rglob(f"{part}/**/*.py"))
        assert not excluded_py, (
            f"المجلد المستثنى «{part}» يحوي ملفات Python قابلة للتشغيل "
            f"({[str(p) for p in excluded_py[:3]]}) — إما تُفحص أو يوثق "
            "استثناؤها بتحقق"
        )


# ---------- عدائية ذاتية: الكاشف نفسه يُختبر بعينات معطوبة (لا تُنفذ) ----------

def test_detector_catches_direct_aliased_import():
    """from sys import exit as leave ← leave(1) — الكاشف يسميها."""
    sample = "from sys import exit as leave\nleave(1)\n"
    violations = _scan_file(Path("probe_sample.py"), sample)
    assert any("مستعار" in d for d, _ in violations), (
        f"الكاشف فوّت الاستيراد المستعار لدالة الإنهاء: {violations}"
    )


def test_detector_catches_assignment_alias():
    """f = sys.exit ← f(1) — الكاشف يسمي الإسناد والاستدعاء."""
    sample = "import sys\nf = sys.exit\nf(1)\n"
    violations = _scan_file(Path("probe_sample.py"), sample)
    assert any("إسناد دالة الإنهاء إلى اسم" in d for d, _ in violations), (
        f"الكاشف فوّت إسناد دالة الإنهاء إلى اسم: {violations}"
    )


def test_detector_catches_annotated_assignment_alias():
    """ثغرة النسخة الأولى (RED أثبتها): stop: object = sys.exit ← stop(1)."""
    sample = "import sys\nstop: object = sys.exit\nstop(1)\n"
    violations = _scan_file(Path("probe_sample.py"), sample)
    assert any("إسناد دالة الإنهاء إلى اسم: stop" in d for d, _ in violations), (
        f"الكاشف فوّت الإسناد المعلّق (AnnAssign) لدالة الإنهاء: {violations}"
    )


def test_detector_catches_attribute_reassignment_in_cli():
    """ثغرة النسخة الأولى (RED أثبتها): os.exit = os._exit ← os.exit(1)
    داخل نقطة دخول مسموحة — الإعفاء لـsys.exit تحديدًا لا لأي .exit."""
    sample = "import os\nos.exit = os._exit\nos.exit(1)\n"
    violations = _scan_file(Path("main.py"), sample)  # main.py في قائمة السماح
    kinds = [d for d, _ in violations]
    assert any("إسناد إلى خاصية إنهاء" in d for d in kinds), (
        f"الكاشف فوّت إسناد خاصية الإنهاء: {kinds}"
    )
    assert any("مسار إنهاء" in d for d in kinds), (
        f"استدعاء os.exit(1) يجب أن يُكشف داخل نقطة الدخول "
        f"(الإعفاء لـsys.exit تحديدًا): {kinds}"
    )


def test_detector_catches_exit_inside_guardian_dir():
    """ملف داخل guardian/ ليس مستثنى — الكشف الفعلي يسمي المخالفة ومسارها."""
    probe = _REPO_ROOT / "guardian" / "_probe_death_path.py"
    try:
        probe.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
        offenders, files = _collect_offenders()
        assert "guardian/_probe_death_path.py" in {str(rel) for rel, _ in files}, (
            "ملفات guardian/*.py يجب أن تكون ضمن نطاق الفحص"
        )
        assert any(
            o.startswith("guardian/_probe_death_path.py:2") for o in offenders
        ), (
            f"الكشف الفعلي يجب أن يسمي المخالفة ومسارها (سطر 2): "
            f"{[o for o in offenders if 'guardian' in o]}"
        )
    finally:
        probe.unlink(missing_ok=True)


def test_detector_catches_hard_exit_in_cli_entry_point():
    """os._exit ممنوع حتى داخل نقطة دخول مسموحة (الخروج النظيف فقط)."""
    sample = "import os\nos._exit(1)\n"
    violations = _scan_file(Path("main.py"), sample)
    assert any("مسار إنهاء" in d for d, _ in violations), (
        "الإعفاء يجب أن يكون لـsys.exit فقط — _exit ممنوع حتى في نقاط الدخول"
    )


def test_detector_allows_clean_sys_exit_in_entry_point():
    """sys.exit في نقطة دخول موثقة = خروج نظيف مسموح (لا إنذار كاذب)."""
    sample = "import sys\nsys.exit(1)\n"
    violations = _scan_file(Path("main.py"), sample)
    assert not violations, (
        f"إنذار كاذب: sys.exit في نقطة دخول مسموح — {violations}"
    )


def test_detector_catches_hidden_exit_reference():
    """ثغرة جولة المراجع الرابعة (RED أولًا): مرجع دالة الإنهاء نفسه
    مخالفة أينما ورد — holder.stop = os._exit ← holder.stop(1):
    الاستدعاء باسم بريء لكن المرجع (قراءة os._exit) يجب أن يُكشف."""
    sample = "import os\nholder.stop = os._exit\nholder.stop(1)\n"
    violations = _scan_file(Path("probe_sample.py"), sample)
    assert any("مرجع دالة الإنهاء" in d for d, _ in violations), (
        f"الكاشف فوّت مرجع دالة الإنهاء تحت اسم بريء: {violations}"
    )
