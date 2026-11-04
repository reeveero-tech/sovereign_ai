# -*- coding: utf-8 -*-
"""R-844: واجهة الطابور غير المتزامن — /queue/*.

- الإدخال: ``POST /queue/jobs`` يحتاج رأسين. ``X-API-Key`` هو مفتاح المالك،
  ولا يوضع في الرابط حتى لا يُسجَّل. و``Idempotency-Key`` إلزامي لأن الإدخال
  كتابة (ممنوع «لا كتابة بلا Idempotency-Key»)، وغيابه يعطي 428.
  الاستجابة 202 لمهمة جديدة، و200 مع ``deduplicated`` للمفتاح نفسه بالحمولة
  نفسها، و409 للمفتاح نفسه بحمولة أخرى، و422 لنوع أو حمولة غير صالحين،
  و429 لطابور ممتلئ.
- القراءة: الحالة والأنواع مفتوحتان لأنهما بيانات وصفية. تفاصيل المهام فيها
  نص طلب المالك، فتحتاج المفتاح.
- ``POST /queue/drain``: تشغيل متزامن محدود (حد أقصى 50) للبيئات التي عمالها
  معطلون.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import kinds as kinds_mod
from . import service
from .store import IdempotencyConflict, QueueError, QueueFull
from .worker import Worker

router = APIRouter(prefix="/queue")


def _verify_owner(api_key: Optional[str]) -> None:
    try:
        from app import verify_api_key
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.app import verify_api_key
    if not verify_api_key(api_key or ""):
        raise HTTPException(status_code=401, detail="مفتاح API غير صحيح (X-API-Key) — أمر إداري")


class EnqueueRequest(BaseModel):
    kind: str = Field(..., min_length=1, max_length=64)
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=-10, le=10)
    actor: str = Field(default="owner", min_length=1, max_length=120)


class DrainRequest(BaseModel):
    max_jobs: int = Field(default=10, ge=1, le=50)


def _public(job: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in job.items() if k not in ("payload_hash", "lease_owner")}
    out["leased"] = bool(job.get("lease_owner"))
    return out


@router.get("/kinds")
async def list_kinds():
    return {"kinds": service.kinds_public()}


@router.get("/stats")
async def stats():
    return {**service.get_store().stats(), "workers": service.workers_status()}


@router.post("/jobs")
def enqueue(body: EnqueueRequest,
            x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
            idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    _verify_owner(x_api_key)
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status_code=428,
                            detail="Idempotency-Key مطلوب — لا كتابة بلا مفتاح عدم تكرار")
    try:
        kind = kinds_mod.get(body.kind)
        kind.validate(body.payload)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc).strip("'\""))
    except kinds_mod.orch_schemas.SchemaError as exc:
        raise HTTPException(status_code=422, detail=f"حمولة غير صالحة: {exc}")
    try:
        job, created = service.get_store().enqueue(
            body.kind, body.payload, idempotency_key.strip(), body.actor,
            max_attempts=kind.max_attempts, timeout_s=kind.timeout_s(body.payload),
            priority=body.priority)
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except QueueFull as exc:
        raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": "30"})
    except QueueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return JSONResponse(status_code=202 if created else 200,
                        content={"job": _public(job), "deduplicated": not created})


@router.get("/jobs")
def list_jobs(status: Optional[str] = None, limit: int = 50,
              x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _verify_owner(x_api_key)
    return {"jobs": [_public(j) for j in service.get_store().list(status, limit)]}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _verify_owner(x_api_key)
    store = service.get_store()
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="مهمة غير موجودة")
    return {"job": _public(job), "events": store.events(job_id)}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _verify_owner(x_api_key)
    store = service.get_store()
    job = store.cancel(job_id, "owner")
    if job is None:
        raise HTTPException(status_code=404, detail="مهمة غير موجودة")
    if job["status"] == "running" and job.get("loop_id"):
        # إلغاء الحلقة نفسها: تتوقف قبل خطوتها التالية (علم الإلغاء في المنسق)
        kinds_mod._orchestrator().cancel(job["loop_id"], "owner")
    return {"job": _public(job)}


@router.post("/drain")
def drain(body: DrainRequest, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    _verify_owner(x_api_key)
    done: List[Dict[str, Any]] = Worker(service.get_store()).drain(body.max_jobs)
    return {"processed": done, "count": len(done)}
