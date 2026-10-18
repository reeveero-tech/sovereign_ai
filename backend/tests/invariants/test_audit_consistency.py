# -*- coding: utf-8 -*-
"""
Invariant: مطابقة مدخل التدقيق مع git حرفيًا (R-686)

قاعدة المشروع الدائمة: أرقام الحذف توثق من numstat الفعلي. هذا الاختبار
يجعل كل صف في مدخل R-686 بجدول DELETED_LINES_AUDIT.md مقارنًا مباشرةً
بـ`git diff --numstat HEAD~1..HEAD` — أي انحراف رقمي أو ملف ناقص/زائد
يفشل الاختبار. لا ادعاء توثيقي بلا مطابقة git.
"""

import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUDIT = _REPO_ROOT / "forensics" / "DELETED_LINES_AUDIT.md"

# صف المدخل بهذا الشكل: - `path`: +N / −D
_ROW = re.compile(r"^- `([^`]+)`: \+(\d+) / −(\d+)$")


def _r686_commit_range():
    """
    مدخل R-686 تاريخي ثابت — المقارنة تُربط بالتزام R-686 نفسه وأبيه،
    لا بآخر التزامين (وإلا فشل الحارس بعد أول التزام لاحق غير متعلق).
    """
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-686", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-686 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]  # (التزام R-686، أبوه)


def _git_numstat():
    """numstat التزام R-686 مقابل أبيه — من git الفعلي (مثبت لا متغير)."""
    r686, parent = _r686_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r686}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _audit_rows():
    """
    صفوف مدخل R-686 فقط من جدول التدقيق — القسم ينتهي عند أول عنوان
    من المستوى نفسه بعده (## إضافة R-687 لاحقًا لا يُبتلع في R-686).
    """
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-686")
    lines = src[start:].splitlines()
    end_idx = len(lines)
    for i, line in enumerate(lines[1:], start=1):
        if line.startswith("## "):
            end_idx = i
            break
    rows = {}
    for line in lines[:end_idx]:
        m = _ROW.match(line)
        if m:
            rows[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    return rows


def test_audit_r686_matches_git_numstat():
    numstat = _git_numstat()
    audit = _audit_rows()
    assert audit, "مدخل R-686 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff HEAD~1..HEAD أعاد صفوفًا فارغة — بيئة بلا تاريخ؟"

    mismatches = []
    for name, declared in sorted(audit.items()):
        actual = numstat.get(name)
        if actual is None:
            mismatches.append(f"{name}: موجود في التدقيق وليس في git")
        elif actual != declared:
            mismatches.append(
                f"{name}: التدقيق يقول {declared} وgit يقول {actual}"
            )
    missing = [n for n in numstat if n not in audit]
    if missing:
        mismatches.append(
            "ملفات في git بلا صف في التدقيق: " + ", ".join(sorted(missing))
        )
    assert not mismatches, (
        "مدخل التدقيق R-686 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r686_total_matches():
    """الإجمالي المعلن في المدخل يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-686")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-686"
    numstat = _git_numstat()
    total_a = sum(v[0] for v in numstat.values())
    total_d = sum(v[1] for v in numstat.values())
    assert int(m.group(1).replace(",", "")) == total_a, (
        f"إجمالي الإضافات المعلن {m.group(1)} ≠ git {total_a}"
    )
    assert int(m.group(2).replace(",", "")) == total_d, (
        f"إجمالي الحذوفات المعلن {m.group(2)} ≠ git {total_d}"
    )
    assert int(m.group(3)) == len(numstat), (
        f"عدد الملفات المعلن {m.group(3)} ≠ git {len(numstat)}"
    )
