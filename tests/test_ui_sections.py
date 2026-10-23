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
    # R-735: التنقل عبر الشريط الرئيسي المرئي (لا شريط ثانٍ مخفي أسفل الصفحة)
    for sec in ("memory", "tools", "evolution"):
        assert f'data-tab="{sec}"' in c, f"قسم «{sec}» بلا زر في الشريط الرئيسي"


def test_section_router_module_real_and_loaded():
    """R-735: الموجّه المنفصل أزيل — كان يدير شريطًا ثانيًا غير مرئي وينقل حقل
    المحادثة. التبديل الحقيقي الآن عبر switchTab في main.js (الشريط الرئيسي)،
    والعزل محروس في tests/test_section_isolation.py."""
    assert not (REPO_ROOT / "frontend/js/modules/section-router.js").exists()
    idx = IDX.read_text(encoding="utf-8")
    assert "section-router.js" not in idx
    main = (REPO_ROOT / "frontend/js/main.js").read_text(encoding="utf-8")
    for pane in ("tab-memory", "tab-tools", "tab-evolution"):
        assert f"getElementById('{pane}')" in main, f"{pane} غير مسجل في switchTab"


def test_sections_declared_in_inventory():
    """بنية الأقسام موثقة في جرد الواجهة (لا هيكل صامت)."""
    inv = (REPO_ROOT / "frontend/INVENTORY.md").read_text(encoding="utf-8")
    assert "section-router.js" in inv, "إزالة الموجّه غير موثقة في الجرد"
    assert "R-735" in inv


def test_memory_section_bound_to_real_api():
    """R-728 (١.٣ توسيع): قسم الذاكرة مربوط فعليًا بنقطة /components/memory —
    إحصاءات حقيقية (core/dynamic/store) لا بيانات وهمية (بند ١.٥)."""
    mod = REPO_ROOT / "frontend/js/modules/memory-viewer.js"
    assert mod.exists(), "عارض الذاكرة مفقود"
    c = mod.read_text(encoding="utf-8")
    assert "/components/memory" in c, "العارض لا يستهلك نقطة API الفعلية"
    idx = IDX.read_text(encoding="utf-8")
    assert "memory-viewer.js" in idx, "العارض غير محمل من index.html"
