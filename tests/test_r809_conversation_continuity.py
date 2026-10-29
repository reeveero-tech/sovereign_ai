"""R-809: استمرارية المحادثات — «محادثة جديدة» لا تمحو السابقة.

الدافع (المالك 2026-10-29): «المحادثات اذا ضغطت محادثه جديده تختفي الاولى».
التشخيص: زر «محادثة جديدة» كان يفرّغ الحالة فورًا — للضيف (بلا مفتاح المالك)
كان الحوار كله يختفي بلا أثر (لا قائمة محفوظة أصلًا)، وللمالك كانت أي رسائل
بعد آخر حفظ تضيع. العناوين كانت فارغة فكل المحادثات تظهر باسم «محادثة».

المثبت هنا (تأكيدات على المصدر — جافاسكربت المتصفح لا يعمل داخل pytest):
- الزر يحفظ المحادثة الجارية قبل التبديل (keepCurrentConversationBeforeNew).
- الضيف له قائمة محادثات في متصفحه (sovereign.localConvs + upsert + reopen).
- المالك: persistConv يُستدعى قبل التبديل، والعنوان مشتق من أول رسالة.
- عنوان المحادثة مشتق من أول دور مستخدم (convTitle) في الإنشاء والتحديث.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHAT_UI = ROOT / "frontend" / "chat" / "index.html"


@pytest.fixture(scope="module")
def _ui() -> str:
    return CHAT_UI.read_text(encoding="utf-8")


def test_new_button_saves_previous_conversation(_ui: str):
    """R-809: الزر يحفظ الجارية أولًا — لا تختفي عند بدء جلسة جديدة."""
    assert "keepCurrentConversationBeforeNew(); // R-809" in _ui, \
        "زر «محادثة جديدة» يجب أن يحفظ المحادثة الجارية قبل التفريغ"


def test_guest_conversations_survive_in_browser(_ui: str):
    """R-809: الضيف بلا مفتاح — قائمة محادثات محلية بدل الحوار الوحيد المهدور."""
    assert "sovereign.localConvs" in _ui, "مفتاح تخزين قائمة محادثات الضيف مفقود"
    assert "function upsertLocalConv" in _ui, "upsertLocalConv مفقودة"
    assert "function openLocalConv" in _ui, "openLocalConv (العودة لمحادثة ضيف) مفقودة"
    # القائمة الجانبية تعرض محادثات الضيف — ليس رسالة «أدخل المفتاح» فقط
    # (R-813: فهرس عرض — slice ثم forEach، والمخزن الكامل يحفظ الجميع)
    assert "localConvs.slice(0, showAllLocalConvs ? localConvs.length : CONV_DISPLAY_CAP).forEach(function (c)" in _ui, \
        "paintConvs لا تعرض محادثات الضيف"


def test_owner_persist_before_switch(_ui: str):
    """R-809: المالك — persistConv قبل التبديل حتى لا تضيع الرسائل غير المحفوظة."""
    assert "persistConv(); // R-809" in _ui, "keepCurrentConversationBeforeNew لا يستدعي persistConv للمالك"


def test_conversation_title_derived_from_first_user_message(_ui: str):
    """R-809: العنوان مشتق من أول رسالة مستخدم — بدل «محادثة» لكل شيء."""
    assert "function convTitle" in _ui, "convTitle مفقودة"
    assert 'title: convTitle(state.messages)' in _ui, "persistConv لا يستخدم العنوان المشتق"


def test_local_conversation_list_capped(_ui: str):
    """R-809/813 (تصحيح المراجعة الثانية): فهرس عرض بأحدث ١٠٠ قابل للتوسيع،
    والمخزن الكامل يحفظ الجميع كاملة — لا اقتطاط ولا حذف أبدًا (أمر المالك)."""
    assert "CONV_DISPLAY_CAP = 100" in _ui, "فهرس عرض بلا سقف"
    assert "localConvs.slice(0, showAllLocalConvs ? localConvs.length : CONV_DISPLAY_CAP)" in _ui
    assert "إظهار الكل" in _ui, "ما بعد السقف يجب أن يبقى قابلًا للفتح (توسيع صادق)"
    assert ".slice(0, 2)" not in _ui, "لا اقتطاط رسائل في التخزين"
