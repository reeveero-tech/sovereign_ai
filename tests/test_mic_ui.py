"""R-742 (البند ٢.٣ — الجولة الموثقة «اللاحقة»: زر الميكروفون في الواجهة):
النصف الثاني المعلن من البند ٢.٣ — واجهة تسجل صوتًا وترسله إلى /stt.

معيار الجولة:
1. زر الميكروفون في صف المحادثة (btn-stt-mic) ومصنف control في LIVE_BINDINGS.
2. وحدة stt-input.js حقيقية: تسجيل عبر MediaRecorder، رفع إلى /stt الفعلية،
   إعلان صادق لكل رموز العقد (503/502/413/415/429)، لا نص مختلق.
3. تطبيع نوع التسجيل: المتصفح يعطي «audio/webm;codecs=opus» والخادم يطابق
   النوع حرفيًا — بلا تطبيع يُرفض كل تسجيل 415. النوع المرسل يجب أن يكون
   ضمن STT_ALLOWED_CONTENT_TYPES حرفيًا (حارس مطابقة عقد).
4. النص يوضع في مربع الإدخال للمراجعة — لا إرسال آلي باسم المالك.
5. السكربت محمّل والوحدة مجرودة في INVENTORY (10/79).
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
INDEX = (FRONTEND / "index.html").read_text(encoding="utf-8", errors="ignore")
BINDINGS = json.loads((FRONTEND / "LIVE_BINDINGS.json").read_text(
    encoding="utf-8"))
STT_JS = FRONTEND / "js" / "modules" / "stt-input.js"
INVENTORY = (FRONTEND / "INVENTORY.md").read_text(encoding="utf-8")
APP_PY = (REPO_ROOT / "backend" / "app.py").read_text(
    encoding="utf-8", errors="ignore")


def _js():
    assert STT_JS.exists(), "وحدة stt-input.js غير موجودة"
    return STT_JS.read_text(encoding="utf-8", errors="ignore")


def test_mic_button_in_chat_row():
    assert 'id="btn-stt-mic"' in INDEX, "زر الميكروفون (btn-stt-mic) غير موجود"
    assert INDEX.find('id="btn-stt-mic"') > INDEX.find('id="chat-input"'), (
        "الزر يجب أن يكون في صف إدخال المحادثة")


def test_mic_button_classified():
    assert "btn-stt-mic" in BINDINGS.get("control", []), (
        "btn-stt-mic غير مصنف في LIVE_BINDINGS.json (control)")


def test_stt_module_real_and_bound():
    js = _js()
    assert "btn-stt-mic" in js, "الوحدة لا تخاطب الزر المعلن"
    assert "MediaRecorder" in js, "الوحدة لا تسجل فعليًا (MediaRecorder)"
    assert "getUserMedia" in js, "الوحدة لا تطلب إذن الميكروفون"
    assert "'/stt'" in js, "الوحدة لا تستدعي نقطة /stt الفعلية"
    for code in ("503", "502", "413", "415", "429"):
        assert code in js, f"الوحدة يجب أن تعلن فشل {code} بصدق (عقد /stt)"


def test_upload_type_normalized_and_in_server_contract():
    """النوع المرسل نوع أساسي بلا معاملات codecs، وهو ضمن قائمة الخادم حرفيًا."""
    js = _js()
    m = re.search(r"STT_ALLOWED_CONTENT_TYPES\s*=\s*\{(.*?)\}", APP_PY, re.S)
    assert m, "STT_ALLOWED_CONTENT_TYPES غير موجودة في app.py"
    server = set(re.findall(r'"([a-z]+/[a-z0-9.+-]+)"', m.group(1)))
    assert "split(';')" in js, (
        "نوع التسجيل غير مطبَّع — «audio/webm;codecs=opus» سيُرفض 415")
    ui = set(re.findall(r"'(audio/[a-z0-9.+-]+)'",
                        js.split("uploadTypes")[1].split("]")[0]))
    assert ui and ui <= server, (
        f"أنواع الرفع في الواجهة خارج عقد الخادم: {sorted(ui - server)}")


def test_size_limit_matches_server_contract():
    js = _js()
    cfg = (REPO_ROOT / "backend" / "config.py").read_text(encoding="utf-8")
    m = re.search(r'STT_MAX_AUDIO_BYTES",\s*str\(([^)]+)\)', cfg)
    assert m, "STT_MAX_AUDIO_BYTES غير موجود في config.py"
    jm = re.search(r"this\.maxBytes\s*=\s*([\d\s*]+);", js)
    assert jm, "maxBytes غير معرف في stt-input.js"
    assert eval(jm.group(1)) == eval(m.group(1)), "انجراف حد الحجم عن الخادم"


def test_transcript_goes_to_input_not_auto_sent():
    """النص يوضع في chat-input للمراجعة — لا إرسال آلي باسم المالك."""
    js = _js()
    assert "chat-input" in js, "النص لا يصل إلى مربع الإدخال"
    assert "sendMessage" not in js, (
        "الوحدة ترسل آليًا — يجب أن يراجع المالك النص قبل الإرسال")


def test_script_loaded_and_inventoried():
    assert "js/modules/stt-input.js" in INDEX, "stt-input.js غير محمّل"
    assert "`stt-input.js`" in INVENTORY, "stt-input.js غير مجرودة"
    assert "| تستهلك API مباشرة | 10 |" in INVENTORY, "عدّة الجرد لم تُحدَّث (9→10)"
