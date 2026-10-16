# forensics/PHASE2_STATUS.md — تقرير حالة المرحلة ٢ (مرساة اليدجر) على الكود

**التاريخ:** 2026-10-16 — فحص الكود لا الوثائق
**الفحص:** قراءة فعلية للملفات + تشغيل الاختبارات + قراءة ملف المراسي الحقيقي

| المكوّن المطلوب | الحالة | الالتزام (آخر تعديل) | ما ينقص |
|---|---|---|---|
| `compute_merkle_root(events)` | **موجودة** — `compute_merkle_root(lines)` + `hash_leaf()` (sha256 لكل حدث) + `verify_merkle_root()` | `a33362c` (2026-10-15) | لا شيء |
| `anchor_batch(batch_range, keyring)` | **موجودة** — تكتب في `data/sovereign_core/ledger.anchors.jsonl` | `a33362c` | لا شيء |
| النطاق 0–116909 (reason: PRE_KEYRING_UNSIGNED_BATCH) | **موجود في الملف الفعلي** — المراسي الست تغطي 0–116909 بالكامل: الأولى `PRE_KEYRING_UNSIGNED_BATCH` (0–13486) ثم `CONTINUOUS_ANCHORING_BATCH_2/3` ثم `R640_COVER_REMAINING_EVENTS`/`R641_ANCHOR_V2` ثم `R643_FULL_COVERAGE_V2` (0–116909 — تغطية كاملة) | تاريخي (2026-10-14) | لا شيء |
| `verify_anchor(anchor, ledger)` | **موجودة** — `verify_anchor()` + `verify_anchor_detailed()` + `verify_all_anchors()`: تفشل إذا تغيّر بايت واحد في النطاق (تغيير أي حدث يغيّر جذر Merkle) | `a33362c` | لا شيء |
| مسار `/ledger/verify` | **موجود** — يُعيد: `total_events`، `verified_with_key` (المُتحقَّق منها بالمفتاح)، `total_anchors` (عدد المراسي)، `anchored_events` (المحمية بمرساة)، `unverifiable` (المجهولة/المفقود مفتاحها)، `invalid` (المزوّرة)، `legacy_pre_keyring` | `3e2b46c` (backend/app.py) | لا شيء |

## الدليل الوظيفي (تشغيل فعلي — هذه الجولة)

```
$ python -m pytest tests/test_ledger_anchor.py tests/test_ledger_verify_endpoint.py tests/test_sovereign_keys.py tests/test_key_selection_rotation.py tests/test_return_none_security.py -q
50 passed
```

## تصويح رقمي (2026-10-16 — مرحلة صفر لوكيل لاحق)

العدد الموثق في النسخة الأصلية من هذا التقرير كان **33 passed** — غير صحيح.
التشغيل الفعلي للأمر الموثق أعلاه يعطي **50 passed**، وأُثبت ذلك على الالتزام
الذي كُتب فيه التقرير نفسه (`dfd5a16`) وعلى `42446ac` (50 passed في كليهما).
التفصيل في `forensics/PHASE1_STATUS.md` (قسم التصويح الرقمي) — نفس الخطأ في
التقريرين، ونفس الحارس يمنع تكراره:
`tests/invariants/test_phase_status_numbers_match_reality.py`.

منها حرفيًا: `test_merkle_root_detects_any_change` (تغيير بايت واحد يُكشف)،
`test_verify_anchor_detects_tampering`، و`test_ledger_verify_endpoint_*` (حقول
التقرير الأربعة كلها).

## ملاحظة عائق بيانات (لا كود)

الملف الخام `data/sovereign_core/ledger.jsonl` (116,910 حدثًا) **غائب عن clone
الحالي** (غير متتبع — موثق غيابه في forensics/NEW_AGENT_INITIAL_AUDIT.md) —
المراسي موجودة وتُتحقق ضد أي نسخة مستقبلية من الأحداث؛ غياب الملف لا يعطل
الكود ولا الاختبارات (تستخدم عزلات اصطناعية موقعة).

جوهر الادعاء (كل المكونات موجودة وكاملة وعاملة) صحيح — الرقم فقط كان خطأ.

كل مكونات المرحلة ٢ موجودة وكاملة وعاملة — **لا ناقص ولا مكسور**.
