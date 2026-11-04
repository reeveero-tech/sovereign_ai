# -*- coding: utf-8 -*-
"""R-846: وسيط ASGI خالص — معرّف طلب ومقاييس HTTP بوسم القالب لا المسار.

- ``X-Request-ID`` وارد صالح (``[A-Za-z0-9._-]{8,64}``) يُحفظ للربط عبر
  الخدمات؛ غير ذلك يُولَّد معرّف جديد. يُعاد في رأس الرد دائمًا ويرتبط
  بكل سجل أثناء الطلب (contextvars).
- وسم ``route`` هو **قالب** المسار (``/items/{item_id}``) لا المسار الفعلي،
  فلا تنفجر السلاسل بالمعرّفات. ما لا يطابق أي مسار ⇒ ``__unmatched__``.
- الاستثناء غير الملتقط يُعدّ 500 ثم يُعاد رفعه كما هو.

وسيط ASGI خالص لا BaseHTTPMiddleware: لا يلمس جسم الرد ولا يكسر البث.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from . import context
from . import metrics as m

UNMATCHED = "__unmatched__"


def _route_template(app: Any, scope: Dict[str, Any]) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None) or getattr(route, "path_format", None)
    if path:
        return str(path)
    try:
        from starlette.routing import Match
    except ImportError:  # TOLERATED: بلا Starlette لا قالب — يُعدّ غير مطابق
        return UNMATCHED
    routes = getattr(getattr(app, "router", None), "routes", None) or getattr(app, "routes", [])
    for r in routes:
        try:
            match, _ = r.matches(scope)
        except Exception:  # TOLERATED: مسار لا يقبل هذا النطاق — يُتخطى
            continue
        if match == Match.FULL:
            return str(getattr(r, "path", UNMATCHED))
    return UNMATCHED


def _metrics(reg: m.Registry):
    return (reg.counter("http_requests_total", "طلبات HTTP حسب الطريقة والقالب والحالة",
                        ["method", "route", "status"]),
            reg.histogram("http_request_duration_seconds", "زمن طلب HTTP بالثواني",
                          ["method", "route"]))


class ObservabilityMiddleware:
    def __init__(self, app: Any, root_app: Optional[Any] = None,
                 registry: Optional[Callable[[], m.Registry]] = None):
        self.app = app
        self.root_app = root_app
        self._registry = registry or m.registry

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        incoming = None
        for k, v in scope.get("headers") or []:
            if k.lower() == b"x-request-id":
                incoming = v.decode("latin-1", "replace")
                break
        rid = context.accept_request_id(incoming)
        scope.setdefault("state", {})["request_id"] = rid
        status = {"code": 500}
        t0 = time.perf_counter()

        async def _send(message):
            if message.get("type") == "http.response.start":
                status["code"] = int(message.get("status", 500))
                headers = [(k, v) for k, v in message.get("headers", [])
                           if k.lower() != b"x-request-id"]
                headers.append((b"x-request-id", rid.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        with context.bind(request_id=rid):
            try:
                await self.app(scope, receive, _send)
            finally:
                dur = time.perf_counter() - t0
                route = _route_template(self.root_app or self.app, scope)
                method = str(scope.get("method", "?")).upper()[:10]
                reg = self._registry()
                total, hist = _metrics(reg)
                total.inc({"method": method, "route": route, "status": str(status["code"])})
                hist.observe({"method": method, "route": route}, dur)


def install_middleware(app: Any) -> None:
    """إضافة الوسيط للتطبيق مع مرجع التطبيق الجذر لمطابقة القوالب."""
    app.add_middleware(ObservabilityMiddleware, root_app=app)
