# -*- coding: utf-8 -*-
"""R-846: تنقية الأسرار — نمط واحد للسجلات والآثار والمقاييس.

يغطي: رموز GitHub (ghp_/gho_/ghu_/ghs_/ghr_/github_pat_)، Supabase (sbp_)،
Render (rnd_)، OpenAI-نمط (sk-)، Slack (xox?-)، Bearer، رمز بوت Telegram،
ومفاتيح بأسماء سرية في نص key=value.
"""
from __future__ import annotations

import re
from typing import Any

SECRET_RE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|sbp_[A-Za-z0-9]{8,}"
    r"|rnd_[A-Za-z0-9]{8,}|sk-[A-Za-z0-9_-]{8,}|xox[abprs]-[A-Za-z0-9-]{8,}"
    r"|Bearer\s+[A-Za-z0-9._~+/=-]{8,}|\b\d{6,12}:[A-Za-z0-9_-]{30,})")
_KV_RE = re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token|authorization)"
                    r"(\s*[=:]\s*)([^\s,;&\"']{4,})")


def redact(text: Any) -> str:
    s = SECRET_RE.sub("***", str(text))
    return _KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}***", s)


def has_secret(text: Any) -> bool:
    return bool(SECRET_RE.search(str(text)))
