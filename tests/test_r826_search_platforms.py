"""R-826 — محرك البحث يميز المطلوب ويبحث في منصات العالم: فهم النية (نوع السؤال/الدولة/العملة/المعدن)،
إجابات مباشرة حية (صرف/ذهب/عملات رقمية/طقس/وقت)، منصات (YouTube/GitHub/Stack Exchange/Lemmy/Open Library/
Baidu/القرآن الكريم/الأبحاث)، تنقيح مكاني وعُملي، مكافأة نوع الإجابة، وكشف لغات العالم.
كل الاختبارات بلا شبكة (نقل httpx وهمي/حقن).
"""

import json
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import config  # noqa: E402
import search_platforms as sp  # noqa: E402
import world_search as w  # noqa: E402


def _mock(monkeypatch, handler):
    """كل طلبات search_platforms تمر عبر نقل وهمي."""
    def _client(timeout=8.0, headers=None):
        return httpx.Client(transport=httpx.MockTransport(handler), headers=headers or {})
    monkeypatch.setattr(sp, "_http", _client)
    sp._RATES_CACHE.clear()


ER = {"result": "success", "time_last_update_unix": 1793404801,
      "rates": {"USD": 1, "SAR": 3.75, "EUR": 0.92, "EGP": 48.5, "TRY": 41.0, "JPY": 150.0}}


# ---------------- فهم المطلوب ----------------
@pytest.mark.parametrize("q,en,kind,atype", [
    ("كم سعر الدولار مقابل الريال اليوم", "How much is the dollar against the riyal today", "currency", "numeric"),
    ("أسعار الذهب اليوم في السعودية", "gold prices today in Saudi Arabia", "metal", None),
    ("كم سعر البيتكوين", "How much is bitcoin", "crypto", "numeric"),
    ("كم درجة الحرارة في جدة الآن", "What is the temperature in Jeddah now", "weather", "numeric"),
    ("كم الساعة الآن في طوكيو", "What time is it now in Tokyo", "time", "numeric"),
    ("كيف أطبخ الكبسة", "How do I cook kabsa", "howto", "howto"),
    ("آية عن الصبر", "A verse about patience", "religion", None),
    ("ما هو الذكاء الاصطناعي", "What is artificial intelligence", "definition", "definition"),
])
def test_analyze_detects_intent(q, en, kind, atype):
    a = sp.analyze(q, en, "ar")
    assert kind in a["kinds"]
    if atype:
        assert a["answer_type"] == atype
    assert a["label_ar"]


def test_analyze_no_false_triggers():
    a = sp.analyze("the team won the cup, try it now", "", "en")
    assert not ({"currency", "metal", "crypto"} & set(a["kinds"]))
    # «مكتبة» ليست «كتب»، و«ما هو أفضل» ليس تعريفًا
    assert "book" not in sp.analyze("أفضل مكتبة بايثون", "best python library", "ar")["kinds"]
    assert "definition" not in sp.analyze("ما هو افضل دايت", "What is the best diet", "ar")["kinds"]
    # سعر منتج بالريال ليس سؤال صرف
    assert "currency" not in sp.analyze("سعر ايفون 17 في السعودية بالريال", "iPhone 17 price in Saudi Arabia in riyals",
                                        "ar")["kinds"]


def test_regions_add_country_language_and_currency():
    a = sp.analyze("ما عاصمة اليابان", "What is the capital of Japan", "ar")
    assert a["regions"] == ["JP"] and a["region_langs"] == ["ja"] and a["local_currency"] == "JPY"
    assert sp.analyze("الذهب في السعودية", None, "ar")["local_currency"] == "SAR"
    # بلا دولة: عملة لغة السائل
    assert sp.analyze("Altın fiyatı bugün", None, "tr", True)["local_currency"] == "TRY"


def test_multilingual_metal_without_translation():
    q = "Quel est le prix de l'or aujourd'hui en France"
    a = sp.analyze(q, None, "fr", w.is_fresh(q))
    assert a["metal"] == "XAU" and a["regions"] == ["FR"] and a["local_currency"] == "EUR"


def test_currency_detection_definite_adjective():
    assert sp.detect_currencies("أسعار الصرف مقابل الريال اليمني") == ["YER"]
    assert sp.detect_currencies("الريال السعودي") == ["SAR"]
    assert sp.mentions_other_currency("سعر الدولار مقابل الجنيه اليوم", ["USD", "SAR"])
    assert not sp.mentions_other_currency("أسعار العملات مقابل الريال اليوم", ["USD", "SAR"])


def test_location_refinement():
    assert sp.mentions_other_region("ارتفاع الأسعار في مصر اليوم", ["SA"])
    assert not sp.mentions_other_region("الذهب في السعودية ومصر", ["SA"])
    assert not sp.mentions_other_region("نص بلا دولة", ["SA"])


def test_type_bonus():
    assert sp.type_bonus("The population is 123 million", "numeric") == 1.0
    assert sp.type_bonus("no digits here", "numeric") == 0.0
    assert sp.type_bonus("He was born in 1879", "date") == 1.0
    assert sp.type_bonus("anything", "general") == 0.0


# ---------------- الإجابات المباشرة ----------------
def test_instant_currency(monkeypatch):
    _mock(monkeypatch, lambda req: httpx.Response(200, json=ER))
    src = sp.instant_currency(["USD", "SAR"], "SAR", "ar")[0]
    assert "3.75" in src["fact_text"] and src["instant"] and src["structured"]
    assert src["provider"] == "instant-currency"


def test_instant_metal_local_karats(monkeypatch):
    def h(req):
        if "gold-api" in str(req.url):
            return httpx.Response(200, json={"name": "Gold", "price": 3110.34768, "updatedAt": "2026-10-31T10:00:00Z"})
        return httpx.Response(200, json=ER)
    _mock(monkeypatch, h)
    fact = sp.instant_metal("XAU", "SAR", "ar")[0]["fact_text"]
    assert "عيار 21" in fact and "375" in fact  # 100$/غ × 3.75 = 375 ريال للغرام (عيار 24)


def test_instant_crypto_falls_back_to_coinbase(monkeypatch):
    def h(req):
        if "coinbase" in str(req.url):
            return httpx.Response(200, json={"data": {"amount": "150.5"}})
        return httpx.Response(200, json=ER)
    _mock(monkeypatch, h)
    src = sp.instant_crypto("SOL", None, "en")[0]
    assert "150.5" in src["fact_text"] and "coinbase" in src["url"]


def test_weather_place_from_arabic_city_without_translation():
    assert sp._weather_place("كم درجة الحرارة في جدة الآن", "", ["SA"]) == "Jeddah"
    assert sp._weather_place("الطقس في السعودية", "", ["SA"]) == "Riyadh"
    assert sp._weather_place("", "weather in Paris today", []) == "Paris"


def test_instant_weather(monkeypatch):
    payload = {"current_condition": [{"temp_C": "29", "FeelsLikeC": "31", "humidity": "56", "windspeedKmph": "15",
                                      "weatherDesc": [{"value": "Sunny"}]}],
               "weather": [{"maxtempC": "34", "mintempC": "27"}],
               "nearest_area": [{"areaName": [{"value": "As Safa"}]}]}
    _mock(monkeypatch, lambda req: httpx.Response(200, json=payload))
    fact = sp.instant_weather("Jeddah", "ar")[0]["fact_text"]
    assert "جدة" in fact and "29" in fact and "مشمس" in fact


def test_instant_time_is_local():
    fact = sp.instant_time(["JP"], "ar")[0]["fact_text"]
    assert "Asia/Tokyo" in fact and "UTC+09" in fact


def test_instant_jobs_match_intent():
    a = sp.analyze("كم سعر الدولار مقابل الريال اليوم", "How much is the dollar against the riyal today", "ar", True)
    names = [n for n, *_ in sp.instant_jobs(a, "كم سعر الدولار مقابل الريال اليوم", None, "ar")]
    assert names == ["instant-currency"]
    a = sp.analyze("ما هو الذكاء الاصطناعي", "What is AI", "ar")
    assert sp.instant_jobs(a, "ما هو الذكاء الاصطناعي", "What is AI", "ar") == []


# ---------------- المنصات ----------------
def test_parse_youtube():
    data = {"contents": {"x": [{"videoRenderer": {
        "videoId": "abc123", "title": {"runs": [{"text": "طريقة الكبسة"}]},
        "ownerText": {"runs": [{"text": "شيف"}]}, "lengthText": {"simpleText": "10:24"},
        "viewCountText": {"simpleText": "1,000 views"}, "publishedTimeText": {"simpleText": "2 days ago"}}}]}}
    html = f"<script>var ytInitialData = {json.dumps(data)};</script>"
    out = sp.parse_youtube(html, "ar")
    assert out[0]["url"] == "https://www.youtube.com/watch?v=abc123"
    assert out[0]["platform"] == "YouTube" and out[0]["kind"] == "video" and out[0]["published"]


def test_parse_baidu():
    html = ('<div class="result c-container xpath" mu="https://zhidao.example.cn/a"><h3><a>黄金价格</a></h3>'
            '<span>今日黄金价格上涨</span></div><div class="result c-container" mu="https://www.baidu.com/x">'
            '<h3>内部</h3></div>')
    out = sp.parse_baidu(html)
    assert len(out) == 1 and out[0]["url"] == "https://zhidao.example.cn/a" and out[0]["lang"] == "zh"


def test_p_quran(monkeypatch):
    payload = {"data": {"matches": [{"text": "واستعينوا بالصبر والصلاة", "numberInSurah": 45,
                                     "surah": {"number": 2, "name": "البقرة", "englishName": "Al-Baqara"}}]}}
    seen = []

    def h(req):
        seen.append(str(req.url))
        return httpx.Response(200, json=payload)
    _mock(monkeypatch, h)
    out = sp.p_quran("آية عن الصبر", "ar")
    assert out[0]["url"] == "https://quran.com/2/45" and out[0]["kind"] == "verse"
    assert "%D8%A7%D9%84%D8%B5%D8%A8%D8%B1" in seen[0]  # «الصبر» لا «آية»


def test_github_token_only_to_github(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok-x")
    got = {}

    def h(req):
        got[req.url.host] = req.headers.get("authorization")
        return httpx.Response(200, json={"items": [{"full_name": "a/b", "html_url": "https://github.com/a/b",
                                                    "description": "bot lib", "stargazers_count": 5}]})
    _mock(monkeypatch, h)
    out = sp.p_github("telegram bot python", "en")
    assert got == {"api.github.com": "Bearer tok-x"} and out[0]["kind"] == "repo"


def test_platform_jobs_routing():
    a = sp.analyze("كيف أطبخ الكبسة فيديو", "How to cook kabsa video", "ar")
    names = [n for n, *_ in sp.platform_jobs(a, {"ar": "كيف أطبخ الكبسة فيديو", "en": "How to cook kabsa video"}, "ar",
                                             w.keyword_query, w.scholarly_query)]
    assert "youtube" in names
    a = sp.analyze("آية عن الصبر", "A verse about patience", "ar")
    names = [n for n, *_ in sp.platform_jobs(a, {"ar": "آية عن الصبر"}, "ar", w.keyword_query, w.scholarly_query)]
    assert names == ["quran"]


# ---------------- كشف لغات العالم ----------------
@pytest.mark.parametrize("text,lang", [
    ("Quel est le meilleur régime pour perdre du poids", "fr"), ("¿Cuál es la capital de Japón?", "es"),
    ("Wie hoch ist der Goldpreis heute", "de"), ("Qual é o melhor celular", "pt"),
    ("Altın fiyatı bugün nedir", "tr"), ("Apa ibu kota Jepang", "id"), ("قیمت طلا امروز چقدر است", "fa"),
    ("سونے کی قیمت کیا ہے", "ur"), ("Яка столиця Японії", "uk"), ("Ποια είναι η πρωτεύουσα", "el"),
    ("What is the capital of Japan", "en"), ("ما عاصمة اليابان", "ar"), ("東京の天気", "ja"),
])
def test_detect_lang_world(text, lang):
    assert w.detect_lang(text) == lang


def test_boilerplate_sentences_dropped():
    assert w.sentences("للإطلاع على الأسعار تابعنا على الفيس بوك مقالات ذات صلة سعر الذهب في الإمارات اليوم.") == []


# ---------------- الخط الكامل ----------------
@pytest.fixture
def platform_world(monkeypatch):
    w._TR_CACHE.clear()
    w._TR_DEAD.clear()
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", True)
    monkeypatch.setenv("WORLD_SEARCH_LANGS", "en")
    monkeypatch.setenv("WORLD_SEARCH_INDEX_ENABLED", "false")
    monkeypatch.setenv("WORLD_SEARCH_CACHE", "false")
    tr = {"كم سعر الدولار مقابل الريال اليوم": "How much is the dollar against the riyal today"}
    monkeypatch.setattr(w, "translate", lambda text, target, source="auto": (tr.get(text, text), "fake"))
    now2 = w._iso(time.time() - 2 * 3600)
    monkeypatch.setattr(w, "_p_google_news", lambda q, lang: [
        {"title": "سعر الدولار مقابل الجنيه اليوم في البنوك", "url": "https://n.example/eg", "snippet": "",
         "text": "سعر الدولار مقابل الجنيه اليوم في البنوك", "provider": "google-news", "lang": "ar",
         "published": now2, "news": True, "site": "مصري", "rank": 0},
        {"title": "سعر الدولار مقابل الريال اليوم مستقر", "url": "https://n.example/sa", "snippet": "",
         "text": "سعر الدولار مقابل الريال اليوم مستقر", "provider": "google-news", "lang": "ar",
         "published": now2, "news": True, "site": "عاجل", "rank": 1}] if lang == "ar" else [])
    for name in ("_p_bing", "_p_bing_news", "_p_duckduckgo", "_p_marginalia", "_p_pubmed", "_p_europepmc",
                 "_p_openalex", "_p_stackexchange", "_p_hackernews", "_p_wikipedia"):
        monkeypatch.setattr(w, name, lambda q, lang: [])
    monkeypatch.setattr(w, "_p_wikidata", lambda q, lang: [])
    monkeypatch.setattr(w, "_p_index", lambda terms, lang, fresh=False: [])
    import web_tools
    monkeypatch.setattr(web_tools, "fetch", lambda url, timeout=None: {"text": ""})
    _mock(monkeypatch, lambda req: httpx.Response(200, json=ER))
    monkeypatch.setattr(sp, "platform_jobs", lambda *a, **k: [("youtube", lambda q, l: [
        {"title": "شرح سعر الصرف", "url": "https://www.youtube.com/watch?v=x", "snippet": "", "provider": "youtube",
         "platform": "YouTube", "kind": "video", "lang": "ar", "site": "قناة", "meta": "5:00", "published": None}],
        ("q", "ar"))])


def test_answer_instant_first_platforms_and_currency_refinement(platform_world):
    res = w.answer("كم سعر الدولار مقابل الريال اليوم")
    assert res["ok"] and res["instant"] == 1
    assert res["points"][0]["instant"] and "3.75" in res["points"][0]["text"]
    assert res["intent"]["label_ar"] and "currency" in res["intent"]["kinds"]
    sites = {n["site"] for n in res["news"]}
    assert "عاجل" in sites and "مصري" not in sites  # خبر الجنيه المصري خارج المطلوب
    assert res["platforms"][0]["platform"] == "YouTube"
    # عنصر المنصة لا يصير جملة مرشحة
    assert all("youtube" not in (s["url"] or "") for s in res["sources"])
    txt = w.format_reply(res)
    assert "فهمت المطلوب" in txt and "الإجابة المباشرة" in txt and "من المنصات" in txt


def test_engine_status_lists_platforms():
    st = w.engine_status()
    assert "youtube" in st["providers"] and "instant-currency" in st["providers"]
    assert "fa" in st["detectable_languages"]
