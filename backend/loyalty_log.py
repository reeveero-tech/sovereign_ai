#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/loyalty_log.py — سجل العزل الدائم (R-687 — المرحلة ٢ من META_SYSTEM)

أمر المالك 2026-10-18 (المرحلة ٢): «آلية التوجيه: مدخل يقرأ من سجل العزل
(الذي أنشأته في المرحلة ١)». فحص المرحلة صفر لهذه الجولة أثبت أن انتهاكات
LoyaltyContract (المرحلة ١) كانت في الذاكرة فقط — لا سجل دائم. هذه الوحدة
هي الطبقة الدائمة: العقد يكتب (Mr.py)، ومدخل التوجيه يقرأ
(backend/circuit_breaker.py) — فصل القراءة عن الكتابة عبر ملف append-only
واحد، بلا استيراد بينهما (قيد R-686: الكود الحي لا يستورد Mr).

العقد التصميمي:
- append-only: كل سطر حدث JSON كامل ({time, kind, detail, component?}) —
  لا تعديل ولا حذف أبدًا؛ الرفع حدث لاحق لا محو للسابق.
- فشل الكتابة لا يرفع استثناءً أبدًا (يعيد False): التسجيل معزول عن الفشل —
  لا يموت النظام ولا يتعطل بسبب السجل (نفس فلسفة R-686: عزل لا موت).
- الأسطر الممزقة (كتابة مقطوعة بانهيار) تُتخطى في القراءة ولا تُصمت: عدد
  الأسطر المتخطاة يُعاد مع القراءة عند الحاجة للتشخيص.
- آلة حالات المكوّنات: مكوّن معزول = آخر حدث له quarantine؛ مرفوع = بعده
  release. الأحداث بلا مكوّن (عزل العقد العام) لا تعزل مكونات التوجيه —
  عزل العقد مسألة ولاء، والتوجيه مسألة مكونات.
"""

import json
import os
import sys
import threading
from pathlib import Path
from typing import List, Optional, Set

# جذر المستودع — لعمل الوحدة مستوردة من أي مسار (مثل سيناريوهات العزل)
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_MODULE_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# الكتابة متسلسلة عبر قفل واحد — لا سطر ممزق من تداخل خيوط
_WRITE_LOCK = threading.Lock()

# الأحداث التي تقرر حالة التوجيه (مع مكوّن) — غيرها يُسجل ولا يوجه
_QUARANTINE_KIND = "quarantine"
_RELEASE_KIND = "release"


def quarantine_log_path(data_root: Optional[os.PathLike] = None) -> Path:
    """مسار سجل العزل — يُحترم SOVEREIGN_DATA_ROOT (عزل الاختبارات R-619)."""
    root = data_root
    if root is None:
        root = os.getenv("SOVEREIGN_DATA_ROOT") or os.path.join(_REPO_ROOT, "data")
    return Path(root) / "loyalty" / "quarantine_log.jsonl"


def append_entry(
    kind: str,
    detail: str,
    component: Optional[str] = None,
    data_root: Optional[os.PathLike] = None,
) -> bool:
    """إلحاق حدث بالسجل — True عند النجاح، False عند فشل الكتابة (لا استثناء).

    component=None يعني حدث العقد العام (لا يعزل مكونات التوجيه).
    """
    entry = {"time": _now(), "kind": str(kind), "detail": str(detail)}
    if component is not None:
        entry["component"] = str(component)
    line = json.dumps(entry, ensure_ascii=False)
    path = quarantine_log_path(data_root)
    try:
        with _WRITE_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return True
    except OSError:
        # عزل الفشل: السجل لا يقتل النظام أبدًا (فلسفة R-686 — عزل لا موت)
        return False


def read_entries(
    path: Optional[os.PathLike] = None,
) -> List[dict]:
    """قراءة الأحداث — الأسطر الممزقة تُتخطى (انهيار كتابة لا يكسر القراءة)."""
    log_path = Path(path) if path is not None else quarantine_log_path()
    if not log_path.exists():
        return []
    entries: List[dict] = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:  # R-687: سطر ممزق (كتابة قُطعت بانهيار) — يُتخطى لا يُصمت
                continue  # القراءة لا تموت بسطر تالف — العد الكامل قابل للتشخيص
    return entries


def quarantined_components(
    path: Optional[os.PathLike] = None,
) -> Set[str]:
    """المكونات المعزولة الآن: آخر حدث لكل مكوّن يحدد حالته.

    عزل ← معزول، رفع لاحق ← مرفوع. الأحداث بلا مكوّن لا تُدخل في الحساب
    (عزل العقد العام مسألة ولاء لا توجيه).
    """
    components: Set[str] = set()
    for entry in read_entries(path):
        component = entry.get("component")
        if component is None:
            continue
        kind = entry.get("kind")
        if kind == _QUARANTINE_KIND:
            components.add(str(component))
        elif kind == _RELEASE_KIND:
            components.discard(str(component))
    return components


def _now() -> float:
    import time
    return time.time()
