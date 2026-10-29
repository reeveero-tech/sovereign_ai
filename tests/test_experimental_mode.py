"""R-731 (البند ١.٥ — بأمر المالك «تابع»): وضع تجريبي صريح — معيار الإغلاق
«لا يوجد عنصر يعرض بيانات ثابتة بلا وسم».

يثبت آليًا:
1. كل عنصر غير مربوط (LIVE_BINDINGS.json) يحمل data-live="experimental"
   ووحدة الوسوم تُظهر بجانبه شارة «تجريبي» مرئية — والعكس: لا وسم تجريبي
   على عنصر غير معلن.
2. لا إشعار يدّعي نشاطًا عصبيًا أو نجاحًا بلا نتيجة خادم.
3. الأوامر المحلية بلا مفتاح السيد لا تدّعي التنفيذ ولا تكتب في حقل مربوط.
4. رسالة الترحيب الثابتة موسومة «محلية» ولا تُنسب للذكاء، وأخطاء الاتصال
   تُنسب للنظام لا للذكاء.
5. نص الرسائل يُعرض نصًا لا HTML (إغلاق ثغرة حقن).
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
INDEX = (FRONTEND / "index.html").read_text(encoding="utf-8", errors="ignore")
MANIFEST = json.loads((FRONTEND / "LIVE_BINDINGS.json").read_text(encoding="utf-8"))
MAIN = (FRONTEND / "js/main.js").read_text(encoding="utf-8")
BADGES = FRONTEND / "js/modules/experimental-badges.js"


def _all_js_text():
    parts = []
    for p in list(FRONTEND.glob("js/**/*.js")) + list(FRONTEND.glob("ui/**/*.js")):
        parts.append((p.relative_to(FRONTEND).as_posix(), p.read_text(encoding="utf-8", errors="ignore")))
    return parts


def _tag_of(element_id):
    m = re.search(r"<[a-zA-Z]+\b[^>]*\bid=\"" + re.escape(element_id) + r"\"[^>]*>", INDEX, re.S)
    assert m, f"العنصر {element_id} غير موجود في index.html"
    return m.group(0)


def _function_body(src, name):
    start = src.index(f"function {name}(")
    # جسم الدالة يبدأ بعد «) {» لا عند أول قوس (قد يكون قيمة افتراضية مثل opts = {})
    depth, i = 0, src.index(") {", start) + 2
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    raise AssertionError(f"{name} بلا نهاية")


# 1) الوسم المرئي
def test_every_unbound_element_is_tagged_experimental():
    for u in MANIFEST["unbound"]:
        tag = _tag_of(u["element"])
        assert 'data-live="experimental"' in tag, (
            f"{u['element']} غير مربوط بلا وسم تجريبي — يعرض شيئًا ثابتًا بلا إعلان (١.٥)"
        )


def test_no_experimental_tag_on_undeclared_element():
    tagged = set(re.findall(r'<[a-zA-Z]+\b[^>]*\bid="([\w-]+)"[^>]*data-live="experimental"', INDEX, re.S))
    tagged |= set(re.findall(r'<[a-zA-Z]+\b[^>]*data-live="experimental"[^>]*\bid="([\w-]+)"', INDEX, re.S))
    declared = {u["element"] for u in MANIFEST["unbound"]}
    assert tagged == declared, f"وسوم تجريبية لا تطابق الخريطة: زائد={tagged - declared} ناقص={declared - tagged}"


def test_badges_module_renders_visible_badge_and_is_loaded():
    assert BADGES.exists(), "وحدة الشارات التجريبية غير موجودة"
    text = BADGES.read_text(encoding="utf-8")
    assert '[data-live="experimental"]' in text, "الوحدة لا تختار العناصر الموسومة"
    assert "تجريبي" in text, "الشارة لا تقول «تجريبي»"
    assert "sovereign-experimental-badge" in text
    assert "js/modules/experimental-badges.js" in INDEX, "الوحدة غير محمّلة"
    css = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in (FRONTEND / "css").glob("*.css"))
    assert ".sovereign-experimental-badge" in css, "لا نمط مرئي للشارة"


# 2) لا إشعارات منتحلة
BANNED_CLAIMS = [
    "Neural Processing Active",
    "Neural Intelligence Active",
    "Runtime Cycle Executed",
    "Sovereign Runtime Online",
]


def test_no_false_activity_notifications():
    hits = [f"{rel}: {c}" for rel, t in _all_js_text() for c in BANNED_CLAIMS if c in t]
    assert not hits, f"إشعارات تدّعي نشاطًا/نجاحًا بلا نتيجة خادم: {hits}"


# 3) الأوامر المحلية صادقة
def test_local_command_fallback_is_honest():
    body = _function_body(MAIN, "handleLocalCommand")
    assert "runtimeMode" not in body, "الأمر المحلي يكتب وضعًا مزيفًا في runtime-mode المربوط بـ/status"
    assert "تم تغيير الوضع إلى" not in body, "يدّعي تغيير وضع الخادم محليًا"
    assert "تم استلام الأمر" not in body, "يدّعي استلام الخادم لأمر لم يُرسل"
    assert "يتطلب مفتاح السيد" in body, "لا يعلن سبب عدم التنفيذ"


# 4) الترحيب والأخطاء منسوبة بصدق
def test_static_greeting_is_labeled_local():
    calls = re.findall(r"addDialogueMessage\(\s*'مرحب[^;]*;", MAIN)
    assert calls, "رسالة الترحيب غير موجودة"
    for c in calls:
        assert re.search(r"\{\s*local:\s*true\s*\}", c), f"ترحيب ثابت بلا وسم محلي: {c[:80]}"
        assert "'الذكاء السيادي'" not in c, "ترحيب ثابت منسوب للذكاء"
    body = _function_body(MAIN, "addDialogueMessage")
    assert "sender" in body.split("label:")[1].split("\n")[0], "label يتجاهل المرسل الفعلي"
    assert "local" in body and "تجريبي" in MAIN, "لا وسم مرئي للرسائل المحلية"


def test_connection_errors_not_attributed_to_ai():
    for phrase in ("لا يمكن الاتصال بالخادم", "حدث خطأ في معالجة رسالتك"):
        for m in re.finditer(r"addDialogueMessage\([^;]*" + phrase + r"[^;]*;", MAIN):
            assert "'الذكاء السيادي'" not in m.group(0), f"خطأ اتصال منسوب للذكاء: {phrase}"


# 5) نص لا HTML
def test_message_content_rendered_as_text():
    body = _function_body(MAIN, "createMessageElement")
    assert "content.innerHTML" not in body, "نص الرسالة يُحقن HTML (ثغرة حقن)"
    assert "content.textContent" in body
