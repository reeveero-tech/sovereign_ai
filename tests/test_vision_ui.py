"""R-741 (البند ٢.٢ — الجولة الموثقة «اللاحقة»: رفع الصور في الواجهة):
النصف الثاني المعلن من معيار البند — واجهة ترفع صورة إلى /vision.

معيار الجولة المعلن في ROADMAP_V4 (حد ٢.٢): «رفع الصور في الواجهة جولة
لاحقة». هذا الحارس يثبت نصف الواجهة:
1. زر الرفع موجود فعلًا في صف المحادثة (btn-vision-upload) بجانب الإرسال.
2. مدخل ملف مخفي يقبل أنواع الصور المسموحة فقط (نفس قائمة الخادم).
3. الزر والمدخل مصنفان في LIVE_BINDINGS.json (control) — حارس R-730
   يرفض عنصرًا بلا تصنيف.
4. وحدة الرؤية الحية موجودة وتخاطب الزر والمدخل ونقطة /vision الفعلية
   وتسلّم الوصف عبر مسار المحادثة الحقيقي — لا كتابة DOM مجهولة.
5. خطاف المحادثة (chat-runtime) له مدخل استقبال وصف الرؤية معلن.
6. السكربت محمّل فعلًا في index.html.
7. الوحدة مجرودة في INVENTORY.md (وحدة حقيقية تستهلك API).
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
INDEX = (FRONTEND / "index.html").read_text(encoding="utf-8", errors="ignore")
BINDINGS = json.loads((FRONTEND / "LIVE_BINDINGS.json").read_text(
    encoding="utf-8"))
VISION_JS = FRONTEND / "js" / "modules" / "vision-input.js"
CHAT_JS = (FRONTEND / "js" / "modules" / "chat-runtime.js").read_text(
    encoding="utf-8", errors="ignore")
INVENTORY = (FRONTEND / "INVENTORY.md").read_text(encoding="utf-8")


def test_upload_button_exists_near_chat_send():
    """زر رفع الصورة موجود في صف المحادثة — لا زر وهمي في مكان معزول."""
    assert 'id="btn-vision-upload"' in INDEX, (
        "زر رفع الصور (btn-vision-upload) غير موجود في index.html")
    chat_pos = INDEX.find('id="chat-input"')
    btn_pos = INDEX.find('id="btn-vision-upload"')
    assert chat_pos != -1 and btn_pos > chat_pos, (
        "الزر يجب أن يكون في صف إدخال المحادثة بعد مربع النص")


def test_file_input_accepts_images_only():
    """مدخل الملف المخفي يقبل أنواع الصور المسموحة فقط (نفس قائمة الخادم)."""
    assert 'id="vision-file-input"' in INDEX, (
        "مدخل ملف الصور (vision-file-input) غير موجود في index.html")
    m = re.search(r'<input[^>]*id="vision-file-input"[^>]*>', INDEX)
    assert m, "مدخل ملف الصور غير قابل للتحليل"
    tag = m.group(0)
    assert 'type="file"' in tag, "المدخل ليس نوع ملف"
    accept = re.search(r'accept="([^"]+)"', tag)
    assert accept, "المدخل بلا قائمة أنواع مسموحة (accept)"
    for allowed in ("image/png", "image/jpeg", "image/webp"):
        assert allowed in accept.group(1), (
            f"النوع {allowed} مفقود من قائمة القبول — يجب أن تطابق الخادم")


def test_upload_controls_classified_in_live_bindings():
    """الزر والمدخل مصنفان control في LIVE_BINDINGS — حارس R-730 يرفض
    غير المصنف (تغطية كاملة لعناصر index.html)."""
    assert "btn-vision-upload" in BINDINGS.get("control", []), (
        "btn-vision-upload غير مصنف في LIVE_BINDINGS.json (control)")
    assert "vision-file-input" in BINDINGS.get("control", []), (
        "vision-file-input غير مصنف في LIVE_BINDINGS.json (control)")


def test_vision_module_real_and_bound():
    """وحدة رفع الصور موجودة وتخاطب الزر والنقطة الفعلية وتسلّم عبر
    مسار المحادثة الحقيقي — لا محاكاة ولا كتابة DOM مجهولة."""
    assert VISION_JS.exists(), "وحدة vision-input.js غير موجودة"
    js = VISION_JS.read_text(encoding="utf-8", errors="ignore")
    assert "btn-vision-upload" in js, "الوحدة لا تخاطب الزر المعلن"
    assert "vision-file-input" in js, "الوحدة لا تخاطب مدخل الملف المعلن"
    assert "/vision" in js, "الوحدة لا تستدعي نقطة /vision الفعلية"
    assert "SOVEREIGN_CHAT_RUNTIME" in js, (
        "الوحدة يجب أن تسلّم الوصف عبر مسار المحادثة الحقيقي "
        "(SOVEREIGN_CHAT_RUNTIME) — لا كتابة DOM مباشرة")
    # صدق الفشل: كل رموز الخادم المعلنة تُعلن في الواجهة لا تُخفى
    for code in ("503", "502", "413", "415", "429"):
        assert code in js, (
            f"الوحدة يجب أن تعلن فشل {code} بصدق (عقد /vision — R-739)")


def test_chat_runtime_has_vision_entry():
    """خطاف المحادثة له مدخل استقبال وصف الرؤية معلن — لا وحدة مجهولة
    تكتب في المحادثة."""
    assert "receiveVisionDescription" in CHAT_JS, (
        "chat-runtime.js لا يملك مدخل استقبال وصف الرؤية "
        "(receiveVisionDescription)")


def test_vision_script_loaded():
    """السكربت محمّل فعلًا في index.html — وحدة غير محملة = زر ميت."""
    assert 'js/modules/vision-input.js' in INDEX, (
        "vision-input.js غير محمّل في index.html")


def test_inventory_lists_vision_module():
    """الوحدة مجرودة في INVENTORY.md كوحدة حقيقية تستهلك API — حارس ١.١
    يرفض وحدة غير مجرودة، والجرد يوثق العدّة الصادقة."""
    assert "`vision-input.js`" in INVENTORY, (
        "vision-input.js غير مدرجة في frontend/INVENTORY.md")
    assert "9 |" in INVENTORY or "| 9 |" in INVENTORY or " 9 " in INVENTORY.split("تستهلك API مباشرة")[1][:60], (
        "عدّة الجرد المباشرة لم تُحدَّث (8 → 9)")


def test_accept_list_matches_server_contract():
    """مطابقة العقد ثنائية الاتجاعة ومحروسة: قائمة الأنواع في accept الواجهة
    = قائمة الخادم في backend/app.py حرفيًا — أي انجراف مستقبلي في أحدهما
    يكسر هذا الحارس لا التطبيق بصمت (تصويب R-741: الادعاء صار محروسًا)."""
    app_py = (REPO_ROOT / "backend" / "app.py").read_text(
        encoding="utf-8", errors="ignore")
    m = re.search(
        r"VISION_ALLOWED_CONTENT_TYPES\s*=\s*\{(.*?)\}",
        app_py, re.S)
    assert m, "قائمة VISION_ALLOWED_CONTENT_TYPES غير موجودة في app.py"
    server_types = set(re.findall(r'"(image/[a-z]+)"', m.group(1)))
    accept = re.search(
        r'<input[^>]*id="vision-file-input"[^>]*accept="([^"]+)"',
        INDEX)
    assert accept, "مدخل الملف بلا accept — لا مطابقة ممكنة"
    ui_types = set(t.strip() for t in accept.group(1).split(","))
    assert ui_types == server_types, (
        f"انجراف عقد بين الواجهة والخادم: UI={sorted(ui_types)} "
        f"vs SERVER={sorted(server_types)}")


def test_size_limit_matches_server_contract():
    """حد الحجم في الواجهة = حد الخادم (VISION_MAX_IMAGE_BYTES في config) —
    انجراف أي طرف يكسر الحارس."""
    config_py = (REPO_ROOT / "backend" / "config.py").read_text(
        encoding="utf-8", errors="ignore")
    m = re.search(
        r"VISION_MAX_IMAGE_BYTES\s*=\s*int\(\w+\(\"VISION_MAX_IMAGE_BYTES\",\s*str\(([^)]+)\)\)\)",
        config_py)
    assert m, "VISION_MAX_IMAGE_BYTES غير موجود في config.py"
    server_expr = m.group(1).replace(" ", "")
    server_limit = eval(server_expr)  # تعبير رقمي معروف المصدر (10*1024*1024)
    js = VISION_JS.read_text(encoding="utf-8", errors="ignore")
    jm = re.search(r"this\.maxBytes\s*=\s*([\d\s*+]+);", js)
    assert jm, "حد الحجم (maxBytes) غير معرف في vision-input.js"
    ui_limit = eval(jm.group(1).replace("\n", "").replace(" ", ""))
    assert ui_limit == server_limit, (
        f"انجراف حد الحجم: UI={ui_limit} vs SERVER={server_limit}")


def test_vision_flow_persists_image_before_description():
    """رسالة الصورة تدخل activeConversation قبل تسليم الوصف — فيرتبط حفظ
    الذاكرة (saveInteraction يبحث آخر رسالة مستخدم) بالصورة لا بما قبلها
    (تصويب R-741 بعد اعتراض المراجعة)."""
    js = CHAT_JS
    m = re.search(
        r"receiveVisionDescription\([^)]*\)\s*\{.*?\n    \}",
        js, re.S)
    assert m, "receiveVisionDescription غير موجود في chat-runtime.js"
    body = m.group(0)
    push_pos = body.find("activeConversation.push")
    receive_pos = body.find("receiveMessage")
    assert push_pos != -1 and receive_pos != -1 and push_pos < receive_pos, (
        "يجب أن تدفع رسالة الصورة إلى activeConversation قبل receiveMessage "
        "— وإلا يُحفظ الوصف في الذاكرة كرد على ما قبل الصورة")
