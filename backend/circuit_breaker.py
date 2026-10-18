#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/circuit_breaker.py — مدخل التوجيه (R-687 — المرحلة ٢ من META_SYSTEM)

أمر المالك 2026-10-18: «آلية التوجيه: مدخل يقرأ من سجل العزل، ويرفض توجيه
الطلبات للمكونات المعزولة (يرجع خطأ محدد)، بينما تستمر بقية المكونات
بالعمل».

العقد التصميمي:
- يقرأ سجل العزل الدائم (backend/loyalty_log) — لا يستورد Mr إطلاقًا
  (قيد R-686: الكود الحي لا يرتبط بعقد الولاء)؛ الفصل عبر الملف.
- الحجب لمسارات المكونات فقط (/components/<name>) — بقية المسارات
  (صحة/محادثة/سجل...) لا تُحجب أبدًا: العزل مكوّن لا نظام.
- الاستجابة محددة: 503 + {error: component_quarantined, component, detail}
  — رفض صريح قابل للتشخيص، لا صمت ولا 500.
- قراءة السجل مُخزنة مؤقتًا ببصمة (mtime+size) — لا قراءة قرص لكل طلب
  إلا عند تغيّر السجل (الكتابة الحية تعزل التوجيه خلال دورة الكشف).
"""

import os
import re
import sys
import threading
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_MODULE_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import logging

logger = logging.getLogger("backend.circuit_breaker")

from backend.loyalty_log import (
    fallback_quarantined,
    fallback_version,
    quarantine_log_path,
    quarantined_components,
)

# مسار مكوّن فقط — لا شيء آخر يُحجب
_COMPONENT_ROUTE = re.compile(r"^/components/([a-z][a-z0-9_]*)$")

# R-688 (مسح نطاق التوجيع — اعتراض المراجع): مسارات الميزات التي تخاطب
# مكوّنًا بالاسم (ليست عرض حالة فقط) — طلب موجه للمكوّن فعلًا. يرفضه المدخل
# عند عزل مكوّنه، وبقية المسارات تعمل. حارس بنيوي يمنع تقادم الخريطة
# (test_feature_route_map_has_no_stale_entries).
_COMPONENT_PATH_MAP = {
    "/nexus/recommendations/live": "nexus",
    "/nexus/recommendations/pending": "nexus",
    "/sovereign/command": "sovereign",
    "/sovereign/reset": "sovereign",
}

# R-689 (اعتراض المراجع ج2): أسباب الحالة غير القابلة للإثبات — تُعاد كسلسلة
# سبب بدل مجموعة، والوسيط يردّ 503 بخطأ محدد حرفيًا حرف السبب:
#   "unreadable" — سجل موجود لا يمكن قراءته
#   "unwritable" — قناة الكتابة معطوبة (لا يمكن توثيق عزل جديد ولا ائتمان
#                  اكتمال الحالة) — الإغلاق على مسارات المكونات فقط
_REASON_UNREADABLE = "unreadable"
_REASON_UNWRITABLE = "unwritable"

# فحص صحة قناة الكتابة — TTL قصير (قابل للضبط بيئيًا للاختبارات)
_PROBE_TTL = float(os.getenv("SOVEREIGN_BREAKER_PROBE_TTL", "2.0"))
_PROBE_LOCK = threading.Lock()
_PROBE = {"ts": 0.0, "ok": True}


def _channel_writable() -> bool:
    """صحة قناة الكتابة من هذه العملية: فتح للإلحاق بلا كتابة يكشف صلاحية
    الكتابة على الملف/المجلد — بذاكرة TTL (لا فحص لكل طلب)."""
    import time as _time
    now = _time.monotonic()
    with _PROBE_LOCK:
        if now - _PROBE["ts"] < _PROBE_TTL:
            return _PROBE["ok"]
        _PROBE["ts"] = now
    ok = _probe_appendable(quarantine_log_path())
    with _PROBE_LOCK:
        _PROBE["ok"] = ok
    return ok


def _probe_appendable(path) -> bool:
    """فحص قابلية الكتابة — ينشئ أدلة الملف أولًا (مثل append_entry تمامًا):
    غياب الدليل ليس قناة معطوبة بل قناة لم تُستخدم بعد؛ الفشل الحقيقي في
    الإنشاء/الفتح هو المعطوب."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8"):
            pass
        return True
    except OSError:
        return False

_CACHE_LOCK = threading.Lock()
_CACHE: dict = {
    "path": None,
    "stamp": None,   # (mtime, size, نسخة الاحتياط) — بصمة تغيّر الحالة
    "components": set(),
}


def _current_quarantined(component: str):
    """حالة العزل للمكوّن المطلوب — أو سلسلة سبب إن تعذر إثبات الحالة.

    ترتيب القرار (اعتراضات المراجع R-688/R-689/R-690):
    ١) الملف غائب: لا حالة مثبتة على القرص تحميها — إن وُجد إثبات سابق
       (كاش دافئ) تُحفظ الحالة المثبتة (سجل append-only لا يُحذف مشروعًا)؛
       وإلا فالاحتياط المحلي (إن وُجد) مرجع هذه العملية (R-688: بقية
       المكونات تستمر)؛ وإلا ففحص صحة قناة الكتابة يحسم (فشل كاتب منفصل
       عبر العمليات ← unwritable).
    ٢) الملف موجود: القراءة أولًا — فشلها = unreadable (إغلاق) مهما كان
       الاحتياط: وجود احتياط لمكوّن لا يُسقط عزلًا مثبتًا على القرص
       (R-690 — اعتراض المراجع ج3)؛ وبعد قراءة ناجحة يُدمج احتياط العملية
       (العزل النافذ فقط — الرفع الفاشل غير منفذ في loyalty_log).
    """
    path = quarantine_log_path()
    local_fallback = fallback_quarantined(path)
    try:
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size, fallback_version())
    except (FileNotFoundError, NotADirectoryError):
        # اختفاء بعد إثبات: الحالة المثبتة لا تُسقط صمتًا
        with _CACHE_LOCK:
            if _CACHE["path"] == str(path) and _CACHE["stamp"] is not None:
                logger.warning(
                    "سجل العزل اختفى بعد إثبات حالة سابقة (%s) — الحالة "
                    "المثبتة محفوظة (سجل append-only لا يُحذف مشروعًا)", path,
                )
                return set(_CACHE["components"]) | local_fallback
        # لا ملف ولا إثبات سابق — لا حالة مثبتة على القرص تحميها:
        # الاحتياط المحلي مرجع هذه العملية (R-688)
        if local_fallback:
            return set(local_fallback)
        # بلا معرفة محلية — صحة القناة تحسم (فشل كاتب منفصل)
        if not _channel_writable():
            return _REASON_UNWRITABLE
        with _CACHE_LOCK:
            _CACHE.update(path=str(path), stamp=None, components=set())
        return set()
    except OSError:
        # موجود لكن حالته مجهولة — لا سماح صامت
        return _REASON_UNREADABLE
    with _CACHE_LOCK:
        if _CACHE["path"] == str(path) and _CACHE["stamp"] == stamp:
            return set(_CACHE["components"]) | local_fallback
    try:
        components = quarantined_components(path)  # يرفع OSError عند تعذر القراءة
    except OSError:
        # ملف موجود غير مقروء = إغلاق مهما كان الاحتياط — لا إسقاط لعزل مثبت
        return _REASON_UNREADABLE
    with _CACHE_LOCK:
        _CACHE.update(path=str(path), stamp=stamp, components=set(components))
    return set(components) | local_fallback


class CircuitBreakerMiddleware:
    """مدخل التوجيه — ASGI middleware خالص (لا يعتمد ترتيب add_middleware).

    R-688 (اعتراض المراجع): فشل السجل لا يتحول سماحًا صامتًا — العزل المثبت
    يُرفض (503 component_quarantined)، والحالة غير القابلة للإثبات تُغلق على
    مسارات المكونات بخطأ محدد (503 quarantine_log_unreadable) والتطبيق حي.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path: Optional[str] = scope.get("path")
            if path:
                component = _COMPONENT_PATH_MAP.get(path)
                if component is None:
                    match = _COMPONENT_ROUTE.match(path)
                    component = match.group(1) if match else None
                if component:
                    quarantined = _current_quarantined(component)
                    if isinstance(quarantined, str):
                        # حالة غير قابلة للإثبات — إغلاق بخطأ محدد حرفيًا
                        # (لا سماح صامت ولا إسقاط لعزل مثبت، والتطبيق حي)
                        response = JSONResponse(
                            status_code=503,
                            content={
                                "error": f"quarantine_log_{quarantined}",
                                "component": component,
                                "detail": (
                                    "قناة سجل العزل غير قابلة للإثبات "
                                    f"({quarantined}) — إغلاق آمن على مسار "
                                    "المكون وبقية التطبيق يعمل"
                                ),
                            },
                        )
                        await response(scope, receive, send)
                        return
                    if component in quarantined:
                        response = JSONResponse(
                            status_code=503,
                            content={
                                "error": "component_quarantined",
                                "component": component,
                                "detail": (
                                    "المكوّن معزول بأمر سجل العزل — الطلب "
                                    "مرفوض بأمان وبقية المكونات تعمل"
                                ),
                            },
                        )
                        await response(scope, receive, send)
                        return
        await self.app(scope, receive, send)


def register_circuit_breaker(app: FastAPI) -> None:
    """تسجيل المدخل على التطبيق — نقطة الربط الوحيدة في app.py (R-687)."""
    app.add_middleware(CircuitBreakerMiddleware)
