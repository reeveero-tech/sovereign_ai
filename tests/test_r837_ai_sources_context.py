# -*- coding: utf-8 -*-
"""R-837 — من محادثة إنتاج رابعة أرسلها المالك (أخبار التكنولوجيا والذكاء الاصطناعي):

«ماذا عن اخر اخبار التكنولوجيا والذكاء الاصطناعي؟» بعد خبر تحطم طائرة في فلوريدا
أُجيبت بذكاء اصطناعي في فلوريدا، و«ماذا عن باقي العالم؟» حُلّت إلى
«ما باقي العالم والذكاء الاصطناعي في فلوريدا» — ثلاثة عيوب مترابطة:
(١) تبديل الكيان كان يرث توصيفات الكيان القديم («في فلوريدا») فيلوث الموضوع الجديد؛
(٢) كشف الأسئلة التقنية (is_tech) لا يعرف كلمات «تكنولوجيا/ذكاء اصطناعي» العربية
    فلم تُشغَّل مزودات GitHub وStack Overflow وHackerNews قط لسؤال عربي عن الذكاء الاصطناعي؛
(٣) لا مزود HuggingFace أصلًا — أمر المالك: مصادر الذكاء الاصطناعي الحقيقية GitHub وHuggingFace.
كل الاختبارات بلا شبكة (نقل httpx وهمي) عدا كشف النية الحتمي (محض regex).
"""
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import context_resolver as cr  # noqa: E402
import search_platforms as sp  # noqa: E402
import world_search as w  # noqa: E402


def _mock(monkeypatch, handler):
    def _client(timeout=8.0, headers=None):
        return httpx.Client(transport=httpx.MockTransport(handler), headers=headers or {})
    monkeypatch.setattr(sp, "_http", _client)


def _resolve_chain(questions):
    """سلسلة متابعات كما في المحادثة الحية: كل سؤال يُحل مقابل ما قبله."""
    prev = None
    out = []
    for q in questions:
        r = cr.resolve(q, [{"role": "user", "content": prev}] if prev else None)
        prev = r["standalone"]
        out.append(prev)
    return out


class TestSwapDropsOldModifiers:
    """«ماذا عن X؟» يرث جوهر السؤال قبل الكيان فقط — توصيفات القديم لا تنتقل."""

    def test_production_chain_no_florida_leak(self):
        """حالة الإنتاج حرفيًا: خبر التكنولوجيا لا يبحث «في فلوريدا»."""
        out = _resolve_chain([
            "ما اخر اخبار العالم ؟",
            "ماذا عن سقوط طائرة في فلوريدا ؟",
            "ماذا عن اخر اخبار التكنولوجيا والذكاء الاصطناعي ؟",
        ])
        assert out[1] == "ما سقوط طائرة في فلوريدا"  # التبديل الأول سليم كما كان
        assert out[2] == "ما اخر اخبار التكنولوجيا والذكاء الاصطناعي"  # بلا فلوريدا

    def test_production_rest_of_world_clean(self):
        """«ماذا عن باقي العالم؟» لا يرث موضوع الذكاء الاصطناعي السابق ولا فلوريدا."""
        out = _resolve_chain([
            "ما اخر اخبار العالم ؟",
            "ماذا عن سقوط طائرة في فلوريدا ؟",
            "ماذا عن اخر اخبار التكنولوجيا والذكاء الاصطناعي ؟",
            "ماذا عن باقي العالم ؟",
        ])
        assert out[3] == "ما باقي العالم"  # كانت: «ما باقي العالم والذكاء الاصطناعي في فلوريدا»

    def test_classic_swap_unchanged(self):
        """التبديل الكلاسيكي سليم: «وماذا عن فرنسا؟» بعد عاصمة اليابان ⇒ عاصمة فرنسا."""
        out = _resolve_chain(["ما عاصمة اليابان", "وماذا عن فرنسا؟"])
        assert out[1] == "ما عاصمة فرنسا"

    def test_head_before_entity_preserved(self):
        """جوهر السؤال قبل الكيان يُحفظ: «كم عدد سكان» + كيان جديد."""
        out = _resolve_chain(["كم عدد سكان اليابان", "وماذا عن فرنسا؟"])
        assert out[1] == "كم عدد سكان فرنسا"

    def test_location_modifier_not_carried(self):
        """«كم أجرة الفندق في مكة» + «وماذا عن جدة» ⇒ الجارة (مكة) لا تنتقل مع الجديد."""
        out = _resolve_chain(["كم أجرة الفندق في مكة", "وماذا عن جدة؟"])
        assert "مكة" not in out[1]  # كانت تبقى: «كم أجرة جدة في مكة»
        assert "جدة" in out[1]


class TestIsTechArabic:
    """كشف الأسئلة التقنية يعرف العربية — أسئلة الذكاء الاصطناعي تفتح مزوداتها الحقيقية."""

    @pytest.mark.parametrize("q", [
        "ماذا عن اخر اخبار التكنولوجيا والذكاء الاصطناعي في فلوريدا",
        "ما اخر اخبار التكنولوجيا والذكاء الاصطناعي",
        "ما مدى تقدم الذكاء الاصطناعي في العالم",
        "أخبرني عن تعلم الآلة",
        "ما هي شبكات عصبية جديدة؟",
        "أحدث أخبار التقنية والروبوتات",
        "What is new in artificial intelligence",
        "machine learning frameworks comparison",
    ])
    def test_tech_detected(self, q):
        assert w.is_tech(q), q

    @pytest.mark.parametrize("q", [
        "ماذا عن باقي العالم",
        "ما عاصمة اليابان",
        "كم سعر الذهب اليوم",
        "ماذا عن سقوط طائرة في فلوريدا",
        "أخبار كرة القدم",
    ])
    def test_not_tech(self, q):
        assert not w.is_tech(q), q

    def test_tech_kind_flows_to_intent(self):
        """is_tech ⇒ نية «تقني» ⇒ مزودات GitHub/HuggingFace/Stack Overflow."""
        intent = sp.analyze("ما اخر اخبار التكنولوجيا والذكاء الاصطناعي",
                            "latest technology and artificial intelligence news", "ar", tech=True)
        assert "tech" in intent["kinds"]


class TestHuggingFacePlatform:
    """مزود HuggingFace: نماذج ومجموعات بيانات — مصدر الذكاء الاصطناعي الحقيقي."""

    def test_p_huggingface_parses_models_and_datasets(self, monkeypatch):
        def h(req):
            assert "huggingface.co/api/" in str(req.url)
            if "/api/models" in str(req.url):
                return httpx.Response(200, json=[
                    {"modelId": "org/vision-xl", "downloads": 1234, "likes": 77, "pipeline_tag": "text-to-image"},
                    {"id": "", "downloads": 0, "likes": 0},  # بلا معرف ⇒ يُتخطى
                ])
            return httpx.Response(200, json=[
                {"id": "org/arabic-corpus", "downloads": 99, "likes": 5},
            ])
        _mock(monkeypatch, h)
        out = sp.p_huggingface("text to image", "en")
        kinds = {x["kind"] for x in out}
        assert kinds == {"model", "dataset"}
        m = next(x for x in out if x["kind"] == "model")
        assert m["title"] == "org/vision-xl"
        assert m["url"] == "https://huggingface.co/org/vision-xl"
        assert m["platform"] == "HuggingFace" and m["provider"] == "huggingface"
        assert "text-to-image" in m["snippet"]
        d = next(x for x in out if x["kind"] == "dataset")
        assert d["url"] == "https://huggingface.co/datasets/org/arabic-corpus"

    def test_huggingface_failure_tolerated(self, monkeypatch):
        """فشل الواجهة ⇒ قائمة فارغة لا استثناء (نمط المزودات)."""
        def h(req):
            return httpx.Response(500)
        _mock(monkeypatch, h)
        assert sp.p_huggingface("anything", "en") == []

    def test_tech_jobs_include_github_and_huggingface(self):
        """سؤال ذكاء اصطناعي ⇒ مزودا GitHub وHuggingFace معًا (أمر المالك)."""
        intent = sp.analyze("ما اخر اخبار التكنولوجيا والذكاء الاصطناعي",
                            "latest artificial intelligence news", "ar", tech=True)
        names = [n for n, *_ in sp.platform_jobs(intent, {"ar": "أخبار الذكاء الاصطناعي",
                                                           "en": "artificial intelligence news"}, "ar",
                                                 w.keyword_query, w.scholarly_query)]
        assert "github" in names
        assert "huggingface" in names

    def test_non_tech_jobs_exclude_huggingface(self):
        """سؤال غير تقني ⇒ لا مزود تقني."""
        intent = sp.analyze("ما عاصمة اليابان", "What is the capital of Japan", "ar")
        names = [n for n, *_ in sp.platform_jobs(intent, {"ar": "عاصمة اليابان",
                                                          "en": "capital of Japan"}, "ar",
                                                 w.keyword_query, w.scholarly_query)]
        assert "huggingface" not in names and "github" not in names
