"""R-838: المعجم المفاهيمي عبر اللغات — وحدات معنى مستقلة عن اللغة.

المبدأ: المعنى يُمثَّل بمفاتيح مفاهيم (concept keys) مستقلة عن اللغة،
والأسطح اللغوية مجرد أسماء لها. هذا ما يجعل:
- الاسترجاع عبر اللغات ممكنًا (سؤال إنجليزي يجد حقيقة قيلت بالعربية).
- ربط الكيانات عبر اللغات ممكنًا (Japan = اليابان = نفس الكيان).
- الفهم من النص الأصلي بلا ترجمة وسيطة (المطابقة على المفاتيح لا على النص).

المعجم حتمي ومحلي (بلا خدمات خارجية) وقابل للتوسع. المفاتيح صغيرة بحجم
مقروء: COUNTRY:JAPAN، PROP:CAPITAL، ...
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from . import scripts as _sc

# ---------------------------------------------------------------------------
# كيانات مسماة شائعة (نوع + أسطح متعددة اللغات)
# ---------------------------------------------------------------------------
_ENTITIES: Dict[str, Dict[str, list]] = {
    "COUNTRY:JAPAN": {"ar": ["اليابان", "يابان"], "en": ["japan"], "type": "country"},
    "COUNTRY:FRANCE": {"ar": ["فرنسا"], "en": ["france"], "fr": ["france"], "type": "country"},
    "COUNTRY:GERMANY": {"ar": ["ألمانيا", "المانيا"], "en": ["germany"], "de": ["deutschland"], "type": "country"},
    "COUNTRY:SAUDI": {"ar": ["السعودية", "السعودية العربية", "المملكة"], "en": ["saudi arabia", "ksa"], "type": "country"},
    "COUNTRY:EGYPT": {"ar": ["مصر"], "en": ["egypt"], "type": "country"},
    "COUNTRY:UAE": {"ar": ["الإمارات", "الامارات"], "en": ["uae", "united arab emirates"], "type": "country"},
    "COUNTRY:USA": {"ar": ["أمريكا", "امريكا", "الولايات المتحدة"], "en": ["usa", "united states", "america"], "type": "country"},
    "COUNTRY:UK": {"ar": ["بريطانيا", "انجلترا", "إنجلترا"], "en": ["uk", "britain", "england"], "type": "country"},
    "COUNTRY:CHINA": {"ar": ["الصين"], "en": ["china"], "zh": ["中国"], "type": "country"},
    "COUNTRY:INDIA": {"ar": ["الهند"], "en": ["india"], "hi": ["भारत"], "type": "country"},
    "COUNTRY:RUSSIA": {"ar": ["روسيا"], "en": ["russia"], "ru": ["россия"], "type": "country"},
    "COUNTRY:TURKEY": {"ar": ["تركيا"], "en": ["turkey"], "tr": ["türkiye"], "type": "country"},
    "COUNTRY:SPAIN": {"ar": ["إسبانيا", "اسبانيا"], "en": ["spain"], "es": ["españa"], "type": "country"},
    "COUNTRY:BRAZIL": {"ar": ["البرازيل"], "en": ["brazil"], "pt": ["brasil"], "type": "country"},
    "COUNTRY:CANADA": {"ar": ["كندا"], "en": ["canada"], "type": "country"},
    "COUNTRY:ITALY": {"ar": ["إيطاليا", "ايطاليا"], "en": ["italy"], "it": ["italia"], "type": "country"},
    "COUNTRY:MOROCCO": {"ar": ["المغرب"], "en": ["morocco"], "fr": ["maroc"], "type": "country"},
    "COUNTRY:QATAR": {"ar": ["قطر"], "en": ["qatar"], "type": "country"},
    "COUNTRY:KUWAIT": {"ar": ["الكويت"], "en": ["kuwait"], "type": "country"},
    "COUNTRY:JORDAN": {"ar": ["الأردن", "الاردن"], "en": ["jordan"], "type": "country"},
    "COUNTRY:LEBANON": {"ar": ["لبنان"], "en": ["lebanon"], "type": "country"},
    "COUNTRY:SYRIA": {"ar": ["سوريا", "سورية"], "en": ["syria"], "type": "country"},
    "COUNTRY:IRAQ": {"ar": ["العراق"], "en": ["iraq"], "type": "country"},
    "COUNTRY:YEMEN": {"ar": ["اليمن"], "en": ["yemen"], "type": "country"},
    "COUNTRY:OMAN": {"ar": ["عمان"], "en": ["oman"], "type": "country"},
    "COUNTRY:BAHRAIN": {"ar": ["البحرين"], "en": ["bahrain"], "type": "country"},
    "COUNTRY:PALESTINE": {"ar": ["فلسطين"], "en": ["palestine"], "type": "country"},
    "COUNTRY:SWEDEN": {"ar": ["السويد"], "en": ["sweden"], "type": "country"},
    "COUNTRY:NORWAY": {"ar": ["النرويج"], "en": ["norway"], "type": "country"},
    "COUNTRY:NETHERLANDS": {"ar": ["هولندا"], "en": ["netherlands", "holland"], "type": "country"},
    "COUNTRY:SWITZERLAND": {"ar": ["سويسرا"], "en": ["switzerland"], "type": "country"},
    "COUNTRY:AUSTRALIA": {"ar": ["أستراليا", "استراليا"], "en": ["australia"], "type": "country"},
    "COUNTRY:KOREA": {"ar": ["كوريا"], "en": ["korea", "south korea"], "type": "country"},
    "COUNTRY:IRAN": {"ar": ["إيران", "ايران"], "en": ["iran"], "fa": ["ایران"], "type": "country"},
    "COUNTRY:PAKISTAN": {"ar": ["باكستان"], "en": ["pakistan"], "ur": ["پاکستان"], "type": "country"},
    "COUNTRY:MALAYSIA": {"ar": ["ماليزيا"], "en": ["malaysia"], "type": "country"},
    "COUNTRY:INDONESIA": {"ar": ["إندونيسيا", "اندونيسيا"], "en": ["indonesia"], "id": ["indonesia"], "type": "country"},
    "COUNTRY:JAPAN_CITY_TOKYO": {"ar": ["طوكيو"], "en": ["tokyo"], "type": "city"},
    "CITY:PARIS": {"ar": ["باريس"], "en": ["paris"], "type": "city"},
    "CITY:LONDON": {"ar": ["لندن"], "en": ["london"], "type": "city"},
    "CITY:NEWYORK": {"ar": ["نيويورك"], "en": ["new york", "nyc"], "type": "city"},
    "CITY:RIYADH": {"ar": ["الرياض"], "en": ["riyadh"], "type": "city"},
    "CITY:JEDDAH": {"ar": ["جدة"], "en": ["jeddah"], "type": "city"},
    "CITY:MECCA": {"ar": ["مكة", "مكه"], "en": ["mecca", "makkah"], "type": "city"},
    "CITY:CAIRO": {"ar": ["القاهرة"], "en": ["cairo"], "type": "city"},
    "CITY:DUBAI": {"ar": ["دبي"], "en": ["dubai"], "type": "city"},
    "CITY:BERLIN": {"ar": ["برلين"], "en": ["berlin"], "type": "city"},
    "CITY:MADRID": {"ar": ["مدريد"], "en": ["madrid"], "type": "city"},
    "CITY:ROME": {"ar": ["روما"], "en": ["rome"], "type": "city"},
    "CITY:ISTANBUL": {"ar": ["إسطنبول", "استانبول", "استنبول"], "en": ["istanbul"], "tr": ["istanbul"], "type": "city"},
    "CITY:AMMAN": {"ar": ["عمان الأردن"], "en": ["amman"], "type": "city"},
    "ORG:GOOGLE": {"ar": ["جوجل", "غوغل"], "en": ["google"], "type": "org"},
    "ORG:MICROSOFT": {"ar": ["مايكروسوفت", "ميكروسوفت"], "en": ["microsoft"], "type": "org"},
    "ORG:APPLE": {"ar": ["آبل", "ابل", "أبل"], "en": ["apple"], "type": "org"},
    "ORG:AMAZON": {"ar": ["أمازون", "امازون"], "en": ["amazon"], "type": "org"},
    "ORG:TESLA": {"ar": ["تسلا"], "en": ["tesla"], "type": "org"},
    "ORG:GITHUB": {"ar": ["جيثب", "غيثب"], "en": ["github"], "type": "org"},
    "ORG:OPENAI": {"ar": ["أوبن إيه آي", "اوپن أي آي"], "en": ["openai"], "type": "org"},
    "ORG:PERPLEXITY": {"ar": ["بيربليكسيتي"], "en": ["perplexity"], "type": "org"},
    "ORG:NETFLIX": {"ar": ["نتفلكس", "نتفليكس"], "en": ["netflix"], "type": "org"},
    "ORG:SONY": {"ar": ["سوني"], "en": ["sony"], "type": "org"},
    "ORG:TOYOTA": {"ar": ["تويوتا"], "en": ["toyota"], "type": "org"},
    "ORG:SUPABASE": {"ar": ["سوابيس"], "en": ["supabase"], "type": "org"},
    "ORG:RENDER": {"ar": ["رندر"], "en": ["render"], "type": "org"},
    "PRODUCT:PYTHON": {"ar": ["بايثون"], "en": ["python"], "type": "product"},
    "PRODUCT:DOCKER": {"ar": ["دوكر"], "en": ["docker"], "type": "product"},
    "PRODUCT:WINDOWS": {"ar": ["ويندوز"], "en": ["windows"], "type": "product"},
    "PRODUCT:ANDROID": {"ar": ["أندرويد", "اندرويد"], "en": ["android"], "type": "product"},
    "PRODUCT:IPHONE": {"ar": ["آيفون", "ايفون"], "en": ["iphone"], "type": "product"},
    "PRODUCT:CHATGPT": {"ar": ["شات جي بي تي", "شاتجيبيتي"], "en": ["chatgpt"], "type": "product"},
}

# ---------------------------------------------------------------------------
# خصائص/مفاهيم عامة (للاسترجاع عبر اللغات وتوسيع الاستعلام بالمفاهيم)
# ---------------------------------------------------------------------------
_CONCEPTS: Dict[str, Dict[str, list]] = {
    "PROP:CAPITAL": {"ar": ["العاصمة", "عاصمة", "عاصمتها"], "en": ["capital"], "fr": ["capitale"]},
    "PROP:POPULATION": {"ar": ["السكان", "سكان", "عدد السكان", "سكانه", "سكانها"], "en": ["population", "people", "inhabitants"]},
    "PROP:AREA": {"ar": ["المساحة", "مساحة", "مساحتها"], "en": ["area", "size"]},
    "PROP:LANGUAGE": {"ar": ["اللغة", "لغة", "لغتها", "اللغات"], "en": ["language", "languages"]},
    "PROP:CURRENCY": {"ar": ["العملة", "عملة", "عملتها"], "en": ["currency"]},
    "PROP:PRESIDENT": {"ar": ["الرئيس", "رئيس", "رئيسها"], "en": ["president", "leader"]},
    "PROP:FOUNDER": {"ar": ["المؤسس", "مؤسس", "مؤسسها"], "en": ["founder", "founded by"]},
    "PROP:PRICE": {"ar": ["السعر", "سعر", "سعره", "أسعار"], "en": ["price", "cost", "pricing"]},
    "PROP:HISTORY": {"ar": ["التاريخ", "تاريخ", "تاريخها"], "en": ["history"]},
    "PROP:ECONOMY": {"ar": ["الاقتصاد", "اقتصاد", "اقتصادها"], "en": ["economy"]},
    "PROP:WEATHER": {"ar": ["الطقس", "طقس", "المناخ"], "en": ["weather", "climate"]},
    "PROP:CITIES": {"ar": ["المدن", "مدن"], "en": ["cities"]},
    "PROP:FOOD": {"ar": ["الطعام", "طعام", "الأكل", "المطبخ"], "en": ["food", "cuisine"]},
    "PROP:RELEASE_DATE": {"ar": ["تاريخ الإصدار", "الإصدار", "أصدرت"], "en": ["release date", "released"]},
    "PROP:VERSION": {"ar": ["الإصدار", "إصدار", "نسخة"], "en": ["version", "release"]},
    "PROP:FEATURES": {"ar": ["الميزات", "ميزات", "المميزات", "خصائص"], "en": ["features", "characteristics"]},
    "PROP:BENEFITS": {"ar": ["الفوائد", "فوائد", "المنافع"], "en": ["benefits", "advantages"]},
    "PROP:RISKS": {"ar": ["المخاطر", "مخاطر", "الأضرار"], "en": ["risks", "dangers", "disadvantages"]},
    "PROP:DEPLOY": {"ar": ["النشر", "نشر", "انشر", "نشرها"], "en": ["deploy", "deployment", "release"]},
    "PROP:ERROR": {"ar": ["الخطأ", "خطأ", "الأخطاء", "مشكلة", "عطل"], "en": ["error", "bug", "issue", "problem"]},
    "PROP:CONFIG": {"ar": ["الإعدادات", "إعدادات", "التهيئة", "ضبط"], "en": ["configuration", "config", "settings"]},
    "PROP:TEST": {"ar": ["الاختبار", "اختبار", "اختبارات", "تجربة"], "en": ["test", "testing", "tests"]},
    "PROP:MEMORY": {"ar": ["الذاكرة", "ذاكرة", "التخزين"], "en": ["memory", "storage"]},
    "PROP:PERFORMANCE": {"ar": ["الأداء", "أداء", "السرعة"], "en": ["performance", "speed", "latency"]},
    "PROP:SECURITY": {"ar": ["الأمان", "أمان", "الخصوصية", "الحماية"], "en": ["security", "privacy", "safety"]},
    "ACT:TRANSLATE": {"ar": ["ترجم", "ترجمة", "ترجمه"], "en": ["translate", "translation"]},
    "ACT:SUMMARIZE": {"ar": ["لخص", "تلخيص", "ملخص", "لخصه"], "en": ["summarize", "summary"]},
    "ACT:EXPLAIN": {"ar": ["اشرح", "شرح", "وضح", "فسر"], "en": ["explain", "explanation"]},
    "ACT:CONTINUE": {"ar": ["أكمل", "تابع", "استمر", "واصل", "المزيد"], "en": ["continue", "go on", "more"]},
    "ACT:CREATE": {"ar": ["أنشئ", "أنشىء", "اصنع", "ابن", "ابني", "ولّد", "ولد"], "en": ["create", "build", "generate", "make"]},
    "ACT:FIX": {"ar": ["أصلح", "اصلح", "صحح", "عدل", "حل المشكلة"], "en": ["fix", "repair", "resolve"]},
    "ACT:SEARCH": {"ar": ["ابحث", "بحث", "ابحث لي"], "en": ["search", "find", "look up"]},
    "ACT:COMPARE": {"ar": ["قارن", "مقارنة", "الفرق بين"], "en": ["compare", "comparison", "difference"]},
    "ACT:REVIEW": {"ar": ["راجع", "مراجعة", "دقق"], "en": ["review", "check"]},
}

# فهرس سطحي: سطح مطبَّع => (مفتاح مفهوم، نوع)
_SURFACE_INDEX: Dict[str, Tuple[str, str]] = {}


def _build_index() -> None:
    for key, entry in _ENTITIES.items():
        for lang, surfaces in entry.items():
            if lang == "type":
                continue
            for s in surfaces:
                _SURFACE_INDEX[_sc.norm_for_match(s)] = (key, entry.get("type", "unknown"))
    for key, entry in _CONCEPTS.items():
        for lang, surfaces in entry.items():
            for s in surfaces:
                _SURFACE_INDEX.setdefault(_sc.norm_for_match(s), (key, "concept"))


_build_index()


def lookup_surface(surface: str) -> Optional[Tuple[str, str]]:
    """يبحث عن سطح لغوي في الفهرس — يعيد (مفتاح_مفهوم، نوع)."""
    if not surface:
        return None
    return _SURFACE_INDEX.get(_sc.norm_for_match(surface))


def lookup_token(root: str) -> Optional[Tuple[str, str]]:
    """مثل lookup_surface لكن على جذر عربي مجرد من السوابق/اللواحق الشائعة."""
    if not root:
        return None
    hit = _SURFACE_INDEX.get(_sc.norm_for_match(root))
    if hit:
        return hit
    # جرّب إزالة تاء التأنيث/الجمع للعربية (مطابقة مرنة على الخصائص)
    n = _sc.norm_for_match(root)
    for suffix in ("ات", "ون", "ين", "ان", "ها", "ه", "تها", "ته", "تها"):
        if n.endswith(suffix) and len(n) - len(suffix) >= 3:
            hit = _SURFACE_INDEX.get(n[: -len(suffix)])
            if hit:
                return hit
    return None


def surfaces_for(key: str, lang: str) -> List[str]:
    """كل الأسطح المعروفة لمفتاح مفهوم بلغة معينة (توسيع الاستعلام)."""
    src = _ENTITIES.get(key) or _CONCEPTS.get(key)
    if not src:
        return []
    return list(src.get(lang, []))


def all_langs_for(key: str) -> Dict[str, List[str]]:
    """الأسطح بكل اللغات — لربط الكيانات عبر اللغات."""
    src = _ENTITIES.get(key) or _CONCEPTS.get(key)
    if not src:
        return {}
    return {k: list(v) for k, v in src.items() if k != "type"}


def related_concepts(key: str) -> List[str]:
    """مفاهيم مرتبطة تقريبية (للتوسيع المفاهيمي للاستعلام)."""
    prefix = key.split(":")[0]
    if prefix == "PROP" and key == "PROP:CAPITAL":
        return ["COUNTRY:*"]
    return []
