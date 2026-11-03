# -*- coding: utf-8 -*-
"""R-841: نقاط واجهة طبقة التنسيق — /orchestrator/*.

عقود صارمة عبر pydantic، وحالات فشل واضحة (403 حوكمي، 404 حلقة، 409
موافقة محسومة) — لا سر يعود في أي رد أبدًا (التنقية في الأثر نفسه).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import schemas
from .runtime import OrchestratorSystem

router = APIRouter(prefix="/orchestrator")

_SYSTEM: Optional[OrchestratorSystem] = None


def _data_dir() -> str:
    try:
        try:
            from ..config import DATA_DIR
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from config import DATA_DIR
        return str(DATA_DIR)
    except ImportError:
        return os.path.join(os.getcwd(), "data")


def get_orchestrator() -> OrchestratorSystem:
    global _SYSTEM
    if _SYSTEM is None:
        _SYSTEM = OrchestratorSystem(data_dir=_data_dir())
    return _SYSTEM


def reset_for_tests() -> None:
    global _SYSTEM
    _SYSTEM = None


# --------------------------------------------------------------------- العقد
class SubmitRequest(BaseModel):
    user_id: str = Field(default="user", min_length=1, max_length=120)
    session_id: str = Field(default="s-default", min_length=1, max_length=120)
    utterance: str = Field(..., min_length=1, max_length=4000)
    permissions: List[str] = Field(default_factory=list)
    constraints: Optional[Dict[str, Any]] = None
    dry_run: bool = False
    api_key: Optional[str] = Field(default=None, max_length=512)


class ApprovalDecision(BaseModel):
    approval_id: str = Field(..., min_length=8, max_length=64)
    decision: str = Field(..., pattern="^(approved|rejected|modified)$")
    approved_by: str = Field(default="user", min_length=1, max_length=120)
    session_scope: bool = False
    api_key: Optional[str] = Field(default=None, max_length=512)


class RollbackRequest(BaseModel):
    step_id: str = Field(..., min_length=1, max_length=64)
    actor: str = Field(default="admin", min_length=1, max_length=120)
    api_key: Optional[str] = Field(default=None, max_length=512)


class CancelRequest(BaseModel):
    actor: str = Field(default="user", min_length=1, max_length=120)
    api_key: Optional[str] = Field(default=None, max_length=512)


class ModifyPlanRequest(BaseModel):
    steps: List[Dict[str, Any]] = Field(..., min_length=1)
    actor: str = Field(default="user", min_length=1, max_length=120)
    api_key: Optional[str] = Field(default=None, max_length=512)


class PauseResumeRequest(BaseModel):
    actor: str = Field(default="user", min_length=1, max_length=120)
    api_key: Optional[str] = Field(default=None, max_length=512)


def _verify_owner(api_key: Optional[str]) -> None:
    """بوابة مفتاح المالك — نمط R-840 نفسه: 401 برسالة، لا صمت."""
    try:
        from app import verify_api_key
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.app import verify_api_key
    if not verify_api_key(api_key or ""):
        raise HTTPException(
            status_code=401, detail="مفتاح API غير صحيح — أمر إداري")


# --------------------------------------------------------------------- المسارات
@router.get("/tools")
async def list_tools():
    """سجل الأدوات المعرّفة — عقد كامل لكل أداة (وصف/خطورة/مخطط)."""
    o = get_orchestrator()
    return {"tools": o.tools.list(), "total": len(o.tools.list())}


@router.get("/schemas")
async def get_schemas():
    """مخططات العقود الخمسة (5.1–5.5) — قابلة للتحقق الآلي."""
    return {"schemas": schemas.SCHEMAS}


@router.get("/health")
async def health():
    """نبض الطبقة — جاهزية المنفذ والسجل."""
    o = get_orchestrator()
    ready = True
    try:
        o._executor()
    except Exception:
        ready = False
    return {"ok": ready, "tools": len(o.tools.list()),
            "pending_approvals": len(o.pending_approvals())}


@router.get("/ui", response_class=HTMLResponse)
async def orchestrator_ui():
    """واجهة الطبقة الأولية: خطة/أثر/موافقة/إلغاء (JS مضمن — بلا وحدة جديدة)."""
    page = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "frontend", "orchestrator.html")
    try:
        with open(page, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except OSError:
        raise HTTPException(status_code=404, detail="صفحة الواجهة غير موجودة")


@router.post("/loops")
async def submit_loop(req: SubmitRequest):
    """استقبال طلب وقيادة الحلقة — يعيد الحالة والخطة والأثر أو انتظار موافقة."""
    _verify_owner(req.api_key)
    o = get_orchestrator()
    request = schemas.new_request(
        user_id=req.user_id, session_id=req.session_id,
        utterance=req.utterance, permissions=req.permissions,
        constraints=req.constraints, dry_run=req.dry_run)
    out = o.submit(request)
    if not out.get("ok", False):
        raise HTTPException(status_code=400, detail=out.get("error", "فشل"))
    return out


@router.get("/loops")
async def list_loops():
    return {"loops": get_orchestrator().state.list()}


@router.get("/loops/{loop_id}")
async def get_loop(loop_id: str):
    out = get_orchestrator().get(loop_id)
    if not out.get("ok", False):
        raise HTTPException(status_code=404, detail=out.get("error", "غير موجود"))
    return out


@router.post("/loops/{loop_id}/cancel")
async def cancel_loop(loop_id: str, body: CancelRequest):
    _verify_owner(body.api_key)
    out = get_orchestrator().cancel(loop_id, body.actor)
    if not out.get("ok", False):
        raise HTTPException(status_code=404, detail=out.get("error"))
    return out


@router.post("/loops/{loop_id}/resume")
async def resume_loop(loop_id: str, body: PauseResumeRequest):
    """استئناف حلقة متوقفة — من نقطة الـcheckpoint نفسها."""
    _verify_owner(body.api_key)
    o = get_orchestrator()
    state = o.state.load(loop_id)
    if state is None:
        raise HTTPException(status_code=404, detail="حلقة غير موجودة")
    if state["status"] not in ("paused",):
        raise HTTPException(
            status_code=409, detail=f"الحلقة {state['status']} — لا استئناف")
    o.hitl.resume(state, "user", "")
    o.state.save(state)
    return o.run(loop_id)


@router.post("/loops/{loop_id}/pause")
async def pause_loop(loop_id: str, body: PauseResumeRequest):
    _verify_owner(body.api_key)
    o = get_orchestrator()
    state = o.state.load(loop_id)
    if state is None:
        raise HTTPException(status_code=404, detail="حلقة غير موجودة")
    out = o.hitl.pause(state, "user", "")
    o.state.save(state)
    return {"ok": out["ok"], "reason": out["reason"]}


@router.post("/loops/{loop_id}/plan")
async def modify_plan(loop_id: str, body: ModifyPlanRequest):
    """تعديل الخطة بتدخل بشري — يُعاد التحقق من المخطط قبل القبول."""
    _verify_owner(body.api_key)
    o = get_orchestrator()
    state = o.state.load(loop_id)
    if state is None:
        raise HTTPException(status_code=404, detail="حلقة غير موجودة")
    out = o.hitl.modify_plan(state, body.steps, body.actor, "")
    o.state.save(state)
    if not out["ok"]:
        raise HTTPException(status_code=409, detail=out["reason"])
    return {"ok": True, "reason": out["reason"], "plan": state["plan"]}


@router.post("/loops/{loop_id}/rollback")
async def rollback_step(loop_id: str, body: RollbackRequest):
    _verify_owner(body.api_key)
    out = get_orchestrator().rollback(loop_id, body.step_id, body.actor)
    if not out.get("ok", False) and "error" in out:
        raise HTTPException(status_code=404, detail=out["error"])
    return out


@router.get("/loops/{loop_id}/trace")
async def get_trace(loop_id: str):
    out = get_orchestrator().trace(loop_id)
    if not out.get("ok", True):
        raise HTTPException(status_code=404, detail=out.get("error", "لا أثر"))
    return out


@router.get("/approvals/pending")
async def pending_approvals():
    return {"approvals": get_orchestrator().pending_approvals()}


@router.post("/approvals")
async def decide_approval(body: ApprovalDecision):
    """حسم موافقة — ثم استئناف الحلقة إن كانت معلّقة عليها."""
    _verify_owner(body.api_key)
    o = get_orchestrator()
    # الربط: كل موافقة تعرف خطوتها وحلقتها من الحالة المحفوظة
    for state in o.state.list():
        full = o.state.load(state["loop_id"])
        pending = (full or {}).get("pending_approval") or {}
        if pending.get("approval_id") == body.approval_id:
            return o.decide_approval(
                state["loop_id"], body.approval_id, body.decision,
                body.approved_by, body.session_scope)
    raise HTTPException(status_code=404, detail="موافقة غير معلّقة على حلقة")
