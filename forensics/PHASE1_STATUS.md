# forensics/PHASE1_STATUS.md — تقرير حالة المرحلة ١ (KeyRing) على الكود

**التاريخ:** 2026-10-16 — فحص الكود لا الوثائق (الأمر: «افحص الكود»)
**الفحص:** قراءة فعلية للملفات + تشغيل الاختبارات (50 passed لملفات المرحلتين — تصويح رقمي 2026-10-16، راجع «تصويح رقمي» أسفل الملف)

| الملف | الحالة | الالتزام (آخر تعديل) | ما ينقص |
|---|---|---|---|
| `backend/sovereign/keys/__init__.py` | **موجود وكامل** — يُصدّر KeyRing/KeyRecord/KeyStatus/SignatureVerifier/VerificationResult/VerificationStatus/KeyRotation | `68959a3` (2026-10-14) | لا شيء |
| `keyring.py` — `KeyRecord` | **موجود وكامل** — كل الحقول المطلوبة: `key_id` (sha256 أول 16 حرفًا من البصمة)، `public_key`، `private_key` (اختياري — None للمفقود/المتقاعد)، `valid_from`/`valid_until` (ISO8601)، `reason_for_retirement` ("lost"/"rotated"/"compromised"/"expired")، `notes` | `dfc6198` (2026-10-14) | لا شيء |
| `keyring.py` — `load_from_disk()`/`save_to_disk()` | **موجودة** + `_append_history()` يكتب `data/keys/HISTORY.jsonl` | `dfc6198` | لا شيء |
| `verifier.py` — `SignatureVerifier` | **موجود وكامل** — `extract_event_data()` يستخرج بيانات الحدث، `verify_event()` يفرّق صراحة: مفتاح غير موجود → `UNVERIFIABLE_MISSING_KEY` (لا نعرف) / توقيع لا يطابق مفتاحًا معروفًا → `INVALID` (مزوّر) — لا خلط بينهما (موثق في رأس الملف) | `97160c8` (2026-10-14) | لا شيء |
| `rotation.py` — `KeyRotation.rotate(reason)` | **موجودة وكاملة** — تُنتج مفتاحًا جديدًا، تُسجّل القديم `retired`، تكتب حدث `KEY_ROTATED` موقّعًا بالمفتاح الجديد (+ `ledger_path` اختياري) | `a33362c` (2026-10-15) | لا شيء |
| `data/keys/HISTORY.jsonl` | **موجود** — 3 أسطر (KEY_CREATED × 3)؛ **لا يُحذف منه سطر**: محمي باختبار ثابت `tests/invariants/test_keyring_immutability.py` (مقارنة بلقطة git) | `a4c3154` (2026-10-14) | لا شيء |

## الدليل الوظيفي (تشغيل فعلي — هذه الجولة)

```
$ python -m pytest tests/test_sovereign_keys.py tests/test_key_selection_rotation.py tests/test_return_none_security.py tests/test_ledger_anchor.py tests/test_ledger_verify_endpoint.py -q
50 passed
```

## تصويح رقمي (2026-10-16 — مرحلة صفر لوكيل لاحق)

العدد الموثق في النسخة الأصلية من هذا التقرير كان **33 passed** — هذا غير
صحيح. التشغيل الفعلي للأمر الموثق أعلاه يعطي **50 passed**، وقد أُثبت ذلك:

1. على HEAD الحالي وقت التصويب (`dfd5a16`): 50 passed.
2. على الالتزام الذي كُتب فيه هذا التقرير نفسه (`42446ac`) عبر git worktree:
   50 passed — أي أن الرقم كان خاطئًا وقت كتابته، لا أن الاختبارات زادت بعده
   (توزيع الملفات الخمسة: 11 + 5 + 17 + 12 + 5 = 50).
3. حارس نزاهة دائم أُضيف لمنع التكرار:
   `tests/invariants/test_phase_status_numbers_match_reality.py` (فشل RED فعلي
   على الرقم الخاطئ قبل التصويب، ونجح GREEN بعده).

ما تحقق منه فعليًا في جولة التصويح: كل ملفات المرحلة موجودة كما يوثق الجدول أعلاه + الأمر الموثق ينجح كاملًا (50 passed). ما لم يتحقق منه داخل clone: لا شيء هنا يتطلب أحداثًا أصلية — الرقم فقط كان خطأ.

كل مكونات المرحلة ١ (خمسة ملفات + HISTORY) موجودة وكاملة وعاملة — **لا ناقص ولا مكسور** (نطاق ما تحقق منه فعليًا: راجع «تصويح رقمي» أعلاه).
