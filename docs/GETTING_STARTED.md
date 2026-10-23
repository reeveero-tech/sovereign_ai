# دليل التجربة — تشغيل الذكاء السيادي محليًا خطوة بخطوة

> أُنشئ في GS-1 (2026-10-20) بأمر المالك. **كل خطوة هنا مُجرّبة فعليًا** على استنساخ نظيف
> لـ `main` عند `a4a80bb` (Linux، Python 3.11.15) — النتائج المكتوبة هي المخرجات الحقيقية لا المتوقعة.
> ما لم يُجرَّب موسوم صراحة بـ «لم يُجرَّب».

---

## ١) المتطلبات

| المتطلب | الملاحظة |
|---|---|
| **Python 3.11.x** | إلزامي — `verify.sh` يرفض أي إصدار آخر (بوابة R-682). تحقق: `python3.11 --version` |
| pip | يأتي مع Python |
| git | للاستنساخ |
| طرفية (Terminal) | طرفيتان للتجربة الكاملة (الخادم + الحارس) |
| curl | لاختبار نقاط النهاية |

**لا يلزم:** Docker، ولا قاعدة بيانات، ولا أي خدمة خارجية، ولا مفتاح API للتجربة الأساسية.

> **تنبيه بيئي:** `.replit` يعلن `python-3.12` بينما المشروع يقبل 3.11 فقط — تعارض معروف (قرار مالك، انظر
> `docs/OWNER_DECISIONS_PENDING.md`). للتجربة المحلية استخدم 3.11.

---

## ٢) التثبيت

```bash
git clone https://github.com/reeveero-tech/sovereign_ai.git
cd sovereign_ai

# البيئة الافتراضية خارج شجرة المستودع (مهم — انظر الملاحظة)
python3.11 -m venv ~/.venvs/sovereign
source ~/.venvs/sovereign/bin/activate        # Windows: %USERPROFILE%\.venvs\sovereign\Scripts\activate

python --version                               # يجب أن يطبع Python 3.11.x
pip install -r requirements.txt
```

**النتيجة الفعلية:** التثبيت اكتمل في ~14 ثانية برمز خروج 0.

> **لماذا البيئة خارج الشجرة؟** بعض المكونات (مؤشر «لا mocks» في `/sovereignty/score`، وخريطة الوعي
> في الحارس) تمسح شجرة المستودع كاملة. بيئة `.venv` داخل الشجرة ثبت أنها علّقت الحزمة أكثر من 10 دقائق
> (بند ٤ من التدقيق الشامل). ضعها خارجها.
>
> Windows: الأوامر أعلاه مُجرّبة على Linux فقط — **لم تُجرَّب على Windows**.

---

## ٣) الإقلاع

من جذر المستودع، والبيئة مفعّلة:

```bash
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

البديل المكافئ (نقطة دخول Replit): `bash start.sh` من جذر المستودع — **لكنه يربط على `0.0.0.0`**، أي يفتح
المنفذ لكل الشبكة المحلية. للتجربة على جهازك فقط استخدم الأمر أعلاه (`127.0.0.1`).

**أوامر لا تعمل (مُجرّبة):**

| الأمر | النتيجة |
|---|---|
| `python -m backend.app` (من الجذر) | `ModuleNotFoundError: No module named 'orchestrator'` |
| `uvicorn backend.app:app` (من الجذر) | الخطأ نفسه |

السبب: `backend/app.py` يستورد وحداته بأسماء مطلقة (`from orchestrator import …`)، فيجب التشغيل من داخل `backend/`.

**ماذا يظهر عند النجاح** (بعد ~20 ثانية — تحميل المكونات):

```
INFO:     Started server process [...]
...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

تظهر قبلها مئات أسطر التحميل، وتحذيرات متوقعة لا تعني فشلًا، منها:

- `⚠️ CORS مفتوح للجميع — مقبول في التطوير فقط (D-034)` — طبيعي في التطوير.
- `R-635: no active signing key — ledger write refused` — طبيعي في استنساخ جديد (انظر §٥).

---

## ٤) اختبار سريع

افتح طرفية ثانية (الخادم يبقى يعمل في الأولى).

### `GET /health`

```bash
curl -s http://127.0.0.1:8000/health
```

**الفعلي:** HTTP 200 — `"status": "healthy"`, `"version": "4.0.0"`، ومعه `uptime_seconds` وحالة كل مكوّن.

### `GET /status`

```bash
curl -s http://127.0.0.1:8000/status
```

**الفعلي:** HTTP 200 — `"status": "operational"`، مع حالة المنسّق والمكونات.

### `GET /supervisor/status`

```bash
curl -s -w "\nHTTP %{http_code}\n" http://127.0.0.1:8000/supervisor/status
```

**الفعلي قبل تشغيل الحارس:** HTTP **503** — `{"supervisor":"down","reason":"invalid"}`.
هذا **صحيح ومقصود**: لا يوجد ملف نبض للحارس بعد، والقيمة غير الصالحة لا تمنح حالة صحية. يصبح 200 في §٦.

### `GET /ledger/verify`

```bash
curl -s http://127.0.0.1:8000/ledger/verify
```

**الفعلي:** HTTP 200 — في استنساخ جديد: `anchored_coverage_pct: 0.0` و`total_events: 0`، والمراسي
المتتبعة في git (6) تظهر فاشلة التحقق. **هذا متوقع**: المراسي توقّع أحداثًا من سجل المالك الحي
(`ledger.jsonl`)، وهذا السجل غير متتبع في git فلا يوجد في الاستنساخ.

### `POST /chat`

```bash
curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"text":"مرحبا، من أنت؟"}'
```

**الفعلي (بلا Ollama):** HTTP 200 —

```json
{"reply":"أهلاً بك. أنا الذكاء السيادي — جاهز لخدمتك. لدي 0 تنبؤاً نشطاً بدقة 50.0%.","status":"ok","cycle_id":"...","processing_time_ms":17.65,...}
```

الرد من **المحرك القالبي** (يبني الرد من حالة النظام الحية — R-614). رسائل أخرى قد تعيد
`"تم تنفيذ القرار: monitor."`.

### نقطة إضافية مفيدة: `GET /guardian/status`

**الفعلي:** HTTP 200، ويظهر `"system_locked": true` و`"ai_frozen": true` — لأن الملفين
`guardian/data/emergency/SYSTEM_LOCKED.lock` و`AI_FROZEN.flag` متتبعان في git. **هما علامتان تشخيصيتان فقط**
— لا يرفض أي مسار الطلبات بسببهما (لذلك `/chat` يعمل). جعلهما ضابطًا فعليًا قرار مالك (بند ٣، س-٣).

---

## ٥) رؤية السجلات تنمو

### السجل السيادي `data/sovereign_core/ledger.jsonl` — **لن ينمو في استنساخ جديد**

```bash
wc -l data/sovereign_core/ledger.jsonl
# الفعلي: No such file or directory — حتى بعد رسائل /chat
```

السبب (مثبت من سجل الخادم): `R-635: no active signing key — ledger write refused (fail-closed)`.
السجل يرفض الكتابة بلا مفتاح توقيع نشط في حلقة المفاتيح — **رفض مغلق مقصود**: لا حدث غير موقّع أبدًا.
إنشاء مفتاح توقيع محلي يمس قرار المالك في إدارة المفاتيح (بند ٢ و٨) — **لم يُنفَّذ في هذا الدليل**.
على خادمك الذي يملك حلقة مفاتيح نشطة، الأمر نفسه (`wc -l`) يعرض النمو بعد كل دورة.

### ما ينمو فعلًا في الاستنساخ (مُقاس)

```bash
wc -l backend/nexus_data/audit/audit_*.jsonl data/sovereign_core/compat_call_log.jsonl
# أرسل 3 رسائل /chat ثم أعد الأمر
```

**الفعلي:** بعد 3 رسائل: سجل التدقيق `audit_*.jsonl` من 2 → 5، و`compat_call_log.jsonl` من 4 → 7
(+1 لكل رسالة في كليهما). وعند تشغيل الحارس (§٦) ينمو `data/supervisor/monitor_log.jsonl` سطرًا كل دورة.

> هذه الملفات مستثناة من git أو غير متتبعة — لا تلتزمها.

---

## ٦) رؤية الحارس (المراقب `supervisor_daemon`)

الحارس عملية **منفصلة** تراقب `/health` دوريًا وتكتب ملف نبض يقرؤه `/supervisor/status`.
التشغيل هنا **يدوي ومحلي فقط** — ليس تفعيلًا للحارس كخدمة (ذلك قرار مالك، §٨).

### التشغيل

في طرفية ثالثة، من **جذر** المستودع والبيئة مفعّلة:

```bash
python -m backend.supervisor_daemon --interval 2
```

```bash
curl -s -w "\nHTTP %{http_code}\n" http://127.0.0.1:8000/supervisor/status
```

**الفعلي:** HTTP 200 — `{"supervisor":"up","last_heartbeat":"...","active_alerts":0}`.

### الإيقاف — ماذا يحدث

اضغط `Ctrl+C` في طرفية الحارس (**الفعلي:** خروج نظيف برمز 0).

| الوقت بعد الإيقاف | `/supervisor/status` |
|---|---|
| فورًا (ثانيتان) | ما زال `up` — النبض الأخير ما زال ضمن المهلة |
| بعد ~10 ثوانٍ | HTTP **503** — `{"supervisor":"down","reason":"stale"}` |

المهلة = `min(max(10s، 3×الفاصل)، 120s)` — مع `--interval 2` تساوي 10 ثوانٍ.
**التطبيق نفسه لا يتأثر:** `/health` بقي 200 و`/chat` يعمل. الحارس يراقب ولا يتحكم.

### الإعادة

أعد الأمر نفسه: `python -m backend.supervisor_daemon --interval 2`.
**الفعلي:** بعد ~5 ثوانٍ عاد `/supervisor/status` إلى HTTP 200 و`"supervisor":"up"` بنبض جديد.

> **أثر جانبي:** تشغيل الحارس يُنشئ `data/supervisor/` و`data/awareness/` — بيانات تشغيل حية. منذ GS-2
> (قرار المالك د.٤) هما مستثنيان في `.gitignore` فلا يظهران في `git status`.

---

## ٧) Ollama — العقل المحلي (اختياري)

بلا Ollama يعمل كل شيء بالمحرك القالبي. مع Ollama تصير الردود لغوية طبيعية. التكامل منفّذ في R-704
(`backend/ollama_client.py` + `backend/sovereign_response.py`) ومعطل افتراضيًا.

### الخطوات

1. **ثبّت Ollama:** Linux: `curl -fsSL https://ollama.com/install.sh | sh` (يتطلب `zstd` — إن ظهر
   `This version requires zstd` فثبّته: `sudo apt-get install zstd`). macOS/Windows: من موقع ollama.com.
2. **شغّله وتحقق:**
   ```bash
   ollama serve            # إن لم يكن يعمل كخدمة
   curl -s http://127.0.0.1:11434/api/tags
   ```
3. **حمّل النموذج:** `ollama pull qwen2.5:7b` (~4.7GB؛ مناسب للعربية).
4. **أنشئ `.env` في جذر المستودع** (مستثنى من git):
   ```
   OLLAMA_ENABLED=true
   OLLAMA_BASE_URL=http://127.0.0.1:11434
   OLLAMA_MODEL=qwen2.5:7b
   # OLLAMA_PROTOCOL=ollama   # الافتراضي — بروتوكول Ollama (/api/chat)
   ```
   R-736 (البند ٢.١): لمزود سحابي متوافق مع OpenAI بدل الخادم المحلي
   (Groq/OpenRouter وأي مزود متوافق) اضبط `OLLAMA_PROTOCOL=openai` مع
   `OLLAMA_BASE_URL` بادئة الإصدار كاملة (مثل `https://api.groq.com/openai/v1`)
   و`OLLAMA_API_KEY` — الدليل الكامل للمصادر الأربعة:
   `forensics/R-736_BRAIN_PROTOCOLS.md`.
   (ملاحظة: Ollama Cloud الرسمي يستخدم بروتوكول ollama نفسه — راجع الدليل.)
5. **أعد تشغيل الخادم** (`Ctrl+C` ثم أمر §٣) — الإعدادات تُقرأ عند الإقلاع.
6. **أرسل رسالة** `/chat` كما في §٤.

### الفرق الملاحَظ (مُجرّب — بنموذج أصغر `qwen2.5:0.5b` لضيق بيئة الاختبار)

| الحالة | الرد الفعلي |
|---|---|
| بلا Ollama | `أهلاً بك. أنا الذكاء السيادي — جاهز لخدمتك. لدي 0 تنبؤاً نشطاً بدقة 50.0%.` |
| مع Ollama | `أنا "الذكاء السيادي" - مساعد شخصي ذاتي استضافة للمالك. كيف يمكنني مساعدتك اليوم؟` |

`qwen2.5:7b` نفسه **لم يُجرَّب** هنا (الحجم) — الخطوات واحدة، والجودة أعلى.

### كيف تتأكد أن الرد من العقل فعلًا — لا من القالب

**لا تعتمد على أن الرد 200 وغير فارغ** — السقوط الاحتياطي يعيد 200 أيضًا. الدليل:

- **سجل Ollama** يُظهر الطلب: `[GIN] ... | 200 | 4.26s | 127.0.0.1 | POST "/api/chat"`.
- **سجل الخادم** عند تعطل Ollama يُظهر: `R-704 [OLLAMA]: فشل خادم العقل (ConnectError) — سقوط للمحرك القالبي`
  (مُجرّب: أوقفنا Ollama مع `OLLAMA_ENABLED=true` → رد قالبي + هذا التحذير).
- ملاحظة: `processing_time_ms` في رد `/chat` **لا يشمل زمن النموذج** (الفعلي 23ms بينما استغرق Ollama 4.3s) —
  لا تستدل به.

الوضع الصارم (`OLLAMA_MODE=llm`: «العقل غير متاح» بدل القوالب) **غير منفّذ** — مصمم فقط (القسم ٣ من الخارطة).

---

## ٨) ما لا يُجرَّب الآن

| البند | السبب |
|---|---|
| النشر (fly.io) | ينتظر أسرار النشر وتعريف CORS للإنتاج — قرار مالك |
| الحارس كخدمة (systemd/compose) | قرار تشغيلي للمالك — §٦ تشغيل يدوي فقط |
| Issue #7 | ينتظر مواصفات المالك |
| السجل السيادي ينمو | يحتاج مفتاح توقيع نشط — قرار مالك (§٥) |
| `/sovereign/command` وما يحتاج مفتاح API | خارج نطاق التجربة الأساسية |
| الإجراءات الآلية القصوى | محجوبة عمدًا (R-703) |

---

## ٩) الإيقاف والتنظيف

- `Ctrl+C` في طرفية الخادم وطرفية الحارس.
- `git status` يجب أن يكون نظيفًا (مخرجات الحارس مستثناة منذ GS-2). لحذفها يدويًا إن أردت:
  `rm -rf data/supervisor data/awareness`.
- لإلغاء Ollama: احذف `.env` أو اضبط `OLLAMA_ENABLED=false` وأعد التشغيل.

---

## ١٠) التحقق الكامل (اختياري — للمطوّر)

```bash
pytest tests/ backend/tests/ -q -m "not operational"
# الفعلي عند GS-1: 743 passed, 1 deselected (~4 دقائق) — العدد الحالي في docs/PROJECT_STATE.md

bash verify.sh --full
# الفعلي: رمز خروج 0 — تطابق ثلاثي (محلي = CI = استنساخ نظيف) — 743/0/0 عند GS-1
```
