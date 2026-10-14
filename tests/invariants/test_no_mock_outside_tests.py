"""
Invariant 4: لا mock خارج الاختبارات (المرحلة 3 من ROADMAP_V2)

يتحقق أن كل استخدام Mock()/MagicMock/patch() موجود فقط في tests/.
أي وجود في كود الإنتاج = فشل (يحمي قاعدة 'لا mock في الإنتاج').
"""

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
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

# مجلدات مسموح فيها mock (اختبارات فقط)
ALLOWED_DIRS = {
    "tests/",
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
