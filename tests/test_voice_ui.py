"""R-740 (البند ٢.٤ — النصف الثاني من معيار الإغلاق): زر التحكم في النطق.

معيار البند: «نص → مقطع صوتي + زر تحكم». هذا الحارس يثبت نصف الواجهة:
1. زر التبديل موجود فعلًا في index.html (btn-tts-toggle) بجانب إرسال
   المحادثة.
2. مصنف في LIVE_BINDINGS.json (control) — حارس R-730 يرفض عنصرًا بلا
   تصنيف.
3. وحدة النطق الحية موجودة وتشير للزر وللنقطة /tts — لا محاكاة.
4. خطاف المحادثة (chat-runtime) يستدعي النطق عند وصول رد — لا نطق من
   وحدة مجهولة.
5. السكربت محمّل فعلًا في index.html.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
INDEX = (FRONTEND / "index.html").read_text(encoding="utf-8", errors="ignore")
BINDINGS = json.loads((FRONTEND / "LIVE_BINDINGS.json").read_text(
    encoding="utf-8"))
VOICE_JS = (FRONTEND / "js" / "modules" / "voice-output.js")
CHAT_JS = (FRONTEND / "js" / "modules" / "chat-runtime.js").read_text(
    encoding="utf-8", errors="ignore")


def test_toggle_button_exists_near_chat_send():
    """الزر موجود في صف المحادثة (قسم الحوار) — لا زر وهمي في مكان معزول."""
    assert 'id="btn-tts-toggle"' in INDEX, (
        "زر تبديل النطق (btn-tts-toggle) غير موجود في index.html")
    # في نفس قسم المحادثة (بين chat-input وقسم الحوار)
    chat_pos = INDEX.find('id="chat-input"')
    btn_pos = INDEX.find('id="btn-tts-toggle"')
    assert chat_pos != -1 and btn_pos > chat_pos, (
        "الزر يجب أن يكون في صف إدخال المحادثة بعد مربع النص")


def test_toggle_classified_in_live_bindings():
    """الزر مصنف control في LIVE_BINDINGS — حارس R-730 يرفض غير المصنف."""
    assert "btn-tts-toggle" in BINDINGS.get("control", []), (
        "btn-tts-toggle غير مصنف في LIVE_BINDINGS.json (control)")


def test_voice_module_real_and_bound():
    """وحدة النطق موجودة وتخاطب الزر والنقطة الفعلية — لا محاكاة."""
    assert VOICE_JS.exists(), "وحدة voice-output.js غير موجودة"
    js = VOICE_JS.read_text(encoding="utf-8", errors="ignore")
    assert "btn-tts-toggle" in js, "الوحدة لا تخاطب الزر المعلن"
    assert "/tts" in js, "الوحدة لا تستدعي نقطة /tts الفعلية"
    assert "localStorage" in js, "حالة التبديل يجب أن تبقى (localStorage)"
    # صدق الفشل: تعطل النقطة يُعلن لا يُخفى
    assert "503" in js or "tts_disabled" in js, (
        "الوحدة يجب أن تعلن تعطل النطق بصدق (لا صمت كاذب)")


def test_chat_runtime_hooks_voice():
    """خطاف المحادثة يستدعي النطق عند وصول رد الذكاء — لا وحدة مجهولة."""
    assert "SOVEREIGN_VOICE" in CHAT_JS, (
        "chat-runtime.js لا يستدعي وحدة النطق عند وصول الرد")


def test_voice_script_loaded():
    """السكربت محمّل فعلًا في index.html — وحدة غير محملة = زر ميت."""
    assert 'js/modules/voice-output.js' in INDEX, (
        "voice-output.js غير محمّل في index.html")
