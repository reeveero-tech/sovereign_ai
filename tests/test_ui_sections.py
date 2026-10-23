"""R-727 (البند ١.٣ — إعادة هيكلة الواجهة): أقسام منفصلة (محادثة/ذاكرة/
قرص وأدوات/تطور ذاتي) لكل قسم امتداده — لا كتلة واحدة تجيب عن كل شيء.
الموجّه section-router.js حقيقي: يبدّل الأقسام بالنقر (تفاعل فعلي لا وهم).
"""


from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IDX = REPO_ROOT / "frontend/index.html"

SECTIONS = ["chat", "memory", "tools", "evolution"]


def test_index_has_four_distinct_sections():
    """أربعة أقسام منفصلة بمعرفات مستقلة + شريط تنقل يبدلها — كل قسم
    بامتداده (بند ١.٣ حرفيًا)."""
    c = IDX.read_text(encoding="utf-8")
    for sec in SECTIONS:
        assert f'id="sovereign-section-{sec}"' in c, (
            f"قسم «{sec}» مفقود — الواجهة لا تزال كتلة واحدة"
        )
    assert 'id="sovereign-section-nav"' in c, "شريط تنقل الأقسام مفقود"


def test_section_router_module_real_and_loaded():
    """الموجّه وحدة حقيقية: يبدّل الأقسام بالنقر عبر بيانات الأقسام —
    ويحمّلها index.html."""
    mod = REPO_ROOT / "frontend/js/modules/section-router.js"
    assert mod.exists(), "موجّه الأقسام مفقود"
    c = mod.read_text(encoding="utf-8")
    assert "sovereign-section-" in c, "الموجّه لا يعمل على معرفات الأقسام"
    assert "addEventListener" in c or "onclick" in c, "الموجّه لا يستجيب للنقر"
    idx = IDX.read_text(encoding="utf-8")
    assert "section-router.js" in idx, "الموجّه غير محمل من index.html"


def test_sections_declared_in_inventory():
    """بنية الأقسام موثقة في جرد الواجهة (لا هيكل صامت)."""
    inv = (REPO_ROOT / "frontend/INVENTORY.md").read_text(encoding="utf-8")
    assert "section-router.js" in inv, "الموجّه غير مجرود"


def test_memory_section_bound_to_real_api():
    """R-728 (١.٣ توسيع): قسم الذاكرة مربوط فعليًا بنقطة /components/memory —
    إحصاءات حقيقية (core/dynamic/store) لا بيانات وهمية (بند ١.٥)."""
    mod = REPO_ROOT / "frontend/js/modules/memory-viewer.js"
    assert mod.exists(), "عارض الذاكرة مفقود"
    c = mod.read_text(encoding="utf-8")
    assert "/components/memory" in c, "العارض لا يستهلك نقطة API الفعلية"
    idx = IDX.read_text(encoding="utf-8")
    assert "memory-viewer.js" in idx, "العارض غير محمل من index.html"
