# -*- coding: utf-8 -*-
"""R-839: تقوية الربط بين أدوات البحث ومحركاته ووكلائه.

قبل R-839 كانت أداة web.search (عبر world_search.search_results) تمر بمسار أنحف
من محرك البحث الكامل: بلا تحليل نية (لا منصات YouTube/GitHub/أبحاث حسب المطلوب)،
بلا محركات ddgs المتعددة، وبدمج تبادلي أعمى بدل دمج metasearch2 الموزون.
الاختبارات بلا شبكة: المزودات وهمية عبر monkeypatch.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import world_search as w  # noqa: E402
from search_agents import metasearch  # noqa: E402


def _capture_jobs(monkeypatch, results_by_name=None):
    """يلتقط أسماء مهام _run_parallel ويعيد نتائج مزيفة لكل اسم مراد."""
    captured = {"names": []}
    real_results = results_by_name or {}

    def _cap(jobs, dl):
        captured["names"].extend(name for name, *_ in jobs)
        return dict(real_results), {n: "ok (mock)" for n, *_ in jobs}
    monkeypatch.setattr(w, "_run_parallel", _cap)
    return captured


def test_search_results_schedules_ddgs_engines(monkeypatch):
    """طبقة المحركات المتعددة (ddgs) جزء من أداة البحث لا من world.answer وحدها."""
    monkeypatch.setenv("WORLD_SEARCH_DDGS", "true")
    monkeypatch.setenv("WORLD_SEARCH_DDGS_ENGINES", "google,yahoo")
    monkeypatch.setenv("WORLD_SEARCH_CACHE", "false")
    cap = _capture_jobs(monkeypatch, {"bing": [{"url": "https://x.com/a", "title": "a"}]})
    out = w.search_results("what is rust programming")
    assert {"ddgs-google", "ddgs-yahoo"} <= set(cap["names"])
    assert out["count"] >= 1


def test_search_results_binds_intent_to_platforms(monkeypatch):
    """نية السؤال تحدد المنصات: سؤال فيديو عربي ⇒ مهمة YouTube لا صفحات نص فقط."""
    monkeypatch.setenv("WORLD_SEARCH_DDGS", "false")
    cap = _capture_jobs(monkeypatch, {"bing": [{"url": "https://x.com/a", "title": "a"}]})
    w.search_results("أريد فيديو شرح بناء واجهات React")
    assert "youtube" in cap["names"], "سؤال فيديو بلا مهمة YouTube — النية غير مربوطة بالمنصات"


def test_search_results_keeps_news_for_fresh_questions(monkeypatch):
    """السؤال الآني يحتفظ بأخبار Google/Bing (سلوك R-825 محفوظ بعد التقوية)."""
    cap = _capture_jobs(monkeypatch, {"bing": [{"url": "https://x.com/a", "title": "a"}]})
    w.search_results("أخبار الانتخابات الأمريكية اليوم")
    assert "google-news" in cap["names"] and "bing-news" in cap["names"]


def test_search_results_fuse_ranks_engines_agreement_first(monkeypatch):
    """دمج metasearch2: الرابط الذي تتفق عليه محركان يعلو على الأعلى مرتبة من محرك واحد."""
    results = {
        "bing": [{"url": "https://x.com/only-bing", "title": "a"},
                 {"url": "https://x.com/agreed", "title": "b"}],
        "ddgs-yahoo": [{"url": "https://x.com/agreed", "title": "b"}],
    }
    cap = _capture_jobs(monkeypatch, results)
    monkeypatch.setenv("WORLD_SEARCH_DDGS", "true")  # conftest يعطلها افتراضيًا
    monkeypatch.setenv("WORLD_SEARCH_DDGS_ENGINES", "yahoo")
    out = w.search_results("rust programming language")
    urls = [r["url"] for r in out["results"]]
    assert urls.index("https://x.com/agreed") < urls.index("https://x.com/only-bing"), \
        "اتفاق المحركات لا يرفع الرابط — الدمج ما زال تبادليًا"
    agreed = next(r for r in out["results"] if r["url"] == "https://x.com/agreed")
    assert set(agreed["engines"]) == {"bing", "yahoo"} and agreed["score"] > 0
    assert out["results"][0]["score"] >= out["results"][1]["score"]


def test_search_results_reports_intent_kinds(monkeypatch):
    """نية السؤال تعود مع النتائج — الأداة تعلن ما فهمته لا تجمع روابط صامتة."""
    _capture_jobs(monkeypatch, {"bing": [{"url": "https://x.com/a", "title": "a"}]})
    out = w.search_results("أريد فيديو شرح بناء واجهات React")
    assert "video" in out.get("intent_kinds", [])


def test_search_results_fails_honestly_when_all_providers_fail(monkeypatch):
    """كل المزودات فشلت ⇒ خطأ معلن، لا نتائج مختلقة (معيار الصدق)."""
    def _fail(jobs, dl):
        return {}, {name: "فشل (mock)" for name, *_ in jobs}
    monkeypatch.setattr(w, "_run_parallel", _fail)
    with pytest.raises(RuntimeError, match="فشل البحث العالمي"):
        w.search_results("أي سؤال")
