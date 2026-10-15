# forensics/PY311_VERIFICATION.md — التحقق الكامل على Python 3.11 (البند ١١)

**التاريخ:** 2026-10-16 — جولة R-682 الشاملة (نسخة نهائية بعد اعتراض المستشار)
**الطريق المستخدم:** GitHub Actions (لا Docker في بيئة الوكيل) — كما أقرّ المستشار.

## الأرقام النهائية

الأرقام في هذه الجولة **424/0/0/0** (410 عند بدء الجولة + 14 اختبارًا أضافتها:
اختبارا الخيوط السلوكيان + مسار فشل الموقفات + اختبارا حراسة نظافة السجل +
9 اختبارات اختيار تشغيل CI الحتمية). تطور العدد الموثق خلال الجولة:
410 ← 412 ← 415 ← 424 — كل زيادة معلنة، لا نقص اختبارات في أي خطوة.

| القياس | القيمة | المصدر |
|---|---|---|
| Python | **3.11.17** | `python -VV` من تشغيل push 38817554052 |
| الحزم | requirements.txt حرفيًا (pip freeze أدناه) | نفس التشغيل |
| الحزمة (الأمر الحرفي داخل Actions) | **424 passed, 0 skipped, 0 failed** | تشغيل verify-full 38818090658 |
| الحزمة (CI push) | **424 passed, 0 skipped, 0 failed** | تشغيل push 38817554052 |
| الحزمة (clone نظيف داخل الأمر الحرفي) | **424 passed, 0 skipped, 0 failed** | تشغيل verify-full 38818090658 |
| التطابق الثلاثي | ✅ محلي = CI = clone (SHA + العد + هوية كل اختبار) | المخراج الكامل أدناه |
| التشغيلي (operational) | ✅ ناجح | تشغيل 38818088145 |
| بوابة الإصدار (البند ١٢) | ✅ Python 3.11 مقبول داخل verify.sh | نفس التشغيل |
| صفر R-626 في السجل الكامل | ✅ (محليًا) | قياس 2026-10-16 — keyring_rejection_count.json |

## تشغيلات GitHub Actions المعتمدة (على الالتزام f2577ca البرمجي وعلى الالتزام الختامي 10c2bf5)

**الالتزام الختامي `10c2bf5` (توثيقي خالص — لا كود):**

| التشغيل | المعرّف | الحدث | النتيجة |
|---|---|---|---|
| push CI | 38819079098 | push | success — 424/0/0 |
| operational | 38819575692 | workflow_dispatch (run_operational=true) | success |
| verify-full (الأمر الحرفي، ci_run_id=38819079098) | 38819578463 | workflow_dispatch (run_verify_full=true) | success — TARGET_SHA=10c2bf5c4921721529d9a3878cd03ddf3720e0fe، تطابق ثلاثي 424/0/0/0، صفر skips مؤكد |

**الالتزام البرمجي `f2577ca`:**

| التشغيل | المعرّف | الحدث | النتيجة |
|---|---|---|---|
| push CI (المرجعي) | 38817554052 | push | success |
| operational | 38818088145 | workflow_dispatch (run_operational=true) | success |
| verify-full (الأمر الحرفي) | 38818090658 | workflow_dispatch (run_verify_full=true, ci_run_id=38817554052) | success |

مسار التجارب السابقة الموثق: أول تشغيل verify-full (38812431011 على a733ab8)
كشف خطأ الانتقاء الذاتي؛ الثاني (38813598872 على 60053d4) نجح؛ الثالث
(38817055678 على 20a81ce) كشف متغيرًا غير معرف؛ الرابع أعلاه هو النهائي.
كلها موثقة في OPERATIONAL_TESTS.md.

## إفصاح البيئة الخام (من تشغيل push 38813044942 — بلا اقتصاص)

```
=== python -VV ==="^[[0m
^[[36;1mpython -VV^[[0m
^[[36;1mecho "=== pip freeze (installed) ==="^[[0m
^[[36;1mpip freeze^[[0m
^[[36;1mecho "=== pip check ==="^[[0m
^[[36;1mpip check^[[0m
^[[36;1mecho "=== END environment disclosure ==="^[[0m
shell: /usr/bin/bash -e {0}
env:
  pythonLocation: /opt/hostedtoolcache/Python/3.11.17/x64
  PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.11.17/x64/lib/pkgconfig
  Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.17/x64
  Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.17/x64
  Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.11.17/x64
  LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.11.17/x64/lib
=== python -VV ===
Python 3.11.17 (main, Oct  1 2026, 14:32:31) [GCC 13.3.0]
=== pip freeze (installed) ===
annotated-types==0.8.0
anyio==4.15.1
certifi==2026.7.22
click==8.5.0
cloudpickle==3.1.2
fastapi==0.115.0
h11==0.16.0
httpcore==1.0.9
httptools==0.9.0
httpx==0.27.0
idna==3.20
iniconfig==2.3.1
joblib==1.6.0
numpy==1.26.4
packaging==26.3
pluggy==1.7.0
pycryptodome==3.24.1
pydantic==2.9.0
pydantic_core==2.23.2
Pygments==2.21.0
pytest==9.1.1
python-dotenv==1.2.4
python-multipart==0.0.12
PyYAML==6.0.3
scikit-learn==1.3.0
scipy==1.13.0
sniffio==1.3.1
starlette==0.38.6
threadpoolctl==3.7.0
typing_extensions==4.16.0
tzdata==2026.5
uvicorn==0.30.0
uvloop==0.23.0
watchfiles==1.3.0
websockets==13.0
=== pip check ===
No broken requirements found.
=== END environment disclosure ===```

## المخرج الكامل للأمر الحرفي (verify.sh --full داخل تشغيل 38818090658 — حرفي بلا اقتصاص)

الأمر المنفذ حرفيًا داخل المهمة:
`cd /tmp && rm -rf verify_exec && git clone -q https://github.com/reeveero-tech/sovereign_ai.git verify_exec && cd verify_exec && git checkout -q f2577ca412c6c19cf82002710e49c9c1fc519f44 && timeout 1500 bash verify.sh --full`

```
==========================================
 R-682 Verification Script
==========================================
HEAD: f2577ca412c6c19cf82002710e49c9c1fc519f44
[info] Generated ephemeral data/key.secret (not committed)

[1/2] Running test suite (tests/ + backend/tests/, excluding operational)...
........................................................................ [ 16%]
........................................................................ [ 33%]
........................................................................ [ 50%]
........................................................................ [ 67%]
........................................................................ [ 84%]
................................................................         [100%]
=============================== warnings summary ===============================
../../opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/starlette/testclient.py:40
  /opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
424 passed, 1 deselected, 1 warning in 227.53s (0:03:47)
✅ git SHA embedded in JUnit XML: f2577ca412c6c19cf82002710e49c9c1fc519f44

[2/2] Verifying zero skips (DoD hard requirement)...
✅ بوابة الاختبارات ناجحة: 424 passed, 0 skipped, 0 failed

==========================================
 [FULL MODE] CI + Clean Clone comparison
==========================================

[3/4] Fetching CI run for HEAD SHA=f2577ca...
CI Run: 38817554052 (completed/success — اختيار صريح + فحص هوية workflow)
CI:     sha=f2577ca412c6... tests=424 failed=0 skipped=0 unique_ids=424
Local:  sha=f2577ca412c6... tests=424 failed=0 skipped=0 unique_ids=424
✅ CI + Local MATCH (SHA + test counts + (normalized_classname,name) Counter + zero failures + zero skips)

[4/4] Clean clone verification (git checkout pinned to SHA=f2577ca)...
[info] Generated ephemeral data/key.secret in clone (not committed)
  /opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/starlette/testclient.py:40: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = typing.Callable[[], typing.ContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
424 passed, 1 deselected, 1 warning in 218.49s (0:03:38)
✅ SHA embedded in clone JUnit: f2577ca412c6c19cf82002710e49c9c1fc519f44
Clone:  tests=424 failed=0 skipped=0 unique_ids=424
Local:  tests=424 failed=0 skipped=0 unique_ids=424
✅ Clean clone JUnit MATCHES Local (count + (normalized_classname,name) Counter + zero failures + zero skips)

==========================================
 VERIFICATION COMPLETE
 HEAD: f2577ca412c6c19cf82002710e49c9c1fc519f44
 JUnit: forensics/pytest_results.xml (git_sha embedded)
 Mode: --full
==========================================```

## حدود الإفصاح

- الأرقام أعلاه من Actions على ubuntu-24.04 مع Python 3.11.17 — البيئة
  المعلنة للمشروع.
- الوكيل محليًا لا يستطيع تشغيل verify.sh بعد بوابة الإصدار (Python 3.14.3
  محليًا — البوابة ترفضه عمدًا؛ راجع LOCAL_ENV_DISCLOSURE.md).
- القياس المحلي (صفر R-626) من جلسة الوكيل المحلية على نفس شجرة الكود؛
  أمر verify.sh لا يمرر --log-file فقياس الرفض موثق محليًا ومفصول المصدر
  (راجع keyring_rejection_count.md وOPERATIONAL_TESTS.md).
