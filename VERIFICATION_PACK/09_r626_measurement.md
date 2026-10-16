# القسم ٦ (الجولة) — قياس R-626: الأمر والنواتج الخام على الالتزامين

## الأمر الذي أنتج قياس «صفر R-626» (على d56e24e — شجرة الـ424 نفسها)

```bash
cd /home/user/workspace/repo && SOVEREIGN_TEST_ROOT=1 timeout 900 python3 -m pytest tests/ backend/tests/ -m "not operational" --log-file=/tmp/final424b_log.log -q > /tmp/final424b_stdout.txt 2> /tmp/final424b_stderr.txt; echo "EXIT=$?"
rg -c "R-626" /tmp/final424b_log.log || echo 0
rg -c -- "--- Logging error ---" /tmp/final424b_stderr.txt /tmp/final424b_stdout.txt || echo 0
```

**الناتج الخام الكامل (بلا مقتطفات):**

```
EXIT=0
stdout (الخاتمة): 424 passed, 1 deselected in 183.33s (0:03:03)
R-626 count: 0
--- Logging error --- في stderr: 0
--- Logging error --- في stdout: 0
stderr size: 0 بايت
```

ملاحظة منهجية: أخطاء معالج التسجيل تُكتب إلى stderr لا إلى ملف --log-file — فالفحص يشمل المسارين معًا (ملف stderr فارغ بالكامل).

## الناتج الخام لـforensics/keyring_rejection_count.json على d56e24e (حرفيًا)

```
{
  "run": {
    "date": "2026-10-16",
    "purpose": "بند ٤ من جولة R-682 — عدّ أسطر الرفض في memory.core بسبب KeyRing (R-626)، مفصولة بمعرّف المفتاح",
    "command": "cd repo && python -m pytest tests/ backend/tests/ -v -m 'not operational' --log-file=<log> --log-file-level=INFO",
    "result_before_fix": "410 passed, 1 deselected, 0 failed (قبل إصلاح R-682)",
    "method": "عدّ سجلات الرفض الفعلية (ERROR من memory.core) من ملف السجل الكامل --log-file — لا نسخ traceback المكررة داخل سجلات «--- Logging error ---»"
  },
  "before_fix_r682": {
    "total_rejected_lines": 244,
    "by_key_id_desc": [
      {
        "key_id": "6530a476917b36a5",
        "rejected_lines": 244,
        "share": "100%"
      }
    ],
    "notes": [
      "الأسطر الـ244 كلها بمفتاح واحد — بصمة مفتاح اختباري أنشأته جلسة pytest نفسها (R-634 في tests/conftest.py)، وليست مفتاح تشغيل",
      "تنبيه نهائي دقيق: لم يُفصل قياسًا بين مصدري الـ244 وقت القياس الأول (الخيوط الخلفية و/أو تلوث سجل الجلسة بمفاتيح معزولة — آليتا الخطأ معًا كانتا قائمتين قبل الإصلاحين). الفصل جاء بالخطوتين: تعطيل الخيوط خفض السجل إلى 10، وإصلاح تلوث السجل خفضه إلى صفر",
      "السبب الجذري (محدد بالتتبع الكامل): (أ) خيوط خلفية daemon خارج عمر بيئتها تحتفظ بمرجع MemoryCore بمفتاح نشط قديم، و(ب) اختبارات تُنشئ SovereignCore() بلا مسارات صريحة وتُدخل فيه KeyRing معزولًا فتكتب أحداثًا في سجل الجذر المشترك للجلسة بمفاتيح ليست في keyring الجلسة (3 أحداث interaction + حدث KEY_ROTATED عبر KeyRotation بلا ledger_path) — ثم يرفض تحقق السلامة التحقق منها (فشل مغلق صحيح السلوك)",
      "الأثر الجانبي نفسه: الخيوط الباقية بعد نهاية الجلسة تكتب في ملفات سجل مغلقة فتظهر رسائل «--- Logging error ---» (3 مرات في جلسة فرعية من 5 اختبارات، ومرة في الجلسة الكاملة)"
    ]
  },
  "after_fix_r682": {
    "total_rejected_lines": 0,
    "by_key_id_desc": [
      {
        "key_id": "7bfb5770cf4efbcc",
        "rejected_lines": 10,
        "share": "100%",
        "path": "ليست من الخيوط — مسار التحقق من سلامة السجل (memory/core.py:1072→1153، verify_content_integrity)"
      }
    ],
    "evidence": [
      "الجلسة الكاملة بعد الإصلاحين معًا: 415 passed, 1 deselected, 0 failed، وصفر سطر R-626 في السجل الكامل، وصفر «--- Logging error ---» بعد الملخص (قياس 2026-10-16 22:1x)",
      "حراسة سلوكية ملتزمة: fixture جلسة في tests/conftest.py (_guard_session_ledger_key_hygiene) تفشل الجلسة إن تلوث سجل الجذر المشترك بأي حدث بمفتاح ليس في keyring الجلسة — RED مثبت على الكود القديم (4 أحداث)، GREEN بعد الإصلاح",
      "اختبار سلوكي ملتزم: tests/test_background_threads_shutdown.py (دورة حياة الخيوط + جلسة نظيفة)",
      "الآلية الكاملة: تعطيل الخيوط في بيئة الاختبار + إدارتها الموحدة + مسارات معزولة صريحة للاختبارات الدوارة"
    ]
  },
  "total_line": "الإجمالي: قبل الإصلاح 244 سطر رفض توقيع (R-626) في memory.core بمفتاح واحد — بلا فصل قياسي بين الخيوط والتلوث وقتها؛ بعد تعطيل الخيوط: 10؛ بعد إصلاح تلوث السجل (مسارات معزولة صريحة): 0"
}```

## الناتج نفسه على الالتزام السابق الذي كان R-626 يظهر فيه (60053d4 — مباشرة قبل إصلاح تلوث السجل)

الأمر: clone نظيف عند 60053d4086e13c76b93f65ae9b41e7a7d3df53f5 ثم الحزمة الكاملة بـ--log-file. الناتج الخام الكامل:

```
PYTEST_EXIT=0
stdout (الخاتمة): 410 passed, 2 skipped, 1 deselected in 179.25s (0:02:59)
R-626 count: 10
stderr bytes: 0
```

**الفرق:** 10 سطور رفض R-626 على 60053d4 (410 passed, 2 skipped) ← صفر على d56e24e (424 passed, 0 skipped). مصدر العشرة: أحداث مكتوبة في سجل الجلسة بمفاتيح معزولة (موثقة في keyring_rejection_count.json وOPERATIONAL_TESTS.md — القياس الأساس 244 كان قبل تعطيل الخيوط، ثم 10 بعد فصل مصدر الخيوط، ثم صفر بعد إصلاح تلوث السجل).
