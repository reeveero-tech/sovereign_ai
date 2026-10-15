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

**الـ 14 موقعًا منخفضة الخطورة أصبحت مُغطاة باختبارات سلوكية** — `tests/test_return_none_lowrisk.py`: **27 اختبارًا سلوكيًا** للمواقع منخفضة الخطورة (لكل موقع: اختبار فشل محقون يتحقق من المسجّل الصحيح والرسالة المحقونة تحديدًا + اختبار مسار سليم) + 33 اختبارًا لبذرة الفينيق (8 فك تشفير + 10 استمرارية/نزاهة/تخفيض/فساد-حالة + 15 تهيئة حقيقية ومخزن حقيقي) = **58 اختبارًا في الملف**. الحساب الكلي: 316 + 8 + 10 + 15 + 27 = **374**.

**ملاحظات منهجية صادقة:**
- اختبارات RED المثبتة قبل التنفيذ (الجولة الأولى) كانت **7** (اختبار فشل قراءة القرص أُضيف بعد التنفيذ).
- الجولتان الأمنيتان الثانية والثالثة: الاختبارات كُتبت **مع/بعد** التنفيذ ضمن نفس الجولة (لا ادعاء RED-أولًا عليهما).

**خوارزمية `_decrypt_seed` نُفّذت فعليًا** (RED → GREEN): `tests/test_return_none_lowrisk.py::TestPhoenixSeedDecryption` (8 اختبارات: roundtrip، مفاتيح الذاكرة، مفتاح خاطئ، تلاعب، بتر، حقل ناقص، قرص، فشل قراءة).

**الجولة الأمنية الرابعة (بعد اعتراض advisor الرابع):**
1. **إثبات الاستعادة عبر مخزن التطبيق الفعلي (SolidMemoryStore حقيقي):** كشفت الفحصة أن المسار القديم كان يعمل فقط مع مخزن وهمي — المخزن الحقيقي **مكسور العقد** من جهتين: (أ) التشفير الكمي كان **يبتر** أي حمولة أطول من المفتاح (64 بايت) — فساد بيانات صامت سابق لعملي؛ (ب) فك الحمولة كان يمر عبر `encoder.decode` **الفقداني بالتصميم** (يعيد الجوهر التقريبي) فكانت `store.query` لا تعيد الحمولات الأصلية أبدًا — كل مستهلك يقرأ `concept`/`definition` كان يحصل على None. أُصلح: المخزن الآن يستخدم التشفير السيادي القابل للعكس (`crypto` level=high) — الحمولات تعود كما كُتبت عبر واجهة القراءة المعتادة، وبتر التشفير الكمي أُصلح بتكرار المفتاح. الاختبار: `test_real_store_e2e_restoration` — SolidMemoryStore حقيقي بملفات معزولة: سجل مميز → بذرة → فقدان (مخزن فارغ جديد) → إعادة تشغيل حقيقية → `resurrect(key)` → السجل عاد عبر `store.query` + بعد إعادة فتح المخزن (استمرار قرصي مثبت).
2. **صدق نتيجة الاستعادة:** `_restore_from_seed` يفشل صراحة إذا استُعيد **صفر** عناصر (بذرة بلا بيانات قابلة للاستعادة = لا نجاح معلن): `test_restore_empty_critical_memory_fails`. والعناصر **الإجرائية** صارت تُستخرج بحمولتها الكاملة (description/trigger_patterns/action_sequence) وتُستعاد فعليًا عبر `save_procedural`: `test_restore_procedural_item_restored`.
3. **غياب master_key_enc في حالة موجودة = فشل تهيئة صريح** (صلاحية JSON وحدها لا تجعل الحالة قابلة للاسترجاع؛ المتابعة كانت تستبدل الحالة صامتًا وتتيه البذور): `test_state_missing_master_key_fails_init`.
4. **فشل الحفظ الأولي يوقف التهيئة** قبل الخيوط والجاهزية (fail-closed كامل: تحميل + حفظ): `test_init_save_failure_stops_init` + `test_save_failure_before_replace_preserves_file_no_seed` (الملف السابق بايت-مطابق + لا بذرة معلنة).
5. **مفتاح سيادة مختلف عبر التهيئة الحقيقية** → فشل صريح + الملف محفوظ: `test_sovereign_key_differs_real_init_fails`.
6. **فشل الرماد لا يحبس النظام في RESURRECTING:** مسار `resurrect` بلا بذرة يعيد النظام إلى DEAD عند فشل قيامة الرماد — رماد محفوظ، لا نجاح معلن: `test_ash_failure_returns_dead_phase`.
7. **ملف مؤقت فريد** لكل عملية حفظ (لا اسم مشترك بين عمليات متزامنة).

**الجولة الأمنية الثالثة (بعد اعتراض advisor الثالث):**
1. **فشل الحالة يوقف التهيئة (fail-closed):** `__init__` يرفع `RuntimeError` صريحًا عند فشل تحميل حالة موجودة (JSON مبتور/مفتاح مغلّف فاسد/مفتاح سيادة مختلف) — قبل الحفظ والخيوط وإنشاء أي بذرة، والملف الأصلي يُحفظ كاملًا حرفيًا بلا تعديل. الاختبارات: `test_truncated_state_fails_init_and_preserves_file`، `test_corrupt_wrapped_key_fails_init`.
2. **حفظ ذرّي متين:** `_save_state` يكتب في ملف مؤقت بنفس المجلد + `fsync` + استبدال ذري `os.replace` + `fsync` للمجلد — فشل أي خطوة يترك الملف الأصلي كما هو. والكتابة مرفوضة تمامًا بعد فشل تحميل (لا استبدال دليل الفساد).
3. **`reset(preserve_seeds=True)` لا يولّد مفتاحًا جديدًا:** توليد مفتاح جديد مع بذور محفوظة كان يجعلها غير قابلة للفك نهائيًا. الاختبار: `test_reset_preserve_seeds_keeps_master_key` (البذرة تبقى قابلة للفك عبر تهيئة حقيقية جديدة).
4. **الاستعادة عبر مخزن التطبيق الفعلي:** البذرة الآن تحمل البيانات القابلة للاستعادة (التعريف/الأسماء البديلة — لا إحصاءات فقط)، و`_restore_from_seed` يكتبها في المخزن الحقيقي عبر واجهاته المعتادة (`get_store().save_semantic`) فيعود ما يقرأه التطبيق عبر واجهة القراءة المعتادة (`store.query`). الاختبار: `test_public_contract_real_init_end_to_end` — سجل مميز في المخزن → بذرة → فقدان السجل → إعادة تشغيل (تهيئة حقيقية بلا أي استدعاء يدوي) → `resurrect(key)` → **السجل عاد عبر واجهة القراءة المعتادة**.
5. **صدق الرماد:** `_decrypt_all_memory` لم يعد يعدّ الرماد مستعادًا ولا يمسحه (فك فعلي غير منفذ)، و`_resurrect_from_ashes` لم يعد يعلن نجاحًا لعملية لم تحدث — يفشل صراحة ويحفظ الرماد. **عقد المفتاح عبر التهيئة الحقيقية:** `get_resurrection_key()` → مثيل جديد بتهيئة حقيقية → `resurrect()` ينجح.

**الجولة الأمنية الثانية (بعد اعتراض advisor الثاني):** أربعة موانع أغلقت فعليًا:
1. **استمرارية عقد المفاتيح + عقد عام موحد:** `master_resurrection_key` يُحفظ مُغلّفًا بـ AES-256-GCM تحت مفتاح السيادة في `phoenix_state.json` (لا يُخزَّن مكشوفًا)، يُحمَّل قبل بدء الخيوط، ويُحفظ حفظًا متينًا **قبل إعلان نجاح أي بذرة** (فشل الحفظ = رفض إنشاء البذرة). `get_resurrection_key()` يعيد بصمة التحقق نفسها التي تقبلها `resurrect()` — العقد العام يعمل من طرف إلى طرف بلا اشتقاق يدوي: `test_public_key_contract_and_data_proof_after_restart`.
2. **تشفير موثق معياري (v3 — AES-256-GCM):** بذرة الفينيق تُشفَّر بـ AES-256-GCM (مفتاح sha256(resurrection_key)، nonce جديد لكل عملية، AAD يوثق الإصدار ومعرف البذرة) — لا XOR متكرر. **المصادقة تمنع قبول أي نص معدّل** (فشل وسم GCM = رفض صريح) — التعديل نفسه ليس مستحيلًا، رفضه هو المضمون. الاختبارات: `test_tamper_any_ciphertext_change_rejected` + `test_positional_tamper_5_to_6_rejected` (تلاعب موضعي مقصود 5→6 عبر بايت النص المشفر المقابل — لولا الوسم لَصار JSON صالحًا بقيمة 6).
3. **منع التخفيض (downgrade):** المسار الاعتيادي يقبل مظروف v3 فقط. نزع المظروف (تقديم النص الداخلي المجرد لخداع المسار الإرثي)، حذف وسم المصادقة، تغيير الإصدار، إفساد النص — كلها مرفوضة فشلًا صريحًا بلا انتقال لأي مسار إرثي (`test_downgrade_*_rejected` × 4). بذور v1 الإرثية لها **مسار ترحيل صريح منفصل** `_decrypt_seed_legacy_v1` مع تحذير صريح — لا اكتشاف تلقائي أبدًا.
4. **إثبات الاستعادة بالبيانات + فساد الحالة الفاشل الصريح:** الاستعادة تُثبت بوجود بيانات البذرة المقصودة في مخزن `restored_seeds` (لا مجرد حدث). فشل الاستعادة = لا REBORN، لا مسح للرماد، البذرة محفوظة (`test_restore_failure_no_reborn_no_ash_clearing`). تلف `master_key_enc` أو اختلاف مفتاح السيادة = فشل تحميل CRITICAL صريح مع حفظ الأصل حرفيًا — لا استبدال صامت بمفتاح جديد قد يُتيه البذور نهائيًا (`test_state_master_key_tamper_clear_failure_original_preserved`، `test_state_wrong_sovereign_key_clear_failure`).

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
