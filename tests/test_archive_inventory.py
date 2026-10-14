# tests/test_archive_inventory.py
# اختبارات جرد الأرشيف — تتحقق أن كل ملف في archive/root_strays/ موثق
# في INVENTORY.py وأن كل الملفات موجودة (لا يُحذف شيء)

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ARCHIVE_DIR = _REPO_ROOT / "archive" / "root_strays"
INVENTORY_PY = _ARCHIVE_DIR / "INVENTORY.py"


def test_inventory_file_exists():
    """يتحقق أن ملف الجرد موجود — توثيق مصاحب لكل ملف أرشيفي"""
    assert INVENTORY_PY.exists(), (
        f"INVENTORY.py should exist at {INVENTORY_PY} (documentation of every archived file)"
    )


def test_every_archived_file_is_documented():
    """
    يتأكد أن كل ملف .py في archive/root_strays/ موثق في INVENTORY.py.
    لا يُحذف أي ملف — فقط يُوثق غايته.
    """
    assert INVENTORY_PY.exists(), "INVENTORY.py must exist first"
    inventory_src = INVENTORY_PY.read_text(encoding="utf-8")

    # الملفات المتوقعة في الأرشيف (بناءً على الجرد الفعلي)
    expected_files = [
        "encryption.py",
        "investigation.py",
        "IDs.js",
        "Fff.txt",
        "attached_assets_create1_prompt.txt",
        "attached_assets_create2_prompt.txt",
        "dockerignore_duplicate",
        "infrastructure_Dockerfile_empty",
        "infrastructure_requirements_empty",
    ]

    # كل ملف متوقع يجب أن يكون موثقًا في INVENTORY.py
    for fname in expected_files:
        assert fname in inventory_src, (
            f"File {fname!r} must be documented in INVENTORY.py"
        )

    # كل ملف موجود فعليًا في الأرشيف يجب أن يكون موثقًا
    actual_files = [
        f.name for f in _ARCHIVE_DIR.iterdir()
        if f.is_file() and f.name != "INVENTORY.py"
    ]
    for fname in actual_files:
        assert fname in inventory_src, (
            f"File {fname!r} exists in archive but is NOT documented in INVENTORY.py"
        )


def test_all_archive_files_still_exist():
    """
    يتأكد أن كل الملفات الأرشيفية ما زالت موجودة — لا حذف، لا تجاهل.
    """
    expected_files = [
        "encryption.py",
        "investigation.py",
        "IDs.js",
        "Fff.txt",
        "attached_assets_create1_prompt.txt",
        "attached_assets_create2_prompt.txt",
        "dockerignore_duplicate",
        "infrastructure_Dockerfile_empty",
        "infrastructure_requirements_empty",
    ]
    for fname in expected_files:
        assert (_ARCHIVE_DIR / fname).exists(), (
            f"Archived file {fname!r} must NOT be deleted (no-deletion rule)"
        )


def test_inventory_is_executable_python():
    """يتحقق أن INVENTORY.py هو كود Python قابل للتشغيل (ليس ملف .md منفصل)"""
    import py_compile
    py_compile.compile(str(INVENTORY_PY), doraise=True)
    # يجب أن يكون فيه دالة قابلة للاستدعاء
    import importlib.util
    spec = importlib.util.spec_from_file_location("archive_inventory", INVENTORY_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "print_inventory"), (
        "INVENTORY.py must define print_inventory() (executable documentation)"
    )
    assert mod.print_inventory() is True
