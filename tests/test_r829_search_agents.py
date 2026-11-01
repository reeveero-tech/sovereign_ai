"""R-829: وكلاء ومحركات البحث مفتوحة المصدر المسحوبة في third_party/ — ربطها الفعلي بمحرك البحث.

بلا شبكة: المحركات والترجمة وويكيبيديا وهمية؛ المكتبات المسحوبة (rank_bm25/bm25s/whoosh/trafilatura/
ddgs) حقيقية تعمل من نسختها في المستودع.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import search_agents  # noqa: E402
import world_search as w  # noqa: E402
from search_agents import deep_research as dr  # noqa: E402
from search_agents import metasearch, ranking, reader, vendored  # noqa: E402


# ---------- السجل: ٣٢ مشروعًا، لكل واحد دور صادق ----------
def test_registry_covers_every_vendored_project_with_honest_mode():
    reg = search_agents.registry()
    assert len(reg) == 32
    modes = {c["mode"] for c in reg.values()}
    assert modes == {"runtime", "ported", "source"}
    for repo, c in reg.items():
        assert c["license"] in {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0"}, repo
        assert re.fullmatch(r"[0-9a-f]{40}", c["commit"] or ""), repo
    runtime = {r for r, c in reg.items() if c["mode"] == "runtime"}
    assert runtime == {"deedy5/ddgs", "adbar/trafilatura", "dorianbrown/rank_bm25", "xhluca/bm25s",
                       "Sygil-Dev/whoosh-reloaded"}


def test_runtime_libraries_all_load():
    st = vendored.status()
    assert all(v["loaded"] for v in st.values()), {k: v["error"] for k, v in st.items()}


# ---------- الترتيب: rank_bm25 / bm25s / whoosh ----------
def test_snowball_stems_languages_the_engine_had_no_stemmer_for():
    assert ranking.stem("национальные", "ru") == ranking.stem("национальный", "ru")
    assert ranking.stem("nazionali", "it") == ranking.stem("nazionale", "it")
    assert w._terms("bibliotecas públicas", "pt") == w._terms("biblioteca pública", "pt")
    assert ranking.stem("برج", "ar") == "برج"  # لغة بلا Snowball ⇒ كما هي


def test_top_sentences_finds_answer_beyond_first_sixty_in_page_order():
    sents = [f"filler sentence number {i} about nothing" for i in range(80)]
    sents.insert(70, "The tower height is 828 metres tall")
    out = ranking.top_sentences(sents, ["tower", "height"], lambda s: s.lower().split(), 60)
    assert len(out) == 60 and "The tower height is 828 metres tall" in out
    assert out == [s for s in sents if s in out]  # الترتيب الأصلي محفوظ


def test_rank_passages_uses_bm25s():
    idx = ranking.rank_passages(["cats and dogs", "burj khalifa is tall", "khalifa khalifa"], ["khalifa"],
                                lambda s: s.split(), 2)
    assert idx[0] in (1, 2) and 0 not in idx


# ---------- الدمج: metasearch2 ----------
def test_fuse_matches_metasearch2_formula():
    f = metasearch.fuse([("bing", [{"url": "a"}, {"url": "b"}]), ("ddgs-google", [{"url": "b", "rank": 0}])])
    assert f["a"]["score"] == pytest.approx(1.0)
    assert f["b"]["score"] == pytest.approx(1.0 / 2 + metasearch.WEIGHTS["google"])
    assert f["b"]["engines"] == {"bing", "google"}


def test_ddgs_provider_shapes_results_and_rejects_mismatch(monkeypatch):
    class FakeDDGS:
        def __init__(self, timeout=7):
            pass

        def text(self, q, region, max_results, backend):
            assert region == "xa-ar" and backend == "google"
            return [{"title": "ارتفاع برج خليفة", "href": "https://x.ae/burj", "body": "برج خليفة 828 مترًا"},
                    {"title": "bad", "href": "javascript:0", "body": ""}]
    monkeypatch.setattr(vendored.load("ddgs"), "DDGS", FakeDDGS)
    rows = w._p_ddgs("google")("ارتفاع برج خليفة", "ar")
    assert [r["url"] for r in rows] == ["https://x.ae/burj"] and rows[0]["provider"] == "ddgs-google"
    with pytest.raises(RuntimeError, match="رُفضت"):
        w._p_ddgs("google")("سعر الذهب في الكويت", "ar")


def test_ddgs_no_results_is_rejection_not_outage(monkeypatch):
    class Empty:
        def __init__(self, timeout=7):
            pass

        def text(self, *a, **k):
            raise Exception("No results found.")
    monkeypatch.setattr(vendored.load("ddgs"), "DDGS", Empty)
    with pytest.raises(RuntimeError, match="رُفضت"):
        metasearch.search("brave", "x", "en")


def test_answer_schedules_ddgs_engines_only_when_enabled(monkeypatch):
    monkeypatch.setenv("WORLD_SEARCH_DDGS", "true")
    monkeypatch.setenv("WORLD_SEARCH_DDGS_ENGINES", "google,yandex")
    seen = []
    monkeypatch.setattr(metasearch, "search", lambda eng, q, lang, **k: seen.append((eng, lang)) or [])
    monkeypatch.setattr(w, "_run_parallel", lambda jobs, dl: ({}, {}))
    monkeypatch.setattr(w, "translate", lambda t, target, source="auto": (t, None))
    monkeypatch.setenv("WORLD_SEARCH_CACHE", "false")
    captured = {}
    real = w._run_parallel

    def _cap(jobs, dl):
        captured.setdefault("names", []).extend(n for n, *_ in jobs)
        return {}, {}
    monkeypatch.setattr(w, "_run_parallel", _cap)
    w.answer("what is the height of burj khalifa")
    assert {"ddgs-google", "ddgs-yandex"} <= set(captured["names"])
    assert real is not None


# ---------- القراءة: trafilatura ----------
def test_reader_extracts_main_text_and_date():
    html = ("<html><head><title>Burj</title><meta property='article:published_time' content='2025-03-04'>"
            "</head><body><nav>Home | About | Login</nav><article><h1>Burj Khalifa</h1><p>"
            + "The Burj Khalifa in Dubai is 828 metres tall and has been the tallest building since 2010. " * 3
            + "</p></article><footer>Copyright ads</footer></body></html>")
    out = reader.extract(html, "https://example.com/burj")
    assert out and "828 metres" in out["text"] and "Login" not in out["text"]
    assert out["date"] == "2025-03-04"
    assert reader.extract("plain text", None) is None


# ---------- البحث العميق ----------
def test_decompose_comparison_mindsearch():
    assert dr.decompose("What is the difference between iPhone 16 and Galaxy S24?") == \
        ["What is iPhone 16", "What is Galaxy S24"]
    assert dr.decompose("What is artificial intelligence") == []


def test_evaluation_types_node_deepresearch():
    assert dr.evaluation_types("x", "difference between Python and Java", {}) == ["definitive", "completeness"]
    assert "plurality" in dr.evaluation_types("x", "symptoms of migraine", {"answer_type": "list"})
    assert "freshness" in dr.evaluation_types("أخبار اليوم", "news today", {})


def test_evaluate_turns_gaps_into_follow_up_queries():
    res = [{"points": [{"text": "iPhone 16 has A18 chip", "original": "iPhone 16 has A18 chip", "score": 0.7,
                       "source": 1}]}]
    ev = dr.evaluate("x", "difference between iPhone 16 and Galaxy S24", {"kinds": []},
                     ["definitive", "completeness"], res)
    assert ev["checks"]["definitive"]["pass"] and not ev["checks"]["completeness"]["pass"]
    assert any(g.startswith("Galaxy S24") for g in ev["gaps"])


def _fake_answer(points_by_q):
    def _a(q, lang=None, budget=None):
        pts = points_by_q.get(q, [])
        return {"ok": bool(pts), "question": q, "intent": {"answer_type": "definition"}, "news": [],
                "points": [{"text": t, "original": t, "source": 1, "score": 0.8} for t in pts],
                "sources": [{"n": 1, "url": f"https://src/{abs(hash(q)) % 97}", "title": q}],
                "elapsed_seconds": 1.0}
    return _a


def test_run_breadth_depth_loop_merges_sources_and_dedupes(monkeypatch):
    q = "What is the difference between iPhone 16 and Galaxy S24"
    monkeypatch.setattr(w, "answer", _fake_answer({
        q: ["iPhone 16 uses the A18 chip from Apple"],
        "What is iPhone 16": ["iPhone 16 uses the A18 chip from Apple", "iPhone 16 launched in September 2024"],
        "What is Galaxy S24": [],
        "Galaxy S24 difference iPhone 16 Galaxy S24": ["Galaxy S24 uses Snapdragon 8 Gen 3 processor"],
    }))
    monkeypatch.setattr(dr, "perspectives", lambda *a, **k: {"article": None, "sections": []})
    monkeypatch.setattr(w, "translate", lambda t, target, source="auto": (t, "identity"))
    monkeypatch.setattr(w, "keyword_query", lambda t, lang: "difference iPhone 16 Galaxy S24")
    res = dr.run(q, breadth=3, depth=2)
    assert res["ok"] and res["depth_reached"] == 2
    # dzhng: مستوى التعمق يأخذ حتى ceil(3/2)=2 سؤال متابعة — هنا فجوة واحدة متبقية (Galaxy S24)
    assert res["rounds"][1]["breadth"] == 1 and res["rounds"][1]["questions"][0].startswith("Galaxy S24")
    texts = [p["text"] for s in res["sections"] for p in s["points"]] + [p["text"] for p in res["summary"]]
    assert texts.count("iPhone 16 uses the A18 chip from Apple") == 1  # تنقيح التكرار بين الأقسام
    assert "Galaxy S24 uses Snapdragon 8 Gen 3 processor" in texts  # الفجوة سُدّت بسؤال متابعة
    urls = [s["url"] for s in res["sources"]]
    assert len(urls) == len(set(urls)) and [s["n"] for s in res["sources"]] == list(range(1, len(urls) + 1))
    assert res["evaluation"]["checks"]["completeness"]["pass"]
    assert "تقييم الاكتمال" in dr.format_report(res)


def test_plan_uses_storm_wikipedia_sections(monkeypatch):
    monkeypatch.setattr(w, "translate", lambda t, target, source="auto": ("What is artificial intelligence", "x"))
    monkeypatch.setattr(dr, "perspectives", lambda topic, limit=4, lang="en": {
        "article": "Artificial intelligence", "sections": ["History", "Goals", "Ethics", "Applications"]})
    pl = dr.plan("ما هو الذكاء الاصطناعي", 3)
    assert [s["q"] for s in pl["sub_questions"]] == ["Artificial intelligence History", "Artificial intelligence Goals",
                                                     "Artificial intelligence Ethics"]
    assert pl["spare"] == ["Artificial intelligence Applications"]


def test_plan_live_question_needs_no_sub_questions(monkeypatch):
    monkeypatch.setattr(w, "translate", lambda t, target, source="auto": ("dollar to riyal today", "x"))
    pl = dr.plan("كم سعر الدولار مقابل الريال اليوم", 3)
    assert pl["sub_questions"] == [] and pl["note"]


def test_chat_deep_research_trigger():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
    import app
    assert app._DEEP_RESEARCH.match("بحث عميق: الذكاء الاصطناعي").group(1) == "الذكاء الاصطناعي"
    assert app._DEEP_RESEARCH.match("deep research quantum computing").group(1) == "quantum computing"
    assert not app._DEEP_RESEARCH.match("ما هو البحث العميق")


# ---------- أداة المزامنة: المصدر الوحيد لقائمة المشاريع وبصماتها ----------
def test_vendor_sync_sources_match_registry_and_tree_hash():
    import importlib.util
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("vendor_sync", root / "scripts" / "vendor_sync.py")
    vs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vs)
    assert {r for r, *_ in vs.SOURCES} == set(search_agents.registry())
    import json
    man = {p["repo"]: p for p in json.loads((root / "third_party" / "MANIFEST.json").read_text())["projects"]}
    p = man["dorianbrown/rank_bm25"]
    assert vs.tree_sha256(root / p["path"]) == p["tree_sha256"]
    # مخرجات البناء/التشغيل لا تدخل البصمة (pip install ./third_party/X يبني في مكانه)
    assert vs._generated(root / p["path"], root / p["path"] / "build" / "lib" / "x.py")
    assert vs._generated(root / p["path"], root / p["path"] / "pkg" / "__pycache__" / "x.pyc")
    assert not vs._generated(root / p["path"], root / p["path"] / "rank_bm25.py")
