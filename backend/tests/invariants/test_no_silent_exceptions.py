"""
Invariant 9: لا except:pass/continue صامت بلا تعليق تبرير (R-680/R-680d)

يستخدم AST (وليس regex) لتحديد المعالجات الصامتة بدقة، ويفحص التعليقات
المرتبطة بها. يفشل إذا وُجد:
- `except: pass` بلا تعليق تبرير
- `except Exception: continue` بلا تعليق تبرير

التعليق المبرر يجب أن يكون:
- على نفس سطر `except` (مثل `except:  # R-680: reason`)
- أو في السطور 1-3 قبل `except` أو قبل `try:` المقابل

الاستثناءات (مجلدات):
- tests/, backend/tests/ (الاختبارات)
- archive/ (أرشيف — غير مُشغّل)
- frontend/ (JavaScript)
- data/ (بيانات)
- guardian/data/emergency (backup)
"""

import ast
import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
for p in [str(_REPO_ROOT), str(_BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


# المجلدات المستثناة من الفحص
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

# أنماط تبرير مقبولة
JUSTIFICATION_RE = re.compile(
    r"#\s*(R-\d+\s*[:\s]|TOLERATED\s*[:\s]|justif|مُبرر|مبرر)"
)

MIN_COMMENT_LENGTH = 8


def _get_except_node_end_lineno(node: ast.ExceptHandler, src: str) -> int:
    """يُعيد رقم السطر الأخير لمعالج except."""
    return getattr(node, "end_lineno", node.lineno)


def _check_comment_on_except_line(node: ast.ExceptHandler, lines: list) -> bool:
    """يفحص التعليق على نفس سطر `except`."""
    except_line = lines[node.lineno - 1]
    if "#" in except_line:
        comment_part = except_line.split("#", 1)[1].strip()
        if (len(comment_part) >= MIN_COMMENT_LENGTH
                and JUSTIFICATION_RE.search(except_line)):
            return True
    return False


def _find_owning_try(node: ast.ExceptHandler, tree: ast.Module) -> ast.Try:
    """يجد عقدة Try التي تملك معالج except هذا (عبر AST، لا بحث نصي).

    R-680e: يربط كل ExceptHandler بـ Try المقابل — لا يسمح بتعليق
    يبرر معالجاً داخلياً أن يُعفي معالجاً خارجياً غير مبرر.
    """
    for try_node in ast.walk(tree):
        if isinstance(try_node, ast.Try):
            if node in try_node.handlers:
                return try_node
    return None


def _check_comment_before_except_or_try(node: ast.ExceptHandler, lines: list,
                                        src: str, tree: ast.Module = None) -> bool:
    """يفحص التعليقات المرتبطة بمعالج except هذا تحديداً.

    R-680e: يربط ExceptHandler بـ Try المالك له عبر AST، ثم يفحص:
    1) تعليق على نفس سطر `except`
    2) تعليق في السطور 1-3 قبل `except` (قبل جسم try مباشرة)
    3) تعليق داخل جسم except (بين `except:` و `pass`) — يبرر هذا المعالج
    4) تعليق في السطور 1-3 قبل `try:` المالك (عبر AST)
    """
    # 0) تعليق داخل جسم except (بين `except:` و `pass`) — يبرر هذا المعالج
    if node.body and len(node.body) == 1:
        stmt = node.body[0]
        for ln in range(node.lineno + 1, stmt.lineno):
            if ln - 1 < len(lines):
                inner_line = lines[ln - 1]
                if "#" in inner_line:
                    comment_part = inner_line.split("#", 1)[1].strip()
                    if (len(comment_part) >= MIN_COMMENT_LENGTH
                            and JUSTIFICATION_RE.search(inner_line)):
                        return True

    # 1) فحص السطور 1-3 قبل `except` مباشرة
    for back in range(1, 4):
        idx = node.lineno - 1 - back
        if idx < 0:
            break
        line = lines[idx]
        stripped = line.strip()
        # تجاهل الأسطر الفارغة
        if not stripped:
            continue
        # تعليق قبل `except` مباشرة
        if "#" in line and not stripped.startswith("try"):
            comment_part = line.split("#", 1)[1].strip()
            if (len(comment_part) >= MIN_COMMENT_LENGTH
                    and JUSTIFICATION_RE.search(line)):
                return True
        break  # أول سطر غير فارغ/غير تعليق → توقف

    # 2) ربط بـ Try المالك عبر AST
    if tree is not None:
        try_node = _find_owning_try(node, tree)
        if try_node is not None:
            # فحص السطور 1-3 قبل `try:`
            for back2 in range(1, 4):
                idx2 = try_node.lineno - 1 - back2
                if idx2 < 0:
                    break
                l2 = lines[idx2]
                if "#" in l2:
                    comment_part = l2.split("#", 1)[1].strip()
                    if (len(comment_part) >= MIN_COMMENT_LENGTH
                            and JUSTIFICATION_RE.search(l2)):
                        return True
            return False
    return False


def _is_silent_except(node: ast.ExceptHandler) -> bool:
    """يحدد إذا كان معالج except صامتاً (pass أو continue)."""
    if len(node.body) != 1:
        return False
    stmt = node.body[0]
    if isinstance(stmt, ast.Pass):
        return True
    # continue
    if isinstance(stmt, ast.Continue):
        return True
    return False


def _scan_silent_exceptions():
    """
    يفحص كل ملفات الإنتاج بحثاً عن `except: pass` أو `except: continue`
    بلا تعليق تبرير. يستخدم AST (لا regex) لدقة أعلى.
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

        # استثناء المجلدات المسموح بها
        if any(rel_posix.startswith(d) for d in EXCLUDED_DIRS):
            continue

        # استثناء هذا الملف نفسه
        if rel_posix == "backend/tests/invariants/test_no_silent_exceptions.py":
            continue

        try:
            src = p.read_text(encoding="utf-8")
        # TOLERATED: unreadable file — excluded from scan (R-680d)
        except Exception:
            continue

        try:
            tree = ast.parse(src)
        # TOLERATED: unparsable AST — excluded from scan (R-680d)
        except SyntaxError:
            continue

        lines = src.split("\n")

        # البحث عن كل معالجات except
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue

            if not _is_silent_except(node):
                continue

            # فحص التعليق
            has_comment = (
                _check_comment_on_except_line(node, lines)
                or _check_comment_before_except_or_try(node, lines, src, tree)
            )

            if not has_comment:
                # تحديد النمط (pass أو continue)
                stmt = node.body[0]
                pattern = "pass" if isinstance(stmt, ast.Pass) else "continue"
                violations.append({
                    "file": rel_posix,
                    "line": node.lineno,
                    "pattern": pattern,
                    "except_line": lines[node.lineno - 1].strip(),
                })

    return violations


class TestNoSilentExceptions:
    """Invariant: كل except صامت (pass/continue) في الإنتاج لديه تعليق تبرير."""

    def test_no_silent_except_in_production(self):
        """يفشل إذا وُجد `except: pass` أو `except: continue` بلا تعليق تبرير."""
        violations = _scan_silent_exceptions()

        if violations:
            error_msg = (
                f"Found {len(violations)} silent `except: pass/continue` in "
                f"production (no justification comment):\n\n"
            )
            for v in violations[:30]:
                error_msg += (
                    f"  - {v['file']}:{v['line']}  "
                    f"({v['except_line']})  [pattern={v['pattern']}]\n"
                )
            if len(violations) > 30:
                error_msg += f"  ... and {len(violations) - 30} more\n"
            error_msg += (
                "\nEvery silent `except` in production code MUST have a "
                "justification comment before `try:` or on the `except` line. "
                "Format: `# R-XXX: <reason>` or `# TOLERATED: <reason>`.\n"
                "See forensics/silent_failure_audit.md for full list."
            )
            assert False, error_msg

    def test_scan_function_works(self):
        """Test that the AST scanner runs and returns a list."""
        violations = _scan_silent_exceptions()
        assert isinstance(violations, list)

    def test_detects_bare_except_pass_no_comment(self, tmp_path):
        """اختبار صغير: يثبت أن الماسح يكشف `except: pass` بلا تعليق (AST-based)."""
        # ملف مؤقت بمحتوى صامت — نحفظه ثم نفحص
        content = "try:\n    x = 1\nexcept Exception:\n    pass\n"
        test_file = tmp_path / "sample_silent.py"
        test_file.write_text(content, encoding="utf-8")

        # نُشغّل الماسح يدوياً على المحتوى
        import ast as ast_mod
        tree = ast_mod.parse(content)
        lines = content.split("\n")
        found = False
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.ExceptHandler):
                if _is_silent_except(node):
                    if not (_check_comment_on_except_line(node, lines)
                            or _check_comment_before_except_or_try(node, lines, content, tree)):
                        found = True
        assert found, "Scanner must detect silent except:pass with no comment"

    def test_detects_bare_except_continue_no_comment(self, tmp_path):
        """اختبار صغير: يثبت أن الماسح يكشف `except: continue` بلا تعليق."""
        content = "for i in range(10):\n    try:\n        x = i\n    except Exception:\n        continue\n"
        import ast as ast_mod
        tree = ast_mod.parse(content)
        lines = content.split("\n")
        found = False
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.ExceptHandler):
                if _is_silent_except(node):
                    if not (_check_comment_on_except_line(node, lines)
                            or _check_comment_before_except_or_try(node, lines, content, tree)):
                        found = True
        assert found, "Scanner must detect silent except:continue with no comment"

    def test_accepts_justified_except(self, tmp_path):
        """اختبار صغير: يثبت أن الماسح يقبل `except: pass` مع تعليق تبرير."""
        content = (
            "# TOLERATED: test justification (R-680)\n"
            "try:\n    x = 1\nexcept Exception:\n    pass\n"
        )
        import ast as ast_mod
        tree = ast_mod.parse(content)
        lines = content.split("\n")
        found_unjustified = False
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.ExceptHandler):
                if _is_silent_except(node):
                    if not (_check_comment_on_except_line(node, lines)
                            or _check_comment_before_except_or_try(node, lines, content, tree)):
                        found_unjustified = True
        assert not found_unjustified, (
            "Scanner must NOT flag except:pass with TOLERATED comment"
        )


    def test_inner_justification_does_not_excuse_outer(self, tmp_path):
        """R-680e: تعليق يبرر معالجاً داخلياً لا يبرر المعالج الخارجي.

        الحالة: try خارجي (غير مبرر) يحتوي try داخلي (مبرر).
        الماسح يجب أن يُبلغ عن المعالج الخارجي، لا أن يُعفيه بتعليق الداخلي.
        """
        content = (
            "try:\n"                              # try خارجي — سطر 1
            "    try:\n"                          # try داخلي
            "        x = 1\n"
            "    except Exception:\n"             # معالج داخلي — مبرر
            "        # TOLERATED: inner justified (R-680e)\n"
            "        pass\n"
            "except Exception:\n"                  # معالج خارجي — غير مبرر
            "    pass\n"
        )
        import ast as ast_mod
        tree = ast_mod.parse(content)
        lines = content.split("\n")

        # الماسح يجب أن يكتشف المعالج الخارجي (غير مبرر)
        outer_found = False
        inner_found = False
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.ExceptHandler):
                if not _is_silent_except(node):
                    continue
                justified = (
                    _check_comment_on_except_line(node, lines)
                    or _check_comment_before_except_or_try(node, lines, content, tree)
                )
                if justified:
                    inner_found = True
                else:
                    outer_found = True
        # المعالج الداخلي مبرر، الخارجي غير مبرر
        assert inner_found, "inner must be justified"
        assert outer_found, "outer must NOT be justified by inner comment"

