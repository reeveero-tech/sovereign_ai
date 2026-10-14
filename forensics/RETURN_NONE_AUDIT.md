# RETURN_NONE_AUDIT.md — Open item 2 (R-681)

**التاريخ:** 2026-10-15
**المرجع:** أمر التسليم — البند المفتوح 2 (فحص return None)
**القاعدة:** إما تنفيذ أو وسم صريح — لا حالة ثالثة.

---

## النتيجة

**25 موقع `except → return None` في كود الإنتاج** (باستثناء الاختبارات).

**الوسم الصريح:** البند مُوسم كـ **audit-complete, implementation-pending** — التدقيق أُنجز، الإصلاح الفعلي (توثيق كل موقع أو logging) يتطلب وقتًا أكبر من نافذة التسليم الحالية. تُتبع كـ issue.

**كيفية إعادة الإنتاج بأمر واحد:**

```bash
cd sovereign_ai && python - <<'EOF'
import ast
from pathlib import Path

REPO = Path(".")
EXCLUDED = {"tests", "backend/tests", "__pycache__", "archive", "frontend", "data", "guardian/data"}
count = 0
for p in REPO.rglob("*.py"):
    rel = str(p.relative_to(REPO))
    if any(rel.startswith(x) for x in EXCLUDED): continue
    if "__pycache__" in rel: continue
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Return) and (stmt.value is None or
                        (isinstance(stmt.value, ast.Constant) and stmt.value.value is None)):
                    count += 1
                    print(f"{rel}:{node.lineno}")
print(f"TOTAL = {count}")
EOF
```

Expected output: `TOTAL = 25`

---

## القائمة الكاملة (25 موقعًا) مع تقييم الخطورة

| # | الملف | السطر | الوحدة | الخطورة | الإجراء الموصى به |
|---|---|---|---|---|---|
| 1 | `backend/orchestrator.py` | 288 | _process_* | متوسط | توثيق + logging |
| 2 | `backend/orchestrator.py` | 299 | _process_* | متوسط | توثيق + logging |
| 3 | `backend/orchestrator.py` | 310 | _process_* | متوسط | توثيق + logging |
| 4 | `backend/orchestrator.py` | 425 | _process_* | متوسط | توثيق + logging |
| 5 | `backend/orchestrator.py` | 442 | _process_* | متوسط | توثيق + logging |
| 6 | `guardian/integrity_checker.py` | 118 | integrity check | **عالي** — فشل صامت = نزاهة | logging فوري |
| 7 | `nexus/data_pipeline/processor.py` | 55 | data pipeline | متوسط | توثيق |
| 8 | `nexus/performance/code_analyzer.py` | 51 | code analyzer | منخفض | توثيق |
| 9 | `nexus/encryption/secure_communication.py` | 83 | **تشفير** | **عالي** | logging فوري |
| 10 | `nexus/encryption/encryption_engine.py` | 77 | **تشفير** | **عالي** | logging فوري |
| 11 | `nexus/storage/long_term_store.py` | 51 | storage | متوسط | توثيق |
| 12 | `nexus/user_management/auth_engine.py` | 76 | **مصادقة** | **عالي** | logging فوري |
| 13 | `backend/memory/encoding.py` | 455 | memory encoding | متوسط | توثيق |
| 14 | `backend/memory/core.py` | 720 | memory core | متوسط | توثيق |
| 15 | `backend/sovereign/directives.py` | 37 | directives | متوسط | توثيق |
| 16 | `backend/sovereign/directives.py` | 43 | directives | متوسط | توثيق |
| 17 | `backend/compat/nexus_recommendations.py` | 43 | compat layer | منخفض | توثيق |
| 18 | `backend/compat/nexus_lifecycle.py` | 85 | compat layer | منخفض | توثيق |
| 19 | `backend/compat/nexus_lifecycle.py` | 112 | compat layer | منخفض | توثيق |
| 20 | `backend/consciousness/identity_core.py` | 722 | identity core | **عالي** | logging فوري |
| 21 | `backend/sovereign/ledger/anchor.py` | 262 | **مرساة اليدجر** | **عالي** — فشل صامت = مرساة تُقبل/تُرفض | logging فوري |
| 22 | `backend/sovereign/keys/rotation.py` | 81 | **تدوير مفتاح** | **عالي** | logging فوري |
| 23 | `backend/memory/defense/ransomware.py` | 274 | defense | **عالي** | logging فوري |
| 24 | `backend/memory/defense/ransomware.py` | 357 | defense | **عالي** | logging فوري |
| 25 | `backend/memory/biological/evolution.py` | 411 | evolution | منخفض | توثيق |

---

## التقييم النهائي

- **9 مواقع عالية الخطورة** (تشفير، مصادقة، نزاهة، مرساة، تدوير مفتاح، دفاع)
- **16 موقع متوسط/منخفض**

**الإجراء الموصى به (غير مُنفذ — يتتبع كـ issue):**
1. أضف `logger.warning()` لكل موقع عالي الخطورة (9 مواقع)
2. أضف تعليق `# TOLERATED: <reason>` لكل موقع متوسط/منخفض (16 موقعًا)
3. أعد تشغيل الماسح (test_no_silent_exceptions.py) للتأكد من عدم إضافة مواقع صامتة جديدة

**الحالة:** audit-complete, implementation-pending (tracked as issue)
