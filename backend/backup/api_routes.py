# -*- coding: utf-8 -*-
"""R-847: ``/backups/*`` — كل المسارات بمفتاح المالك (``X-API-Key``).

- ``GET /backups``: الفهرس والإعدادات (بلا مفتاح التشفير أبدًا).
- ``POST /backups``: إدراج ``backup.create`` في الطابور. ``Idempotency-Key`` إلزامي
  (428 بدونه)، والاستجابة 202 بالمهمة.
- ``POST /backups/{id}/verify``: تحقق كامل (قراءة فقط).
- ``POST /backups/{id}/restore/plan``: خطة جافة و``plan_hash``.
- ``POST /backups/{id}/restore``: تجهيز حساس — ``Idempotency-Key`` و``plan_hash``
  و``confirm="RESTORE <id>"``. يأخذ نسخة ``pre_restore`` أولًا، ويُطبق عند الإقلاع.
- ``GET /backups/restore``: المجهز وآخر نتيجة.
- ``DELETE /backups/restore/pending``: إلغاء تجهيز لم يبدأ تطبيقه (``Idempotency-Key``).
- ``GET /backups/offsite``: كائنات الوجهة الخارجية.
- ``POST /backups/offsite/{id}/fetch``: جلب نسخة من الخارج للتعافي من كارثة.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import offsite, service
from .catalog import valid_id
from .restore import RestoreError
from .snapshot import BackupError

_STATUS = {"not_found": 404, "confirm_mismatch": 422, "plan_mismatch": 409,
           "restore_pending_exists": 409, "verify_failed": 422, "pre_restore_failed": 503,
           "busy": 409, "offsite_not_configured": 409}


class RestoreBody(BaseModel):
    plan_hash: str = Field(..., min_length=64, max_length=64)
    confirm: str = Field(..., min_length=1, max_length=80)
    actor: str = Field(default="owner", min_length=1, max_length=120)


def _owner_from_app(key: str) -> bool:
    try:
        from app import verify_api_key
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.app import verify_api_key
    return bool(verify_api_key(key or ""))


def _job_store():
    try:
        from job_queue import service as jq
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.job_queue import service as jq
    return jq.get_store()


def _err(exc: Exception) -> HTTPException:
    reason = getattr(exc, "reason", type(exc).__name__)
    return HTTPException(status_code=_STATUS.get(reason, 422),
                         detail={"reason": reason, "detail": getattr(exc, "detail", "")})


def make_router(owner_ok: Callable[[str], bool] = _owner_from_app,
                job_store: Callable[[], Any] = _job_store) -> APIRouter:
    r = APIRouter(prefix="/backups")

    def _owner(k: Optional[str]) -> None:
        if not owner_ok(k or ""):
            raise HTTPException(status_code=401, detail="مفتاح API غير صحيح (X-API-Key) — أمر إداري")

    def _idem(k: Optional[str]) -> str:
        if not k or len(k) > 200:
            raise HTTPException(status_code=428,
                                detail="Idempotency-Key مطلوب — لا كتابة بلا مفتاح عدم تكرار")
        return k

    def _bid(bid: str) -> str:
        if not valid_id(bid):
            raise HTTPException(status_code=404, detail="معرّف نسخة غير صالح")
        return bid

    @r.get("")
    def list_backups(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
        _owner(x_api_key)
        s = service.settings()
        return {"backups": s.catalog().list(), "settings": service.summary(s)}

    @r.post("")
    def create_backup(x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
                      idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
        _owner(x_api_key)
        key = _idem(idempotency_key)
        job, created = job_store().enqueue("backup.create", {"kind": "manual"},
                                           f"backup:manual:{key}", "owner",
                                           max_attempts=1, timeout_s=1800.0)
        return JSONResponse(status_code=202 if created else 200,
                            content={"job_id": job["id"], "created": created,
                                     "status": job["status"],
                                     "link": f"/queue/jobs/{job['id']}"})

    @r.get("/restore")
    def restore_status(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
        _owner(x_api_key)
        return service.restore_status()

    @r.delete("/restore/pending")
    def cancel_restore(x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
                       idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
        _owner(x_api_key)
        _idem(idempotency_key)
        from .restore import cancel
        return cancel(service.settings().data_dir)

    @r.get("/offsite")
    def offsite_list(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
        _owner(x_api_key)
        s = service.settings()
        if s.dest is None:
            return {"destination": None, "objects": [], "reason": s.offsite_error or "غير مضبوطة"}
        try:
            return {"destination": s.dest.name, "objects": s.dest.list()}
        except offsite.OffsiteError as exc:
            raise HTTPException(status_code=502, detail={"reason": exc.kind}) from exc

    @r.post("/offsite/{bid}/fetch")
    def offsite_fetch(bid: str, x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
                      idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
        _owner(x_api_key)
        _idem(idempotency_key)
        try:
            return service.fetch(_bid(bid))
        except BackupError as exc:
            raise _err(exc) from exc

    @r.post("/{bid}/verify")
    def verify(bid: str, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
        _owner(x_api_key)
        out = service.verify(_bid(bid))
        if out.get("reason") == "not_found":
            raise HTTPException(status_code=404, detail="نسخة غير موجودة")
        return out

    @r.post("/{bid}/restore/plan")
    def restore_plan(bid: str, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
        _owner(x_api_key)
        try:
            return service.plan(_bid(bid))
        except RestoreError as exc:
            raise _err(exc) from exc

    @r.post("/{bid}/restore")
    def restore_stage(bid: str, body: RestoreBody,
                      x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
                      idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
        _owner(x_api_key)
        key = _idem(idempotency_key)
        try:
            out = service.stage(_bid(bid), body.plan_hash, body.confirm, body.actor, key)
        except RestoreError as exc:
            raise _err(exc) from exc
        return JSONResponse(status_code=200 if out.get("replayed") else 202,
                            content={**out, "next": "أعد تشغيل الخادم لتطبيق الاستعادة"
                                                    " (fly machine restart)"})

    return r


router = make_router()
