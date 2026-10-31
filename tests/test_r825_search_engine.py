"""R-825 — محرك البحث المطوَّر: مزودات تعمل من السحابة (Bing/أخبار Bing/أخبار Google/OpenAlex/
Stack Overflow/HN)، نية الحداثة، ميزانية زمنية حقيقية، حارس جودة النتائج، الفهرس الذاتي
والذاكرة المؤقتة في Supabase، وواجهة البحث. كل الاختبارات بلا شبكة (نقل httpx وهمي/حقن).
"""

import base64
import json
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import config  # noqa: E402
import search_index  # noqa: E402
import world_search as w  # noqa: E402


def _now_rfc(hours_ago=0):
    from email.utils import formatdate
    return formatdate(time.time() - hours_ago * 3600, usegmt=True)


def _ck(url):
    return ("https://www.bing.com/ck/a?!&amp;&amp;p=abc&amp;u=a1"
            + base64.urlsafe_b64encode(url.encode()).decode().rstrip("=") + "&amp;ntb=1")


BING_HTML = (
    '<html><ol id="b_results"><li class="b_algo" data-id="1"><div class="b_tpcn"></div>'
    f'<h2><a href="{_ck("https://www.kitco.com/charts/gold")}" h="ID=SERP">Price of <strong>Gold</strong> Per Ounce</a></h2>'
    '<div class="b_caption"><p class="b_lineclamp2"><span class="news_dt">14 hours ago</span>&ensp;&#0183;&ensp;'
    'Live gold price charts from international gold markets in New York and London …</p></div></li>'
    '<li class="b_algo"><h2><a href="https://tradingeconomics.com/commodity/gold">Gold - Price - Chart</a></h2>'
    '<div class="b_caption"><p>Gold fell to 3,875.84 USD/t.oz on October 30, 2026, down 3.62% from the previous day.</p>'
    '</div></li></ol></html>')


def _transport(routes):
    def handler(request):
        for key, (status, body, ctype) in routes.items():
            if key in str(request.url):
                return httpx.Response(status, text=body, headers={"content-type": ctype})
        return httpx.Response(404, text="")
    return httpx.MockTransport(handler)


# ---------- Bing ----------
def test_bing_real_url_decodes_base64_redirect():
    assert w._bing_real_url(_ck("https://www.kitco.com/charts/gold")) == "https://www.kitco.com/charts/gold"
    assert w._bing_real_url("http://www.bing.com/news/apiclick.aspx?ref=FexRss&url=https%3a%2f%2fx.com%2fa") == "https://x.com/a"
    assert w._bing_real_url("https://example.org/p") == "https://example.org/p"


def test_parse_bing_html_extracts_title_real_url_snippet_and_date():
    out = w.parse_bing_html(BING_HTML, "en")
    assert [r["url"] for r in out] == ["https://www.kitco.com/charts/gold", "https://tradingeconomics.com/commodity/gold"]
    assert out[0]["title"] == "Price of Gold Per Ounce"
    assert out[0]["snippet"].startswith("Live gold price charts") and not out[0]["snippet"].endswith("…")
    assert w.age_days(out[0]["published"]) == pytest.approx(14 / 24, abs=0.05)
    assert "3,875.84" in out[1]["snippet"] and out[1]["published"] is None
    assert out[0]["rank"] == 0 and out[1]["rank"] == 1


def test_p_bing_uses_html_then_rejects_unrelated_results(monkeypatch):
    monkeypatch.setattr(w, "_plain_client", lambda timeout=None: httpx.Client(
        transport=_transport({"bing.com/search": (200, BING_HTML, "text/html")})))
    res = w._p_bing("gold price", "en")
    assert len(res) == 2 and res[0]["provider"] == "bing"
    # IP مقيَّد يعيد صفحات سياحة لسؤال حمية ⇒ الدفعة تُرفض وتُعلن بدل قراءتها
    with pytest.raises(RuntimeError, match="غير مطابقة"):
        w._p_bing("diet weight loss", "en")


def test_results_match_query_ratio():
    good = [{"title": "Gold price today", "snippet": ""}, {"title": "x", "snippet": "y"}]
    bad = [{"title": "France tourism", "snippet": "Paris"}] * 5
    assert w.results_match_query(good, "gold price", "en")
    assert not w.results_match_query(bad, "gold price", "en")


# ---------- RSS الأخبار ----------
def _rss(items):
    return "<rss><channel>" + "".join(items) + "</channel></rss>"


def test_bing_news_rss_gives_direct_article_and_date(monkeypatch):
    item = ("<item><title>Gold slides 3% to one-year low</title><link>http://www.bing.com/news/apiclick.aspx?"
            "ref=FexRss&amp;url=https%3a%2f%2fwww.reuters.com%2fmarkets%2fgold&amp;c=1</link>"
            "<description>Spot gold fell 3% on Friday as the dollar firmed and yields rose sharply.</description>"
            f"<pubDate>{_now_rfc(2)}</pubDate><News:Source>Reuters</News:Source></item>")
    monkeypatch.setattr(w, "_plain_client", lambda timeout=None: httpx.Client(
        transport=_transport({"bing.com/news/search": (200, _rss([item]), "application/xml")})))
    out = w._p_bing_news("gold price", "en")
    assert out[0]["url"] == "https://www.reuters.com/markets/gold"
    assert out[0]["site"] == "Reuters" and out[0]["news"] is True
    assert out[0]["text"].startswith("Gold slides 3%") and "Spot gold fell" in out[0]["text"]
    assert w.age_days(out[0]["published"]) < 0.2


def test_google_news_rss_strips_publisher_suffix(monkeypatch):
    item = ("<item><title>أسعار الذهب في السعودية اليوم - عاجل</title><link>https://news.google.com/rss/articles/X?oc=5</link>"
            f"<pubDate>{_now_rfc(4)}</pubDate><source url=\"https://ajel.sa\">عاجل</source></item>")
    seen = {}

    def factory(timeout=None):
        def handler(req):
            seen["url"] = str(req.url)
            return httpx.Response(200, text=_rss([item]), headers={"content-type": "application/xml"})
        return httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(w, "_plain_client", factory)
    out = w._p_google_news("سعر الذهب", "ar")
    assert out[0]["title"] == "أسعار الذهب في السعودية اليوم" and out[0]["site"] == "عاجل"
    assert "gl=SA" in seen["url"] and "hl=ar" in seen["url"]


def test_parse_date_variants():
    assert w.parse_date("") is None and w.parse_date("garbage") is None
    assert w.age_days(w.parse_date("3 days ago")) == pytest.approx(3, abs=0.01)
    assert w.parse_date("Sat, 31 Oct 2026 05:55:00 GMT") == "2026-10-31T05:55:00Z"
    assert w.parse_date("2024-05-01T10:00:00Z") == "2024-05-01T10:00:00Z"


def test_openalex_abstract_rebuilt_from_inverted_index():
    inv = {"Gold": [0], "prices": [1], "fell": [2], "sharply": [3]}
    assert w._openalex_abstract(inv) == "Gold prices fell sharply"
    assert w._openalex_abstract(None) == ""


# ---------- النوايا والحداثة ----------
@pytest.mark.parametrize("q,expected", [
    ("أسعار الذهب اليوم في السعودية", True), ("latest iPhone release", True), ("كم سعر الدولار", True),
    ("ما هو افضل دايت لشخص وزنه 90 كيلو وكم سعرات", False), ("ما عاصمة اليابان", False),
    ("what is heart rate", False), ("شخص آخر", False)])
def test_is_fresh(q, expected):
    assert w.is_fresh(q) is expected


def test_is_tech():
    assert w.is_tech("how to fix python ModuleNotFoundError")
    assert not w.is_tech("ما عاصمة اليابان")


def test_freshness_decays():
    assert w.freshness(w._iso(time.time()), 30) == pytest.approx(1.0, abs=0.01)
    assert w.freshness(w._iso(time.time() - 15 * 86400), 30) == pytest.approx(0.5, abs=0.01)
    assert w.freshness(None) == 0.0


def test_evaluate_fresh_mode_prefers_recent_source():
    q = {"en": w._terms("gold price saudi arabia", "en")}
    cands = [
        {"text": "The gold price in Saudi Arabia was historically tied to oil revenues and trade in the old souks.",
         "lang": "en", "source_idx": 0, "cred": 0.8, "fresh": 0.0},
        {"text": "The gold price in Saudi Arabia fell today to 408 riyals per gram for 21 karat after a global drop.",
         "lang": "en", "source_idx": 1, "cred": 0.6, "fresh": 1.0}]
    top = w.evaluate([dict(c) for c in cands], q, None, top_k=1, fresh_mode=True)
    assert top[0]["source_idx"] == 1


# ---------- الميزانية الزمنية الحقيقية ----------
def test_run_parallel_enforces_deadline_without_waiting_for_slow_provider():
    t0 = time.monotonic()
    res, st = w._run_parallel([("fast", lambda: [1], ()), ("slow", lambda: time.sleep(3) or [2], ())],
                              time.monotonic() + 1.0)
    assert time.monotonic() - t0 < 2.0  # قبل R-825 كان ينتظر ٣ ث كاملة
    assert res == {"fast": [1]} and st["slow"] == "تجاوز المهلة"
    assert w.engine_status()["providers_last_run"]["slow"]["status"] == "تجاوز المهلة"


# ---------- الخط الكامل: سؤال آني ----------
@pytest.fixture
def fresh_world(monkeypatch):
    w._TR_CACHE.clear()
    w._TR_DEAD.clear()
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", True)
    monkeypatch.setenv("WORLD_SEARCH_LANGS", "en")
    monkeypatch.setenv("WORLD_SEARCH_INDEX_ENABLED", "false")
    tr = {"أسعار الذهب اليوم في السعودية": "gold prices today in Saudi Arabia"}
    monkeypatch.setattr(w, "translate", lambda text, target, source="auto": (tr.get(text, text), "fake"))
    now2 = w._iso(time.time() - 2 * 3600)
    monkeypatch.setattr(w, "_p_bing_news", lambda q, lang: [{
        "title": "Gold prices in Saudi Arabia drop today", "url": f"https://news.example.com/{lang}/gold",
        "snippet": "Gold prices in Saudi Arabia dropped today, with 21 karat gold at 408 riyals per gram.",
        "text": "Gold prices in Saudi Arabia drop today. Gold prices in Saudi Arabia dropped today, with 21 karat "
                "gold at 408 riyals per gram.", "provider": "bing-news", "lang": lang, "published": now2,
        "news": True, "site": "Example News", "rank": 0}] if lang == "en" else [])
    monkeypatch.setattr(w, "_p_google_news", lambda q, lang: [{
        "title": "أسعار الذهب في السعودية اليوم تتراجع", "url": "https://news.google.com/rss/articles/A",
        "snippet": "", "text": "أسعار الذهب في السعودية اليوم تتراجع", "provider": "google-news", "lang": lang,
        "published": now2, "news": True, "site": "عاجل", "rank": 0}] if lang == "ar" else [])
    monkeypatch.setattr(w, "_p_wikipedia", lambda q, lang: [{
        "title": "Gold", "url": f"https://{lang}.wikipedia.org/wiki/Gold", "snippet": "", "lang": lang,
        "provider": f"wikipedia-{lang}",
        "text": "Gold prices in Saudi Arabia were historically set in the traditional souks of Jeddah and Riyadh."}]
        if lang == "en" else [])
    for name in ("_p_bing", "_p_duckduckgo", "_p_marginalia", "_p_pubmed", "_p_europepmc", "_p_openalex",
                 "_p_stackexchange", "_p_hackernews"):
        monkeypatch.setattr(w, name, lambda q, lang: [])
    monkeypatch.setattr(w, "_p_wikidata", lambda q, lang: [])
    monkeypatch.setattr(w, "_p_index", lambda terms, lang, fresh=False: [])
    import web_tools
    monkeypatch.setattr(web_tools, "fetch", lambda url, timeout=None: {"text": ""})


def test_fresh_answer_has_dated_news_and_recent_point_first(fresh_world):
    res = w.answer("أسعار الذهب اليوم في السعودية")
    assert res["ok"] and res["fresh"] is True
    assert "408" in res["points"][0]["original"]  # الخبر الحديث يغلب نص الموسوعة التاريخي
    assert res["points"][0]["published"]
    assert {n["site"] for n in res["news"]} >= {"عاجل"}
    # كل خبر مستشهد بمصدر حقيقي في قائمة المصادر
    urls = {s["n"]: s["url"] for s in res["sources"]}
    assert all(urls[n["source"]] == n["url"] for n in res["news"])
    text = w.format_reply(res)
    assert "أحدث العناوين المطابقة" in text and "منذ ساعتين" in text and "سؤال آني" in text


def test_answer_returns_cached_payload_without_searching(fresh_world, monkeypatch):
    monkeypatch.setenv("WORLD_SEARCH_INDEX_ENABLED", "true")
    monkeypatch.setattr(search_index, "cache_get", lambda key: {"ok": True, "points": [{"text": "x"}], "cached": True})
    monkeypatch.setattr(w, "_p_bing_news", lambda q, lang: (_ for _ in ()).throw(AssertionError("لا بحث")))
    res = w.answer("أسعار الذهب اليوم في السعودية")
    assert res["cached"] is True and res["ok"]


def test_answer_stores_pages_and_caches_with_short_ttl_for_fresh(fresh_world, monkeypatch):
    stored, cached = [], []
    monkeypatch.setattr(search_index, "store_pages_async", lambda srcs: stored.extend(srcs))
    monkeypatch.setattr(search_index, "cache_put_async", lambda k, p, ttl: cached.append(ttl))
    monkeypatch.setattr(search_index, "cache_get", lambda key: None)
    w.answer("أسعار الذهب اليوم في السعودية")
    assert any(s.get("news") for s in stored) and cached == [900]


def test_search_results_interleaves_providers(monkeypatch):
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", True)
    monkeypatch.setattr(w, "_p_bing", lambda q, lang: [{"title": f"B{i}", "url": f"https://b.com/{i}", "snippet": "s",
                                                        "provider": "bing", "lang": lang} for i in range(3)])
    monkeypatch.setattr(w, "_p_index", lambda terms, lang, fresh=False: [
        {"title": "I0", "url": "https://i.com/0", "text": "t", "provider": "index", "lang": lang}])
    for name in ("_p_duckduckgo", "_p_marginalia", "_p_wikipedia", "_p_google_news", "_p_bing_news"):
        monkeypatch.setattr(w, name, lambda q, lang: [])
    res = w.search_results("history of the ottoman empire")
    assert [r["title"] for r in res["results"]][:3] == ["B0", "I0", "B1"]
    assert res["results"][0]["provider"] == "bing" and res["fresh"] is False


# ---------- الفهرس الذاتي والذاكرة المؤقتة ----------
def test_index_disabled_without_supabase(monkeypatch):
    monkeypatch.setenv("WORLD_SEARCH_INDEX_ENABLED", "false")
    assert not search_index.enabled()
    assert search_index.store_pages([{"url": "https://a.com", "text": "x" * 200}]) == 0
    assert search_index.query(["gold"]) == [] and search_index.cache_get("k") is None
    assert search_index.status()["enabled"] is False


@pytest.fixture
def fake_supabase(monkeypatch):
    calls = []
    store = {}

    def handler(req):
        body = json.loads(req.content or b"null") if req.content else None
        calls.append((req.method, req.url.path, dict(req.url.params), body))
        if req.url.path == "/rest/v1/rpc/search_pages_query":
            return httpx.Response(200, json=[{"url": "https://k.com/g", "title": "Gold", "lang": "en",
                                              "provider": "bing", "body": "gold body", "published_at": None,
                                              "fetched_at": "2026-10-31T00:00:00Z", "rank": 0.3}])
        if req.url.path == "/rest/v1/search_cache" and req.method == "POST":
            store[body["key"]] = body
            return httpx.Response(201)
        if req.url.path == "/rest/v1/search_cache" and req.method == "GET":
            key = req.url.params["key"][3:]
            row = store.get(key)
            return httpx.Response(200, json=[{"payload": row["payload"], "created_at": row["created_at"],
                                              "ttl_seconds": row["ttl_seconds"]}] if row else [])
        return httpx.Response(201)
    monkeypatch.setenv("WORLD_SEARCH_INDEX_ENABLED", "true")
    monkeypatch.setattr(search_index, "enabled", lambda: True)
    monkeypatch.setattr(search_index, "_client", lambda timeout=4.0: httpx.Client(
        base_url="https://sb.example", transport=httpx.MockTransport(handler)))
    return calls, store


def test_index_store_filters_and_upserts(fake_supabase):
    calls, _ = fake_supabase
    n = search_index.store_pages([
        {"url": "https://a.com/1", "title": "A", "text": "gold " * 40, "provider": "bing", "lang": "en"},
        {"url": "https://a.com/1", "title": "dup", "text": "gold " * 40},
        {"url": "https://a.com/short", "text": "short"},
        {"url": "https://i.com/x", "text": "y " * 100, "provider": "index"}])
    assert n == 1
    method, path, _, body = calls[-1]
    assert method == "POST" and path == "/rest/v1/search_pages" and body[0]["url"] == "https://a.com/1"


def test_index_query_sanitizes_terms_and_maps_rows(fake_supabase):
    calls, _ = fake_supabase
    rows = search_index.query(["gold", "Gold", "x", "price;drop", "سعر"], limit=5, max_age_days=2)
    assert calls[-1][3] == {"terms": ["gold", "سعر"], "lim": 5, "max_age_days": 2}
    assert rows[0]["provider"] == "index" and rows[0]["text"] == "gold body"


def test_cache_roundtrip_and_ttl(fake_supabase):
    key = search_index.cache_key("سعر الذهب", "ar")
    assert key == search_index.cache_key("  سعر   الذهب؟ ", "ar") and key != search_index.cache_key("سعر الذهب", "en")
    assert search_index.cache_put(key, {"ok": True, "points": [1]}, 600)
    hit = search_index.cache_get(key)
    assert hit["cached"] is True and hit["points"] == [1]
    search_index.cache_put(key, {"ok": True, "points": [2]}, 0)
    assert search_index.cache_get(key) is None
    assert not search_index.cache_put("k2", {"ok": False}, 600)  # فشل لا يُحفظ


def test_sql_migration_defines_index_cache_and_rpc():
    sql = (ROOT / "infra" / "supabase" / "r825_search_index.sql").read_text(encoding="utf-8")
    for needle in ("create table if not exists public.search_pages", "using gin (fts)",
                   "create table if not exists public.search_cache", "function public.search_pages_query",
                   "enable row level security"):
        assert needle in sql


# ---------- الربط بالتطبيق والواجهة ----------
def test_search_status_tool_registered():
    from tool_registry import get_registry
    import app  # noqa: F401 — يسجل الأدوات
    names = {t["name"] for t in get_registry().list_tools()}
    assert {"search.status", "world.answer", "web.search"} <= names
    st = get_registry().invoke("search.status", caller="test", inputs={})
    assert st["ok"] and "index" in st["result"] and "bing" in st["result"]["providers"]


def test_frontend_search_panel_renders_answers_and_status():
    html = (ROOT / "frontend" / "chat" / "index.html").read_text(encoding="utf-8")
    for needle in ('id="aBtn"', 'id="stBtn"', 'id="sList"', 'tool("world.answer"', 'tool("search.status"',
                   "function renderAnswer", "function renderResults", "noopener noreferrer"):
        assert needle in html
