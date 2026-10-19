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


# ---------- R-687: نفس القاعدة لمدخل الحارس ومدخل التوجيه ----------

def _r687_commit_range():
    """
    مدخل R-687 مثبت على التزام R-687 وأبيه — لا بآخر التزامين
    (نفس منطق R-686 أعلاه: يصمد بعد أي التزام لاحق).
    """
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-687", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-687 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]


def _r687_git_numstat():
    r687, parent = _r687_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r687}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r687_audit_rows():
    """صفوف مدخل R-687 فقط — القسم ينتهي عند أول عنوان ## لاحق."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-687")
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


def test_audit_r687_matches_git_numstat():
    numstat = _r687_git_numstat()
    audit = _r687_audit_rows()
    assert audit, "مدخل R-687 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff لالتزام R-687 أعاد صفوفًا فارغة"

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
        "مدخل التدقيق R-687 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r687_total_matches():
    """الإجمالي المعلن في مدخل R-687 يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-687")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-687"
    numstat = _r687_git_numstat()
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


# ---------- R-688: نفس القاعدة لجولة إصلاحات اعتراضات المراجع ----------

def _r688_commit_range():
    """مدخل R-688 مثبت على التزام R-688 وأبيه (cc83a51) — لا بآخر التزامين."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-688", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-688 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]


def _r688_git_numstat():
    r688, parent = _r688_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r688}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r688_audit_rows():
    """صفوف مدخل R-688 فقط — القسم ينتهي عند أول عنوان ## لاحق."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-688")
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


def test_audit_r688_matches_git_numstat():
    numstat = _r688_git_numstat()
    audit = _r688_audit_rows()
    assert audit, "مدخل R-688 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff لالتزام R-688 أعاد صفوفًا فارغة"

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
        "مدخل التدقيق R-688 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r688_total_matches():
    """الإجمالي المعلن في مدخل R-688 يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-688")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-688"
    numstat = _r688_git_numstat()
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


# ---------- R-689: نفس القاعدة لجولة اعتراضات المراجع ج2 ----------

def _r689_commit_range():
    """مدخل R-689 مثبت على التزام R-689 وأبيه (fa77b1e) — لا بآخر التزامين."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-689", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-689 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]


def _r689_git_numstat():
    r689, parent = _r689_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r689}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r689_audit_rows():
    """صفوف مدخل R-689 فقط — القسم ينتهي عند أول عنوان ## لاحق."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-689")
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


def test_audit_r689_matches_git_numstat():
    numstat = _r689_git_numstat()
    audit = _r689_audit_rows()
    assert audit, "مدخل R-689 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff لالتزام R-689 أعاد صفوفًا فارغة"

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
        "مدخل التدقيق R-689 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r689_total_matches():
    """الإجمالي المعلن في مدخل R-689 يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-689")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-689"
    numstat = _r689_git_numstat()
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


# ---------- R-690: نفس القاعدة لجولة اعتراضات المراجع ج3 ----------

def _r690_commit_range():
    """مدخل R-690 مثبت على التزام R-690 وأبيه (bc11f2a) — لا بآخر التزامين."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-690", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-690 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]


def _r690_git_numstat():
    r690, parent = _r690_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r690}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r690_audit_rows():
    """صفوف مدخل R-690 فقط — القسم ينتهي عند أول عنوان ## لاحق."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-690")
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


def test_audit_r690_matches_git_numstat():
    numstat = _r690_git_numstat()
    audit = _r690_audit_rows()
    assert audit, "مدخل R-690 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff لالتزام R-690 أعاد صفوفًا فارغة"

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
        "مدخل التدقيق R-690 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r690_total_matches():
    """الإجمالي المعلن في مدخل R-690 يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-690")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-690"
    numstat = _r690_git_numstat()
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


# ---------- R-691: نفس القاعدة لجولة اعتراضات المراجع ج4 ----------

def _r691_commit_range():
    """مدخل R-691 مثبت على التزام R-691 وأبيه (d3a06e0) — لا بآخر التزامين."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-691", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-691 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]


def _r691_git_numstat():
    r691, parent = _r691_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r691}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r691_audit_rows():
    """صفوف مدخل R-691 فقط — القسم ينتهي عند أول عنوان ## لاحق."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-691")
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


def test_audit_r691_matches_git_numstat():
    numstat = _r691_git_numstat()
    audit = _r691_audit_rows()
    assert audit, "مدخل R-691 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff لالتزام R-691 أعاد صفوفًا فارغة"

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
        "مدخل التدقيق R-691 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r691_total_matches():
    """الإجمالي المعلن في مدخل R-691 يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-691")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-691"
    numstat = _r691_git_numstat()
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


# ---------- R-692: نفس القاعدة لجولة اعتراضات المراجع ج5 ----------

def _r692_commit_range():
    """مدخل R-692 مثبت على التزام R-692 وأبيه (1580189) — لا بآخر التزامين."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-692", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-692 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]


def _r692_git_numstat():
    r692, parent = _r692_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r692}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r692_audit_rows():
    """صفوف مدخل R-692 فقط — القسم ينتهي عند أول عنوان ## لاحق."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-692")
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


def test_audit_r692_matches_git_numstat():
    numstat = _r692_git_numstat()
    audit = _r692_audit_rows()
    assert audit, "مدخل R-692 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff لالتزام R-692 أعاد صفوفًا فارغة"

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
        "مدخل التدقيق R-692 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r692_total_matches():
    """الإجمالي المعلن في مدخل R-692 يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-692")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-692"
    numstat = _r692_git_numstat()
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


# ---------- R-693: نفس القاعدة لجولات اعتراضات المراجع ج6–ج10 ----------

def _r693_commit_range():
    """مدخل R-693 مثبت على التزام R-693 وأبيه (96fd16a) — لا بآخر التزامين."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-693", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-693 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]


def _r693_git_numstat():
    r693, parent = _r693_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r693}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r693_audit_rows():
    """صفوف مدخل R-693 فقط — القسم ينتهي عند أول عنوان ## لاحق أو نهاية الملف."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-693")
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


def test_audit_r693_matches_git_numstat():
    numstat = _r693_git_numstat()
    audit = _r693_audit_rows()
    assert audit, "مدخل R-693 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff لالتزام R-693 أعاد صفوفًا فارغة"

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
        "مدخل التدقيق R-693 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r693_total_matches():
    """الإجمالي المعلن في مدخل R-693 يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-693")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-693"
    numstat = _r693_git_numstat()
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


# ---------- R-694: المرحلة ٣ — طبقة الوعي (خريطة المشروع وكشف العبث) ----------

def _r694_commit_range():
    """مدخل R-694 مثبت على التزام R-694 وأبيه (1deb940) — لا بآخر التزامين."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-694", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, (
        "التزام R-694 غير موجود في تاريخ git — مدخل التدقيق بلا مرجع"
    )
    return parts[0], parts[1]


def _r694_git_numstat():
    r694, parent = _r694_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r694}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r694_audit_rows():
    """صفوف مدخل R-694 فقط — القسم آخر مدخل (ينتهي عند أول ## لاحق أو نهاية الملف)."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-694")
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


def test_audit_r694_matches_git_numstat():
    numstat = _r694_git_numstat()
    audit = _r694_audit_rows()
    assert audit, "مدخل R-694 في جدول التدقيق غير موجود أو صفر الصفوف"
    assert numstat, "git diff لالتزام R-694 أعاد صفوفًا فارغة"

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
        "مدخل التدقيق R-694 لا يطابق git — القاعدة: أرقام من numstat "
        "الفعلي:\n  " + "\n  ".join(mismatches)
    )


def test_audit_r694_total_matches():
    """الإجمالي المعلن في مدخل R-694 يطابق مجموع git حرفيًا."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-694")
    section = src[start:]
    m = re.search(
        r"الإجمالي: ([\d,]+) إضافة / ([\d,]+) حذفًا في (\d+) ملف", section
    )
    assert m, "سطر الإجمالي غير موجود في مدخل R-694"
    numstat = _r694_git_numstat()
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


# ---------- R-694 — مدخل تصحيحات المراجع ج2–ج3 (التزام منفصل فوق 17c17de) ----------

def _r694b_corrections_commit():
    """التزام التصحيحات ج2–ج3 — يثبَّت برسالته لا بترتيبه (التزامات
    الأدلة اللاحقة لا تحمل هذه العبارة فلا تُخطئ)."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P",
         "--grep=تصحيحات المراجع ج2–ج3 للمرحلة ٣", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, "التزام تصحيحات ج2–ج3 غير موجود في تاريخ git"
    return parts[0], parts[1]


def _r694b_numstat():
    r694b, parent = _r694b_corrections_commit()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r694b}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r694b_section_rows():
    """قسم التصحيحات من الملف الحالي: الصفوف + الإجمالي + صفوف المبررات."""
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة تصحيحات المراجع ج2–ج3 لـR-694")
    lines = src[start:].splitlines()
    end_idx = len(lines)
    for i, line in enumerate(lines[1:], start=1):
        if line.startswith("## "):
            end_idx = i
            break
    section = lines[:end_idx]
    rows = {}
    justifications = {}
    total = None
    for line in section:
        m = _ROW.match(line)
        if m:
            rows[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        if "DELETION-JUSTIFIED" in line and line.startswith("| `"):
            name = line.split("`")[1]
            justifications[name] = line
        m = re.search(
            r"الإجمالي: ([\d,]+) إضافة / (\d+) حذفًا في (\d+) ملف", line
        )
        if m and total is None:
            total = (
                int(m.group(1).replace(",", "")), int(m.group(2)),
                int(m.group(3)),
            )
    return rows, justifications, total


def test_audit_r694b_rows_and_total_match_git():
    """كل صفوف مدخل التصحيحات وإجماليُّه تطابق git حرفيًا (اعتراض إغلاق
    المراجع: التزام عادي آخر يُوثَّق ويتحقق آليًا — لا يكشفه تدقيق الأصل)."""
    rows, _, total = _r694b_section_rows()
    numstat = _r694b_numstat()
    assert rows, "مدخل التصحيحات بلا صفوف — لم يُصلح بعد؟"
    assert total, "سطر الإجمالي غائب من مدخل التصحيحات"
    mismatches = []
    for name, declared in sorted(rows.items()):
        actual = numstat.get(name)
        if actual is None:
            mismatches.append(f"{name}: في التدقيق وليس في git")
        elif actual != declared:
            mismatches.append(
                f"{name}: التدقيق {declared} ≠ git {actual}"
            )
    missing = [n for n in numstat if n not in rows]
    if missing:
        mismatches.append("في git بلا صف: " + ", ".join(sorted(missing)))
    assert not mismatches, "مدخل التصحيحات لا يطابق git:\n  " + "\n  ".join(mismatches)
    ta = sum(v[0] for v in numstat.values())
    td = sum(v[1] for v in numstat.values())
    assert total == (ta, td, len(numstat)), (
        f"الإجمالي المعلن {total} ≠ git {(ta, td, len(numstat))}"
    )


def test_audit_r694b_justifications_cover_exactly_deletions():
    """المبررات تغطي الحذف الفعلي حصرًا: كل ملف له حذف له صف مُعلَّل،
    ولا تعليل لملف بلا حذف (اعتراض المراجع: نسبة حذف لملفات لم تُحذف)."""
    _, justifications, _ = _r694b_section_rows()
    numstat = _r694b_numstat()
    actually_deleted = {n for n, (a, d) in numstat.items() if d > 0}
    justified = set(justifications)
    missing = actually_deleted - justified
    extra = justified - actually_deleted
    assert not missing, "حذف بلا مبرر: " + ", ".join(sorted(missing))
    assert not extra, "مبرر لملف بلا حذف فعلي: " + ", ".join(sorted(extra))
    for name, row in justifications.items():
        assert "# DELETION-JUSTIFIED" in row, f"مبرر بلا الوسم: {name}"


# ---------- R-695: المرحلة ٤ — مصنف الأخطاء ومقترح الرقع ----------

def _r695_commit_range():
    """مدخل R-695 مثبت على التزام R-695 وأبيه (62375e0) — لا بآخر التزامين."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P", "--grep=^R-695", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, "التزام R-695 غير موجود في تاريخ git"
    return parts[0], parts[1]


def _r695_git_numstat():
    r695, parent = _r695_commit_range()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r695}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    result = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        result[name] = (int(a), int(d))
    return result


def _r695_section():
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة R-695")
    lines = src[start:].splitlines()
    end_idx = len(lines)
    for i, line in enumerate(lines[1:], start=1):
        if line.startswith("## "):
            end_idx = i
            break
    rows, justifications, total = {}, {}, None
    for line in lines[:end_idx]:
        m = _ROW.match(line)
        if m:
            rows[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        if "DELETION-JUSTIFIED" in line and line.startswith("| `"):
            justifications[line.split("`")[1]] = line
        m = re.search(r"الإجمالي: ([\d,]+) إضافة / (\d+) حذفًا في (\d+) ملف", line)
        if m and total is None:
            total = (int(m.group(1).replace(",", "")), int(m.group(2)),
                     int(m.group(3)))
    return rows, justifications, total


def test_audit_r695_rows_total_and_justifications_match_git():
    """مدخل R-695: الصفوف والإجمالي والمبررات تطابق git حرفيًا — الحذف بلا
    مبرر يفشل، والمبرر لملف بلا حذف يفشل (عقد المراجع R-694 ج2 مجددًا)."""
    rows, justifications, total = _r695_section()
    numstat = _r695_git_numstat()
    assert rows, "مدخل R-695 بلا صفوف"
    assert total, "سطر الإجمالي غائب من مدخل R-695"
    mismatches = []
    for name, declared in sorted(rows.items()):
        actual = numstat.get(name)
        if actual is None:
            mismatches.append(f"{name}: في التدقيق وليس في git")
        elif actual != declared:
            mismatches.append(f"{name}: التدقيق {declared} ≠ git {actual}")
    missing = [n for n in numstat if n not in rows]
    if missing:
        mismatches.append("في git بلا صف: " + ", ".join(sorted(missing)))
    assert not mismatches, "مدخل R-695 لا يطابق git:\n  " + "\n  ".join(mismatches)
    ta = sum(v[0] for v in numstat.values())
    td = sum(v[1] for v in numstat.values())
    assert total == (ta, td, len(numstat)), (
        f"الإجمالي المعلن {total} ≠ git {(ta, td, len(numstat))}"
    )
    actually_deleted = {n for n, (a, d) in numstat.items() if d > 0}
    justified = set(justifications)
    assert not (actually_deleted - justified), "حذف بلا مبرر"
    assert not (justified - actually_deleted), "مبرر لملف بلا حذف فعلي"
    for name, row in justifications.items():
        assert "# DELETION-JUSTIFIED" in row, f"مبرر بلا الوسم: {name}"


# ---------- R-695 — مدخل تصحيحات المراجع ج2 (التزام منفصل فوق 5e8bc03) ----------

def _r695b_corrections_commit():
    """التزام تصحيحات ج2 لـR-695 — يثبت برسالته (لا بترتيبه؛ التزامات
    الأدلة اللاحقة لا تحمل العبارة)."""
    proc = subprocess.run(
        ["git", "log", "--format=%H %P",
         "--grep=تصحيحات المراجع ج2 لـR-695", "-1", "--no-merges"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    parts = proc.stdout.strip().split()
    assert len(parts) >= 2, "التزام تصحيحات ج2 لـR-695 غير موجود في تاريخ git"
    return parts[0], parts[1]


def test_audit_r695b_corrections_entry_matches_git():
    """مدخل التصحيحات: الصفوف والإجمالي والمبررات تطابق git حرفيًا —
    الحذف بلا مبرر يفشل والمبرر لملف بلا حذف يفشل (عقد R-694 ج2)."""
    r695b, parent = _r695b_corrections_commit()
    proc = subprocess.run(
        ["git", "diff", "--numstat", f"{parent}..{r695b}"],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), check=True,
    )
    numstat = {}
    for line in proc.stdout.strip().splitlines():
        a, d, name = line.split("\t")
        numstat[name] = (int(a), int(d))
    src = _AUDIT.read_text(encoding="utf-8")
    start = src.index("## إضافة تصحيحات المراجع ج2 لـR-695")
    lines = src[start:].splitlines()
    end_idx = len(lines)
    for i, line in enumerate(lines[1:], start=1):
        if line.startswith("## "):
            end_idx = i
            break
    rows, justifications, total = {}, {}, None
    for line in lines[:end_idx]:
        m = _ROW.match(line)
        if m:
            rows[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        if "DELETION-JUSTIFIED" in line and line.startswith("| `"):
            justifications[line.split("`")[1]] = line
        m = re.search(r"الإجمالي: ([\d,]+) إضافة / (\d+) حذفًا في (\d+) ملف", line)
        if m and total is None:
            total = (int(m.group(1).replace(",", "")), int(m.group(2)),
                     int(m.group(3)))
    assert rows and total, "مدخل التصحيحات ناقص"
    mismatches = []
    for name, declared in sorted(rows.items()):
        actual = numstat.get(name)
        if actual is None:
            mismatches.append(f"{name}: في التدقيق وليس في git")
        elif actual != declared:
            mismatches.append(f"{name}: التدقيق {declared} ≠ git {actual}")
    missing = [n for n in numstat if n not in rows]
    if missing:
        mismatches.append("في git بلا صف: " + ", ".join(sorted(missing)))
    assert not mismatches, "مدخل تصحيحات R-695 لا يطابق git:\n  " + "\n  ".join(mismatches)
    ta = sum(v[0] for v in numstat.values())
    td = sum(v[1] for v in numstat.values())
    assert total == (ta, td, len(numstat)), (
        f"الإجمالي {total} ≠ git {(ta, td, len(numstat))}"
    )
    actually_deleted = {n for n, (a, d) in numstat.items() if d > 0}
    assert not (actually_deleted - set(justifications)), "حذف بلا مبرر"
    assert not (set(justifications) - actually_deleted), "مبرر بلا حذف فعلي"
    for name, row in justifications.items():
        assert "# DELETION-JUSTIFIED" in row, f"مبرر بلا الوسم: {name}"
