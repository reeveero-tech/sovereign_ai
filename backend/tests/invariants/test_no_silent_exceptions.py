"""
Invariant 9: لا except:pass صامت بلا تعليق تبرير (R-680)

يتحقق أن كل `except: pass` في كود الإنتاج (خارج tests/) لديه تعليق تبرير
قبل بداية `try` أو على نفس سطر `except`.

النمط المسموح:
    # R-XXX: <reason>            ← تعليق تبرير
    try:
        ...
    except:
        pass                      ← مسموح (مبرر)

أو

    try:
        ...
    except:  # R-XXX reason
        pass

أي `except: pass` بلا تعليق تبرير = فشل الاختبار.

الاستثناءات:
- tests/ (كل ملفات الاختبارات — بلا تعليق مطلوب)
- archive/ (أرشيف — غير مُشغّل)
- frontend/ (JavaScript — غير Py)
- data/ (بيانات)
- guardian/data/emergency (backup)
"""

import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


# المجلدات المستثناة من الفحص (اختبارات، أرشيف، غير كود الإنتاج)
EXCLUDED_DIRS = {
    "tests/",
    "backend/tests/",
    "archive/",
    "frontend/",
    "data/",
    "guardian/data/emergency",
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules",
    "venv",
    "emergency_backups",
}

# أنماط تبرير مقبولة (تعليق يحتوي على R-XXX أو TOLERATED أو توضيح عربي/إنجليزي طويل)
JUSTIFICATION_PATTERNS = [
    r"#\s*R-\d+\s*[:\s]",          # R-680, R-670, etc.
    r"#\s*TOLERATED\s*[:\s]",       # # TOLERATED: reason
    r"#\s*justif",                   # justification (English)
    r"#\s*مُبرر",                  # مُبرر (عربي)
    r"#\s*مبرر",                  # مبرر (عربي)
    r"#\s*تعليق",
]
JUSTIFICATION_RE = re.compile("|".join(JUSTIFICATION_PATTERNS))

# الحد الأدنى لطول التعليق (حتى لا يكون `# x` تبريراً زائفاً)
MIN_COMMENT_LENGTH = 8


def _has_justification_comment(lines: list, except_line_idx: int) -> bool:
    """
    يفحص السطور السابقة (1-4) لسطر `except` للبحث عن تعليق تبرير.
    أيضاً يفحص التعليق على نفس سطر `except`.
    """
    # 1) التعليق على نفس سطر `except` (مثل `except:  # R-680: reason`)
    except_line = lines[except_line_idx]
    if "#" in except_line:
        comment_part = except_line.split("#", 1)[1].strip()
        if len(comment_part) >= MIN_COMMENT_LENGTH and JUSTIFICATION_RE.search(except_line):
            return True

    # 2) التعليق في السطور السابقة (من 1 إلى 4 سطور قبل `except` أو `try`)
    # نبحث أول عن `try:` قبل `except` — ثم نفحص السطور بين `try:` و `except`
    for back in range(1, 5):
        idx = except_line_idx - back
        if idx < 0: break
        line = lines[idx]
        stripped = line.strip()
        # إذا وجدنا `try:` قبل — فالتعليق يجب أن يكون قبل `try:`
        if stripped.startswith("try"):
            # نفحص السطور قبل `try:`
            for back2 in range(1, 4):
                idx2 = idx - back2
                if idx2 < 0: break
                l2 = lines[idx2]
                if "#" in l2:
                    comment_part = l2.split("#", 1)[1].strip()
                    if len(comment_part) >= MIN_COMMENT_LENGTH and JUSTIFICATION_RE.search(l2):
                        return True
            break
        # إذا كان السطر يحتوي تعليقاً مباشرة قبل `except` (ليس `try`)
        if "#" in line and not stripped.startswith("try"):
            comment_part = line.split("#", 1)[1].strip()
            if len(comment_part) >= MIN_COMMENT_LENGTH and JUSTIFICATION_RE.search(line):
                return True

    return False


def _scan_silent_exceptions():
    """
    يفحص كل ملفات الإنتاج بحثاً عن `except: pass` بلا تعليق تبرير.
    يُعيد قائمة (file, line_number, except_line).
    """
    violations = []

    for p in _REPO_ROOT.rglob("*.py"):
        rel = str(p.relative_to(_REPO_ROOT))
        rel_posix = rel.replace("\\", "/")

        # استثناء المجلدات غير الحية
        if any(x in rel_posix for x in [
            "__pycache__", ".git", ".pytest_cache", "node_modules", "venv",
            "emergency_backups", "guardian/data/emergency",
        ]):
            continue

        # استثناء المجلدات المسموح بها (اختبارات، أرشيف، إلخ)
        if any(rel_posix.startswith(d) for d in EXCLUDED_DIRS):
            continue

        # استثناء هذا الملف نفسه (لا يفحص نفسه)
        if rel_posix == "backend/tests/invariants/test_no_silent_exceptions.py":
            continue

        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = src.split("\n")

        # نمط: `except...:` ثم سطر `pass` مباشرة
        for i in range(len(lines) - 1):
            stripped = lines[i].strip()
            if (stripped.startswith("except") and stripped.endswith(":")
                    and lines[i + 1].strip() == "pass"):
                if not _has_justification_comment(lines, i):
                    violations.append({
                        "file": rel_posix,
                        "line": i + 1,
                        "except_line": stripped,
                    })

        # نمط إضافي: `except...:` ثم سطر `continue` (يُخفي فشلاً في حلقة)
        for i in range(len(lines) - 1):
            stripped = lines[i].strip()
            if (stripped.startswith("except") and stripped.endswith(":")
                    and lines[i + 1].strip() == "continue"):
                if not _has_justification_comment(lines, i):
                    violations.append({
                        "file": rel_posix,
                        "line": i + 1,
                        "except_line": stripped,
                        "pattern": "except_continue",
                    })

    return violations


class TestNoSilentExceptions:
    """Invariant: كل except:pass في الإنتاج لديه تعليق تبرير."""

    def test_no_silent_except_pass_in_production(self):
        """
        يفشل إذا وُجد `except: pass` بلا تعليق تبرير في كود الإنتاج.
        """
        violations = _scan_silent_exceptions()

        if violations:
            error_msg = (
                f"Found {len(violations)} silent `except: pass` in production "
                f"(no justification comment):\n\n"
            )
            for v in violations[:30]:  # أول 30 للاختصار
                error_msg += f"  - {v['file']}:{v['line']}  ({v['except_line']})\n"
            if len(violations) > 30:
                error_msg += f"  ... and {len(violations) - 30} more\n"
            error_msg += (
                "\nEvery `except: pass` in production code MUST have a "
                "justification comment before `try:` or on the `except` line. "
                "Format: `# R-XXX: <reason>` or `# TOLERATED: <reason>`.\n"
                "See forensics/silent_failure_audit.md for full list."
            )
            assert False, error_msg

    def test_scan_function_works(self):
        """Test that the scanner runs and returns a list."""
        violations = _scan_silent_exceptions()
        assert isinstance(violations, list)

