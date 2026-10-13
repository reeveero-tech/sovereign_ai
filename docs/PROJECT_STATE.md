# PROJECT_STATE.md — حالة المشروع

> أين نحن الآن؟ هذه الوثيقة تُحدَّث في **كل دفعة** (قاعدة الدفعة الذرية).
> آخر تحديث: 2026-10-14 (الدفعة M6 — R-609)

---

## 1) ملخص الحالة

| البعد | الحالة |
|---|---|
| المرحلة | **M6 — Continuous Improvement** (R-609 مكتمل؛ 35 بنداً منجزاً) |
| البناء | ✅ الخادم يُقلع ويستجيب (`/health`, `/status`, `/chat`, `/api/*`, `/nexus/*`, `/security/*`) |
| الاختبارات | ✅ 48 اختباراً (`tests/`) — آخر تشغيل: 48 passed + اختبار تحميل JS (122/122) |
| CI/CD | ✅ GitHub Actions + بوابة atomic-batch |
| التوثيق | ✅ API/Swagger/ReDoc + وثائق الحوكمة محدثة |
| الأمان | ✅ طبقة الأمان الكاملة حيّة (R-608/R-609): SafetyGuard يفحص كل المدخلات (بما فيها WebSocket `/ws/{user_id}`) + 6 نقاط /nexus/* + الضغط الأسطوري مربوط + تشفير AES-256-CBC (pycryptodome)؛ ختم الهوية سليم (R-604)؛ نقاط التحكم الأساسية محمية |
| الحالة العامة | **مستقر** — M5 وM6 متحققان ومنشوران؛ دورة المنسق سريعة (~0.25 ثانية)؛ نظام Sovereign Runtime كامل في الواجهة (R-607)؛ طبقة الأمان كاملة في الخلفية (R-608)؛ تدقيق شامل أصلح 6 أخطاء حقيقية (R-609)؛ لا عوائق نشر حالية |

---

## 2) ما الذي يعمل (مُتحقق منه في هذه الدفعة)

- ✅ الخادم يُقلع: `cd backend && uvicorn app:app` → يعمل على المنفذ.
- ✅ `/health` → `{"status":"healthy","version":"4.0.0"}` مع 23 مكوّناً كلها `healthy`.
- ✅ `/status` → `operational`، orchestrator نشط.
- ✅ `/chat` → يستجيب بقرار (مثال: `تم تنفيذ القرار: monitor`).
- ✅ `/api/run`, `/api/state`, `/api/components`, `/api/mode`, `/api/history` → تعمل.
- ✅ `/orchestrator/cycle` → يعمل ويتطلب `api_key`.
- ✅ `nexus.main.initialize_nexus` → يُستورد بنجاح ومكوّنات NexusCore موصولة بالنواة عبر `/components/nexus`.
- ✅ 135 ملف Python في backend+nexus+memory: **كلها سليمة نحوياً** (py_compile).
- ✅ 122 ملف JS في frontend: **كلها سليمة ومحمّلة في index.html** (R-607: إحياء 43 ملفاً ميتاً — نظام Sovereign Runtime كامل).
- ✅ **R-608**: طبقة الأمان الكاملة حيّة — `SafetyGuard` يفحص كل مدخلات `/chat` وWebSocket و`/sovereign/*`؛ 6 نقاط `/nexus/*` تعمل (REST API لـ NexusCore)؛ الضغط الأسطوري مربوط في دورة المنسق (كل 50 دورة)؛ 44 اختباراً تمر.
- ✅ **R-609**: تدقيق شامل لكل ملف/مجلد/اسم — إصلاح 6 أخطاء حقيقية: (1) `/components/predictive` كان يعيد 500 (`get_controller_status` غير موجودة)؛ (2)+(3) استدعاء `ingest` في المنسق كان يمرر `importance` و3 وسائط موضعية (التوقيع `intensity` ووسيطان) → TypeError كل دورة؛ (4)+(5) `PredictiveEngine.reset()` كان يستدعي `_load_index()` و`_now_iso()` غير المعرّفتين؛ (6) WebSocket `/ws/{user_id}` (مسار المحادثة الحي) لم يكن مفحوصاً بطبقة الأمان. أُضيف `pycryptodome` (تشفير AES-256-CBC بدل XOR-DEV)؛ 4 اختبارات جديدة؛ 48 اختباراً تمر.

- ✅ **M1 (R-101..R-112)**: 12 إصلاحات مكتملة — راجع `ROADMAP.md`.
- ✅ **R-109**: دورة الوعي تكتمل بنجاح (`success=True`, `decision=monitor`, `errors=[]`, ~37 ثانية) — كانت تعلق لأكثر من 120 ثانية.
- ✅ **R-106**: `/api-key` محمي (403 بدون مفتاح، 200 مع `master_key`).
- ✅ **R-108**: `/orchestrator/cycle` محمي (401 بدون `api_key`، 200 معه).
- ✅ **R-107**: CORS مقيد (يقرأ `CORS_ORIGINS` من الإعدادات).
- ✅ **R-104**: المنافذ موحدة على `PORT` (افتراضي 8000).
- ✅ **R-105**: `main.py --test` يمر بجميع الاختبارات (22 مكوّناً صحياً).
- ✅ **R-112**: `.gitignore` أُنشئ — `__pycache__` وبيانات وقت التشغيل لم تعد تُتتبع.

- ✅ **M2 (R-201..R-203)**: 3 بنود اكتملت — راجع `ROADMAP.md`.
- ✅ **R-201**: بنية الجذر نظيفة — أُزيلت بقايا المجلدات الفارغة، أُرشف `dockerignore` المكرر.
- ✅ **R-202**: التسمية موحدة على **Sovereign AI (SOVRA)** — README حُدث.
- ✅ **R-203**: نمط الكود الموحد موثق في QUALITY.md.

- ✅ **M3 (R-302, R-303)**: 2 من 3 بنود اكتملت — راجع `ROADMAP.md`.
- ✅ **R-302**: القرار D-010 — إعادة التوصيف بصدق (rule-based، لا LLM).
- ✅ **R-303**: أُرشف `backend/biological` المكسور — النواة تستخدم `memory.biological`.
- ✅ **R-301**: NexusCore مدمجة في النواة (قرار D-012) — 46 مكوّناً فرعياً، `/components/nexus` يعمل.
- ✅ **R-401**: 15 اختباراً أساسياً (إقلاع + API + صياغة) — كشف خطأ `status` في `/sovereign/command`.
- ✅ **R-402**: CI/CD (GitHub Actions) + بوابة الدفعة الذرية.
- ✅ **R-403**: توثيق حي (Swagger/ReDoc/OpenAPI) + API.md محدثة.
- ✅ **R-501**: الواجهة الأمامية اجتازت QA متصفحياً: `issue_count: 0`، لا أخطاء JavaScript، لا طلبات فاشلة.
- ✅ **R-502**: ضغط GZip للاستجابات الكبيرة؛ `/` انخفض من 35,240 إلى 4,727 بايت مع gzip (86.6%).
- ✅ **R-601**: مراجعة دورية للخارطة والحوكمة؛ 27 بنداً منجزاً قبل دفعة R-602.
- ✅ **R-602**: أزيل المفتاح السيد الافتراضي المعروف؛ التطوير يولد مفتاحاً عشوائياً مؤقتاً والإنتاج يفشل مغلقاً دون سر.
- ✅ **R-603**: `/chat` محدود إلى `MAX_USER_MESSAGES_PER_MINUTE` لكل IP مباشر؛ التجاوز يعيد 429/`Retry-After`. المحدد bounded ومحلي لكل عملية؛ 29 بنداً منجزاً.
- ✅ **R-604**: أُصلح انحدار سلامة ختم الهوية — طابع زمني موحد للتوقيع، بصمة قوالب أنماط ثابتة بدل الاحتمالات المتغيرة، فحص سلسلة الذاكرة بدل مقارنة `core_hash` الثابت، وترحيل الأختام القديمة (v3→v4). لا إنذارات `ختم الهوية تالف` بعد الإصلاح؛ 30 بنداً منجزاً.
- ✅ **R-605**: أُزيل تتبع 2233 ملف بيانات وقت تشغيل (8.8MB) من git — شجرة العمل تبقى نظيفة بعد تشغيل الاختبارات؛ الملفات تبقى على القرص وتُعاد إنشاؤها تلقائياً؛ 31 بنداً منجزاً.
- ✅ **R-606**: تحسين أداء دورة المنسق — تخزين مؤقت قصير (TTL) لـ 12 getter باهظ الثمن (الاستدعاء الثاني شبه فوري)، إصلاح عودية `get_early_warnings_list`، إصلاح ذاكرة التحقق من سلامة السجل، إصلاح `reset()`/إعادة بناء الفهرس، مسار ذيل سريع في `iterate_events`، وإصلاح سجل تالف (رأس مقطوع + مفاتيح مختلطة). زمن الدورة ~11 ثانية → ~0.25 ثانية؛ صفر فشل سلامة؛ 32 بنداً منجزاً.

### حالة النشر
- ✅ **GitHub متزامن**: `HEAD` و`origin/main` متطابقان بعد نشر R-603 (`ahead/behind: 0/0`). أُغلق R-003 بعد نجاح الدفع والتحقق.



---

## 3) ما الذي لا يعمل / أخطاء مُتحقق منها

### أخطاء وقت التشغيل
- ✅ **أُصلحت في R-109**: أخطاء `MemoryWatcher.get_status`, `str.value`, `السجل غير موجود` — كلها أُصلحت. الدورة تكتمل بصفر أخطاء.

### أخطاء صياغة في الواجهة
- ✅ **أُصلحت في R-101/R-102**: `system-thought-nebula.js` اكتمل (640 سطراً)، `system-runtime-consciousness-loop.js` أُصلحت مفاتيحه. كل 122 ملف JS يمر `node --check`.

### مشاكل تشغيل/نشر
- ✅ **أُصلحت في R-103/R-104/R-105**: الاعتماديات موحدة (9 مثبتة)، المنافذ موحدة على `PORT` (8000)، `Dockerfile` يعمل (`WORKDIR /app/backend`, `PYTHONPATH`, `uvicorn app:app`).

---

## 4) البنية الحالية (ملخص)

```
sovereign_ai/
├── backend/          # النواة (FastAPI): app.py, orchestrator.py, api.py, config.py, safety.py
│   ├── consciousness/  # الوعي (field, identity, self_model, awareness, attention, introspection)
│   ├── memory/         # الذاكرة (core, views, compress, encoding + biological/ defense/ dynamic/ store/)
│   ├── predictive/     # التنبؤ
│   ├── simulation/     # المحاكاة
│   ├── quantum/        # "الكم" (محاكاة مفاهيمية)
│   ├── sovereign/      # الإرادة/التحكم/التوجيه/المواءمة
│   └── biological/     # حزمة backend/biological المكررة أُرشفت في R-303; النشط في memory/biological
├── frontend/         # واجهة عربية RTL (index.html + 122 ملف JS + css + ui)
├── nexus/            # منصة NexusCore — 71 ملف، مدمجة بالنواة ومكشوفة عبر /components/nexus
├── guardian/         # نظام طوارئ/نسخ احتياطي (204 ملف) — يحتوي قفل SYSTEM_LOCKED
├── data/             # بيانات وقت التشغيل (11MB، 2233 ملف متتبع — blobs مشفرة zlib)
├── memory/           # ⚠️ نسخة مكررة قديمة من backend/memory/defense/polymorphic.py
├── nexus_data/       # nexus.db (SQLite — فارغ: 0 أحداث، 0 مفاتيح)
├── infrastructure/   # ⚠️ Dockerfile + requirements.txt فارغان (بايت واحد)
├── attached_assets/  # ⚠️ ملفان نصيان يحويان تعليمات AI (ليسا كوداً)
├── Fff, IDs.py, encryption.py, investigation.py, Mr.py  # ⚠️ ملفات جذر شاذة (راجع أدناه)
├── main.py           # نقطة تشغيل بديلة (يجب تشغيله من backend)
├── Dockerfile, fly.toml, start.sh, .replit, requirements.txt
└── docs/             # 🆕 وثائق الحوكمة (أُنشئت في هذه الدفعة)
```

---

## 5) الملفات الجذرية الشاذة (قرارات مفتوحة)

| الملف | الحجم | الحقيقة | الحالة (R-110) |
|---|---|---|---|
| `Fff` | 28KB | نص تعليمات AI (ليس كوداً) | ✅ مؤرشفة → `archive/root_strays/Fff.txt` |
| `IDs.py` | 61KB | كود TypeScript/JS (رغم امتداد .py) — "غرفة التحري" | ✅ مؤرشفة → `archive/root_strays/IDs.js` |
| `encryption.py` | 74KB | "موسوعة التشفير" Python | ✅ مؤرشفة → `archive/root_strays/encryption.py` |
| `investigation.py` | 103KB | نظام CIKMS استخباراتي (أسماء عربية) | ✅ مؤرشفة → `archive/root_strays/investigation.py` |
| `Mr.py` | 44KB | "محرك الولاء" — يحتوي بروتوكول موت/كشف عبث (sys.exit) | ⚠️ **أُبقي في مكانه** (خطر تدمير ذاتي عند النقل) — قرار D-005 |

> كلها كانت **كوداً ميتاً** (لا شيء يستوردها). أُرشفت في R-110 (قرار D-005). `Mr.py` أُبقي دون لمس بسبب بروتوكول الموت الذاتي.

---

## 6) المخاطر الحالية (ملخص — التفاصيل في RISKS.md)

1. ✅ **مفتاح API** — `/api-key` يتطلب `master_key` (R-106).
2. ✅ **CORS مفتوح** — أُغلق في R-107 (يقرأ `CORS_ORIGINS`).
3. ✅ **مفتاح سيد افتراضي** — لا قيمة ثابتة؛ الإنتاج يفشل مغلقاً دون `SOVEREIGN_KEY` (R-602).
4. ✅ **`/orchestrator/cycle`** — يتطلب `api_key` (R-108). `/chat` محدود المعدل في R-603، لكنه ما يزال بلا تسجيل دخول.
5. 🟠 **Mr.py**: كود "ولاء" مع بروتوكول موت ذاتي (sys.exit) وكشف عبث — أُبقي دون لمس (قرار D-005). خطر تشغيلي/أمني قائم.
6. 🟠 **guardian/SYSTEM_LOCKED.lock**: قفل طارئ مقصود (PROTECTED_ACTION_WITHOUT_MASTER_TOKEN) — أُبقي كحالة أمان موثقة (قرار D-006). يتطلب رمز إعادة تفعيل من السيد (س-3).
7. ✅ **لا .gitignore** — أُنشئ في R-112.
8. ✅ **الاختبارات وCI** — 48 اختباراً وبوابة atomic-batch في GitHub Actions (R-401/R-402/R-609).

---

## 7) القرارات المسجلة

- **D-001**: بدء المشروع بمرحلة M0 (مسح + توثيق) دون إصلاح أي خطأ — بأمر السيد ("لا تصلح أي خطأ الآن").
- **D-002**: اعتماد قاعدة الدفعة الذرية كقاعدة حوكمة وحيدة غير قابلة للتفاوض (راجع `GOVERNANCE.md`).
- **D-003**: إنشاء مجلد `docs/` للوثائق الحاكمة (لم يكن موجوداً).
- **D-005**: أرشفة الملفات الجذرية الشاذة (R-110) — إبقاء `Mr.py` دون لمس.
- **D-006**: إبقاء قفل guardian (R-111) — آلية أمان مقصودة، لا تُرفع.
- **D-007**: تخزين مؤقت (TTL) لمسار الاستبطان (R-109) — الدورة تكتمل بصفر أخطاء.
- **D-008**: توحيد التسمية على SOVRA (R-202).
- **D-009**: تنظيف بنية الجذر (R-201).
- **D-010**: إعادة التوصيف بصدق — لا LLM الآن (R-302).
- **D-011**: أرشفة backend/biological المكسور (R-303).
- **D-012**: دمج NexusCore في النواة (R-301).

---

## 8) العوائق الحالية

- لا عائق نشر مسجل بعد التحقق من تزامن `HEAD` و`origin/main`.
- **قيد أمني معروف**: حد `/chat` process-local؛ deployment متعدد workers يحتاج مخزناً مشتركاً إن لزم حد عالمي.
- دورة الوعي تكتمل لكن وقتها متغير (~37-68 ثانية) بسبب 41 خيطاً خلفياً يتنافس على القفل — مؤجل إلى M2/M3.

---

## 9) سجل الحالة

| التاريخ | الحالة | الدفعة |
|---|---|---|
| 2026-10-12 | M0 قيد الإنجاز — مسح مكتمل، وثائق أُنشئت | M0: baseline audit + roadmap bootstrap |
| 2026-10-12 | M1 مكتملة — 12 إصلاحاً (R-101..R-112)، الدورة تكتمل بصفر أخطاء | M1: stop the bleeding |
| 2026-10-12 | M2 مكتملة — 3 بنود (R-201..R-203)، بنية نظيفة، تسمية موحدة، نمط كود | M2: consistency |
| 2026-10-12 | M3 جزئية — R-302/R-303 مكتملتان، R-301 بانتظار قرار السيد | M3: architecture |
| 2026-10-12 | M3 مكتملة — R-301: دمج NexusCore في النواة | M3: architecture |
| 2026-10-13 | M4 مكتملة — R-401/R-402/R-403: اختبارات + CI/CD + توثيق | M4: quality gates |
| 2026-10-13 | M5 مكتملة — R-501/R-502: QA الواجهة + ضغط الاستجابات | M5: delivery |
| 2026-10-13 | M6 — R-604: إصلاح سلامة ختم الهوية (انحدار حقيقي) + 7 اختبارات | M6: continuous improvement |
| 2026-10-13 | M6 — R-605: إلغاء تتبع بيانات وقت التشغيل (قرار R-112 المؤجل) | M6: continuous improvement |
| 2026-10-13 | M6 — R-606: تحسين أداء دورة المنسق (TTL caching + إصلاح عودية + إصلاح سجل + مسار ذيل سريع) | M6: continuous improvement |
| 2026-10-13 | M6 — R-607: إحياء 43 ملف JS ميت (نظام Sovereign Runtime) — ترتيب اعتماديات + إصلاح 3 أخطاء + ربط بـ index.html | M6: continuous improvement |
| 2026-10-14 | M6 — R-608: إحياء طبقة الأمان الكاملة (safety.py + api_gateway + compress.py) | M6: continuous improvement |
| 2026-10-14 | M6 — R-609: تدقيق شامل — إصلاح 6 أخطاء حقيقية + تشفير AES-256-CBC + 48 اختباراً | M6: continuous improvement |


## 10) R-603 — دليل التحقق

- `python -m pytest tests/ -q`: **23 passed**, 6 تحذيرات إهمال من dependencies.
- اختبارات R-603 تغطي تجاوز الحد، انتهاء النافذة، استقلال العملاء، bounded tracking، ربط dependency بمسار `/chat`، ورفض إعداد حد غير صالح.
- النشر والتحقق النهائي: `git push origin main` ناجح؛ `HEAD` و`origin/main` متطابقان (0/0).


## 15) R-608 — دليل التحقق

- **التحقيق**: 3 مكونات ميتة في الخلفية: `backend/safety.py` (SafetyGuard — 520 سطراً، غير مستورد)، `nexus/api_gateway/` (NexusRouter + RateLimiter، غير مستورد)، `memory/compress.py` (SovereignCompressor، مستورد فقط عبر `memory/__init__.py` غير المستورد). اكتشاف إضافي: طريقة `reset` في `compress.py` كانت على العمود 0 (خارج الفئة) — ابتلعت `__init__` و`compress` و`get_stats` كدوال متداخلة، فكانت الفئة بلا أي طرق وتتعطل عند أي استخدام (سبب كونها كوداً ميتاً فعلياً).
- **الإجراء**: (1) ربط `SafetyGuard` في `app.py` (فحص `/chat` + `/sovereign/command` + `/sovereign/reset`) و`api.py` (فحص WebSocket `sir_command` + `chat_message`)؛ (2) إضافة نقطتي `/security/status` و`/security/log`؛ (3) ربط `NexusRouter` في التطبيق (6 نقاط `/nexus/*`)؛ (4) إصلاح بنية `compress.py` (إزاحة `reset` إلى داخل الفئة) وربط الضغط في `orchestrator._update_memory` (كل 50 دورة)؛ (5) حذف النسختين المكررتين الأصغر (`archive/root_strays/memory_defense_polymorphic_duplicate.py` 756 سطراً — v3.0.0 أقدم من الحية v4.0.0؛ `archive/root_strays/backend_biological_init_duplicate.py` 25 سطراً) وإبقاء الأكبر (النسخة الحية 798 سطراً + النسخة الاحتياطية الكبرى في guardian 4.5MB)؛ (6) 9 اختبارات جديدة في `tests/test_safety_layer.py`.
- **التحقق**: `python -m pytest tests/ -q`: **44 passed** (35 + 9 جديدة)؛ رسالة خطيرة في `/chat` → `status: blocked` مع رد أمني؛ `/security/status` → `safety_guard.active: True`؛ `/nexus/health` → `200 healthy`؛ ضغط 3 أحداث → وعي 16 بايت؛ إجمالي المسارات 37 → 45.
- النشر والتحقق النهائي: `git push origin main` ناجح؛ `HEAD` و`origin/main` متطابقان (0/0).


## 16) R-609 — دليل التحقق

- **التحقيق**: تدقيق شامل لكل ملف ومجلد واسم في المستودع — 245 JS + 215 Python + 17 وثيقة + كل المسارات والمكونات والمراجع.
- **الأخطاء المكتشفة والمصلحة (6)**:
  1. `/components/predictive` → 500: `PredictiveController.get_controller_status()` غير موجودة (الموجودة: `get_stats`, `get_mode`, `get_last_decision`) — استُبدلت بدالة تجميع.
  2. `orchestrator._update_memory`: `ingest(..., importance=0.5)` — التوقيع `intensity=0.5` → TypeError "فشل استدعاء ingest" كل دورة.
  3. نفس الاستدعاء: 3 وسائط موضعية (`"system", f"cycle_{id}", str(record)`) لكن `ingest(user_id, text)` وسيطان — حُذفت الوسيطة الثالثة.
  4. `PredictiveEngine.reset()`: `self._load_index()` غير موجودة — استُبدلت بـ `_load_state()` + `_load_forecasts()`.
  5. `PredictiveEngine.reset()`: `_now_iso()` غير معرّفة — استُبدلت بـ `time.time()`.
  6. WebSocket `/ws/{user_id}` (مسار المحادثة الحي في الواجهة) لم يكن مفحوصاً بطبقة الأمان — أُضيف فحص `enforce_input_safety` (الرسائل الخطيرة → `blocked=True` + `cycle_id="safety-block"`).
- **فجوة أمان**: `pycryptodome` لم يكن في `requirements.txt` — التشفير كان يتراجع إلى XOR-DEV. أُضيف `pycryptodome==3.24.1` — تحقق: AES-256-CBC يعمل (encrypt/decrypt round-trip).
- **نظافة**: `data/security_log.json` و`data/approval_cache.json` (بيانات وقت تشغيل) أُضيفا إلى `.gitignore`.
- **التحقق**: `python -m pytest tests/ -q`: **48 passed** (44 + 4 جديدة)؛ كل نقاط `/components/*` و`/security/*` و`/nexus/*` تعيد 200؛ WebSocket خطير → `blocked=True`؛ كل 54 وحدة backend + 51 وحدة nexus + 4 وحدات guardian تُستورد بنجاح؛ `main.py --test` يمر.
- النشر والتحقق النهائي: `git push origin main` ناجح؛ `HEAD` و`origin/main` متطابقان (0/0).

## 11) R-604 — دليل التحقق

- **التحقيق**: إنذار `❌ ختم الهوية تالف: الأنماط الأصلية تغيرت!` كان انحداراً حقيقياً في الختم نفسه (ثلاثة أسباب جذرية: طابع زمني غير موحد، بصمة أنماط متغيرة، مقارنة `core_hash` ثابت).
- **الإصلاح**: `create_seal` (v4) بطابع زمني موحد وبصمة قوالب ثابتة؛ `verify_seal` يتحقق من التوقيع من الحقول المخزنة ويفحص سلسلة الذاكرة؛ `_load_seal` يهاجر الأختام القديمة (v3→v4).
- `tests/test_identity_seal.py`: **7 اختبارات جديدة** (ختم جديد، بقاء عبر تطور الأنماط، بقاء عبر إضافة أحداث، كشف تلاعب المفتاح، كشف تلاعب التوقيع، إعادة التحميل، ترحيل v3).
- `python -m pytest tests/ -q`: **30 passed** — لا إنذارات `ختم الهوية تالف` في التشغيل.
- النشر والتحقق النهائي: `git push origin main` ناجح؛ `HEAD` و`origin/main` متطابقان (0/0).

## 12) R-605 — دليل التحقق

- **القرار المؤجل من R-112**: 2233 ملف بيانات وقت تشغيل (2228 blob + 5 ملفات حالة) كانت مُتتبَّعة في git رغم `.gitignore` (أُنشئ بعد تتبعها).
- **الإجراء**: `git rm -r --cached data/` — إزالة من الفهرس مع إبقاء الملفات على القرص.
- **التحقق**: `git ls-files data/` = 0؛ `git check-ignore --no-index` يطابق كل ملف؛ `git status` نظيف بعد تشغيل `pytest`؛ الملفات تبقى على القرص.
- النشر والتحقق النهائي: `git push origin main` ناجح؛ `HEAD` و`origin/main` متطابقان (0/0).

## 13) R-606 — دليل التحقق

- **التحقيق**: دورة المنسق ~11 ثانية؛ `_analyze_future`/`sense_state` هما عنق الزجاجة (41.9 ثانية) لأن كل `get_*_status()` يُعيد تشغيل دورة كاملة (يقرأ آلاف blobs) وتُستدعى بشكل متكرر داخل دورة المنسق الواحدة. خطأ عودية في `get_early_warnings_list` (تعريف مكرر — الأخير يستدعي نفسه). ذاكرة `verify_integrity` تُبطل في كل إضافة حدث → فحص كامل للسجل (15378 سطراً) يفشل عند السطر 1 (رأس مقطوع من تشغيلات اختبار).
- **الإصلاح**: (1) TTL caching (نمط `drives.py` — 2 ثانية) على 12 getter باهظ الثمن؛ (2) إزالة التعريف المكرر العودي؛ (3) إبطال ذاكرة التحقق عند الإضافة + TTL 60 ثانية؛ (4) إصلاح `_load_index` وإضافة `_rebuild_index` وإصلاح ترتيب `_save_meta` بعد الفهرس؛ (5) مسار ذيل سريع في `iterate_events`؛ (6) إصلاح السجل التالف عبر `reset()` (نسخة احتياطية `.bak` أولاً).
- `tests/test_performance_r606.py`: **5 اختبارات جديدة** (تخزين getter، لا عودية، TTL سلامة، تطابق مسار الذيل، إعادة بناء الفهرس).
- `python -m pytest tests/ -q`: **35 passed**.
- قياس الأداء: دورة المنسق ~0.25 ثانية (من ~11 ثانية)؛ صفر `prev_hash غير متطابق` في التشغيل.
- النشر والتحقق النهائي: `git push origin main` ناجح؛ `HEAD` و`origin/main` متطابقان (0/0).


## 14) R-607 — دليل التحقق

- **التحقيق**: 43 ملف JS (26,880 سطراً) على القرص غير محمّلة في index.html — تشكّل نظام "Sovereign Runtime" الفرعي الكامل (محرك الإدراك، النواة السيادية، إدارة الجلسات، حوكمة التنفيذ، العدالة، قياس التدفق، الوعي الذاتي). النواة (runtime-kernel, runtime-orchestrator-ai, runtime-consciousness-core, runtime-init) محمّلة بالفعل؛ الوحدات الميتة صُممت للتسجيل فيها عبر `window.SOVEREIGN`.
- **الإجراء**: (1) بناء خريطة اعتماديات كاملة (معرّفو globals ← مستخدموها)؛ (2) ترتيب طوبولوجي — 43 ملفاً بلا دوائر (4 ملفات في "دائرة" لكن كل الوصولات `?.` آمنة)؛ (3) إدراج 43 وسم سكربت في index.html قبل runtime-init.js؛ (4) إصلاح 3 أخطاء حقيقية في الكود الميت: `startCognitiveLoop` مفقودة في cognition-engine، `registerLaw` مفقودة في sovereign-core، خطأ مطبعي `self.selfQuarantine` → `this.selfQuarantine` في autonomous-preservation.
- **التحقق**: اختبار تحميل jsdom — **122/122 ملف تُحمَّل، 0 فشل**؛ **40/40 وحدة ميتة سُجّلت** في `window.SOVEREIGN` (52 نظاماً إجمالاً، من 17 سابقاً)؛ `node --check` يمر على الملفات الثلاثة المُصلحة؛ `python -m pytest tests/ -q`: **35 passed**.
- النشر والتحقق النهائي: `git push origin main` ناجح؛ `HEAD` و`origin/main` متطابقان (0/0).
