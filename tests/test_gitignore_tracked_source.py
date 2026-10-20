# -*- coding: utf-8 -*-
"""
R-702 — لا شيفرة مصدرية متتبعة مخفية بقواعد .gitignore.

العيب (اكتُشف 2026-10-20): نمط `memory/` في .gitignore (المقصود به مجلد وقت
التشغيل الجذري — «مجلدات وقت تشغيل فارغة») يطابق أيضًا `backend/memory/`
المتتبع (نواة السجل نفسها: core.py وغيره). الأثر: أدوات البحث التي تحترم
.gitignore (rg، والمحررات) تتخطى نواة السجل بصمت — فحص أمني بـ`rg` على
المستودع لا يرى `backend/memory/core.py` إطلاقًا (وقع فعلًا في فحص المرحلة
صفر 2026-10-20 وصُحح يدويًا بـ`--no-ignore`)، وأي ملف جديد هناك لن يُضاف
بـ`git add` العادي.
"""

import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent


def _git(*args):
    return subprocess.run(["git", *args], cwd=_REPO, capture_output=True,
                          text=True)


def test_no_tracked_backend_source_is_gitignored():
    if _git("rev-parse", "--is-inside-work-tree").returncode != 0:
        pytest.skip("ليس مستودع git")
    res = _git("ls-files", "-ci", "--exclude-standard", "--", "backend")
    hidden = [f for f in res.stdout.splitlines() if f.endswith(".py")]
    assert not hidden, (
        f"{len(hidden)} ملف مصدري متتبع تخفيه .gitignore (مثل {hidden[:3]}) — "
        "أدوات البحث ستتخطاه بصمت"
    )


def test_root_runtime_memory_dir_still_ignored():
    """عدم ارتداد: مجلد وقت التشغيل الجذري `memory/` ما زال مُتجاهلًا."""
    if _git("rev-parse", "--is-inside-work-tree").returncode != 0:
        pytest.skip("ليس مستودع git")
    res = _git("check-ignore", "-q", "memory/runtime_probe.json")
    assert res.returncode == 0, "مجلد memory/ الجذري لم يعد مُتجاهلًا"
