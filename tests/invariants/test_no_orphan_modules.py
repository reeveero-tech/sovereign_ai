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

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
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
    """يُعيد كل ملفات Python الحية (بدون backup/pycache/git)."""
    live = []
    for p in _REPO_ROOT.rglob("*.py"):
        rel = str(p.relative_to(_REPO_ROOT))
        if any(x in rel for x in [
            "emergency_backups", "__pycache__", ".git",
            "guardian/data/emergency",
        ]):
            continue
        live.append(rel)
    return sorted(live)


def _build_import_graph(live_files: list) -> dict:
    """يبني خريطة الاستيراد (من يستورد من)."""
    imports_of = {}
    imported_by = {}
    live_set = set(live_files)

    for f in live_files:
        try:
            src = (_REPO_ROOT / f).read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            imports_of[f] = []
            continue

        imps = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imps.append(a.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imps.append(node.module)
                for a in node.names:
                    imps.append(a.name)
        imports_of[f] = imps

        # محاولة مطابقة كل استيراد لملف حي
        # (يدعم: 'from consciousness.field' → 'backend/consciousness/field.py'
        #  و 'from backend.consciousness.field' → نفس الملف
        #  و 'import nexus.core.engine' → 'nexus/core/engine.py'
        #  و 'from .quantum_state' (نسبي) → 'backend/quantum/quantum_state.py')
        file_dir = str(Path(f).parent)
        for imp in imps:
            parts = tuple(imp.split("."))
            for i in range(len(parts), 0, -1):
                suffix = parts[-i:]
                rel_path = "/".join(suffix) + ".py"
                if rel_path in live_set and rel_path != f:
                    imported_by.setdefault(rel_path, []).append(f)
                    break
                # محاولة مع backend/ prefix (الاستيراد النسبي من داخل backend/)
                backend_path = "backend/" + rel_path
                if backend_path in live_set and backend_path != f:
                    imported_by.setdefault(backend_path, []).append(f)
                    break
                # محاولة الاستيراد النسبي (from .module) — نفس مجلد الملف المستورد
                relative_path = file_dir + "/" + rel_path
                if relative_path in live_set and relative_path != f:
                    imported_by.setdefault(relative_path, []).append(f)
                    break

    return imported_by


def test_no_orphan_modules():
    """
    Invariant: كل ملف .py حي يجب أن يكون إما مستوردًا، نقطة دخول،
    أو مُدرجًا في الأرشيف الموثق (INVENTORY.py).
    """
    live_files = _get_live_python_files()
    imported_by = _build_import_graph(live_files)

    orphans = []
    for f in live_files:
        if f in imported_by:
            continue  # مستورد — ليس يتيمًا
        if f in KNOWN_ENTRY_POINTS:
            continue  # نقطة دخول معروفة
        if f in ARCHIVED_FILES:
            continue  # أرشيف موثق
        if f.startswith("tests/"):
            continue  # اختبارات (نقاط دخول اختبارية)
        if f.endswith("__init__.py"):
            continue  # ملفات حزمة Python (مطلوبة)
        if f.startswith("archive/"):
            continue  # أرشيف (موثق في INVENTORY.py)
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
