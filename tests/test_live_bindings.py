"""R-730 (البند ١.٤ — بأمر المالك «توسيع ١.٤»): الربط الحي — معيار الإغلاق
«فحص آلي يطابق كل عنصر واجهة مع نقطة API».

الخريطة frontend/LIVE_BINDINGS.json تصنف كل عنصر بمعرّف في index.html.
هذا الحارس يثبت آليًا:
1. التغطية: لا عنصر في index.html بلا تصنيف (ولا تصنيف لعنصر غير موجود).
2. كل نقطة مربوطة مسار مسجل فعلًا في backend بنفس الطريقة.
3. كل حقل مربوط موجود فعلًا في استجابة backend الحقيقية (لا حقل وهمي يسقط
   إلى قيمة مزروعة — العيب الذي أظهر «75%» و«متدهور» زورًا قبل R-730).
4. كاتب واحد معلن لكل عنصر: لا وحدة أخرى تكتب فيه (عدّاد الإطارات كان يطغى
   على total_cycles الحقيقي).
5. لا محاكاة: لا قيم عشوائية/جيبية ولا «محاكاة محلية» تُعرض كبيانات حية.
6. غير المربوط يقول ذلك بصدق ولا يكتبه أي JS.
"""

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
sys.path.insert(0, str(REPO_ROOT / "backend"))

MANIFEST = json.loads((FRONTEND / "LIVE_BINDINGS.json").read_text(encoding="utf-8"))
INDEX = (FRONTEND / "index.html").read_text(encoding="utf-8", errors="ignore")
# ناقلو DOM (ينقلون عنصرًا لقسمه دون كتابة بياناته) — مسموح ذكرهم للمعرّف
MOVERS = {"js/modules/section-router.js"}


def _index_ids():
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', INDEX))


def _all_js():
    out = {}
    for p in list(FRONTEND.glob("js/**/*.js")) + list(FRONTEND.glob("ui/**/*.js")):
        out[p.relative_to(FRONTEND).as_posix()] = p.read_text(encoding="utf-8", errors="ignore")
    return out


def _classified():
    ids = set()
    for b in MANIFEST["bound"]:
        if not b.get("created_by_writer"):
            ids.add(b["element"])
    for c in MANIFEST["client"]:
        ids.add(c["element"])
    for u in MANIFEST["unbound"]:
        ids.add(u["element"])
    ids.update(MANIFEST["action_log"], MANIFEST["control"], MANIFEST["container"])
    return ids


def _routes():
    from app import app
    routes = set()
    for r in app.routes:
        for m in getattr(r, "methods", None) or []:
            routes.add((m, getattr(r, "path", "")))
    return routes


def _resolve(data, dotted):
    cur = data
    for part in dotted.split("."):
        assert isinstance(cur, dict) and part in cur, f"الحقل {dotted} غير موجود (توقف عند {part})"
        cur = cur[part]
    return cur


def _api_key():
    return os.environ.get("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


# 1) التغطية الكاملة
def test_every_index_element_is_classified():
    ids = _index_ids()
    classified = _classified()
    unclassified = ids - classified
    assert not unclassified, f"عناصر واجهة بلا تصنيف ربط (١.٤): {sorted(unclassified)}"
    phantom = classified - ids
    assert not phantom, f"تصنيف لعناصر غير موجودة في index.html: {sorted(phantom)}"


# 2) النقاط مسجلة فعلًا
def test_every_bound_endpoint_is_a_registered_route():
    routes = _routes()
    missing = []
    for b in MANIFEST["bound"]:
        method, path = b["endpoint"].split(" ", 1)
        if (method, path) not in routes:
            missing.append(b["endpoint"])
    assert not missing, f"نقاط مربوطة غير مسجلة في backend: {missing}"


def test_main_js_config_endpoints_exist():
    """كل مسار في CONFIG.API_ENDPOINTS بـmain.js مسجل فعلًا (كان HISTORY يضرب
    GET على مسار POST فقط → 405 صامت، وCOMPONENTS على مسار غير موجود)."""
    main = (FRONTEND / "js/main.js").read_text(encoding="utf-8")
    block = re.search(r"API_ENDPOINTS:\s*\{(.*?)\}", main, re.S)
    assert block, "API_ENDPOINTS غير موجود في main.js"
    paths = re.findall(r":\s*'(/[^']*)'", block.group(1))
    assert paths
    registered = {p for _, p in _routes()}
    bad = [p for p in paths if p not in registered]
    assert not bad, f"مسارات main.js غير مسجلة في backend: {bad}"


# 3) الحقول موجودة في الاستجابة الحقيقية
def test_every_bound_field_exists_in_real_response():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        for b in MANIFEST["bound"]:
            if not b.get("field"):
                continue
            method, path = b["endpoint"].split(" ", 1)
            if method == "GET":
                r = client.get(path)
            elif path == "/chat":
                r = client.post(path, json={"text": "مرحبا", "user_id": "binding_probe"})
            else:
                continue
            assert r.status_code == 200, f"{b['endpoint']} → {r.status_code}"
            _resolve(r.json(), b["field"])


def test_writer_reads_the_declared_field():
    """الكاتب المعلن يقرأ فعلًا اسم الحقل المعلن (لا اسم قديم منسي)."""
    for b in MANIFEST["bound"]:
        if not b.get("field"):
            continue
        leaf = b["field"].split(".")[-1]
        writer = b["writers"][0]
        text = (FRONTEND / writer).read_text(encoding="utf-8")
        assert leaf in text, f"{writer} لا يقرأ الحقل {b['field']} المعلن لـ{b['element']}"


# 4) كاتب واحد معلن
def test_single_declared_writer_per_element():
    js = _all_js()
    owners = {}
    for b in MANIFEST["bound"]:
        owners.setdefault(b["element"], set()).update(b["writers"])
    for c in MANIFEST["client"]:
        owners.setdefault(c["element"], set()).update(c["writers"])
    violations = []
    for element, writers in owners.items():
        pat = re.compile(r"['\"]#?" + re.escape(element) + r"['\"]")
        for rel, text in js.items():
            if pat.search(text) and rel not in writers and rel not in MOVERS:
                violations.append(f"{element} ← {rel}")
    assert not violations, (
        "وحدات غير معلنة تكتب في عناصر مربوطة (مصدر بيانات مزدوج/وهمي): "
        f"{violations}"
    )


# 5) لا محاكاة تُعرض كبيانات حية
def test_no_simulated_metrics_in_live_paths():
    main = (FRONTEND / "js/main.js").read_text(encoding="utf-8")
    assert "simulateMetricsUpdate" not in main, "محاكاة المقاييس العشوائية ما زالت في main.js"
    assert "محاكاة محلية" not in main, "main.js ما زال يدّعي نجاحًا بـ«محاكاة محلية» عند فشل الخادم"
    assert not re.search(r"currentMetrics\.\w+\s*=[^;\n]*Math\.random", main)
    assert "|| 0.75" not in main, "صحة مزروعة 75% عند غياب الحقل"
    engine = (FRONTEND / "js/modules/metrics-engine.js").read_text(encoding="utf-8")
    assert "cycles++" not in engine, "عدّاد إطارات يُعرض كدورات النظام"
    assert "Math.sin" not in engine, "طاقة حقل من موجة جيبية تُعرض كقياس"


# 6) غير المربوط صادق
def test_unbound_elements_are_honest_and_unwritten():
    js = _all_js()
    for u in MANIFEST["unbound"]:
        el = u["element"]
        pat = re.compile(r"['\"]#?" + re.escape(el) + r"['\"]")
        writers = [rel for rel, t in js.items() if pat.search(t) and rel not in MOVERS]
        if el.startswith("sovereign-section-"):
            # الأقسام يعرضها الموجّه بلافتة «قيد الربط» — لا كاتب بيانات
            writers = [w for w in writers if w != "js/modules/section-router.js"]
        assert not writers, f"{el} غير مربوط لكن تكتبه: {writers}"
    # R-733: كل خانة قيمة غير مربوطة (metric-value) تعلن «غير مربوط» نصًا
    for u in MANIFEST["unbound"]:
        tag = re.search(r'<[a-z]+\b[^>]*id="' + re.escape(u["element"]) + r'"[^>]*>\s*([^<]*?)\s*<', INDEX, re.S)
        if tag and 'class="metric-value"' in tag.group(0):
            assert tag.group(1).strip() == "غير مربوط", f"{u['element']} يجب أن يعلن «غير مربوط»"


def test_no_hardcoded_live_claims_in_header():
    """نصوص ثابتة كانت تنتحل الحياة: «Neural Link Active» ونبضها، وv2.0.0
    (والخادم 4.0.0). القيمة الابتدائية الآن «جارٍ الاتصال…»/«—» حتى تصل
    البيانات الفعلية من /health."""
    assert "Neural Link Active" not in INDEX
    assert "v2.0.0" not in INDEX
    assert 'id="version-pill"' in INDEX
