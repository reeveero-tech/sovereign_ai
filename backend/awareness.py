#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/awareness.py — طبقة الوعي (R-694 — المرحلة ٣ من خطة المالك)

مواصفة المالك 2026-10-19: «خريطة المشروع: بصمة SHA256 لكل ملف في الشجرة
الحية + بصمة كلية. كشف العبث: عند مقارنة خريطتين (الحالية بالسابقة)، أي
تغيير غير مفسّر يُسجَّل. الربط: الخريطة تُربط بالحارس (المرحلة ٢)، لا
بالتطبيق — الحارس يقرأ الخريطة دوريًا. لا ربط مباشر بـ app.py. لا تعالج
الربط الآمن (المرحلة ٥) — يبقى لقرار المالك. لا تلمس backend/compat».

العقد التصميمي (اعتراضات المراجع — تخطيط R-694):
- stdlib خالص: لا تبعيات — الحارس المعزول يستوردها بأمان بلا HTTP.
- لا خريطة ناقصة أبدًا: تعذر قراءة ملف داخل النطاق = استثناء (لا إسكات).
- الاستثناءات تشغيلية مبررة وموثقة فقط: مخازن VCS وبناء (‎.git،
  __pycache__، ‎.pytest_cache، venv/.venv، node_modules، ‎*.pyc) ومخرجات
  الحارس نفسها (مخزن الخريطة وسجل المراقبة — لا يراقب مخرجاته). لا
  استثناء لمجلد باسم «data» كاملة (قرار المراجع) — ملفات البيانات
  الأخرى داخل النطاق تبقى مرصودة.
- الروابط الرمزية تُتخطى (لا تُتبع) — سياسة موثقة تمنع الحلقات.
- الصيغة القانونية للبصمة الكلية موثقة: SHA256 لسطور «المسار:الهاش»
  مفروزة بمسار الملف — الاختبار يحسبها استقلالًا.
- لا آلية اعتماد أو إصلاح تلقائي هنا: الفروق تُسجَّل كما رُصدت —
  «تغييرات مرصودة غير مفسّرة» (الربط الآمن مرحلة ٥ مؤجل — قرار المالك).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_MODULE_DIR)

# استثناءات تشغيلية بالاسم (مخازن VCS ومخرجات البناء والبيئات) — قائمة
# مغلقة قابلة للتدقيق، لا تعريفًا ضمنيًا من .gitignore
EXCLUDED_DIR_NAMES = frozenset(
    {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
     "venv", ".venv", "node_modules"}
)
EXCLUDED_SUFFIXES = (".pyc", ".pyo")


def _sha256_file(path: Path) -> str:
    """بصمة الملف — تعذر القراءة يستثني (لا خريطة ناقصة صامتة)."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def awareness_map_path(data_root: str | os.PathLike) -> Path:
    """مخزن الخريطة المرجعية — <جذر البيانات>/awareness/project_map.json
    (يُحترم SOVEREIGN_DATA_ROOT للعزل — نفس عقد الحارس R-687)."""
    return Path(data_root) / "awareness" / "project_map.json"


def _is_excluded(rel: str, path: Path, exclude_paths: List[Path]) -> bool:
    """استثناء تشغيلي مبرر: امتداد بناء، أو مسار داخل مخرجات الحارس."""
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    for ex in exclude_paths:
        try:
            path.relative_to(ex)
            return True
        except ValueError:  # R-694: ليس داخل المسار المستثنى — افحص التالي
            continue
    return False


def build_project_map(
    repo_root: str | os.PathLike,
    *,
    exclude_paths: List[str | os.PathLike] | None = None,
) -> Dict[str, str]:
    """خريطة الشجرة الحية: {المسار النسبي posix: sha256}.

    exclude_paths: مسارات داخل الجذر تُستبعد (الحارس يستثني مخرجاته: مخزن
    الخريطة وسجل المراقبة). تعذر قراءة ملف داخل النطاق يرفع OSError —
    لا خريطة ناجحة ناقصة. الروابط الرمزية تُتخطى (سياسة موثقة).
    """
    root = Path(repo_root)
    excluded = [Path(p) for p in (exclude_paths or ())]
    result: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        # استثناء بالاسم أثناء النزول: مخازن VCS/بناء/بيئات — لا ننزل فيها
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(root).parts[:-1]):
            continue
        if path.is_dir():
            continue
        rel = path.relative_to(root).as_posix()
        if path.name in EXCLUDED_DIR_NAMES:
            continue
        if path.is_symlink():
            continue  # سياسة موثقة: الروابط الرمزية لا تُتبع
        if _is_excluded(rel, path, excluded):
            continue
        result[rel] = _sha256_file(path)  # OSError عند تعذر القراءة — لا إسكات
    return result


def overall_fingerprint(project_map: Dict[str, str]) -> str:
    """البصمة الكلية: SHA256 لسطور «المسار:الهاش» مفروزة بالمسار —
    الصيغة القانونية الموثقة (الاختبار يحسبها استقلالًا)."""
    canonical = "\n".join(
        f"{rel}:{sha}" for rel, sha in sorted(project_map.items())
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def diff_maps(
    previous: Dict[str, str], current: Dict[str, str]
) -> Dict[str, List[str]]:
    """فروق خريطتين: {added, removed, modified} — مفروزة، أي تغيير يظهر
    كما رُصد (تغيير مرصود غير مفسّر — لا آلية اعتماد هنا)."""
    added = sorted(set(current) - set(previous))
    removed = sorted(set(previous) - set(current))
    modified = sorted(
        rel for rel in set(previous) & set(current)
        if previous[rel] != current[rel]
    )
    return {"added": added, "removed": removed, "modified": modified}


def save_map(
    project_map: Dict[str, str], store_path: str | os.PathLike
) -> None:
    """حفظ الخريطة المرجعية (JSON: البصمة + الملفات) — يستدعي الحارس بعد
    نجاح إلحاق السجل (الترتيب: مقارنة ← إلحاق ناجح ← حفظ المرجعية)."""
    store = Path(store_path)
    store.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fingerprint": overall_fingerprint(project_map),
        "files": project_map,
    }
    store.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def load_map(store_path: str | os.PathLike) -> Dict[str, str]:
    """تحميل الخريطة المرجعية — التالفة (ValueError) أو غير المقروءة
    (OSError) تستثني: ليست «أول تشغيل» صامتًا يستبدلها — المتصل يسجل
    الخطأ ويُبقي المرجعية كما هي."""
    store = Path(store_path)
    with open(store, "r", encoding="utf-8") as f:
        payload = json.load(f)  # ValueError عند التلف
    files = payload["files"]
    if not isinstance(files, dict):
        raise ValueError(f"مرجعية تالفة: files ليست خريطة — {store}")
    return dict(files)
