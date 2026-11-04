# -*- coding: utf-8 -*-
"""R-845: واجهة الإشعارات — /notifications/*.

- مفتوحة لأنها وصفية بلا أسرار أو روابط: ``GET /channels`` (هل كل قناة مضبوطة
  ولماذا، دون الرابط أو الرمز) و``GET /stats``.
- بمفتاح المالك (``X-API-Key``):
  - ``GET /notifications``: الصندوق الداخلي، وفيه نصوص الردود.
  - ``POST /{id}/read``.
  - ``POST /test``: إشعار تجريبي، و``Idempotency-Key`` إلزامي لأنه كتابة
    وإرسال خارجي.
  - ``POST /dispatch``: تصريف يدوي بحد أقصى 50.
  - ``POST /channels/{name}/enable``: رفع تعطيل المصادقة بعد إصلاح الإعداد.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import channels as ch_mod
from . import events, service

router = APIRouter(prefix="/notifications")


def _verify_owner(api_key: Optional[str]) -> None:
    try:
        from app import verify_api_key
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.app import verify_api_key
    if not verify_api_key(api_key or ""):
        raise HTTPException(status_code=401, detail="مفتاح API غير صحيح (X-API-Key) — أمر إداري")


class DispatchRequest(BaseModel):
    max_items: int = Field(default=20, ge=1, le=50)


@router.get("/channels")
def list_channels():
    return {"channels": service.channels_public(),
            "inbox": {"channel": "inbox", "configured": True,
                      "reason": "داخلي دائمًا — كل الشدات"}}


@router.get("/stats")
def stats():
    return {**service.get_store().stats(), "dispatcher": service.dispatcher_status()}


@router.get("")
def list_notifications(unread_only: bool = False, limit: int = 50,
                       x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _verify_owner(x_api_key)
    return {"notifications": service.get_store().list(unread_only, limit)}


@router.post("/test")
def send_test(x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
              idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    _verify_owner(x_api_key)
    key = (idempotency_key or "").strip()
    if not key or len(key) > 200:
        raise HTTPException(status_code=428,
                            detail="Idempotency-Key إلزامي (1–200 حرف) — الإشعار التجريبي كتابة وإرسال")
    ev = events.make("notify.test", f"notify.test:{key}", "owner",
                     "إشعار تجريبي من النظام السيادي — القناة تعمل",
                     link="/notifications")
    n, created = service.emit(ev)
    return JSONResponse(status_code=202 if created else 200,
                        content={"notification": service.get_store().get(n["id"]),
                                 "deduplicated": not created})


@router.post("/dispatch")
def dispatch(body: DispatchRequest = DispatchRequest(),
             x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _verify_owner(x_api_key)
    done = service.dispatcher().dispatch_once(body.max_items)
    return {"dispatched": done, "count": len(done)}


@router.post("/channels/{name}/enable")
def enable_channel(name: str, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _verify_owner(x_api_key)
    if ch_mod.get(name) is None:
        raise HTTPException(status_code=404, detail="قناة غير معروفة")
    return {"channel": name, "was_disabled": service.get_store().enable_channel(name)}


@router.post("/{notification_id}/read")
def mark_read(notification_id: str,
              x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _verify_owner(x_api_key)
    n = service.get_store().mark_read(notification_id)
    if n is None:
        raise HTTPException(status_code=404, detail="إشعار غير موجود")
    return {"notification": n}
