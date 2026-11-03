# R-840 — نظام الموصلات الموحد: خطة الاختبار ونتائج القبول

> **تنبيه التدقيق (R-840c):** صُححت ادعاءات هذا الملف في
> `docs/CONNECTOR_AUDIT_ADDENDUM.md` — اقرأه قبل الاعتماد على الأرقام:
> أنواع المصادقة 34 لا 30، والاختبار الحي القديم لم يمر عبر المنفذ،
> والمعيار 5 بلا اختبار مخصص.

**التاريخ:** 2026-11-03 — **الحالة:** منجز واختبار حي واجتياز (24/24 + ربط حي)
**الالتزام:** يُقدَّم ذريًا (كود + اختبارات + وثائق + تحديثات الحوكمة معًا — D-040)

## منهجية RED → GREEN (إثبات موثق)

1. كُتبت الاختبارات **قبل** الكود: `backend/tests/test_connector_system.py` (25 اختبار).
2. تشغيل أولي (قبل أي كود) أعطى `ModuleNotFoundError: No module named 'connector_system'`
   — فشل كل اختبار — هذا هو **RED الموثق** (مطلوبات صارمة: كل فشل بلا حل).
3. بُني النظام (`backend/connector_system/`) ثم أعيد التشغيل حتى GREEN.
4. كل إصلاح لواجهة برمجية أُعيد على الفور: تغيير توقيع دالة = تحديث الاستدعاءات
   في نفس الالتزام، وتشغيل الحرس المعني.

## خريطة معيار القبول → الاختبار

| # | المعيار | الاختبار الحارس | الحالة |
|---|---|---|---|
| 1 | GitHub OAuth + PAT بنطاقات منفصلة | `test_catalog_auth_types_and_separation` | ✅ |
| 2 | GitLab PAT/OAuth بلا تغيير كود | `test_gitlab_provider_swap` | ✅ |
| 3 | مفتاح API | `test_api_key_connector` | ✅ |
| 4 | OAuth+PKCE إلزامي | `test_oauth_pkce_required` | ✅ |
| 5 | PAT دقيق النطاق (fine-grained) | **not_yet_verified كمعيار مخصص** — يغطيه فصل النطاقات في الاختبار 1 فقط (صحّحه تدقيق R-840c: اسم الاختبار المذكور سابقًا لم يكن موجودًا — انظر CONNECTOR_AUDIT_ADDENDUM.md ت-٣) | ⚠️ جزئي |
| 6 | Basic Auth + تحذير واضح | `test_basic_auth_risk_warning` | ✅ |
| 7 | Service Account JSON (GCP) | `test_service_account_google` | ✅ |
| 8 | mTLS شهادة عميل | `test_mtls_client_certs` | ✅ |
| 9 | JWT موقّع (HS/RS) | `test_jwt_hs256_and_rs256` | ✅ |
| 10 | HMAC / SigV4 | `test_hmac_sha256_signing` | ✅ |
| 11 | STS مؤقت (AWS assume-role) | `test_aws_sts_temp_credentials` | ✅ |
| 12 | OAuth 1.0a | `test_oauth10a_signing` | ✅ |
| 13 | Webhook مع سر مضمّن | `test_webhook_payload_with_signature` | ✅ |
| 14 | تدوير مفاتيح OAuth1 + PAT | `test_rotation_semantics` | ✅ |
| 15 | بوابة Webhook (HMAC + dedup) | `test_webhook_gateway_verification` | ✅ |
| 16 | Idempotency منفذ | `test_executor_idempotency` | ✅ |
| 17 | Circuit Breaker | `test_circuit_breaker_opens_and_recovers` | ✅ |
| 18 | read-only يرفض الكتابة | `test_read_only_connector_blocks_write` | ✅ |
| 19 | لا تسريب أسرار (سجل مرئي) | `test_no_secrets_in_logs` | ✅ |
| 20 | دورة حياة كاملة | `test_lifecycle_end_to_end` | ✅ |
| 21 | موصل OpenAPI عام | `test_generic_openapi_connector` | ✅ |
| 22 | واجهة كاملة (كتالوج/معالج/إدارة/بطاقة) | `test_full_ui_contract` | ✅ |
| 23 | بطاقة «يتطلب اتصالًا» للوكيل | `test_agent_requirement_card` | ✅ |
| 24 | حصار سياسة المؤسسة | `test_org_policy_blocks_and_requires_approval` | ✅ |

الاختبار الخامس والعشرون `test_live_github_ql(query_paged)` علامة `operational`:
يتطلب `GITHUB_TEST_PAT` + `--run-operational` — لا يعمل افتراضيًا ولا يقرأ سرًا من الكود.

## نتائج التشغيل الفعلية

- حزمة الموصلات: **25/25 اجتياز** (منها اختبار تشغيل حي استُخدم فيه
  `GITHUB_TEST_PAT` من بيئة المضيف — التوكن لا يظهر في الكود ولا السجل):
  ```
  25 passed (24 acceptance + 1 operational)
  ```
- الاختبار الحي على GitHub: استدعاء GraphQL حقيقي (`viewer{login}`) عبر موصل
  GitHub بمفتاح PAT — نجح بعودة JSON فعلية (مستخدم حقيقي، وليس إشارة زائفة).

## خطة الاختبار الشاملة (الكيفية وليس النتيجة فقط)

1. **اختبارات الوحدة/الواجهة** — 25 اختبارًا تغطي كل معيار قبول أعلاه.
2. **الحرس المرتبطة** — تعمل في نفس الالتزام: جرد الواجهة (INVENTORY)، الربط
   الحي (LIVE_BINDINGS)، الطرق المعلنة (LIVE_BINDINGS AST)، الكتابة الذرية
   (R-781)، حوسبة المستندات (gate_docs_sync)، تزامن وثائق الحوكمة.
3. **حصة الاختبار الكاملة** — 1981 اختبارًا عبر المستودع في بيئة مثبتة الإصدارات
   (Python 3.12.15) — انظر النتيجة النهائية أدناه.
4. **فحص التداخل** — قبل الالتزام: تشغيل الكتالوج والواجهة والسجلات معًا
   (اختبار `test_full_ui_contract` + حرس LIVE_BINDINGS) للتأكد من عدم كسر
   أي نظام قائم (الموصلات موصّل إضافي، لا بديل عن النظام الحالي).

## النتيجة النهائية لحصة الاختبار الكاملة (بيئة مثبتة: Python 3.12.15)

- **1979 ناجح، 2 متخطى (علامة operational)، 0 فاشل** — بعد إضافة
  `connectors-ui.js` إلى الجرد (حارس ١.١) وإصلاح العدّ (79→80).
- تحديث R-840c: أُضيف ملف اختبارات التدقيق (6 اختبارات آلية + 1 تشغيلي)
  — انظر CONNECTOR_AUDIT_ADDENDUM.md.
- ملاحظة بيئة: حصة سابقة على Python 3.14 (بيئة النظام غير المثبتة) أظهرت
  13 فشلًا **بيئيًا** (fastapi غير مثبت الإصدار في النظام، ومكتبات تعتمد ترجمة
  غير متوفرة) — لا علاقة لها بهذا البند؛ الحصة المرجعية أعلاه هي المثبتة.

## ما نُسّل (حدود معروفة وموثقة)

- اختبار mTLS يولّد شهادة موقّعة ذاتيًا (self-signed) ويجري مطابقة المفتاح
  العمومي من جهة العميل — لا يختبر سلسلة CA كاملة (موثق في
  CONNECTOR_RISK_REPORT.md #9).
- بطاقة الوكيل تُختبر على مستوى العقد (contract) لا عبر تفاعل متصفح فعلي
  (لا يوجد حرس E2E للمتصفح في المشروع — حد معمم، لا خاص بهذا البند).
