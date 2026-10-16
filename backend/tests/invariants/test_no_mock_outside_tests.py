"""
Invariant 4: لا mock خارج الاختبارات (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل استخدام Mock()/MagicMock/patch() موجود فقط في tests/.
أي وجود في كود الإنتاج = فشل (يحمي قاعدة 'لا mock في الإنتاج').
"""

import re
import sys
from pathlib import Path

# الملف في backend/tests/invariants/ — الجذر أربع مستويات أعلى
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest

# أنماط mock الممنوعة في الإنتاج (أكثر دقة — لا تُطابق dispatch أو كلمات عادية)
MOCK_PATTERNS = [
    r"\bMock\(\)",           # Mock() — وليس dispatch(
    r"\bMagicMock\(",
    r"\bpatch\.\w+\(",        # patch.object(, patch.anything( — وليس dispatch(
    r"\bpatch\(",
    r"\bunittest\.mock\b",
    r"\bfrom unittest\.mock import",
]

# مجلدات مسموح فيها mock (اختبارات فقط — backend/tests/ مجلد اختبارات
# شرعي مثل tests/: انتقلت إليه invariants المرحلة 3 وفق مسار ROADMAP_V2)
ALLOWED_DIRS = {
    "tests/",
    "backend/tests/",  # مجلد اختبارات (نُقلت إليه invariants — مسار ROADMAP)
    "archive/",       # أرشيف (موثق — لا يُشغّل)
}


def test_no_mock_outside_tests():
    """
    Invariant: لا Mock/MagicMock/patch في كود الإنتاج.
    كل استخدام يجب أن يكون داخل tests/ فقط.
    """
    violations = []

    for p in _REPO_ROOT.rglob("*.py"):
        rel = str(p.relative_to(_REPO_ROOT))

        # استبعاد المجلدات غير الحية
        if any(x in rel for x in [
            "emergency_backups", "__pycache__", ".git",
            "guardian/data/emergency",
        ]):
            continue

        # المجلدات المسموح بها
        if any(rel.startswith(d) for d in ALLOWED_DIRS):
            continue

        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue

        # فحص الأنماط الممنوعة
        for pattern in MOCK_PATTERNS:
            matches = re.findall(pattern, src)
            if matches:
                violations.append({
                    "file": rel,
                    "pattern": pattern,
                    "count": len(matches),
                })

    assert len(violations) == 0, (
        f"Found mock usage in production code (outside tests/): {violations}. "
        f"Mocks are ONLY allowed inside tests/ per the constitution."
    )


def test_no_stub_placeholders_in_production():
    """
    Invariant: لا stub دائم أو placeholder يخفي فشلًا في الإنتاج.
    (يبحث عن عبارات واضحة مثل 'TODO: implement', 'pass  # stub',
    'raise NotImplementedError' في كود الإنتاج)
    """
    stub_patterns = [
        r"#\s*TODO:\s*implement",
        r"#\s*stub",
        r"#\s*placeholder",
        r"raise NotImplementedError",
        r"pass\s*#\s*stub",
    ]

    violations = []

    for p in _REPO_ROOT.rglob("*.py"):
        rel = str(p.relative_to(_REPO_ROOT))

        if any(x in rel for x in [
            "emergency_backups", "__pycache__", ".git",
            "guardian/data/emergency",
        ]):
            continue

        if any(rel.startswith(d) for d in ALLOWED_DIRS):
            continue

        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue

        for pattern in stub_patterns:
            matches = re.findall(pattern, src, re.IGNORECASE)
            if matches:
                violations.append({
                    "file": rel,
                    "pattern": pattern,
                    "count": len(matches),
                })

    assert len(violations) == 0, (
        f"Found stub/placeholder in production code: {violations}. "
        f"Stubs that hide failures are forbidden per the constitution."
    )


def test_guard_flags_mock_outside_tests():
    """إثبات RED سلوكي دائم (قاعدة الجولة الإنشائية 2026-10-16):

    الحارس يفشل عند إدخال ملف تجريبي يستخدم Mock() خارج مجلدات الاختبارات،
    ويعود أخضر بعد إزالته — نفس المسبار يُنفذ في كل تشغيل (سب-بروسس مع ملف
    تجريبي موجود ثم بعد إزالته)، فلا يعتمد الإثبات على تشغيل تاريخي.
    """
    import shutil
    import subprocess

    probe_dir = _REPO_ROOT / "_mock_probe_tmp"
    probe = probe_dir / "uses_mock.py"
    probe_dir.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        "# probe — uses Mock() outside test dirs (guard must flag it)\n"
        "from unittest.mock import Mock\n"
        "thing = Mock()\n",
        encoding="utf-8",
    )
    cmd = [
        sys.executable, "-m", "pytest",
        "backend/tests/invariants/test_no_mock_outside_tests.py"
        "::test_no_mock_outside_tests",
        "-q", "--no-header",
    ]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(_REPO_ROOT), timeout=300,
        )
        # مع الملف المخالف: الحارس يفشل ويذكره بالاسم
        assert r.returncode != 0, (
            "guard must FAIL while a Mock()-using file exists outside test dirs"
        )
        assert "_mock_probe_tmp/uses_mock.py" in r.stdout, (
            f"probe must be named in the failure output: {r.stdout[-300:]}"
        )
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)

    # بعد الإزالة: الحارس يعود أخضر
    r2 = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(_REPO_ROOT), timeout=300,
    )
    assert r2.returncode == 0, (
        f"guard must pass again after probe removal: {r2.stdout[-300:]}"
    )
