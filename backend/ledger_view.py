# -*- coding: utf-8 -*-
"""R-850 (٦.٥.١): نافذة قراءة على السجل السيادي — بيانات وصفية فقط.

أساس مهارة «تلخيص السجل»: آخر N حدث (نوع/زمن/بادئة البصمة) + توزيع الأنواع
+ فحص ترابط السلسلة داخل النافذة (prev_hash لكل حدث = بصمة الأقدم منه).

حدود صريحة:
- قراءة فقط: لا كتابة ولا توقيع ولا تعديل.
- لا حمولة ولا blob ولا توقيع في الناتج — الخصوصية قبل التفصيل.
- الحد ١..٥٠ حدثًا؛ التصفية بالنوع تفحص أحدث ٥٠٠ حدث فقط وتعلن ذلك.
- مع التصفية لا يُفحص الترابط (الأحداث غير متتالية) — يُعلن لا يُفترض.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

MAX_LIMIT = 50
SCAN_CAP = 500


class LedgerViewError(ValueError):
    pass


def _limit(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise LedgerViewError(f"حد غير صالح: {value!r}") from exc
    if isinstance(value, bool) or not 1 <= n <= MAX_LIMIT:
        raise LedgerViewError(f"الحد بين 1 و{MAX_LIMIT}")
    return n


def recent(core, limit: Any = 10, event_type: Optional[str] = None) -> Dict[str, Any]:
    n = _limit(limit)
    etype = (str(event_type).strip() or None) if event_type is not None else None
    if etype is not None and len(etype) > 64:
        raise LedgerViewError("نوع حدث طويل جدًا")
    scan = SCAN_CAP if etype else n
    events = []
    for ev in core.iterate_events(reverse=True, limit=scan):
        if etype and ev.get("type") != etype:
            continue
        events.append(ev)
        if len(events) >= n:
            break
    by_type: Dict[str, int] = {}
    for ev in events:
        t = str(ev.get("type") or "?")
        by_type[t] = by_type.get(t, 0) + 1
    out: Dict[str, Any] = {
        "window": n, "filter": etype, "count": len(events),
        "events": [{"time": ev.get("time"), "type": ev.get("type"),
                    "hash": str(ev.get("hash") or "")[:16]} for ev in events],
        "by_type": dict(sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0]))),
        "newest": events[0].get("time") if events else None,
        "oldest": events[-1].get("time") if events else None,
    }
    if etype:
        out.update(chain_checked=False, chain_links=0, chain_linked=None,
                   scanned=SCAN_CAP,
                   note="التصفية بالنوع: الأحداث غير متتالية فلا يُفحص الترابط")
    else:
        links = [events[i].get("prev_hash") == events[i + 1].get("hash")
                 for i in range(len(events) - 1)]
        out.update(chain_checked=True, chain_links=len(links),
                   chain_linked=all(links), broken_links=links.count(False))
    return out
