"""R-825 — الفهرس الذاتي لمحرك البحث (محرك ينمو مع كل سؤال) + ذاكرة إجابات مؤقتة.

أمر المالك: «قم بتركيب أو تطوير محرك البحث».

لماذا: المزودات العامة تُحجب أو تُبطئ من عناوين السحابة (DuckDuckGo/Marginalia تنتهي مهلتها من
Render). كل صفحة يقرؤها المحرك فعلًا تُحفظ هنا في Postgres (Supabase) بفهرس نص كامل GIN
(to_tsvector('simple') — يعمل لكل اللغات بلا قاموس)، فيصبح المحرك نفسه مزودًا مستقلًا
(_p_index في world_search) لا تحجبه أي جهة، ويزداد غنى مع كل بحث.

الذاكرة المؤقتة: الإجابة المقيّمة تُحفظ بمفتاح (لغة + سؤال موحّد) ومهلة صلاحية — قصيرة
للأسئلة الآنية (سعر/اليوم/أحدث) وطويلة للأسئلة الثابتة — فالسؤال المكرر يُجاب فورًا.

المخطط: infra/supabase/r825_search_index.sql (جدولا search_pages وsearch_cache ودالة
search_pages_query). بلا Supabase مضبوط ⇒ الطبقة معطلة صراحةً ولا تكسر البحث.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sovereign.search_index")

_STATS = {"stored": 0, "store_errors": 0, "queries": 0, "query_errors": 0,
          "cache_hits": 0, "cache_misses": 0, "last_error": None}


def _env(name: str) -> Optional[str]:
    from sovereign.cloud_disk import _supabase_env
    return _supabase_env(name)


def enabled() -> bool:
    """مفعّل إذا ضُبط Supabase (الرابط + سر الخدمة) ولم يُطفأ بـ WORLD_SEARCH_INDEX_ENABLED=false."""
    if str(os.getenv("WORLD_SEARCH_INDEX_ENABLED", "true")).strip().lower() == "false":
        return False
    return bool(_env("SUPABASE_URL") and _env("SUPABASE_SECRET_KEY"))


def _client(timeout: float = 4.0):
    import httpx
    key = _env("SUPABASE_SECRET_KEY") or ""
    return httpx.Client(base_url=(_env("SUPABASE_URL") or "").rstrip("/"), timeout=timeout,
                        headers={"apikey": key, "Authorization": f"Bearer {key}",
                                 "Content-Type": "application/json"})


def _note_error(kind: str, e: Exception) -> None:
    _STATS[kind] += 1
    _STATS["last_error"] = f"{type(e).__name__}: {str(e)[:160]}"
    logger.warning("R-825: فهرس البحث (%s): %s", kind, _STATS["last_error"])


# ============================================================
# الصفحات
# ============================================================
def _row(src: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = str(src.get("url") or "").strip()
    body = " ".join(str(src.get("text") or src.get("snippet") or "").split())
    if not url.startswith("http") or len(body) < 80:
        return None
    return {"url": url[:1000], "title": str(src.get("title") or "")[:300],
            "lang": str(src.get("lang") or "")[:8], "provider": str(src.get("provider") or "")[:40],
            "body": body[:50000], "published_at": src.get("published") or None,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def store_pages(sources: List[Dict[str, Any]]) -> int:
    """إدراج-تحديث الصفحات المقروءة في الفهرس — يعيد عدد الصفوف المرسلة (0 عند التعطيل/الفشل)."""
    if not enabled():
        return 0
    rows, seen = [], set()
    for s in sources:
        r = _row(s)
        if r and r["url"] not in seen and s.get("provider") != "index":
            seen.add(r["url"])
            rows.append(r)
    if not rows:
        return 0
    try:
        with _client(timeout=8.0) as c:
            resp = c.post("/rest/v1/search_pages", json=rows[:40],
                          headers={"Prefer": "resolution=merge-duplicates,return=minimal"})
            resp.raise_for_status()
        _STATS["stored"] += len(rows[:40])
        return len(rows[:40])
    except Exception as e:  # TOLERATED: فشل الفهرسة لا يُسقط الجواب — يُعدّ ويُعلن في الحالة
        _note_error("store_errors", e)
        return 0


def store_pages_async(sources: List[Dict[str, Any]]) -> None:
    """الفهرسة في خيط خلفي — الجواب لا ينتظر الكتابة."""
    if not enabled():
        return
    snap = [dict(s) for s in sources]
    threading.Thread(target=store_pages, args=(snap,), daemon=True, name="search-index-store").start()


def query(terms: List[str], limit: int = 8, max_age_days: int = 3650) -> List[Dict[str, Any]]:
    """بحث نصي مرتب في الفهرس (OR بين المصطلحات + مطابقة بادئة) — يعيد مصادر بنصها الكامل."""
    if not enabled():
        return []
    clean = [t for t in dict.fromkeys(str(x).strip().lower() for x in terms)
             if t and len(t) > 1 and re.fullmatch(r"[\w\u0600-\u06FF\-']+", t)][:16]
    if not clean:
        return []
    _STATS["queries"] += 1
    try:
        with _client() as c:
            resp = c.post("/rest/v1/rpc/search_pages_query",
                          json={"terms": clean, "lim": int(limit), "max_age_days": int(max_age_days)})
            resp.raise_for_status()
            rows = resp.json() or []
    except Exception as e:  # TOLERATED: الفهرس مزود بين مزودات — فشله يُعلن ولا يسقط البحث
        _note_error("query_errors", e)
        raise
    return [{"title": r.get("title") or "", "url": r["url"], "snippet": "", "text": r.get("body") or "",
             "provider": "index", "lang": r.get("lang") or "", "published": r.get("published_at"),
             "indexed_at": r.get("fetched_at"), "index_rank": r.get("rank")} for r in rows if r.get("url")]


# ============================================================
# ذاكرة الإجابات المؤقتة
# ============================================================
def cache_key(question: str, lang: str) -> str:
    norm = " ".join(re.sub(r"[^\w]+", " ", str(question or "").lower()).split())  # ؟ و، علامات لا حروف
    return "wa:" + hashlib.sha256(f"{lang}|{norm}".encode()).hexdigest()[:40]


def cache_get(key: str) -> Optional[Dict[str, Any]]:
    if not enabled():
        return None
    try:
        with _client(timeout=3.0) as c:
            resp = c.get("/rest/v1/search_cache", params={"key": f"eq.{key}", "select": "payload,created_at,ttl_seconds"})
            resp.raise_for_status()
            rows = resp.json() or []
    except Exception as e:  # TOLERATED: الذاكرة المؤقتة اختيارية — فشلها ⇒ بحث حي
        _note_error("query_errors", e)
        return None
    if not rows:
        _STATS["cache_misses"] += 1
        return None
    row = rows[0]
    try:
        from datetime import datetime
        created = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")).timestamp()
    except Exception:  # TOLERATED: تاريخ غير مقروء ⇒ يُعامل منتهيًا
        created = 0.0
    age = time.time() - created
    if age > int(row.get("ttl_seconds") or 0):
        _STATS["cache_misses"] += 1
        return None
    _STATS["cache_hits"] += 1
    payload = dict(row.get("payload") or {})
    payload["cached"] = True
    payload["cache_age_seconds"] = int(age)
    return payload


def cache_put(key: str, payload: Dict[str, Any], ttl_seconds: int) -> bool:
    if not enabled() or not payload.get("ok"):
        return False
    try:
        with _client(timeout=4.0) as c:
            resp = c.post("/rest/v1/search_cache",
                          json={"key": key, "payload": payload, "ttl_seconds": int(ttl_seconds),
                                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                          headers={"Prefer": "resolution=merge-duplicates,return=minimal"})
            resp.raise_for_status()
        return True
    except Exception as e:  # TOLERATED: الحفظ المؤقت اختياري
        _note_error("store_errors", e)
        return False


def cache_put_async(key: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
    if enabled() and payload.get("ok"):
        threading.Thread(target=cache_put, args=(key, dict(payload), ttl_seconds),
                         daemon=True, name="search-cache-put").start()


def status() -> Dict[str, Any]:
    """حالة الفهرس الحية: عدد الصفحات المفهرسة فعلًا + عدادات هذه العملية."""
    out: Dict[str, Any] = {"enabled": enabled(), **_STATS}
    if not out["enabled"]:
        out["reason"] = "Supabase غير مضبوط (SUPABASE_URL + SUPABASE_SECRET_KEY) أو WORLD_SEARCH_INDEX_ENABLED=false"
        return out
    try:
        with _client(timeout=4.0) as c:
            resp = c.get("/rest/v1/search_pages", params={"select": "url", "limit": "1"},
                          headers={"Prefer": "count=exact", "Range": "0-0"})
            resp.raise_for_status()
            rng = resp.headers.get("content-range") or ""
            out["pages_indexed"] = int(rng.split("/")[-1]) if "/" in rng and rng.split("/")[-1].isdigit() else None
    except Exception as e:  # TOLERATED: الحالة تُعلن الخطأ بدل إخفائه
        out["pages_indexed"] = None
        out["status_error"] = f"{type(e).__name__}: {str(e)[:120]}"
    return out
