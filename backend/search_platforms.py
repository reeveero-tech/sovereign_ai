"""R-826 — فهم المطلوب + الإجابات المباشرة الدقيقة + منصات العالم لمحرك البحث.

أمر المالك: «أريد أن يكون بإمكانه البحث في كل منصات العالم ومواقع العالم بكل لغات العالم وأن يميز
المطلوب منه وأن ينقح إجاباته وأن يكون دقيقًا وشاملًا».

ثلاث طبقات يستدعيها world_search.answer:
1) analyze(): يميز المطلوب — نوع الإجابة (رقم/تاريخ/شخص/مكان/تعريف/طريقة/مقارنة)، النوايا
   (آني، تقني، علمي، فيديو، كتب، كود، نقاشات، قرآن، عملة، معدن، عملة رقمية، طقس، وقت)، والدول المذكورة
   ⇒ لغاتها تُضاف للبحث، ومصطلحاتها قيد مكاني يُنقَّح به (خبر مصري لا يجيب عن سعر الذهب في السعودية).
2) instant_answers(): إجابات مباشرة من مصادر بيانات دقيقة (فُحصت حيًا من Render): أسعار الصرف
   (open.er-api)، الذهب والفضة والبلاتين وبيتكوين/إيثريوم (gold-api) وبقية العملات الرقمية (Coinbase)،
   الطقس (wttr.in)، الوقت المحلي (zoneinfo محليًا بلا شبكة).
3) منصات: YouTube، GitHub، Baidu (الصينية)، arXiv، Crossref، Semantic Scholar، Open Library، Lemmy،
   مواقع Stack Exchange حسب الموضوع (طبخ/سفر/لياقة/مال/إسلام/تاريخ/…)، القرآن الكريم (alquran.cloud).

كل مزود يُعلن نجاحه أو فشله في حالة المزودات — لا شيء صامت ولا قيمة مخترعة.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

# ============================================================
# ١) الدول: الاسم بالعربية/الإنجليزية ⇒ اللغة، العملة، المنطقة الزمنية
# ============================================================
# (رمز، لغة، عملة، منطقة زمنية، أسماء عربية، أسماء إنجليزية)
COUNTRIES: Tuple[Tuple[str, str, str, str, Tuple[str, ...], Tuple[str, ...]], ...] = (
    ("SA", "ar", "SAR", "Asia/Riyadh", ("السعودية", "المملكة العربية السعودية", "الرياض", "جدة", "مكة", "المدينة المنورة", "الدمام"),
     ("saudi", "saudi arabia", "riyadh", "jeddah", "mecca", "makkah", "medina", "dammam")),
    ("AE", "ar", "AED", "Asia/Dubai", ("الإمارات", "الامارات", "دبي", "أبوظبي", "ابوظبي", "الشارقة"), ("uae", "emirates", "dubai", "abu dhabi", "sharjah")),
    ("EG", "ar", "EGP", "Africa/Cairo", ("مصر", "القاهرة", "الإسكندرية", "الاسكندرية"), ("egypt", "cairo", "alexandria")),
    ("KW", "ar", "KWD", "Asia/Kuwait", ("الكويت",), ("kuwait",)),
    ("QA", "ar", "QAR", "Asia/Qatar", ("قطر", "الدوحة"), ("qatar", "doha")),
    ("BH", "ar", "BHD", "Asia/Bahrain", ("البحرين", "المنامة"), ("bahrain", "manama")),
    ("OM", "ar", "OMR", "Asia/Muscat", ("عمان", "عُمان", "مسقط"), ("oman", "muscat")),
    ("JO", "ar", "JOD", "Asia/Amman", ("الأردن", "الاردن"), ("jordan", "amman")),
    ("IQ", "ar", "IQD", "Asia/Baghdad", ("العراق", "بغداد"), ("iraq", "baghdad")),
    ("MA", "ar", "MAD", "Africa/Casablanca", ("المغرب", "الرباط", "الدار البيضاء"), ("morocco", "rabat", "casablanca")),
    ("DZ", "ar", "DZD", "Africa/Algiers", ("الجزائر",), ("algeria", "algiers")),
    ("TN", "ar", "TND", "Africa/Tunis", ("تونس",), ("tunisia", "tunis")),
    ("YE", "ar", "YER", "Asia/Aden", ("اليمن", "صنعاء", "عدن"), ("yemen", "sanaa", "aden")),
    ("LB", "ar", "LBP", "Asia/Beirut", ("لبنان", "بيروت"), ("lebanon", "beirut")),
    ("SY", "ar", "SYP", "Asia/Damascus", ("سوريا", "سورية", "دمشق"), ("syria", "damascus")),
    ("SD", "ar", "SDG", "Africa/Khartoum", ("السودان", "الخرطوم"), ("sudan", "khartoum")),
    ("LY", "ar", "LYD", "Africa/Tripoli", ("ليبيا", "طرابلس"), ("libya", "tripoli")),
    ("PS", "ar", "ILS", "Asia/Gaza", ("فلسطين", "غزة", "القدس"), ("palestine", "gaza", "jerusalem")),
    ("US", "en", "USD", "America/New_York", ("أمريكا", "امريكا", "الولايات المتحدة", "نيويورك", "واشنطن"), ("united states", "usa", "america", "new york", "washington")),
    ("GB", "en", "GBP", "Europe/London", ("بريطانيا", "المملكة المتحدة", "لندن", "إنجلترا", "انجلترا"), ("united kingdom", "uk", "britain", "england", "london")),
    ("CA", "en", "CAD", "America/Toronto", ("كندا", "تورنتو"), ("canada", "toronto")),
    ("AU", "en", "AUD", "Australia/Sydney", ("أستراليا", "استراليا", "سيدني"), ("australia", "sydney")),
    ("FR", "fr", "EUR", "Europe/Paris", ("فرنسا", "باريس"), ("france", "paris", "en france")),
    ("DE", "de", "EUR", "Europe/Berlin", ("ألمانيا", "المانيا", "برلين"), ("germany", "berlin")),
    ("ES", "es", "EUR", "Europe/Madrid", ("إسبانيا", "اسبانيا", "مدريد"), ("spain", "madrid")),
    ("IT", "it", "EUR", "Europe/Rome", ("إيطاليا", "ايطاليا", "روما"), ("italy", "rome")),
    ("PT", "pt", "EUR", "Europe/Lisbon", ("البرتغال", "لشبونة"), ("portugal", "lisbon")),
    ("NL", "nl", "EUR", "Europe/Amsterdam", ("هولندا", "أمستردام"), ("netherlands", "amsterdam")),
    ("BR", "pt", "BRL", "America/Sao_Paulo", ("البرازيل",), ("brazil", "sao paulo")),
    ("MX", "es", "MXN", "America/Mexico_City", ("المكسيك",), ("mexico",)),
    ("RU", "ru", "RUB", "Europe/Moscow", ("روسيا", "موسكو"), ("russia", "moscow")),
    ("UA", "uk", "UAH", "Europe/Kyiv", ("أوكرانيا", "اوكرانيا", "كييف"), ("ukraine", "kyiv", "kiev")),
    ("TR", "tr", "TRY", "Europe/Istanbul", ("تركيا", "إسطنبول", "اسطنبول", "أنقرة"), ("turkey", "turkiye", "istanbul", "ankara")),
    ("IR", "fa", "IRR", "Asia/Tehran", ("إيران", "ايران", "طهران"), ("iran", "tehran")),
    ("PK", "ur", "PKR", "Asia/Karachi", ("باكستان", "كراتشي", "إسلام آباد"), ("pakistan", "karachi", "islamabad")),
    ("IN", "hi", "INR", "Asia/Kolkata", ("الهند", "نيودلهي", "مومباي"), ("india", "new delhi", "delhi", "mumbai")),
    ("CN", "zh", "CNY", "Asia/Shanghai", ("الصين", "بكين", "شنغهاي"), ("china", "beijing", "shanghai")),
    ("JP", "ja", "JPY", "Asia/Tokyo", ("اليابان", "طوكيو", "أوساكا"), ("japan", "tokyo", "osaka")),
    ("KR", "ko", "KRW", "Asia/Seoul", ("كوريا الجنوبية", "كوريا", "سيول"), ("south korea", "korea", "seoul")),
    ("ID", "id", "IDR", "Asia/Jakarta", ("إندونيسيا", "اندونيسيا", "جاكرتا"), ("indonesia", "jakarta")),
    ("MY", "ms", "MYR", "Asia/Kuala_Lumpur", ("ماليزيا", "كوالالمبور"), ("malaysia", "kuala lumpur")),
    ("TH", "th", "THB", "Asia/Bangkok", ("تايلاند", "بانكوك"), ("thailand", "bangkok")),
    ("GR", "el", "EUR", "Europe/Athens", ("اليونان", "أثينا"), ("greece", "athens")),
    ("IL", "he", "ILS", "Asia/Jerusalem", ("إسرائيل", "اسرائيل", "تل أبيب"), ("israel", "tel aviv")),
    ("NG", "en", "NGN", "Africa/Lagos", ("نيجيريا",), ("nigeria", "lagos")),
    ("KE", "sw", "KES", "Africa/Nairobi", ("كينيا", "نيروبي"), ("kenya", "nairobi")),
    ("ET", "am", "ETB", "Africa/Addis_Ababa", ("إثيوبيا", "اثيوبيا", "أديس أبابا"), ("ethiopia", "addis ababa")),
    ("BD", "bn", "BDT", "Asia/Dhaka", ("بنغلاديش", "دكا"), ("bangladesh", "dhaka")),
    ("CH", "de", "CHF", "Europe/Zurich", ("سويسرا", "زيورخ", "جنيف"), ("switzerland", "zurich", "geneva")),
    ("SE", "sv", "SEK", "Europe/Stockholm", ("السويد", "ستوكهولم"), ("sweden", "stockholm")),
    ("PL", "pl", "PLN", "Europe/Warsaw", ("بولندا", "وارسو"), ("poland", "warsaw")),
)
_BY_CODE = {c[0]: c for c in COUNTRIES}


def _name_rx(names: Tuple[str, ...], arabic: bool) -> re.Pattern:
    alts = "|".join(sorted((re.escape(n) for n in names), key=len, reverse=True))
    if arabic:  # يسمح بأدوات الجر الملتصقة (بالسعودية/والسعودية/للسعودية)
        return re.compile(rf"(?<![\w])(?:و|ب|ل|ف)?(?:{alts})(?![\w])")
    return re.compile(rf"\b(?:{alts})\b", re.I)


_COUNTRY_RX = [(c[0], _name_rx(c[4], True), _name_rx(c[5], False)) for c in COUNTRIES]


def detect_regions(*texts: str) -> List[str]:
    """رموز الدول المذكورة (بترتيب أول ظهور) في النص العربي أو الإنجليزي."""
    found: List[Tuple[int, str]] = []
    for code, rx_ar, rx_en in _COUNTRY_RX:
        best = None
        for t in texts:
            for rx in (rx_ar, rx_en):
                m = rx.search(str(t or ""))
                if m and (best is None or m.start() < best):
                    best = m.start()
        if best is not None:
            found.append((best, code))
    # «عمان» العاصمة الأردنية تُكتب عمّان — إن ذُكر الأردن فلا تُحسب عُمان
    codes = [c for _, c in sorted(found)]
    if "JO" in codes and "OM" in codes:
        codes.remove("OM")
    return codes


def region_terms(codes: List[str]) -> List[str]:
    out: List[str] = []
    for c in codes:
        row = _BY_CODE.get(c)
        if row:
            out += list(row[4]) + list(row[5])
    return out


def mentions_other_region(text: str, codes: List[str]) -> bool:
    """تنقيح مكاني: النص يذكر دولة أخرى ولا يذكر أيًا من الدول المطلوبة ⇒ خارج المطلوب."""
    if not codes:
        return False
    here = detect_regions(text)
    return bool(here) and not (set(here) & set(codes))


def mentions_other_currency(text: str, codes: List[str]) -> bool:
    """سؤال عن صرف عملات بعينها ⇒ نص عن عملة محلية أخرى (الجنيه/الريال اليمني) خارج المطلوب.

    الدولار واليورو مرجعيتان عالميتان فلا يُستبعد بهما.
    """
    if not codes:
        return False
    here = set(detect_currencies(text)) - {"USD", "EUR"}
    return bool(here - set(codes))


# ============================================================
# ٢) العملات والمعادن والعملات الرقمية
# ============================================================
# (رمز، الاسم العربي للعرض، أنماط عربية، أنماط إنجليزية)
CURRENCIES: Tuple[Tuple[str, str, str, str], ...] = (
    ("SAR", "ريال سعودي", r"ريال(?:ات)?(?:\s+سعودي)?(?!\s+(?:قطري|عماني|يمني|إيراني|ايراني|برازيلي))", r"saudi riyals?|\bsar\b|riyals?(?! (?:qatari|omani|yemeni|iranian))"),
    ("QAR", "ريال قطري", r"ريال(?:ات)?\s+قطري", r"qatari riyals?|\bqar\b"),
    ("OMR", "ريال عماني", r"ريال(?:ات)?\s+عماني", r"omani rials?|\bomr\b"),
    ("YER", "ريال يمني", r"ريال(?:ات)?\s+يمني", r"yemeni rials?|\byer\b"),
    ("IRR", "ريال إيراني", r"(?:ريال|تومان)\s*(?:إيراني|ايراني)?(?=.*(?:إيران|ايران))|تومان", r"iranian rials?|\birr\b|toman"),
    ("USD", "دولار أمريكي", r"دولار(?:ات)?(?:\s+(?:أمريكي|امريكي|أميركي))?(?!\s+(?:كندي|أسترالي|استرالي|سنغافوري|هونغ))", r"(?:us |american )?dollars?(?! (?:canadian|australian))|\busd\b|\$"),
    ("CAD", "دولار كندي", r"دولار(?:ات)?\s+كندي", r"canadian dollars?|\bcad\b"),
    ("AUD", "دولار أسترالي", r"دولار(?:ات)?\s+(?:أسترالي|استرالي)", r"australian dollars?|\baud\b"),
    ("EUR", "يورو", r"يورو", r"euros?|\beur\b|€"),
    ("GBP", "جنيه إسترليني", r"جنيه(?:ات)?\s+(?:إسترليني|استرليني)|إسترليني|استرليني", r"pounds? sterling|british pounds?|\bgbp\b|£"),
    ("EGP", "جنيه مصري", r"جنيه(?:ات)?(?:\s+مصري)?(?!\s+(?:إسترليني|استرليني|سوداني))", r"egyptian pounds?|\begp\b"),
    ("SDG", "جنيه سوداني", r"جنيه(?:ات)?\s+سوداني", r"sudanese pounds?|\bsdg\b"),
    ("AED", "درهم إماراتي", r"درهم(?:\s+إماراتي|\s+اماراتي)?(?!\s+مغربي)", r"(?:uae |emirati )?dirhams?(?! moroccan)|\baed\b"),
    ("MAD", "درهم مغربي", r"درهم\s+مغربي", r"moroccan dirhams?"),
    ("KWD", "دينار كويتي", r"دينار(?:\s+كويتي)?(?!\s+(?:أردني|اردني|بحريني|عراقي|ليبي|تونسي|جزائري))", r"kuwaiti dinars?|\bkwd\b"),
    ("JOD", "دينار أردني", r"دينار\s+(?:أردني|اردني)", r"jordanian dinars?|\bjod\b"),
    ("BHD", "دينار بحريني", r"دينار\s+بحريني", r"bahraini dinars?|\bbhd\b"),
    ("IQD", "دينار عراقي", r"دينار\s+عراقي", r"iraqi dinars?|\biqd\b"),
    ("LYD", "دينار ليبي", r"دينار\s+ليبي", r"libyan dinars?|\blyd\b"),
    ("TND", "دينار تونسي", r"دينار\s+تونسي", r"tunisian dinars?|\btnd\b"),
    ("DZD", "دينار جزائري", r"دينار\s+جزائري", r"algerian dinars?|\bdzd\b"),
    ("TRY", "ليرة تركية", r"ليرة(?:\s+تركية)?(?!\s+(?:لبنانية|سورية))", r"turkish liras?|lira(?! (?:lebanese|syrian))"),
    ("LBP", "ليرة لبنانية", r"ليرة\s+لبنانية", r"lebanese pounds?|\blbp\b"),
    ("SYP", "ليرة سورية", r"ليرة\s+سورية", r"syrian pounds?|\bsyp\b"),
    ("JPY", "ين ياباني", r"(?<![\w])ين(?:\s+ياباني)?(?![\w])", r"\byen\b|\bjpy\b"),
    ("CNY", "يوان صيني", r"يوان", r"\byuan\b|renminbi|\bcny\b|\brmb\b"),
    ("INR", "روبية هندية", r"روبية(?:\s+هندية)?(?!\s+(?:باكستانية|إندونيسية))", r"indian rupees?|\binr\b|rupees?(?! pakistani)"),
    ("PKR", "روبية باكستانية", r"روبية\s+باكستانية", r"pakistani rupees?|\bpkr\b"),
    ("RUB", "روبل روسي", r"روبل", r"rubles?|roubles?|\brub\b"),
    ("CHF", "فرنك سويسري", r"فرنك(?:\s+سويسري)?", r"swiss francs?|\bchf\b"),
    ("KRW", "وون كوري", r"(?<![\w])وون(?![\w])", r"korean won|\bkrw\b"),
    ("ILS", "شيكل", r"شيكل|شيقل", r"shekels?|\bils\b"),
)
_CUR_NAME = {c[0]: c[1] for c in CURRENCIES}
_CUR_EN = {"SAR": "Saudi riyal", "USD": "US dollar", "EUR": "euro", "GBP": "British pound", "EGP": "Egyptian pound",
           "AED": "UAE dirham", "KWD": "Kuwaiti dinar", "JPY": "Japanese yen", "CNY": "Chinese yuan", "TRY": "Turkish lira"}
# الصفة تأتي معرّفة أو نكرة: «ريال يمني» و«الريال اليمني» ⇒ (?:ال)? بعد كل فاصل في النمط العربي
_CUR_RX = [(c[0], re.compile(c[2].replace(r"\s+", r"\s+(?:ال)?")), re.compile(c[3], re.I)) for c in CURRENCIES]

METALS = {"XAU": ("الذهب", "gold", r"ذهب|الذهب|جرام ذهب|غرام ذهب", r"\bgold\b|l['’]or\b|\bde l['’]or\b|\boro\b|\bouro\b|altın|золот|黄金|金价|金価格|금값|\bemas\b|طلا|سونے"),
          "XAG": ("الفضة", "silver", r"فضة|الفضة", r"\bsilver\b|\bargent\b|\bplata\b|\bsilber\b|\bprata\b|gümüş|серебр|白银|銀価格|نقره"),
          "XPT": ("البلاتين", "platinum", r"بلاتين", r"\bplatinum\b")}
CRYPTO = {"BTC": ("بيتكوين", r"بيتكوين|بتكوين|بيتكوين", r"\bbitcoin\b|\bbtc\b"),
          "ETH": ("إيثريوم", r"إيثريوم|ايثريوم|إثيريوم|اثيريوم", r"\bethereum\b|\beth\b"),
          "SOL": ("سولانا", r"سولانا", r"\bsolana\b"),
          "XRP": ("ريبل", r"ريبل", r"\bripple\b|\bxrp\b"),
          "DOGE": ("دوجكوين", r"دوج", r"\bdogecoin\b|\bdoge\b"),
          "BNB": ("بينانس كوين", r"بينانس", r"\bbnb\b|binance coin"),
          "USDT": ("تيثر", r"تيثر", r"\btether\b|\busdt\b")}

_PRICE_WORD = re.compile(r"سعر|أسعار|اسعار|كم\s+(?:يساوي|سعر|قيمة)|قيمة|صرف|مقابل|تحويل|بكم|\bprices?\b|\brates?\b|"
                         r"\bprix\b|precio|\bpreis\b|preço|prezzo|fiyat|цена|价格|価格|가격|\bharga\b|قیمت|"
                         r"\bexchange\b|\bconvert\b|\bworth\b|\bhow much\b", re.I)
# عملة واحدة تُعد «سؤال صرف» فقط إن سُئل عنها هي: سعر الدولار/صرف/مقابل/تحويل — لا «سعر آيفون بالريال»
_FX_WORD = re.compile(r"صرف|مقابل|تحويل|\bexchange\b|\bconvert\b|\bagainst\b|(?:سعر|أسعار|اسعار|قيمة)\s+(?:ال)?"
                      r"(?:دولار|يورو|جنيه|درهم|دينار|ليرة|ين|يوان|روبية|روبل|ريال|فرنك|إسترليني|استرليني)|"
                      r"\b(?:dollar|euro|pound|dirham|dinar|lira|yen|yuan|rupee|ruble|riyal|franc)s?\s+(?:exchange\s+)?rate|"
                      r"\bprice of (?:the )?(?:dollar|euro|pound|dirham|dinar|lira|yen|yuan|rupee|ruble|riyal|franc)", re.I)


def detect_currencies(*texts: str) -> List[str]:
    found: List[Tuple[int, str]] = []
    for code, rx_ar, rx_en in _CUR_RX:
        best = None
        for t in texts:
            for rx in (rx_ar, rx_en):
                m = rx.search(str(t or ""))
                if m and (best is None or m.start() < best):
                    best = m.start()
        if best is not None:
            found.append((best, code))
    return list(dict.fromkeys(c for _, c in sorted(found)))


def _first(patterns: Dict[str, Tuple], text_ar: str, text_en: str, i_ar: int, i_en: int) -> Optional[str]:
    for sym, row in patterns.items():
        # النمط «الأجنبي» يُطبق على السؤال الأصلي أيضًا (سؤال فرنسي/تركي بلا ترجمة)
        if re.search(row[i_ar], text_ar) or re.search(row[i_en], f"{text_ar}\n{text_en}", re.I):
            return sym
    return None


# ============================================================
# ٣) فهم المطلوب
# ============================================================
_K = {
    "video": r"فيديو|مقطع|يوتيوب|شرح مرئي|\bvideos?\b|youtube|\bwatch\b|tutorial",
    "howto": r"كيف|كيفية|طريقة|خطوات|\bhow (?:to|do|can|should)\b|\bsteps?\b|\bguide\b",
    "definition": r"(?:ما هو|ما هي|ماهو|ماهي)(?!\s+(?:أفضل|افضل|أحسن|احسن|أكبر|اكبر|أسرع|عدد|سعر|درجة|عاصمة))|"
                  r"تعريف|معنى|ما المقصود|\bwhat (?:is|are)\b(?!\s+(?:the\s+)?(?:best|biggest|largest|fastest|"
                  r"number|price|temperature|weather|capital|population|time))|\bdefine\b|\bmeaning of\b",
    "numeric": r"(?<![\w])كم(?![\w])|عدد|نسبة|مساحة|طول|ارتفاع|\bhow (?:many|much|long|tall|far|big|old)\b|"
               r"\bnumber of\b|\bpercentage\b|\bpopulation\b|\barea\b",
    "date": r"متى|في أي (?:سنة|عام|تاريخ)|تاريخ (?:تأسيس|ميلاد|وفاة)|\bwhen\b|\bwhat year\b|\bwhat date\b",
    "person": r"من هو|من هي|من هم|مَن|\bwho (?:is|was|are|were|invented|founded|wrote|discovered)\b",
    "place": r"(?<![\w])(?:أين|وين)(?![\w])|\bwhere\b",
    "comparison": r"الفرق بين|مقارنة|أيهما|ايهما|أفضل من|افضل من|مقابل(?=.*(?:أفضل|افضل))|\bvs\.?\b|\bversus\b|"
                  r"\bdifference between\b|\bcompare\b|\bbetter than\b|\bwhich is better\b",
    "book": r"(?<![\w])(?:ال)?(?:كتاب|كتب|رواية|روايات|مؤلف|مؤلفات)(?![\w])|\bbooks?\b|\bnovels?\b|\bauthor\b",
    "code": r"كود|برمجة|برمجي|مكتبة برمجية|مستودع|مفتوح المصدر|\bgithub\b|\brepo(?:sitory)?\b|\bsource code\b|"
            r"\bopen[- ]source\b|\blibrary\b|\bframework\b|\bsdk\b|\bapi\b",
    "scholarly": r"دراسة|دراسات|بحث علمي|أبحاث|ابحاث|علمي|مرض|علاج|دواء|أعراض|اعراض|صحة|سرطان|سكري|ضغط الدم|"
                 r"\bstud(?:y|ies)\b|\bresearch\b|\bpapers?\b|\bevidence\b|\bclinical\b|\bdisease\b|\btreatment\b|"
                 r"\bsymptoms?\b|\bdrugs?\b|\bcancer\b|\bdiabetes\b|\bphysics\b|\bchemistry\b|\bbiology\b",
    "religion": r"آية|اية|سورة|القرآن|قرآن|القران|\bquran\b|\bkoran\b|\bverse\b|\bsurah\b",
    "discussion": r"آراء|اراء|تجارب|تجربة|رأيكم|رايكم|نصيحة|\breviews?\b|\bopinions?\b|\bexperiences?\b|\badvice\b",
    "weather": r"طقس|الطقس|درجة الحرارة|درجات الحرارة|حرارة الجو|أمطار|امطار|\bweather\b|\btemperature\b|\bforecast\b",
    "time": r"كم الساعة|الساعة الآن|الساعة كم|الوقت الآن في|التوقيت في|\bwhat time is it\b|\blocal time\b|\btime (?:now )?in\b",
}
_KRX = {k: re.compile(v, re.I) for k, v in _K.items()}

_SE_SITES = (  # موقع Stack Exchange حسب الموضوع
    ("cooking", r"طبخ|وصفة|طريقة عمل|مطبخ|\brecipes?\b|\bcook(?:ing)?\b|\bbak(?:e|ing)\b"),
    ("travel", r"سفر|تأشيرة|تاشيرة|فيزا|طيران|مطار|\btravel\b|\bvisas?\b|\bflights?\b|\bairport\b"),
    ("fitness", r"تمرين|تمارين|رياضة|عضل|نادي رياضي|لياقة|\bworkout\b|\bexercises?\b|\bfitness\b|\bgym\b|\bmuscle\b"),
    ("money", r"ادخار|استثمار|قرض|ضريبة|ميزانية|تقاعد|\bsavings?\b|\binvest(?:ing|ment)?\b|\bloans?\b|\btax(?:es)?\b|\bbudget\b"),
    ("islam", r"فقه|صلاة|صيام|زكاة|حج|عمرة|حلال|حرام|وضوء|\bislam\b|\bprayer\b|\bfasting\b|\bhalal\b|\bzakat\b"),
    ("history", r"تاريخ|التاريخ|حضارة|الدولة العثمانية|\bhistory\b|\bempire\b|\bancient\b"),
    ("medicalsciences", r"مرض|علاج|دواء|أعراض|اعراض|\bdisease\b|\btreatment\b|\bsymptoms?\b|\bmedication\b"),
    ("math", r"رياضيات|معادلة|تكامل|اشتقاق|\bmath(?:s|ematics)?\b|\bequation\b|\bintegral\b|\bderivative\b"),
    ("physics", r"فيزياء|\bphysics\b|\bquantum\b|\brelativity\b"),
    ("law", r"قانون|محكمة|عقد|\blaw\b|\blegal\b|\bcontract\b|\bcourt\b"),
    ("academia", r"جامعة|ماجستير|دكتوراه|ابتعاث|\buniversity\b|\bphd\b|\bmaster'?s\b|\bscholarship\b"),
    ("workplace", r"وظيفة|مقابلة عمل|مدير|راتب|\bjob\b|\binterview\b|\bcareer\b|\bsalary\b|\bboss\b"),
    ("superuser", r"ويندوز|حاسوب|كمبيوتر|لابتوب|\bwindows\b|\bcomputer\b|\blaptop\b|\bpc\b"),
    ("android", r"أندرويد|اندرويد|\bandroid\b"),
    ("apple", r"آيفون|ايفون|ماك|\biphone\b|\bmacbook\b|\bmacos\b|\bios\b"),
    ("gaming", r"لعبة|ألعاب|العاب|بلايستيشن|\bgames?\b|\bgaming\b|\bplaystation\b|\bxbox\b"),
    ("movies", r"فيلم|أفلام|افلام|مسلسل|\bmovies?\b|\bfilms?\b|\bseries\b"),
    ("diy", r"سباكة|كهرباء المنزل|صيانة المنزل|\bdiy\b|\bplumbing\b|\bwiring\b"),
    ("ell", r"قواعد الإنجليزية|اللغة الإنجليزية|\bgrammar\b|\benglish (?:word|phrase|sentence)\b"),
)
_SE_RX = [(site, re.compile(rx, re.I)) for site, rx in _SE_SITES]

_KIND_AR = {"fresh": "آني", "tech": "تقني", "video": "فيديو", "howto": "طريقة/خطوات", "definition": "تعريف",
            "numeric": "رقم/كمية", "date": "تاريخ/زمن", "person": "شخص", "place": "مكان", "comparison": "مقارنة",
            "book": "كتب", "code": "كود/مستودعات", "scholarly": "علمي/صحي", "religion": "قرآن/دين",
            "discussion": "آراء وتجارب", "weather": "طقس", "time": "الوقت المحلي", "currency": "سعر صرف",
            "metal": "سعر معدن", "crypto": "عملة رقمية"}
_TYPE_ORDER = ("comparison", "howto", "person", "date", "numeric", "place", "definition")
_DIRECT = {"weather", "time", "currency", "metal", "crypto"}


_LANG_CUR = {"ar": "SAR", "fr": "EUR", "de": "EUR", "es": "EUR", "it": "EUR", "pt": "EUR", "nl": "EUR", "el": "EUR",
             "tr": "TRY", "ru": "RUB", "uk": "UAH", "ja": "JPY", "zh": "CNY", "ko": "KRW", "hi": "INR", "ur": "PKR",
             "fa": "IRR", "id": "IDR", "ms": "MYR", "th": "THB", "bn": "BDT", "he": "ILS", "sv": "SEK", "pl": "PLN",
             "sw": "KES", "am": "ETB"}


def analyze(question: str, en_q: Optional[str], user_lang: str, fresh: bool = False, tech: bool = False) -> Dict[str, Any]:
    """يميز المطلوب: أنواع النية، نوع الإجابة، الدول ولغاتها، العملات/المعدن/العملة الرقمية، مواقع Q&A المناسبة."""
    q_ar = str(question or "")
    q_en = str(en_q or "")
    both = f"{q_ar} \n {q_en}"
    kinds = [k for k, rx in _KRX.items() if rx.search(both)]
    if fresh:
        kinds.insert(0, "fresh")
    if tech:
        kinds.append("tech")
    regions = detect_regions(q_ar, q_en)
    currencies = detect_currencies(q_ar, q_en)
    metal = _first(METALS, q_ar, q_en, 2, 3)
    crypto = _first(CRYPTO, q_ar, q_en, 1, 2)
    priced = bool(_PRICE_WORD.search(both)) or fresh
    if metal and priced:
        kinds.append("metal")
    if crypto and priced:
        kinds.append("crypto")
    # عملة: زوج صريح، أو عملة واحدة مع كلمة سعر/صرف (وليست مجرد عملة تسعير لمعدن)
    if (len(currencies) >= 2 or (currencies and _FX_WORD.search(both))) and not metal and not crypto:
        kinds.append("currency")
    if _DIRECT & set(kinds) and "definition" in kinds:
        kinds.remove("definition")  # «ما هو سعر…/ما هي درجة الحرارة» طلب قيمة لا تعريف
    answer_type = next((t for t in _TYPE_ORDER if t in kinds), "general")
    se_sites = [site for site, rx in _SE_RX if rx.search(both)][:2]
    langs = []
    for c in regions:
        lang = _BY_CODE[c][1]
        if lang not in langs:
            langs.append(lang)
    local_cur = None
    if regions:
        local_cur = _BY_CODE[regions[0]][2]
    else:  # بلا دولة مذكورة: عملة لغة السائل الغالبة
        local_cur = _LANG_CUR.get(user_lang)
    label = "، ".join(dict.fromkeys(_KIND_AR.get(k, k) for k in kinds)) or "سؤال عام"
    region_ar = "، ".join(_BY_CODE[c][4][0] for c in regions)
    return {"kinds": list(dict.fromkeys(kinds)), "answer_type": answer_type, "regions": regions,
            "region_langs": langs, "currencies": currencies, "metal": metal if "metal" in kinds else None,
            "crypto": crypto if "crypto" in kinds else None, "local_currency": local_cur,
            "se_sites": se_sites, "label_ar": label, "regions_ar": region_ar,
            "location_terms": region_terms(regions)}


# ---------- نوع الإجابة ⇒ مكافأة تقييم ----------
_MONTHS = (r"january|february|march|april|may|june|july|august|september|october|november|december|"
           r"يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر")
_TB = {
    "numeric": re.compile(r"\d"),
    "date": re.compile(rf"\b(?:1[0-9]|20)\d\d\b|{_MONTHS}|\d{{1,2}}/\d{{1,2}}/\d{{2,4}}", re.I),
    "definition": re.compile(r"\b(?:is an?|is the|are an?|refers to|is defined as|means)\b|(?:هو|هي)\s+(?:عبارة|أحد|احد|نوع|مصطلح)|يُعرَّف|يعرف بأنه|يشير إلى", re.I),
    "person": re.compile(r"\b(?:born|was an?|is an?|founded|invented|wrote|died)\b|وُلد|ولد|توفي|أسس|اخترع|كتب", re.I),
    "place": re.compile(r"\b(?:located|lies|situated|capital|north|south|east|west)\b|يقع|تقع|عاصمة|شمال|جنوب|شرق|غرب", re.I),
    "howto": re.compile(r"\b(?:first|then|step|use|make sure|you can|you should)\b|أولاً|اولا|ثم|خطوة|يمكنك|يجب|استخدم", re.I),
    "comparison": re.compile(r"\b(?:than|whereas|while|unlike|compared|both|difference)\b|بينما|مقارنة|أكثر من|أقل من|بخلاف|كلاهما|الفرق", re.I),
}


def type_bonus(text: str, answer_type: str) -> float:
    rx = _TB.get(answer_type)
    return 1.0 if rx and rx.search(str(text or "")) else 0.0


# ============================================================
# ٤) الإجابات المباشرة (مصادر بيانات دقيقة)
# ============================================================
def _http(timeout: float = 8.0, headers: Optional[Dict[str, str]] = None):
    import httpx
    return httpx.Client(timeout=timeout, follow_redirects=True, headers=headers or {})


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _fmt(x: float) -> str:
    if x >= 1000:
        return f"{x:,.2f}"
    if x >= 1:
        return f"{x:,.4f}".rstrip("0").rstrip(".")
    return f"{x:.6f}".rstrip("0").rstrip(".")


_RATES_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def rates(base: str) -> Dict[str, Any]:
    """أسعار الصرف الحالية لعملة أساس (open.er-api.com، مجاني بلا مفتاح، يُحدَّث يوميًا) — ذاكرة ٣٠ دقيقة."""
    base = base.upper()
    hit = _RATES_CACHE.get(base)
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    with _http() as c:
        r = c.get(f"https://open.er-api.com/v6/latest/{base}")
        r.raise_for_status()
        data = r.json()
    if data.get("result") != "success" or not data.get("rates"):
        raise RuntimeError(f"er-api: {data.get('error-type') or 'رد غير صالح'}")
    _RATES_CACHE[base] = (time.time(), data)
    return data


def _src(kind: str, title: str, url: str, fact: str, lang: str, published: Optional[str]) -> Dict[str, Any]:
    return {"title": title, "url": url, "snippet": fact, "text": fact, "fact_text": fact, "provider": f"instant-{kind}",
            "lang": lang, "published": published, "structured": True, "instant": True}


def instant_currency(codes: List[str], local: Optional[str], lang: str) -> List[Dict[str, Any]]:
    base = codes[0]
    quotes = [c for c in codes[1:] if c != base] or [x for x in ([local] if local else []) + ["USD", "EUR"] if x and x != base][:2]
    data = rates(base)
    upd = data.get("time_last_update_unix")
    parts = []
    for qc in quotes:
        v = data["rates"].get(qc)
        if v is None:
            continue
        if lang == "ar":
            parts.append(f"1 {_CUR_NAME.get(base, base)} = {_fmt(v)} {_CUR_NAME.get(qc, qc)}، و1 {_CUR_NAME.get(qc, qc)} = {_fmt(1 / v)} {_CUR_NAME.get(base, base)}")
        else:
            parts.append(f"1 {base} = {_fmt(v)} {qc}, and 1 {qc} = {_fmt(1 / v)} {base}")
    if not parts:
        raise RuntimeError("er-api: العملة غير مدعومة")
    when = time.strftime("%Y-%m-%d", time.gmtime(upd)) if upd else ""
    fact = ("سعر الصرف الحالي: " + "؛ ".join(parts) + f" (السعر المرجعي ليوم {when}؛ أسعار البنوك والصرافات تختلف قليلًا)."
            if lang == "ar" else "Current exchange rate: " + "; ".join(parts) + f" (reference rate of {when}; bank rates differ slightly).")
    return [_src("currency", f"ExchangeRate-API — {base}", f"https://www.exchangerate-api.com/docs/free", fact, lang,
                 _iso(upd) if upd else None)]


def _gold_api(sym: str) -> Dict[str, Any]:
    with _http() as c:
        r = c.get(f"https://api.gold-api.com/price/{sym}")
        r.raise_for_status()
        d = r.json()
    if not d.get("price"):
        raise RuntimeError("gold-api: بلا سعر")
    return d


def instant_metal(sym: str, local: Optional[str], lang: str) -> List[Dict[str, Any]]:
    """سعر المعدن الفوري العالمي (للأونصة) + الغرام بالعملة المحلية + أعيرة الذهب ٢٤/٢٢/٢١/١٨."""
    d = _gold_api(sym)
    usd_oz = float(d["price"])
    cur = local or "USD"
    fx = 1.0 if cur == "USD" else float(rates("USD")["rates"].get(cur) or 0) or None
    if fx is None:
        cur, fx = "USD", 1.0
    gram = usd_oz / 31.1034768 * fx
    name_ar, name_en = METALS[sym][0], METALS[sym][1]
    cur_ar = _CUR_NAME.get(cur, cur)
    if lang == "ar":
        karats = ""
        if sym == "XAU":
            karats = "؛ " + "، ".join(f"عيار {k}: {_fmt(gram * k / 24)} {cur_ar}" for k in (24, 22, 21, 18))
        fact = (f"سعر {name_ar} الفوري العالمي الآن: الأونصة {_fmt(usd_oz)} دولار أمريكي؛ الغرام ≈ {_fmt(gram)} {cur_ar}"
                f"{karats} (للغرام، قبل المصنعية وهامش المحلات).")
    else:
        karats = ""
        if sym == "XAU":
            karats = "; " + ", ".join(f"{k}K: {_fmt(gram * k / 24)} {cur}" for k in (24, 22, 21, 18))
        fact = (f"Live global spot {name_en} price: {_fmt(usd_oz)} USD per troy ounce; ≈ {_fmt(gram)} {cur} per gram"
                f"{karats} (per gram, before retail markup).")
    return [_src("metal", f"Gold API — {d.get('name') or name_en} spot", "https://gold-api.com/", fact, lang,
                 d.get("updatedAt") or _iso(time.time()))]


def instant_crypto(sym: str, local: Optional[str], lang: str) -> List[Dict[str, Any]]:
    try:
        if sym not in ("BTC", "ETH"):
            raise RuntimeError("ليس في gold-api")
        d = _gold_api(sym)
        usd, upd, src_url, src_name = float(d["price"]), d.get("updatedAt"), "https://gold-api.com/", "Gold API"
    except Exception:  # TOLERATED: البديل Coinbase (كل العملات الرقمية الكبرى)
        with _http() as c:
            r = c.get(f"https://api.coinbase.com/v2/prices/{sym}-USD/spot")
            r.raise_for_status()
            usd = float(r.json()["data"]["amount"])
        upd, src_url, src_name = _iso(time.time()), f"https://www.coinbase.com/price/{sym.lower()}", "Coinbase"
    cur = local if local and local != "USD" else None
    loc = ""
    if cur:
        fx = rates("USD")["rates"].get(cur)
        if fx:
            loc = (f" ≈ {_fmt(usd * fx)} {_CUR_NAME.get(cur, cur)}" if lang == "ar" else f" ≈ {_fmt(usd * fx)} {cur}")
    name = CRYPTO[sym][0]
    fact = (f"سعر {name} ({sym}) الآن: {_fmt(usd)} دولار أمريكي{loc} (سعر فوري يتغير كل لحظة)." if lang == "ar"
            else f"{sym} price now: {_fmt(usd)} USD{loc} (live spot price, changes constantly).")
    return [_src("crypto", f"{src_name} — {sym}", src_url, fact, lang, upd)]


# المدن بالعربية ⇒ اسمها لخدمة الطقس (لا يعتمد على نجاح الترجمة)
_CITY_AR = {"الرياض": "Riyadh", "جدة": "Jeddah", "مكة": "Mecca", "المدينة المنورة": "Medina", "الدمام": "Dammam",
            "الطائف": "Taif", "أبها": "Abha", "ابها": "Abha", "تبوك": "Tabuk", "الخبر": "Khobar", "جازان": "Jazan",
            "حائل": "Hail", "بريدة": "Buraydah", "ينبع": "Yanbu", "نجران": "Najran", "الأحساء": "Al Hofuf",
            "دبي": "Dubai", "أبوظبي": "Abu Dhabi", "ابوظبي": "Abu Dhabi", "الشارقة": "Sharjah", "القاهرة": "Cairo",
            "الإسكندرية": "Alexandria", "الاسكندرية": "Alexandria", "الكويت": "Kuwait City", "الدوحة": "Doha",
            "المنامة": "Manama", "مسقط": "Muscat", "عمّان": "Amman", "بغداد": "Baghdad", "الرباط": "Rabat",
            "الدار البيضاء": "Casablanca", "الجزائر": "Algiers", "تونس": "Tunis", "صنعاء": "Sanaa", "عدن": "Aden",
            "بيروت": "Beirut", "دمشق": "Damascus", "الخرطوم": "Khartoum", "طرابلس": "Tripoli", "غزة": "Gaza",
            "القدس": "Jerusalem", "نيويورك": "New York", "واشنطن": "Washington", "لندن": "London", "باريس": "Paris",
            "برلين": "Berlin", "مدريد": "Madrid", "روما": "Rome", "موسكو": "Moscow", "إسطنبول": "Istanbul",
            "اسطنبول": "Istanbul", "أنقرة": "Ankara", "طهران": "Tehran", "كراتشي": "Karachi", "مومباي": "Mumbai",
            "نيودلهي": "New Delhi", "بكين": "Beijing", "شنغهاي": "Shanghai", "طوكيو": "Tokyo", "أوساكا": "Osaka",
            "سيول": "Seoul", "جاكرتا": "Jakarta", "كوالالمبور": "Kuala Lumpur", "بانكوك": "Bangkok",
            "تورنتو": "Toronto", "سيدني": "Sydney", "أمستردام": "Amsterdam", "زيورخ": "Zurich", "جنيف": "Geneva"}
_CITY_AR_RX = [(re.compile(rf"(?<![\w])(?:و|ب|ل|ف)?{re.escape(k)}(?![\w])"), v)
               for k, v in sorted(_CITY_AR.items(), key=lambda kv: -len(kv[0]))]
# العاصمة لكل دولة (عند ذكر الدولة وحدها)
_CAPITAL = {"SA": "Riyadh", "AE": "Abu Dhabi", "EG": "Cairo", "KW": "Kuwait City", "QA": "Doha", "BH": "Manama",
            "OM": "Muscat", "JO": "Amman", "IQ": "Baghdad", "MA": "Rabat", "DZ": "Algiers", "TN": "Tunis", "YE": "Sanaa",
            "LB": "Beirut", "SY": "Damascus", "SD": "Khartoum", "LY": "Tripoli", "PS": "Jerusalem", "US": "Washington",
            "GB": "London", "CA": "Ottawa", "AU": "Canberra", "FR": "Paris", "DE": "Berlin", "ES": "Madrid", "IT": "Rome",
            "PT": "Lisbon", "NL": "Amsterdam", "BR": "Brasilia", "MX": "Mexico City", "RU": "Moscow", "UA": "Kyiv",
            "TR": "Ankara", "IR": "Tehran", "PK": "Islamabad", "IN": "New Delhi", "CN": "Beijing", "JP": "Tokyo",
            "KR": "Seoul", "ID": "Jakarta", "MY": "Kuala Lumpur", "TH": "Bangkok", "GR": "Athens", "IL": "Jerusalem",
            "NG": "Abuja", "KE": "Nairobi", "ET": "Addis Ababa", "BD": "Dhaka", "CH": "Bern", "SE": "Stockholm",
            "PL": "Warsaw"}


def _weather_place(question: str, en_q: str, regions: List[str]) -> Optional[str]:
    for rx, en_name in _CITY_AR_RX:  # المدينة العربية المذكورة أولًا (أدق من أي ترجمة)
        if rx.search(question or ""):
            return en_name
    m = re.search(r"\b(?:weather|temperature|forecast)\b.*?\b(?:in|at|of|for)\s+([A-Za-z][A-Za-z .'-]{1,40})", en_q or "", re.I)
    if m:
        return m.group(1).strip(" .?!").split(" today")[0].split(" now")[0].strip()
    m = re.search(r"\b(?:in|at)\s+([A-Z][A-Za-z .'-]{1,30})\b", en_q or "")
    if m:
        return m.group(1).strip(" .?!")
    for c in regions:  # المدينة المذكورة (إن وجدت) وإلا العاصمة الأولى في القائمة
        row = _BY_CODE[c]
        for en_name in row[5]:
            if re.search(rf"\b{re.escape(en_name)}\b", en_q or "", re.I):
                return en_name
        return _CAPITAL.get(c) or row[5][0]
    return None


_WX_AR = {"sunny": "مشمس", "clear": "صافٍ", "partly cloudy": "غائم جزئيًا", "cloudy": "غائم", "overcast": "ملبد بالغيوم",
          "mist": "ضباب خفيف", "fog": "ضباب", "light rain": "مطر خفيف", "rain": "مطر", "heavy rain": "مطر غزير",
          "patchy rain possible": "احتمال مطر متفرق", "thunder": "رعد", "haze": "غبار/عتمة", "dust": "غبار"}


def instant_weather(place: str, lang: str) -> List[Dict[str, Any]]:
    with _http(10.0, {"User-Agent": "curl/8"}) as c:
        r = c.get(f"https://wttr.in/{quote(place)}", params={"format": "j1"})
        r.raise_for_status()
        d = r.json()
    cur = (d.get("current_condition") or [{}])[0]
    day = (d.get("weather") or [{}])[0]
    near = ((d.get("nearest_area") or [{}])[0].get("areaName") or [{}])[0].get("value") or ""
    shown = next((k for k, v in _CITY_AR.items() if v == place), None) if lang == "ar" else None
    area = (shown or place) + (f" ({near})" if near and near.lower() not in place.lower() else "")
    desc = ((cur.get("weatherDesc") or [{}])[0].get("value") or "").strip()
    if not cur.get("temp_C"):
        raise RuntimeError("wttr: بلا قراءة")
    if lang == "ar":
        dar = _WX_AR.get(desc.lower(), desc)
        fact = (f"الطقس الآن في {area}: {cur['temp_C']}°م (الإحساس {cur.get('FeelsLikeC')}°م)، {dar}، الرطوبة "
                f"{cur.get('humidity')}٪، الرياح {cur.get('windspeedKmph')} كم/س؛ اليوم: العظمى {day.get('maxtempC')}°م "
                f"والصغرى {day.get('mintempC')}°م.")
    else:
        fact = (f"Weather now in {area}: {cur['temp_C']}°C (feels {cur.get('FeelsLikeC')}°C), {desc}, humidity "
                f"{cur.get('humidity')}%, wind {cur.get('windspeedKmph')} km/h; today: high {day.get('maxtempC')}°C, "
                f"low {day.get('mintempC')}°C.")
    return [_src("weather", f"wttr.in — {area}", f"https://wttr.in/{quote(place)}", fact, lang, _iso(time.time()))]


def instant_time(codes: List[str], lang: str) -> List[Dict[str, Any]]:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    out = []
    for c in codes[:3]:
        row = _BY_CODE[c]
        now = datetime.now(ZoneInfo(row[3]))
        hhmm = now.strftime("%H:%M")
        fact = (f"الوقت الآن في {row[4][0]}: {hhmm} ({now.strftime('%Y-%m-%d')}، المنطقة الزمنية {row[3]}، UTC{now.strftime('%z')[:3]})."
                if lang == "ar" else f"Local time now in {row[5][0].title()}: {hhmm} ({now.strftime('%Y-%m-%d')}, {row[3]}, UTC{now.strftime('%z')[:3]}).")
        out.append(_src("time", f"IANA tz — {row[3]}", "https://www.iana.org/time-zones", fact, lang, _iso(time.time())))
    if not out:
        raise RuntimeError("لا دولة محددة للوقت")
    return out


def instant_jobs(intent: Dict[str, Any], question: str, en_q: Optional[str], lang: str) -> List[Tuple[str, Any, tuple]]:
    """مهام الإجابات المباشرة المناسبة للنية (تُشغَّل متوازية مع البحث)."""
    jobs: List[Tuple[str, Any, tuple]] = []
    fact_lang = "ar" if lang == "ar" else "en"
    k = intent["kinds"]
    if intent.get("metal"):
        jobs.append(("instant-metal", instant_metal, (intent["metal"], intent.get("local_currency"), fact_lang)))
    if intent.get("crypto"):
        jobs.append(("instant-crypto", instant_crypto, (intent["crypto"], intent.get("local_currency"), fact_lang)))
    if "currency" in k and intent["currencies"]:
        jobs.append(("instant-currency", instant_currency, (intent["currencies"], intent.get("local_currency"), fact_lang)))
    if "weather" in k:
        place = _weather_place(question, en_q or "", intent["regions"])
        if place:
            jobs.append(("instant-weather", instant_weather, (place, fact_lang)))
    if "time" in k and intent["regions"]:
        jobs.append(("instant-time", instant_time, (intent["regions"], fact_lang)))
    return jobs


# ============================================================
# ٥) المنصات
# ============================================================
def _strip(s: str) -> str:
    import html as _h
    return " ".join(_h.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())


def _yt_walk(o):
    if isinstance(o, dict):
        if "videoRenderer" in o:
            yield o["videoRenderer"]
        for v in o.values():
            yield from _yt_walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _yt_walk(v)


def _runs(x) -> str:
    if not isinstance(x, dict):
        return ""
    return x.get("simpleText") or "".join(r.get("text", "") for r in x.get("runs") or [])


def parse_youtube(html: str, lang: str) -> List[Dict[str, Any]]:
    from world_search import parse_date
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        return []
    out = []
    for v in _yt_walk(json.loads(m.group(1))):
        vid = v.get("videoId")
        title = _runs(v.get("title"))
        if not vid or not title:
            continue
        ago = _runs(v.get("publishedTimeText"))
        ago_n = re.sub(r"^(\d+)\s*([a-z])[a-z]*\s*ago$", lambda mm: f"{mm.group(1)} " + {"h": "hours", "d": "days", "w": "weeks", "m": "months", "y": "years"}.get(mm.group(2), "days") + " ago", ago.strip())
        snippet = " ".join(_runs(s.get("snippetText")) for s in v.get("detailedMetadataSnippets") or [])
        out.append({"title": title, "url": f"https://www.youtube.com/watch?v={vid}", "snippet": snippet[:300],
                    "provider": "youtube", "platform": "YouTube", "kind": "video", "lang": lang,
                    "site": _runs(v.get("ownerText")), "published": parse_date(ago_n) if ago_n else None,
                    "meta": " · ".join(x for x in (_runs(v.get("lengthText")), _runs(v.get("viewCountText"))) if x)})
        if len(out) >= 6:
            break
    return out


def p_youtube(q: str, lang: str) -> List[Dict[str, Any]]:
    with _http(10.0) as c:
        r = c.get("https://www.youtube.com/results", params={"search_query": q, "hl": lang})
        r.raise_for_status()
    return parse_youtube(r.text, lang)


def p_github(q: str, lang: str) -> List[Dict[str, Any]]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "SovereignAI-search"}
    tok = os.getenv("GITHUB_TOKEN")
    if tok:  # الرمز يُرسل إلى api.github.com وحدها
        headers["Authorization"] = f"Bearer {tok}"
    with _http(8.0, headers) as c:
        r = c.get("https://api.github.com/search/repositories", params={"q": q, "sort": "stars", "per_page": 6})
        r.raise_for_status()
        items = r.json().get("items") or []
    return [{"title": it["full_name"], "url": it["html_url"], "snippet": (it.get("description") or "")[:300],
             "text": f"{it['full_name']}: {it.get('description') or ''}", "provider": "github", "platform": "GitHub",
             "kind": "repo", "lang": "en", "published": it.get("pushed_at"),
             "meta": f"★ {it.get('stargazers_count', 0):,} · {it.get('language') or ''}".strip(" ·")} for it in items]


def p_arxiv(q: str, lang: str) -> List[Dict[str, Any]]:
    with _http(10.0) as c:
        r = c.get("http://export.arxiv.org/api/query", params={"search_query": f"all:{q}", "max_results": 5,
                                                                 "sortBy": "relevance"})
        r.raise_for_status()
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", r.text, re.S):
        def tag(n):
            m = re.search(rf"<{n}[^>]*>(.*?)</{n}>", e, re.S)
            return _strip(m.group(1)) if m else ""
        summary = tag("summary")
        if len(summary) < 120:
            continue
        out.append({"title": tag("title"), "url": tag("id").replace("http://", "https://"), "snippet": summary[:300],
                    "text": summary, "provider": "arxiv", "lang": "en", "scholarly": True, "published": tag("published") or None})
    return out


def p_crossref(q: str, lang: str) -> List[Dict[str, Any]]:
    params = {"query": q, "rows": 8, "filter": "has-abstract:true", "select": "DOI,title,abstract,issued,container-title"}
    mail = os.getenv("WORLD_SEARCH_CONTACT_EMAIL")
    if mail:
        params["mailto"] = mail
    with _http(10.0) as c:
        r = c.get("https://api.crossref.org/works", params=params)
        r.raise_for_status()
        items = (r.json().get("message") or {}).get("items") or []
    out = []
    for it in items:
        ab = _strip(it.get("abstract") or "")
        ab = re.sub(r"^(?:Abstract|Background)\s*[:.]?\s*", "", ab)
        if len(ab) < 120:
            continue
        year = (((it.get("issued") or {}).get("date-parts") or [[None]])[0] or [None])[0]
        out.append({"title": " ".join(it.get("title") or [])[:300], "url": f"https://doi.org/{it['DOI']}", "snippet": ab[:300],
                    "text": ab, "provider": "crossref", "lang": "en", "scholarly": True,
                    "published": f"{year}-01-01T00:00:00Z" if year else None})
    return out[:5]


def p_semantic_scholar(q: str, lang: str) -> List[Dict[str, Any]]:
    with _http(8.0) as c:
        r = c.get("https://api.semanticscholar.org/graph/v1/paper/search",
                  params={"query": q, "limit": 6, "fields": "title,abstract,year,url,citationCount"})
        r.raise_for_status()
        data = r.json().get("data") or []
    return [{"title": d.get("title") or "", "url": d.get("url") or f"https://www.semanticscholar.org/paper/{d['paperId']}",
             "snippet": (d.get("abstract") or "")[:300], "text": d.get("abstract") or "", "provider": "semanticscholar",
             "lang": "en", "scholarly": True, "published": f"{d['year']}-01-01T00:00:00Z" if d.get("year") else None}
            for d in data if len(d.get("abstract") or "") >= 120]


def p_openlibrary(q: str, lang: str) -> List[Dict[str, Any]]:
    with _http(8.0) as c:
        r = c.get("https://openlibrary.org/search.json",
                  params={"q": q, "limit": 6, "fields": "title,author_name,first_publish_year,key,language"})
        r.raise_for_status()
        docs = r.json().get("docs") or []
    return [{"title": d.get("title") or "", "url": f"https://openlibrary.org{d['key']}", "snippet": "",
             "provider": "openlibrary", "platform": "Open Library", "kind": "book", "lang": "en",
             "site": "، ".join((d.get("author_name") or [])[:2]),
             "published": f"{d['first_publish_year']}-01-01T00:00:00Z" if d.get("first_publish_year") else None,
             "meta": str(d.get("first_publish_year") or "")} for d in docs if d.get("key")]


def p_lemmy(q: str, lang: str) -> List[Dict[str, Any]]:
    with _http(8.0) as c:
        r = c.get("https://lemmy.world/api/v3/search", params={"q": q, "type_": "Posts", "sort": "TopAll", "limit": 6})
        r.raise_for_status()
        posts = r.json().get("posts") or []
    out = []
    for p in posts:
        post = p.get("post") or {}
        if not post.get("ap_id") and not post.get("id"):
            continue
        body = _strip(post.get("body") or "")
        out.append({"title": post.get("name") or "", "url": post.get("ap_id") or f"https://lemmy.world/post/{post['id']}",
                    "snippet": body[:300], "text": f"{post.get('name') or ''}. {body}"[:4000], "provider": "lemmy",
                    "platform": "Lemmy", "kind": "discussion", "lang": "en", "published": post.get("published"),
                    "site": (p.get("community") or {}).get("name") or "",
                    "meta": f"▲ {(p.get('counts') or {}).get('score', 0)}"})
    return out


def p_stackexchange_site(q: str, site: str) -> List[Dict[str, Any]]:
    with _http(8.0) as c:
        r = c.get("https://api.stackexchange.com/2.3/search/excerpts",
                  params={"order": "desc", "sort": "relevance", "q": q, "site": site, "pagesize": 6})
        r.raise_for_status()
        items = r.json().get("items") or []
    host = {"superuser": "superuser.com", "askubuntu": "askubuntu.com"}.get(site, f"{site}.stackexchange.com")
    out = []
    for it in items:
        qid = it.get("question_id")
        if not qid:
            continue
        body = _strip(it.get("excerpt") or "")
        title = _strip(it.get("title") or "")
        out.append({"title": title, "url": f"https://{host}/q/{qid}" + (f"#{it['answer_id']}" if it.get("answer_id") else ""),
                    "snippet": body[:300], "text": f"{title}. {body}", "provider": f"stackexchange-{site}", "lang": "en",
                    "platform": "Stack Exchange", "kind": "qa", "site": host,
                    "published": _iso(it["last_activity_date"]) if it.get("last_activity_date") else None})
    return out


def parse_baidu(html: str) -> List[Dict[str, Any]]:
    out = []
    for block in re.split(r'<div class="result c-container', html)[1:]:
        block = block[:15000]
        mu = re.search(r'\bmu="(https?://[^"]+)"', block)
        h3 = re.search(r"<h3[^>]*>(.*?)</h3>", block, re.S)
        if not mu or not h3 or "baidu.com" in mu.group(1).split("/")[2]:
            continue
        rest = _strip(re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", block[h3.end():], flags=re.S))
        out.append({"title": _strip(h3.group(1)), "url": mu.group(1), "snippet": rest[:300], "provider": "baidu",
                    "lang": "zh", "rank": len(out)})
        if len(out) >= 8:
            break
    return out


def p_baidu(q: str, lang: str = "zh") -> List[Dict[str, Any]]:
    with _http(10.0, {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/124.0 Safari/537.36", "Accept-Language": "zh-CN,zh;q=0.9"}) as c:
        r = c.get("https://www.baidu.com/s", params={"wd": q})
        r.raise_for_status()
    return parse_baidu(r.text)


def p_quran(q_ar: str, lang: str) -> List[Dict[str, Any]]:
    """القرآن الكريم (alquran.cloud): الآيات المطابقة بنصها العثماني مع رقم السورة والآية ورابط quran.com."""
    words = [w for w in re.findall(r"[\u0621-\u064A]{3,}", q_ar or "")
             if w not in {"آية", "اية", "سورة", "القرآن", "قرآن", "القران", "الكريم", "تتحدث", "تتكلم", "التي", "الذي",
                          "عن", "في", "ما", "هي", "هو", "عن", "اريد", "أريد", "ابحث"}]
    if not words:
        return []
    kw = max(words, key=len)
    with _http(8.0) as c:
        r = c.get(f"https://api.alquran.cloud/v1/search/{quote(kw)}/all/quran-simple-clean")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        matches = ((r.json().get("data") or {}).get("matches") or [])[:6]
    out = []
    for m in matches:
        s = m.get("surah") or {}
        num, ay = s.get("number"), m.get("numberInSurah")
        text = f"{m.get('text', '')} ({s.get('name', '')}، الآية {ay})"
        out.append({"title": f"{s.get('name', '')} — الآية {ay}", "url": f"https://quran.com/{num}/{ay}", "snippet": text,
                    "text": text, "provider": "quran", "platform": "القرآن الكريم", "kind": "verse", "lang": "ar",
                    "site": "alquran.cloud", "published": None, "meta": f"{s.get('englishName', '')} {num}:{ay}"})
    return out


def platform_jobs(intent: Dict[str, Any], queries: Dict[str, str], user_lang: str, keyword_query,
                  scholarly_query) -> List[Tuple[str, Any, tuple]]:
    """مهام المنصات المناسبة لما يطلبه السؤال (YouTube للفيديو والطرق، GitHub للكود، الكتب، النقاشات…)."""
    k = set(intent["kinds"])
    en_q = queries.get("en")
    jobs: List[Tuple[str, Any, tuple]] = []
    uq = keyword_query(queries.get(user_lang, ""), user_lang) if queries.get(user_lang) else None
    if k & {"video", "howto"} and uq:
        jobs.append(("youtube", p_youtube, (uq, user_lang)))
    if en_q:
        ek = keyword_query(en_q, "en")
        if "code" in k or ("tech" in k and "howto" not in k):
            jobs.append(("github", p_github, (ek, "en")))
        if "scholarly" in k and "fresh" not in k:
            sq = scholarly_query(en_q)
            jobs += [("crossref", p_crossref, (sq, "en")), ("arxiv", p_arxiv, (sq, "en")),
                     ("semanticscholar", p_semantic_scholar, (sq, "en"))]
        if "book" in k:
            jobs.append(("openlibrary", p_openlibrary, (ek, "en")))
        if "discussion" in k or "comparison" in k:
            jobs.append(("lemmy", p_lemmy, (ek, "en")))
        for site in intent.get("se_sites") or []:
            if site in ("stackoverflow",):
                continue
            jobs.append((f"stackexchange-{site}", p_stackexchange_site, (ek, site)))
    if "zh" in queries:
        jobs.append(("baidu", p_baidu, (keyword_query(queries["zh"], "zh"), "zh")))
    if "religion" in k and queries.get("ar"):
        jobs.append(("quran", p_quran, (queries["ar"], "ar")))
    return jobs
