# -*- coding: utf-8 -*-
"""R-832: كلمات الاستفهام لا تُخطف إلى قالب «مساعدة» — طلب البحث يصل بحثه.

الخلفية (مشاهد حيًا في النشر): «ابحث عن كيفية تدريب نموذج ذكاء اصطناعي»
صُنّفت نيتها «help» لأن كلمة «كيف» كانت من كلمات نية المساعدة، والمطابقة
جزئية («كيف» داخل «كيفية») — فأجاب النظام بقالب قدرات النظام عن طلب بحث.
والأخطر: «help» من نوايا البيانات الحية فلا يسقط للبحث العالمي عند تعذر
العقل — الطلب المفتوح يُحرم من بحثه كليًا.

الإصلاح: أُزيلت كلمات الاستفهام/الحاجة (كيف/how/أحتاج/need) من نية المساعدة؛
طلب المساعدة الصريح يطابق «مساعدة»/«help»/«ساعدني».
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nexus"))
from nlp.intent_recognizer import DEFAULT_INTENTS, IntentRecognizer  # noqa: E402


@pytest.fixture
def recognizer():
    return IntentRecognizer()


class TestR832IntentNotHijacked:
    """الأسئلة المفتوحة لا تُصنف «مساعدة» — تصل مسارها (البحث العالمي عند تعذر العقل)."""

    SEARCH_QUESTIONS = [
        "ابحث عن كيفية تدريب نموذج ذكاء اصطناعي",  # الحالة المشاهدة حيًا
        "كيفية عمل القهوة",
        "كيف أتعلم البرمجة",
        "how do I train a model",
        "أحتاج خطة تسويق لمشروعي",
        "need a marketing plan",
    ]

    @pytest.mark.parametrize("text", SEARCH_QUESTIONS)
    def test_open_questions_not_help(self, recognizer, text):
        """سؤال فيه «كيف/أحتاج/need/how» ليس طلب مساعدة — لا يُخطف للقالب."""
        intent = recognizer.recognize(text)
        assert not (intent and intent.name == "help"), (
            f"«{text}» صُنفت «help» — كلمة استفهام/حاجة تخطف السؤال المفتوح "
            "إلى قالب القدرات فيُحرم من بحثه"
        )

    HELP_REQUESTS = ["أحتاج مساعدة", "I need help", "ساعدني", "مساعدة", "help me"]

    @pytest.mark.parametrize("text", HELP_REQUESTS)
    def test_genuine_help_still_recognized(self, recognizer, text):
        """طلب المساعدة الصريح يظل يُصنف «help» — القالب يجيب سؤاله."""
        intent = recognizer.recognize(text)
        assert intent is not None and intent.name == "help", (
            f"«{text}» طلب مساعدة صريح يجب أن يُصنف «help»"
        )

    def test_no_question_words_in_help_keywords(self):
        """تثبيت الانحدار: كلمات الاستفهام/الحاجة المجردة ليست من كلمات المساعدة."""
        banned = {"كيف", "how", "need", "أحتاج"}
        help_keywords = set(DEFAULT_INTENTS.get("help", []))
        assert not (help_keywords & banned), (
            "كلمات استفهام/حاجة مجردة في نية المساعدة تخطف الأسئلة المفتوحة: "
            f"{help_keywords & banned}"
        )

    def test_search_request_reaches_open_path(self, recognizer):
        """الحالة المشاهدة حيًا: طلب البحث بلا نية ⇒ يسقط للبحث العالمي عند تعذر العقل."""
        intent = recognizer.recognize("ابحث عن كيفية تدريب نموذج ذكاء اصطناعي")
        # بلا نية (أو نية غير «help» الحاجبة للبحث) — المسار المفتوح متاح
        assert intent is None or intent.name != "help"
