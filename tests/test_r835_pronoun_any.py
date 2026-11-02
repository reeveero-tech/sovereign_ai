# -*- coding: utf-8 -*-
"""R-835: الضمير المتصل بأي اسم لا خاصية معروفة فقط — من محادثة إنتاج.

«ما مدى جهوزيته للانتاج؟» بعد نقاش مستودع xuux بقي خامًا (جهوزية ليست في
_AR_PROPS) فبحث العالمي عن «production readiness» عامًا وأجاب عن طعام إنتاجي
(محادثة المالك 2026-11-02 15:43). كل مسارات الرد (الوكيل/الجسر/البحث العالمي)
تستخدم eff_text — فالحل هنا يصل الجميع.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import context_resolver  # noqa: E402

XUUX_HIST = [
    {"role": "user",
     "content": "https://github.com/ovvvog/xuux اريد تحليل دقيق للمشروع xuux ارفقت لك رابطه"},
    {"role": "assistant",
     "content": "بيانات مستودع GitHub ovvvog/xuux: JavaScript 89%، النجوم: 0"},
]


class TestLooseAttachedPronoun:
    """«جهوزيته/حاله/مشاكله» — ضمير متصل بكلمة ليست خاصية معروفة."""

    def test_production_case_jahuziytu(self):
        """حالة الإنتاج حرفيًا: جهوزيته ⇒ جهوزية + رابط المستودع."""
        r = context_resolver.resolve("ما مدى جهوزيته للانتاج ؟", XUUX_HIST)
        assert r["followup"] and r["kind"] == "pronoun"
        assert "github.com/ovvvog/xuux" in r["standalone"]
        assert "جهوزية" in r["standalone"]
        assert "جهوزيته" not in r["standalone"]

    def test_halu_masakiluh(self):
        """حاله/مشاكله — جذوع سليمة ≥3 أحرف."""
        for q, stem in (("كيف حاله ؟", "حال"), ("ما مشاكله ؟", "مشاكل")):
            r = context_resolver.resolve(q, XUUX_HIST)
            assert r["followup"] and r["kind"] == "pronoun", q
            assert stem in r["standalone"] and "github.com/ovvvog/xuux" in r["standalone"], q

    def test_two_attached_pronouns(self):
        """ضميران متصلان في سؤال واحد — كلهما يُستبدلان."""
        r = context_resolver.resolve("ما مدى جودة كوده ؟", XUUX_HIST)
        assert r["followup"] and "كود" in r["standalone"]
        assert "github.com/ovvvog/xuux" in r["standalone"]

    def test_no_history_no_resolution(self):
        """بلا تاريخ لا كيان — القاعدة لا تخترع شيئًا."""
        r = context_resolver.resolve("ما مدى جهوزيته للانتاج ؟", [])
        assert not r["followup"] and r["kind"] == "none"


class TestPrepPronoun:
    """R-835: حرف جر + ضمير («عليها/فيه») ⇒ الجار + الكيان."""

    def test_alayha_resolves(self):
        """«ماذا تعرف عليها؟» — كانت تُخطف كتبديل كيان فتنتج نصًا مكسورًا."""
        r = context_resolver.resolve("ماذا تعرف عليها ؟", XUUX_HIST)
        assert r["followup"] and r["kind"] == "pronoun"
        assert "على https://github.com/ovvvog/xuux" in r["standalone"]

    def test_fihi_resolves(self):
        r = context_resolver.resolve("ما رأيك فيه ؟", XUUX_HIST)
        assert r["followup"] and "في https://github.com/ovvvog/xuux" in r["standalone"]


class TestGuards:
    """الحُرّاس: القاعدة لا تلمس كلمات السؤال ولا الضمائر المستقلة."""

    def test_what_is_it_not_touched(self):
        """«ما هو؟» ليست إشارة كيان — تعيّن حارس R-834."""
        r = context_resolver.resolve("ما هو ؟", XUUX_HIST)
        assert not r["followup"]

    def test_stopword_pron_not_touched(self):
        """«ذلك/هذا» كلمات وقف — لا تُستبدل بالقاعدة الجديدة."""
        r = context_resolver.resolve("اشرح ذلك اكثر", XUUX_HIST)
        # «اشرح ذلك اكثر» ليست جملة استزادة كاملة (كلمة زائدة) — لا ضمير متصل ⇒ خام
        assert r["standalone"] == "اشرح ذلك اكثر"

    def test_long_question_not_touched(self):
        """سؤال طويل (>8 كلمات) لا تدخله القاعدة — حارس الطول."""
        q = " ".join(["ما", "مدى", "جهوزيته", "بالنسبة"] + ["كلمة"] * 7)
        r = context_resolver.resolve(q, XUUX_HIST)
        assert not r["followup"]

    def test_english_no_pronoun_unaffected(self):
        """سؤال إنجليزي بلا ضمير لا تلمسه القواعد — يبقى خامًا."""
        r = context_resolver.resolve("how ready is the project for production?", XUUX_HIST)
        assert not r["followup"]


class TestSwapGuardAndUrlEntity:
    """حارس التبديل + استخراج الرابط بالمخطط."""

    def test_swap_still_works(self):
        """«وماذا عن فرنسا» تبديل كيان سليم — الحارس لا يفسده."""
        r = context_resolver.resolve("وماذا عن فرنسا", XUUX_HIST)
        assert r["followup"] and r["kind"] == "entity_swap"
        assert "فرنسا" in r["standalone"] and "https://" not in r["standalone"].split("فرنسا")[0]

    def test_entity_includes_scheme(self):
        """الكيان = الرابط كاملًا بالمخطط — التبديل لا يترك https:// معلقًا."""
        ent = context_resolver.entity_of(XUUX_HIST[0]["content"])
        assert ent.startswith("https://github.com/ovvvog/xuux")
