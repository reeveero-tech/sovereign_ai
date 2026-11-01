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


def test_other_asset_refinement():
    cur = sp.analyze("كم سعر الدولار مقابل الريال اليوم", "dollar against riyal today", "ar", True)
    assert sp.mentions_other_asset("سعر غرام الذهب عيار 24 بالريال", cur)
    assert not sp.mentions_other_asset("سعر الدولار مقابل الريال مستقر", cur)
    gold = sp.analyze("أسعار الذهب اليوم", "gold prices today", "ar", True)
    assert sp.mentions_other_asset("سعر البيتكوين يهبط", gold)


def test_cache_key_includes_engine_version(monkeypatch):
    import search_index
    k1 = search_index.cache_key("سؤال", "ar")
    monkeypatch.setattr(search_index, "ENGINE_VERSION", "next")
    assert search_index.cache_key("سؤال", "ar") != k1


def test_r826d_refinements():
    gold = sp.analyze("Quel est le prix de l'or aujourd'hui en France", None, "fr", True)
    assert sp.mentions_other_asset("Prix du diesel : ce que TotalEnergies change dès aujourd'hui", gold)
    assert not sp.mentions_other_asset("Le prix de l'or recule aujourd'hui", gold)
    cur = sp.analyze("كم سعر الدولار مقابل الريال اليوم", "dollar against riyal today", "ar", True)
    assert cur["regions"] == ["SA"]  # النطاق من العملة المحلية
    assert sp.github_query("best python library for making a telegram bot") == "python telegram bot"


def test_repo_titles_not_translated(platform_world, monkeypatch):
    monkeypatch.setattr(sp, "platform_jobs", lambda *a, **k: [("github", lambda q, l: [
        {"title": "python-telegram-bot/python-telegram-bot", "url": "https://github.com/python-telegram-bot/x",
         "snippet": "", "provider": "github", "platform": "GitHub", "kind": "repo", "lang": "en", "published": None}],
        ("q", "en"))])
    monkeypatch.setattr(w, "translate", lambda text, target, source="auto": ("[tr] " + text, "fake"))
    res = w.answer("كم سعر الدولار مقابل الريال اليوم")
    assert res["platforms"][0]["title"] == "python-telegram-bot/python-telegram-bot"


# ---------------- R-827 ----------------
def test_r827_stat_intent_and_worldbank(monkeypatch):
    a = sp.analyze("كم عدد سكان اليابان", "How many people live in Japan", "ar")
    assert "stat" in a["kinds"] and a["stats"] == ["SP.POP.TOTL"]
    assert sp.analyze("ما هو الناتج المحلي للسعودية", "What is the GDP of Saudi Arabia", "ar")["stats"] == ["NY.GDP.MKTP.CD"]
    assert sp.analyze("كم عدد السكان", "population", "ar")["stats"] == []  # بلا دولة لا إحصاء
    body = [{"page": 1}, [{"date": "2025", "value": None, "country": {"value": "Japan"}},
                          {"date": "2024", "value": 123975371, "country": {"value": "Japan"}}]]
    _mock(monkeypatch, lambda req: httpx.Response(200, json=body))
    src = sp.instant_worldbank(["JP"], ["SP.POP.TOTL"], "ar")[0]
    assert "123,975,371" in src["fact_text"] and "2024" in src["fact_text"] and src["provider"] == "instant-stat"
    names = [n for n, *_ in sp.instant_jobs(a, "كم عدد سكان اليابان", None, "ar")]
    assert "instant-stat" in names


def test_r827_wb_value_format():
    assert sp._wb_value("NY.GDP.MKTP.CD", 1.28e12, "ar") == "1.28 تريليون دولار"
    assert sp._wb_value("FP.CPI.TOTL.ZG", 14.08, "en") == "14.1%"


def test_r827_archive_and_naver(monkeypatch):
    docs = {"response": {"docs": [{"identifier": "muq", "title": "Muqaddimah", "year": "1958", "creator": ["Ibn Khaldun"],
                                   "downloads": 1200}]}}
    _mock(monkeypatch, lambda req: httpx.Response(200, json=docs))
    out = sp.p_archive("ibn khaldun", "en")
    assert out[0]["url"] == "https://archive.org/details/muq" and out[0]["kind"] == "book"
    html = ('<a href="https://www.visitseoul.net/">Visit Seoul 새 창 열림</a><a href="https://blog.naver.com/x">블로그 글 제목</a>'
            '<a href="https://www.navercorp.com/">© NAVER Corp.</a><a href="https://news.example.kr/1">서울 여행 가이드 기사</a>')
    got = sp.parse_naver(html)
    assert [g["url"] for g in got] == ["https://www.visitseoul.net/", "https://news.example.kr/1"]
    a = sp.analyze("أفضل كتب ابن خلدون", "Best books by Ibn Khaldun", "ar")
    names = [n for n, *_ in sp.platform_jobs(a, {"ar": "x", "en": "Best books by Ibn Khaldun", "ko": "서울"}, "ar",
                                             w.keyword_query, w.scholarly_query)]
    assert "archive" in names and "naver" in names


def test_r827_numeric_check():
    assert w.extract_quantities("يبلغ عدد سكان اليابان 123.8 مليون نسمة عام 2024") == [(123800000.0, "نسمة")]
    assert w.extract_quantities("التضخم ٣٫٥٪") == [(3.5, "%")]
    ok = w.numeric_check([{"text": "عدد السكان 123.8 مليون نسمة", "source": 1},
                          {"text": "يبلغ عدد السكان 124 مليون نسمة", "source": 2}])
    assert ok["kind"] == "consensus" and ok["sources"] == [1, 2]
    bad = w.numeric_check([{"text": "عدد السكان 100 مليون نسمة", "source": 1},
                           {"text": "عدد السكان 140 مليون نسمة", "source": 2}])
    assert bad["kind"] == "conflict"
    assert w.numeric_check([{"text": "السكان 100 مليون نسمة", "source": 1}, {"text": "المساحة 377 ألف كم", "source": 2}]) is None
    txt = w.format_reply({"ok": True, "points": [{"text": "x", "source": 1}], "sources": [], "news": [],
                          "numeric_check": ok, "languages": ["ar"], "question": "q", "method": "m"})
    assert "تحقق الأرقام" in txt


# ---------------- R-828 ----------------
def _wiki(sents):
    return lambda q, lang: [{"title": "W", "url": f"https://{lang}.wikipedia.org/wiki/X{i}", "snippet": "", "text": t,
                             "provider": f"wikipedia-{lang}", "lang": lang} for i, t in enumerate(sents)] \
        if lang == "ar" else []


def test_r828_entity_focus_drops_other_entity(platform_world, monkeypatch):
    monkeypatch.setattr(w, "translate", lambda text, target, source="auto": (text, "fake"))
    monkeypatch.setattr(sp, "platform_jobs", lambda *a, **k: [])
    monkeypatch.setattr(w, "_p_wikidata", lambda q, lang: [{
        "title": "برج خليفة — Wikidata Q12495", "url": "https://www.wikidata.org/wiki/Q12495", "snippet": "", "text": "",
        "provider": "wikidata", "lang": "ar", "facts": [], "fact_text": "الارتفاع (برج خليفة): 828 م", "entity": "برج خليفة"}])
    monkeypatch.setattr(w, "_p_wikipedia", _wiki([
        "يبلغ ارتفاع برج خليفة 828 مترا وهو أطول برج في العالم منذ افتتاحه.",
        "يبلغ ارتفاع برج جدة المخطط ألف متر وهو أطول برج في العالم عند اكتماله."]))
    res = w.answer("كم يبلغ ارتفاع برج خليفة في العالم")
    texts = " ".join(p["text"] for p in res["points"])
    assert "برج جدة" not in texts and "828" in texts


def test_r828_stat_requires_country_mention(platform_world, monkeypatch):
    monkeypatch.setattr(w, "translate", lambda text, target, source="auto": (text, "fake"))
    monkeypatch.setattr(sp, "platform_jobs", lambda *a, **k: [])
    monkeypatch.setattr(sp, "instant_jobs", lambda *a, **k: [])
    monkeypatch.setattr(w, "_p_wikipedia", _wiki([
        "بلغ معدل التضخم السنوي في مصر نحو أربعة عشر بالمئة وفق البيانات الرسمية الأخيرة.",
        "التضخم هو المعدل الذي ترتفع به أسعار السلع والخدمات مع مرور الوقت في الاقتصاد."]))
    res = w.answer("معدل التضخم في مصر")
    texts = " ".join(p["text"] for p in res["points"])
    assert "مصر" in texts and "مع مرور الوقت" not in texts


def test_r828_list_intent_and_medlineplus(monkeypatch):
    a = sp.analyze("ما هي أعراض فقر الدم", "What are the symptoms of anemia", "ar")
    assert a["answer_type"] == "list" and "scholarly" in a["kinds"]
    assert sp.type_bonus("Symptoms include fatigue, pale skin, and dizziness", "list") == 1.0
    xml = ('<nlmSearchResult><list><document rank="0" url="https://medlineplus.gov/anemia.html">'
           '<content name="title">&lt;span&gt;Anemia&lt;/span&gt;</content>'
           '<content name="FullSummary">&lt;p&gt;Symptoms include:&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Fatigue&lt;/li&gt;'
           '&lt;li&gt;Dizziness&lt;/li&gt;&lt;/ul&gt;</content></document>'
           '<document rank="1" url="https://medlineplus.gov/crohnsdisease.html"><content name="title">Crohn</content>'
           '<content name="FullSummary">&lt;p&gt;Crohn text.&lt;/p&gt;</content></document></list></nlmSearchResult>')
    _mock(monkeypatch, lambda req: httpx.Response(200, text=xml))
    out = sp.p_medlineplus("symptoms anemia", "en")
    assert [o["url"] for o in out] == ["https://medlineplus.gov/anemia.html"]
    assert "Fatigue, Dizziness" in out[0]["text"]
    names = [n for n, *_ in sp.platform_jobs(a, {"ar": "x", "en": "What are the symptoms of anemia"}, "ar",
                                             w.keyword_query, w.scholarly_query)]
    assert "medlineplus" in names


def test_r828_weather_city_with_country(monkeypatch):
    seen = []

    def h(req):
        seen.append(str(req.url))
        return httpx.Response(200, json={"current_condition": [{"temp_C": "31", "weatherDesc": [{"value": "Severe sandstorm"}]}],
                                         "weather": [{}], "nearest_area": [{"areaName": [{"value": "Riyadh"}]}]})
    _mock(monkeypatch, h)
    a = sp.analyze("طقس الرياض اليوم", "Riyadh weather today", "ar", True)
    (name, fn, args), = sp.instant_jobs(a, "طقس الرياض اليوم", "Riyadh weather today", "ar")
    fact = fn(*args)[0]["fact_text"]
    assert "Riyadh%2CSaudi%20Arabia" in seen[0] and "عاصفة رملية شديدة" in fact


def test_r828_citation_marks_removed():
    out = w.sentences("اخترع ألكسندر جراهام بيل الهاتف عام 1876 وسجل براءة اختراعه[12] في الولايات المتحدة[citation needed].")
    assert out and "[" not in out[0]


def test_r828c_medlineplus_is_direct_medical_reference(monkeypatch):
    res = {"ok": True, "method": "test", "question": "ما هي أعراض فقر الدم", "fresh": False, "intent": {"label_ar": "قائمة"},
           "points": [{"text": "فقر الدم: الأعراض تشمل التعب والدوخة.", "source": 1, "instant": True,
                       "authority": "medical"}, {"text": "جملة داعمة.", "source": 2}],
           "sources": [{"n": 1, "title": "Anemia — MedlinePlus", "url": "https://medlineplus.gov/anemia.html", "credibility_label": "مرجع"},
                       {"n": 2, "title": "x", "url": "https://e.org", "credibility_label": "عام"}]}
    out = w.format_reply(res)
    assert "الإجابة المباشرة (مرجع طبي موثوق):" in out and "بيانات حية" not in out


def test_r828d_health_terms_detected_without_false_positives():
    assert "scholarly" in sp.analyze("ما أسباب الصداع النصفي", "", "ar")["kinds"]
    assert "scholarly" in sp.analyze("أعراض الحساسية", "", "ar")["kinds"]
    for q in ("عواصم العالم", "حملة تسويق", "عدد سكان العالم"):
        assert "scholarly" not in sp.analyze(q, "", "ar")["kinds"], q


def test_r828d_platform_titles_must_name_the_topic(monkeypatch):
    assert not sp.title_covers("Is snake venom safe to drink?", "symptoms anemia")
    assert sp.title_covers("How is anemia usually diagnosed?", "symptoms anemia")
    assert sp.title_covers("How does OnePlus 13 compare with Samsung/iPhone?", "compare iphone samsung")
    assert not sp.title_covers("Samsung 2nm node in mass production", "compare iphone samsung")
    _mock(monkeypatch, lambda req: httpx.Response(200, json={"items": [
        {"question_id": 1, "title": "Is snake venom safe?", "excerpt": "x"},
        {"question_id": 2, "title": "How is anemia diagnosed?", "excerpt": "y"}]}))
    assert [o["url"] for o in sp.p_stackexchange_site("symptoms anemia", "medicalsciences")] == \
        ["https://medicalsciences.stackexchange.com/q/2"]


def test_r828d_medlineplus_labelled_as_official_medical_reference():
    cred, label = w.credibility("https://medlineplus.gov/anemia.html", True)
    assert cred == 1.0 and "مرجع طبي رسمي" in label
    assert w.credibility("https://doi.org/10.1/x", True)[1] == "بحث علمي محكّم"


def test_r828d_keyword_query_keeps_concept_qualifiers():
    assert w.keyword_query("What are the symptoms of vitamin D deficiency", "en") == "symptoms vitamin D deficiency"
    assert w.keyword_query("Compare iPhone 16 and Galaxy S25", "en") == "Compare iPhone 16 Galaxy S25"
    assert w.keyword_query("What is 5G", "en") == "5G"
    assert w.keyword_query("I am a teacher", "en") == "teacher"


def test_r828d_breaker_pauses_repeated_failures_and_priority_first(monkeypatch):
    monkeypatch.setenv("WORLD_SEARCH_BREAKER_TEST", "1")
    monkeypatch.setattr(w, "_BREAKER", {})
    calls = []

    def bad():
        calls.append("bad")
        raise RuntimeError("bot challenge")

    for _ in range(3):
        w._run_parallel([("dead", bad, ())], time.monotonic() + 5)
    _, st = w._run_parallel([("dead", bad, ()), ("ok", lambda: [1], ())], time.monotonic() + 5)
    assert len(calls) == 3 and st["dead"].startswith("متوقف مؤقتًا") and st["ok"] == "ok (1)"
    assert w._BREAKER["dead"][0] == 3
    monkeypatch.setattr(w, "_BREAKER", {"dead": (3, time.time() - 601)})  # بعد التبريد يُجرَّب من جديد
    w._run_parallel([("dead", bad, ())], time.monotonic() + 5)
    assert len(calls) == 4
    order = []
    w._run_parallel([("lemmy", lambda: order.append("lemmy") or [], ()),
                     ("medlineplus", lambda: order.append("medlineplus") or [], ())], time.monotonic() + 5)
    assert set(order) == {"lemmy", "medlineplus"}
    jobs = sorted([("lemmy", 0, ()), ("medlineplus", 0, ()), ("instant-weather", 0, ())],
                  key=lambda j: 0 if j[0].startswith(w._PRIORITY_PREFIXES) else 1)
    assert [j[0] for j in jobs][-1] == "lemmy"


def test_r828e_medlineplus_topic_query_and_no_random_fallback(monkeypatch):
    seen = []
    xml = ('<nlmSearchResult><list><document rank="0" url="https://medlineplus.gov/uterinefibroids.html">'
           '<content name="title">Uterine Fibroids</content><content name="FullSummary">x</content>'
           '</document></list></nlmSearchResult>')

    def h(req):
        seen.append(req.url.params.get("term"))
        return httpx.Response(200, text=xml)
    _mock(monkeypatch, h)
    assert sp.p_medlineplus("symptoms vitamin D deficiency", "en") == []
    assert seen == ["vitamin D deficiency"]


def test_r828e_breaker_ignores_quality_rejections(monkeypatch):
    monkeypatch.setenv("WORLD_SEARCH_BREAKER_TEST", "1")
    monkeypatch.setattr(w, "_BREAKER", {})

    def rejected():
        raise RuntimeError("bing: نتائج غير مطابقة للسؤال — رُفضت")
    for _ in range(4):
        _, st = w._run_parallel([("bing-ar", rejected, ())], time.monotonic() + 5)
    assert st["bing-ar"].startswith("فشل") and "bing-ar" not in w._BREAKER
