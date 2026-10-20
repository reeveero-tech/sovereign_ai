# GS-3 — دليل RED→GREEN لتوسيع حارس العناوين (قرار المالك د.٣)

> مخرجات حقيقية (`pytest -rA` مجمّعة، رموز خروج فعلية). العناوين في E2E مقنّعة `<masked>` (القاعدة ٨).
> المراحل بُنيت بتبديل النواة: المرحلة ٠ = النطاقات الثلاثة لـ IPv4 فقط (= سلوك الحارس الحالي).

```
=== STAGE 0 — النواة بنطاقات IPv4 فقط (= الحارس الحالي)، بلا hook — RED متوقع للنطاقين والـhook
      1 9 failed, 10 passed, 1 warning, 4 errors in 0.34s
      1 ERROR tests/test_private_ip_guard_ipv6.py::test_pre_commit_hook_allows_clean_commit
      3 ERROR tests/test_private_ip_guard_ipv6.py::test_pre_commit_hook_blocks_private_address
      4 FAILED tests/test_private_ip_guard_ipv6.py::test_link_local_detected
      5 FAILED tests/test_private_ip_guard_ipv6.py::test_ula_detected
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_ipv4_pattern_in_sync_with_ci_guard
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_no_private_ipv6_in_tracked_files
      8 PASSED tests/test_private_ip_guard_ipv6.py::test_out_of_scope_not_flagged
EXIT=1
=== STAGE 1 — + ULA fc00::/7
      1 4 failed, 15 passed, 1 warning, 4 errors in 0.50s
      1 ERROR tests/test_private_ip_guard_ipv6.py::test_pre_commit_hook_allows_clean_commit
      3 ERROR tests/test_private_ip_guard_ipv6.py::test_pre_commit_hook_blocks_private_address
      4 FAILED tests/test_private_ip_guard_ipv6.py::test_link_local_detected
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_ipv4_pattern_in_sync_with_ci_guard
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_no_private_ipv6_in_tracked_files
      8 PASSED tests/test_private_ip_guard_ipv6.py::test_out_of_scope_not_flagged
      5 PASSED tests/test_private_ip_guard_ipv6.py::test_ula_detected
EXIT=1
=== STAGE 2 — + link-local fe80::/10
      1 19 passed, 1 warning, 4 errors in 0.68s
      1 ERROR tests/test_private_ip_guard_ipv6.py::test_pre_commit_hook_allows_clean_commit
      3 ERROR tests/test_private_ip_guard_ipv6.py::test_pre_commit_hook_blocks_private_address
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_ipv4_pattern_in_sync_with_ci_guard
      4 PASSED tests/test_private_ip_guard_ipv6.py::test_link_local_detected
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_no_private_ipv6_in_tracked_files
      8 PASSED tests/test_private_ip_guard_ipv6.py::test_out_of_scope_not_flagged
      5 PASSED tests/test_private_ip_guard_ipv6.py::test_ula_detected
EXIT=1
=== STAGE 3 — + hook pre-commit
      1 23 passed, 1 warning in 2.03s
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_ipv4_pattern_in_sync_with_ci_guard
      4 PASSED tests/test_private_ip_guard_ipv6.py::test_link_local_detected
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_no_private_ipv6_in_tracked_files
      8 PASSED tests/test_private_ip_guard_ipv6.py::test_out_of_scope_not_flagged
      1 PASSED tests/test_private_ip_guard_ipv6.py::test_pre_commit_hook_allows_clean_commit
      3 PASSED tests/test_private_ip_guard_ipv6.py::test_pre_commit_hook_blocks_private_address
      5 PASSED tests/test_private_ip_guard_ipv6.py::test_ula_detected
EXIT=0
=== E2E-1: الحارس الحالي (HEAD 68f01b0) مع ملف متتبع يحوي ULA وlink-local
1 passed, 1 warning in 0.17s
EXIT=0  ← RED على مستوى النظام: الثغرة قائمة
=== E2E-2: بعد الرقعة — الملف نفسه
E         probe.txt:1: [ula] <masked>
E         probe.txt:2: [link_local] <masked>
E       assert not ['probe.txt:1: [ula] <masked>', 'probe.txt:2: [link_local] <masked>']
1 failed, 1 warning in 0.67s
EXIT=1
=== E2E-3: hook حقيقي على المستودع (core.hooksPath=.githooks)
❌ حارس العناوين الخاصة: عناوين شبكة داخلية — الالتزام مرفوض:
probe.txt:1: [ula] <masked>
probe.txt:2: [link_local] <masked>
COMMIT_EXIT=1
91f8756 TEMP B (local only)
```

> ملاحظة على السجل أعلاه: `TEMP B` التزام محلي مؤقت في نسخة العمل (يمثّل شجرة GS-2) لإنتاج الرقعة — لم يُدفع، وليس في التاريخ.

---

## درس مستقل: «الحارس أمسك نفسه أثناء كتابته — فجوة R-705 تتكرر، كشفها الـhook لا اختبار الملفات المتتبعة»

**ما حدث (وقائع مسجّلة أثناء البناء):**

1. النسخة الأولى من `tools/private_ip_guard.py` عرّفت قواعد النطاقات الثلاث (ULA وlink-local) **حرفيًا** في السطر 52: ثلاث سلاسل كلٌّ منها قاعدة نطاق متبوعة بـ `::` (مقنّعة هنا: `<ula-base-1>::`، `<ula-base-2>::`، `<link-local-base>::`).
2. اختبار الملفات المتتبعة `test_no_private_ipv6_in_tracked_files` **نجح** — لأن الملف الجديد لم يكن متتبعًا بعد، و`git ls-files` لا يرى غير المتتبعين. هذه بالضبط فجوة R-705 (`5626117`): الفحص الذاتي «نجح» لأنه لم يجرِ على الملف أصلًا.
3. اختبار الـhook `test_pre_commit_hook_allows_clean_commit` **فشل** (`assert 1 == 0`): الـhook يفحص **الفهرس** (`git diff --cached`)، والملف مُضاف فيه، فرفض الالتزام النظيف برسالة:
   `tools/private_ip_guard.py:52: [ula] <masked>` ×2 و`[link_local] <masked>` ×1.
4. لو اكتفينا باختبار الملفات المتتبعة لالتُزم الملف، ثم فشل CI على الالتزام نفسه — تكرار حرفي لسلسلة R-705..R-709.

**الإصلاح:** القواعد تُبنى وقت التشغيل (`{first + "::" for first in (...)}`) مع تعليق يحيل إلى هذا الدرس — لا سلسلة حرفية تطابق نمط الحارس في ملفه.

**الدرس:**

- اختبار «الملفات المتتبعة» يصدق على الماضي فقط؛ لا يرى الملف الذي يُكتب الآن. أي حارس محتوى يجب أن يُفحص على **الفهرس** قبل الالتزام، لا على `git ls-files` وحده.
- لذلك الـhook ليس رفاهية: هو الطبقة الوحيدة التي ترى «ما سيُلتزم فعلًا». واختباره (`test_pre_commit_hook_*`) جزء من الحزمة الدائمة، فيبقى هذا الكشف قائمًا على كل حارس مستقبلي يُضاف إلى `tools/`.
- CI تبقى البوابة الصلبة (الـhook يُتجاوز بـ `--no-verify`)، لكن الـhook يحوّل الفشل من «فشل CI بعد الدفع» إلى «رفض محلي قبل الالتزام».
