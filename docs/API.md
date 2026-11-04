# API.md — الواجهات البرمجية

> كل نقاط API في النواة، كما رُصدت في مسح M0 + تحديث M6 (R-608).
> آخر تحديث: 2026-11-04 (R-841 — نقاط `/orchestrator/*` الستة عشر)
> **توثيق حي**: Swagger على `/docs`، ReDoc على `/redoc`، OpenAPI على `/openapi.json` (45 مساراً).

> **حد معلن (R-714):** أجسام الطلبات المضغوطة غير مدعومة — لا يوجد فك ضغط للطلبات. طلب مضغوط فعليًا (اختُبر gzip وdeflate) يُرفض بـ400 (رسالة عامة من محلل الجسم)؛ رأس ترميز غير معروف يُتجاهل وتُفحص البايتات الخام. الموجود ضغط **استجابات** فقط (GZipMiddleware، مستوى 6 — R-502). فك ضغط الطلبات لم يُنفّذ في هذه الجولة — يتطلب تصميمًا أمنيًا واختبارات قبل إضافته (قنابل فك الضغط، حدود حجم قبل المصادقة/تقييد المعدل، ترميزات متسلسلة).

---

## 1) النواة (backend/app.py) — 45 مساراً

### عام
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/` | الواجهة (HTML عربي RTL) | لا |
| GET | `/health` | فحص الصحة (23 مكوّناً) | لا |
| GET | `/status` | حالة النظام | لا |
| GET | `/api-key` | بصمة مفتاح API (لا يُكشف المفتاح) | رأس `X-API-Key` (جولة المجلس <1> — صيغة الاستعلام أُزيلت) |

### محادثة
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/chat` | محادثة؛ حد 30 طلباً/دقيقة لكل IP افتراضياً + فحص طبقة الأمان | لا؛ حد معدل |
| GET | `/` | واجهة المحادثة (R-786 — `frontend/chat/index.html`) | لا |
| GET | `/console` | لوحة SOVRA التقنية القديمة (كانت على `/` قبل R-786) | لا |
| WS | `/ws/{user_id}` | محادثة WebSocket (مع فحص طبقة الأمان) — العقد أدناه (R-715) | لا |

**عقد `/ws/{user_id}` (R-715):**

| الإطار الوارد | الرد | دورة منسّق؟ |
|---|---|---|
| `{"type":"chat_message","payload":{"text":"…"}}` | `{"type":"chat_reply","message":"…","payload":{"text":"…"},"cycle_id":"…"}` — نفس محرك ردود `/chat` | نعم |
| `{"text":"…"}` (الصيغة القديمة) | `{"type":"reply","message":"…","cycle_id":"…"}` | نعم |
| `{"type":"ping"}` / `heartbeat` | `{"type":"pong"}` | لا |
| `{"type":"sovereign_command",…}` | `{"type":"error"}` — استخدم `POST /sovereign/command` مع المفتاح | لا |
| أي `type` آخر (`hello`، `run_cycle`…) | `{"type":"system","event":"ignored"}` | لا |
| نص فارغ / JSON ليس كائنًا | `{"type":"error"}` | لا |

نص المحادثة (بأي صيغة) يمر بطبقة الأمان قبل المنسّق؛ المحجوب يُرد بـ`blocked: true` و`cycle_id: "safety-block"`.

### أوامر السيد (تتطلب api_key في body)
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/sovereign/command` | أمر سيادي (فحص أمان حتى للسيد) | api_key |
| POST | `/sovereign/reset` | إعادة تعيين (فحص أمان) | api_key |

### أخرى
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/orchestrator/cycle` | تشغيل دورة | `api_key` في الجسم |
| GET | `/components/consciousness` | حالة الوعي | لا |
| GET | `/components/memory` | حالة الذاكرة | لا |
| GET | `/components/predictive` | حالة التنبؤ | لا |
| GET | `/components/simulation` | حالة المحاكاة | لا |
| GET | `/components/sovereign` | حالة السيادة | لا |
| GET | `/components/quantum` | حالة الكم | لا |
| GET | `/components/nexus` | حالة NexusCore المدمجة (R-301) | لا |
| GET | `/components/defense` | حالة الدفاع | لا |

### طبقة الأمان (R-608)
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/security/status` | حالة SafetyGuard (نشط/قوائم/سجل) | لا |
| GET | `/security/log` | آخر أحداث سجل الأمان (limit 1-500) | لا |

### NexusCore REST API (R-608)
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/nexus/status` | حالة محرك NexusCore | لا |
| POST | `/nexus/analyze/text` | تحليل نص (مشاعر/نية/لغة) | لا |
| POST | `/nexus/ingest` | إدخال بيانات عبر DataCollector | لا |
| GET | `/nexus/health` | صحة NexusCore | لا |
| POST | `/nexus/budget/analyze` | تحليل ميزانية (قائمة) | لا |
| GET | `/nexus/recommendations` | توصيات | لا |

---

## 2) واجهة /api/* (backend/api.py) — 11 مساراً

| الطريقة | المسار | الوصف |
|---|---|---|
| GET | `/api/health` | صحة (version 3.0.0) |
| POST | `/api/run` | تشغيل دورة |
| POST | `/api/reset` | إعادة تعيين |
| GET | `/api/state` | الحالة |
| GET | `/api/history` | التاريخ |
| POST | `/api/event` | حدث |
| GET | `/api/components` | المكوّنات |
| GET | `/api/connections` | الاتصالات |
| GET | `/api/mode` | الوضع |
| POST | `/api/mode/{mode}` | تعيين الوضع |
| WS | `/api/ws` | WebSocket (مع فحص طبقة الأمان) |

---

## 3) نماذج الطلبات/الاستجابات

### POST /chat
```json
// طلب
{"text": "مرحباً", "user_id": "user1", "session_id": "abc"}
// R-786: سياق اختياري — حتى 20 دورًا، role ∈ {user, assistant}، content ≤ 4000؛
// أدوار المستخدم تمر بطبقة الأمان وما يُرفض يسقط؛ دور آخر ⇒ 422
{"text": "وما عاصمتها؟", "history": [{"role": "user", "content": "حدثني عن السعودية"}, {"role": "assistant", "content": "..."}]}
// استجابة عادية
{"reply": "تم تنفيذ القرار: monitor", "status": "ok", "cycle_id": "...", "processing_time_ms": 12.3, "timestamp": 1234.5}
// استجابة محجوبة (طبقة الأمان)
{"reply": "هذا الأمر محظور...", "status": "blocked", "cycle_id": "safety-block", ...}
```

### POST /sovereign/command
```json
// طلب (يتطلب api_key)
{"api_key": "...", "command": "get_status"}
```

### POST /orchestrator/cycle
```json
// استجابة
{"cycle_id": "...", "success": true, "duration": 0.22, "decision": {"action": "monitor", "confidence": 0.6, ...}}
```

### POST /nexus/analyze/text
```json
// طلب
{"text": "نص للتحليل"}
// استجابة
{"sentiment": {...}, "intent": {...}, "language": {...}}
```

### GET /security/status
```json
// استجابة
{"safety_guard": {"active": true, "forbidden_absolute": 6, "dangerous_patterns": [...], ...}, "rate_limiter": {...}, "nexus_api": {...}}
```

---

## 4) ملاحظات أمنية (راجع RISKS.md)

- `GET /api-key` يتطلب رأس `X-API-Key` (R-106 — وصيغة الاستعلام `master_key` أُزيلت في جولة المجلس <1> لأنها تُسجّل في سجلات الوصول).
- `POST /orchestrator/cycle` يتطلب `api_key` (R-108).
- `POST /chat` لا يتطلب تسجيل دخول؛ يطبق حداً انزلاقياً per-IP (30/60 ثانية افتراضياً)، ويرد بـ 429 و`Retry-After` عند التجاوز (R-603).
- محدد `/chat` في الذاكرة داخل كل عملية؛ ليس حداً موزعاً بين workers أو الخوادم.
- **طبقة الأمان (R-608)**: كل مدخلات `/chat` وWebSocket و`/sovereign/*` تُفحص عبر `SafetyGuard` — الأوامر الممنوعة تماماً (تدمير ذاتي، مسح ذاكرة...) تُحجب حتى للسيد.
- راجع `CORS_ORIGINS` في `SECURITY.md` قبل النشر.

---

## 6) نظام الموصلات الموحد (backend/connector_system/api_routes.py) — 16 مساراً (R-840)

بادئة كل المسارات: `/connectors/system`. العقد الكامل في `docs/CONNECTOR_SYSTEM.md`.

| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/connectors/system/catalog` | كتالوج الموصلات المسجلة + أنواع المصادقة المدعومة لكل موصل | لا |
| GET | `/connectors/system/auth-types` | أنواع المصادقة الـ30 مع تصنيف الخطر وحقول المعالج | لا |
| GET | `/connectors/system/state` | حالة كل موصل: مربوط/لا، النطاقات، آخر تدوير | لا |
| GET | `/connectors/system/logs` | سجل الأحداث (بلا أسرار — السر لا يُسجَّل أبدًا) | لا |
| POST | `/connectors/system/setup` | ربط اعتماد جديد (PAT/API key/JWT/Service Account/mTLS…) | لا |
| POST | `/connectors/system/oauth/start` | بدء تدفق OAuth — يُرفض بلا PKCE (إلزامي) | لا |
| GET | `/connectors/system/oauth/callback` | استقبال رمز التفويض وتبديله | لا |
| POST | `/connectors/system/test` | اختبار موصل مربوط | لا |
| POST | `/connectors/system/rotate` | تدوير سر اعتماد | لا |
| POST | `/connectors/system/revoke` | سحب اعتماد وإيقاف الموصل | لا |
| POST | `/connectors/system/update-scopes` | تحديث النطاقات المطلوبة | لا |
| POST | `/connectors/system/execute` | تنفيذ عملية عبر موصل (سياسة + قاطع دائرة + Idempotency-Key) | لا |
| GET | `/connectors/system/agent-card` | بطاقة «يتطلب اتصالًا» للوكيل (عقد موحد) | لا |
| GET | `/connectors/system/policy` | سياسة المؤسسة الحالية | لا |
| POST | `/connectors/system/policy` | تحديث سياسة المؤسسة (حصار أنواع خطرة، require_approval، all_allow) | لا |
| POST | `/connectors/system/webhooks/{connector_id}` | بوابة Webhook: تحقق HMAC-SHA256 + إزالة تكرار | توقيع HMAC |

ملاحظة أمنية: خزينة الاعتمادات تُخرج المفاتيح فقط — أي سر يُرفض رجوعه في أي
استجابة أو سجل (محمي باختبار `test_no_secrets_in_logs`).

## 7) طبقة تنسيق الوكلاء (backend/agent_orchestrator/api_routes.py) — 17 مساراً (R-841 + R-842)

بادئة كل المسارات: `/orchestrator`. العقد الكامل في `docs/ORCHESTRATOR.md`.
القراءات مفتوحة؛ **كل نقطة تغيير تتطلب `api_key`** (بوابة مفتاح المالك — 401).

| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/orchestrator/health` | نبض الطبقة (جاهزية المنفذ/السجل) | لا |
| GET | `/orchestrator/tools` | سجل الأدوات بعقدها (وصف/خطورة/مخطط) | لا |
| GET | `/orchestrator/schemas` | مخططات العقود 5.1–5.5 | لا |
| GET | `/orchestrator/ui` | واجهة الطبقة (HTML) | لا |
| POST | `/orchestrator/loops` | استقبال طلب وقيادة الحلقة (`dry_run` اختياري) | `api_key` |
| GET | `/orchestrator/loops` | قائمة الحلقات | لا |
| GET | `/orchestrator/loops/{id}` | حالة حلقة (خطة/نتائج/رد) | لا |
| GET | `/orchestrator/loops/{id}/trace` | الأثر الكامل (spans/قرارات) | لا |
| POST | `/orchestrator/loops/{id}/cancel` | إلغاء فوري موثق (ما تم/ما لم يتم) | `api_key` |
| POST | `/orchestrator/loops/{id}/pause` | إيقاف بشري | `api_key` |
| POST | `/orchestrator/loops/{id}/resume` | استئناف من الـcheckpoint | `api_key` |
| POST | `/orchestrator/loops/{id}/plan` | تعديل الخطة بتدخل بشري | `api_key` |
| POST | `/orchestrator/loops/{id}/rollback` | تراجع/تعويض عن خطوة | `api_key` |
| GET | `/orchestrator/approvals/pending` | الموافقات المعلقة | لا |
| POST | `/orchestrator/approvals` | حسم موافقة ثم استئناف الحلقة | `api_key` |
| GET | `/orchestrator/planner/eval?set=dev\|holdout&mode=keyword\|semantic` | **R-842:** تقييم اختيار الأدوات على مجموعة مرجعية (دقة/فئات/امتناع/إخفاقات) — قراءة فقط، لا تنفيذ | لا |
| POST | `/orchestrator/planner/eval` | **R-842:** التقييم نفسه مع `mode=brain` (العقل الحي — مكلف) `{set, mode, api_key}` | `api_key` |

ملاحظة أمنية: الأثر (trace) يُنقّى من أي مفتاح سرّي قبل التسجيل (كناري آلي
في CI — `test_a26_no_secret_leak_canary`).

## 7ب) التقييم المستقل (backend/evaluation/api_routes.py) — 3 مسارات + 1 (R-843)

| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/evaluation/suites` | المجموعات المجمّدة (معرّف/بيانات/بصمة/أرضية) + حالة الحَكَم واستقلاله | لا |
| GET | `/evaluation/latest` | آخر تقرير تقييم محفوظ (`report: null` إن لم يوجد) | لا |
| POST | `/evaluation/run` | تشغيل `{suites?: [...], api_key}` وحفظ التقرير ذريًا؛ معرّف مجهول ⇒ 422 | `api_key` |
| POST | `/skills/evaluate_independent` | تقييم مستقل لمهارة `{name, version, cases, actor?, api_key}` — شرط `approve` (٦.٥.٢) | `api_key` |

## 7ج) الطابور غير المتزامن (backend/job_queue/api_routes.py) — 7 مسارات (R-844)

| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/queue/kinds` | أنواع المهام بوصفها وخطرها ومخططها | لا |
| GET | `/queue/stats` | العدد حسب الحالة، والعمق، والحد، والعمال | لا |
| POST | `/queue/jobs` | `{kind, payload, priority?}` + ترويسة `Idempotency-Key`. 202 جديد، 200 مكرر (`deduplicated`)، 401، 409 تعارض، 422، 428 بلا مفتاح، 429 ممتلئ + `Retry-After` | `X-API-Key` |
| GET | `/queue/jobs` | قائمة (`status?`، `limit?`) | `X-API-Key` |
| GET | `/queue/jobs/{id}` | المهمة وأحداثها، 404 إن لم توجد | `X-API-Key` |
| POST | `/queue/jobs/{id}/cancel` | إلغاء (فوري إن كانت `queued`، مطلوب وتُلغى الحلقة إن كانت `running`) | `X-API-Key` |
| POST | `/queue/drain` | تصريف يدوي `{max_jobs?}` بسقف 50 | `X-API-Key` |

## 7د) الإشعارات (backend/notifications/api_routes.py) — 7 مسارات (R-845)

| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/notifications/channels` | حالة القنوات وسببها وحدها الأدنى وتعطيلها، بلا روابط أو أسرار | لا |
| GET | `/notifications/stats` | الإشعارات وغير المقروء والتسليمات حسب الحالة والموزع | لا |
| GET | `/notifications` | الصندوق الداخلي (`unread_only?`، `limit?`) مع التسليمات | `X-API-Key` |
| POST | `/notifications/test` | إشعار تجريبي + `Idempotency-Key`. 202 جديد، 200 مكرر، 428 بلا مفتاح | `X-API-Key` |
| POST | `/notifications/dispatch` | تصريف يدوي `{max_items?}` بسقف 50 | `X-API-Key` |
| POST | `/notifications/{id}/read` | تعليم مقروء، 404 إن لم يوجد | `X-API-Key` |
| POST | `/notifications/channels/{name}/enable` | رفع تعطيل المصادقة بعد إصلاح الإعداد | `X-API-Key` |

## 8) سجل التحديثات

| التاريخ | التغيير | الدفعة |
|---|---|---|
| 2026-10-12 | توثيق نقاط API من مسح M0 | M0 |
| 2026-10-13 | R-603: توثيق تقييد معدل `/chat` وحالة المصادقة الفعلية | M6 |
| 2026-10-14 | R-608: توثيق نقاط `/nexus/*` و`/security/*` وفحص طبقة الأمان | M6 |
| 2026-11-03 | R-840: توثيق نقاط `/connectors/system/*` الستة عشر (نظام الموصلات الموحد) | R-840 |
| 2026-11-04 | R-843: نقاط `/evaluation/*` و`/skills/evaluate_independent` | R-843 |
| 2026-11-04 | R-844: نقاط `/queue/*` السبع (الطابور غير المتزامن) | R-844 |
| 2026-11-04 | R-845: نقاط `/notifications/*` السبع (الإشعارات) | R-845 |
