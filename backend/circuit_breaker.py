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

from backend.loyalty_log import quarantine_log_path, quarantined_components

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

# R-688 (اعتراض المراجع): حالة لا يمكن إثباتها — السجل موجود لكنه غير قابل
# للقراءة. القرار: إغلاق على مسارات المكونات بخطأ محدد (لا سماح صامت ولا
# إسقاط لعزل مثبت)، والمسارات غير المكوّنية والتطبيق كله يبقيان أحياء.
_UNKNOWN = object()

_CACHE_LOCK = threading.Lock()
_CACHE: dict = {
    "path": None,
    "stamp": None,   # (mtime, size) — بصمة تغيّر السجل
    "components": set(),
}


def _current_quarantined():
    """المكونات المعزولة الآن — أو _UNKNOWN إذا تعذر إثبات حالة السجل.

    - لا ملف: لا عزل على القرص — لكن يبقى احتياط الذاكرة (أحداث فشل توثيقها
      في هذه العملية) — لا سماح صامت لفشل الكتابة.
    - ملف موجود مقروء: قراءة بذاكرة ببصمة تغيّر (لا قرص لكل طلب).
    - ملف موجود غير مقروء: OSError ← _UNKNOWN (المتصل يغلق بخطأ محدد).
    """
    path = quarantine_log_path()
    try:
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
    except (FileNotFoundError, NotADirectoryError):
        # لا سجل على القرص أصلًا (أو موضعه مكسور) — مشروع: لم يُوثق عزل
        # على القرص. يبقى احتياط الذاكرة (أحداث فشل توثيقها في هذه العملية).
        components = quarantined_components(path)
        with _CACHE_LOCK:
            _CACHE.update(path=str(path), stamp=None, components=set(components))
        return set(components)
    except OSError:
        # موجود لكن حالته مجهولة — لا سماح صامت (القرار عند المتصل: إغلاق)
        return _UNKNOWN
    with _CACHE_LOCK:
        if _CACHE["path"] == str(path) and _CACHE["stamp"] == stamp:
            return set(_CACHE["components"])
    try:
        components = quarantined_components(path)
    except OSError:
        return _UNKNOWN
    with _CACHE_LOCK:
        _CACHE.update(path=str(path), stamp=stamp, components=set(components))
    return components


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
                    quarantined = _current_quarantined()
                    if quarantined is _UNKNOWN:
                        response = JSONResponse(
                            status_code=503,
                            content={
                                "error": "quarantine_log_unreadable",
                                "component": component,
                                "detail": (
                                    "سجل العزل موجود لكنه غير قابل للقراءة — "
                                    "حالة التوجيه غير قابلة للإثبات: إغلاق "
                                    "آمن على مسار المكون وبقية التطبيق يعمل"
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
