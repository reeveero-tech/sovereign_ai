# RETURN_NONE_AUDIT_R682.md — R-682 (corrected scope — re-verified by advisor R-682 final)

**التاريخ:** 2026-10-15 (re-verified) — **تحديث تنفيذي:** 2026-10-15 (تنفيذ فعلي — راجع الأسفل)
**المرجع:** أمر التسليم R-682 — Task 2.1 + advisor correction
**التصحيح:** العدد الصحيح **23 موقعًا فريدًا** (وليس 25 — كان هناك عدّ مكرر في directives.py بسبب `ast.walk()` يعبر الدوال المتداخلة).

**إعادة التحقق (R-682 final):** أُعيد تشغيل الماسح فعليًا في هذه الجلسة → `TOTAL = 23`. القائمة الكاملة 23 موقعًا كما في الكود أعلاه.

## تحديث تنفيذي (الجلسة التالية — تنفيذ حقيقي)

**الماسح (منهجية حدود الدوال) الآن: `TOTAL = 25` موقعًا** — الأصل 23 + موقعان جديدان نتجا عن تنفيذ خوارزمية فك تشفير البذرة:
- `backend/memory/defense/ransomware.py:414` — رفض صريح للحقول الإلزامية الناقصة (logger.error + exc_info)
- `backend/memory/defense/ransomware.py:674` — فشل قراءة ملف البذرة من القرص (logger.exception)

**ملاحظة منهجية:** الموقع القديم `ransomware.py:364` (stub غير المنفذ) أصبح `:431` بعد إعادة كتابة `_decrypt_seed` بخوارزمية حقيقية.

**الـ 14 موقعًا منخفضة الخطورة أصبحت مُغطاة باختبارات سلوكية** — `tests/test_return_none_lowrisk.py` (20 اختبارًا): لكل موقع اختبار فشل محقون (يُثبت التسجيل لا الصمت) + اختبار مسار سليم.

**خوارزمية `_decrypt_seed` نُفّذت فعليًا** (RED → GREEN): `tests/test_return_none_lowrisk.py::TestPhoenixSeedDecryption` (8 اختبارات: roundtrip، مفاتيح الذاكرة، مفتاح خاطئ، تلاعب، بتر، حقل ناقص، قرص، فشل قراءة).

**9 مواقع عالية الخطورة** من الـ 25 مُغطاة بـ `tests/test_return_none_security.py` (17 اختبارًا):
1. `backend/sovereign/ledger/anchor.py:262`
2. `backend/sovereign/keys/rotation.py:81`
3. `guardian/integrity_checker.py:118`
4. `nexus/encryption/encryption_engine.py:77`
5. `nexus/encryption/secure_communication.py:83`
6. `nexus/user_management/auth_engine.py:76`
7. `backend/consciousness/identity_core.py:722`
8. `backend/memory/defense/ransomware.py:274`
9. `backend/memory/defense/ransomware.py:431` (كان 364 — خوارزمية حقيقية الآن)

**14 موقعًا المتبقية** منخفضة الخطورة (لا تعالج تشفير/مصادقة/نزاهة/مرساة/تدوير مفتاح/دفاع):
- `backend/compat/nexus_lifecycle.py:85,112`
- `backend/compat/nexus_recommendations.py:43`
- `backend/memory/biological/evolution.py:411`
- `backend/memory/core.py:720`
- `backend/memory/encoding.py:455`
- `backend/orchestrator.py:288,301,314,431,450`
- `nexus/data_pipeline/processor.py:55`
- `nexus/performance/code_analyzer.py:51`
- `nexus/storage/long_term_store.py:51`

---

## كيفية إعادة الإنتاج (أمر واحد — منهجية شاملة)

**المنهجية (advisor):** يفحص داخل المعالج بما يشمل الشرط/الحلقة، لكن يتوقف عند حدود الدوال/الفئات المتداخلة.

```bash
cd sovereign_ai && python3 - << 'PYEOF'
import ast
from pathlib import Path

REPO = Path(".")
EXCLUDED = {"tests", "backend/tests", "__pycache__", "archive", "frontend", "data", "guardian/data"}

class _Finder(ast.NodeVisitor):
    def __init__(self): self.results = []
    def visit_FunctionDef(self, node): pass  # stop at nested functions
    def visit_AsyncFunctionDef(self, node): pass
    def visit_ClassDef(self, node): pass
    def visit_Return(self, node):
        if node.value is None or (isinstance(node.value, ast.Constant) and node.value.value is None):
            self.results.append(node)

sites = set()
for p in REPO.rglob("*.py"):
    rel = str(p.relative_to(REPO))
    if any(rel.startswith(x) for x in EXCLUDED): continue
    if "__pycache__" in rel: continue
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except Exception: continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            finder = _Finder()
            for stmt in node.body:
                finder.visit(stmt)  # includes if/loop, excludes nested functions
            if finder.results:
                sites.add((rel, node.lineno))

print(f"TOTAL = {len(sites)}")
for f, l in sorted(sites): print(f"{f}:{l}")
PYEOF
```

**النتيجة:** `TOTAL = 23`

**ملاحظة:** التدقيق الشامل (بما في الشرط/الحلقة) يُعيد نفس 23 موقعًا — لا يوجد `return None` إضافي داخل شرط أو حلقة ضمن المعالجات.

---

## القائمة الصحيحة (23 موقعًا)

| # | الملف | السطر | التصنيف | الإجراء (R-682) |
|---|---|---|---|---|
| 1 | `backend/orchestrator.py` | 288 | متوسط | logger.warning + R-682 tag |
| 2 | `backend/orchestrator.py` | 301 | متوسط | logger.warning + R-682 tag |
| 3 | `backend/orchestrator.py` | 314 | متوسط | logger.warning + R-682 tag |
| 4 | `backend/orchestrator.py` | 431 | متوسط | logger.warning + R-682 tag |
| 5 | `backend/orchestrator.py` | 450 | متوسط | logger.warning + R-682 tag |
| 6 | `guardian/integrity_checker.py` | 118 | **عالي** | logger.exception + [SECURITY] |
| 7 | `nexus/data_pipeline/processor.py` | 55 | متوسط | logger.exception + R-682 tag |
| 8 | `nexus/performance/code_analyzer.py` | 51 | منخفض | logger.warning + R-682 tag |
| 9 | `nexus/encryption/secure_communication.py` | 83 | **عالي** | logger.exception + [SECURITY] |
| 10 | `nexus/encryption/encryption_engine.py` | 77 | **عالي** | logger.exception + [SECURITY] |
| 11 | `nexus/storage/long_term_store.py` | 51 | متوسط | logger.exception + R-682 tag |
| 12 | `nexus/user_management/auth_engine.py` | 76 | **عالي** | logger.exception + [SECURITY] |
| 13 | `backend/memory/encoding.py` | 455 | متوسط | logger.exception + R-682 tag |
| 14 | `backend/memory/core.py` | 720 | متوسط | logger.exception + R-682 tag |
| 15 | `backend/compat/nexus_recommendations.py` | 43 | منخفض | logger.exception + R-682 tag |
| 16 | `backend/compat/nexus_lifecycle.py` | 85 | منخفض | logger.exception + R-682 tag |
| 17 | `backend/compat/nexus_lifecycle.py` | 112 | منخفض | logger.exception + R-682 tag |
| 18 | `backend/consciousness/identity_core.py` | 722 | **عالي** | logger.exception + [SECURITY] |
| 19 | `backend/sovereign/ledger/anchor.py` | 262 | **عالي** | logger.exception + [SECURITY] |
| 20 | `backend/sovereign/keys/rotation.py` | 81 | **عالي** | logger.exception + [SECURITY] |
| 21 | `backend/memory/defense/ransomware.py` | 274 | **عالي** | logger.exception + [SECURITY] |
| 22 | `backend/memory/defense/ransomware.py` | 364 | **عالي** | logger.exception + [SECURITY] |
| 23 | `backend/memory/biological/evolution.py` | 411 | منخفض | logger.exception + R-682 tag |

**ملاحظة:** `backend/sovereign/directives.py` كان يُحسب مرتين في R-681 (خطأ عدّ) — الموقع الوحيد كان `except ImportError` fallback وليس return None في except handler مباشر.

---

## المواقع التسعة عالية الخطورة — لماذا لا يُرفع الاستثناء

لكل موقع، السبب الموثق (لا يمكن الرفع لأنه يكسر تدفقًا مشروعًا):

1. **integrity_checker.py:118** — `_snapshot_file` يُستخدم في حلقة baseline؛ رفع الاستثناء سيوقف الفحص بالكامل عند أول ملف غير مقروء. **Log + skip** هو السلوك الصحيح.
2. **secure_communication.py:83** — `decode_payload` يُستخدم في مسار استقبال الرسائل؛ رفع الاستثناء سيُسقط الاتصال. **Log + None** يسمح للمرسل بإعادة المحاولة.
3. **encryption_engine.py:77** — `decrypt` يُستخدم في فك تشفير البيانات المخزنة؛ رفع الاستثناء سيُسقط التطبيق عند أي بيانات تالفة. **Log + None** يسمح بالتعافي.
4. **auth_engine.py:76** — `verify_token` يُستخدم في كل طلب؛ رفع الاستثناء سيُرجع 500 بدل 401. **Log + None** يسمح برفض آمن.
5. **identity_core.py:722** — `backup_identity` يُستخدم في الحفظ الدوري؛ رفع الاستثناء سيوقف الوعي. **Log + None** يسمح بالاستمرار.
6. **anchor.py:262** — `anchor_batch` يُستخدم في التثبيت الدوري؛ رفع الاستثناء سيوقف التثبيت. **Log + None** يسمح بالمحاولة لاحقًا.
7. **rotation.py:81** — `rotate` يُستخدم في التدوير المُجدول؛ رفع الاستثناء سيوقف التدوير. **Log + None** يسمح بالمحاولة لاحقًا.
8. **ransomware.py:274** — `create_seed` يُستخدم في الدفاع؛ رفع الاستثناء سيوقف الدفاع. **Log + None** يسمح بالاستمرار.
9. **ransomware.py:364** — `decrypt_seed` يُستخدم في القيامة؛ رفع الاستثناء سيوقف القيامة. **Log + None** يسمح بالمحاولة.

**الاختبارات:** `tests/test_return_none_security.py` — 17 اختبارًا يُثبت كل موقع.

**SECURITY_FIXES_R682.md:** توثيق كامل لكل موقع + سبب عدم الرفع + الحقيقة (تحسين تشخيصي، ليس إغلاق ثغرة).

---

## الحالة

**CLOSED** — كل موقع له logging + سبب عدم الرفع مُوثّق + اختبار يُثبت السلوك.
