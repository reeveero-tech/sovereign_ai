هذا التقرير مُنتَج بأدوار مُنفصلة على نفس النموذج — ليس مراجعة مستقلة، بل مراجعة عدائية منظمة.

# RED_GREEN_PROOF — إثبات RED→GREEN حقيقي (نسخة مصححة معروضة للمراجعة قبل الالتزام)

## إفصاح الجولتين

**التشغيل الأول (معيب — كان ضمن d4d9983):** 16 failed / 1 passed، لكن فحص
السجل الخام كشف أن ثلاثة من الإخفاقات كانت آثار تركيب لا سلوكًا:
مسبارا المؤشر النشط فشلا بـNameError (استيراد KeyRecord ناقص في بناء
الحالة)، واختبار التثبيت فشل لأن متطلبات الأساس (a90b481) لم تكن تحوي
تثبيت starlette — إخفاق صالح لفجوة «غياب التثبيت» لكنه لا يثبت رفض
انحراف FastAPI. لا يُحسب هذا التشغيل دليلًا على الفجوات الثلاث.

**التشغيل المصحح (أُعيد بناؤه وتشغيله في نسخة معزولة):** الحالة = قاعدة
a90b481 الحرفية (الحارسان القديمان بدوالهما الكاملة من git show) +
المسبارات الجديدة + الاستيراد الكامل (KeyRecord و_active_pointer_
contradictions) + متطلبات مثبتة مصلاة + بيئة منحرفة فعليًا (fastapi
0.143.3 / starlette 1.8.0) في venv خارج شجرة النسخة (عزل داخلي كان
يلوث حارس اليتامى بـ1724 وحدة من site-packages).

## أوامر التشغيل الفعلية (التشغيل المصحح)

حالة الكود: نسخة عند a8cbf0f (= شجرة a90b481) مع الملفات المعدلة
للبناء أعلاه. حالة البيئة: venv بايثون 3.11 + fastapi==0.143.3.

التشغيل (RED):
```
python -m pytest <17 node ID للمسبارات الجديدة> -q --no-header
```
المخرجات (كاملة في RED_run_corrected_raw.log):
```
15 failed, 2 passed, 2 warnings in 10.69s
```

تطبيق الإصلاح:
```
git checkout d4d9983 -- .
pip install fastapi==0.115.0 starlette==0.38.6
```

التشغيل (GREEN):
```
python -m pytest <نفس الـ17 node ID> -q --no-header
```
المخرجات (كاملة في GREEN_run_corrected_raw.log):
```
17 passed, 2 warnings in 20.35s
```

## أسباب الإخفاق الخمسة عشر — توكيدات سلوكية من أقسام الفشل (لا سطور FAILED مضمّنة)

- test_history_guard_catches_old_committed_deletion:
  «deletion committed 3 commits ago must be caught — the invariant is append-only FOREVER»
- test_history_guard_catches_delete_then_restore:
  «delete-then-restore must be caught as a permanent violation»
- test_history_guard_catches_whole_file_deletion:
  «whole-file deletion must be caught — restoring identical content must not erase the violation»
- test_history_guard_catches_branch_delete_with_merge:
  «branch-side deletion must be caught despite --no-ff merge and identical final content»
- test_active_pointer_red_green_on_real_guard: «DID NOT RAISE» —
  الحارس الحالي (القديم في حالة RED) قبل الحالة السيئة بدل رفضها
- مسبارات حارس اليتامى التسعة، كلها: «guard must FAIL while ...» —
  الحارس القديم كان يمرر الحالات المخفية (stray script في scripts/،
  المسمى كنسخة احتياطية، الزوج متبادل الاستيراد بلا نقطة دخول، ملف
  archive/ غير المدرج، المساعدات غير المستوردة، ملف لاحقة __init__.py،
  والاستيراد النسبي المحلول عبر المطلق — والناجح الوحيد في الاتجاه
  السالب: الحارس القديم كان يعلم ملفًا مشروعًا يتيمًا زائفًا)
- test_fastapi_version_pinned: «fastapi 0.143.3 is installed but
  requirements.txt pins 0.115.0 — silent upgrade detected»

## الناجحان في RED (موثقان لا خافيان)

- test_history_guard_catches_rewritten_same_count: الحارس القديم كان
  يلتقط إعادة الكتابة بمكان الأسطر أصلًا (انتهاك البادئة مرئي في
  HEAD~1→HEAD) — ليس فجوة.
- test_no_active_lost_keys_catches_bad_active_pointer: مسبار توثيقي
  يختبر المنطقين (القديم والجديد) داخليًا — لا يصلح RED بطبيعته؛
  فجوته موثقة بالمسبار الآخر (DID NOT RAISE أعلاه).

## التحقق المحلي الكامل (على الترويسة d4d9983)

```
git clone <repo> verify311 && cd verify311 && git checkout d4d9983
uv venv --python 3.11 /tmp/verifyvenv && uv pip install -r requirements.txt
bash verify.sh --full
```
المخرجات (verify_full_local_311.log): «GATE OK: 525 passed, 1 deselected»،
«بوابة الاختبارات ناجحة: 525 passed, 0 skipped, 0 failed»،
«VERIFICATION COMPLETE»، **VERIFY_EXIT=0** — بوابة إصدار Python 3.11
عبرت دون تعديل أو تجاوز.
