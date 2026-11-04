# -*- coding: utf-8 -*-
"""R-846: سياق الربط — request_id/loop_id/job_id عبر contextvars.

contextvars آمنة للخيوط وasyncio معًا: كل طلب أو مهمة يرى قيمه فقط.
"""
from __future__ import annotations

import contextvars
import re
import uuid
from contextlib import contextmanager
from typing import Dict, Optional

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
loop_id: contextvars.ContextVar[str] = contextvars.ContextVar("loop_id", default="")
job_id: contextvars.ContextVar[str] = contextvars.ContextVar("job_id", default="")

_VARS = {"request_id": request_id, "loop_id": loop_id, "job_id": job_id}
_VALID_RID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def accept_request_id(incoming: Optional[str]) -> str:
    """معرّف وارد صالح يُحفظ (ربط عبر الخدمات)؛ غير ذلك ⇒ معرّف جديد."""
    if incoming and _VALID_RID.match(incoming):
        return incoming
    return uuid.uuid4().hex


def current() -> Dict[str, str]:
    return {k: v.get() for k, v in _VARS.items() if v.get()}


@contextmanager
def bind(**values: str):
    tokens = []
    try:
        for k, v in values.items():
            if k in _VARS and v:
                tokens.append((_VARS[k], _VARS[k].set(str(v)[:64])))
        yield
    finally:
        for var, tok in reversed(tokens):
            var.reset(tok)
