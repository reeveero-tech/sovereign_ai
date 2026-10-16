# سجل تشغيل إثبات RED — قلب بايت واحد (2026-10-16)

أثر تشغيل فعلي ملتقط (الجولة الإنشائية — تصويب المراجع، الاعتراض 8).
الدورة تُعاد كاملة في كل تشغيل للاختبار
`backend/tests/invariants/test_no_unsigned_ledger_events.py::test_single_byte_tamper_run_log`
(عبر `SOVEREIGN_SYNTHETIC_LEDGER_DIR` + وضع `reuse_existing`) — هذا الملف
أثر تنفيذ يدوي مطابق موثَّق، والاختبار أعادها في كل تشغيل.

## الخطوات

1. بناء سجل تجريبي سليم (مواقعة + مرساة موقعة + مفاتيح) في جذر معزول.
2. تشغيل الحارس `test_all_anchors_valid` عبر سب-بروسس على الدليل النظيف.
3. قلب بايت ASCII واحد (استبدال رقم برقم آخر داخل حدث مُرسى) — الفرق
   المُثبت على مستوى الملف كله: **بايت واحد بالضبط**، والسطر يبقى JSON
   صالحًا.
4. إعادة تشغيل الحارس على البيانات المعبوثة.
5. استعادة البايت وإعادة التشغيل.

## الأثر الملتقط

```
=== CLEAN RUN ===
exit_code: 0
1 passed in 0.14s

=== TAMPER ===
byte_diff: 1 (must be exactly 1)

=== TAMPERED RUN ===
exit_code: 1
merkle root mismatch: expected de6e28a6c3e810a3..., got 023c704e2d585cdf...
— content was modified
FAILED test_all_anchors_valid
1 failed in 0.09s

=== RESTORED RUN ===
exit_code: 0
1 passed in 0.07s
```

## الدلالة

- فشل الحارس سببه عدم تطابق جذر ميركل (العبث الفعلي) — لا خطأ جمع أو
  استيراد.
- الفشل قابل للعكس: استعادة البايت الواحد تعيد النجاح.
- نفس نمط المسبار مطبق في RED الحدث غير المصنف
  (`test_unclassified_event_rejected`): الحارس الحقيقي يفشل بسبب
  `unclassified` ثم ينجح بعد إزالة الحدث الدخيل.
