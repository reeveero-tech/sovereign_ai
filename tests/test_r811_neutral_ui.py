"""R-811 (المالك — البند ٧): واجهة محايدة بلا اسم «سيادي».

الدافع (المالك 2026-10-29): «اريد منك أن تزيل اسم سيادي من الواجهة إذ أنها
توحي بأن المشروع عبثي أو مشروع هواه». الاسم الظاهر للمستخدم صار محايدًا
مهنيًا («مساحة العمل») في كل ما يُعرض: العناوين، الشعار، أسماء المرسل،
التلميحات، والأدوار الظاهرة في الحوارات.

الحدود الصريحة (لا مساس): أسماء وحدات الخلفية (sovereign/…)، ترويسة
X-Sovereign-Key، المخطوطات المحفوظة، وأسماء ملفات الواجهة — كلها بنية تحتية
لا تظهر للمستخدم، وتغييرها يكسر التوافق بلا داعٍ. هذا الحارس يحمي الطبقة
المعروضة فقط: أي عودة لكلمة «سيادي» في نصوص الواجهة تُرفض.

ملاحظة: تعليقات الشيفرة الداخلية (غير المعروضة) في js/modules وjs/system
خارج نطاق هذا الحارس — الحارس يفحص ما يُقدَّم للمستخدم.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHAT_UI = ROOT / "frontend" / "chat" / "index.html"
CLASSIC_UI = ROOT / "frontend" / "chat" / "classic.html"
LEGACY_UI = ROOT / "frontend" / "index.html"


@pytest.mark.parametrize("ui", [CHAT_UI, CLASSIC_UI, LEGACY_UI], ids=["chat", "classic", "legacy"])
def test_served_ui_has_no_sovereign_name(ui):
    """البند ٧: لا «سيادي» في أي نص معروض للواجهات الثلاث."""
    html = ui.read_text(encoding="utf-8")
    assert "سيادي" not in html, f"{ui.name} لا يزال يحمل اسم «سيادي» في نصوصه المعروضة"


def test_main_ui_uses_neutral_workspace_name():
    """الاسم الجديد محايد ومهني — «مساحة العمل» في العنوان والشعار."""
    html = CHAT_UI.read_text(encoding="utf-8")
    assert "<title>مساحة العمل</title>" in html
    assert '<div class="brand">مساحة العمل</div>' in html


def test_dialogue_sender_is_neutral():
    """أسماء مرسل الحوارات في الواجهة القديمة محايدة — لا «الذكاء السيادي»."""
    main_js = (ROOT / "frontend" / "js" / "main.js").read_text(encoding="utf-8")
    ws_js = (ROOT / "frontend" / "js" / "websocket.js").read_text(encoding="utf-8")
    for src in (main_js, ws_js):
        assert "الذكاء السيادي" not in src
        assert "'المساعد'" in src


def test_greeting_is_professional():
    """لا مخاطبة «أيها السيد» — نبرة مهنية."""
    main_js = (ROOT / "frontend" / "js" / "main.js").read_text(encoding="utf-8")
    assert "أيها السيد" not in main_js
    assert "جاهز للعمل" in main_js
