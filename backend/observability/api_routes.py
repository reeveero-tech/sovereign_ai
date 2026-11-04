# -*- coding: utf-8 -*-
"""R-846: واجهة الرصد.

- ``GET /metrics``: صيغة Prometheus النصية. تتطلب ``X-API-Key`` أو
  ``Authorization: Bearer $SOVEREIGN_METRICS_TOKEN`` (≥16 حرفًا) — المقاييس
  تكشف بنية التشغيل فلا تُفتح للعموم.
- ``GET /observability/health``: مفتوحة (للمراقب الخارجي)، أسباب بلا مسارات
  ولا أسرار، و503 عند ``failing``. ``/health`` القديمة تبقى فحص حياة لـRender.
- ``GET /observability/summary``: بمفتاح المالك — الجاهزية والمراقب ولقطة JSON.

``make_router`` يقبل التبعيات محقونة (السجل، الفحوص، تحقق المالك) كي تختبر
مجموعة التقييم النقاط الحقيقية دون إقلاع التطبيق كاملًا.
"""
from __future__ import annotations

import hmac
import os
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from . import health, service
from . import metrics as m

PROM_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def _app_owner_ok(api_key: str) -> bool:
    try:
        from app import verify_api_key
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.app import verify_api_key
    return bool(verify_api_key(api_key))


def bearer_ok(authorization: Optional[str]) -> bool:
    tok = os.environ.get("SOVEREIGN_METRICS_TOKEN", "").strip()
    if len(tok) < 16 or not authorization:
        return False
    scheme, _, given = authorization.partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(
        given.strip().encode("utf-8"), tok.encode("utf-8"))


def make_router(registry: Callable[[], m.Registry] = m.registry,
                checks: Callable[[], List[Dict[str, str]]] = health.live_checks,
                owner_ok: Callable[[str], bool] = _app_owner_ok,
                summary: Callable[[], Dict[str, Any]] = service.summary) -> APIRouter:
    r = APIRouter()

    def _owner(k: Optional[str]) -> bool:
        return bool(k) and owner_ok(k)

    @r.get("/metrics")
    def metrics_endpoint(x_api_key: Optional[str] = Header(default=None),
                         authorization: Optional[str] = Header(default=None)):
        if not (bearer_ok(authorization) or _owner(x_api_key)):
            raise HTTPException(status_code=401,
                                detail="المقاييس تتطلب X-API-Key أو Bearer SOVEREIGN_METRICS_TOKEN")
        return PlainTextResponse(registry().render(), media_type=PROM_CONTENT_TYPE)

    @r.get("/observability/health")
    def observability_health():
        rep = health.report(checks())
        return JSONResponse(rep, status_code=503 if rep["status"] == health.FAILING else 200)

    @r.get("/observability/summary")
    def observability_summary(x_api_key: Optional[str] = Header(default=None)):
        if not _owner(x_api_key):
            raise HTTPException(status_code=401, detail="مفتاح API غير صحيح (X-API-Key)")
        return summary()

    return r


router = make_router()
