"""
Invariant 3: كل وحدة compat لها SUNSET_CRITERIA (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل ملف في backend/compat/ له معيار إزالة (sunset criteria)
موثّق. أي وحدة compat بدون معيار إزالة = فشل.
"""

import ast
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
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
    if not meta_file.exists():
        pytest.skip("__meta__.py does not exist yet")

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
