# القسم ٢ — المواد الخام للالتزامين المحوريين (على d56e24e)

الالتزامان: `182949f` (المخالفة التاريخية الأصلية) و`d56e24e` (رأس main الحالي).

## 7) git show --stat كاملًا لكل التزامين

```
commit 182949f912d116cdde618697312ba5a2e394b5a7
Author: reeveero-tech <282669851+reeveero-tech@users.noreply.github.com>
Date: Thu Oct 15 17:41:33 2026 +0000

 .github/workflows/ci.yml             | 23 +++++++++++++++++------
 forensics/OPERATIONAL_TESTS.md       | 36 ++++++++++++++++++++++++++++++++++++
 tests/test_gate1_operational_auth.py |  9 +++++++--
 3 files changed, 60 insertions(+), 8 deletions(-)

---

commit d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
Author: reeveero-tech <282669851+reeveero-tech@users.noreply.github.com>
Date: Thu Oct 15 23:26:01 2026 +0000

 forensics/CONTRACT_EXCEPTION_1.md |  5 +++++
 forensics/DELETED_LINES_AUDIT.md  | 27 ++++++++++++++++++++++++---
 forensics/FINAL_CLOSURE_R-682.md  |  8 +++++---
 forensics/OPERATIONAL_TESTS.md    | 21 +++++++++++++++------
 4 files changed, 49 insertions(+), 12 deletions(-)
```

## 8) رسالة الالتزام حرفيًا (git log -1 --format=%B)

### 182949f

```
R-682 (operational): provision old rotated key via KEY_OLD_SECRET + safe secret passing + no key leakage in subprocess

Design gap found before triggering (advisor controls applied): the
operational test requires BOTH data/key.secret (from KEY_SECRET) AND
data/key.secret.old_rotated_2026_10_14 (the real rotated key — forensic
artifact of the 2026-10-14 rotation), but the CI operational job never
provisioned the second file — any run would have failed at
'assert old_key_path.exists()' (a spurious failure measuring nothing
about auth behavior). A synthetic old key would weaken the test to
'any wrong key is rejected'; the forensic value requires the REAL old
key (proving the rotation left it invalid).

Fixes (all per advisor):
1. ci.yml operational job: both secrets passed via env (no direct
   interpolation inside run), files written with umask 077 +
   printf '%s' "", explicit failure message if either secret is
   missing, values never printed, key files never in any artifact.
2. Test: keys passed to the subprocess via environment variables
   (TEST_NEW_KEY/TEST_OLD_KEY) — never embedded in the script source,
   so they cannot appear in any traceback, failure message, or pytest
   output.
3. Docs (OPERATIONAL_TESTS.md): the two required secrets documented
   (KEY_SECRET = current key; KEY_OLD_SECRET = content of the host's
   key.secret.old_rotated_2026_10_14), the design gap + fixes
   documented, and the claim scope corrected: the regular test job
   does NOT use the repo secret (it auto-generates an ephemeral key),
   and operational success proves auth in the CI environment loaded
   with the two real keys — not the production server state.

Regular suite unchanged: 407 passed, 1 deselected, 0 failed, 0
skipped (the operational test remains deselected; this commit does
not touch collected tests).

Closure condition (per advisor): the job itself must run with
run_operational=true on a pinned SHA — operational job green + JUnit
proving the single test executed (200/403) with no failure/skip.

```

### d56e24e

```
R-682: التزام تصحيحي ثانٍ — معالجة عوائق المستشار الثلاثة الأخيرة

1. CONTRACT_EXCEPTION_1.md حُدّث فعليًا هذه المرة: البند ٥ لنص التوقيع الجاهز يدرج مخالفات d05a248 (4 أسطر بلا تدقيق) و7164044 (تدقيق ناقص: 6 من 7) وf2577ca (عدد خاطئ 10 بدل 9).
2. مدخل 7164044 في التدقيق استُكمل بالسطر السابع (سطر إفصاح المستشار البدائي بشرطة — سقط من نمط الاستخراج الأولي) مع تسجيل النقص كمخالفة توثيقية موثقة في نص الاستثناء. وصُوبت صياغة مدخل f2577ca (دُقق في التزامه لكن بعدد خاطئ؛ 20a81ce يسبقه زمنيًا — لا غياب تدقيق).
3. قياس أخطاء التسجيل أعيد بالطريقة الصحيحة: قبض كامل لstdout وstderr (الملف فارغ بالكامل — 0 بايت) + ملف --log-file + رمز خروج = EXIT=0، 424 passed، صفر R-626، صفر --- Logging error --- في المسارين معًا — مفصول صراحة عن القياس القديم (415).

حذوفات هذا الالتزام (12 سطرًا — استبدالات تصويبية موثقة سطرًا سطرًا) مدققة في نفسه.

```

## 9) الفرق الكامل

### git show 182949f (كامل)

```
commit 182949f912d116cdde618697312ba5a2e394b5a7
Author: reeveero-tech <282669851+reeveero-tech@users.noreply.github.com>
Date:   Thu Oct 15 17:41:33 2026 +0000

    R-682 (operational): provision old rotated key via KEY_OLD_SECRET + safe secret passing + no key leakage in subprocess
    
    Design gap found before triggering (advisor controls applied): the
    operational test requires BOTH data/key.secret (from KEY_SECRET) AND
    data/key.secret.old_rotated_2026_10_14 (the real rotated key — forensic
    artifact of the 2026-10-14 rotation), but the CI operational job never
    provisioned the second file — any run would have failed at
    'assert old_key_path.exists()' (a spurious failure measuring nothing
    about auth behavior). A synthetic old key would weaken the test to
    'any wrong key is rejected'; the forensic value requires the REAL old
    key (proving the rotation left it invalid).
    
    Fixes (all per advisor):
    1. ci.yml operational job: both secrets passed via env (no direct
       interpolation inside run), files written with umask 077 +
       printf '%s' "", explicit failure message if either secret is
       missing, values never printed, key files never in any artifact.
    2. Test: keys passed to the subprocess via environment variables
       (TEST_NEW_KEY/TEST_OLD_KEY) — never embedded in the script source,
       so they cannot appear in any traceback, failure message, or pytest
       output.
    3. Docs (OPERATIONAL_TESTS.md): the two required secrets documented
       (KEY_SECRET = current key; KEY_OLD_SECRET = content of the host's
       key.secret.old_rotated_2026_10_14), the design gap + fixes
       documented, and the claim scope corrected: the regular test job
       does NOT use the repo secret (it auto-generates an ephemeral key),
       and operational success proves auth in the CI environment loaded
       with the two real keys — not the production server state.
    
    Regular suite unchanged: 407 passed, 1 deselected, 0 failed, 0
    skipped (the operational test remains deselected; this commit does
    not touch collected tests).
    
    Closure condition (per advisor): the job itself must run with
    run_operational=true on a pinned SHA — operational job green + JUnit
    proving the single test executed (200/403) with no failure/skip.

diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index 17d985a..23ef005 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -179,16 +179,27 @@ jobs:
           pip install --upgrade pip
           pip install -r requirements.txt
 
-      - name: Load KEY_SECRET from repository secret
+      # R-682 (جولة التشغيلية — أمر المستشار): السران يُمرَّران عبر env (لا
+      # استيفاء مباشر داخل run)، والملفات بـ umask 077 + printf، وقيمهما لا
+      # تُطبع أبدًا ولا تدخل أي artifact.
+      - name: Load keys from repository secrets (KEY_SECRET + KEY_OLD_SECRET)
+        env:
+          KEY_SECRET: ${{ secrets.KEY_SECRET }}
+          KEY_OLD_SECRET: ${{ secrets.KEY_OLD_SECRET }}
         run: |
-          if [ -z "${{ secrets.KEY_SECRET }}" ]; then
-            echo "❌ KEY_SECRET secret not configured — cannot run operational tests"
+          set -euo pipefail
+          if [ -z "${KEY_SECRET}" ] || [ -z "${KEY_OLD_SECRET}" ]; then
+            echo "❌ KEY_SECRET and KEY_OLD_SECRET secrets must both be configured"
+            echo "   KEY_SECRET     = current master key (data/key.secret)"
+            echo "   KEY_OLD_SECRET = old rotated key (data/key.secret.old_rotated_2026_10_14)"
+            echo "   — cannot run operational tests"
             exit 1
           fi
+          umask 077
           mkdir -p data
-          printf '%s' "${{ secrets.KEY_SECRET }}" > data/key.secret
-          chmod 600 data/key.secret
-          echo "key.secret loaded from secret"
+          printf '%s' "$KEY_SECRET" > data/key.secret
+          printf '%s' "$KEY_OLD_SECRET" > data/key.secret.old_rotated_2026_10_14
+          echo "key.secret + old_rotated loaded from secrets (values never printed)"
 
       - name: Run operational tests
         run: |
diff --git a/forensics/OPERATIONAL_TESTS.md b/forensics/OPERATIONAL_TESTS.md
index 367f239..d7c84c6 100644
--- a/forensics/OPERATIONAL_TESTS.md
+++ b/forensics/OPERATIONAL_TESTS.md
@@ -63,3 +63,39 @@ python -m pytest tests/ backend/tests/ -v -m "not operational" ...
 **خطوة `sha` (تصحيح R-682 final):** كان الـ workflow يشير إلى `steps.sha.outputs.short` في job `operational` بدون وجود step `sha` — أُضيف step `sha` لتفادي فشل تسمية artifact.
 
 **الحالة:** مُنفَّذ (isolation) — الاختبار لم يُحذف، فقط عُزل.
+
+---
+
+## الجولة التشغيلية (2026-10-15) — إعداد التشغيل الفعلي بعد إضافة المالك `KEY_SECRET`
+
+**فجوة التصميم المكتشفة قبل التشغيل:** الاختبار التشغيلي يتطلب ملفين —
+`data/key.secret` (المفتاح الحالي، متاح من `KEY_SECRET`) **و**
+`data/key.secret.old_rotated_2026_10_14` (المفتاح القديم — أثر التدوير
+الجنائي) — والوظيفة في `ci.yml` لم تكن توفر الثاني إطلاقًا، فأي تشغيل كان
+سيفشل حتمًا عند `assert old_key_path.exists()` (فشل زائف لا يقيس سلوك
+المصادقة). القيمة الجنائية للاختبار تتطلب المفتاح القديم **الحقيقي** — لا
+بديل اصطناعي (مفتاح اصطناعي يُضعفه إلى «أي مفتاح خاطئ يُرفض»).
+
+**الإصلاحات (أوامر المستشار):**
+1. **`ci.yml`:** خطوة التحميل صارت تمرّر السرين عبر `env` (لا استيفاء مباشر
+   داخل `run`)، وتكتب الملفين بـ `umask 077` + `printf '%s' "$VAR"`، وتفشل
+   برسالة صريحة إذا غاب أحدهما، ولا تطبع القيم ولا تدخل الملفان أي artifact.
+2. **الاختبار:** المفتاحان يُمرَّران إلى السب-بروسس عبر متغيرات بيئة
+   (`TEST_NEW_KEY`/`TEST_OLD_KEY`) — لا يُضمَّنان في مصدر السكربت، فلا يظهران
+   في أي traceback أو رسالة إخفاق أو مخرجات pytest.
+
+**السران المطلوبان (قرار المالك):**
+| السر | المحتوى | الملف الذي يُنشأه |
+|---|---|---|
+| `KEY_SECRET` | المفتاح الرئيسي الحالي | `data/key.secret` |
+| `KEY_OLD_SECRET` | محتوى ملف `data/key.secret.old_rotated_2026_10_14` من مضيف المالك | الملف نفسه |
+
+**نطاق الادعاء (تصويب أمر المستشار):** الوظيفة الاعتيادية (`test`) **لا
+تستخدم** سر المستودع — تُولّد مفتاحًا مؤقتًا ذاتيًا. ونجاح الوظيفة
+التشغيلية يثبت المصادقة **داخل بيئة CI المحمّلة بالمفتاحين الحقيقيين** —
+لا حالة خادم الإنتاج.
+
+**الإغلاق يتطلب (أمر المستشار):** تشغيل الوظيفة نفسها بـ
+`run_operational=true` على SHA محدد + نجاح job الـoperational + JUnit يثبت
+تنفيذ الاختبار الواحد بنجاح (200/403) دون فشل أو تخطٍّ — لا يُغلق البند
+قبل ظهور هذه الأدلة.
diff --git a/tests/test_gate1_operational_auth.py b/tests/test_gate1_operational_auth.py
index 6671c15..a989dee 100644
--- a/tests/test_gate1_operational_auth.py
+++ b/tests/test_gate1_operational_auth.py
@@ -62,6 +62,9 @@ class TestOperationalAuth:
 
         # سكربت التحقق التشغيلي (subprocess — عملية جديدة)
         # يُحمّل التطبيق بالإعدادات الحقيقية (دون monkeypatch/reload)
+        # R-682 (جولة التشغيلية — أمر المستشار): المفتاحان يُمرَّران عبر
+        # متغيرات بيئة السب-بروسس — لا يُضمَّنان في مصدر السكربت نفسه، فلا
+        # يظهران في أي traceback أو رسالة إخفاق أو مخرجات pytest.
         script = (
             "import sys, os, json\n"
             f"sys.path.insert(0, {str(_REPO_ROOT / 'backend')!r})\n"
@@ -74,23 +77,25 @@ class TestOperationalAuth:
             "client = TestClient(app.app)\n"
             "results = {}\n"
             "try:\n"
-            f"    r = client.get('/api-key', params={{'master_key': {new_key!r}}})\n"
+            "    r = client.get('/api-key', params={'master_key': os.environ['TEST_NEW_KEY']})\n"
             "    results['new_key_status'] = r.status_code\n"
             "except Exception as e:\n"
             "    results['new_key_error'] = str(e)\n"
             "try:\n"
-            f"    r = client.get('/api-key', params={{'master_key': {old_key!r}}})\n"
+            "    r = client.get('/api-key', params={'master_key': os.environ['TEST_OLD_KEY']})\n"
             "    results['old_key_status'] = r.status_code\n"
             "except Exception as e:\n"
             "    results['old_key_error'] = str(e)\n"
             "print(json.dumps(results))\n"
         )
 
+        subprocess_env = {**os.environ, "TEST_NEW_KEY": new_key, "TEST_OLD_KEY": old_key}
         result = subprocess.run(
             [sys.executable, "-c", script],
             capture_output=True,
             text=True,
             cwd=str(_REPO_ROOT),
+            env=subprocess_env,
             timeout=120,
         )
 
```

### git show d56e24e (كامل)

```
commit d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
Author: reeveero-tech <282669851+reeveero-tech@users.noreply.github.com>
Date:   Thu Oct 15 23:26:01 2026 +0000

    R-682: التزام تصحيحي ثانٍ — معالجة عوائق المستشار الثلاثة الأخيرة
    
    1. CONTRACT_EXCEPTION_1.md حُدّث فعليًا هذه المرة: البند ٥ لنص التوقيع الجاهز يدرج مخالفات d05a248 (4 أسطر بلا تدقيق) و7164044 (تدقيق ناقص: 6 من 7) وf2577ca (عدد خاطئ 10 بدل 9).
    2. مدخل 7164044 في التدقيق استُكمل بالسطر السابع (سطر إفصاح المستشار البدائي بشرطة — سقط من نمط الاستخراج الأولي) مع تسجيل النقص كمخالفة توثيقية موثقة في نص الاستثناء. وصُوبت صياغة مدخل f2577ca (دُقق في التزامه لكن بعدد خاطئ؛ 20a81ce يسبقه زمنيًا — لا غياب تدقيق).
    3. قياس أخطاء التسجيل أعيد بالطريقة الصحيحة: قبض كامل لstdout وstderr (الملف فارغ بالكامل — 0 بايت) + ملف --log-file + رمز خروج = EXIT=0، 424 passed، صفر R-626، صفر --- Logging error --- في المسارين معًا — مفصول صراحة عن القياس القديم (415).
    
    حذوفات هذا الالتزام (12 سطرًا — استبدالات تصويبية موثقة سطرًا سطرًا) مدققة في نفسه.

diff --git a/forensics/CONTRACT_EXCEPTION_1.md b/forensics/CONTRACT_EXCEPTION_1.md
index e722c93..159486f 100644
--- a/forensics/CONTRACT_EXCEPTION_1.md
+++ b/forensics/CONTRACT_EXCEPTION_1.md
@@ -209,6 +209,11 @@ print(f'Code deletions: {len(code_del)}')
    خطأ في رسالتي آخر التزامين («لا حذوفات») — أُدرجت بأثر رجعي في
    `DELETED_LINES_AUDIT.md`. قرارك هنا يشملها: قبول الاستثناء الموثق أو
    طلب إجراء تصحيحي إضافي.
+5. مخالفات إضافية من الجولة نفسها بعد تدقيق المستشار: (أ) الالتزام `d05a248`
+   حذف 4 أسطر (استبدالات صياغية) دون تدقيق ودون ذكر في رسالته — أُدرجت
+   بأثر رجعي؛ (ب) الالتزام التصحيحي `7164044` وثّق 6 من أسطره المحذوفة
+   السبعة (سقط سطر يبدأ بشرطة من الاستخراج) — ناقص موثق هنا؛ (ج) مدخل
+   تدقيق `f2577ca` ذكر 10 بينما الفعلي 9 (صُوب لاحقًا). قرارك يشمل الثلاث.
 
 التوقيع: ____________________    التاريخ: ____ / ____ / ________
 (أو أمر صريح جديد مني بنفس المضمون يُرفق بهذا الملف)
diff --git a/forensics/DELETED_LINES_AUDIT.md b/forensics/DELETED_LINES_AUDIT.md
index f1c752d..73a42f4 100644
--- a/forensics/DELETED_LINES_AUDIT.md
+++ b/forensics/DELETED_LINES_AUDIT.md
@@ -590,8 +590,11 @@ tests/ci_run_selection.py (--require-completed). الحذف كله استبدا
 و`if [ "$CI_CONCLUSION" != "success" ]` مع أسطر الصدى الخاص بهما (8 أسطر)
 + سطر فارغ واحد فاصل. **تصويب:** المدخل الأولي ورسالة الالتزام قالا «10» —
 الرقم الفعلي من git numstat هو **9**. رسالة الالتزام غير قابلة للتعديل؛ هذا
-التصويح هو التوثيق الصحيح. (المخالفة الأصلية — حذف دون تدقيق في نفس
-الالتزام — لا تزال مسجلة في مدخل 20a81ce أدناه.)
+التصويح هو التوثيق الصحيح. **تصويب صياغي إضافي:** العبارة السابقة هنا
+قالت إن مخالفة هذا الالتزام «مسجلة في مدخل 20a81ce» — خطأ: الالتزام
+`f2577ca` **دُققت حذوفاته في التزامه نفسه** لكن بعدد خاطئ (10 بدل 9)،
+و`20a81ce` يسبقه زمنيًا. المخالفة الصحيحة المنسوبة لـ`f2577ca`: تدقيق
+بعدد غير مطابق، لا غياب تدقيق.
 
 ## R-682 — تدقيق رجعي للالتزام d05a248 (2026-10-16): 4 أسطر — مخالفة مسجلة
 
@@ -618,4 +621,22 @@ tests/ci_run_selection.py (--require-completed). الحذف كله استبدا
 3. `## R-682 — إصلاح متغير غير معرف في verify.sh (2026-10-16): 10 أسطر` — استُبدل بـ9
 4. `الأسطر العشرة (حرفيًا)...` — استُبدلت بالأسطر التسعة مع التصويح
 5. `` `if [ "$CI_CONCLUSION" != "success" ]` مع أسطر الصدى الخاص بهما. `` — جزء من الاستبدال
-6. `الثلاثة على SHA واحد (11 اختبارًا) + مخرجات كاملة محفوظة (لا مقتطفات).` — استُبدل بـ(9 اختبارات)
+6. `الثلاثة على SHA واحد (11 اختبارًا) + مخرجات كاملة محفوظة (لا مقتطفات).`
+7. `- **نصوصها ليست مخزنة في المستودع** — تُحفظ تلقائيًا خارج المستودع في مسار جلسة العمل المحلي.` — سطر إفصاح المستشار القديم (استُبدل بصياغة مميزة للنصوص الأصلية عن النسخ المضمّنة).
+
+**تصويح لاحق (بعد تدقيق المستشار):** الاستخراج الأولي أسقط السطر السابع لأنه
+يبدأ بشرطة (نمط `^-[^-]`) — مخالفة توثيقية في هذا الالتزام التصحيحي نفسه
+(قائمة ناقصة)، مسجلة هنا بأثر رجعي ومدرجة في نص استثناء المالك (البند ٥). — استُبدل بـ(9 اختبارات)
+
+## R-682 — الالتزام التصحيحي الثاني (2026-10-16): 12 سطرًا — مدققة في نفس الالتزام
+
+استخراج الحذوفات من مقاطع التغيير في الـstaged diff (بما فيها الأسطر
+البدائية بشرطة — لا نمط `-[^-]`) — كلها استبدالات تصويبية، لا حذف معلومات:
+
+- مدخل f2577ca: سطرا الصياغة الخاطئة («مسجلة في مدخل 20a81ce») — استُبدلا
+  بالتصويح (f2577ca دُقق في التزامه لكن بعدد خاطئ؛ 20a81ce يسبقه).
+- مدخل 7164044: سطر البند السادس — استُبدل بصيغة تشير للتسعة.
+- FINAL_CLOSURE: 3 أسطر فقرة القياس القديمة — استُبدلت بالقياس كامل القبض
+  (stdout + stderr + exit).
+- OPERATIONAL_TESTS: 6 أسطر قسم القياس القديم — استُبدل بالقياس المكتمل
+  وملاحظته المنهجية (stderr لا ملف السجل هو مسار أخطاء المعالج).
diff --git a/forensics/FINAL_CLOSURE_R-682.md b/forensics/FINAL_CLOSURE_R-682.md
index 5884039..6d4ca3b 100644
--- a/forensics/FINAL_CLOSURE_R-682.md
+++ b/forensics/FINAL_CLOSURE_R-682.md
@@ -86,9 +86,11 @@ DELETED_LINES_AUDIT.md وضمن نص استثناء المالك.
    + حراسة جلسة + كل تشغيلات الجولة.
 
    **قياس موحد على الشجرة النهائية نفسها (424 اختبارًا):** جلسة محلية كاملة
-   بـ--log-file على الشجرة النهائية (نفس شجرة الـ424 المُتحقق عليها في CI)
-   = 424 passed / صفر R-626 في السجل / صفر Logging error — قياس واحد على
-   نفس الشجرة، لا دمج قياسين مختلفين (القياس السابق على 415 كان على شجرة
+   على الشجرة النهائية (نفس شجرة الـ424 المُتحقق عليها في CI) بقبض كامل:
+   stdout + stderr + --log-file + رمز الخروج = 424 passed / EXIT=0 /
+   stderr فارغ بالكامل (0 بايت) / صفر R-626 في ملف السجل / صفر
+   `--- Logging error ---` في stdout وstderr معًا — قياس واحد على نفس
+   الشجرة، لا دمج قياسين مختلفين (القياس السابق على 415 كان على شجرة
    أبكر — موثق في keyring_rejection_count.json).
 
 ## ملفات الجولة
diff --git a/forensics/OPERATIONAL_TESTS.md b/forensics/OPERATIONAL_TESTS.md
index b4a9c9c..db973ae 100644
--- a/forensics/OPERATIONAL_TESTS.md
+++ b/forensics/OPERATIONAL_TESTS.md
@@ -525,17 +525,26 @@ verify-full داخل Actions».
 tests/ci_run_selection.py (--require-completed) تقوم بالتحقق نفسه. إعادة
 الإطلاق على الالتزام الجديد هي الإثبات.
 
-## R-682 (ختام): قياس موحد على الشجرة النهائية (424 اختبارًا)
+## R-682 (ختام): قياس موحد على الشجرة النهائية (424 اختبارًا) — قبض كامل
 
-فصلًا لأي دمج بين قياسين، أُعيد القياس المحلي بـ--log-file على الشجرة
-النهائية نفسها (نفس شجرة الـ424 المُتحقق عليها حرفيًا في CI):
+فصلًا لأي دمج بين قياسين، أُعيد القياس المحلي على الشجرة النهائية نفسها
+(نفس شجرة الـ424 المُتحقق عليها حرفيًا في CI) **بقبض كامل لكل المسارات**:
+stdout وstderr كاملين بلا اقتصاص + ملف --log-file + رمز الخروج:
 
 ```
-424 passed, 1 deselected in 181.82s
-R-626 count: 0
-Logging error count: 0
+EXIT=0
+stdout (كامل): 424 passed, 1 deselected in 183.33s
+stderr (كامل): فارغ — 0 بايت
+R-626 في ملف السجل: 0
+--- Logging error --- في stderr: 0
+--- Logging error --- في stdout: 0
 ```
 
+ملاحظة منهجية (تصويب بعد تدقيق المستشار): أخطاء معالج التسجيل
+(`--- Logging error ---`) تُكتب إلى stderr لا إلى ملف --log-file — فالبحث
+في الملف وحده لا يثبت الصفر؛ القياس أعلاه يفحص المسارين معًا وملف
+stderr فارغ بالكامل (0 بايت).
+
 القياس السابق (415 اختبارًا) كان على شجرة أبكر قبل إضافة اختبارات اختيار
 CI — يبقى سجلًا تاريخيًا محددًا في keyring_rejection_count.json ولا يُنسب
 إلى تشغيل الـ424.
```

## 10) هل d56e24e هو رأس main الآن؟

```
d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad
```

## 11) git status على الحالة الحالية

```
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	VERIFICATION_PACK/

nothing added to commit but untracked files present (use "git add" to track)
```
