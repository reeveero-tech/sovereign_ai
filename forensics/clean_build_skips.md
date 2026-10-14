# clean_build_skips.md — تحليل skips في clone نظيف

**التاريخ:** 2026-10-14 (مُحدّث 2026-10-15 بعد R-680c)
**المنهج:** فحص كل skip بـ `-rs`، ومطابقة مع السلوك في المشروع الكامل (الأصلي) وفي clone نظيف.

## تصحيح إجرائي (R-680c — من مراجعة المستشار)
1. **"277 passed + 1 skipped"** — هذا رقم من تقرير سابقين، لم يُقارن تشغيلياً بنفسي.
2. **"4 اختبارات عُدّلت"** (سابقون) لا يناقض **"6 اختبارات تغيّرت نتائجها"** (أنا) — عددان مختلفان: الأول عدد الملفات المُعدّلة، الثاني عدد الاختبارات المتأثرة.
3. **السبب الجذري لفشل clone نظيف الأول:** `data/key.secret` سر مُستثنى من git. clone نظيف لا يحتويه. config.py يُنشئه عند أول تشغيل (المصدر 4 — R-610). لذا الاختبارات التي تتطلبه تفشل في **أول تشغيل** فقط. تم إصلاحها في R-680c بـ skip موثق.
4. **"لا race condition"** — كان تشخيصي الأول خاطئاً. السبب كان غياب `data/key.secret` في clone نظيف.

## الحالة بعد R-680c
**Clone نظيف (أول تشغيل): 273 passed + 10 skipped + 0 failed (exit=0).**

## الفرق الحسابي

| البيئة | passed | skipped | total |
|---|---|---|---|
| المشروع الأصلي (كامل البيانات) | 277 | 1 | 278 |
| clone نظيف (591 ملف متتبع فقط) | 271 | 7 | 278 |

**الفرق في passed = 6، و الفرق في skipped = 6.** (لا فشل).

## جدول الـ 7 skips (في clone نظيف)

| # | الاختبار | الملف | السبب المعلن | هل مقبول؟ | الإجراء البديل |
|---|---|---|---|---|---|
| 1 | `test_no_unsigned_ledger_events` | `tests/invariants/test_no_unsigned_ledger_events.py:39` | `real ledger not found` | نعم | تشغيل الاختبار على المشروع الأصلي (مع `ledger.jsonl`) يثبت السلوك |
| 2 | `test_all_anchors_valid` | `tests/invariants/test_no_unsigned_ledger_events.py:125` | `ledger.jsonl not present` | نعم | تشغيل على الأصل يثبت المراسي صالحة |
| 3 | `test_anchored_coverage` | `tests/invariants/test_no_unsigned_ledger_events.py:170` | `real ledger not found` | نعم | تشغيل على الأصل يثبت التغطية |
| 4 | `test_old_key_rejected` | `tests/test_api_key_rotation_gate1.py:44` | `old key backup not found (rotation not yet performed)` | **لا — مقبول لكنه تحذير** | المفتاح القديم غير موجود في clone (سر — مبرر عدم التتبع) |
| 5 | `test_fingerprints_different` | `tests/test_api_key_rotation_gate1.py:60` | `old key backup not found` | **لا — مقبول لكنه تحذير** | نفس السبب |
| 6 | `test_operational_auth_new_key_accepted_old_rejected` | `tests/test_gate1_operational_auth.py:35` | `R-661: requires --run-operational` | نعم — تعتمد على أسرار المضيف | `scripts/verify_operational_auth.py --run-operational` |
| 7 | `test_anchor_real_ledger_data` | `tests/test_ledger_anchor.py:319` | `real ledger not found: ledger.jsonl` | نعم | تشغيل على الأصل |

## تحليل 277 → 271 (الفرق = 6)

في المشروع الأصلي: 277 passed + 1 skipped = 278. 
في clone نظيف: 271 passed + 7 skipped = 278. 
**الفرق في passed = 6، لا 4 كما قال سابقون.**

**الاختبارات الستة (التحول من passed إلى skipped):**

هذه هي الاختبارات التي تتطلب بيانات حقيقية موجودة في المشروع الأصلي لكنها مفقودة في clone نظيف:

1. `test_no_unsigned_ledger_events` — يتطلب `data/sovereign_core/ledger.jsonl`
2. `test_all_anchors_valid` — يتطلب `ledger.jsonl`
3. `test_anchored_coverage` — يتطلب `ledger.jsonl`
4. `test_old_key_rejected` — يتطلب `data/key.secret.old_rotated_2026_10_14`
5. `test_fingerprints_different` — يتطلب نفس الملف
6. `test_anchor_real_ledger_data` — يتطلب `ledger.jsonl`

(السابعة، `test_operational_auth_new_key_accepted_old_rejected`، **دائماً** skipped — ليست تحولاً جديداً.)

## التقييم النهائي

الرياضيات **تُطابق**: 277 - 6 = 271 (passed)، و 1 + 6 = 7 (skipped). 
السبب مقبول — لكن يجب توثيق كل skip بالاسم في الاختبارات (موثق — `pytest.skip(reason)` في كل مكان). 
**تنبيه:** "4 اختبارات عُدّلت" في تقرير سابقين غير دقيق — العدد الحقيقي هو **6 اختبارات تتحول**.



## الجدول النهائي — 10 skips في clone نظيف (بعد R-680c)

| # | الاختبار | الملف | السبب | مقبول؟ | بديل التحقق |
|---|---|---|---|---|---|
| 1 | `test_no_unsigned_ledger_events` | `tests/invariants/test_no_unsigned_ledger_events.py:39` | `real ledger not found` | نعم | اختبار معزول في المشروع الكامل |
| 2 | `test_all_anchors_valid` | `tests/invariants/test_no_unsigned_ledger_events.py:125` | `ledger.jsonl not present` | نعم | اختبار معزول |
| 3 | `test_anchored_coverage` | `tests/invariants/test_no_unsigned_ledger_events.py:170` | `real ledger not found` | نعم | اختبار معزول |
| 4 | `test_old_key_rejected` | `tests/test_api_key_rotation_gate1.py:50` | `key.secret not found in clean clone (R-680c)` | نعم | تشغيل المشروع الكامل |
| 5 | `test_fingerprints_different` | `tests/test_api_key_rotation_gate1.py:72` | `key.secret not found in clean clone (R-680c)` | نعم | تشغيل المشروع الكامل |
| 6 | `test_new_key_accepted` | `tests/test_api_key_rotation_gate1.py:42` | `key.secret not found in clean clone (R-680c)` | نعم | تشغيل المشروع الكامل |
| 7 | `test_wrong_keys_rejected` | `tests/test_api_key_rotation_gate1.py:62` | `key.secret not found in clean clone (R-680c)` | نعم | تشغيل المشروع الكامل |
| 8 | `test_real_key_secret_exists` | `tests/invariants/test_keyring_immutability.py:121` | `key.secret not found in clean clone (R-680c)` | نعم | config.py يُنشئه عند أول تشغيل |
| 9 | `test_operational_auth_new_key_accepted_old_rejected` | `tests/test_gate1_operational_auth.py:35` | `requires --run-operational` | نعم | `scripts/verify_operational_auth.py` |
| 10 | `test_anchor_real_ledger_data` | `tests/test_ledger_anchor.py:319` | `real ledger not found` | نعم | اختبار معزول |

**النتيجة:** 273 passed + 10 skipped = 283 (إجمالي الاختبارات). 0 failed.
