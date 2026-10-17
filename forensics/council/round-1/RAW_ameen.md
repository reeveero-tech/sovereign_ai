# RAW — المراجع «أمين» — الجولة 1: الأمان (التشفير، KeyRing، ransomware.py)

- الشجرة: `/home/user/workspace/council/ameen` — `git log -1` = `4bc5500`، و`git status --short` فارغ قبل الفحص وبعده (لم يُعدَّل أي ملف كود، ولا commit ولا push).
- المفسّر: `/home/user/workspace/.venv-sov/bin/python` (pycryptodome 3.24.1 مثبت).
- كل التجارب كُتبت في `/tmp` (خارج الشجرة) وبجذور بيانات مؤقتة (`SOVEREIGN_DATA_ROOT=/tmp/...`) أو بعد إعادة توجيه ثوابت المسارات إلى `/tmp`، حتى لا تُلمس ملفات الشجرة المتتبعة. نصوص التجارب كاملة في الملحق (ب).
- مقياس الشدة: حرجة / متوسطة / منخفضة. الأنواع: خلل أمني / فجوة اختبار / عدم تطابق توثيق.

---

## 0) الاختبارات القائمة — نتيجة التشغيل

| الأمر | النتيجة |
|---|---|
| `python -m pytest tests/test_return_none_lowrisk.py tests/test_return_none_security.py tests/test_sovereign_keys.py tests/test_key_selection_rotation.py tests/test_fail_closed_rotation.py tests/test_writer_keyring_binding.py backend/tests/invariants/test_keyring_immutability.py backend/tests/invariants/test_key_state_vulnerability.py backend/tests/invariants/test_key_state_transitions.py -q -p no:cacheprovider` | `178 passed in 2.20s` |
| `python -m pytest tests/test_config_security.py tests/test_ledger_verify_endpoint.py tests/test_session_ledger_key_hygiene.py backend/tests/invariants/test_no_unsigned_ledger_events.py backend/tests/invariants/test_anchor_rejects_arbitrary_signature.py -q -p no:cacheprovider` | `29 passed, 1 warning` |

كل الاختبارات تنجح. لكن العيوب الموثقة أدناه كلها تمر رغم ذلك، أي أن الاختبارات لا تغطيها (انظر القسم 8).

---

## 1) مسارات HTTP غير محمية تمس الأمان والسلامة

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 1.1 `POST /api/reset` بلا أي مصادقة، وينفّذ `orch.reset_all()` الذي يستدعي `memory_core.reset()` بالقيمة الافتراضية `preserve_events=False` | `backend/api.py:255-279` (لا فحص مفتاح)، `backend/orchestrator.py:1322,1360-1361`، `backend/memory/core.py:515-533`. تشغيل: TestClient مع orchestrator وهمي → `/api/reset no key -> 200 تم إعادة تهيئة النظام بالكامل` و`calls: [('reset_all', False), ...]`. أما `/sovereign/reset` بمفتاح خاطئ فيعيد `401` | خلل أمني | حرجة | إضافة نفس فحص المفتاح المستخدم في `/sovereign/reset` (في الرأس) إلى كل مسارات `/api/*` التي تغيّر الحالة، أو إزالة المسار المكرر |
| 1.2 إعادة التهيئة تتلف السجل السيادي نهائيًا: النسخة الاحتياطية واحدة `.jsonl.bak` ويُكتب فوقها في كل reset، فاستدعاءان متتاليان لـ 1.1 يمحوان الأصل | `backend/memory/core.py:528-532` (`shutil.copy2(self.log_file, backup_file)` ثم `unlink`). تشغيل على `SovereignCore` معزول: `ledger lines before reset: 5 \| .bak after 1st reset: 5 \| .bak after 2nd reset: 2` | خلل أمني | حرجة | نسخ احتياطي باسم فريد بطابع زمني لا يُكتب فوقه، ورفض reset الكامل دون تفويض صريح |
| 1.3 `POST /api/run` و`POST /api/event` و`POST /api/mode/{mode}` بلا مصادقة وبلا SafetyGuard، وهي تتجاوز `POST /orchestrator/cycle` المحمي (تشغّل `orch.run_cycle` نفسه) | `backend/api.py:209-231` و`354-378` و`445-466`. تشغيل: `/api/mode/emergency no key -> 200 success` | خلل أمني | حرجة | توحيد المصادقة لكل مسارات `/api/*` التي تكتب، وتمرير المدخلات عبر `SafetyGuard` |
| 1.4 `GET /security/log` بلا مصادقة ويعيد أوامر السيد نفسها (`sovereign_command` بحقل `command`) ورسائل المستخدمين | `backend/app.py:1113-1124`، و`backend/safety.py:200-203` يسجّل `"command": message[:100]`. تشغيل: `/security/log 200 {"events":[{"event_type":"sovereign_command","details":{"command":"SECRET-OWNER-COMMAND"...` | خلل أمني | متوسطة | حماية المسار بمفتاح في الرأس، أو إعادة أعداد وأنواع فقط بلا محتوى |
| 1.5 `GET /api-key` يقبل السر الرئيسي في معامل استعلام `?master_key=`، وuvicorn يسجّل المسار مع الاستعلام في access log عند `--log-level info` | `backend/app.py:1307-1315`، و`start.sh` (`--log-level info`)، و`.venv-sov/.../uvicorn/protocols/http/h11_impl.py:466-473` + `uvicorn/protocols/utils.py:52-56` (`get_path_with_query_string`) | خلل أمني | متوسطة | إزالة صيغة الاستعلام أو رفضها (`/api-key-header` موجود)، وتعطيل access log أو تنقيته |
| 1.6 مقارنات مفتاح API ليست ثابتة الزمن (`==` و`!=`)، ولا تحديد لمعدل المحاولات على مسارات المفتاح | `backend/app.py:776,1296,1315` | خلل أمني | منخفضة | `hmac.compare_digest` + حد معدل |
| 1.7 `/guardian/status` لا يكشف محتوى ملفات القفل (أعلام حضور فقط)، و`/api-key` و`/api-key-header` يرفضان بلا مفتاح (403) | `backend/compat/guardian_api.py:35-76`. تشغيل: `/guardian/status 200 {"emergency_flags":{"system_locked":true,"ai_frozen":true}...` و`/api-key 403` | — (لا خلل في التسريب) | — | — |

## 2) مفتاح السيادة وdata/key.secret والنشر

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 2.1 سر واحد لكل الأغراض: `SOVEREIGN_KEY` هو مفتاح API الذي يرسله العميل عبر HTTP، وهو أيضًا أساس توقيع السجل، وتغليف مفتاح الفينيق الرئيسي، ومفتاح الرماد، ومفتاح تشفير المخزن. من يملك كلمة مرور API يملك كل التشفير | `backend/app.py:82` (`SOVEREIGN_KEY as SOVEREIGN_API_KEY`)، `backend/memory/core.py:448,460`، `backend/memory/defense/ransomware.py:1036,1192,1591,1611`، `backend/memory/store/__init__.py:508` | خلل أمني | حرجة | اشتقاق مفاتيح منفصلة لكل غرض (HKDF مع وسم الغرض)، وفصل مفتاح API عن مادة التشفير |
| 2.2 النشر لا يضبط `AI_ENVIRONMENT=production`، فيعمل الإنتاج كـ development: لا يُفعَّل الرفض المغلق، ويُولَّد `key.secret` جديد داخل نظام ملفات الحاوية المؤقت في كل نشر (لا volume) | `backend/config.py:19` (الافتراضي `"development"`)، و`config.py:145-158` (التوليد عند `IS_DEVELOPMENT`)، و`Dockerfile` (لا `ENV AI_ENVIRONMENT`)، و`fly.toml` قسم `[env]` (فيه `PORT` و`PYTHONPATH` فقط ولا mounts). تشغيل: `AI_ENVIRONMENT=production` بلا مفتاح → `ValueError`، أي أن الرفض يعمل فقط إن ضُبط المتغير | خلل أمني | حرجة | ضبط `AI_ENVIRONMENT=production` في Dockerfile/fly.toml، وتمرير السر عبر `fly secrets`، ورفض البدء إن غاب |
| 2.3 `.dockerignore` لا يستثني `data/key.secret` ولا `.env` ولا `data/keys/keyring.json` ولا `data/key.secret.*`، و`COPY . .` ينسخ سياق البناء كله. أي بناء من نسخة محلية فيها هذه الملفات يضمّن الأسرار في طبقات الصورة | `.dockerignore` (محتواه كاملًا: `fly.toml`، `.git/`، `__pycache__/`، `.envrc`، `.venv/`)، و`Dockerfile` (`COPY . .`) | خلل أمني | حرجة (مشروطة بوجود الأسرار في سياق البناء) | إضافة `data/` و`.env` و`*.secret*` و`credentials/` إلى `.dockerignore` |
| 2.4 `key.secret` الموجود يُقبل دون فحص أذوناته، فملف `0644` مقروء للجميع يُستخدم بصمت. فحص 0600 موجود في الاختبار فقط | `backend/config.py:133-142`. تشغيل: ملف `0644` في جذر معزول → `accepted 0644 key: True` | خلل أمني | متوسطة | `os.stat` ثم رفض أو تحذير إن كان `mode & 0o077 != 0`، أو `chmod 0600` |
| 2.5 توليد `key.secret` نفسه سليم: `secrets.token_urlsafe(32)` و`O_CREAT\|O_EXCL` بأذونات `0o600`، ومعالجة السباق بإعادة القراءة | `backend/config.py:145-163`. الاختبار `test_real_key_secret_exists` ينجح ويثبت `0600` في جذر معزول | — (لا خلل) | — | — |
| 2.6 استثناء `data/key.secret` من git فعّال، والملف لم يُدفع في أي commit | `git check-ignore -v data/key.secret` → `.gitignore:43:*.secret`، و`git log --all --diff-filter=A -- '*key.secret*'` → لا نتائج | — (لا خلل) | — | — |
| 2.7 قيم سرية ثابتة في الكود كبديل: إن فشل `from config import` يُستخدم نص ثابت معروف كمفتاح HMAC أو تشفير | `backend/memory/core.py:44-50` (`"يجب_تغيير_هذا_المفتاح_فوراً"`)، و`backend/memory/encoding.py:33-36`. تشغيل: تحميل `core.py` مستقلًا → `SOVEREIGN_KEY is hardcoded default: True` | خلل أمني | منخفضة (المسار العادي يجد config) | الفشل المغلق (raise) بدل القيمة الثابتة |
| 2.8 بديل ثانٍ ثابت: إن كان المفتاح فارغًا يُستبدل بـ `b'new_generated_key_here'` رغم أن التعليق يقول «توليد مفتاح جديد». والمقارنة تتم مع نص إنجليزي (`you_must_change_this_key_immediately`) لا يطابق البديل العربي في 2.7 | `backend/memory/core.py:460-463` | خلل أمني + عدم تطابق توثيق | منخفضة | الرفض بدل الاستبدال |
| 2.9 تعليق `config.py` يصف `key.secret` بأنه «مشفر»، والكود يقرؤه نصًا صريحًا | `backend/config.py:110` مقابل `135-138` | عدم تطابق توثيق | منخفضة | تصحيح الوصف |

## 3) KeyRing ومنظومة المفاتيح (`backend/sovereign/keys/`)

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 3.1 `keyring.json` يُكتب بـ `write_text` (umask الافتراضي، فيصير `0644`) ويحمل `private_key` نصًا صريحًا، والكتابة غير ذرية | `backend/sovereign/keys/keyring.py:151-163`. تشغيل: `keyring.json mode: 0o644 \| contains plaintext private_key: True` | خلل أمني | متوسطة | `os.open(..., 0o600)` مع ملف مؤقت ثم `os.replace`، وتغليف `private_key` تحت مفتاح منفصل |
| 3.2 ملف keyring تالف يُحمَّل بصمت كأنه فارغ (يُسجَّل الخطأ فقط)، ثم يكتب أول `save_to_disk` فوقه فتضيع كل المفاتيح. هذا يناقض قاعدة «لا حذف» | `keyring.py:129-146`، و`159`. تشغيل: `corrupt keyring loaded silently as empty: True` ثم `old keys survive after save: False` | خلل أمني | حرجة | فشل مغلق عند التحميل، ومنع الحفظ بعد فشل التحميل (على غرار `ransomware._state_master_key_invalid`)، ونسخة احتياطية قبل الكتابة |
| 3.3 الحدث المزوَّر المنسوب إلى مفتاح RETIRED يُصنَّف `unverifiable_missing_key` لا `invalid`، لأن فحص الحالة يسبق فحص HMAC. بعد أي تدوير يصبح كل تاريخ ما قبل التدوير قابلًا للتلاعب دون أن يصنّفه المتحقق (المستخدم في `/ledger/verify`) مزوّرًا | `backend/sovereign/keys/verifier.py:135-151` قبل `153-168`، و`backend/app.py:358,409` (`/ledger/verify` يستدعي `verifier.verify_event`). تشغيل: الحدث المزوّر نفسه → وهو ACTIVE: `invalid`، وبعد `rotate()`: `unverifiable_missing_key` | خلل أمني | حرجة | حساب HMAC أولًا متى توفرت مادة المفتاح، وإعادة INVALID عند عدم التطابق، ثم تطبيق سياسة الحالة على التطابق فقط |
| 3.4 حدث بـ `key_id` مختلق غير موجود في KeyRing يُصنَّف `unverifiable_missing_key`، فيمكن حقن أحداث مزوّرة لا تُعد مزوّرة | `verifier.py:105-110`. تشغيل: `forged event with fabricated key_id -> unverifiable_missing_key` | خلل أمني | متوسطة | تصنيف مستقل (مفتاح غير معروف) يُعامَل كفشل في `/ledger/verify` لكل حدث لاحق لنشأة KeyRing |
| 3.5 حدث `KEY_ROTATED` يُكتب في ledger بلا `signature` وبلا `hash/prev_hash`، خلافًا لتعليق «موقّعًا بالمفتاح الجديد» | `backend/sovereign/keys/rotation.py:8,49,73,92-108`. تشغيل: `KEY_ROTATED ledger line has signature field: False` | خلل أمني + عدم تطابق توثيق | متوسطة | كتابته عبر `SovereignCore.append_event` (موقّع ومتسلسل) |
| 3.6 `classify_ledger` ينهار بـ `KeyError: 'hash'` على أول سطر `KEY_ROTATED`، لأن `extract_event_data` يفترض الحقول، و`verify_event` يُستدعى بلا التقاط استثناء | `verifier.py:81` و`224` (ضمن `188-227`). تشغيل: `classify_ledger raised: KeyError 'hash'` | خلل أمني (توافر التحقق) | متوسطة | التقاط الاستثناء لكل سطر وتصنيفه `invalid`/`malformed` |
| 3.7 KeyRing لا يفرض آلة الحالات: `retire_key` يحوّل COMPROMISED إلى RETIRED (وهو «غسل» لحالة الاختراق)، و`mark_key_compromised` يقبل LOST→COMPROMISED. كلاهما ممنوع في العقد | `keyring.py:248-275,299-321` مقابل `state_machine.py:42-59`. تشغيل: `retire compromised ... -> retired` و`LOST->COMPROMISED allowed by code: True compromised` | خلل أمني | متوسطة | استدعاء `state_machine.transition()` داخل كل تغيير حالة |
| 3.8 `state_machine.py` غير مستخدم في أي مسار إنتاجي، بل في الاختبارات فقط، فالعقد الذي يحرسه `test_key_state_transitions.py` لا يُطبَّق على `keyring.py` و`verifier.py` | `grep -rn "state_machine\|KeyStateMachine\|KeyState\b" --include=*.py backend \| grep -v "/tests/\|keys/state_machine.py"` → لا نتائج | فجوة اختبار + عدم تطابق توثيق | متوسطة | ربط keyring/verifier بالآلة، واختبار يمر عبر `KeyRing` نفسه |
| 3.9 مفتاح خاص حقيقي دُفع إلى git في `05704ef:data/keys/keyring.json` (مفتاح `b8bf12ab28abfc01`، الحالة active، طول المفتاح 43) وما زال في التاريخ. والسجل الإلحاقي `data/keys/HISTORY.jsonl` لا يحوي أي `KEY_MARKED_COMPROMISED` له، بل ثلاثة أسطر `KEY_CREATED` فقط، أحدها `433759679aca9268` بسبب `"R-616: replacement for compromised key (exposed in git)"` | `git show 05704ef:data/keys/keyring.json` (فُحص وجود المفتاح وطوله دون طباعته)، و`git log --all -- data/keys/keyring.json` → `ff8f80a` و`05704ef`، و`data/keys/HISTORY.jsonl` الأسطر 1-3 | خلل أمني | متوسطة (المفتاح دُوِّر، لكن ما وقّعه قابل للتزوير لكل من يملك نسخة من المستودع، ولم تُتحقق حالته في keyring التشغيلي لأنه غير موجود في الشجرة) | تسجيل `KEY_MARKED_COMPROMISED` لـ `b8bf12ab28abfc01` في HISTORY، وضمان أن حالته في keyring التشغيلي COMPROMISED، والنظر في إعادة كتابة التاريخ إن كان المستودع عامًا |
| 3.10 اختبار (R-621) كتب مفتاحًا في HISTORY الحقيقي المتتبع: `979e95cbd4469226 "R-621 test"` | `data/keys/HISTORY.jsonl` السطر 3 | خلل أمني (تلويث سجل حقيقي) | منخفضة | توثيقه كحدث غير تشغيلي (لا حذف)، وحارس اختبار يمنع الكتابة إلى `data/keys` الحقيقي |
| 3.11 توليد المفاتيح سليم: `secrets.token_urlsafe(32)`، و`compare_digest` في التحقق، و`to_dict` يحجب `private_key` | `keyring.py:50-57,197`، و`verifier.py:157` | — (لا خلل) | — | — |
| 3.12 لا تسرب لمفاتيح خاصة في HISTORY المتتبع: حقول كل سطر هي `action, key_id, public_key, reason, ts` فقط | فحص مفاتيح JSON لكل سطر في `data/keys/HISTORY.jsonl` | — (لا خلل) | — | — |
| 3.13 `.gitignore` يغطي الآن `data/keys/keyring.json` و`data/key.secret.old_rotated_2026_10_14` و`data/key.secret.new` | `.gitignore:125,126,130` + `git check-ignore -v` لكل مسار | — (لا خلل) | — | — |

## 4) `backend/memory/defense/ransomware.py` (نظام الفينيق)

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 4.1 فهرس الرماد في الذاكرة فقط: `self.ashes` لا يُكتب على القرص (يُحفظ `ashes_count` وحده)، و`PHOENIX_ASHES_DIR` يُنشأ ولا يُكتب فيه شيء. بعد إعادة التشغيل يضيع الرماد وتفشل القيامة منه، رغم أن الموت أعلن نجاحه | `ransomware.py:64-67,177,1008,1644` (`grep -n "PHOENIX_ASHES_DIR"` → السطران 64 و66 فقط). تشغيل (pytest خارج الشجرة يرث مُهيّئات `TestAshResurrection`): `ashes_before_restart= 1 ashes_after_restart= 0 phase_after_restart= dead` ثم `resurrect_after_restart= False لا رماد متاح للاستعادة \| blob restored: False` | خلل أمني (توافر/استرداد) | حرجة | حفظ فهرس الرماد (المعرّف ← original_id + البصمة المشفرة) ذريًا قبل إعلان نجاح الموت، وتحميله في `_load_state` |
| 4.2 مقارنة مفتاح القيامة ليست ثابتة الزمن (`key == expected`)، رغم أن `hmac` مستورد في الملف دون أي استخدام | `ransomware.py:1190-1193`، و`19` (`grep -n "hmac\." ransomware.py` → لا نتائج) | خلل أمني | منخفضة | `hmac.compare_digest` |
| 4.3 الحماية كلها تعود إلى `SOVEREIGN_KEY`: مفتاح التغليف `sha256(SOVEREIGN_KEY)` بلا KDF ولا ملح، والمفتاح المقبول للقيامة `sha256(SOVEREIGN_KEY:master)`. من يملك `key.secret` و`phoenix_state.json` من القرص نفسه يستعيد كل شيء، فالحماية ضد مهاجم على القرص (سيناريو الفدية نفسه) صفرية | `ransomware.py:1591,1611,1192,1036` | خلل أمني (تصميم) | متوسطة | مفتاح قيامة يُحفظ خارج الجهاز ولا يُشتق من سر على القرص نفسه، + HKDF بوسوم أغراض |
| 4.4 `expires_at` للبذرة لا يُفرض عند فك التشفير أو القيامة، فالبذور المنتهية تبقى صالحة (الحقل يُستخدم لحلقة التجديد فقط) | `ransomware.py:608-625` (لا فحص)، و`1533` (التجديد فقط) | خلل أمني | منخفضة | رفض أو تحذير عند `expires_at < now` |
| 4.5 ملفات البذور والحالة تُكتب بأذونات umask الافتراضية، ومجلد `data/phoenix/` غير مستثنى من git | `ransomware.py:322-324,1676-1680`، و`git check-ignore -v data/phoenix/phoenix_state.json` → غير مستثنى | خلل أمني | منخفضة (المحتوى مشفر) | `0o600` وإضافة `data/phoenix/` إلى `.gitignore` |
| 4.6 كتلة `__main__` تطبع أول 32 حرفًا من مفتاح القيامة | `ransomware.py:2004-2006` | خلل أمني | منخفضة | عدم طباعة المفتاح |
| 4.7 الخوارزميات سليمة: AES-256-GCM، وnonce عشوائي 12 بايت لكل عملية (`get_random_bytes`)، وAAD يربط الإصدار والمعرّف، و`decrypt_and_verify` مع الفشل المغلق، ورفض صيغ XOR الإرثية خارج مسار الترحيل الصريح | `ransomware.py:431-444,520-534,987-996,1328-1347,1587-1625`. اختبارات التلاعب والتخفيض في `tests/test_return_none_lowrisk.py:94-115,300-391,1309` تنجح | — (لا خلل في هذا الجانب) | — | — |

## 5) `nexus/encryption/`

ملاحظة نطاق: المكونات الثلاثة تُنشأ في `nexus/main.py:113-115` بمفاتيح عشوائية مؤقتة (`os.urandom`)، ولم أجد مستدعيًا آخر لها خارج الاختبارات.

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 5.1 فك التشفير يتجاهل حقل `algorithm`، والتراجع إلى XOR بمفتاح متكرر ما زال في الكود عند غياب pycryptodome (مع تحذير في السجل فقط) | `nexus/encryption/encryption_engine.py:22-24,39,51-52,62-76,99-100`. تشغيل: تغيير `algorithm` إلى `"XOR-DEV"` → `algorithm field ignored ... -> hello` | خلل أمني | متوسطة | إزالة التراجع (raise عند غياب AES)، والتحقق من `algorithm/version` وإدخالهما في الـ MAC |
| 5.2 المفتاح نفسه يُستخدم لـ AES-CBC ولـ HMAC، ولا تحقق من طول المفتاح: مفتاح 16 بايت يعمل AES-128 بينما الوسم يقول `AES-256-CBC` | `encryption_engine.py:42,49,53,66`. تشغيل: `16B key ALGORITHM label: AES-256-CBC works: x` | خلل أمني | منخفضة | اشتقاق مفتاحين منفصلين، وفرض `len==32` |
| 5.3 تعليق الوحدة «لا يتطلب مكتبات خارجية — stdlib فقط» خاطئ (تستخدم pycryptodome) | `encryption_engine.py:4` مقابل `19-20` | عدم تطابق توثيق | منخفضة | تصحيح التعليق |
| 5.4 `SecureCommunication`: التوقيع على `f"{sender_id}\|{ts}\|{data}"` بلا ترميز للحدود، فيمكن إعادة تفسير رسالة موقّعة صحيحة على أنها رسالة أخرى بمرسل وحمولة مختلفين، متى بدأت الحمولة بـ `<رقم>\|`. ولا حد للطوابع الزمنية المستقبلية، فتُقبل الرسالة المعاد تفسيرها بطابع مستقبلي حتى مع `max_age` الافتراضي | `nexus/encryption/secure_communication.py:39-40,49,58-60`. تشغيل: `delimiter reinterpretation (old ts) -> True` و`delimiter reinterpretation (future ts, default max_age) -> True` | خلل أمني | متوسطة | توقيع ترميز قانوني (JSON مرتب أو حقول بأطوال مسبوقة)، ورفض `ts > now + skew` و`NaN` |
| 5.5 الحماية الأساسية في `SecureCommunication` تعمل: إعادة الإرسال تُرفض، والمقارنة بـ `compare_digest` | `secure_communication.py:53-66`. تشغيل: `verify: True replay: False` | — (لا خلل) | — | — |
| 5.6 `KeyManager`: التعليق يقول «المفتاح مشفر داخل الذاكرة» والمفتاح مخزن بايتات صريحة، و`_master_key` يُولَّد ولا يُستخدم أبدًا، ومجلد `nexus_data/keys` يُنشأ ولا يُكتب فيه، و`"RSA-2048"` ينتج 256 بايتًا عشوائيًا وليس مفتاح RSA | `nexus/encryption/key_manager.py:27-28,34-38,46` | عدم تطابق توثيق | منخفضة | تصحيح التعليقات وإزالة `RSA-2048` أو تنفيذه فعلًا |
| 5.7 التشفير داخل `encryption_engine` نفسه سليم في المسار الأساسي: IV عشوائي 16 بايت، وEncrypt-then-MAC يغطي `ciphertext+iv`، و`compare_digest`. التلاعب بالنص المشفر يُرفض | `encryption_engine.py:47-54,66-70`. تشغيل: `roundtrip: hello` و`tamper ct -> None` | — (لا خلل) | — | — |

## 6) `guardian/`

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 6.1 عبارة مرور افتراضية ثابتة: بلا `master_passphrase` تُقبل `"CHANGE_ME_IMMEDIATELY"` رمزًا للسيد، والمدخل الوحيد (`nexus/main.py:193`) يستدعي `initialize_guardian()` بلا عبارة | `guardian/master_guardian.py:92`، و`nexus/main.py:145,152,193`. تشغيل: `default passphrase accepted: True` | خلل أمني | حرجة | رفض الإنشاء بلا عبارة، أو قراءتها من سر خارجي |
| 6.2 «تفويض ذاتي»: `approve_changes` و`execute_approved_update` يأخذان رمز السيد **وتجزئته المتوقعة** من المستدعي نفسه، فأي مستدعٍ يمرّر `(x, sha256(x))` وينجح | `guardian/integrity_checker.py:207-215`، و`guardian/self_evolve.py:125-136`. تشغيل: `approve_changes self-auth: True` و`execute_approved_update self-auth: True` | خلل أمني | حرجة | التحقق مقابل تجزئة يملكها الحارس (`MasterGuardian.verify_master_code`) لا مقابل وسيط |
| 6.3 فحص «كود السيد» بمقارنة بادئة نصية خام، فيُتجاوز بـ `./backend/...` أو مسار مطلق أو `\` أو `x/../backend/...` | `guardian/master_guardian.py:232-233`. تشغيل: `'./backend/app.py' allowed: True`، `'/abs/backend/app.py' allowed: True`، `'backend\\app.py' allowed: True`، `'x/../backend/app.py' allowed: True` (بينما `'backend/app.py' allowed: False`) | خلل أمني | حرجة | `Path(target).resolve()` ثم `is_relative_to(repo_root/dir)` |
| 6.4 الوثيقة تقول إن كسر الزجاج يُفعَّل عند «مرتين أو أكثر»، بينما callbacks `on_emergency`، ومنها `breaker.activate` في `nexus/main.py`، تُستدعى عند **أول** انتهاك محمي | `guardian/emergency_breaker.py:65` و`master_guardian.py:199-206` مقابل `nexus/main.py:158-164`. تشغيل: `on_emergency callbacks after FIRST violation: ['disable_guardian'] emergency_triggered: False` | عدم تطابق توثيق + خلل منطقي | متوسطة | استدعاء callbacks داخل `_trigger_emergency` فقط |
| 6.5 رمز إعادة التفعيل يُكتب صريحًا في السجل على مستوى CRITICAL، فمن يقرأ السجلات يفك القفل | `guardian/emergency_breaker.py:238-239`. تشغيل: `reactivation code present in log output: True` | خلل أمني | متوسطة | عدم تسجيله، وإرساله عبر قناة منفصلة |
| 6.6 القفل والتجميد مجرد ملفات: `is_locked()` = وجود الملف، وحذف الملف يرفع القفل، ولا شيء في التشغيل الحي يقرأ `AI_FROZEN.flag` أو `SYSTEM_LOCKED.lock` ليوقف شيئًا (المستهلك الوحيد هو `/guardian/status` للعرض). والملفان متتبعان في git بحالة «مقفل»، والنظام يعمل كالمعتاد | `emergency_breaker.py:255-268,292-293`، و`grep -rn "AI_FROZEN\|SYSTEM_LOCKED" --include=*.py` → `guardian_api.py:68-69` فقط، و`git ls-files guardian/data/emergency` | خلل أمني + عدم تطابق توثيق | متوسطة | فرض القفل في مدخلات التطبيق (middleware)، وتوقيع ملف القفل (HMAC) |
| 6.7 `reactivate` يقرأ تجزئة الرمز من ملف القفل نفسه بلا مصادقة (من يكتب الملف يضع تجزئة رمزه)، والمقارنة ليست ثابتة الزمن، ولا حد للمحاولات | `emergency_breaker.py:258-263` | خلل أمني | منخفضة | تجزئة في الذاكرة أو موقّعة، و`compare_digest`، وحد للمحاولات |
| 6.8 `IntegrityChecker`: المسارات المحمية نسبية إلى cwd رغم تعليق R-611 «تعمل من أي دليل»، فمن cwd آخر يُبنى baseline فارغ وتعيد `check()` قائمة فارغة بصمت. كما أن غياب baseline يُعامَل ببناء جديد مع `[]` (حذف الملف يعيد الثقة)، والـ baseline غير موقّع، والملف غير المقروء لا يُعد تعديلًا | `guardian/integrity_checker.py:15-19` مقابل `28-37,92,142,167`، و`135-138,155,243-245`. تشغيل من cwd=/tmp: `baseline built from cwd=tmp: 0 files` | خلل أمني | متوسطة | مسارات مطلقة من `_REPO_ROOT`، والفشل المغلق عند غياب baseline، وتوقيع baseline بـ HMAC |
| 6.9 `verify_alignment` يحسب checksum لقائمة ثابتة مكتوبة داخل الدالة نفسها لا للقواعد الفعلية، فلا يكتشف أي انحراف أبدًا، والقائمة نفسها (3 أفعال) تخالف `PROTECTED_ACTIONS` (6 أفعال) | `guardian/self_evolve.py:205-213` مقابل `master_guardian.py:35-42`. تشغيل: بعد تفريغ `PROTECTED_ACTIONS` و`MASTER_CODE_DIRS` → `verify_alignment ... aligned` | خلل أمني + عدم تطابق توثيق | متوسطة | حساب checksum من الثوابت الفعلية المستوردة |
| 6.10 «توقيعات» أحداث الحارس هي `sha256(secret‖payload)[:24]` (ليست HMAC، ومبتورة إلى 96 بت)، والسر مؤقت لكل عملية فلا يمكن التحقق منها بعد إعادة التشغيل، ولا توجد دالة تحقق، و`details` خارج التوقيع. هذا يناقض «مسجّلة ولا يمكن محوها» | `master_guardian.py:9,91,242-243,252-264`، و`self_evolve.py:215-217` | خلل أمني + عدم تطابق توثيق | منخفضة | HMAC بمفتاح دائم يغطي السجل كاملًا مع تسلسل hash |
| 6.11 النسخة الاحتياطية في `_step3` تستخدم مسارات نسبية إلى cwd، و193 ملفًا من نسخة احتياطية قديمة للكود متتبعة في git (فيها القيم الثابتة القديمة من `config/core/encoding`) | `emergency_breaker.py:179-180`، و`git ls-files guardian/data/emergency/emergency_backups \| wc -l` → `193`، و`.gitignore:120` يستثني `*/data/` فقط | خلل أمني + عدم تطابق توثيق | منخفضة | مسارات من `_REPO_ROOT`، وتقرير عن إبقاء النسخ المتتبعة أو أرشفتها (بلا حذف) |
| 6.12 العشوائية في guardian سليمة (`os.urandom(32)` للأسرار، و`uuid4` للمعرّفات) | `master_guardian.py:91`، `emergency_breaker.py:72`، `self_evolve.py:62,147` | — (لا خلل) | — | — |

## 7) عدم تطابق التوثيق (docs/) مع الكود

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 7.1 «أسرار في الكود: 🟢 لا توجد أسرار مكتوبة» — خاطئ | `docs/SECURITY.md:20` مقابل `guardian/master_guardian.py:92` و`backend/memory/core.py:49,463` و`backend/memory/encoding.py:36` | عدم تطابق توثيق | متوسطة | تصحيح البند وإدراج القيم |
| 7.2 «التطوير يستخدم مفتاحًا عشوائيًا مؤقتًا» و«المفتاح يتولد عشوائيًا عند كل إقلاع (`secrets.token_hex(32)`) ولا يُحفظ» — قديم وخاطئ: التطوير يولّد `token_urlsafe(32)` ويحفظه في `data/key.secret` | `docs/SECURITY.md:14,30` مقابل `backend/config.py:145-158` | عدم تطابق توثيق | منخفضة | تحديث |
| 7.3 «في الإنتاج يفشل التشغيل مغلقًا» — صحيح في الكود، لكن مسار النشر الفعلي لا يدخل وضع الإنتاج أصلًا (2.2) | `docs/SECURITY.md:41` مقابل `Dockerfile` و`fly.toml` و`config.py:19` | عدم تطابق توثيق | متوسطة | توثيق شرط `AI_ENVIRONMENT` وضبطه في النشر |
| 7.4 RK-04 «أُغلق — النقاط العامة محمية» — بينما `/api/reset` و`/api/run` و`/api/event` و`/api/mode/{mode}` بلا مصادقة (1.1-1.3) | `docs/SECURITY.md:44-48` | عدم تطابق توثيق | حرجة (يعطي طمأنة زائفة عن خلل حرج) | إعادة فتح RK-04 |
| 7.5 «التشفير ✅ AES-256-CBC — لم يعد XOR-DEV» — التراجع إلى XOR-DEV ما زال في الكود، و`QuantumLikeEncryption` في `encoding.py` كله XOR متكرر بلا مصادقة («high» = ثلاث XOR تساوي XOR واحدًا بمفتاح 16 بايت، و`salt` يُولَّد ولا يُستخدم)، و«التوقيع» `sha3_256` بلا مفتاح. (لم أجد مستدعيًا حيًا لـ `encoder.encode/decode` خارج `__main__`) | `docs/SECURITY.md:22,76` مقابل `nexus/encryption/encryption_engine.py:51-52,74-75` و`backend/memory/encoding.py:360-408,679-682` | عدم تطابق توثيق | منخفضة | توثيق الوضع الحقيقي، ووسم `QuantumLikeEncryption` بأنه غير آمن |
| 7.6 القفل «أُبقي كآلية أمان» — لا يُفرض في أي مكان (6.6) | `docs/SECURITY.md:19,63-67` | عدم تطابق توثيق | متوسطة | توضيح أنه علامة لا تُفرض |
| 7.7 `KEY_STATE_MACHINE.md`: يذكر حالة `ROTATED` (الكود `RETIRED`)، و«ROTATED مسموح للتحقق التاريخي» (`verifier.py` يعيد unverifiable لـ RETIRED)، وحالات `UNVERIFIABLE_COMPROMISED/EXPIRED` (المتحقق الحي فيه 3 حالات فقط)، و«حقل `state` إلزامي وإلا فشل عند التحميل» (الكود `status`، والفشل يُبتلع ويعطي keyring فارغًا) | `docs/KEY_STATE_MACHINE.md:61-77` مقابل `keyring.py:24-31,133-146` و`verifier.py:24-27,135-151` | عدم تطابق توثيق | متوسطة | مواءمة الوثيقة أو الكود (يفضَّل ربط الكود بـ `state_machine.py`) |
| 7.8 `/orchestrator/cycle`: التعليق يقول «يتطلب X-API-Key في الرأس»، والكود يقرأ `api_key` من الجسم فقط. تشغيل: رأس فقط → `401`، جسم → يمر من المصادقة. (`docs/API.md:34` يقول «في الجسم» وهو مطابق للكود) | `backend/app.py:1334` مقابل `1337-1339` | عدم تطابق توثيق | منخفضة | تصحيح التعليق أو قبول الرأس |
| 7.9 `docs/API.md` يصف `/security/log` بـ «مصادقة: لا» دون التنبيه إلى أنه يكشف أوامر السيد، ويدرج `/api/reset` بلا عمود مصادقة | `docs/API.md:48,62-76` | عدم تطابق توثيق | منخفضة | ذكر المصادقة صراحة لكل مسار |
| 7.10 مسار ملف القفل في الوثيقة `data/emergency/SYSTEM_LOCKED.lock`، والفعلي `guardian/data/emergency/SYSTEM_LOCKED.lock` | `docs/ARCHITECTURE.md:73` مقابل `guardian/emergency_breaker.py:34-36` | عدم تطابق توثيق | منخفضة | تصحيح المسار |

## 8) فجوات الاختبارات الأمنية

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 8.1 لا اختبار يتحقق من مصادقة `/api/reset` و`/api/run` و`/api/event` و`/api/mode/*` و`/security/log` | `rg -n "api/reset\|/api/run\|/api/event\|/api/mode\|security/log" tests backend/tests` → `tests/test_safety_layer.py:69` فقط (وجود المسار لا مصادقته) | فجوة اختبار | حرجة | اختبار لكل مسار يكتب: 401/403 بلا مفتاح |
| 8.2 لا اختبار لأي منطق تفويض في guardian (العبارة الافتراضية، التفويض الذاتي، تجاوز المسار، رمز إعادة التفعيل) | `rg -n "reactivat\|_targets_master_code\|approve_changes\|execute_approved_update\|CHANGE_ME" tests backend/tests` → لا نتائج تفويض (`test_compat_layer.py:234` يخص التسريب فقط) | فجوة اختبار | حرجة | اختبارات سلبية لكل بند في القسم 6 |
| 8.3 اختبار فك تشفير `EncryptionEngine` معطوب: يمرر `hexdigest()` (نص 64 حرفًا) مفتاحًا، فالمحرك لا يستطيع التشفير أصلًا (`ValueError: Incorrect AES key length (64 bytes)`)، ويمرر نصًا بدل `EncryptedPayload` فيختبر `AttributeError` لا التلاعب، ويراقب اسم مسجّل `nexus.encryption.encryption_engine` بينما الفعلي `nexus.encryption.engine` | `tests/test_return_none_security.py:198,202-203` مقابل `encryption_engine.py:16`. تشغيل: `str key -> ValueError Incorrect AES key length (64 bytes)` | فجوة اختبار | متوسطة | اختبار ذهاب وإياب + قلب بت في ciphertext/iv/tag + تغيير `algorithm` |
| 8.4 لا اختبار لـ `SecureCommunication.verify_message` (إعادة الإرسال، الطابع المستقبلي، إعادة تفسير الحدود) | `rg -n "verify_message" tests backend/tests` → لا نتائج | فجوة اختبار | متوسطة | اختبارات للحالات الثلاث |
| 8.5 اختبار القيامة من الرماد لا يعيد التشغيل بين الموت والقيامة، فلم يكشف 4.1 | `tests/test_return_none_lowrisk.py:1251-1308` (الكائن `obj` نفسه للموت والقيامة) | فجوة اختبار | حرجة | اختبار موت ثم مثيل جديد ثم قيامة من الرماد |
| 8.6 اختبار التدوير يعلّق «موقّعًا بالمفتاح الجديد» ولا يتحقق من أي توقيع | `tests/test_sovereign_keys.py:257-264` | فجوة اختبار | متوسطة | `assert "signature" in rot_event` + تحقق HMAC + تمرير `classify_ledger` |
| 8.7 لا اختبار لتزوير حدث بمفتاح RETIRED أو بـ `key_id` مختلق ضمن مسار `SignatureVerifier`، ولا لتحميل keyring تالف، ولا لأذونات `keyring.json`، ولا لـ `key.secret` بأذونات متساهلة | `rg` على `tests backend/tests` لا يُظهر حالات من هذا النوع، والتجارب 3.1-3.4 و2.4 تنجح في كسرها بينما كل الاختبارات تمر | فجوة اختبار | متوسطة | اختبار لكل حالة |
| 8.8 `test_key_state_transitions.py` يختبر `state_machine.py` المعزول، لا `KeyRing` الذي لا يستخدمه (3.8) | `backend/tests/invariants/test_key_state_transitions.py` + 3.8 | فجوة اختبار | متوسطة | اختبار الانتقالات عبر `KeyRing.retire_key/mark_*` |

## 9) جرد `credentials/` (دون فتح أسرار)

| البند | الدليل (ملف:سطر) | نوعه | شدته | اقتراح المعالجة |
|---|---|---|---|---|
| 9.1 `credentials/` فيه ملف واحد: `ROTATION_RECEIPT.json` (11575 بايت، `0644`، متتبع، آخر commits عليه `dda6e51` …). فحصت بنية مفاتيحه وأنواعها وأطوالها فقط: بصمات من 16 حرفًا (`old_key_fingerprint` و`new_key_fingerprint`)، وأطوال المفاتيح، وحقول توثيقية، ولا حقل بطول أو شكل مفتاح خام | `ls -la credentials`، ومسح بنيوي بالبايثون يطبع المسار والنوع والطول دون القيم (الملحق ب) | — (لا سر خام ظاهر) | منخفضة | لا إجراء لازم. الاسم «credentials» مضلل لأنه إيصال لا اعتماد |
| 9.2 مسح الأسرار على كل الملفات المتتبعة (أنماط AWS وGitHub وOpenAI وPEM وSlack و`"private_key": "<قيمة طويلة>"` و`SOVEREIGN_KEY="..."`) — لا نتائج في HEAD. النتيجة الوحيدة تاريخية في 3.9 | أوامر `rg` في الملحق (أ)-12 | — (لا خلل في HEAD) | — | — |

## 10) جوانب فُحصت ولم يُعثر فيها على خلل (صراحة)

- **العشوائية**: كل توليد للأسرار والمفاتيح والـ nonce يستخدم `secrets` أو `os.urandom` أو `Crypto.Random.get_random_bytes` (`config.py:149`، `keyring.py:197`، `ransomware.py:298,432,682,991,1003,1549,1592`، `encryption_engine.py:42,47`، `key_manager.py:38,47`، `secure_communication.py:31`، guardian). الدالة `random` مستوردة في `ransomware.py:34`، والبحث عن `random\.` في الملف لا يجد استخدامًا لها في توليد مفاتيح. المسح: `grep -nE "random\.|secrets\.|get_random_bytes"`.
- **أوضاع AES**: لا ECB، ولا IV أو nonce ثابت أو معاد في أي من المسارات الحية (GCM في ransomware/store، وCBC+HMAC بـ IV عشوائي في nexus).
- **توليد data/key.secret واستثناؤه من git**: سليمان (2.5، 2.6).
- **تسرب مسار `/guardian/status`**: سليم (1.7).
- **اشتقاق `derive_key`** في nexus: PBKDF2-HMAC-SHA256 بـ 200000 تكرار وملح عشوائي 32 بايت — سليم (`encryption_engine.py:93-96`).

---

## الملحق (أ) — أوامر التحقق الرئيسية ونتائجها

1. `git log --oneline -1` → `4bc5500 …`، و`git status --short` → فارغ (قبل وبعد).
2. `for p in data/key.secret data/keys/keyring.json data/key.secret.old_rotated_2026_10_14 data/key.secret.new data/phoenix/phoenix_state.json data/keys/HISTORY.jsonl .env; do git check-ignore -v "$p"; done` → الأولى مستثناة بـ `.gitignore:43/125/126/130/42`، و`data/phoenix/phoenix_state.json` و`HISTORY.jsonl` غير مستثنيين (الثاني عمدًا: `!data/keys/HISTORY.jsonl`).
3. `git log --all --oneline --diff-filter=A --name-only -- '*key.secret*' '*keyring.json' '.env' '*.secret'` → `05704ef … data/keys/keyring.json` فقط.
4. `key.secret` بأذونات `0644` في جذر معزول: `env -u SOVEREIGN_KEY SOVEREIGN_DATA_ROOT=$T python -c "import sys; sys.path.insert(0,'backend'); import config; …"` → `accepted 0644 key: True`.
5. `AI_ENVIRONMENT=production` بلا مفتاح → `ValueError: ❌ خطأ أمني خطير: لم يتم تعيين مفتاح السيد في بيئة الإنتاج!`.
6. TestClient على `backend/app.py` (جذر بيانات مؤقت، `SOVEREIGN_KEYRING_FALLBACK_DISABLED=1`): `/security/log 200 (يعرض SECRET-OWNER-COMMAND)`، `/api-key 403`، `/orchestrator/cycle` برأس فقط `401`.
7. TestClient مع `api.get_orch` وهمي: `/api/reset no key -> 200`، `/api/mode/emergency no key -> 200`، `/sovereign/reset wrong key -> 401`.
8. `SovereignCore` معزول مع KeyRing محقون: `ledger lines before reset: 5 | .bak after 1st reset: 5 | .bak after 2nd reset: 2`.
9. `/tmp/ameen_probe_keys.py` → A..G2 (القسم 3).
10. `/tmp/ameen_probe_trans.py` → انتقالات الحالة (3.7).
11. `/tmp/ameen_probe_nexus.py` → القسم 5. `/tmp/ameen_probe_guardian.py` → القسم 6 (كل الكتابات إلى `/tmp` عبر إعادة توجيه الثوابت، و`os.chdir(/tmp)` قبل `activate` حتى لا يُنسخ الكود).
12. مسح الأسرار: `git ls-files -z | xargs -0 rg -n -e 'AKIA[0-9A-Z]{16}' -e 'ghp_[A-Za-z0-9]{36}' -e 'sk-[A-Za-z0-9]{20,}' -e '-----BEGIN [A-Z ]*PRIVATE KEY' -e 'xox[baprs]-'` → لا نتائج. و`… -e '"private_key"\s*:\s*"[A-Za-z0-9_\-]{30,}"' -e 'SOVEREIGN_KEY\s*=\s*["\x27][A-Za-z0-9_\-]{20,}'` → لا نتائج.
13. `python -m pytest /tmp/ameen_probe_tests/test_ameen_ash_restart.py -q -s -p no:cacheprovider --rootdir=.` → السطران `PROBE …` في 4.1.

## الملحق (ب) — نصوص التجارب (منسوخة حرفيًا من /tmp)

### `/tmp/ameen_probe_keys.py`

```python
import os, tempfile
import sys, os, tempfile, json, stat
from pathlib import Path
sys.path.insert(0,'.'); sys.path.insert(0,'backend'); os.environ['SOVEREIGN_DATA_ROOT']=tempfile.mkdtemp()+'/data'
T=Path(tempfile.mkdtemp())
os.umask(0o022)
from backend.sovereign.keys.keyring import KeyRing, KeyStatus
from backend.sovereign.keys.rotation import KeyRotation
from backend.sovereign.keys.verifier import SignatureVerifier
kr=KeyRing(keys_dir=T/"keys"); k1=kr.generate_new_key("probe"); kr.save_to_disk()
print("A) keyring.json mode:", oct(stat.S_IMODE((T/"keys/keyring.json").stat().st_mode)), "| contains plaintext private_key:", k1.private_key in (T/"keys/keyring.json").read_text())
v=SignatureVerifier(kr)
ev={"hash":"h","prev_hash":"p","blob":"b","time":"t","type":"x","key_id":k1.key_id}
ev["signature"]=v._compute_signature(v.extract_event_data(ev),k1.private_key)
forged=dict(ev, blob="EVIL")
print("B) forged event, key ACTIVE ->", v.verify_event(forged).status.value)
rot=KeyRotation(kr, ledger_path=T/"ledger.jsonl"); k2=rot.rotate("probe")
print("C) same forged event after rotation (key RETIRED) ->", v.verify_event(forged).status.value)
forged2=dict(forged, key_id="0000000000000000")
print("D) forged event with fabricated key_id ->", v.verify_event(forged2).status.value)
line=(T/"ledger.jsonl").read_text().strip(); print("E) KEY_ROTATED ledger line has signature field:", "signature" in json.loads(line))
try:
    print("F) classify_ledger on rotation ledger:", v.classify_ledger(T/"ledger.jsonl"))
except Exception as e: print("F) classify_ledger raised:", type(e).__name__, e)
# corrupt keyring -> silent empty -> save overwrites
kf=T/"keys/keyring.json"; orig=kf.read_text(); kf.write_text(orig[:-5])
kr2=KeyRing(keys_dir=T/"keys").load_from_disk()
print("G) corrupt keyring loaded silently as empty:", kr2.stats()["total_keys"]==0)
kr2.generate_new_key("after-corrupt"); kr2.save_to_disk()
print("G2) old keys survive after save:", k1.key_id in kf.read_text() or k2.key_id in kf.read_text())
```

### `/tmp/ameen_probe_trans.py`

```python
import os, sys, tempfile
sys.path.insert(0,'.'); sys.path.insert(0,'backend'); os.environ['SOVEREIGN_DATA_ROOT']=tempfile.mkdtemp()+'/data'
from pathlib import Path
from backend.sovereign.keys.keyring import KeyRing
kr=KeyRing(keys_dir=Path(tempfile.mkdtemp()))
k=kr.generate_new_key("p")
print("compromised:", kr.mark_key_compromised(k.key_id,"leak"), kr.get_key(k.key_id).status.value)
print("retire compromised (COMPROMISED->RETIRED, forbidden by contract):", kr.retire_key(k.key_id,"rotated"), "->", kr.get_key(k.key_id).status.value)
k2=kr.generate_new_key("p2"); kr.mark_key_lost(k2.key_id)
print("LOST->COMPROMISED allowed by code:", kr.mark_key_compromised(k2.key_id,"x"), kr.get_key(k2.key_id).status.value)
```

### `/tmp/ameen_probe_nexus.py`

```python
import sys, base64, dataclasses, time
sys.path.insert(0,'.')
from nexus.encryption.encryption_engine import EncryptionEngine, EncryptedPayload
from nexus.encryption.secure_communication import SecureCommunication, SignedMessage
e=EncryptionEngine()
p=e.encrypt("hello")
print("roundtrip:", e.decrypt(p))
ct=bytearray(base64.b64decode(p.ciphertext_b64)); ct[0]^=1
p2=dataclasses.replace(p,ciphertext_b64=base64.b64encode(bytes(ct)).decode())
print("tamper ct ->", e.decrypt(p2))
p3=dataclasses.replace(p,algorithm="XOR-DEV")
print("algorithm field ignored (changed to XOR-DEV) ->", e.decrypt(p3))
# str key
try:
    EncryptionEngine(master_key="a"*64).encrypt("x"); print("str key accepted")
except Exception as ex: print("str key ->", type(ex).__name__, ex)
# 16-byte key -> AES-128 silently
e16=EncryptionEngine(master_key=b"k"*16); print("16B key ALGORITHM label:", e16.ALGORITHM, "works:", e16.decrypt(e16.encrypt("x")))
# secure comm future timestamp
s=SecureCommunication(secret=b"s"*32)
m=s.sign_message({"a":1},"A")
print("verify:", s.verify_message(m), "replay:", s.verify_message(m))
# delimiter ambiguity
m=s.sign_message("1700000000.0|evil","A")
forged=SignedMessage(payload="evil", signature=m.signature, timestamp=1700000000.0, sender_id=f"A|{m.timestamp}")
print("delimiter reinterpretation (old ts) ->", s.verify_message(forged, max_age_seconds=10**10))
fut=time.time()+10**6
m=s.sign_message(f"{fut}|evil","A")
forged=SignedMessage(payload="evil", signature=m.signature, timestamp=fut, sender_id=f"A|{m.timestamp}")
print("delimiter reinterpretation (future ts, default max_age) ->", s.verify_message(forged))
```

### `/tmp/ameen_probe_guardian.py`

```python
import sys, os, tempfile, hashlib, logging, io
from pathlib import Path
sys.path.insert(0,'.')
T=Path(tempfile.mkdtemp())
import guardian.emergency_breaker as eb, guardian.integrity_checker as ic, guardian.self_evolve as se
# redirect all writes to tmp
eb.EMERGENCY_LOG_DIR=T/"em"; eb.EMERGENCY_LOG_FILE=T/"em/ev.jsonl"; eb.LOCK_FILE=T/"em/LOCK"; eb.BACKUP_DIR=T/"em/bk"
ic.INTEGRITY_DB=T/"ib.json"; ic.INTEGRITY_LOG=T/"il.jsonl"; se.EVOLUTION_LOG=T/"evo.jsonl"
from guardian.master_guardian import MasterGuardian
g=MasterGuardian(guardian_dir=str(T/"g"))
print("1) default passphrase accepted:", g.verify_master_code("CHANGE_ME_IMMEDIATELY"))
calls=[]
g.on("on_emergency", lambda e: calls.append(e.action))
g.request_action("AI","disable_guardian")
print("2) on_emergency callbacks after FIRST violation:", calls, "emergency_triggered:", g.status.emergency_triggered)
for t in ["backend/app.py","./backend/app.py","/abs/backend/app.py","backend\\app.py","frontend/../backend/app.py","x/../backend/app.py"]:
    r=g.request_action("AI","write_file",target=t)
    print("3) target",repr(t),"allowed:",r["allowed"])
# integrity approve self-auth
c=ic.IntegrityChecker()
print("4) approve_changes self-auth:", c.approve_changes([],"attacker",hashlib.sha256(b"attacker").hexdigest())["success"])
ev=se.GuardianSelfEvolver()
p=ev.propose_key_rotation()
print("5) execute_approved_update self-auth:", ev.execute_approved_update(p["proposal_id"],"attacker",hashlib.sha256(b"attacker").hexdigest())["success"])
import guardian.master_guardian as mg
mg.PROTECTED_ACTIONS.clear(); mg.MASTER_CODE_DIRS.clear()
print("6) verify_alignment after clearing PROTECTED_ACTIONS+MASTER_CODE_DIRS:", ev.verify_alignment()["status"])
# reactivation code in logs
buf=io.StringIO(); h=logging.StreamHandler(buf); logging.getLogger("guardian.emergency").addHandler(h); logging.getLogger("guardian.emergency").setLevel(logging.INFO)
b=eb.EmergencyBreaker()
os.chdir(T)  # avoid copying repo code in step3
inc=b.activate("probe","AI")
code=b._reactivation_code
print("7) reactivation code present in log output:", code in buf.getvalue())
eb.LOCK_FILE.unlink()
print("8) after deleting lock file is_locked():", b.is_locked())
# integrity: cwd-relative
c2=ic.IntegrityChecker(); 
print("9) baseline built from cwd=tmp:", len(c2.build_baseline()), "files (repo has protected files but cwd differs)")
```

### `/tmp/ameen_probe_tests/test_ameen_ash_restart.py`

```python
import threading as _th
from unittest.mock import MagicMock
from tests.test_return_none_lowrisk import TestAshResurrection, _IsolatedStore, _NoThreads

class TestAmeenAshRestartProbe(TestAshResurrection):
    def test_ashes_lost_after_restart(self, tmp_path, monkeypatch):
        import backend.memory.defense.ransomware as rw
        import backend.memory.store as store_mod
        seeds_dir = tmp_path / "seeds"; seeds_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(rw, "PHOENIX_SEEDS_DIR", seeds_dir)
        monkeypatch.setattr(rw, "PHOENIX_STATE_FILE", tmp_path / "phoenix_state.json")
        core = self._mock_core_with_blobs(tmp_path)
        monkeypatch.setattr(rw, "get_core", lambda: core)
        monkeypatch.setattr(rw, "get_encoder", lambda: MagicMock())
        monkeypatch.setattr(rw, "get_watcher", lambda: MagicMock())
        iso = _IsolatedStore(); monkeypatch.setattr(store_mod, "get_store", lambda: iso)
        monkeypatch.setattr(_th, "Thread", _NoThreads)
        original = b"ameen_probe_" * 16
        h = core.blob_store.put(original, compress=True)
        core.iterate_events = lambda limit=1000, **k: [{"blob": h}]
        obj = rw.RansomwareDefense()
        assert obj.initiate_death(reason="probe") is True
        n_before = len(obj.ashes)
        key = obj.get_resurrection_key()
        core.blob_store.delete(h)
        for f in seeds_dir.glob("*.enc"): f.unlink()
        restarted = rw.RansomwareDefense()   # simulated process restart
        print("\nPROBE ashes_before_restart=", n_before, "ashes_after_restart=", len(restarted.ashes),
              "phase_after_restart=", restarted.phoenix_phase.value)
        res = restarted.resurrect(key)
        print("PROBE resurrect_after_restart=", res.get("success"), res.get("error"), "| blob restored:", core.blob_store.exists(h))
```

### مسح بنية `credentials/ROTATION_RECEIPT.json` (يطبع المسار والنوع والطول فقط — لا قيم)

```python
import json; d=json.load(open('credentials/ROTATION_RECEIPT.json'))
def walk(x,p=''):
    if isinstance(x,dict):
        for k,v in x.items(): walk(v,p+'/'+k)
    elif isinstance(x,list): print(p,'[list len',len(x),']')
    else: print(p, type(x).__name__, 'len', len(str(x)))
walk(d)
```

### فحص المفتاح المدفوع تاريخيًا (لا يطبع المفتاح)

```python
import subprocess, json
s=subprocess.run(["git","show","05704ef:data/keys/keyring.json"],capture_output=True,text=True).stdout
for k in json.loads(s)["keys"]:
    pk=k.get("private_key"); print(k["key_id"], k["status"], bool(pk) and pk!="***redacted***", len(pk or ""))
# الناتج: b8bf12ab28abfc01 active True 43
```

— نهاية التقرير الخام (أمين، الجولة 1) —
