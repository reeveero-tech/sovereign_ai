# clean_build_skips.md — تحليل 277 → 271 + 7 skips

**التاريخ:** 2026-10-14
**المنهج:** فحص كل skip بـ `-rs`، ومطابقة مع السلوك في المشروع الكامل (الأصلي) وفي clone نظيف.

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

