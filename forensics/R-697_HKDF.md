# R-697 — فصل اشتقاق المفاتيح الغرضي (HKDF-SHA256)

> تقرير التنفيذ الكامل للجولة الأولى من ROADMAP_V3، تنفيذًا لقرار المالك
> D-033 (2026-10-17) بأمر تنفيذ R-697 (2026-10-20).
> الحقيقة هي الكود والاختبارات — هذا الملف يوثق ما حدث فعلًا، لا ما يُدَّعى.

---

## 1) المواصفة المنفذة

- **الخوارزمية**: HKDF-SHA256 حسب RFC 5869، تنفيذ بايثون خالص
  (hashlib + hmac — لا مكتبة خارجية).
- **المعاملات**: `salt=None` (يعادل HashLen أصفارًا — 32 بايتًا)،
  `info = الغرض`، الناتج 32 بايتًا (256-bit).
- **الجذر**: `SOVEREIGN_KEY` من `config.py` (IKM للاشتقاق فقط).
- **الواجهة**: `derive_key(purpose, root_key=None) -> bytes` و
  `derive_key_hex(purpose, root_key=None) -> str`.
- **الحتمية**: نفس (الجذر، الغرض) ← نفس المفتاح دائمًا (اختبار 1).
- **الغرض غير المعروف**: `ValueError` صريح — لا صمت ولا افتراضات (اختبار 3).
- **الأغراض الستة المعتمدة** (`PURPOSES` frozenset):

| الغرض | الاستهلاك القياسي |
|---|---|
| `signing` | توقيع أحداث ledger وأفعال السلامة (safety.py) وسلسلة إقلاع bootkit |
| `encryption` | تشفير حمولات المخزن (store) وختم الهوية (identity_core) ومفتاح QuantumEncoder |
| `keyring_identity` | بصمة ختم/حلقة الهوية المرتبطة بمفتاح السيد (identity_core) |
| `phoenix_seed` | بذور/مفتاح الإحياء الرئيسي وتغليفه في دورة الفينيق (ransomware) |
| `phoenix_ash` | مفاتيح موت/رماد البيانات في دورة الفينيق (ransomware) |
| `api_auth` | المصادقة القياسية للـAPI (api.py وapp.py — المقبول الجديد) |

## 2) الاختبارات السبعة الإلزامية (RED → GREEN)

الاختبارات في `backend/tests/invariants/test_key_derivation.py`:

1. `test_derive_key_deterministic` — حتمية الناتج.
2. `test_derive_key_purpose_isolated` — عزل الأغراض (مفاتيح مختلفة).
3. `test_derive_key_unknown_purpose_rejected` — رفض الغرض غير المعروف.
4. `test_signing_key_differs_from_root` — لا يساوي الجذر الخام.
5. `test_encryption_uses_derived_key_not_root` — تجسس على الاستدعاء:
   الاشتقاق يُستدعى بغرض `encryption` فعلًا (mock على وحدة identity_core).
6. `test_legacy_decrypt_path_exists_and_writes_nothing_new` — مسار فك
   التشفير التاريخي موجود ولا يكتب جديدًا بالجذر.
7. `test_all_consumers_migrated` — مسح ساكن: كل سطر في `backend/**/*.py`
   (خارج derivation.py وconfig.py والاختبارات) يذكر `SOVEREIGN_KEY` يجب
   أن يحمل وسم `LEGACY-ROOT-KEY` — لا استخدام تشفيري/توقيعي جديد للجذر.

### مرحلة RED (مُشاهدة فعلًا قبل التنفيذ)

- **المرحلة 1 — الوحدة غير موجودة** (السجل الحرفي: الملف غير ملتزم
  `r697_red_stage1.log` في محرر الجولة، الملخص أدناه):
  فشل جمع الاختبارات بـ `ModuleNotFoundError: No module named
  'backend.sovereign.keys.derivation'` — الاختبارات كُتبت قبل الكود.
- **المرحلة 2 — الوحدة موجودة، الترحيل لم يحدث** (السجل الحرفي:
  `r697_red_stage2.log`):
  `3 failed, 4 passed` — الاختبارات 1-4 (خصائص الاشتقاق نفسها) نجحت،
  والاختبارات 5-7 (الاستهلاك والترحيل والlegacy) فشلت:
  - `test_encryption_uses_derived_key_not_root` FAILED
  - `test_legacy_decrypt_path_exists_and_writes_nothing_new` FAILED
  - `test_all_consumers_migrated` FAILED

### مرحلة GREEN

- الاختبارات السبعة: `7 passed` (بعد الترحيل الكامل — وثيقة فشل وسيطة
  واحدة في test_all_consumers_migrated أثناء الترحيل أُصلحت، انظر §4).
- **الحزمة الكاملة**: `685 passed, 1 deselected` (678 القائمة + 7 الجديدة)
  في `tests/` + `backend/tests/` مع `-m "not operational"`.

## 3) الترحيل (13 ملفًا)

| الملف | الغرض المشتق | ملاحظة |
|---|---|---|
| `backend/api.py` | `api_auth` | `X-API-Key` القياسي = المشتق؛ الجذر الخام مقبول كـlegacy قراءة فقط |
| `backend/app.py` | `api_auth` | `verify_api_key` تقبل المشتق القياسي ثم الجذر legacy |
| `backend/consciousness/identity_core.py` | `encryption`, `keyring_identity` | ختم الهوية والتحقق |
| `backend/memory/biological/instincts.py` | — | استيراد كسول (قطع دائرة سبكية) |
| `backend/memory/core.py` | `signing` | مفتاح التوقيع مشتق؛ الجذر legacy للتحقق التاريخي فقط |
| `backend/memory/defense/bootkit.py` | `signing` | توقيع سلسلة الإقلاع |
| `backend/memory/defense/polymorphic.py` | — | استيراد كسول |
| `backend/memory/defense/ransomware.py` | `phoenix_seed`, `phoenix_ash` | مفاتيح الإحياء والموت |
| `backend/memory/defense/stealth.py` | — | استيراد كسول |
| `backend/memory/encoding.py` | `encryption` | مفتاح QuantumEncoder الافتراضي مشتق |
| `backend/memory/store/__init__.py` | `encryption` | مفتاح تشفير الحمولات |
| `backend/repair.py` | — | تعديل مرافق |
| `backend/safety.py` | `signing` | توليد التوقيع مشتق؛ التحقق يقبل المشتق ثم الجذر legacy |

**مسار القراءة فقط (legacy)**: كل موضع يقرأ بيانات تاريخية مشفرة/موقعة
بالجذر الخام موسوم `# LEGACY-ROOT-KEY (read-only)` في نفس السطر، ويتضمن:
فك تشفير حمولات المخزن القديمة، فك ختم الهوية القديم، تحقق توقيعات ledger
التاريخية، فك مفاتيح الفينيق القديمة (بما فيها إحياء الرماد)، والتحقق من
`X-API-Key` التاريخي. **لا مسار كتابة جديد يستخدم الجذر الخام.**

## 4) مشكلات حقيقية وُاجهت وأُصلحت (إفصاح كامل)

1. **دورات سبكية عند الاستيراد**: الاستيراد المباشر لوحدة الاشتقاق على
   مستوى الوحدة في ملفات الذاكرة سبب سلسلة
   `sovereign/__init__ → will → instincts → store → encoding (جزئي)`
   وفشل إقلاع التطبيق. الحل: استيراد كسول داخل الدوال/`__init__`
   (encoding, store, ransomware, bootkit, instincts, polymorphic,
   identity_core). الوكيل الكسول في identity_core يسمح للفحص الساكن
   بالتجسس على الاستدعاءات.
2. **خطأ تسمية في الاستيراد المزدوج**: فرع `backend.sovereign...` في
   api.py وapp.py استورد الاسم بلا alias بينما الكود يستدعي الاسم
   المُعلَّى في فرع الاستثناء → `NameError` عند التشغيل من جذر المستودع
   (22 اختبارًا فشل). أُصلح بموائمة الاسم في الفرعين.
3. **فحص ثابت مُقيد بفعل الاشتقاق**: خطوط المساعد الكسول الجديدة كانت
   تحمل النص الحرفي للمتغير بلا وسم legacy → فشل الاختبار 7. الحل:
   نقل قراءة الجذر إلى `derive_key_from_module()` داخل وحدة الاشتقاق
   نفسها (المستثناة من المسح) — والسطر في ملف الذاكرة لا يحمل النص الحرفي.
4. **احترام monkeypatch اختبارات الفينيق (R-682)**: اختباران يغيّران
   جذر السيد عبر monkeypatch على مستوى وحدة ransomware ويتوقعان فشل
   فك الحالة القديمة. الاشتقاق من config مباشرة كان سيكسرهما — الحل:
   `derive_key_from_module(purpose, globals())` يقرأ جذر الوحدة وقت
   الاستدعاء، فيبقى سلوك «مفتاح مختلف = فشل صريح» محفوظًا.

## 5) البصمة الحية (تشغيل فعلي)

- إقلاع التطبيق: `uvicorn app:app` ← `/health` يعيد
  `{"status":"healthy","version":"4.0.0",...}`.
- مصادقة API على مسار محمي (`POST /api/run`):
  - بدون مفتاح: `401` ✅
  - مفتاح مشتق (`api_auth` hex): `200` ✅
  - الجذر الخام (legacy قراءة): `200` ✅
  - مفتاح خاطئ: `401` ✅

## 6) القيود المحترمة

- `backend/compat/` و`backend/Mr.py` **لم يُلمسا** (git diff يثبت).
- الاختبارات الـ678 القائمة كلها تمر (لا كسر — الحزمة 685 = 678+7).
- لا force-push، لا amend، لا rebase — التزام ذري واحد فوق `dc07a08`.
- الحذف الوحيد: أسطر مستبدلة في الترحيل — موسومة `# DELETION-JUSTIFIED`
  وموثقة في `forensics/DELETED_LINES_AUDIT.md`.

## 7) الحالة

**R-697 مكتملة** — بانتظار CI ثم `verify.sh --full` (تطابق ثلاثي) قبل
إعلان الإغلاق النهائي في تقرير الجولة.
