# -*- coding: utf-8 -*-
"""R-846: تنقية الأسرار للسجلات والآثار والمقاييس.

R-848 (D-063): الأنماط انتقلت إلى المصدر الوحيد ``secret_guard.catalog``
(GitHub، Render، Supabase sbp_/sb_secret_، JWT، AWS، Stripe، Google، sk-، Slack،
Telegram، PEM، Bearer، key=value). هذه الوحدة واجهة توافقية فقط.
"""
from __future__ import annotations

from typing import Any

try:
    from secret_guard import catalog as _catalog
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.secret_guard import catalog as _catalog


def redact(text: Any) -> str:
    return _catalog.redact(text)


def has_secret(text: Any) -> bool:
    return _catalog.has_secret(text)
