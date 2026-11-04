# -*- coding: utf-8 -*-
"""R-846: سجلات منقّاة ومربوطة بالسياق.

1. **التنقية عند المصدر**: غلاف لـ ``LogRecordFactory`` يحسب نص الرسالة
   (``getMessage``) وينقّيه من الرموز السرية قبل أن يراه أي معالج، ثم يجعل
   ``args=()`` كي لا يعيد معالج تنسيق القيم الخام. يضيف للسجل
   ``request_id``/``loop_id``/``job_id`` من السياق الحالي.
2. **تنقية الاستثناءات**: مرشّح على معالجات الجذر ينقّي ``exc_text``.
3. **JSON اختياري**: ``SOVEREIGN_LOG_FORMAT=json`` يجعل معالجات الجذر تكتب
   سطر JSON لكل سجل (ts, level, logger, msg, request_id, loop_id, job_id, exc).

التثبيت متكرر بأمان (idempotent) عبر علامة على المصنع والمرشّح.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

from . import context
from .redact import redact

_MARK = "_r846"


def _scrub_record(record: logging.LogRecord) -> None:
    if getattr(record, "_r846_scrubbed", False):
        return
    try:
        msg = record.getMessage()
    except Exception:  # TOLERATED: رسالة لا تُنسَّق — تُحفظ كما هي نصًا منقّى
        msg = str(record.msg)
    record.msg, record.args = redact(msg), ()
    for k, v in context.current().items():
        if not getattr(record, k, None):
            setattr(record, k, v)
    record._r846_scrubbed = True


def _wrap_factory(base):
    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        rec = base(*args, **kwargs)
        _scrub_record(rec)
        return rec
    setattr(factory, _MARK, True)
    return factory


class ScrubFilter(logging.Filter):
    """ينقّي نص الاستثناء والمكدس (والرسالة إن فات المصنع سجلٌ مصنوع يدويًا)."""

    def filter(self, record: logging.LogRecord) -> bool:
        _scrub_record(record)
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            # exc_info يبقى (معالجات ومراجعات تعتمد عليه)؛ Formatter يستعمل
            # exc_text المخزّن ولا يعيد توليده خامًا ما دام موجودًا
            record.exc_text = redact(record.exc_text)
        if record.stack_info:
            record.stack_info = redact(record.stack_info)
        return True


setattr(ScrubFilter, _MARK, True)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        _scrub_record(record)
        out = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
                  + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
        }
        for k in ("request_id", "loop_id", "job_id"):
            v = getattr(record, k, "")
            if v:
                out[k] = v
        exc = record.exc_text
        if not exc and record.exc_info:
            exc = self.formatException(record.exc_info)
        if exc:
            out["exc"] = redact(exc)[-4000:]
        return json.dumps(out, ensure_ascii=False)


def _has_filter(h: logging.Handler) -> bool:
    return any(getattr(f, _MARK, False) for f in h.filters)


def install_logging(root: Optional[logging.Logger] = None) -> str:
    """تثبيت التنقية والربط (وJSON إن طُلب). يعيد سببًا معلنًا."""
    base = logging.getLogRecordFactory()
    if not getattr(base, _MARK, False):
        logging.setLogRecordFactory(_wrap_factory(base))
    root = root or logging.getLogger()
    fmt_json = os.environ.get("SOVEREIGN_LOG_FORMAT", "").strip().lower() == "json"
    for h in root.handlers:
        if not _has_filter(h):
            h.addFilter(ScrubFilter())
        if fmt_json and not isinstance(h.formatter, JsonFormatter):
            h.setFormatter(JsonFormatter())
    return ("السجلات: تنقية الأسرار + معرّفات الربط"
            + (" — صيغة JSON" if fmt_json else " — الصيغة النصية"))
