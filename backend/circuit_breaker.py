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
from typing import Optional, Set

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_MODULE_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.loyalty_log import quarantine_log_path, quarantined_components

# مسار مكوّن فقط — لا شيء آخر يُحجب
_COMPONENT_ROUTE = re.compile(r"^/components/([a-z][a-z0-9_]*)$")

_CACHE_LOCK = threading.Lock()
_CACHE: dict = {
    "path": None,
    "stamp": None,   # (mtime, size) — بصمة تغيّر السجل
    "components": set(),
}


def _current_quarantined() -> Set[str]:
    """المكونات المعزولة الآن — بذاكرة ببصمة تغيّر الملف (لا قرص لكل طلب)."""
    try:
        path = quarantine_log_path()
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        # السجل غير موجود بعد = لا عزل — بلا ذاكرة (غياب الملف ليس حالة)
        return set()
    with _CACHE_LOCK:
        if _CACHE["path"] == path and _CACHE["stamp"] == stamp:
            return set(_CACHE["components"])
    components = quarantined_components(path)
    with _CACHE_LOCK:
        _CACHE["path"] = path
        _CACHE["stamp"] = stamp
        _CACHE["components"] = set(components)
    return components


class CircuitBreakerMiddleware:
    """مدخل التوجيه — ASGI middleware خالص (لا يعتمد ترتيب add_middleware)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path: Optional[str] = scope.get("path")
            if path:
                match = _COMPONENT_ROUTE.match(path)
                if match:
                    component = match.group(1)
                    if component in _current_quarantined():
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
