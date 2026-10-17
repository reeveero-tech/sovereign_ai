هذا التقرير مُنتَج بأدوار مُنفصلة على نفس النموذج — ليس مراجعة مستقلة، بل مراجعة عدائية منظمة.

# RED_GREEN_PROOF — إثبات RED→GREEN حرفي (الإعادة الثالثة — أمر المالك)

## إفصاح الجولتين السابقتين

التشغيل الأول (داخل d4d9983): 16 failed / 1 passed — فحص السجل الخام كشف
أن ثلاثة من الإخفاقات كانت آثار تركيب لا سلوكًا (NameError ×2 لاستيراد
KeyRecord ناقص في بناء الحالة + فشل اختبار التثبيت لأن متطلبات الأساس
لم تكن تحوي تثبيت starlette — صالح كدليل على فجوة غياب التثبيت لكنه لا
يثبت رفض انحراف الإصدار). لا يُحسب دليلًا. التشغيل الثاني (داخل d0d78e4):
البناء صحيح (15 failed / 2 passed سلوكي خالص) لكن الملف المودع أوامره
كانت نائبة («<17 node ID>») ووصف مسبار لاحقة الاستيراد كان غير دقيق —
تراجع بأمر المالك. هذا الملف: الأمر الحرفي الكامل + وصف كل إخفاق بدقة.

## حالة RED — الكود والبيئة قبل الإصلاح

- الكود: نسخة عند 1337a3f (= شجرة a90b481: الحارسان القديمان
  بمقارنة HEAD/HEAD~1 والمصفيات الواسعة) مع الملفات الثلاثة المعدلة
  لبناء الحالة (القاعدة القديمة الحرفية + المسبارات الجديدة ملحقة +
  الاستيراد الكامل KeyRecord/_active_pointer_contradictions).
- البيئة: venv بايثون 3.11 خارج شجرة النسخة، مثبت فيها fastapi==0.143.3
  وstarlette==1.8.0 (المنحرفان عن المثبت)، والمتطلبات في الشجرة هي
  النسخة المثبتة المصلاة (fastapi==0.115.0 وstarlette==0.38.6).

## الأمر الحرفي الكامل (قابل للنسخ واللصق — RED)

```
python -m pytest backend/tests/invariants/test_keyring_immutability.py::test_no_active_lost_keys_catches_bad_active_pointer backend/tests/invariants/test_keyring_immutability.py::test_history_guard_catches_old_committed_deletion backend/tests/invariants/test_keyring_immutability.py::test_history_guard_catches_delete_then_restore backend/tests/invariants/test_keyring_immutability.py::test_history_guard_catches_whole_file_deletion backend/tests/invariants/test_keyring_immutability.py::test_history_guard_catches_rewritten_same_count backend/tests/invariants/test_keyring_immutability.py::test_history_guard_catches_branch_delete_with_merge backend/tests/invariants/test_keyring_immutability.py::test_active_pointer_red_green_on_real_guard backend/tests/invariants/test_no_orphan_modules.py::test_guard_catches_stray_script backend/tests/invariants/test_no_orphan_modules.py::test_guard_catches_stray_named_like_backup backend/tests/invariants/test_no_orphan_modules.py::test_guard_does_not_mark_orphan_imported_via_nonrelative_import backend/tests/invariants/test_no_orphan_modules.py::test_guard_relative_import_resolves_only_relative backend/tests/invariants/test_no_orphan_modules.py::test_guard_catches_stray_double_underscore_init backend/tests/invariants/test_no_orphan_modules.py::test_guard_catches_unreferenced_test_helper backend/tests/invariants/test_no_orphan_modules.py::test_guard_catches_unreferenced_backend_test_helper backend/tests/invariants/test_no_orphan_modules.py::test_guard_catches_unlisted_archive_file backend/tests/invariants/test_no_orphan_modules.py::test_guard_catches_mutual_import_pair backend/tests/invariants/test_dependency_pins.py::test_fastapi_version_pinned -q --no-header
```

المخرجات (السجل الخام الكامل: RED_run_corrected_raw.log):
```
15 failed, 2 passed, 2 warnings in 10.69s
```

## أسباب الإخفاق الخمسة عشر — كلها AssertionError بسبب الثغرات (لا NameError ولا إخفاق بناء)

حارس HISTORY (4):
- old_committed_deletion: AssertionError «deletion committed 3 commits
  ago must be caught — the invariant is append-only FOREVER» — الحارس
  القديم (مقارنة HEAD/HEAD~1 فقط) لم يرَ حذفًا أقدم من التزامين.
- delete_then_restore: AssertionError «delete-then-restore must be
  caught as a permanent violation» — المقارنة النهائية فقط كانت تمحو
  الحذف المستعاد.
- whole_file_deletion: AssertionError «whole-file deletion must be
  caught — restoring identical content must not erase the violation».
- branch_delete_with_merge: AssertionError «branch-side deletion must be
  caught despite --no-ff merge and identical final content».
- المسبار المزدوج (active_pointer_red_green_on_real_guard): Failed
  «DID NOT RAISE» — الحارس الحالي في حالة RED (القديم) قبل مؤشرًا
  نشطًا يشير إلى مفتاح LOST بدل رفضه.

حارس اليتامى (9):
- stray_script: AssertionError «guard must FAIL while a stray unimported
  script exists in scripts/» — المصفّي الواسع كان يعفي scripts/ كاملة.
- stray_named_like_backup: AssertionError «guard must FAIL while a stray
  file named like a backup exists outside the owner-deferred backup
  paths» — مطابقة اللاحقة كانت تُخفيه.
- does_not_mark_orphan_imported_via_nonrelative_import: AssertionError
  «orphan must be named in failure output» — الثغرة: الحارس القديم كان
  يطابق لاحقة الاستيراد غير النسبي (import guardian.orphan_probe_
  module) مع أي ملف يحمل الاسم الأخير فيُصنّف اليتيم «مستوردًا» —
  اليتيم لم يُذكر في مخرج الحارس إطلاقًا بينما ذُكر المستورد.
- relative_import_resolves_only_relative: AssertionError «guard must
  FAIL while a root orphan shares a relative import's module name» —
  حل الاستيراد النسبي عبر المطلق كان يخفي اليتيم.
- stray_double_underscore_init: AssertionError «guard must FAIL while a
  stray file whose name ends with __init__.py exists».
- unreferenced_test_helper وunreferenced_backend_test_helper:
  AssertionError «guard must FAIL while an unreferenced non-collected
  helper exists in tests/ (backend/tests/)» — إعفاء البادئة كان
  يخفيهما.
- unlisted_archive_file: AssertionError «guard must FAIL while an
  unlisted file exists in archive/» — الإعفاء المجلدي كان يخفيه.
- mutual_import_pair: AssertionError «guard must FAIL while a
  mutually-importing pair with NO entry point exists» — الزوج
  المتبادل كان يحل بعضه لبعض دون وصول من الجذور.

اختبار التثبيت (1):
- test_fastapi_version_pinned: AssertionError «fastapi 0.143.3 is
  installed but requirements.txt pins 0.115.0 — silent upgrade
  detected» — التوكيد السلوكي نفسه للترقية الصامتة.

## الناجحان في RED (موثقان — ليسا فجوتين)

- test_history_guard_catches_rewritten_same_count: الحارس القديم يلتقط
  إعادة الكتابة بمكان الأسطر أصلًا (انتهاك البادئة مرئي في
  HEAD~1→HEAD).
- test_no_active_lost_keys_catches_bad_active_pointer: مسبار توثيقي
  يختبر المنطقين (القديم والجديد) داخليًا فينجح في الحالتين — فجوة
  المؤشر النشط موثقة بالمسبار المزدوج أعلاه (DID NOT RAISE).

## تطبيق الإصلاح ثم GREEN — الأمر الحرفي الكامل

```
git checkout d0d78e4 -- .
pip install fastapi==0.115.0 starlette==0.38.6
```
ثم نفس أمر pytest الحرفي أعلاه (الـ17 معرفًا كما هي، حرفيًا).

المخرجات (السجل الخام الكامل: GREEN_run_corrected_raw.log):
```
17 passed, 2 warnings in 20.35s
```

## تسلسل التحقق المعتمد بقرار المالك (2026-10-18)

1. محليًا قبل الدفع: لا NameError (الحزمة الكاملة خضراء 525 ناجحًا /
   صفر فشل / صفر تخطٍ) + ‏pip install -r requirements.txt يمر بلا أخطاء.
2. الدفع.
3. CI أخضر على الالتزام نفسه.
4. ‏verify.sh --full من clone نظيف عند الالتزام: EXIT=0 مع التطابق
   الثلاثي (Local + CI + Clone). ملاحظة بنيوية موثقة: خطوة المقارنة في
   وضع --full تتطلب تشغيل CI على الـSHA نفسه فلا تكتمل قبل الدفع —
   لذلك اعتمد المالك هذا الترتيب صراحة. سجل التشغيل الكامل للتحقق على
   الالتزام يُرفق بالتسليم (verify_full_local.log) وأرقام تشغيلات CI
   في جدول التسليم.
