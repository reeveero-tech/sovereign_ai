"""R-829: البحث المتعدد المحركات — ddgs (deedy5) مسحوبة كاملة + خوارزمية دمج metasearch2 (mat-1).

ddgs تتحدث مباشرة إلى صفحات نتائج محركات العالم (Google/Yandex/Brave/Mojeek/Yahoo/Startpage/
Wikipedia…) — كل محرك مزود مستقل في المحرك له قاطع دائرة خاص (بلا تجاوز للحجب: محرك يرفض ⇒ يُعلن
ويُوقف مؤقتًا). Bing له مزود أصلي في world_search فلا يُكرر هنا.

fuse(): نقل حرفي لـ merge_engine_responses في third_party/mat-1__metasearch2/src/engines/ranking.rs:
نتيجة في المرتبة r من محرك وزنه w تأخذ w/(r+1)، وتُجمع الدرجات عبر المحركات لنفس الرابط —
الرابط الذي تتفق عليه محركات عدة يعلو.
"""

import os
import re
from typing import Any, Dict, Iterable, List, Tuple

from . import vendored

# لغة السؤال ← منطقة ddgs (region)
_REGION = {"ar": "xa-ar", "en": "us-en", "fr": "fr-fr", "es": "es-es", "de": "de-de", "it": "it-it",
           "pt": "br-pt", "ru": "ru-ru", "tr": "tr-tr", "ja": "jp-jp", "zh": "cn-zh", "ko": "kr-kr",
           "nl": "nl-nl", "sv": "se-sv", "pl": "pl-pl", "hi": "in-en", "id": "id-id", "fa": "xa-ar",
           "ur": "pk-en", "he": "il-he", "uk": "ua-uk", "vi": "vn-vi", "th": "th-th"}

# أوزان المحركات (config.engines.*.weight في metasearch2) — Google وBrave أعلى دقة للويب العام
WEIGHTS = {"google": 1.05, "brave": 1.0, "bing": 1.0, "yandex": 0.9, "mojeek": 0.8, "yahoo": 0.8,
           "startpage": 0.95, "wikipedia": 0.9, "duckduckgo": 0.9}


def engines() -> List[str]:
    """المحركات المفعّلة. الافتراضي yahoo وحده: من الاختبار الحي على Render (R-829c) Google/Yandex/Mojeek
    تتجاوز المهلة وBrave/Startpage تعيد صفحة فارغة لعناوين مراكز البيانات — مزود لا يجيب يحبس مرحلة البحث
    حتى مهلتها. بيئة أخرى (خادم منزلي/VPS) تفعّل البقية: WORLD_SEARCH_DDGS_ENGINES=google,brave,yandex,…"""
    raw = os.getenv("WORLD_SEARCH_DDGS_ENGINES", "yahoo")
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


def enabled() -> bool:
    return str(os.getenv("WORLD_SEARCH_DDGS", "true")).strip().lower() != "false"


def _clean(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def search(engine: str, q: str, lang: str, max_results: int = 10, timeout: float = 5.0) -> List[Dict[str, Any]]:
    """نتائج محرك واحد عبر ddgs المسحوبة، بصيغة مزودات world_search."""
    ddgs = vendored.load("ddgs")
    if ddgs is None:
        raise RuntimeError(f"ddgs غير محمّلة: {vendored.errors().get('ddgs', 'سبب مجهول')}")
    region = _REGION.get(lang, "us-en")
    try:
        rows = ddgs.DDGS(timeout=int(max(3, timeout))).text(q, region=region, max_results=max_results,
                                                             backend=engine)
    except Exception as exc:  # TOLERATED: «لا نتائج» من ddgs ليست عطلًا للمحرك — تُعلن كرفض لا كفشل شبكة
        if "No results" in str(exc):
            raise RuntimeError(f"ddgs-{engine}: لا نتائج لهذا السؤال — رُفضت") from exc
        raise
    out = []
    for i, r in enumerate(rows or []):
        url = _clean(r.get("href") or r.get("url"))
        if not url.startswith("http"):
            continue
        out.append({"title": _clean(r.get("title"))[:300], "url": url, "snippet": _clean(r.get("body"))[:600],
                    "provider": f"ddgs-{engine}", "lang": lang, "rank": i, "engine": engine})
    return out


def provider(engine: str):
    """دالة مزود (q, lang) ⇒ نتائج — تُسجَّل في jobs محرك البحث باسم ddgs-<engine>."""
    def _p(q: str, lang: str) -> List[Dict[str, Any]]:
        return search(engine, q, lang)
    _p.__name__ = f"p_ddgs_{engine}"
    return _p


def fuse(lists: Iterable[Tuple[str, List[Dict[str, Any]]]]) -> Dict[str, Dict[str, Any]]:
    """دمج metasearch2: درجة الرابط = Σ وزن_المحرك/(المرتبة+1)، مع مجموعة المحركات المتفقة."""
    merged: Dict[str, Dict[str, Any]] = {}
    for engine, rows in lists:
        base = engine.split("-")[1] if engine.startswith("ddgs-") else engine.split("-")[0]
        w = WEIGHTS.get(base, 0.85)
        for idx, r in enumerate(rows or []):
            url = r.get("url")
            if not url:
                continue
            rank = r.get("rank", idx)
            score = w / (rank + 1)
            m = merged.setdefault(url, {"score": 0.0, "engines": set()})
            m["score"] += score
            m["engines"].add(base)
    return merged
