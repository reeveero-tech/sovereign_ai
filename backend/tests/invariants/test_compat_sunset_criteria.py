"""
Invariant 3: كل وحدة compat لها SUNSET_CRITERIA (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل ملف في backend/compat/ له معيار إزالة (sunset criteria)
موثّق. أي وحدة compat بدون معيار إزالة = فشل.
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

COMPAT_DIR = _REPO_ROOT / "backend" / "compat"


def test_every_compat_module_has_sunset_criteria():
    """
    Invariant: كل وحدة في backend/compat/ يجب أن تحتوي SUNSET_CRITERIA
    (معيار إزالة موثّق). الوحدة بدون معيار = لا أفق للإزالة = فشل.
    """
    assert COMPAT_DIR.exists(), "backend/compat/ must exist"

    compat_files = list(COMPAT_DIR.glob("*.py"))
    assert len(compat_files) > 0, "backend/compat/ must have at least one module"

    missing_criteria = []

    for cf in compat_files:
        if cf.name == "__init__.py":
            continue  # ملف حزمة — لا يحتاج معيارًا

        src = cf.read_text(encoding="utf-8")

        # البحث عن SUNSET_CRITERIA (كمتغير أو في تعليق)
        has_sunset = (
            "SUNSET_CRITERIA" in src
            or "sunset_criteria" in src
            or "sunset" in src.lower()
        )

        if not has_sunset:
            missing_criteria.append(cf.name)

    assert len(missing_criteria) == 0, (
        f"Compat modules without SUNSET_CRITERIA: {missing_criteria}. "
        f"Every compat module must document when it can be retired."
    )


def test_compat_meta_exists():
    """يجب أن يوجد backend/compat/__meta__.py (طبقة توثيق lifecycle)."""
    meta_file = COMPAT_DIR / "__meta__.py"
    assert meta_file.exists(), (
        "backend/compat/__meta__.py must exist (compat lifecycle metadata)"
    )


def test_compat_meta_contains_lifecycle_dict():
    """__meta__.py يجب أن يحتوي COMPAT_LIFECYCLE (قاموس lifecycle)."""
    meta_file = COMPAT_DIR / "__meta__.py"
    # (قاعدة الجولة الإنشائية 2026-10-16: لا skip — الملف موجود؛
    # وغيابه فشل صريح للاختبار لا حالة تُتخطى)
    assert meta_file.exists(), (
        "backend/compat/__meta__.py must exist (compat lifecycle metadata)"
    )

    src = meta_file.read_text(encoding="utf-8")
    assert "COMPAT_LIFECYCLE" in src, (
        "__meta__.py must define COMPAT_LIFECYCLE dict"
    )

    # تحقق أن كل وحدة compat لها إدخال في COMPAT_LIFECYCLE
    tree = ast.parse(src)
    lifecycle_entries = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "COMPAT_LIFECYCLE":
                    if isinstance(node.value, ast.Dict):
                        for key in node.value.keys:
                            if isinstance(key, ast.Constant):
                                lifecycle_entries.add(key.value)

    compat_files = [
        cf.stem for cf in COMPAT_DIR.glob("*.py")
        if cf.name not in ("__init__.py", "__meta__.py")
    ]

    missing = [cf for cf in compat_files if cf not in lifecycle_entries]
    assert len(missing) == 0, (
        f"Compat modules missing from COMPAT_LIFECYCLE: {missing}"
    )


def test_guard_flags_new_compat_without_sunset():
    """إثبات RED سلوكي دائم (قاعدة الجولة الإنشائية 2026-10-16):

    وحدة compat جديدة بلا SUNSET_CRITERIA تفشل الحارس، وإضافتها تعيد النجاح —
    المسبار يُنفذ في كل تشغيل (سب-بروسس)، فلا يعتمد على تشغيل تاريخي.
    """
    import shutil
    import subprocess

    probe = COMPAT_DIR / "_probe_no_criteria.py"
    probe.write_text(
        "# probe — compat module missing its retirement criterion\n"
        "def probe_helper():\n"
        "    return 1\n",
        encoding="utf-8",
    )
    cmd = [
        sys.executable, "-m", "pytest",
        "backend/tests/invariants/test_compat_sunset_criteria.py"
        "::test_every_compat_module_has_sunset_criteria",
        "-q", "--no-header",
    ]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(_REPO_ROOT), timeout=300,
        )
        # مع الوحدة الجديدة بلا معيار: الحارس يفشل ويذكرها بالاسم
        assert r.returncode != 0, (
            "guard must FAIL while a compat module lacks SUNSET_CRITERIA"
        )
        assert "_probe_no_criteria.py" in r.stdout, (
            f"probe module must be named in the failure output: {r.stdout[-300:]}"
        )
    finally:
        probe.unlink(missing_ok=True)

    # بعد الإزالة: الحارس يعود أخضر
    r2 = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(_REPO_ROOT), timeout=300,
    )
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )
