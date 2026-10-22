"""حارس جرد الواجهة (البند ١.١ / R-723): كل ملف JS في الواجهة يجب أن يكون
مدرجًا في frontend/INVENTORY.md — وحدة غير مجرودة = رفض الدفعة. الجرد هو
أساس البند ١.٢ (إزالة الوهم) فلا يجوز أن يتقادم صامتًا.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
INVENTORY = FRONTEND / "INVENTORY.md"


def _frontend_js_files():
    return sorted(
        list((FRONTEND / "js").glob("*.js"))
        + list((FRONTEND / "js/modules").glob("*.js"))
        + list((FRONTEND / "ui").glob("*.js"))
    )


def test_inventory_covers_all_frontend_js_modules():
    """كل وحدة حالية مجرودة — أي وحدة جديدة يجب أن تُدرج في نفس الالتزام."""
    assert INVENTORY.exists(), "frontend/INVENTORY.md مفقود — البند ١.١ غير منفذ"
    text = INVENTORY.read_text(encoding="utf-8")
    listed = set(re.findall(r"\|\s*`([A-Za-z0-9_.-]+\.js)`\s*\|", text))
    missing = [p.name for p in _frontend_js_files() if p.name not in listed]
    assert not missing, (
        f"وحدات واجهة غير مجرودة في INVENTORY.md: {missing} — "
        "أي وحدة جديدة تُدرج في الجرد في نفس الالتزام (حارس ١.١)"
    )


def test_inventory_has_honest_verdict_counts():
    """الجرد يوثق العدّة الصادقة (مباشرة/وسيطة/زخرفية) — لا جرد بلا حكم."""
    text = INVENTORY.read_text(encoding="utf-8")
    for label in ("تستهلك API مباشرة", "تعمل بالأحداث", "زخرفية بحتة", "المجموع"):
        assert label in text, f"الجرد ينقصه تصنيف «{label}» — الجرد بلا حكم صادق ناقص"


# -------------------------
# R-724 (البند ١.٢): الوحدات الزخرفية البحتة أزيلت — لا عودة للوهم
# -------------------------

REMOVED_DECORATIVE = [
    "dialogue-engine.js", "legacy-cleanup.js", "neural-animation-engine.js",
    "render-engine.js", "runtime-access.js", "runtime-cache.js",
    "runtime-execution-sandboxes.js", "runtime-migration-manager.js",
    "runtime-queue-intelligence.js", "runtime-scheduler.js",
    "runtime-unified-registry.js",
    # R-725 (١.٢ مرحلة ٢): ناشرون اصطناعيون (مؤقتات/عشوائية + نشر أحداث، بلا
    # أي استخدام فعلي من الكود المتبقي — مسارح نشاط ذاتية)
    "runtime-adaptive-scheduler.js", "runtime-analytics.js", "runtime-bus.js",
    "runtime-domain-router.js", "runtime-execution-scheduler.js",
    "runtime-intelligence.js", "runtime-kernel.js", "runtime-lifecycle.js",
    "runtime-policy-engine.js", "runtime-session-policies.js",
    "runtime-signals.js",
]


def test_removed_decorative_modules_stay_removed():
    """الـ11 الزخرفية البحتة (جرد ١.١) أزيلت بأمر المالك (١.٢) — لا تحميل
    من index.html ولا وجود للملفات. إعادتها تحتاج أمر المالك وتوثيقًا."""
    idx = (FRONTEND / "index.html").read_text(encoding="utf-8", errors="ignore")
    for name in REMOVED_DECORATIVE:
        assert name not in idx, (
            f"{name} عاد للتحميل من index.html — وحدة زخرفية أزيلت بأمر المالك (١.٢)"
        )
        assert not (FRONTEND / "js/modules" / name).exists(), (
            f"ملف {name} عاد للوجود — إعادة وحدة زخرفية تحتاج أمر المالك وتوثيقًا"
        )
