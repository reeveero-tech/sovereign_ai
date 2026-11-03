# R-840c — ملحق تدقيق نظام الموصلات: تحويل الادعاءات إلى براهين

**التاريخ:** 2026-11-03 · **الحالة:** مُسلَّم للفصل
**المرجع:** توجيه المالك «توجيه تدقيق ملحق — Connector System Audit Addendum»
**النطاق:** لا عمل جديد — تدقيق ما نُفّذ في R-840/R-840b، مع تصحيح أخطاء التقرير،
وإصلاح ثلاثة خلل حقيقية كشفها التدقيق نفسه (بمسار الحوكمة الكامل).

---

## ٠) تصحيحات صريحة لادعاءات التقرير السابق (قبل المصفوفات)

التقرير السابق (R-840) وثّق ادعاءات ثلاثة تبيّن عند التدقيق أنها غير دقيقة.
تُصحَّح هنا ولا تُخفى:

| # | الادعاء السابق | الحقيقة بعد التدقيق | الدليل |
|---|---|---|---|
| ت-١ | «30 نوع مصادقة» | **34 نوعًا** في `AUTH_TYPES` | `backend/connector_system/auth_types.py` (الأسطر 46–175)؛ `GET /connectors/system/auth-types` يعيد `total: 34` |
| ت-٢ | «اختبار حي على GitHub عبر نظام الموصلات» | الاختبار الحي (`test_operational_github_live_pat`) كان يستدعي `httpx` مباشرة — **لم يمر عبر المنفذ/الموصل أصلًا**. عالجه هذا التدقيق: أُضيف `test_operational_github_through_executor` (خزينة → حل → منفذ → موصل) ونجح حيًا | `backend/tests/test_connector_system.py:536–547` (القديم) مقابل `backend/tests/test_connector_audit_addendum.py::test_operational_github_through_executor` (الجديد) |
| ت-٣ | مصفوفة القبول: «5 \| PAT دقيق النطاق \| test_fine_grained_pat» | **اسم الاختبار المذكور غير موجود** — المعيار 5 لا يملك اختبارًا مخصصًا (يغطيه جزئيًا فصل النطاقات في المعيار 1). صُحّح جدول `CONNECTOR_ACCEPTANCE.md` | `rg test_fine_grained` في المستودع = لا نتائج |
| ت-٤ | «/setup يعمل» (ضمنيًا في وثاقة الواجهة) | نقطة `/setup` كانت **تنهار بـ TypeError** (`auth_type_id` لا يطابق توقيع `create`) — لم تكن مختبرة على مستوى API قط. أصلحها هذا التدقيق | `backend/connector_system/api_routes.py:115` قبل/بعد؛ الاختبار: `test_audit_canary_secret_never_in_any_output` (ينجح الآن عبر `/setup` فعليًا) |

**الخلل الثلاثة التي أصلحها التدقيق (كلها بلا تغيير سلوك مشروع، مع اختبار حارس):**

1. `/setup` TypeError (ت-٤ أعلاه) — حارس: اختبار الكناري يستدعي `/setup` فعليًا.
2. رفض سياسة المؤسسة كان يسقط **500** بدل 403 في `/setup` و`/execute`
   (`PolicyError` غير معترض) — حارس: `test_audit_policy_denied_returns_403_not_500`.
3. نصوص الأخطاء كانت تُسجَّل/تُرفع كما هي — إن صدّى المزود السر في رسالة خطأ
   (استثناء نقل يحوي الرابط مثلًا) وصل إلى السجل ورد API — حارس: سيناريو
   «صدى المزود» داخل `test_audit_canary_secret_never_in_any_output` (الدالة
   `_scrub` في `execution.py:60–69`).

---

## أ) مصفوفة أنواع المصادقة — 34 صفًا (لا دمج)

التصنيف الاصطلاحي: **implemented** = كود موجود في `auth_types` + فرع في
`resolve()` أو مُعالج مخصص؛ **tested** = اختبار آلي بالاسم؛ **verified_live**
= تشغيل حقيقي ضد مزود؛ **documented_only** = معرّف في المصفوفة بلا فرع فعلي؛
**planned** = غير موجود أصلًا (لا صف هنا يحمله — لا ادعاء بذلك).

المصادر: `auth_types.py` (التعريف)، `auth_engine.py:280–371` (`resolve`)،
`backend/tests/test_connector_system.py` و`backend/tests/test_connector_audit_addendum.py`
(الاختبارات). «فرع bearer» = `auth_engine.py:286–294`.

| # | نوع المصادقة | الخطر | implemented | tested (آلي) | verified_live | documented | ملاحظات/قيد |
|---|---|---|---|---|---|---|---|
| 1 | oauth2_auth_code_pkce | safe | نعم — تدفق كامل `OAuthPKCEFlow` + فرع bearer | نعم — `test_acceptance_4_oauth_pkce_full_flow_and_reject_without_pkce` + `test_acceptance_oauth_refresh_and_401_single_retry` + `test_acceptance_2` | لا | نعم | تدفق المحرك مختبر بمزود مزيف؛ مسار API (`/oauth/callback`) لا يكمل التبديل — فجوة ج-٢ |
| 2 | oauth2_auth_code (بلا PKCE) | caution | نعم — فرع bearer | جزئي — عبر `test_acceptance_2` (تكافؤ مادة Bearer مع PAT) | لا | نعم | لا اختبار مخصص للتدفق بلا PKCE |
| 3 | client_credentials | safe | نعم — فرع bearer | لا — لا اختبار | لا | نعم | not_yet_verified (فجوة ج-٥ ضمنيًا) |
| 4 | device_code | safe | نعم — `build_device_flow_start` + فرع bearer | لا — الدالة بلا اختبار | لا | نعم | not_yet_verified |
| 5 | implicit | deprecated | محظور بالتصميم | نعم — `test_audit_deprecated_auth_types_rejected_at_setup_api` (رفض 400 صريح) | لا (مرفوض) | نعم | عزل مزدوج: ليس في `auth_types` أي موصل + رفض في `/setup` (`api_routes.py:108–109`) حتى مع سياسة سماح |
| 6 | ropc | deprecated | محظور بالتصميم | نعم — نفس اختبار الرفض | لا (مرفوض) | نعم | كصف 5 |
| 7 | oauth1a | caution | جزئي — `oauth1a_sign` مُنفّذ؛ `resolve` يوقّع ضد URL وهمي (`auth_engine.py:354–358`) | جزئي — `test_acceptance_12_oauth1a_signature` (الدالة: حتمية + طول HMAC-SHA1) | لا | نعم | التوقيع كدالة مختبر؛ الربط بطلب فعلي not_yet_verified (فجوة ج-٤) |
| 8 | refresh_token | safe | نعم — `refresh_credential` | جزئي — عبر `test_acceptance_oauth_refresh_and_401_single_retry` (باعتماد oauth2_auth_code_pkce) | لا | نعم | تجديد النوع نفسه مختبر ضمن تدفق OAuth |
| 9 | obo | safe | نعم — فرع bearer | لا | لا | نعم | not_yet_verified |
| 10 | app_installation | safe | نعم — فرع bearer (`installation_token`) | لا | لا | نعم | not_yet_verified |
| 11 | pat | safe | نعم — فرع bearer | نعم — `test_acceptance_1`، `14`، `16`، `17`، `18`، `19` + الكناري | **نعم** — `test_operational_github_through_executor` (عبر المنفذ، GET /user حقيقي) و`test_operational_github_live_pat` | نعم | النوع الوحيد verified_live |
| 12 | bot_token | safe | نعم — فرع bearer | لا — لا اختبار مخصص | لا | نعم | not_yet_verified |
| 13 | ssh_key | caution | **documented_only** — `resolve` يعيد مادة فارغة (`auth_engine.py:369–371`) | لا | لا | نعم | فجوة ج-٣ |
| 14 | app_password | caution | **documented_only** — مادة فارغة | لا | لا | نعم | فجوة ج-٣ |
| 15 | connection_string | caution | جزئي — `resolve` يعيد مادة فارغة بلا ترويسات (`auth_engine.py:366–367`) | لا | لا | نعم | فجوة ج-٣ |
| 16 | api_key | safe | نعم | نعم — `test_acceptance_3` (Render) + `test_acceptance_21` (OpenAPI عام) | لا | نعم | |
| 17 | api_key_secret | safe | نعم — ترويستان X-API-Key/Secret | لا | لا | نعم | not_yet_verified |
| 18 | service_account | safe | نعم — تحقق JSON + فرع resolve | نعم — `test_acceptance_7_service_account_json_validation` (قبول/رفض بالسبب) | لا | نعم | PEM اصطناعي وقت التشغيل (مبدأ حارس D-032) |
| 19 | presigned_url | caution | **documented_only** — مادة فارغة | لا | لا | نعم | فجوة ج-٣ |
| 20 | webhook_url | caution | نعم — `validate_webhook_url` (https فقط) | نعم — `test_acceptance_13_webhook_url_with_embedded_secret` | لا | نعم | |
| 21 | mtls | safe | نعم — `build_mtls_material` (مطابقة مفتاح عمومي فعليًا) | نعم — `test_acceptance_8_mtls` (شهادة موقعة ذاتيًا حقيقية + مفتاح أجنبي يُرفض) | لا | نعم | لا تحقق سلسلة CA (فجوة ج-٦) |
| 22 | x509 | safe | **documented_only** — مادة فارغة | لا | لا | نعم | فجوة ج-٣ |
| 23 | basic | caution | نعم — Base64 | نعم — `test_acceptance_6_basic_auth_works_with_warning` (تحذير موجود) | لا | نعم | |
| 24 | jwt_signed | safe | جزئي — `sign_jwt_hs256` مُنفّذ؛ **`resolve` يعيد مادة فارغة** (لا فرع) | جزئي — `test_acceptance_9` (الدالة) | لا | نعم | التوليد مختبر؛ الربط في resolve غير موجود (فجوة ج-٣) |
| 25 | jwt_bearer_grant | safe | جزئي — `sign_jwt_rs256` + `build_jwt_bearer_grant` مُنفّذان؛ resolve = bearer فقط | جزئي — `test_acceptance_9` (الدالتان) | لا | نعم | منح RFC 7523 لا يُرسل عبر resolve (فجوة ج-٤) |
| 26 | saml | caution | **documented_only** — مادة فارغة | لا | لا | نعم | فجوة ج-٣ |
| 27 | kerberos | caution | **documented_only** — مادة فارغة | لا | لا | نعم | فجوة ج-٣ |
| 28 | hmac | safe | نعم — `verify_hmac` (مقارنة ثابتة الزمن) + بوابة | نعم — `test_acceptance_10` + `test_acceptance_15` + الكناري (رفض Webhook) | لا | نعم | التوقيع الصادر `sign_request` في resolve علامة عدم (`lambda: None`) — للتحقق الوارد فقط |
| 29 | signed_request | safe | نعم — فرع resolve (طابع زمني + nonce) | لا | لا | نعم | not_yet_verified |
| 30 | sts | safe | نعم — فرع resolve + `refresh_credential` STS | جزئي — `test_acceptance_11_sts_temporary_expiry` (الانتهاء فقط) | لا | نعم | ترويسات ناقصة (Credential بلا توقيع SigV4 كامل) — فجوة ج-٤ |
| 31 | one_time | caution | نعم — فرع bearer | لا | لا | نعم | not_yet_verified |
| 32 | cookies_session | deprecated | محظور بالتصميم | نعم — اختبار الرفض نفسه | لا (مرفوض) | نعم | كصف 5 |
| 33 | header_injection | safe | نعم — ترويسة مخصصة | لا | لا | نعم | not_yet_verified |
| 34 | query_token | deprecated | محظور بالتصميم | نعم — اختبار الرفض نفسه | لا (مرفوض) | نعم | كصف 5 — وكان محظورًا حتى قبلها: لا موصل يعرضه |

**خلاصة المصفوفة:** 26 نوعًا implemented (منها 1 محظور بالتصميم عمدًا... بل 4
محرمة: صفوف 5/6/32/34)، 8 أنواع documented_only (13، 14، 15، 19، 22، 24، 26،
27 — منها jwt_signed وjwt_bearer_grant «جزئي»)، verified_live = PAT فقط.

---

## ب) مصفوفة معايير القبول الـ24 × نوع المصادقة المُختبر

قاعدة التوجيه مطبقة: المعيار الذي جُرّب على GitHub/PAT فقط يُسجَّل كذلك.
«حي» = تشغيل ضد مزود حقيقي. الملفان: `test_connector_system.py` (S)
و`test_connector_audit_addendum.py` (A).

| # | المعيار | نوع المصادقة المُختبر | نوع الاختبار | النتيجة | ملف الدليل |
|---|---|---|---|---|---|
| 1 | GitHub OAuth+PAT بنطاقات منفصلة | oauth2_auth_code_pkce + pat | وحدة (تعريف) | passed | S::`test_acceptance_1_github_definition_oauth_and_pat_with_separated_scopes` |
| 2 | GitLab PAT/OAuth بلا تغيير كود | pat + oauth2 (تكافؤ مادة Bearer) | وحدة | passed | S::`test_acceptance_2_gitlab_pat_oauth_swap_without_code_change` |
| 3 | مفتاح API | api_key (Render) | وحدة | passed | S::`test_acceptance_3_api_key_setup_encrypted_storage_and_use` |
| 4 | OAuth+PKCE إلزامي | oauth2_auth_code_pkce | وحدة (مزود مزيف + رفض بلا verifier) | passed | S::`test_acceptance_4_oauth_pkce_full_flow_and_reject_without_pkce` |
| 5 | PAT دقيق النطاق | pat (مفهوم النطاق فقط) | **not_yet_verified كمعيار مخصص** — يغطيه فصل النطاقات في المعيار 1؛ لا اختبار لتدفق fine-grained مخصص | جزئي | S::`test_acceptance_1` (جزئي) — صُحح توثيق CONNECTOR_ACCEPTANCE |
| 6 | Basic + تحذير | basic | وحدة | passed | S::`test_acceptance_6_basic_auth_works_with_warning` |
| 7 | Service Account JSON | service_account | وحدة | passed | S::`test_acceptance_7_service_account_json_validation` |
| 8 | mTLS | mtls | وحدة (شهادة حقيقية + crypto) | passed | S::`test_acceptance_8_mtls` |
| 9 | JWT موقّع | jwt_signed (HS256) + jwt_bearer_grant (RS256) | وحدة (دوال) | passed | S::`test_acceptance_9_jwt_signed_and_bearer_grant` |
| 10 | HMAC/SigV4 | hmac (+ دالة SigV4) | وحدة | passed | S::`test_acceptance_10_hmac_sigv4_sign_and_reject_wrong` |
| 11 | STS مؤقت | sts | وحدة (الانتهاء فقط) | passed | S::`test_acceptance_11_sts_temporary_expiry` |
| 12 | OAuth 1.0a | oauth1a | وحدة (دالة التوقيع) | passed | S::`test_acceptance_12_oauth1a_signature` |
| 13 | Webhook بسر مضمّن | webhook_url | وحدة | passed | S::`test_acceptance_13_webhook_url_with_embedded_secret` |
| 14 | التدوير | pat + oauth2 (تجديد) | وحدة | passed | S::`test_acceptance_14_secret_rotation_without_downtime` + `test_acceptance_oauth_refresh_and_401_single_retry` |
| 15 | بوابة Webhook | hmac | وحدة (توقيع خاطئ + dedup + نافذة زمنية + DLQ) | passed | S::`test_acceptance_15_webhook_gateway_hmac_replay_dedup_dlq` |
| 16 | Idempotency | pat (github) | وحدة | passed | S::`test_acceptance_16_idempotency_no_duplicate_writes` |
| 17 | قاطع الدائرة | pat | وحدة (فشل 500 محاكى) + تعافٍ (A) | passed | S::`test_acceptance_17_circuit_breaker` + A::`test_audit_breaker_opens_then_recovers_after_cooldown` |
| 18 | read-only يرفض الكتابة | pat | وحدة | passed | S::`test_acceptance_18_read_only_refuses_write` |
| 19 | لا تسريب أسرار | pat | وحدة + كناري آلي (A) | passed | S::`test_acceptance_19_no_secret_leak_in_logs_or_responses` + A::`test_audit_canary_secret_never_in_any_output` |
| 20 | دورة الحياة | — (سجل) | وحدة | passed | S::`test_acceptance_20_lifecycle_version_and_deprecation_notice` |
| 21 | OpenAPI عام | api_key | وحدة | passed | S::`test_acceptance_21_generic_openapi_register_and_read` |
| 22 | واجهة كاملة | — | تكامل (TestClient + ملفات) | passed | S::`test_acceptance_22_ui_endpoints_and_files` |
| 23 | بطاقة «يتطلب اتصالًا» | pat | وحدة + تكامل API (424 — A) | passed | S::`test_acceptance_23` + A::`test_audit_execute_without_connection_returns_424_card` |
| 24 | سياسة المؤسسة | oauth2/pat | وحدة + تكامل API (403 — A) | passed | S::`test_acceptance_24` + A::`test_audit_policy_denied_returns_403_not_500` |

**المصحح:** المعيار 5 حالته not_yet_verified كمعيار مخصص (ت-٣ أعلاه) — لا
تعميم. المعايير 1–4 و6–24 مغطاة باختبارات آلية مسماة.

---

## ج) دليل حي لكل موصل مبدئي

| الموصل | اتصال حي فعلي؟ | العمليات المنفّذة | نوع المصادقة | مسار البرهان (بلا أسرار) | ما لم يُجرَّب بعد |
|---|---|---|---|---|---|
| **GitHub** | **نعم — عبر المنفذ نفسه** | قراءة فقط: `test_connection` (GET /user) | pat | أمر التشغيل: `pytest tests/test_frontend_inventory.py backend/tests/test_connector_audit_addendum.py backend/tests/test_connector_system.py -m operational --run-operational` — الناتج: `test_operational_github_through_executor PASSED` + `test_operational_github_live_pat PASSED` (2 passed). المفتاح من `GITHUB_TEST_PAT` في البيئة — لا سر في الكود ولا في السجل | كل عمليات الكتابة (`issue_create`)؛ OAuth الحي؛ `repo_read` حي |
| **GitLab** | **لا** | — | — | — | كل شيء حي (PAT/OAuth) |
| **Render** | **لا** | — | — | — | كل شيء حي (api_key) |
| **Supabase** | **لا** | — | — | — | كل شيء حي (api_key/connection_string) |
| **OpenAPI العام** | **لا** (اختبار وحدة بمواصفة مزيفة فقط) | — | — | — | مواصفة OpenAPI حقيقية لمزود حقيقي |

الحد الصادق: «الموصلات المبدئية» خارج GitHub لم تلمس مزودًا حقيقيًا قط —
موثقة كفجوة ج-٥ بخطة.

---

## د) برهان «لا تُخرج سرًا أبدًا» — فحص آلي (كناري)

**الفحص:** `backend/tests/test_connector_audit_addendum.py::test_audit_canary_secret_never_in_any_output`

**الطريقة:** يولّد قيمة فريدة `SECRET_CANARY_<uuid4>` وقت التشغيل، يمررها عبر
كل مسارات النظام، ثم يتحقق آليًا من غيابها في كل المخرجات:

| المسار | المخرج المفحوص | النتيجة |
|---|---|---|
| الإعداد | رد `/connectors/system/setup` | نظيف |
| الحالة | رد `/state` + ملف `credentials.json` على القرص | نظيف |
| السجلات | رد `/logs` + ملف `call_log.jsonl` | نظيف |
| الكتالوج/المصفوفة | ردود `/catalog` و`/auth-types` | نظيف |
| صدى المزود | استثناء نقل يحوي السر → `str(exc)` المرفوع + سجل الاستدعاء (يجب أن يظهر `***`) | نظيف — التنقية `execution.py::_scrub` تعمل فعليًا |
| Webhook | رد 401 لرفض التوقيع + DLQ (بصمة الجسم فقط) | نظيف |
| سجل السياسة | `policy.audit_log()` | نظيف |
| الموضع الصحيح الوحيد | الخزينة (`vault.store`) | السر موجود هنا فقط — وهذا موضعه |

**أمر التشغيل والناتج:**
```
/home/user/workspace/venv312/bin/python -m pytest backend/tests/test_connector_audit_addendum.py -q
→ 6 passed, 1 skipped (operational)  [الكناري ضمن الستة]
```

**وجوده في CI:** نعم — داخل مجموعة الاختبارات الافتراضية (بلا علامة
operational)، يعمل في job **«Tests + Atomic Batch Gate»**
(`.github/workflows/ci.yml`) في كل تشغيل، بما في ذلك تشغيل هذا الالتزام
نفسه (انظر Actions للالتزام). **ليس فجوة.**

---

## هـ) برهان قاطع الدائرة

| البند | الدليل |
|---|---|
| ضد فشل حقيقي أم محاكاة؟ | **محاكاة** — نقل مزيف يعيد 500 (لا خدمة معطلة فعلًا) — موثق كحد، لا يخفى |
| سيناريو الفشل | 3 استدعاءات متتالية تفشل → `failures >= threshold(3)` → `opened_at` يُضبط |
| معايير الفتح/الإغلاق | `execution.py::CircuitBreaker` — عتبة 3 إخفاقات، تهدئة 60 ثانية، نصف مفتوح بعد التهدئة، نجاح واحد يصفّر (`failures=0, opened_at=None`) |
| الزمن حتى الفتح | بعد الفشل الثالث فورًا؛ الرفض بعده محلي (< 50 مللي ثانية، بلا نداء شبكة) |
| سلوك إعادة المحاولة | backoff أسّي `0.5 × 2^attempt` حتى `retry_max_attempts=3` — **غير مغطى باختبار** (فجوة ج-٧) |
| التعافي | **مختبر آليًا** — `test_audit_breaker_opens_then_recovers_after_cooldown`: فتح → رفض فوري → تقدم الساعة 61 ثانية → نجاح → تصفير فعلي. أُغلق بذلك ج-٧ السابقة (كان التعافي منفذًا بلا اختبار) |
| الدليل | الاختبار أعلاه (اسم الملف والحالة) — passed |

---

## و) برهان HMAC للـWebhooks

السيناريوهات الثلاثة المطلوبة، كلها مختبرة آليًا في
`test_acceptance_15_webhook_gateway_hmac_replay_dedup_dlq`:

| السيناريو | الحالة | الدليل |
|---|---|---|
| توقيع خاطئ فعلي | `sha256=` + 64 صفرًا → رفض (لا يقتصر على التوقيع الصحيح) | السطر 343–346 من الاختبار + `verify_hmac` بمقارنة ثابتة الزمن (`webhook_gateway.py:33`) |
| إعادة إرسال نفس الحدث (dedup) | نفس `event_id` → رفض بسبب `duplicate` | السطر 348–351 + `webhook_gateway.py:78–85` |
| نافذة زمنية منتهية (replay) | طابع زمني قبل 600 ثانية (النافذة 300) → رفض «خارج النافذة الزمنية» | السطر 353–357 + `webhook_gateway.py:67–69` |
| DLQ | المرفوضات تُسجل بسببها وبصمة جسمها (لا الجسم ولا السر) | السطر 358–359 + `webhook_gateway.py:90–99` |

حد صادق: كلها محاكاة وحدة على مستوى البوابة — لم تُختبر ضد مزود Webhook
حقيقي (ضمن فجوة ج-٥).

---

## ز) عزل أنواع المصادقة الخطرة (Implicit، Query Token، Cookies، ROPC)

| السؤال | الجواب | الدليل |
|---|---|---|
| معزولة بتحذير صريح في الواجهة؟ | نعم — علامة ⚠️ للمهجور في القوائم، تحذير كتلميح على الخيار، وصندوق تحذير في المعالج | `connectors-ui.js:147–148, 200, 250–251` + حارس `test_audit_ui_shows_warnings_for_risky_types` |
| ممنوعة افتراضيًا؟ | **نعم — رفض صلب لا مجرد تحذير**: `/setup` يرفض أي نوع `risk=deprecated` بـ 400 وسبب صريح «نوع مصادقة مهجور — مرفوض» — حتى لو سمحت سياسة المؤسسة | `api_routes.py:108–109` + حارس `test_audit_deprecated_auth_types_rejected_at_setup_api` (الأربعة كلها 400) |
| تحتاج تفعيلًا إداريًا؟ | **لا يوجد مسار تفعيل أصلًا** — العزل مزدوج: (1) لا موصل مسجل يعرض هذه الأنواع في `auth_types`؛ (2) حتى لو أعلنها موصل (سيناريو الاختبار الافتراضي `legacy_provider`) تُرفض | الاختبار نفسه (فرع `legacy_provider` يثبت الرفض حتى مع الإعلان) |
| ملاحظة على المواصفة الأصلية | المواصفة طلبت «إتاحة مع تحذير صريح»؛ التنفيذ **أشد** (حظر كامل). قاعدة الحسم في أمر المالك («لا تفترض صلاحية كاملة... الأقل صلاحية») تبرر التشدد — موثق كقرار لا كخطأ | D-054 |

الأنواع الأربعة الخطرة الأخرى (caution): مسموحة مع تحذير نصي إلزامي في
المعالج (اختبار المعيار 6 لـbasic يثبت النمط).

---

## ح) سياسة المؤسسة والموافقة الإدارية

**تعمل فعليًا — سيناريوهان على الأقل مع دليل تنفيذ:**

| السيناريو | الدليل |
|---|---|
| موصل محظور → الرفض | وحدة: `test_acceptance_24` (block → `PolicyDenied` عند check_setup) · تكامل API: `test_audit_policy_denied_returns_403_not_500` — رد 403 صريح بكلمة «محظور» (كان 500 — خلل أصلحه التدقيق) |
| موصل يتطلب موافقة → لا يعمل قبلها ويعمل بعدها | وحدة: `test_acceptance_24` (require_approval → `ApprovalRequired`؛ approve → اجتياز) · تكامل API: نفس اختبار الـ403 — قبل الموافقة 403 «موافقة»، وبعدها يجتاز السياسة (الرفض اللاحق 422 سببه فشل اختبار الاتصال بالنقل المزيف — أي السياسة لم تعد عائقًا) |
| حظر نوع مصادقة على مستوى المؤسسة | وحدة: `test_acceptance_24` (`allow_auth_types` → رفض basic خارج القائمة) |
| سجل تدقيق | `policy.audit_log()` — كل قرار مسجل (فحص الكناري يؤكد خلوه من الأسرار) |

---

## ط) بطاقة «يتطلب اتصالًا» للوكيل

| السؤال | الجواب | الدليل |
|---|---|---|
| تعمل في مسار الوكيل الحقيقي؟ | **على مستوى API: نعم** — `POST /connectors/system/execute` بلا اتصال يعيد **424** مع البطاقة كاملة (`type: requires_connection`، الموصل، النطاقات الناقصة، مسار الإعداد) | حارس `test_audit_execute_without_connection_returns_424_card` + `api_routes.py:293–296` |
| على مستوى حلقة الوكيل الداخلية | **جزئي** — `runtime_bridge.requirement_card/precheck` مختبران وحدويًا (S::`test_acceptance_23`)؛ لكن ربط حلقة المحادثة نفسها (عرض البطاقة تلقائيًا للوكيل في `/chat`) غير مربوط باختبار — فجوة ج-٨ |
| لقطة/سجل | رد الـ424 الفعلي في الاختبار: `detail.card.setup_path == "/connectors/system/catalog?connector=github"` و`needed_scopes` تحوي `repo:read` | الاختبار أعلاه |

---

## ي) الفجوات المعروفة (Known Gaps) — مرقمة بخطة وأولوية

| # | الوصف | الأثر | خطة المعالجة | الأولوية |
|---|---|---|---|---|
| ج-١ | `/oauth/start` يركّب ترويسات تفويض GitHub حرفيًا لأي موصل (`api_routes.py:179–184`) — موصل GitLab مثلًا سيولّد رابط تفويض GitHub | عالٍ | إضافة `oauth_urls` لعقد الموصل + اختبار لكل موصل OAuth | عالية |
| ج-٢ | `/oauth/callback` لا يبدّل الرمز ولا يخزن اعتمادًا (`api_routes.py:191–199`) — تدفق OAuth لا يكتمل عبر API أبدًا (المحرك مختبر وحدويًا فقط) | عالٍ | استدعاء `exchange_code` + إنشاء اعتماد في الـcallback + اختبار تكامل | عالية |
| ج-٣ | 8 أنواع documented_only ترجع مادة فارغة من `resolve` (ssh_key, app_password, connection_string, presigned_url, x509, jwt_signed, saml, kerberos) — مسجلة في الواجهة كأنها مدعومة | متوسط–عالٍ (فشل صامت عند الاستخدام) | إما تنفيذ الفروع أو وسمها `documented_only` في الكتالوج لتظهر صدقًا | عالية |
| ج-٤ | ربط placeholder: oauth1a يوقّع ضد URL وهمي، sts بلا توقيع SigV4 كامل، jwt_bearer_grant لا يُرسل عبر resolve | متوسط | ربط الدوال المُنفّذة بالفعل بالطلبات الفعلية + اختبارات | متوسطة |
| ج-٥ | التحقق الحي محصور في GitHub PAT (قراءة فقط) — لا كتابة حية، لا OAuth حي، لا GitLab/Render/Supabase/OpenAPI حي، لا Webhook من مزود حقيقي | متوسط | اختبارات operational لكل موصل بمفاتيح من البيئة (النمط موجود: GITHUB_TEST_PAT) | متوسطة |
| ج-٦ | mTLS: لا تحقق سلسلة CA ولا قائمة إبطال — شهادة موقعة ذاتيًا فقط | متوسط | تحقق سلسلة ضد CA للموصل + اختبار | متوسطة |
| ج-٧ | backoff/إعادة المحاولة الأسّية غير مغطاة باختبار (القاطع نفسه مغطى بفتح+تعافٍ) | منخفض | اختبار يعدّ محاولات النقل | منخفضة |
| ج-٨ | بطاقة الوكيل غير مربوطة بحلقة `/chat` الفعلية (مستوى API مغطى) | متوسط | ربط `precheck` بمسار الوكيل + اختبار تكامل | متوسطة |
| ج-٩ | حالة dedup للبوابة وDLQ في الذاكرة فقط — إعادة التشغيل تفقدهما (نافذة الإعادة 300 ثانية تبقى حامية) | منخفض | استمرارية على القرص (نمط atomic_json القائم) | منخفضة |
| ج-١٠ | توكنات المالك الثلاثة كُشفت نصًا في محادثة الاستلام | عالٍ (خارج الكود) | **تدويرها/سحبها على المالك** — موثق في CONNECTOR_RISK_REPORT.md خطر #1 | عالية (يدوي) |

**ما أُغلق بهذا التدقيق:** فجوة التعافي للقاطع (ج-٧ جزئيًا — التعافي مختبر،
backoff باقٍ)، فجوة الكناري (لا وجود لها الآن — آلي وداخل CI)، فجوة اختبار
API للسياسة/البطاقة/الأنواع المهجورة (مغطاة باختبارات تكامل).

---

## معايير قبول الملحق نفسه — فحص ذاتي

| المعيار | الحالة |
|---|---|
| 1. مصفوفة الأنواع كاملة بلا دمج | ✅ — 34 صفًا (صُحح الادعاء من 30) |
| 2. مصفوفة الـ24 مع نوع المصادقة لكل معيار | ✅ — القسم ب |
| 3. دليل حي أو تصريح بغيابه لكل موصل | ✅ — القسم ج (GitHub: حي عبر المنفذ؛ الأربعة: تصريح صريح) |
| 4. برهان آلي لعدم التسريب | ✅ — الكناري (القسم د) داخل CI |
| 5. برهان القاطع وHMAC على سيناريوهات فشل | ✅ — القسمان هـ/و (مع تصريح أنها محاكاة لا خدمة معطلة حقيقية) |
| 6. عزل الأنواع الخطرة وسلوكها الافتراضي | ✅ — القسم ز (حظر صلب مزدوج) |
| 7. فجوات مرقمة بخطة | ✅ — القسم ي (10 فجوات) |
| 8. كل yes بمرجع وكل no بسبب وخطة | ✅ — كل خلية تحمل مرجعًا أو سببًا |
| 9. لا تعديل main إلا لإصلاح خلل حقيقي عبر الحوكمة | ✅ — ثلاثة إصلاحات فقط (ت-٤ والـ403 والتنقية)، كلها بخلل كشفه التدقيق واختبار حارس، عبر مسار work-branch → CI → main |

## حكم التدقيق النهائي

النظام **مُنفّذ ومُختبر آليًا على نطاق واسع** (24 اختبار قبول + 7 اختبارات
تدقيق)، مع **برهان حي واحد عبر المنفذ** (GitHub PAT، قراءة فقط)، و**برهان
عدم تسريب آلي داخل CI**. الادعاءات غير الدقيقة في التقرير السابق صُححت
(العدد 34 لا 30؛ الاختبار الحي القديم لم يكن يمر عبر النظام؛ معيار 5 بلا
اختبار مخصص). أخطر فجوتين تبقيان: اكتمال تدفق OAuth عبر API (ج-٢) وروابط
التفويض المثبتة على GitHub (ج-١) — كلتاهما موثوفتان بخطة وأولوية عالية،
ولا يخفيهما هذا الملحق.
