# فهرس الأدلة — الجولة <2> (تشغيلات RED/GREEN الموثقة)

> أُعيد بناء الفهرس من محتوى السجلات نفسها (بعد اعتراض حكيم) — كل سطر
> مأخوذ من سطر الخلاصة الفعلي داخل السجل. الأسماء ليست شهادات؛ الحالة
> الفعلية موثقة لكل سجل. سجلات المراحل الوسيطة محفوظة بصدق كفشل تنفيذ.

## سلسلة حارس اليتامى (test_no_orphan_modules)

| السجل | الخلاصة الفعلية داخل السجل | المعنى |
|-------|------------------------------|--------|
| RED_probes_orphan_rel_init.log | 1 failed, 1 passed | مسبار x__init__ فشل (RED: الحارس أخفاه)؛ مسبار الاستيراد النسبي نجح لسبب خاطئ (فشل الحارس بسبب ملفات الحزمة، واليتيم الجذري target.py مخفي — أُثبت بتشغيل يدوي وُثّق في المحادثة) |
| GREEN_orphan_suite_after_amreen.log | 8 passed | أخضر بعد إصلاحات أمين الأولى (قبل مسبارات بصير) |
| RED_probes_baseer.log | 4 failed | RED مُشاهَد لمسبارات بصير الأربعة (مساعد غير مُجمَّع ×2، أرشيف غير مُدرج، زوج متبادل) |
| GREEN_orphan_reachability_73false.log | 11 failed, 1 passed | فشل وسيط: تحليل وصول بلا حل حزم — 73 يتيمًا زائفًا |
| GREEN_orphan_bfs_bug.log | 11 failed, 1 passed | فشل وسيط: NameError (خلل إغلاق في _try) |
| GREEN_orphan_bfs_bug2.log | 11 failed, 1 passed | فشل وسيط: الـ73 زائفًا ما زالت (اتجاه BFS معكوس) |
| GREEN_orphan_mid_fix.log | 2 failed, 1 passed | فشل وسيط: مسبار الاستيراد النسبي (دلالة وصول) + conftest شارد (R-682) |
| GREEN_orphan_mid_fix2.log | 2 failed, 1 passed | فشل وسيط: نفس السابقين قبل إعادة هيكلة المسبار |
| GREEN_orphan_suite_final.log | **12 passed** | الحزمة النهائية كاملة: الحارس + كل المسبارات خضراء |

## سلسلة حارس HISTORY (test_keyring_immutability)

| السجل | الخلاصة الفعلية | المعنى |
|-------|-----------------|--------|
| RED_keyring_delete_restore.log | 2 failed | RED مُشاهَد: الحارس قبل حذف-ثم-استعادة وحذف الملف كاملًا |
| GREEN_keyring_suite_after_amreen.log | 1 failed, 9 passed | بعد إصلاح الانتقالات: السلوكيات خضراء + الاكتشاف الجنائي على المستودع الحقيقي |
| GREEN_keyring_revlist.log | 1 failed, 10 passed | بعد rev-list --parents: نفس النمط (الاكتشاف قائم) |
| GREEN_keyring_samecount_merge_v1.log | 1 failed, 1 passed | مسبار إعادة الكتابة بنفس العدد أخضر؛ مسبار الفرع والدمج فشل (تعريف هوية git للدمج) |
| GREEN_keyring_merge_final.log | 1 passed | مسبار الفرع والدمج --no-ff أخضر بعد الإصلاح |

## سلسلة المؤشر النشط (test_no_active_lost_keys)

| السجل | الخلاصة الفعلية | المعنى |
|-------|-----------------|--------|
| RED_GREEN_active_pointer_setup_fail.log | 1 failed | فشل تجهيزي (TypeError معاملات KeyRecord) — ليس RED للفجوة |
| GREEN_active_pointer_probe.log | 1 passed | المسبار الأولي أخضر (بعد استيراد KeyRecord) |
| GREEN_merkle_and_active_pointer_v1.log | 1 failed, 1 passed | فشل NameError: hash_leaf (تجهيزي) |
| GREEN_active_pointer_real_guard.log | **1 passed** | المسبار التعاقدي النهائي: الحارس القديم الفعلي (مصدر a90b481 عبر git) قَبِل الحالة السيئة (RED بالتشغيل) والحارس الحالي الفعلي رفضها (GREEN) |

## سلسلة Merkle والمراسي

| السجل | الخلاصة الفعلية | المعنى |
|-------|-----------------|--------|
| GREEN_merkle_boundary_v1.log | 1 failed | فشل NameError: hash_leaf (تجهيزي) قبل الاستيراد |
| GREEN_merkle_and_active_pointer_v1.log | (أعلاه) | — |
| GREEN_merkle_integral.log | **1 passed** | المسبار التكاملي الموقّع: مرساة صحيحة تُقبل، التزوير المُعاد التفسير يُرفض بالتوقيع |
| GREEN_real_anchors_coverage.log | **1 passed** | فحص البيانات الحقيقية المتتبعة: المراسي تغطي [0,116909] بلا فجوات + مرساة v2 شاملة |

## الحزم النهائية

| السجل | الخلاصة الفعلية | المعنى |
|-------|-----------------|--------|
| GREEN_invariants_all.log | 2 failed, 123 passed | فشلان معروفان: أثر بيئة FastAPI + الاكتشاف الجنائي R2-2 |
| GREEN_full_suite.log | **2 failed, 518 passed, 1 deselected** | الحزمة الكاملة `timeout 600 python -m pytest tests/ backend/tests/ -q -m "not operational"` — الفشلان محددان وموثقان، CI هو الفاصل |

## الحقيقة النهائية (518/2/1)

الفشلان: (1) test_all_registered_routes_respond — أثر بيئة محلي معروف
(FastAPI 0.143.3 محلي مقابل 0.115.0 المثبت في CI — موثق منذ الجولة <1>)؛
(2) test_keyring_history_immutable — الاكتشاف الجنائي R2-2 (الحارس يعمل
كما صُمم؛ واقعة تاريخية حقيقية تنتظر قرار المالك). ليست حزمة خضراء —
الدفع متوقف بقرار بروتوكولي حتى قرار المالك.

## السجل الختامي

| السجل | الخلاصة الفعلية | المعنى |
|-------|-----------------|--------|
| GREEN_final_three_guards.log | 1 failed, 36 passed | الحارسة الثلاثة معًا: 36 سلوكيًا أخضر + فشل الاكتشاف الجنائي وحده (R2-2) — الحالة النهائية قبل عرض القرار على المالك |

## سجلات تنفيذ قرارات المالك (المرحلة الأخيرة)

| السجل | الخلاصة الفعلية | المعنى |
|-------|-----------------|--------|
| GREEN_keyring_r22_grandfather.log | 14 passed | حد الجدّ R2-2: الحارس أخضر والاكتشاف الجنائي مؤرَّش كاستثناء تاريخي |
| RED_merkle_v2.log | 2 failed | RED مُشاهَد لاختباري v2 قبل التنفيذ (الدالة غير موجودة) |
| GREEN_merkle_v2_wiring.log | 40 passed + فشلان وسيطان | إصلاحات الربط (استيراد + مرساة يدوية v2) |
| GREEN_anchor_rejects_v2.log | 12 passed | ملف اختبار الرفض كاملًا على v2 |
| GREEN_fastapi_pin.log | 8 passed | تثبيت التبعيات: أثر بيئة FastAPI انتهى محليًا (اختبار المسارات ينجح) |
| GREEN_full_suite_525.log | **525 passed, 1 deselected** | الحزمة الكاملة بعد كل القرارات — صفر فشل |

## دورة التسليم الفعلية (ما بعد 1a9141f)

| التشغيل | النتيجة | ملاحظة |
|---------|---------|--------|
| CI على 1a9141f (39057505124) | **فشل — رفض زائف** | بوابة Issue #8 رفضت رغم أن العلامة في فرق الالتزام 4 مرات: عطل grep -q/SIGPIPE/pipefail (الإثبات: GREEN_ci_gate_sigpipe_fix.log) |
| CI على 6ef6e89 (39057708298 — بعد إصلاح البوابة) | **أخضر — 525 passed, 1 deselected** | يغطي الترويسة النهائية بكل التزامات الجولة |
| verify-full (39057964408) | **VERIFICATION COMPLETE — 525 passed, 0 skipped, 0 failed** (من clone نظيف على 6ef6e89) | المطابقة الثلاثية: محلي 525/0/0 + CI 525/0/0 + تحقق كامل 525/0/0 |
