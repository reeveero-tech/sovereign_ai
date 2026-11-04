# -*- coding: utf-8 -*-
"""R-843: واجهة طبقة التقييم المستقل — /evaluation/*.

- GET  /evaluation/suites  — المجموعات المجمّدة (بصمة/أرضية) + حالة استقلال الحَكَم.
- GET  /evaluation/latest  — آخر تقرير محفوظ (قراءة فقط).
- POST /evaluation/run     — تشغيل المجموعات وحفظ التقرير — مفتاح المالك.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import runner, suites
from .judge import IndependentJudge

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class RunRequest(BaseModel):
    suites: Optional[List[str]] = Field(default=None, max_length=20)
    api_key: Optional[str] = Field(default=None, max_length=512)


def _verify_owner(api_key: Optional[str]) -> None:
    try:
        from app import verify_api_key
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.app import verify_api_key
    if not verify_api_key(api_key or ""):
        raise HTTPException(status_code=401, detail="مفتاح API غير صحيح — أمر إداري")


@router.get("/suites")
async def list_suites():
    return {"suites": [s.public() for s in suites.SUITES],
            "judge": IndependentJudge().public()}


@router.get("/latest")
async def latest():
    import json
    import os
    from pathlib import Path
    root = Path(os.environ.get("SOVEREIGN_EVAL_DIR") or
                Path(__file__).resolve().parents[2] / "data" / "evaluation")
    p = root / "latest.json"
    if not p.exists():
        return {"report": None, "note": "لم يُشغَّل التقييم بعد على هذه الآلة"}
    return {"report": json.loads(p.read_text(encoding="utf-8"))}


@router.post("/run")
async def run(body: RunRequest):
    _verify_owner(body.api_key)
    try:
        report = runner.run_suites(body.suites)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    report["saved_to"] = runner.save_report(report)
    return report
