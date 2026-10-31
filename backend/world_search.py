"""R-823 — البحث العالمي الحتمي بلا نموذج لغوي (أمر المالك: «حتى لو لم يكن العقل متصلًا لا بد
أن يكون المشروع قادرًا على البحث في جميع مواقع العالم بكافة اللغات ثم تقييم أفضل وأصدق
إجابة ثم ترجمتها وإرفاقها للمستخدم — هذا لا يتطلب نموذجًا لغويًا»).

خط حتمي بالكامل (لا نداء عقل في أي خطوة):

١. فهم السؤال: كشف لغته من نظام كتابته، وتجريد صيغة الطلب («أريد أن تقوم ببحث عن…»)
   للوصول إلى جوهر السؤال.
٢. تعدد اللغات: ترجمة جوهر السؤال إلى لغات البحث (WORLD_SEARCH_LANGS) عبر سلسلة مترجمات
   آلية بلا مفتاح (Google gtx ← MyMemory ← Lingva) — فشل مترجم يمرر للتالي.
٣. البحث المتوازي في مزودات مستقلة: DuckDuckGo (الويب العام)، Marginalia (فهرس ويب مستقل)،
   ويكيبيديا بكل لغة بحث، وEurope PMC (الأدبيات العلمية المحكّمة)، ومزود المالك إن ضُبط
   (searxng/tavily). فشل مزود يُعلن في الحالة ولا يُسقط البحث.
٤. القراءة: أعلى صفحات الويب تُجلب عبر web_tools.fetch (حارس SSRF نفسه).
٥. التقييم: كل جملة مرشحة تُقيَّم بثلاثة أبعاد قابلة للتفسير —
   الصلة (BM25 مقابل مصطلحات السؤال بلغة المصدر)، موثوقية المصدر (طبقات نطاقات: جهات
   حكومية/أكاديمية/طبية مرجعية ⇒ أعلى، المنتديات ⇒ أدنى)، والتوافق (كم مصدرًا مستقلًا آخر
   يقول المعنى نفسه — بعد توحيد اللغة بالترجمة). الدرجة = 0.45·صلة + 0.35·موثوقية + 0.2·توافق.
٦. الاختيار: أعلى الجمل مع تنويع (لا تكرار شبه حرفي، وحد جملتين لكل مصدر).
٧. الترجمة والإرفاق: الجمل المختارة تُترجم إلى لغة المستخدم وتُرفق بمصادرها ودرجاتها.

الصدق: لا جملة في الجواب إلا وهي مقتبسة من مصدر حقيقي مرفق برابطه؛ والترجمة الآلية معلنة.
"""

from __future__ import annotations

import logging
import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, unquote, urlsplit

logger = logging.getLogger("sovereign.world_search")

UA_BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
UA_BOT = "SovereignAI/1.0 (+https://github.com/reeveero-tech/sovereign_ai)"

LANG_NAMES_AR = {
    "ar": "العربية", "en": "الإنجليزية", "fr": "الفرنسية", "es": "الإسبانية",
    "de": "الألمانية", "ru": "الروسية", "zh": "الصينية", "ja": "اليابانية",
    "ko": "الكورية", "fa": "الفارسية", "ur": "الأردية", "tr": "التركية",
    "hi": "الهندية", "pt": "البرتغالية", "it": "الإيطالية", "he": "العبرية",
}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def search_langs() -> List[str]:
    raw = os.getenv("WORLD_SEARCH_LANGS", "en,fr,es") or "en"
    return [x.strip().lower() for x in raw.split(",") if x.strip()][:8]


def enabled() -> bool:
    """البحث العالمي متاح: أدوات الويب مفعّلة وWORLD_SEARCH_ENABLED=true (أو المزود world)."""
    try:
        import config
        if not getattr(config, "WEB_TOOLS_ENABLED", False):
            return False
        if str(getattr(config, "SEARCH_PROVIDER", "") or "").strip().lower() == "world":
            return True
    except Exception:  # TOLERATED: بلا إعداد ⇒ غير مفعّل
        return False
    return str(os.getenv("WORLD_SEARCH_ENABLED", "false")).strip().lower() == "true"


def _client(timeout: Optional[float] = None):
    import httpx
    return httpx.Client(timeout=timeout or _env_float("WORLD_SEARCH_HTTP_TIMEOUT_SECONDS", 8.0),
                        follow_redirects=True, headers={"User-Agent": UA_BROWSER})


# ============================================================
# ١) اللغة وجوهر السؤال
# ============================================================
_SCRIPTS = [
    ("ar", re.compile(r"[\u0600-\u06FF]")), ("he", re.compile(r"[\u0590-\u05FF]")),
    ("ru", re.compile(r"[\u0400-\u04FF]")), ("zh", re.compile(r"[\u4E00-\u9FFF]")),
    ("ja", re.compile(r"[\u3040-\u30FF]")), ("ko", re.compile(r"[\uAC00-\uD7AF]")),
    ("hi", re.compile(r"[\u0900-\u097F]")),
]


def detect_lang(text: str) -> str:
    """كشف حتمي بنظام الكتابة الغالب (اللاتينية ⇒ en افتراضيًا)."""
    text = str(text or "")
    best, best_n = "en", 0
    for code, rx in _SCRIPTS:
        n = len(rx.findall(text))
        if n > best_n:
            best, best_n = code, n
    latin = len(re.findall(r"[A-Za-z]", text))
    return best if best_n > latin else "en"


_AR_REQUEST_PREFIX = re.compile(
    r"^\s*(?:(?:من\s+فضلك|لو\s+سمحت|رجاء[ًا]?)\s*[،,]?\s*)?"
    r"(?:(?:أ|ا)ريد(?:ك)?|(?:أ|ا)بغى|ابي|أبي|نريد|ممكن|هل\s+يمكنك|هل\s+تستطيع|(?:أ|ا)رجو)?\s*"
    r"(?:(?:أ|ا)ن\s+)?(?:تقوم\s+)?(?:ب)?"
    r"(?:(?:إ|ا)نشاء|عمل|(?:إ|ا)عداد|كتابة|(?:أ|ا)جراء|تجهيز|تبحث|ابحث|البحث|بحث)?\s*"
    r"(?:(?:بحث|بحثا|بحثًا|تقرير|تقريرا|تقريرًا|دراسة)\s*)?"
    r"(?:(?:معمق|معمقا|معمقًا|شامل|شاملا|شاملًا|مفصل|مفصلا|مفصلًا|دقيق|دقيقا|دقيقًا)\s*)?"
    r"(?:(?:عن|حول|في|بخصوص)\s+)?")
_EN_REQUEST_PREFIX = re.compile(
    r"^\s*(?:please\s+)?(?:(?:i\s+want|i'd\s+like|i\s+would\s+like|can\s+you|could\s+you)\s+(?:you\s+)?(?:to\s+)?)?"
    r"(?:do|make|create|write|perform|conduct|search|research|find)?\s*"
    r"(?:an?\s+)?(?:(?:in-depth|deep|detailed|thorough|comprehensive)\s+)?"
    r"(?:research|search|report|study)?\s*(?:on|about|for|into)?\s+", re.I)


_FITNESS_CTX = re.compile(r"دايت|رجيم|حمية|غذائي|وزن|تمرين|رياض|عضل|بروتين|سعرات|كيلو")
_AR_NORMALIZE = (
    # العامية ⇒ الفصحى قبل الترجمة (المترجم الآلي يخطئ فيها: «النادي» ⇒ club)
    (re.compile(r"(?<![\w])(?:ال)?(?:دايت|رجيم)(?![\w])"), "حمية غذائية لإنقاص الوزن"),
    (re.compile(r"(?<![\w])(?:ال)?جيم(?![\w])"), "الصالة الرياضية"),
)
_AR_GYM = re.compile(r"(يرتاد|يذهب\s+(?:إلى|الى)|يتمرن\s+في|مشترك\s+في|يداوم\s+في)\s+(?:ال)?نادي(?![\w])")


def normalize_colloquial(text: str) -> str:
    t = str(text or "")
    for rx, rep in _AR_NORMALIZE:
        t = rx.sub(rep, t)
    if _FITNESS_CTX.search(t):
        t = _AR_GYM.sub(r"\1 الصالة الرياضية", t)
    return t


def core_question(text: str) -> str:
    """جوهر السؤال بعد تجريد صيغة الطلب — يبقى النص كما هو إن لم تُطابق الصيغة."""
    t = normalize_colloquial(" ".join(str(text or "").split()))
    t2 = _AR_REQUEST_PREFIX.sub("", t, count=1)
    t2 = _EN_REQUEST_PREFIX.sub("", t2, count=1) if t2 == t else t2
    t2 = t2.strip(" ،,.؟?!")
    return t2 if len(t2) >= 4 else t.strip(" ،,.؟?!")


_STOP = {
    "en": set("""a an the of to in on for and or but with by at from as is are was were be been
        being it its this that these those what which who whom whose how why when where do does did
        i you he she we they me my your our their him her them want would like can could should
        about into than then so such very more most best someone who's goes go going wants want
        weighs weigh weighing kg kilos kilo kilogram kilograms please make create write research
        deep depth in-depth search report study those people person anyone everyone also just
        get got need needs well good""".split()),
    "fr": set("le la les un une des de du et ou en dans pour par sur au aux est sont qui que quoi "
              "comment pourquoi quel quelle ce cette ces avec plus meilleur meilleure".split()),
    "es": set("el la los las un una unos unas de del y o en para por con sobre es son que qué cómo "
              "por qué cuál este esta estos más mejor".split()),
    "de": set("der die das ein eine einer und oder in im für von mit auf ist sind was wie warum "
              "welche welcher dies diese beste besten".split()),
    "ar": set("""في من على إلى الى عن مع هذا هذه ذلك تلك التي الذي الذين ما ماذا كيف لماذا متى أين
        هل أو او و ثم لكن كان كانت يكون هو هي هم أن ان إن لا لم لن قد كل بعض أي اي أفضل افضل لمن
        يريد اريد أريد ويريد""".split()),
}


def _terms(text: str, lang: str) -> List[str]:
    stop = _STOP.get(lang, set()) | _STOP["en"]
    toks = re.findall(r"[\w\u0600-\u06FF]+", str(text or "").lower())
    out = []
    for t in toks:
        if t in stop or len(t) < 3 and not t.isdigit():
            continue
        if lang == "ar":
            t = re.sub(r"^(?:وال|بال|كال|فال|لل|ال|و)(?=\w{3,})", "", t)
        out.append(_stem(t) if lang in ("en", "fr", "es", "de") else t)
    return out


def _stem(t: str) -> str:
    """جذع خفيف حتمي: weight/weigh/weighing ⇒ weigh، dietary/dieting ⇒ diet."""
    for suf in ("ational", "ations", "ation", "ingly", "ments", "ment", "ness", "ing", "ary", "ies",
                "ied", "ed", "es", "al", "ly", "s", "t"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            t = t[: -len(suf)]
            break
    return t[:6]


# مجموعات مفاهيم (إنجليزية الجذع) — تغطية السؤال تُحسب بالمفهوم لا بالكلمة الحرفية
_CONCEPTS = (
    ({"weigh", "obes", "fat", "adipos", "bmi", "overwe"}, "obesity"),
    ({"diet", "nutrit", "calor", "kcal", "protein", "eat", "food", "meal", "carboh", "macron"}, "diet"),
    ({"gym", "exerci", "train", "resist", "workou", "fitnes", "aerobi", "strengt", "physic"}, "exercise"),
    ({"lose", "loss", "reduct", "reduc", "deficit", "lost"}, "weight loss"),
    ({"muscl", "lean", "hypert"}, "muscle"),
    ({"sleep", "insomn"}, "sleep"), ({"diabet", "glucos", "insulin"}, "diabetes"),
)


def _concepts(qterms: List[str]) -> List[set]:
    groups, used = [], set()
    for t in dict.fromkeys(qterms):
        if t.isdigit() or t in used:
            continue
        g = {t}
        for members, _canon in _CONCEPTS:
            if t in members:
                g = set(members)
                break
        if any(g == x for x in groups):
            continue
        used |= g
        groups.append(g)
    return groups


def scholarly_query(en_q: str) -> str:
    """استعلام علمي: المفاهيم بصيغتها المعيارية (gym ⇒ exercise، weigh ⇒ obesity)."""
    terms = _terms(en_q, "en")
    out = []
    for t in dict.fromkeys(terms):
        canon = next((c for m, c in _CONCEPTS if t in m), None)
        if canon and canon not in out:
            out.append(canon)
    return " ".join(out) if len(out) >= 2 else keyword_query(en_q, "en")


def keyword_query(text: str, lang: str) -> str:
    seen, out = set(), []
    for raw in re.findall(r"[\w\u0600-\u06FF]+", str(text or "")):
        low = raw.lower()
        if low in (_STOP.get(lang, set()) | _STOP["en"]) or len(low) < 3 or low.isdigit():
            continue
        if low not in seen:
            seen.add(low)
            out.append(raw)
    return " ".join(out[:10]) or str(text or "")


# ============================================================
# ٢) الترجمة الآلية بلا مفتاح — سلسلة مزودات
# ============================================================
_TR_CACHE: Dict[Tuple[str, str, str], Tuple[str, str]] = {}


def _tr_google(text: str, target: str, source: str) -> str:
    with _client() as c:
        r = c.get("https://translate.googleapis.com/translate_a/single",
                  params={"client": "gtx", "sl": source or "auto", "tl": target, "dt": "t", "q": text})
        r.raise_for_status()
        data = r.json()
    return "".join(seg[0] for seg in (data[0] or []) if seg and seg[0])


def _tr_mymemory(text: str, target: str, source: str) -> str:
    src = source if source and source != "auto" else detect_lang(text)
    if src == target:
        return text
    params = {"q": text[:480], "langpair": f"{src}|{target}"}
    email = os.getenv("WORLD_SEARCH_CONTACT_EMAIL")
    if email:
        params["de"] = email
    with _client() as c:
        r = c.get("https://api.mymemory.translated.net/get", params=params)
        r.raise_for_status()
        data = r.json()
    out = str((data.get("responseData") or {}).get("translatedText") or "")
    if not out or "MYMEMORY WARNING" in out.upper() or data.get("quotaFinished"):
        raise RuntimeError("mymemory quota")
    return out


def _tr_lingva(text: str, target: str, source: str) -> str:
    last = None
    for base in ("https://lingva.ml", "https://lingva.lunar.icu", "https://translate.plausibility.cloud"):
        try:
            with _client(6.0) as c:
                r = c.get(f"{base}/api/v1/{source or 'auto'}/{target}/{quote(text, safe='')}")
                r.raise_for_status()
                out = r.json().get("translation")
            if out:
                return str(out)
        except Exception as e:  # TOLERATED: النسخة التالية
            last = e
    raise RuntimeError(f"lingva: {type(last).__name__ if last else 'empty'}")


TRANSLATORS = (("google", _tr_google), ("mymemory", _tr_mymemory), ("lingva", _tr_lingva))
_TR_DEAD: Dict[str, float] = {}


def translate(text: str, target: str, source: str = "auto") -> Tuple[str, Optional[str]]:
    """ترجمة آلية — يعيد (النص، اسم المترجم) أو (الأصل، None) إن فشلت السلسلة كلها."""
    text = str(text or "").strip()
    if not text or (source != "auto" and source == target):
        return text, "identity"
    if source == "auto" and detect_lang(text) == target and target not in ("en", "fr", "es", "de"):
        return text, "identity"
    key = (text, target, source)
    if key in _TR_CACHE:
        return _TR_CACHE[key]
    for name, fn in TRANSLATORS:
        if time.monotonic() < _TR_DEAD.get(name, 0):
            continue
        try:
            chunks, out = _chunks(text, 450 if name == "mymemory" else 1800), []
            for ch in chunks:
                out.append(fn(ch, target, source))
            res = (" ".join(x.strip() for x in out if x).strip(), name)
            if res[0]:
                _TR_CACHE[key] = res
                return res
        except Exception as e:  # TOLERATED: المترجم التالي — يُعلَّم معطلًا مؤقتًا
            _TR_DEAD[name] = time.monotonic() + 300
            logger.info("R-823: مترجم %s فشل (%s)", name, type(e).__name__)
    return text, None


def _chunks(text: str, size: int) -> List[str]:
    if len(text) <= size:
        return [text]
    parts, cur = [], ""
    for sent in re.split(r"(?<=[.!?؟。\n])\s+", text):
        if len(cur) + len(sent) + 1 > size and cur:
            parts.append(cur)
            cur = ""
        cur = (cur + " " + sent).strip() if len(sent) < size else sent[:size]
    if cur:
        parts.append(cur)
    return parts


# ============================================================
# ٣) مزودات البحث المستقلة
# ============================================================
def _p_duckduckgo(q: str, lang: str) -> List[Dict[str, Any]]:
    region = {"en": "us-en", "fr": "fr-fr", "es": "es-es", "de": "de-de", "ar": "xa-ar"}.get(lang, "wt-wt")
    # R-825: مهلة أقصر — من عناوين السحابة كثيرًا ما تنتهي مهلته فلا يحجز ميزانية البحث
    with _client(_env_float("WORLD_SEARCH_LEGACY_TIMEOUT_SECONDS", 4.0)) as c:
        r = c.post("https://html.duckduckgo.com/html/", data={"q": q, "kl": region})
        r.raise_for_status()
        html = r.text
    out = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=class="result__a"|$)',
                         html, re.S):
        href, title, rest = m.group(1), _strip_tags(m.group(2)), m.group(3)
        if "uddg=" in href:
            href = unquote(parse_qs(urlsplit(href).query).get("uddg", [href])[0])
        if href.startswith("//"):
            href = "https:" + href
        sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.S)
        if href.startswith("http") and "duckduckgo.com/y.js" not in href:
            out.append({"title": title, "url": href, "snippet": _strip_tags(sn.group(1)) if sn else "",
                        "provider": "duckduckgo", "lang": lang})
    if not out and "anomaly" in html.lower():
        raise RuntimeError("duckduckgo: تحدي مكافحة الروبوتات")
    return out[:8]


def _p_marginalia(q: str, lang: str) -> List[Dict[str, Any]]:
    key = os.getenv("MARGINALIA_API_KEY", "public") or "public"
    with _client(_env_float("WORLD_SEARCH_LEGACY_TIMEOUT_SECONDS", 4.0)) as c:  # R-825: مهلة أقصر
        r = c.get(f"https://api.marginalia.nu/{key}/search/{quote(q, safe='')}", params={"count": 8})
        r.raise_for_status()
        data = r.json()
    return [{"title": str(x.get("title") or ""), "url": str(x.get("url") or ""),
             "snippet": str(x.get("description") or ""), "provider": "marginalia", "lang": lang}
            for x in (data.get("results") or []) if x.get("url")][:8]


def _p_wikipedia(q: str, lang: str) -> List[Dict[str, Any]]:
    import httpx
    with httpx.Client(timeout=_env_float("WORLD_SEARCH_HTTP_TIMEOUT_SECONDS", 8.0),
                      headers={"User-Agent": UA_BOT}) as c:
        r = c.get(f"https://{lang}.wikipedia.org/w/api.php", params={
            "action": "query", "generator": "search", "gsrsearch": q, "gsrlimit": 3,
            "prop": "extracts|info", "inprop": "url", "exintro": 1, "explaintext": 1,
            "exsentences": 10, "format": "json", "formatversion": 2})
        r.raise_for_status()
        pages = ((r.json().get("query") or {}).get("pages") or [])
    pages.sort(key=lambda p: p.get("index", 99))
    if pages:
        # أعلى نتيجة: المقالة كاملة (المقدمة وحدها لا تحمل التفاصيل غالبًا)
        try:
            with httpx.Client(timeout=_env_float("WORLD_SEARCH_HTTP_TIMEOUT_SECONDS", 8.0),
                              headers={"User-Agent": UA_BOT}) as c:
                r = c.get(f"https://{lang}.wikipedia.org/w/api.php", params={
                    "action": "query", "prop": "extracts", "explaintext": 1, "titles": pages[0]["title"],
                    "format": "json", "formatversion": 2})
                r.raise_for_status()
                full = (((r.json().get("query") or {}).get("pages") or [{}])[0]).get("extract")
            if full:
                pages[0]["extract"] = full[:40000]
        except Exception:  # TOLERATED: المقدمة تكفي إن تعذر الكامل
            pass
    return [{"title": p.get("title", ""), "url": p.get("fullurl") or
             f"https://{lang}.wikipedia.org/wiki/{quote(str(p.get('title', '')).replace(' ', '_'))}",
             "snippet": "", "text": p.get("extract") or "", "provider": f"wikipedia-{lang}", "lang": lang}
            for p in pages if p.get("extract")]


# ============================================================
# ويكي بيانات — حقائق دقيقة منظّمة (العاصمة/السكان/المساحة/العملة/…) بلا نموذج لغوي
# ============================================================
_WD_PROPS = (
    (("capit",), "P36"), (("popula", "people", "inhabi", "resid"), "P1082"), (("area", "size"), "P2046"),
    (("curren",), "P38"), (("langua",), "P37"), (("presid", "head of state", "king", "monarc"), "P35"),
    (("prime", "premie", "head of gov"), "P6"), (("founde", "establ", "incept", "create"), "P571"),
    (("born", "birth"), "P569"), (("died", "death"), "P570"), (("height", "tall", "elevat"), "P2048"),
    (("author", "wrote", "writer"), "P50"), (("ceo", "chief exec"), "P169"),
    (("headqu",), "P159"), (("contin",), "P30"), (("direct",), "P57"), (("anthem",), "P85"),
    (("gdp", "gross domes"), "P2131"), (("calling code", "dial"), "P474"), (("mayor",), "P6"),
)


def _wd_props_for(text: str) -> List[str]:
    low = str(text or "").lower()
    stems = set(_terms(low, "en"))
    out = []
    for keys, pid in _WD_PROPS:
        if any((k in low) if " " in k else any(st.startswith(k[:5]) for st in stems) for k in keys):
            if pid not in out:
                out.append(pid)
    return out[:4]


def _wd_entity_phrase(text: str) -> str:
    caps = re.findall(r"\b[A-Z][\w'’-]+(?:\s+(?:of|the|de|del|[A-Z][\w'’-]+))*", str(text or ""))
    caps = [c for c in caps if c.split()[0].lower() not in _STOP["en"]]
    return max(caps, key=len) if caps else ""


def _wd_get(c, params):
    r = c.get("https://www.wikidata.org/w/api.php", params={**params, "format": "json"})
    r.raise_for_status()
    return r.json()


def _p_wikidata(en_q: str, user_lang: str) -> List[Dict[str, Any]]:
    pids = _wd_props_for(en_q)
    ent = _wd_entity_phrase(en_q)
    if not pids or not ent:
        return []
    import httpx
    langs = "|".join(dict.fromkeys([user_lang, "en"]))
    with httpx.Client(timeout=_env_float("WORLD_SEARCH_HTTP_TIMEOUT_SECONDS", 8.0),
                      headers={"User-Agent": UA_BOT}) as c:
        hits = _wd_get(c, {"action": "wbsearchentities", "search": ent, "language": "en", "limit": 1}).get("search") or []
        if not hits:
            return []
        qid = hits[0]["id"]
        data = _wd_get(c, {"action": "wbgetentities", "ids": qid, "props": "claims|labels", "languages": langs})
        entity = (data.get("entities") or {}).get(qid) or {}
        claims = entity.get("claims") or {}
        facts, need_labels = [], set(pids)
        for pid in pids:
            stmts = [x for x in claims.get(pid, []) if x.get("rank") != "deprecated"]
            pref = [x for x in stmts if x.get("rank") == "preferred"] or stmts
            if not pref:
                continue
            if pid == "P1082":  # أحدث تعداد
                def _when(x):
                    q = (x.get("qualifiers") or {}).get("P585") or [{}]
                    return ((q[0].get("datavalue") or {}).get("value") or {}).get("time", "")
                pref = sorted(stmts, key=_when, reverse=True)[:1]
            for st in pref[:3]:
                dv = ((st.get("mainsnak") or {}).get("datavalue") or {})
                facts.append((pid, dv.get("type"), dv.get("value"), st))
                if dv.get("type") == "wikibase-entityid":
                    need_labels.add(dv["value"]["id"])
        labels = {}
        ids = sorted(need_labels)
        for i in range(0, len(ids), 40):
            ld = _wd_get(c, {"action": "wbgetentities", "ids": "|".join(ids[i:i + 40]), "props": "labels",
                             "languages": langs})
            for k, v in (ld.get("entities") or {}).items():
                lab = (v.get("labels") or {})
                labels[k] = (lab.get(user_lang) or lab.get("en") or {}).get("value", k)
    elabel = ((entity.get("labels") or {}).get(user_lang) or (entity.get("labels") or {}).get("en") or {}).get("value", ent)
    out: Dict[str, List[str]] = {}
    for pid, typ, val, st in facts:
        if typ == "wikibase-entityid":
            text = labels.get(val["id"], val["id"])
        elif typ == "quantity":
            amt = float(val.get("amount", "0"))
            unit = str(val.get("unit", ""))
            text = f"{amt:,.0f}" if amt >= 100 else f"{amt:g}"
            if unit.endswith("Q712226"):
                text += " كم²" if user_lang == "ar" else " km²"
            elif unit.endswith("Q11573"):
                text += " م" if user_lang == "ar" else " m"
            q = (st.get("qualifiers") or {}).get("P585")
            if q:
                yr = str(((q[0].get("datavalue") or {}).get("value") or {}).get("time", ""))[1:5]
                if yr:
                    text += f" ({yr})"
        elif typ == "time":
            t = str(val.get("time", ""))
            text = t[1:11] if val.get("precision", 9) >= 11 else t[1:5]
        elif typ == "monolingualtext":
            text = val.get("text", "")
        else:
            text = str(val)[:120]
        out.setdefault(pid, []).append(text)
    rows = []
    for pid, vals in out.items():
        rows.append({"pid": pid, "label": labels.get(pid, pid), "values": vals})
    if not rows:
        return []
    body = "؛ ".join(f"{r['label']} ({elabel}): {'، '.join(r['values'])}" if user_lang == "ar"
                    else f"{r['label']} of {elabel}: {', '.join(r['values'])}" for r in rows)
    return [{"title": f"{elabel} — Wikidata {qid}", "url": f"https://www.wikidata.org/wiki/{qid}",
             "snippet": "", "text": "", "provider": "wikidata", "lang": user_lang,
             "facts": rows, "fact_text": body, "entity": elabel}]


def _p_pubmed(q: str, lang: str) -> List[Dict[str, Any]]:
    """PubMed (المكتبة الوطنية للطب الأمريكية) — ملخصات أبحاث محكّمة عبر E-utilities بلا مفتاح."""
    import httpx
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    common = {"tool": "sovereign_ai"}
    email = os.getenv("WORLD_SEARCH_CONTACT_EMAIL")
    if email:
        common["email"] = email
    with httpx.Client(timeout=_env_float("WORLD_SEARCH_HTTP_TIMEOUT_SECONDS", 8.0),
                      headers={"User-Agent": UA_BOT}) as c:
        r = c.get(f"{base}/esearch.fcgi", params={**common, "db": "pubmed", "term": q, "retmode": "json",
                                                   "retmax": 6, "sort": "relevance"})
        r.raise_for_status()
        ids = (r.json().get("esearchresult") or {}).get("idlist") or []
        if not ids:
            return []
        r = c.get(f"{base}/efetch.fcgi", params={**common, "db": "pubmed", "id": ",".join(ids),
                                                  "retmode": "xml"})
        r.raise_for_status()
        xml = r.text
    out = []
    for art in re.findall(r"<PubmedArticle>(.*?)</PubmedArticle>", xml, re.S):
        pmid = re.search(r"<PMID[^>]*>(\d+)</PMID>", art)
        title = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", art, re.S)
        journal = re.search(r"<Title>(.*?)</Title>", art, re.S)
        year = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", art, re.S)
        abstract = " ".join(_strip_tags(x) for x in re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", art, re.S))
        if not (pmid and abstract):
            continue
        out.append({"title": f"{_strip_tags(title.group(1)) if title else ''} "
                             f"({_strip_tags(journal.group(1)) if journal else 'PubMed'}، {year.group(1) if year else ''})",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid.group(1)}/", "snippet": "",
                    "text": abstract, "provider": "pubmed", "lang": "en", "scholarly": True})
    return out


def _p_europepmc(q: str, lang: str) -> List[Dict[str, Any]]:
    with _client() as c:
        r = c.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={
            "query": f"({q}) AND HAS_ABSTRACT:Y", "format": "json", "pageSize": 6,
            "resultType": "core", "sort": "RELEVANCE"})
        r.raise_for_status()
        data = r.json()
    out = []
    for x in ((data.get("resultList") or {}).get("result") or []):
        abstract = _strip_tags(x.get("abstractText") or "")
        if not abstract:
            continue
        doi = x.get("doi")
        url = f"https://doi.org/{doi}" if doi else f"https://europepmc.org/article/{x.get('source', 'MED')}/{x.get('id')}"
        out.append({"title": f"{x.get('title', '')} ({x.get('journalTitle') or x.get('bookOrReportDetails', {}).get('publisher', '') or 'Europe PMC'}، {x.get('pubYear', '')})",
                    "url": url, "snippet": "", "text": abstract, "provider": "europepmc", "lang": "en",
                    "scholarly": True})
    return out


def _p_owner(q: str, lang: str) -> List[Dict[str, Any]]:
    """مزود المالك المضبوط (searxng/tavily) عبر web_tools.search نفسه."""
    import config
    provider = str(getattr(config, "SEARCH_PROVIDER", "") or "").lower()
    if provider in ("", "world"):
        return []
    import chat_tools
    if not chat_tools.search_configured():
        return []
    import web_tools
    res = web_tools.search(q)
    return [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("snippet", ""),
             "provider": provider, "lang": lang} for x in res.get("results", [])]


# ============================================================
# R-825: مزودات محرك البحث المطوَّر — مصادر تعمل فعلًا من عناوين السحابة
# (فُحصت حيًا من Render: Bing وأخبار Bing وأخبار Google وOpenAlex تجيب؛ DuckDuckGo
# وMarginalia تنتهي مهلتها هناك فخُفضت مهلتها ولم تُحذف — تبقى مفيدة محليًا)
# ============================================================
_BING_MKT = {"ar": "ar-SA", "en": "en-US", "fr": "fr-FR", "es": "es-ES", "de": "de-DE", "ru": "ru-RU",
             "zh": "zh-CN", "ja": "ja-JP", "ko": "ko-KR", "tr": "tr-TR", "pt": "pt-BR", "it": "it-IT",
             "hi": "en-IN", "fa": "en-US", "ur": "en-US", "he": "en-US"}
_GNEWS = {"ar": ("ar", "SA", "SA:ar"), "en": ("en-US", "US", "US:en"), "fr": ("fr", "FR", "FR:fr"),
          "es": ("es-419", "US", "US:es-419"), "de": ("de", "DE", "DE:de"), "ru": ("ru", "RU", "RU:ru"),
          "zh": ("zh-CN", "CN", "CN:zh-Hans"), "ja": ("ja", "JP", "JP:ja"), "ko": ("ko", "KR", "KR:ko"),
          "tr": ("tr", "TR", "TR:tr"), "pt": ("pt-BR", "BR", "BR:pt-419"), "it": ("it", "IT", "IT:it"),
          "hi": ("hi", "IN", "IN:hi"), "he": ("he", "IL", "IL:he")}


def _plain_client(timeout: Optional[float] = None):
    """عميل بلا ترويسة متصفح — Bing يقدّم صفحة نتائج كاملة لعميل برمجي صريح (فُحص من Render)."""
    import httpx
    return httpx.Client(timeout=timeout or _env_float("WORLD_SEARCH_HTTP_TIMEOUT_SECONDS", 8.0),
                        follow_redirects=True)


def _bing_real_url(href: str) -> str:
    """روابط Bing الوسيطة (bing.com/ck/a?…&u=a1<base64url>) ⇒ الرابط الحقيقي."""
    import base64
    import html as _html
    href = _html.unescape(href or "")
    parts = urlsplit(href)
    if (parts.hostname or "").endswith("bing.com"):
        qs = parse_qs(parts.query)
        u = (qs.get("u") or [""])[0]
        if u.startswith("a1"):
            raw = u[2:]
            try:
                return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")
            except Exception:  # TOLERATED: ترميز غير متوقع ⇒ يُترك الرابط كما هو
                return href
        if qs.get("url"):
            return unquote(qs["url"][0])
    return href


_REL_AGO = re.compile(r"^\s*(\d+)\s*(minute|min|hour|day|week|month|year|دقيقة|دقائق|ساعة|ساعات|يوم|أيام|"
                      r"أسبوع|أسابيع|شهر|أشهر|سنة|سنوات)s?\s*(?:ago)?", re.I)
_REL_SECONDS = {"minute": 60, "min": 60, "دقيقة": 60, "دقائق": 60, "hour": 3600, "ساعة": 3600,
                "ساعات": 3600, "day": 86400, "يوم": 86400, "أيام": 86400, "week": 604800,
                "أسبوع": 604800, "أسابيع": 604800, "month": 2592000, "شهر": 2592000,
                "أشهر": 2592000, "year": 31536000, "سنة": 31536000, "سنوات": 31536000}


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def parse_date(text: str) -> Optional[str]:
    """تاريخ النشر بصيغة ISO من «14 hours ago» أو RFC-822 (RSS) أو ISO — وإلا None."""
    s = str(text or "").strip()
    if not s:
        return None
    m = _REL_AGO.match(s)
    if m:
        unit = m.group(2).lower()
        return _iso(time.time() - int(m.group(1)) * _REL_SECONDS.get(unit, _REL_SECONDS.get(unit.rstrip("s"), 86400)))
    try:
        from email.utils import parsedate_to_datetime
        return _iso(parsedate_to_datetime(s).timestamp())
    except Exception:  # TOLERATED: ليست RFC-822 — نجرب ISO
        pass
    try:
        from datetime import datetime
        return _iso(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except Exception:  # TOLERATED: بلا تاريخ مقروء
        return None


def age_days(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        from datetime import datetime
        return max(0.0, (time.time() - datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()) / 86400)
    except Exception:  # TOLERATED: تاريخ غير مقروء
        return None


def parse_bing_html(html: str, lang: str) -> List[Dict[str, Any]]:
    """صفحة نتائج Bing ⇒ نتائج (عنوان/رابط حقيقي/مقتطف/تاريخ). متسامح مع تغيّر التنسيق."""
    out = []
    for block in re.split(r'<li class="b_algo\b', html)[1:]:
        block = block[:20000]
        m = re.search(r"<h2[^>]*>\s*<a\b[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", block, re.S)
        if not m:
            continue
        url = _bing_real_url(m.group(1))
        if not url.startswith("http") or "bing.com/" in url.split("?")[0]:
            continue
        snip_html = ""
        for pat in (r'<p\b[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>',
                    r'<div class="b_caption[^"]*"[^>]*>.*?<p\b[^>]*>(.*?)</p>', r"<p\b[^>]*>(.*?)</p>"):
            sm = re.search(pat, block, re.S)
            if sm:
                snip_html = sm.group(1)
                break
        published = None
        dm = re.search(r'<span class="news_dt"[^>]*>(.*?)</span>', snip_html, re.S)
        if dm:
            published = parse_date(_strip_tags(dm.group(1)))
            snip_html = snip_html.replace(dm.group(0), " ")
        snippet = _strip_tags(snip_html).lstrip("·•-– ").rstrip(" …").strip()
        out.append({"title": _strip_tags(m.group(2)), "url": url, "snippet": snippet,
                    "provider": "bing", "lang": lang, "published": published, "rank": len(out)})
    return out


def _rss_items(xml: str) -> List[Dict[str, str]]:
    import html as _html
    items = []
    for it in re.findall(r"<item\b[^>]*>(.*?)</item>", xml, re.S):
        def tag(name):
            m = re.search(rf"<{name}\b[^>]*>(.*?)</{name}>", it, re.S)
            v = m.group(1) if m else ""
            v = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", v.strip(), flags=re.S)
            return _html.unescape(v)
        src = re.search(r'<source\b[^>]*url="([^"]*)"[^>]*>(.*?)</source>', it, re.S)
        items.append({"title": _strip_tags(tag("title")), "link": tag("link").strip(),
                      "description": _strip_tags(tag("description")), "pubDate": tag("pubDate"),
                      "source": _strip_tags(tag("News:Source")) or (_strip_tags(src.group(2)) if src else ""),
                      "source_url": _html.unescape(src.group(1)) if src else ""})
    return items


def _p_bing(q: str, lang: str) -> List[Dict[str, Any]]:
    """Bing (الويب العام): صفحة النتائج HTML بلغة/سوق البحث، ثم RSS بديلًا إن خلت."""
    mkt = _BING_MKT.get(lang, "en-US")
    with _plain_client() as c:
        r = c.get("https://www.bing.com/search", params={"q": q, "setlang": lang, "mkt": mkt})
        r.raise_for_status()
        out = parse_bing_html(r.text, lang)
        if not out:
            rr = c.get("https://www.bing.com/search", params={"q": q, "format": "rss", "setlang": lang, "mkt": mkt})
            if rr.status_code == 200:
                for i, it in enumerate(_rss_items(rr.text)):
                    if it["link"].startswith("http"):
                        out.append({"title": it["title"], "url": it["link"], "snippet": it["description"],
                                    "provider": "bing", "lang": lang, "published": parse_date(it["pubDate"]),
                                    "rank": i})
    if not out and re.search(r"captcha|b_no\b", r.text[:200000], re.I):
        raise RuntimeError("bing: لا نتائج لهذا العنوان (حجب/تقييد)")
    if out and not results_match_query(out, q, lang):
        raise RuntimeError("bing: نتائج غير مطابقة للسؤال (تقييد العنوان) — رُفضت")
    return out[:10]


def results_match_query(results: List[Dict[str, Any]], q: str, lang: str, min_ratio: float = 0.3) -> bool:
    """حارس جودة: محرك مقيَّد قد يعيد صفحات لا علاقة لها بالسؤال (سياحة لسؤال حمية) —
    إن لم يحمل ٣٠٪ من النتائج على الأقل مصطلحًا من السؤال تُرفض الدفعة كلها."""
    qt = set(_terms(q, lang))
    if not qt or not results:
        return True
    hit = sum(1 for r in results if qt & set(_terms(f"{r.get('title', '')} {r.get('snippet', '')}", lang)))
    return hit / len(results) >= min_ratio


def _p_bing_news(q: str, lang: str) -> List[Dict[str, Any]]:
    """أخبار Bing (RSS): روابط المقالات الأصلية مباشرة + وصف + تاريخ نشر + اسم المصدر."""
    with _plain_client() as c:
        r = c.get("https://www.bing.com/news/search",
                  params={"q": q, "format": "rss", "setlang": lang, "mkt": _BING_MKT.get(lang, "en-US")})
        r.raise_for_status()
    out = []
    for i, it in enumerate(_rss_items(r.text)):
        url = _bing_real_url(it["link"])
        if not url.startswith("http"):
            continue
        out.append({"title": it["title"], "url": url, "snippet": it["description"],
                    "text": f"{it['title']}. {it['description']}".strip(), "provider": "bing-news",
                    "lang": lang, "published": parse_date(it["pubDate"]), "news": True,
                    "site": it["source"], "rank": i})
    return out[:10]


def _p_google_news(q: str, lang: str) -> List[Dict[str, Any]]:
    """أخبار Google (RSS) بلغة وبلد البحث: عناوين حديثة مؤرخة مع اسم الناشر."""
    hl, gl, ceid = _GNEWS.get(lang, ("en-US", "US", "US:en"))
    with _plain_client() as c:
        r = c.get("https://news.google.com/rss/search", params={"q": q, "hl": hl, "gl": gl, "ceid": ceid})
        r.raise_for_status()
    out = []
    for i, it in enumerate(_rss_items(r.text)[:15]):
        title = it["title"]
        site = it["source"]
        if site and title.endswith(" - " + site):
            title = title[: -len(site) - 3]
        out.append({"title": title, "url": it["link"], "snippet": "", "text": title,
                    "provider": "google-news", "lang": lang, "published": parse_date(it["pubDate"]),
                    "news": True, "site": site, "site_url": it["source_url"], "rank": i})
    return out


def _openalex_abstract(inv: Optional[Dict[str, List[int]]]) -> str:
    if not inv:
        return ""
    pos: Dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def _p_openalex(q: str, lang: str) -> List[Dict[str, Any]]:
    """OpenAlex: فهرس عالمي مفتوح لـ ٢٥٠+ مليون عمل علمي — الملخص يُعاد بناؤه من الفهرس المقلوب."""
    params = {"search": q, "per-page": 6, "select": "id,doi,title,publication_year,abstract_inverted_index,"
              "primary_location,cited_by_count"}
    mail = os.getenv("WORLD_SEARCH_CONTACT_EMAIL")
    if mail:
        params["mailto"] = mail
    with _client() as c:
        r = c.get("https://api.openalex.org/works", params=params)
        r.raise_for_status()
        data = r.json()
    out = []
    for w in data.get("results") or []:
        abstract = _openalex_abstract(w.get("abstract_inverted_index"))
        if len(abstract) < 120:
            continue
        loc = (w.get("primary_location") or {})
        url = w.get("doi") or loc.get("landing_page_url") or w.get("id")
        out.append({"title": str(w.get("title") or "")[:300], "url": url, "snippet": abstract[:300],
                    "text": abstract, "provider": "openalex", "lang": "en", "scholarly": True,
                    "published": f"{w['publication_year']}-01-01T00:00:00Z" if w.get("publication_year") else None,
                    "cited_by": w.get("cited_by_count")})
    return out


def _p_stackexchange(q: str, lang: str) -> List[Dict[str, Any]]:
    """Stack Overflow (أسئلة وأجوبة برمجية) — مقتطفات الأسئلة والأجوبة المطابقة."""
    with _client() as c:
        r = c.get("https://api.stackexchange.com/2.3/search/excerpts",
                  params={"order": "desc", "sort": "relevance", "q": q, "site": "stackoverflow", "pagesize": 8})
        r.raise_for_status()
        items = r.json().get("items") or []
    out = []
    for it in items:
        qid = it.get("question_id")
        if not qid:
            continue
        url = f"https://stackoverflow.com/q/{qid}" + (f"#{it['answer_id']}" if it.get("answer_id") else "")
        body = _strip_tags(it.get("excerpt") or "")
        out.append({"title": _strip_tags(it.get("title") or ""), "url": url, "snippet": body[:300],
                    "text": f"{_strip_tags(it.get('title') or '')}. {body}", "provider": "stackoverflow",
                    "lang": "en", "published": _iso(it["last_activity_date"]) if it.get("last_activity_date") else None})
    return out


def _p_hackernews(q: str, lang: str) -> List[Dict[str, Any]]:
    """Hacker News (Algolia): أخبار التقنية ونقاشاتها مع الرابط الأصلي والتاريخ."""
    with _client() as c:
        r = c.get("https://hn.algolia.com/api/v1/search", params={"query": q, "tags": "story", "hitsPerPage": 8})
        r.raise_for_status()
        hits = r.json().get("hits") or []
    return [{"title": h.get("title") or "", "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
             "snippet": "", "text": h.get("title") or "", "provider": "hackernews", "lang": "en",
             "published": h.get("created_at"), "news": True, "site": "Hacker News", "rank": i}
            for i, h in enumerate(hits) if h.get("title")]


def _p_index(terms: List[str], lang: str, fresh: bool = False) -> List[Dict[str, Any]]:
    """الفهرس الذاتي (search_index): صفحات قرأها المحرك سابقًا — لا يحجبه أحد. للآني: يومان فقط."""
    import search_index
    return search_index.query(terms, limit=6, max_age_days=2 if fresh else 3650)


# ---------- نوايا السؤال ----------
_FRESH = re.compile(
    r"اليوم|الآن|الان|حاليًا|حاليا|الحالي|الحالية|أحدث|احدث|"
    r"آخر\s+(?:أخبار|اخبار|إصدار|اصدار|تحديث|نسخة|موديل|سعر|مستجدات|التطورات)|"
    r"(?<![\w])(?:ب|وب|و|ال|بال|وال)?سعر(?!ات)|أسعار|اسعار|أخبار|اخبار|عاجل|مستجدات|"
    r"هذا الأسبوع|هذا الشهر|هذه السنة|هذا العام|مباراة|طقس|"
    r"\b(?:today|now|currently|latest|newest|recent|price|prices|news|breaking|this week|this month|"
    r"this year|tonight|score|weather|stock price|exchange rate)\b|\b20[2-3]\d\b", re.I)
_TECH = re.compile(
    r"برمج|كود|بايثون|جافا|خطأ برمجي|مكتبة|\b(?:python|javascript|typescript|java|rust|golang|c\+\+|c#|sql|"
    r"api|bug|error|exception|library|framework|react|docker|kubernetes|linux|git|npm|pip|code|"
    r"programming|compile|regex|llm|ai model|gpu)\b", re.I)


def is_fresh(text: str) -> bool:
    """سؤال آني (أسعار/أخبار/اليوم/أحدث/سنة حديثة) ⇒ الأولوية لمصادر الأخبار والحداثة."""
    return bool(_FRESH.search(str(text or "")))


def is_tech(text: str) -> bool:
    return bool(_TECH.search(str(text or "")))


def freshness(iso: Optional[str], horizon_days: float = 30.0) -> float:
    """درجة الحداثة 0..1 (اليوم=1، تتناقص حتى الأفق، بلا تاريخ=0)."""
    d = age_days(iso)
    if d is None:
        return 0.0
    return round(max(0.0, 1.0 - d / horizon_days), 3)


def news_digest(sources: List[Dict[str, Any]], qterms: Dict[str, List[str]], limit: int = 6) -> List[Dict[str, Any]]:
    """أحدث العناوين المطابقة (أخبار Bing/Google/HN) — تغطية مصطلحات السؤال × الحداثة، مع تنويع الناشرين."""
    scored = []
    for i, s in enumerate(sources):
        if not s.get("news"):
            continue
        lang = s.get("lang") or "en"
        q = qterms.get(lang) or qterms.get("en") or []
        groups = _concepts(q) or [set(q)]
        ds = set(_terms(f"{s.get('title', '')} {s.get('snippet', '')}", lang))
        cov = (sum(1 for g in groups if g & ds) / len(groups)) if groups else 0.0
        need = 1.0 if len(groups) <= 2 else 0.6
        if cov < need - 1e-9:
            continue
        fr = freshness(s.get("published"), 14.0)
        direct = 0.05 if s.get("provider") != "google-news" else 0.0  # رابط المقالة المباشر أفضل للقارئ
        scored.append((0.6 * cov + 0.4 * fr + direct, i))
    out, seen_titles, per_site = [], [], {}
    for sc, i in sorted(scored, key=lambda x: -x[0]):
        s = sources[i]
        tset = set(_terms(s.get("title", ""), s.get("lang") or "en"))
        if any(_jaccard(tset, t) > 0.6 for t in seen_titles):
            continue
        site = (s.get("site") or urlsplit(s["url"]).hostname or "").lower()
        if per_site.get(site, 0) >= 2:
            continue
        per_site[site] = per_site.get(site, 0) + 1
        seen_titles.append(tset)
        out.append({"source_idx": i, "score": round(sc, 3)})
        if len(out) >= limit:
            break
    return out


def _strip_tags(s: str) -> str:
    import html as _html
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())


# ============================================================
# ٤) الموثوقية — طبقات نطاقات قابلة للتفسير
# ============================================================
_HIGH = ("who.int", "nih.gov", "ncbi.nlm.nih.gov", "cdc.gov", "nhs.uk", "europepmc.org",
         "doi.org", "cochrane", "mayoclinic.org", "clevelandclinic.org", "hopkinsmedicine.org",
         "harvard.edu", "stanford.edu", "bmj.com", "thelancet.com", "nature.com", "nejm.org",
         "sciencedirect.com", "springer.com", "wiley.com", "jamanetwork.com", "fao.org", "un.org",
         "worldbank.org", "oecd.org", "europa.eu", "britannica.com", "moh.gov.sa", "sfda.gov.sa")
_LOW = ("reddit.com", "quora.com", "pinterest.", "facebook.com", "tiktok.com", "instagram.com",
        "x.com", "twitter.com", "youtube.com", "answers.", "forum", "blogspot.", "medium.com")


_TECH_COMMUNITY = ("stackoverflow.com", "stackexchange.com", "superuser.com", "serverfault.com",
                   "github.com", "docs.python.org", "developer.mozilla.org", "learn.microsoft.com")


def credibility(url: str, scholarly: bool = False) -> Tuple[float, str]:
    host = (urlsplit(url).hostname or "").lower()
    if scholarly:
        return 1.0, "بحث علمي محكّم"
    if any(h in host for h in _HIGH) or re.search(r"\.(gov|edu|ac\.[a-z]{2}|gov\.[a-z]{2}|edu\.[a-z]{2})$", host):
        return 1.0, "جهة مرجعية (حكومية/أكاديمية/طبية)"
    if host.endswith("wikipedia.org"):
        return 0.8, "موسوعة (ويكيبيديا)"
    if host.endswith("wikidata.org"):
        return 0.95, "قاعدة بيانات منظّمة (ويكي بيانات)"
    if any(h in host for h in _LOW):
        return 0.35, "منتدى/شبكة اجتماعية"
    if any(host == h or host.endswith("." + h) for h in _TECH_COMMUNITY):  # R-825
        return 0.7, "مجتمع تقني (أسئلة وأجوبة/مستودعات)"
    return 0.6, "موقع عام"


# ============================================================
# ٥) التقطيع والتقييم
# ============================================================
_BOILER = re.compile(r"cookie|subscribe|sign up|newsletter|all rights reserved|javascript|privacy policy|"
                     r"click here|advertis|log in|skip to|main content|search the|back to|"
                     r"ملفات تعريف|اشترك|جميع الحقوق|انتقل إلى المحتوى", re.I)


def sentences(text: str) -> List[str]:
    out = []
    for s in re.split(r"(?<=[.!?؟。])\s+|\n+", str(text or "")):
        s = " ".join(s.split())
        if 40 <= len(s) <= 330 and not _BOILER.search(s) and len(re.findall(r"[\w\u0600-\u06FF]", s)) > len(s) * 0.6:
            out.append(s)
    return out


def _bm25(docs: List[List[str]], query: List[str], k1: float = 1.4, b: float = 0.75) -> List[float]:
    if not docs:
        return []
    n = len(docs)
    avg = sum(len(d) for d in docs) / n or 1.0
    df: Dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    qset = list(dict.fromkeys(query))
    scores = []
    for d in docs:
        tf: Dict[str, int] = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        for t in qset:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avg))
        scores.append(s)
    return scores


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


_SUBQ = re.compile(r"\s*(?:,\s*)?\b(?:and|also)\s+(?=(?:how|what|who|when|where|which|why|is|are|does|do)\b)", re.I)


def split_subquestions(en_q: str) -> List[str]:
    """«ما عاصمة اليابان وكم عدد سكانها» ⇒ جزآن؛ الكيان المسمى في الأول يُحمل للتالي."""
    parts = [p.strip(" ?.") for p in _SUBQ.split(str(en_q or "")) if p and p.strip(" ?.")]
    if len(parts) < 2:
        return [en_q] if en_q else []
    ent = _wd_entity_phrase(parts[0])
    return [parts[0]] + [(p + " " + ent).strip() if ent and ent not in p else p for p in parts[1:]][:3]


def evaluate(candidates: List[Dict[str, Any]], qterms_by_lang: Dict[str, List[str]],
             to_pivot=None, top_k: int = 6, fresh_mode: bool = False) -> List[Dict[str, Any]]:
    """يقيّم الجمل المرشحة ويختار أفضلها — حتمي بالكامل وقابل للتفسير.

    candidates: [{text, lang, source_idx, cred, fresh?}] — to_pivot(list[str], lang) يوحّد اللغة للتوافق.
    R-825: fresh_mode (سؤال آني) ⇒ بُعد رابع «الحداثة» من تاريخ نشر المصدر:
    0.4·صلة + 0.25·موثوقية + 0.15·توافق + 0.2·حداثة — فخبر الأمس يغلب مقالة تاريخية.
    """
    if not candidates:
        return []
    by_lang: Dict[str, List[int]] = {}
    for i, c in enumerate(candidates):
        by_lang.setdefault(c["lang"], []).append(i)
    rel = [0.0] * len(candidates)
    for lang, idxs in by_lang.items():
        q = qterms_by_lang.get(lang) or qterms_by_lang.get("en") or []
        docs = [_terms(candidates[i]["text"], lang) for i in idxs]
        sc = _bm25(docs, q)
        mx = max(sc) if sc else 0
        groups = _concepts(q) or [set(q)]
        need = len(groups) if len(groups) <= 2 else max(2, math.ceil(0.6 * len(groups)))
        for i, s_, d in zip(idxs, sc, docs):
            ds = set(d)
            hit = sum(1 for g in groups if g & ds)
            cov = hit / len(groups) if groups else 0.0
            if len(candidates[i]["text"].split()) < 9:
                hit = 0  # عنوان/شذرة لا جملة خبرية
            # تغطية مصطلحات السؤال شرط: جملة تطابق مصطلحًا عرضيًا واحدًا ليست جوابًا
            candidates[i]["coverage"] = round(cov, 3)
            rel[i] = 0.0 if hit < need else 0.6 * cov + 0.4 * ((s_ / mx) if mx > 0 else 0.0)
    # الأعلى صلةً فقط يدخل حساب التوافق (حد زمني للترجمة)
    pool = sorted(range(len(candidates)), key=lambda i: -(rel[i] * 0.6 + candidates[i]["cred"] * 0.4))[:30]
    pool = [i for i in pool if rel[i] > 0.05] or pool[:10]
    pivot_text: Dict[int, str] = {}
    for lang in {candidates[i]["lang"] for i in pool}:
        idxs = [i for i in pool if candidates[i]["lang"] == lang]
        texts = [candidates[i]["text"] for i in idxs]
        conv = to_pivot(texts, lang) if (to_pivot and lang != "en") else texts
        for i, t in zip(idxs, conv):
            pivot_text[i] = t
    term_sets = {i: set(_terms(pivot_text.get(i, candidates[i]["text"]),
                               "en" if i in pivot_text and pivot_text[i] != candidates[i]["text"]
                               else candidates[i]["lang"])) for i in pool}
    agree = {}
    for i in pool:
        others = {candidates[j]["source_idx"] for j in pool
                  if candidates[j]["source_idx"] != candidates[i]["source_idx"]
                  and _jaccard(term_sets[i], term_sets[j]) >= 0.16}
        agree[i] = min(1.0, len(others) / 3.0)
    for i in pool:
        c = candidates[i]
        c["relevance"] = round(rel[i], 3)
        c["agreement"] = round(agree[i], 3)
        if fresh_mode:
            c["score"] = round(0.4 * rel[i] + 0.25 * c["cred"] + 0.15 * agree[i] + 0.2 * c.get("fresh", 0.0), 3)
        else:
            c["score"] = round(0.45 * rel[i] + 0.35 * c["cred"] + 0.2 * agree[i], 3)
        c["pivot"] = pivot_text.get(i, c["text"])
    chosen: List[int] = []
    per_source: Dict[int, int] = {}
    for i in sorted(pool, key=lambda i: -candidates[i]["score"]):
        c = candidates[i]
        if c["relevance"] < 0.12 or per_source.get(c["source_idx"], 0) >= 2:
            continue
        if any(_jaccard(term_sets[i], term_sets[j]) > 0.5 for j in chosen):
            continue
        chosen.append(i)
        per_source[c["source_idx"]] = per_source.get(c["source_idx"], 0) + 1
        if len(chosen) >= top_k:
            break
    return [candidates[i] for i in chosen]


# ============================================================
# ٦) الخط الكامل
# ============================================================
def _run_parallel(jobs: List[Tuple[str, Any, tuple]], deadline: float) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """تشغيل متوازٍ بميزانية زمنية حقيقية.

    R-825 (إصلاح): كان `with ThreadPoolExecutor` ينتظر عند الخروج كل مزود بطيء حتى انتهاء مهلته
    الخاصة — فالميزانية لم تكن تُطبَّق فعليًا. الآن: عند انتهاء الميزانية يُعلن ما لم يكتمل
    «تجاوز المهلة» ويُترك خيطه يكمل في الخلفية دون أن يحجز الجواب.
    """
    results, status = {}, {}
    if not jobs:
        return results, status
    ex = ThreadPoolExecutor(max_workers=min(24, max(1, len(jobs))))
    futs = {ex.submit(fn, *args): name for name, fn, args in jobs}
    try:
        for f in as_completed(futs, timeout=max(1.0, deadline - time.monotonic())):
            name = futs[f]
            try:
                results[name] = f.result()
                status[name] = f"ok ({len(results[name]) if isinstance(results[name], list) else 1})"
            except Exception as e:  # TOLERATED: مزود واحد يفشل لا يسقط البحث — يُعلن
                status[name] = f"فشل: {type(e).__name__}: {str(e)[:80]}"
    except Exception:  # TOLERATED: انتهاء الميزانية — ما لم يكتمل يُعلن
        for f, name in futs.items():
            status.setdefault(name, "تجاوز المهلة")
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    _LAST_STATUS.update({k: {"status": v, "at": int(time.time())} for k, v in status.items()})
    return results, status


_LAST_STATUS: Dict[str, Dict[str, Any]] = {}


def engine_status() -> Dict[str, Any]:
    """حالة محرك البحث: آخر نتيجة لكل مزود (من عمليات حقيقية) + حالة الفهرس الذاتي."""
    import search_index
    return {"enabled": enabled(), "languages": search_langs(), "providers_last_run": dict(_LAST_STATUS),
            "index": search_index.status(),
            "providers": ["bing", "bing-news", "google-news", "wikipedia-*", "wikidata", "pubmed",
                          "europepmc", "openalex", "stackoverflow", "hackernews", "index",
                          "duckduckgo", "marginalia", "owner-provider"]}


def search_results(query: str, max_results: int = 10) -> Dict[str, Any]:
    """نتائج بحث موحدة من كل المزودات (يخدم web.search بالمزود world).

    R-825: Bing أولًا (يعمل من السحابة) + الفهرس الذاتي + أخبار Google للأسئلة الآنية، ثم
    DuckDuckGo/Marginalia/ويكيبيديا. الدمج تبادلي (الأول من كل مزود ثم الثاني…) بلا تكرار.
    """
    lang = detect_lang(query)
    core = core_question(query)
    q = keyword_query(core, lang)
    fresh = is_fresh(query)
    deadline = time.monotonic() + _env_float("WORLD_SEARCH_SEARCH_BUDGET_SECONDS", 12.0)
    jobs = [("bing", _p_bing, (q, lang)), ("index", _p_index, (_terms(core, lang), lang, fresh)),
            ("duckduckgo", _p_duckduckgo, (q, lang)), ("marginalia", _p_marginalia, (q, lang)),
            (f"wikipedia-{lang}", _p_wikipedia, (q, lang))]
    if fresh:
        jobs.insert(1, ("google-news", _p_google_news, (q, lang)))
        jobs.insert(2, ("bing-news", _p_bing_news, (q, lang)))
    if is_tech(query):
        jobs.append(("stackoverflow", _p_stackexchange, (q, lang)))
    results, status = _run_parallel(jobs, deadline)
    lists = [results.get(name) or [] for name, *_ in jobs]
    merged, seen = [], set()
    for depth in range(max((len(x) for x in lists), default=0)):
        for lst in lists:
            if depth < len(lst):
                r = lst[depth]
                if not r.get("url") or r["url"] in seen:
                    continue
                seen.add(r["url"])
                merged.append({"title": r["title"][:200], "url": r["url"][:500],
                               "snippet": (r.get("snippet") or r.get("text") or "")[:500],
                               "provider": r.get("provider"), "published": r.get("published"),
                               "site": r.get("site")})
    if not merged:
        raise RuntimeError("فشل البحث العالمي — كل المزودات: " + "؛ ".join(f"{k}: {v}" for k, v in status.items()))
    return {"query": query, "provider": "world", "count": min(len(merged), max_results),
            "results": merged[:max_results], "providers": status, "fresh": fresh}


def answer(question: str, target_lang: Optional[str] = None) -> Dict[str, Any]:
    """سؤال بأي لغة ⇒ أفضل إجابة مقيّمة من مصادر العالم مترجمة إلى لغة السائل. بلا نموذج لغوي."""
    t0 = time.monotonic()
    budget = _env_float("WORLD_SEARCH_BUDGET_SECONDS", 40.0)
    deadline = t0 + budget
    question = str(question or "").strip()[:600]
    if not question:
        return {"ok": False, "error": "سؤال فارغ"}
    user_lang = target_lang or detect_lang(question)
    core = core_question(question)
    import search_index
    use_cache = str(os.getenv("WORLD_SEARCH_CACHE", "true")).strip().lower() != "false"
    ckey = search_index.cache_key(core, user_lang)
    if use_cache:
        hit = search_index.cache_get(ckey)
        if hit and hit.get("ok"):
            hit["elapsed_seconds"] = round(time.monotonic() - t0, 2)
            return hit
    langs = list(dict.fromkeys([user_lang] + search_langs()))
    translators_used: Dict[str, str] = {}

    # ١) ترجمة جوهر السؤال إلى لغات البحث (متوازية)
    def _tq(lang):
        if lang == user_lang:
            return core, "identity"
        return translate(core, lang, user_lang)
    tq, tstat = _run_parallel([(lang, _tq, (lang,)) for lang in langs], t0 + 8.0)
    queries: Dict[str, str] = {}
    for lang in langs:
        if lang in tq and tq[lang][1]:
            queries[lang] = tq[lang][0]
            translators_used[f"سؤال→{lang}"] = tq[lang][1]
    qterms = {lang: _terms(q, lang) for lang, q in queries.items()}
    en_q = queries.get("en")
    fresh = is_fresh(question) or is_fresh(en_q or "")
    tech = is_tech(question) or is_tech(en_q or "")

    # ٢) البحث المتوازي
    jobs = []
    for lang, q in queries.items():
        jobs.append((f"wikipedia-{lang}", _p_wikipedia, (keyword_query(q, lang), lang)))
    web_lang = "en" if en_q else user_lang
    web_q = keyword_query(queries.get(web_lang, core), web_lang)
    user_q = keyword_query(core, user_lang)
    # R-825: Bing أولًا (يعمل من السحابة) بلغة السائل وبالإنجليزية، والفهرس الذاتي دائمًا
    jobs.insert(0, ("bing", _p_bing, (web_q, web_lang)))
    if user_lang != web_lang:
        jobs.insert(1, (f"bing-{user_lang}", _p_bing, (user_q, user_lang)))
    idx_terms = list(dict.fromkeys(t for lang in queries for t in qterms.get(lang, [])))[:16]
    jobs.append(("index", _p_index, (idx_terms, user_lang, fresh)))
    if fresh:  # سؤال آني ⇒ مصادر الأخبار المؤرخة بلغة السائل وبالإنجليزية
        for lang_ in dict.fromkeys([user_lang, web_lang]):
            qq = user_q if lang_ == user_lang else web_q
            jobs.append((f"bing-news-{lang_}", _p_bing_news, (qq, lang_)))
            jobs.append((f"google-news-{lang_}", _p_google_news, (qq, lang_)))
    if tech and en_q:
        jobs.append(("stackoverflow", _p_stackexchange, (keyword_query(en_q, "en"), "en")))
        jobs.append(("hackernews", _p_hackernews, (keyword_query(en_q, "en"), "en")))
    if en_q and not fresh:
        jobs.append(("openalex", _p_openalex, (scholarly_query(en_q), "en")))
    jobs.append(("duckduckgo", _p_duckduckgo, (web_q, web_lang)))
    if user_lang != web_lang:
        jobs.append((f"duckduckgo-{user_lang}", _p_duckduckgo, (keyword_query(core, user_lang), user_lang)))
    jobs.append(("marginalia", _p_marginalia, (web_q, web_lang)))
    if en_q:
        jobs.append(("europepmc", _p_europepmc, (scholarly_query(en_q), "en")))
        jobs.append(("pubmed", _p_pubmed, (scholarly_query(en_q), "en")))
    jobs.append(("owner-provider", _p_owner, (web_q, web_lang)))
    if en_q:
        jobs.append(("wikidata", _p_wikidata, (en_q, user_lang)))
    sres, providers = _run_parallel(jobs, min(deadline, time.monotonic() + 14.0))
    providers = {k: v for k, v in providers.items() if not (k == "owner-provider" and v.startswith("ok (0"))}

    # ٣) المصادر + قراءة أعلى صفحات الويب
    sources: List[Dict[str, Any]] = []
    seen = set()
    order = [n for n, *_ in jobs]
    for name in order:
        for r in sres.get(name) or []:
            url = r.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            cred, label = credibility(url, bool(r.get("scholarly")))
            sources.append({**r, "cred": cred, "cred_label": label})
    # R-825: ترتيب القراءة = موثوقية + مكافأة ترتيب محرك البحث (أعلى نتائج Bing) + للآني: أخبار Bing
    def _read_priority(s_):
        bonus = 0.0
        if str(s_.get("provider", "")).startswith("bing") and s_.get("rank", 99) < 4:
            bonus += 0.3 - 0.05 * s_.get("rank", 0)
        if fresh and s_.get("news"):
            bonus += 0.2
        return -(s_["cred"] + bonus)
    readable = [s_ for s_ in sources if not s_.get("text")
                or (fresh and s_.get("provider") == "bing-news" and s_.get("rank", 99) < 3)]
    web_to_read = sorted(readable, key=_read_priority)[:_env_int("WORLD_SEARCH_MAX_PAGES", 6)]

    def _read(src):
        import web_tools
        page = web_tools.fetch(src["url"], timeout=8.0)
        return (page.get("text") or "")[:60000]
    if web_to_read and time.monotonic() < deadline - 6:
        pres, pstat = _run_parallel([(s["url"], _read, (s,)) for s in web_to_read],
                                    min(deadline - 5, time.monotonic() + 12.0))
        for s in web_to_read:
            base = s.get("text") or ""
            s["text"] = ((base + "\n") if base and s["url"] in pres else "") + (pres.get(s["url"]) or base or s.get("snippet") or "")
            s["read"] = s["url"] in pres
    for s in sources:
        if not s.get("text"):
            s["text"] = s.get("snippet") or ""

    # ٤) المرشحات والتقييم
    candidates = []
    for idx, s in enumerate(sources):
        if fresh and s.get("news") and s.get("text") == s.get("title"):
            continue  # عنوان خبر مجرد ⇒ يُعرض في «أحدث العناوين» لا كنقطة مكررة
        fr = freshness(s.get("published"), 30.0)
        cred = s["cred"]
        if fresh and (s.get("provider", "").startswith("wikipedia") or s.get("scholarly")):
            cred = round(cred * 0.7, 3)  # الآني: الموسوعة والأبحاث لا تعرف سعر اليوم
        texts = sentences(s["text"])[:60]
        if s.get("snippet") and s.get("text") != s.get("snippet"):
            texts = sentences(s["snippet"])[:2] + texts  # مقتطف المحرك غالبًا أدق جملة
        for sent in dict.fromkeys(texts):
            candidates.append({"text": sent, "lang": s.get("lang") or detect_lang(sent),
                               "source_idx": idx, "cred": cred, "fresh": fr})
    for c in candidates:  # لغة الجملة الفعلية (صفحة إنجليزية من بحث عربي مثلًا)
        c["lang"] = detect_lang(c["text"]) if c["lang"] not in ("fr", "es", "de") else c["lang"]

    def _to_pivot(texts, lang):
        if time.monotonic() > deadline - 6:
            return texts
        joined = "\n".join(texts)
        out, name = translate(joined, "en", lang)
        if not name or name == "identity":
            return texts
        parts = out.split("\n")
        return parts if len(parts) == len(texts) else texts
    top_k = _env_int("WORLD_SEARCH_TOP_K", 6)
    parts = split_subquestions(en_q) if en_q else []
    if len(parts) > 1:
        # سؤال مركّب: كل جزء يُقيَّم وحده (جملة تجيب جزءًا لا تُحسب جوابًا للآخر)
        chosen, seen_txt = [], set()
        for part in parts:
            for c in evaluate([dict(x) for x in candidates], {**qterms, "en": _terms(part, "en")},
                              _to_pivot, top_k=max(2, top_k // len(parts)), fresh_mode=fresh):
                if c["text"] not in seen_txt:
                    seen_txt.add(c["text"])
                    chosen.append(c)
    else:
        chosen = evaluate(candidates, qterms, _to_pivot, top_k=top_k, fresh_mode=fresh)
    wd = next((s_ for s_ in sources if s_.get("provider") == "wikidata"), None)
    if wd:  # الحقيقة المنظّمة تجيب ⇒ لا يُرفق من الجمل إلا القوي جدًا (لا حشو)
        chosen = [c for c in chosen if c.get("score", 0) >= 0.75 and c.get("coverage", 0) >= 0.99][:3]

    # ٥) الترجمة إلى لغة السائل
    for c in chosen:
        if c["lang"] == user_lang:
            c["translated"], c["translator"] = c["text"], "identity"
            continue
        if time.monotonic() > deadline - 2:
            c["translated"], c["translator"] = c["text"], None
            continue
        # الأصل أولًا (أدق)؛ وإن فشل والنسخة الوسيطة الإنجليزية متاحة تُترجم هي
        c["translated"], c["translator"] = translate(c["text"], user_lang, c["lang"])
        if not c["translator"] and c.get("pivot") and c["pivot"] != c["text"]:
            c["translated"], c["translator"] = translate(c["pivot"], user_lang, "en")
    # R-825: أحدث العناوين المطابقة (للأسئلة الآنية) — مؤرخة ومترجمة إلى لغة السائل
    digest = news_digest(sources, qterms, limit=_env_int("WORLD_SEARCH_NEWS_ITEMS", 5)) if fresh else []
    for lang_ in {sources[d["source_idx"]].get("lang") for d in digest}:
        idxs = [d for d in digest if sources[d["source_idx"]].get("lang") == lang_]
        titles = [sources[d["source_idx"]]["title"] for d in idxs]
        if lang_ == user_lang or time.monotonic() > deadline - 2:
            out_t, tname = titles, ("identity" if lang_ == user_lang else None)
        else:
            joined, tname = translate("\n".join(titles), user_lang, lang_ or "auto")
            out_t = joined.split("\n") if tname and len(joined.split("\n")) == len(titles) else titles
            tname = tname if out_t is not titles else None
        for d, t in zip(idxs, out_t):
            d["translated"], d["translator"] = t, tname
    used_idx = [sources.index(wd)] if wd else []
    for c in chosen:
        if c["source_idx"] not in used_idx:
            used_idx.append(c["source_idx"])
    for d in digest:
        if d["source_idx"] not in used_idx:
            used_idx.append(d["source_idx"])
    cited = [{"n": n + 1, "title": sources[i].get("title", "")[:160], "url": sources[i]["url"],
              "provider": sources[i].get("provider"), "credibility": sources[i]["cred"],
              "credibility_label": sources[i]["cred_label"], "lang": sources[i].get("lang"),
              "published": sources[i].get("published"), "site": sources[i].get("site")}
             for n, i in enumerate(used_idx)]
    num = {i: n + 1 for n, i in enumerate(used_idx)}  # يشمل مصادر الأخبار
    points = [{"text": c.get("translated") or c["text"], "original": c["text"], "lang": c["lang"],
               "source": num[c["source_idx"]], "score": c["score"], "relevance": c["relevance"],
               "agreement": c["agreement"], "credibility": c["cred"], "translator": c.get("translator"),
               "published": sources[c["source_idx"]].get("published"), "freshness": c.get("fresh", 0.0)}
              for c in chosen]
    news = [{"title": d.get("translated") or sources[d["source_idx"]]["title"],
             "original": sources[d["source_idx"]]["title"], "source": num.get(d["source_idx"]) or
             (used_idx.index(d["source_idx"]) + 1), "site": sources[d["source_idx"]].get("site"),
             "published": sources[d["source_idx"]].get("published"), "url": sources[d["source_idx"]]["url"],
             "score": d["score"], "translator": d.get("translator")} for d in digest]
    if wd:  # الحقيقة المنظّمة أولًا — أدق من أي جملة مقتبسة
        points.insert(0, {"text": wd["fact_text"], "original": wd["fact_text"], "lang": user_lang,
                          "source": 1, "score": 1.0,
                          "relevance": 1.0, "agreement": 0.0, "credibility": wd["cred"],
                          "translator": "identity", "structured": True})
    # R-825: الفهرس الذاتي ينمو — كل ما قُرئ أو وُجد بنص كافٍ يُحفظ في الخلفية
    search_index.store_pages_async([s_ for s_ in sources if s_.get("provider") != "index" and
                                    (s_.get("read") or s_.get("news") or s_.get("scholarly")
                                     or str(s_.get("provider", "")).startswith("wikipedia"))])
    result = {
        "ok": bool(points or news), "question": question, "core_question": core, "user_lang": user_lang,
        "fresh": fresh, "news": news, "cached": False,
        "index_used": sum(1 for i in used_idx if sources[i].get("provider") == "index"),
        "queries": queries, "languages_searched": sorted({s.get("lang") for s in sources if s.get("lang")}),
        "points": points, "sources": cited, "sources_considered": len(sources),
        "candidates_evaluated": len(candidates), "providers": providers,
        "translators": translators_used, "elapsed_seconds": round(time.monotonic() - t0, 2),
        "error": None if (points or news) else "لم يُعثر على جمل ذات صلة كافية في المصادر المتاحة",
        "method": ("بحث متعدد المزودات واللغات (Bing وأخبار Bing/Google وويكيبيديا وويكي بيانات والأبحاث "
                   "المحكّمة والفهرس الذاتي) ← قراءة المصادر ← تقييم حتمي ("
                   + ("صلة ٤٠٪ + موثوقية ٢٥٪ + توافق ١٥٪ + حداثة ٢٠٪ — سؤال آني"
                      if fresh else "صلة BM25 وتغطية المفاهيم ٤٥٪ + موثوقية المصدر ٣٥٪ + توافق المصادر المستقلة ٢٠٪")
                   + ") ← ترجمة آلية — بلا نموذج لغوي"),
    }
    if use_cache and result["ok"]:
        search_index.cache_put_async(ckey, result, _env_int("WORLD_SEARCH_FRESH_TTL_SECONDS", 900) if fresh
                                     else _env_int("WORLD_SEARCH_CACHE_TTL_SECONDS", 259200))
    return result


def _date_ar(iso: Optional[str]) -> str:
    """تاريخ مختصر للعرض: «منذ ٣ ساعات» للحديث جدًا وإلا YYYY-MM-DD."""
    d = age_days(iso)
    if d is None:
        return ""
    def _n(k, one, two, few, many):
        return one if k == 1 else two if k == 2 else f"{k} {few}" if 3 <= k <= 10 else f"{k} {many}"
    if d < 1:
        h = int(d * 24)
        return "منذ أقل من ساعة" if h < 1 else "منذ " + _n(h, "ساعة", "ساعتين", "ساعات", "ساعة")
    if d < 7:
        return "منذ " + _n(int(d), "يوم", "يومين", "أيام", "يومًا")
    return str(iso)[:10]


def format_reply(res: Dict[str, Any]) -> str:
    """تنسيق عربي للجواب — كل جملة مقتبسة برقم مصدرها، والأخبار مؤرخة."""
    if not res.get("ok"):
        prov = "؛ ".join(f"{k}: {v}" for k, v in (res.get("providers") or {}).items())
        return ("بحثت في مصادر العالم بلا نموذج لغوي لكن لم أجد إجابة موثوقة كافية: "
                f"{res.get('error') or 'فشل'}." + (f"\nحالة المزودات: {prov}" if prov else ""))
    pts = res.get("points") or []
    news = res.get("news") or []
    head = (f"إجابة مجمّعة من {len(res['sources'])} مصدر (من {res.get('sources_considered', 0)} مصدرًا "
            f"و{res.get('candidates_evaluated', 0)} جملة قُيّمت، لغات البحث: "
            + "، ".join(LANG_NAMES_AR.get(x, x) for x in res.get("languages_searched") or []) + ")")
    if res.get("cached"):
        head += f" — من ذاكرة المحرك (عمرها {int(res.get('cache_age_seconds') or 0) // 60} دقيقة)"
    lines = [head + ":", ""]

    def _d(p):
        dd = _date_ar(p.get("published"))
        return f" ({dd})" if dd and res.get("fresh") else ""
    if pts:
        lines.append(f"الخلاصة الأقوى: {pts[0]['text']} [{pts[0]['source']}]{_d(pts[0])}")
        if len(pts) > 1:
            lines += ["", "نقاط داعمة:"]
            lines += [f"• {p['text']} [{p['source']}]{_d(p)}" for p in pts[1:]]
    if news:
        if pts:
            lines.append("")
        lines.append("أحدث العناوين المطابقة:")
        for n in news:
            meta = " — ".join(x for x in (n.get("site") or "", _date_ar(n.get("published"))) if x)
            lines.append(f"• {n['title']} [{n['source']}]" + (f" ({meta})" if meta else ""))
    lines += ["", "المصادر (مرتبة بالاستشهاد):"]
    for s in res["sources"]:
        dd = _date_ar(s.get("published"))
        lines.append(f"[{s['n']}] {s['title'] or s['url']} — {s['credibility_label']}"
                     + (f" — {dd}" if dd else "") + f" — {s['url']}")
    allp = pts + news
    machine = any(p.get("translator") not in (None, "identity") for p in allp)
    untrans = any(p.get("translator") is None and p.get("lang", "") != res.get("user_lang") for p in pts)
    lines += ["", "المنهج: " + res["method"] + "."]
    if res.get("fresh"):
        lines.append("تنبيه: سؤال آني — القيم تتغير باستمرار؛ التاريخ بجانب كل معلومة هو تاريخ نشر مصدرها.")
    if machine:
        lines.append("تنبيه: الترجمة آلية — راجع النص الأصلي في المصدر عند الحاجة.")
    if untrans:
        lines.append("تنبيه: تعذرت ترجمة بعض الجمل فبقيت بلغتها الأصلية.")
    lines.append("هذه معلومات عامة من المصادر وليست استشارة طبية أو مهنية شخصية."
                 if any(s.get("provider") in ("europepmc", "pubmed", "openalex") for s in res["sources"]) else "")
    return "\n".join(x for x in lines if x is not None).rstrip()
