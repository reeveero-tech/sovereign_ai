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
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set

# جذر المستودع — لعمل الوحدة مستوردة من أي مسار (مثل سيناريوهات العزل)
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_MODULE_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

logger = logging.getLogger("backend.loyalty_log")

# الكتابة متسلسلة عبر قفل واحد — لا سطر ممزق من تداخل خيوط
_WRITE_LOCK = threading.Lock()

# R-688 (اعتراض المراجع): احتياط في ذاكرة العملية للأحداث التي فشل توثيقها
# على القرص — مفاتيحه مسارات السجل نفسها (عزل جذور الاختبارات عن بعضها).
# الهدف: فشل التوثيق مرئي لا صامت — المدخل في نفس العملية يرى الحدث رغم فشل
# القرص، وفشل الكتابة يعيد False ويطلق تحذيرًا مسموعًا (لا ابتلاع).
_FALLBACK_LOCK = threading.Lock()
_FALLBACK: Dict[str, List[dict]] = {}

# R-689 (اعتراض المراجع ج2): عداد نسخ للاحتياط — بصمة كاش المدخل تشمله
# حتى لا يخدم الكاش الدافئ حالة قديمة بعد إلحاق فشل توثيقه (ذهب للاحتياط)
_FALLBACK_VERSION = 0

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
    """إلحاق حدث بالسجل — True عند نجاح التوثيق على القرص، False عند فشله
    (لا استثناء أبدًا). عند الفشل: الحدث لا يضيع صامتًا — يُحفظ في احتياط ذاكرة
    العملية (يقرؤه مدخل التوجيه في نفس العملية) ويُطلق تحذير مسموع.

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
        # R-688 (اعتراض المراجع): فشل التوثيق لا يجوز أن يتحول سماحًا صامتًا —
        # الحدث يبقى مرئيًا في ذاكرة هذه العملية + تحذير مسموع، والقرص يُعاد
        # في الدورة التالية (عزل الفشل لا موت ولا صمت)
        global _FALLBACK_VERSION
        with _FALLBACK_LOCK:
            _FALLBACK.setdefault(str(path), []).append(entry)
            _FALLBACK_VERSION += 1
        logger.warning(
            "فشل توثيق حدث سجل العزل على القرص (%s) — محفوظ في احتياط الذاكرة "
            "لهذه العملية: kind=%s component=%s",
            path, entry["kind"], entry.get("component"),
        )
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
    """المكونات المعزولة الآن — دمج مصدري الإثبات:

    ١) الملف: آخر حدث لكل مكوّن يحدد حالته (عزل ← معزول، رفع ← مرفوع).
    ٢) احتياط الذاكرة (أحداث فشل توثيقها في هذه العملية): **العزل فقط نافذ** —
       الرفع الفاشل التوثيق غير منفذ (R-690 — اعتراض المراجع ج3: فشل
       التوثيق لا يفتح بوابة؛ اتجاه آمن، والرفع الموثق وحده يرفع).

    الأحداث بلا مكوّن لا تدخل في الحساب (عزل العقد العام مسألة ولاء لا توجيه).
    يرفع OSError إذا كان السجل موجودًا لكنه غير قابل للقراءة — الحالة غير
    القابلة للإثبات قرار المتصل (المدخل يغلق، لا يسكت).
    """
    log_path = Path(path) if path is not None else quarantine_log_path()
    # أحداث فعالة مرتبة زمنيًا: الملف (عزل+رفع نافذان) + عزل الاحتياط فقط
    # (الرفع الفاشل التوثيق مستبعد من التنفيذ — R-690) — الترتيب زمني
    # فيسمح الرفع الموثق اللاحق بإنهاء عزل سابق فشل توثيقه في الاحتياط
    # (R-691 — اعتراض المراجع ج4)
    events: List[tuple] = []
    for entry in read_entries(log_path):  # يرفع OSError إذا موجود وغير مقروء
        events.append(
            (entry.get("time", 0), entry.get("kind"), entry.get("component"))
        )
    with _FALLBACK_LOCK:
        for entry in _FALLBACK.get(str(log_path), []):
            if entry.get("kind") == _QUARANTINE_KIND:
                events.append(
                    (entry.get("time", 0), entry.get("kind"), entry.get("component"))
                )
    events.sort(key=lambda e: e[0])
    components: Set[str] = set()
    for _, kind, component in events:
        if component is None:
            continue
        if kind == _QUARANTINE_KIND:
            components.add(str(component))
        elif kind == _RELEASE_KIND:
            components.discard(str(component))
    return components


def _merged_entries(log_path: Path) -> List[dict]:
    """أحداث الملف (إن كان قابلًا للقراءة) + احتياط الذاكرة لمساره — مرتبة
    زمنيًا. غياب الملف مشروع (لا عزل على القرص)؛ وجوده غير المقروء يُرفع
    (OSError) لا يُصمت."""
    with _FALLBACK_LOCK:
        fallback = list(_FALLBACK.get(str(log_path), []))
    file_entries = read_entries(log_path)  # يرفع OSError إذا موجود وغير مقروء
    merged = file_entries + fallback
    merged.sort(key=lambda e: e.get("time", 0))
    return merged


def clear_fallback(path: Optional[os.PathLike] = None) -> None:
    """تفريغ احتياط الذاكرة (أداة اختبار — عزل الاختبارات عن بعضها)."""
    global _FALLBACK_VERSION
    with _FALLBACK_LOCK:
        if path is None:
            _FALLBACK.clear()
        else:
            _FALLBACK.pop(str(Path(path)), None)
        _FALLBACK_VERSION += 1


def fallback_version() -> int:
    """نسخة الاحتياط — تتغير عند كل إلحاق/تفريغ (تدخل بصمة كاش المدخل)."""
    with _FALLBACK_LOCK:
        return _FALLBACK_VERSION


def fallback_quarantined(path: Optional[os.PathLike] = None) -> Set[str]:
    """المكونات المعزولة من احتياط الذاكرة فقط (بلا قراءة الملف) — أدق
    مصدر متاح في هذه العملية للأحداث التي فشل توثيقها على القرص.
    R-690: **العزل فقط نافذ** — أحداث الرفع الفاشلة التوثيق تُتجاهل هنا
    (الرفع غير الموثق لا يُنفذ: لا يفتح بوابة) لكنها تبقى مرئية كسجل
    انتهاكات (اقرأها المتصل إن احتاج الإثبات)."""
    log_path = Path(path) if path is not None else quarantine_log_path()
    with _FALLBACK_LOCK:
        entries = list(_FALLBACK.get(str(log_path), []))
    components: Set[str] = set()
    for entry in entries:
        component = entry.get("component")
        if component is None:
            continue
        if entry.get("kind") == _QUARANTINE_KIND:
            components.add(str(component))
    return components


def _now() -> float:
    import time
    return time.time()
