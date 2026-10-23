"""R-733 (توسيع ١.٤ — بأمر المالك «توسيع ١.٤ تابع»): ربط العنصرين الباقيين
القابلين للربط بمصدر حي فعلي.

- «الطاقة» (لا مفهوم لها في backend — كانت موجة جيبية ثم «غير مربوط») تُستبدل
  بخانة «سلامة المكونات» = عدد المكونات السليمة/الكل من /health الفعلي.
- performanceChart (لوحة فارغة أخفاها R-715 «حتى يُربط رسم حقيقي») ترسم سلسلة
  زمنية حية: المكونات السليمة + زمن استجابة /health المقاس فعلًا في المتصفح.
- قسم التطور يبقى تجريبيًا موسومًا: مصدره الحقيقي القسم ٤ (لم يُبنَ)؛ وسجل
  /agent/ledger ليس تطورًا ذاتيًا (أفعال بناء متوقفة منذ منتصف أكتوبر) — عرضه
  هناك تضليل.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
INDEX = (FRONTEND / "index.html").read_text(encoding="utf-8", errors="ignore")
MANIFEST = json.loads((FRONTEND / "LIVE_BINDINGS.json").read_text(encoding="utf-8"))
MODULE = FRONTEND / "js/modules/live-health-chart.js"


def _bound(element):
    return [b for b in MANIFEST["bound"] if b["element"] == element]


def test_only_evolution_section_remains_unbound():
    unbound = {u["element"] for u in MANIFEST["unbound"]}
    assert unbound == {"sovereign-section-evolution"}, (
        f"عناصر غير مربوطة يمكن ربطها بمصدر حي: {unbound - {'sovereign-section-evolution'}}"
    )


def test_chart_and_components_health_bound_to_health():
    for el in ("performanceChart", "metric-components-health"):
        b = _bound(el)
        assert b, f"{el} غير مربوط في الخريطة"
        assert b[0]["endpoint"] == "GET /health" and b[0]["field"] == "components"
        assert b[0]["writers"] == ["js/modules/live-health-chart.js"]


def test_energy_card_replaced_not_relabeled_fake():
    assert 'id="metric-field-energy"' not in INDEX, "خانة «الطاقة» بلا مصدر ما زالت"
    assert 'id="metric-components-health"' in INDEX
    assert "data-live=\"experimental\"" not in re.search(
        r'<[a-z]+\b[^>]*id="performanceChart"[^>]*>', INDEX).group(0), "اللوحة مربوطة ولا تزال موسومة تجريبية"


def test_module_is_real_live_consumer():
    assert MODULE.exists(), "وحدة الرسم الحي غير موجودة"
    js = MODULE.read_text(encoding="utf-8")
    assert '"/health"' in js or "'/health'" in js
    assert "setInterval" in js, "لا تحديث دوري"
    assert "getContext" in js, "لا رسم فعلي في اللوحة"
    assert "performance.now" in js, "زمن الاستجابة يجب أن يُقاس فعلًا"
    assert "=== \"healthy\"" in js or "=== 'healthy'" in js, "العد من الحالة الفعلية لكل مكون"
    assert "Math.random" not in js and "Math.sin" not in js, "لا قيم مولّدة"
    assert "js/modules/live-health-chart.js" in INDEX, "الوحدة غير محمّلة"


def test_failed_fetch_is_a_gap_not_a_fake_point():
    """فشل الجلب = فجوة معلنة («غير متصل») لا نقطة مختلقة ولا تكرار لآخر قيمة."""
    js = MODULE.read_text(encoding="utf-8")
    assert "null" in js and "غير متصل" in js


def test_monitor_extra_no_longer_hidden():
    css = (FRONTEND / "css/runtime.css").read_text(encoding="utf-8")
    assert not re.search(r"#monitor-extra\s*\{\s*display:\s*none", css), (
        "R-715 أخفى اللوحة حتى يُربط رسم حقيقي — رُبط الآن فيجب إظهارها"
    )
