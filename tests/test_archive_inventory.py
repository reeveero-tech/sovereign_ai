# tests/test_archive_inventory.py
# حرس قرار الحذف (2026-10-18): أمر المالك بحذف الأرشيف الميت والنسخ
# الاحتياطية القديمة بعد تسليم حزمة احتياطية كاملة وتأكيد تحميلها
# (owner_archive_backup.zip — 204 ملفات مصدر + MANIFEST + README؛
# مطابقة بايت-بالبايت مع المستودع متحققة قبل الحذف).
# القرار الأصلي: D-005 (أرشفة داخلية) → أمر المالك 2026-10-18 (حذف بعد
# أرشفة خارجية) → هذا الملف يحرس القرار: ما حُذف لا يُستعاد.

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_root_strays_archive_deleted_stays_deleted():
    """archive/root_strays حُذف بقرار المالك — لا يُستعاد داخل المستودع"""
    assert not (_REPO_ROOT / "archive" / "root_strays").exists(), (
        "archive/root_strays حُذف بأمر المالك 2026-10-18 بعد تسليم حزمة "
        "احتياطية كاملة (owner_archive_backup.zip) وتأكيد تحميلها — لا "
        "يُستعاد. النسخة الاحتياطية الكاملة بحوزة المالك."
    )


def test_emergency_backups_deleted_stays_deleted():
    """النسخ الاحتياطية القديمة حُذفت بقرار المالك — لا تُستعاد"""
    backups = _REPO_ROOT / "guardian" / "data" / "emergency" / "emergency_backups"
    assert not backups.exists(), (
        "guardian/data/emergency/emergency_backups حُذف بأمر المالك "
        "2026-10-18 بعد تسليم حزمة احتياطية كاملة (owner_archive_backup.zip) "
        "وتأكيد تحميلها — لا يُستعاد. تقييم فائدة المحتوى لم يكتمل (فحص سابق "
        "معيب سُحب ادعاؤه) — الحزمة الكاملة بحوزة المالك."
    )
