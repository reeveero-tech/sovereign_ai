"""R-823: البحث العالمي الحتمي بلا نموذج لغوي — اختبارات بلا شبكة (مزودات ومترجمات مزيفة)."""
import pytest

import chat_agent
import config
import ollama_client
import world_search as w


# ---------------- فهم السؤال ----------------
def test_detect_lang_by_script():
    assert w.detect_lang("ما هي عاصمة اليابان") == "ar"
    assert w.detect_lang("What is the capital of Japan") == "en"
    assert w.detect_lang("Какая столица") == "ru"


def test_core_question_strips_request_and_normalizes_colloquial():
    q = "اريد ان تقوم بانشاء بحث معمق عن النظام الغذائي الافضل لمن يرتاد النادي ووزنه 120 كيلو ويريد دايت"
    core = w.core_question(q)
    assert not core.startswith("اريد")
    assert "الصالة الرياضية" in core  # «النادي» في سياق اللياقة ⇒ صالة رياضية لا club
    assert "حمية غذائية" in core and "دايت" not in core
    # «النادي» بلا سياق لياقة يبقى كما هو
    assert "النادي" in w.core_question("متى تأسس النادي الأهلي")


def test_split_subquestions_carries_entity():
    parts = w.split_subquestions("What is the capital of Japan and how many people live there?")
    assert parts == ["What is the capital of Japan", "how many people live there Japan"]
    assert w.split_subquestions("best diet for weight loss") == ["best diet for weight loss"]


def test_scholarly_query_maps_concepts():
    q = w.scholarly_query("The best diet for those who go to the gym and weigh 120 kilos and want to lose weight")
    assert "exercise" in q and "diet" in q and "obesity" in q


# ---------------- الموثوقية والتقييم ----------------
def test_credibility_tiers():
    assert w.credibility("https://www.nhs.uk/x")[0] == 1.0
    assert w.credibility("https://pubmed.ncbi.nlm.nih.gov/1/", scholarly=True)[0] == 1.0
    assert w.credibility("https://uni.edu.sa/x")[0] == 1.0
    assert w.credibility("https://en.wikipedia.org/wiki/X")[0] == 0.8
    assert w.credibility("https://www.reddit.com/r/x")[0] < w.credibility("https://blog.example.com")[0]


def test_evaluate_prefers_relevant_credible_and_rejects_offtopic():
    q = {"en": w._terms("best diet exercise weight loss", "en")}
    cands = [
        {"text": "Combining a calorie restricted diet with regular exercise produces greater weight loss than either alone.",
         "lang": "en", "source_idx": 0, "cred": 1.0},
        {"text": "A balanced diet together with exercise helps adults achieve sustained weight loss over the long term.",
         "lang": "en", "source_idx": 1, "cred": 0.8},
        {"text": "The football club won the national championship fourteen times since it was founded long ago.",
         "lang": "en", "source_idx": 2, "cred": 0.8},
        {"text": "Combining a calorie restricted diet with regular exercise produces greater weight loss than either alone!",
         "lang": "en", "source_idx": 3, "cred": 0.35},
    ]
    chosen = w.evaluate(cands, q, None, top_k=5)
    texts = [c["text"] for c in chosen]
    assert texts[0].startswith("Combining") and chosen[0]["source_idx"] == 0
    assert not any("football" in t for t in texts), "جملة خارج الموضوع لا تدخل الجواب"
    assert len([t for t in texts if t.startswith("Combining")]) == 1, "لا تكرار شبه حرفي"
    assert chosen[0]["agreement"] > 0, "مصدر مستقل آخر يقول المعنى نفسه"


def test_sentences_filters_boilerplate_and_fragments():
    text = ("Skip to main content Search the NHS website. Accept all cookies to continue browsing. "
            "Regular physical activity combined with a healthy diet is the most reliable way to lose weight.")
    out = w.sentences(text)
    assert out == ["Regular physical activity combined with a healthy diet is the most reliable way to lose weight."]


# ---------------- الترجمة ----------------
def test_translate_chain_falls_through(monkeypatch):
    w._TR_CACHE.clear()
    w._TR_DEAD.clear()

    def bad(*a):
        raise RuntimeError("blocked")
    monkeypatch.setattr(w, "TRANSLATORS", (("a", bad), ("b", lambda t, tl, sl: "مرحبا")))
    assert w.translate("hello there", "ar", "en") == ("مرحبا", "b")
    monkeypatch.setattr(w, "TRANSLATORS", (("a", bad),))
    w._TR_CACHE.clear()
    w._TR_DEAD.clear()
    assert w.translate("good morning", "ar", "en") == ("good morning", None)  # فشل معلن لا اختلاق


# ---------------- الخط الكامل بمزودات مزيفة ----------------
@pytest.fixture
def fake_world(monkeypatch):
    w._TR_CACHE.clear()
    w._TR_DEAD.clear()
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", True)
    monkeypatch.setenv("WORLD_SEARCH_ENABLED", "true")
    monkeypatch.setenv("WORLD_SEARCH_LANGS", "en")
    tr = {"النظام الغذائي الافضل لإنقاص الوزن مع التمارين": "best diet for weight loss with exercise"}
    monkeypatch.setattr(w, "translate", lambda text, target, source="auto": (
        (tr.get(text, "[ar] " + text) if target in ("en", "ar") else text), "fake"))
    monkeypatch.setattr(w, "_p_wikipedia", lambda q, lang: [{
        "title": "Dieting", "url": f"https://{lang}.wikipedia.org/wiki/Dieting", "snippet": "", "lang": lang,
        "provider": f"wikipedia-{lang}",
        "text": "A balanced diet together with exercise helps adults achieve sustained weight loss over the long term."}]
        if lang == "en" else [])
    monkeypatch.setattr(w, "_p_pubmed", lambda q, lang: [{
        "title": "Obesity and exercise (Lancet، 2020)", "url": "https://pubmed.ncbi.nlm.nih.gov/1/", "snippet": "",
        "lang": "en", "provider": "pubmed", "scholarly": True,
        "text": "Combining a calorie restricted diet with regular exercise produces greater weight loss than either alone."}])
    monkeypatch.setattr(w, "_p_europepmc", lambda q, lang: (_ for _ in ()).throw(RuntimeError("503")))
    monkeypatch.setattr(w, "_p_duckduckgo", lambda q, lang: [{
        "title": "Football", "url": "https://sports.example.com/club", "snippet": "", "lang": "en",
        "provider": "duckduckgo"}])
    monkeypatch.setattr(w, "_p_marginalia", lambda q, lang: [])
    monkeypatch.setattr(w, "_p_wikidata", lambda q, lang: [])
    import web_tools
    monkeypatch.setattr(web_tools, "fetch", lambda url, timeout=None: {
        "text": "The football club won the national championship fourteen times since it was founded long ago."})


def test_answer_end_to_end_cites_real_sources_and_reports_failures(fake_world):
    res = w.answer("النظام الغذائي الافضل لإنقاص الوزن مع التمارين")
    assert res["ok"] and res["user_lang"] == "ar"
    urls = {s["url"] for s in res["sources"]}
    assert "https://pubmed.ncbi.nlm.nih.gov/1/" in urls
    assert "https://sports.example.com/club" not in urls, "مصدر خارج الموضوع لا يُستشهد به"
    assert res["points"][0]["text"].startswith("[ar] Combining"), "الجواب مترجم إلى لغة السائل"
    assert res["providers"]["europepmc"].startswith("فشل"), "فشل مزود يُعلن"
    reply = w.format_reply(res)
    assert "https://pubmed.ncbi.nlm.nih.gov/1/" in reply and "[1]" in reply
    assert "بلا نموذج لغوي" in reply and "الترجمة آلية" in reply


def test_answer_without_relevant_sources_is_honest(fake_world, monkeypatch):
    monkeypatch.setattr(w, "_p_wikipedia", lambda q, lang: [])
    monkeypatch.setattr(w, "_p_pubmed", lambda q, lang: [])
    res = w.answer("النظام الغذائي الافضل لإنقاص الوزن مع التمارين")
    assert not res["ok"] and res["points"] == []
    assert "لم أجد إجابة موثوقة" in w.format_reply(res)


def test_wikidata_fact_leads_the_answer(fake_world, monkeypatch):
    monkeypatch.setattr(w, "_p_wikidata", lambda q, lang: [{
        "title": "اليابان — Wikidata Q17", "url": "https://www.wikidata.org/wiki/Q17", "snippet": "", "text": "",
        "provider": "wikidata", "lang": "ar", "entity": "اليابان",
        "facts": [{"pid": "P36", "label": "العاصمة", "values": ["طوكيو"]}],
        "fact_text": "العاصمة (اليابان): طوكيو"}])
    res = w.answer("النظام الغذائي الافضل لإنقاص الوزن مع التمارين")
    assert res["points"][0]["structured"] and res["points"][0]["text"] == "العاصمة (اليابان): طوكيو"
    assert res["sources"][0]["url"] == "https://www.wikidata.org/wiki/Q17"


def test_wd_props_detection():
    assert w._wd_props_for("What is the capital of Japan and what is its population") == ["P36", "P1082"]
    assert w._wd_entity_phrase("What is the capital of Japan") == "Japan"


# ---------------- الربط بالمنظومة ----------------
def test_search_configured_and_web_search_dispatch(monkeypatch):
    import chat_tools
    import web_tools
    monkeypatch.setattr(config, "WEB_TOOLS_ENABLED", True)
    monkeypatch.setattr(config, "SEARCH_PROVIDER", "world", raising=False)
    assert chat_tools.search_configured() is True
    assert w.enabled() is True
    monkeypatch.setattr(w, "search_results", lambda q, max_results=10: {"provider": "world", "results": [1]})
    assert web_tools.search("x")["provider"] == "world"


def test_world_answer_registered_in_registry():
    from app import app  # noqa: F401 — يسجل الأدوات
    from tool_registry import get_registry
    assert "world.answer" in {t["name"] for t in get_registry().list_tools()}


def test_chat_brain_unreachable_uses_world_search(monkeypatch):
    import chat_tools
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient
    chat_rate_limiter._requests.clear()
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
    monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: True)
    monkeypatch.setattr(chat_tools, "gather", lambda t, c: {"context": "", "tools_used": [], "direct_reply": None})
    monkeypatch.setattr(w, "enabled", lambda: True)
    monkeypatch.setattr(w, "answer", lambda question, target_lang=None: {
        "ok": True, "points": [{"text": "جواب مستشهد", "source": 1, "translator": "identity", "lang": "ar"}],
        "sources": [{"n": 1, "title": "NHS", "url": "https://www.nhs.uk/x", "credibility_label": "جهة مرجعية",
                     "provider": "duckduckgo"}],
        "languages_searched": ["en"], "sources_considered": 3, "candidates_evaluated": 9,
        "user_lang": "ar", "method": "منهج"})
    with TestClient(fastapi_app) as c:
        body = c.post("/chat", json={"text": "اريد ان تقوم بانشاء بحث معمق عن النظام الغذائي",
                                     "user_id": "t"}).json()
    assert body["agent_status"] == "brain_unreachable_world_search"
    assert body["status"] == "ok"
    assert "جواب مستشهد" in body["reply"] and "https://www.nhs.uk/x" in body["reply"]
    assert "تم تنفيذ القرار" not in body["reply"]
