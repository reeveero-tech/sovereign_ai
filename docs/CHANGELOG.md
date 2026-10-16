# CHANGELOG.md — سجل التغييرات

> كل تغيير يُسجل هنا (قاعدة الدفعة الذرية).
> آخر تحديث: 2026-10-14 (الدفعة M6 — R-614)

---

## [M6] — 2026-10-14 — R-614: إغلاق س-5 وس-9 — بصمة المفتاح + محرك ردود سيادي

### أُصلح
- **س-5 (تسريب مفتاح API)**: `/api-key` كانت تعيد المفتاح الحقيقي بلا مصادقة. الآن تتطلب `master_key` (403 بدونها) وتعيد فقط بصمة SHA-256 (16 حرفاً) + مصدر الثبات + حالة التطوير. المفتاح الحقيقي لا يظهر في أي استجابة (المفتاح دائم منذ R-610: `data/key.secret` 0600 مستثنى من git أو `SOVEREIGN_KEY`).
- **س-9 (ردود جاهزة بدل ذكاء)**: ردود `/chat` كانت قوالب ثابتة رغم وجود حالة حية غنية. أُنشئ `backend/sovereign_response.py` — `gather_evidence()` يقرأ الحالة الفعلية (ذاكرة، تنبؤات، مخاطر، محاكاة، متحكم سيادي، وعي) و`build_reply(intent, text, result)` يصوغ الرد من الأدلة. كل getter مغلّف بـ try/except — لا يرمي أبداً. وُصل في `/chat` مع احتياط للقوالب القديمة.

### أُضيف
- `backend/sovereign_response.py`: محرك الردود السيادي (جديد).
- `tests/test_sovereign_response_r614.py`: 9 اختبارات (لا تسريب للمفتاح، جمع الأدلة، ردود status/greet/alert/help، لا يرمي لكل النوايا).
- تحديث `tests/test_api.py`: تأكيد غياب `api_key` من استجابة `/api-key`.

### تحقق
- `python -m pytest tests/ -q` → **71 passed, 1 warning** (التحذير من starlette الخارجية — غير قابل للإصلاح).
- `/api-key` → 200 مع بصمة `7d282c7d622f5ab2` بلا `api_key`؛ بلا `master_key` → 403.
- `/chat` "مرحبا" → "أهلاً بك... لدي 34 تنبؤاً نشطاً بدقة 50.0%"؛ "ما حالة النظام؟" → حالة بأرقام حقيقية؛ "حلل الوضع" → خطر 48.8% مقابل فرصة 54.3%؛ "توقع المستقبل" → توقعات حقيقية؛ "تنبيه" → ⚠️ 1 خطر عالي الأولوية. كلها status ok.

---

## [M6] — 2026-10-14 — R-613: التدقيق العميق — إصلاح 3 أخطاء حقيقية

### أُصلح
- `backend/simulation/simulation_environment.py`: **`reset()` كان مكسوراً** — يستدعي `_now_iso()` و`self._load_index()` غير المعرّفتين ويشير إلى خصائص غير موجودة (`environment_state`, `environment_history`, `_index`, `policies`). كان يُستدعى من `simulation_controller.py:218` داخل `try/except pass` — الخطأ يُبتلع بصمت. أُصلح: إعادة تعيين حقيقية للحالة (templates/parameter_sets/instances/active_template/active_parameter_set) + دالة `_now_iso()` على مستوى الوحدة.
- `backend/memory/core.py`: **`verify_integrity()` كان يمشي السجل الكامل (9141 حدثاً) في كل استدعاء** — `_integrity_cache` كان يُصفَّر عند كل إضافة حدث (خلفية اللقطات) → فرع الكاش 60s لا يُصل أبداً. أُزيل التصفير — الكاش 60s يكفي. `verify_integrity()` بعد الإضافة: 0.0s (كان ~2.5s).
- `backend/predictive/predictive_simulation.py`: **`get_simulation_results()`/`get_recommendations()` كانا يشغّلان محاكاة كاملة 100×12 عند قراءة حالة فقط (~3.4s)** — الآن دورة صغيرة 10×6. `get_risk_status()` 1.61s (كان 13.65s)؛ `/components/predictive` 200 في 2.04s بارد / 0.002s دافئ (كانت timeout >20s).
- `backend/memory/compress.py`: **`SovereignCompressor.reset()` كان مكسوراً** — يستدعي `self._load_index()` غير المعرّفة و`self.core.append_event(...)` مع `self.core` غير المعيّن أبداً في `__init__`. أُصلح: `_load_index()` حقيقية (فهرس الضغط) + `get_core()` بدل `self.core` (مطابقاً لـ `compress_from_core`).
- `backend/app.py`: تنظيف متغيرات ميتة (`status` في `/health`، `reasoning` و`lang` في `/chat`).

### أُضيف
- `tests/test_simulation_reset_r613.py`: 2 اختبارات (إعادة تعيين بيئة المحاكاة تنظف الحالة الحقيقية؛ إعادة تعيين المتحكم لا ترمي).
- `tests/test_compress_reset_r613.py`: 2 اختبارات (إعادة تعيين الضاغط تعمل؛ متماثلة).
- `tests/test_predictive_perf_r613.py`: 2 اختبارات (كاش `verify_integrity` يبقى بعد الإضافة؛ `get_simulation_results` سريعة).

### حُدث
- `.gitignore`: استثناء `guardian/data/emergency/emergency_backups/*/data/` (بيانات وقت تشغيل).
- وثائق الحوكمة: `ROADMAP.md`, `PROJECT_STATE.md`, `OPEN_QUESTIONS.md`.

### ملاحظات
- تحقق فعلي: `python -m pytest tests/ -q` → `62 passed, 1 warning` (كانت 56)؛ `SimulationEnvironmentManager().reset()` → templates 0/param_sets 0/instances 0؛ `SimulationController().reset()` يعمل؛ `SovereignCompressor().reset()` يعمل مرتين؛ `/components/predictive` → 200 في 2.04s بارد؛ فحص ثابت شامل: لا استدعاء `self.<method>()` بدون تعريف ولا دالة وحدة غير معرّفة في كل backend؛ `git status --short` نظيف بعد تشغيل كامل. سُجل القرار D-026.

---

## [M6] — 2026-10-14 — R-612: الذكاء السيادي الحقيقي

### أُصلح
- `backend/orchestrator.py`: **قرار المتحكم السيادي كان يُتجاهل دائماً** — `_make_decision` كان يقرأ `controller_decision.sovereign_decision` غير الموجودة (الحقل الفعلي `final_decision` بكائن `FinalDecision` يحمل `command_name`). الشرط كان دائماً `False` → القرار السيادي لا يُستخدم أبداً. أُصلح: قراءة `final_decision.command_name` مع خريطة أوامر → إجراءات. المصدر الآن `sovereign_controller`.
- `backend/orchestrator.py`: **NexusCore (47 مكوّناً) كان معزولاً** — دورة المنسق لم تكن تقرأ نص المستخدم. أُضيف فهم النص في `_gather_perception` (لغة + مشاعر + نية + كلمات مفتاحية) → `perception["nexus"]`، وتوجيه القرار بنية المستخدم (`analyze`→`explore`, `alert`→`activate_defense`).
- `backend/memory.py`: ملف ميت (1 بايت) لا يُستورد أبداً — حُذف.

### أُضيف
- `backend/orchestrator.py`: كل دورة تُحفظ في `nexus_data/store/cycles/` عبر مكوّن `store` + سجل تدقيق موقّع عبر مكوّن `audit` — الذاكرة الطويلة حقيقية (S-7 مغلقة).
- `backend/app.py` + `backend/api.py`: ردود حقيقية في `/chat` و`/ws/{user_id}` و`/api/ws` — `فهمت — نيتك: تحليل. القرار: explore.` بدل الرد الجاهز.
- `tests/test_nexus_wiring_r612.py`: 5 اختبارات انحدار (فهم العربية/الإنجليزية، توجيه نية التحليل، استخدام قرار المتحكم، استمرار الدورة في مخزن Nexus).

### حُدث
- `.gitignore`: استثناء بيانات وقت تشغيل NexusCore (`nexus_data/store/`, `audit/`, `backups/`, `emergency/`, `exports/`, `files/`, `keys/`, `reports/`, `security/`).
- وثائق الحوكمة: `ROADMAP.md`, `PROJECT_STATE.md`, `OPEN_QUESTIONS.md`.

### ملاحظات
- تحقق فعلي: `python -m pytest tests/ -q` → `56 passed, 1 warning` (كانت 51)؛ `/chat {"text":"حلل هذه البيانات من فضلك"}` → `فهمت — نيتك: تحليل. القرار: explore.`؛ `/chat {"text":"مرحبا"}` → `قرار المتحكم السيادي: continue.`؛ WebSocket `/ws/{user_id}` و`/api/ws` يردان بفهم حقيقي ويمنعان الرسائل الخطيرة؛ `nexus_data/store/cycles/*.json` تُنشأ بعد كل دورة؛ `git status --short` نظيف بعد تشغيل كامل. سُجل القرار D-025.

---

## [M6] — 2026-10-14 — R-611: تحصين الإنتاج

### أُصلح
- `nexus/main.py`: نقطة الدخول كانت تفشل بـ `ModuleNotFoundError: No module named 'nexus'` عند التشغيل المباشر `python3 nexus/main.py` — أُضيف جذر المستودع إلى `sys.path` في كتلة `__main__`. الآن تعمل من أي دليل: `✅ NexusCore: 47 components` + `🛡️ Guardian: ACTIVE`.
- `backend/app.py` + `backend/api.py`: 5 تحذيرات `PydanticDeprecatedSince20` (class-based `Config`) حُوّلت إلى `model_config = ConfigDict(...)` — التحذيرات انخفضت من 6 إلى 1 (المتبقي من مكتبة starlette الخارجية).
- `backend/requirements.txt`: كان غير متزامن مع الجذر — أُضيف `pycryptodome==3.24.1` (تشفير AES-256-CBC) و`pytest==9.1.1` (الاختبارات). الآن مطابق تماماً للجذر.

### حُدث
- `.gitignore`: `guardian/data/guardian_events.jsonl` و`nexus_data/nexus.db` (بيانات وقت تشغيل تُنشأ تلقائياً) لم تعودا مُتتبعتين — شجرة العمل نظيفة بعد التشغيل (نفس فئة R-605).
- وثائق الحوكمة: `ROADMAP.md`, `PROJECT_STATE.md`.

### ملاحظات
- تحقق فعلي: `python3 nexus/main.py` يعمل؛ `python -m pytest tests/ -q` → `51 passed, 1 warning`؛ `git status --short` نظيف بعد تشغيل الخادم والاختبارات؛ WebSocket `/ws/{user_id}` و`/api/ws` يمنعان `shutdown the system` بـ `safety-block` (عميل WebSocket حقيقي). سُجل القرار D-024.

---

## [M6] — 2026-10-14 — R-610: الهوية السيادية الدائمة

### أُضيف
- `backend/config.py`: توليد مفتاح سيد دائم في التطوير عند غياب أي مصدر — يُحفظ في `data/key.secret` (0600، مستثنى من git) ويُعاد استخدامه عبر عمليات التشغيل. الهوية السيادية (ختم الهوية + توقيعات السجل) تستمر عبر إعادة التشغيل.
- `tests/test_identity_persistence.py` — 3 اختبارات: المفتاح الدائم ينجو من إعادة التشغيل؛ ختم الهوية يُتحقق منه بعد إعادة التحميل؛ تغيير المفتاح يُكتشف كتلاعب.

### حُدث
- `tests/test_config_security.py`: اختبار التطوير الآن يتحقق من مفتاح دائم يُعاد استخدامه (نفس القيمة عبر تشغيلين) بدل مفتاح مؤقت متغير.
- وثائق الحوكمة: `ROADMAP.md`, `PROJECT_STATE.md`, `QUALITY.md`, `RISKS.md`, `DECISIONS.md`, `SECURITY.md`.

### ملاحظات
- الإنتاج يبقى fail-closed (يرفض التشغيل دون سر مُدار خارج الكود) — لم يتغير.
- 51 اختباراً تمر (48 + 3 جديدة). سُجل القرار D-023.

---

## [M0] — 2026-10-12 — Baseline Audit + Roadmap Bootstrap

### أُضيف
- `docs/PROJECT_CHARTER.md` — ميثاق المشروع.
- `docs/PROJECT_STATE.md` — حالة المشروع.
- `docs/ROADMAP.md` — خارطة الطريق الحية (R-001..R-601).
- `docs/ARCHITECTURE.md` — البنية المعمارية.
- `docs/RISKS.md` — سجل المخاطر.
- `docs/OPEN_QUESTIONS.md` — الأسئلة المفتوحة (15 سؤالاً).
- `docs/GOVERNANCE.md` — الحوكمة وقاعدة الدفعة الذرية.
- `docs/DOMAIN.md` — منطق العمل.
- `docs/API.md` — الواجهات البرمجية.
- `docs/DATA_MODEL.md` — نموذج البيانات.
- `docs/OPERATIONS.md` — التشغيل والنشر.
- `docs/SECURITY.md` — الأمان.
- `docs/QUALITY.md` — الجودة والاختبارات.
- `docs/DECISIONS.md` — سجل القرارات (D-001..D-004).

### لم يتغير
- لا تغيير في الكود (بأمر السيد: "لا تصلح أي خطأ الآن").

### ملاحظات
- هذه الدفعة هي **الأولى** في المشروع — لا يوجد سجل سابق.

## [M1] — 2026-10-12 — Stop the Bleeding (R-101..R-112)

### أُصلح
- **R-101**: `frontend/js/system/system-thought-nebula.js` — اكتمل الملف المقطوع (585 → 640 سطراً)، `node --check` يمر.
- **R-102**: `frontend/js/system/system-runtime-consciousness-loop.js` — أُصلحت المفاتيح ذات الواصلة، `node --check` يمر.
- **R-103**: توحيد الاعتماديات — `requirements.txt` (جذر) مُنقّى إلى 9 اعتماديات مثبتة، `backend/requirements.txt` متوافق.
- **R-104**: توحيد المنافذ — `PORT` (افتراضي 8000)، `.replit` 5000→8000، `fly.toml` 8080.
- **R-105**: `Dockerfile` أُصلح (`WORKDIR /app/backend`, `PYTHONPATH`, `uvicorn app:app` على 8080)؛ `main.py --test` يمر.
- **R-106**: `/api-key` محمي — يتطلب `master_key` (403 بدون، 200 مع).
- **R-107**: CORS مقيد — يقرأ `CORS_ORIGINS` من الإعدادات.
- **R-108**: `/orchestrator/cycle` محمي — يتطلب `api_key` في الجسم (401 بدون، 200 مع).
- **R-109**: أخطاء وقت التشغيل — إصلاح `watcher.py` (مسافة بادئة + استيراد Callable)، `append_event` يقبل str/EventType، `iterate_events` بمعامل limit، `FILE_MAP`، `_load_last_hash` يقرأ السجل، حفظ حالة ذري (temp+rename)، حماية القفل القديم (STALE_AFTER_SECONDS=30)، عدادات blob مخزنة، تحسين `_blob_path`، تخزين مؤقت TTL لـ `verify_integrity`/`watcher.get_status`/`drives.get_drive_status`، إصلاح خطأ `EventType`. **الدورة تكتمل بصفر أخطاء (~37 ثانية)**.
- **R-110**: أرشفة الملفات الجذرية الشاذة (Fff, IDs.py, encryption.py, investigation.py, memory/defense المكرر, infrastructure/ الفارغ, attached_assets/) → `archive/root_strays/`. `Mr.py` أُبقي دون لمس (قرار D-005).
- **R-111**: قفل guardian موثق كآلية أمان مقصودة — أُبقي (قرار D-006).
- **R-112**: `.gitignore` أُنشئ — `__pycache__` وبيانات وقت التشغيل لم تعد تُتتبع.

### أُضيف
- `archive/root_strays/` — الملفات المؤرشفة (قابلة للاسترجاع).
- `.gitignore` — منع تتبع الملفات المؤقتة.

### قرارات
- **D-005**: أرشفة الملفات الجذرية الشاذة، إبقاء `Mr.py`.
- **D-006**: إبقاء قفل guardian كحالة أمان.
- **D-007**: تخزين مؤقت TTL لمسار الاستبطان.

### ملاحظات
- دورة الوعي تكتمل لكن وقتها متغير (~37-68 ثانية) بسبب 41 خيطاً خلفياً يتنافس على القفل — مؤجل إلى M2/M3.

## [M2] — 2026-10-12 — Consistency (R-201..R-203)

### أُنجز
- **R-201**: تنظيف بنية الجذر — أُزيلت بقايا المجلدات الفارغة (memory/defense, cache/, experiments/, exports/)، أُرشف `dockerignore` المكرر (محتوى مختلف عن `.dockerignore`). ARCHITECTURE.md حُدث.
- **R-202**: توحيد التسمية — القرار D-008: الاسم الرسمي **Sovereign AI (SOVRA)**. README حُدث (العنوان + شجرة البنية المكسورة أُصلحت).
- **R-203**: نمط الكود الموحد — موثق في QUALITY.md (Python: 4 مسافات، استيرادات مطلقة، docstrings، ≤100 حرف؛ JS: 4 مسافات، مفاتيح مقتبسة).

### قرارات
- **D-008**: توحيد التسمية على SOVRA.
- **D-009**: تنظيف بنية الجذر.

### ملاحظات
- التوحيد الكامل للتسمية في الكود (backend/frontend) مؤجل — لا تغيير وظيفي.

## [M3] — 2026-10-12 — Architecture (R-301..R-303)

### أُنجز
- **R-302**: القرار D-010 — إعادة التوصيف بصدق: النظام rule-based، لا LLM. DOMAIN.md، PROJECT_CHARTER.md، OPEN_QUESTIONS (س-9) حُدثت.
- **R-303**: أُرشف `backend/biological/__init__.py` المكسور (يستورد 11 وحدة غير موجودة) → `archive/root_strays/backend_biological_init_duplicate.py`. النواة تستخدم `memory.biological` (يعمل).

### أُنجز لاحقاً
- **R-301**: دمج NexusCore في النواة (قرار D-012) — `orchestrator._load_nexus()` يحمّل 46 مكوّناً فرعياً، `/components/nexus` يعمل، `/health` سليم.
- **R-401**: 15 اختباراً أساسياً (tests/) — إقلاع + API + صياغة. كشف خطأ `status` في `/sovereign/command` (D-013).
- **R-402**: CI/CD (GitHub Actions) + بوابة الدفعة الذرية.
- **R-403**: توثيق حي (Swagger/ReDoc/OpenAPI) + API.md محدثة.

### قرارات
- **D-010**: إعادة التوصيف بصدق — لا LLM الآن.
- **D-011**: أرشفة backend/biological المكسور.
- **D-012**: دمج NexusCore في النواة.
- **D-013**: إصلاح خطأ `status` (تظليل متغير) في `/sovereign/command` — كشفه R-401.
- كل الأخطاء المكتشفة موثقة في PROJECT_STATE.md و RISKS.md، وتُعالج في M1.


## [M5] — 2026-10-13 — Delivery (R-501/R-502)

### أُنجز
- **R-501**: QA متصفحياً ناجح (`issue_count: 0`): أُصلحت تصريحات JavaScript المكررة (`registerWithRegistry`, `btnWsConnect`, `btnWsDisconnect`, `wsStatusChip`)؛ أُضيفت mounts للمجلدَين `themes/` و`assets/`؛ وأُلغي طلب `/api-key` غير الموثق تلقائياً من الواجهة مع إبقاء الحماية؛ أُضيف `themes/dark.css` و`assets/logo.svg`.
- **R-502**: أُضيف `GZipMiddleware` للاستجابات الأكبر من 1,024 بايت. الصفحة الرئيسية: 35,240 → 4,727 بايت مع gzip (86.6% خفض).

### التحقق
- `python -m pytest tests/ -q`: **15 passed**.
- Browser QA: لا أخطاء console، لا طلبات فاشلة، لا أخطاء page.
- قياسات warm: `/health` 3.71ms median، `/status` 1.34ms، `/components/nexus` 1.31ms.


## [M6] — 2026-10-13 — Continuous Improvement (R-601)

- أُجريت مراجعة دورية لحالات الخارطة وصُححت العدادات: 26 منجزاً، لا بنود قيد التنفيذ أو مقترحة، وبند واحد محجوب.
- أُعيد تصنيف R-003 إلى `blocked` لأن `git push origin main` فشل بمصادقة GitHub؛ لا تُحتسب الدفعة منشورة دون تحقق remote.
- أُضيفت قاعدة مراجعة دورية إلى `GOVERNANCE.md` وسُجل القرار D-014.


### M6 follow-up — إغلاق R-003

- أُغلقت حالة النشر بعد نجاح `git push origin main`.
- تم التحقق من أن `origin/main` و`HEAD` كلاهما عند `8c495cd`، مع تطابق كامل (`ahead/behind: 0/0`).
- أصبحت خارطة الطريق بلا بنود `blocked` أو `in_progress` أو `proposed`.


## [M6] — R-602 — 2026-10-13 — Secret hardening

- أزيل المفتاح السيد الافتراضي المعروف من مسار الإعداد.
- التطوير غير المهيأ يستخدم مفتاحاً عشوائياً مؤقتاً؛ الإنتاج يفشل مغلقاً دون سر.
- أضيفت اختبارات انحدار للتأكد من العشوائية ومنع التشغيل الإنتاجي غير المهيأ.
- أُغلق RK-03 وسُجل القرار D-015.


## [M6] — R-603 — 2026-10-13 — Chat rate limiting

- فُعّل `MAX_USER_MESSAGES_PER_MINUTE` على `POST /chat` بمحدد انزلاقي bounded لكل IP مباشر؛ الحد الافتراضي 30/60 ثانية.
- الطلبات الزائدة تعيد 429 مع `Retry-After`؛ لا يتم الوثوق بـ`X-Forwarded-For` افتراضياً.
- أضيفت 6 اختبارات؛ `pytest`: 23 passed.
- الحد محلي لكل عملية، وليس موزعاً بين workers/replicas (D-016).
- صححت المراجعة توثيق API والأمن والمخاطر والجودة والتشغيل وحالة المشروع.


## [M6] — R-604 — 2026-10-13 — Identity seal integrity

- **التحقيق**: إنذار `❌ ختم الهوية تالف: الأنماط الأصلية تغيرت!` كان انحداراً حقيقياً في الختم نفسه، بثلاثة أسباب جذرية:
  1. `create_seal` وقّع بطابع زمني مختلف عن `created_at` المخزن — ففشل التحقق من التوقيع دائماً.
  2. بصمة الأنماط حُسبت من الاحتمالات المتغيرة كل دقيقة — فالتطور الطبيعي يُعتبر تلاعباً.
  3. `verify_seal` قارن `core_hash` الثابت بـ`_last_hash` الحي الذي يتغير مع كل حدث.
- **الإصلاح**: `create_seal` (v4) بطابع زمني موحد وبصمة قوالب أنماط ثابتة؛ `verify_seal` يتحقق من التوقيع من الحقول المخزنة ويفحص سلامة سلسلة الذاكرة؛ `_load_seal` يهاجر الأختام القديمة (v3→v4) تلقائياً.
- أضيفت 7 اختبارات (`tests/test_identity_seal.py`)؛ `pytest`: 30 passed — لا إنذارات `ختم الهوية تالف`.
- أُغلق RK-08 وسُجل القرار D-017.

## [M6] — R-605 — 2026-10-13 — Untrack runtime data files

- **القرار المؤجل من R-112**: 2233 ملف بيانات وقت تشغيل (8.8MB) كانت مُتتبَّعة في git رغم `.gitignore` — تُنشأ تلقائياً وتُلوّث شجرة العمل في كل تشغيل اختبار.
- **الإجراء**: `git rm -r --cached data/` — إزالة من الفهرس مع إبقاء الملفات على القرص.
- **التحقق**: `git ls-files data/` = 0؛ `git status` نظيف بعد `pytest`؛ كل ملف يطابق `.gitignore`.

## [M6] — R-606 — 2026-10-13 — Orchestrator cycle performance

- **التحقيق**: دورة المنسق ~11 ثانية؛ عنق الزجاجة في `_analyze_future`/`sense_state` (41.9 ثانية) لأن كل `get_*_status()` يُعيد تشغيل دورة كاملة (يقرأ آلاف blobs) وتُستدعى بشكل متكرر داخل دورة المنسق الواحدة.
- **أُصلح**:
  - تخزين مؤقت قصير (TTL 2 ثانية، نمط `drives.py`) على 12 getter باهظ الثمن: `get_prediction_status`, `get_risk_status`, `get_scenario_status`, `get_simulation_status`, `get_controller_status` (sovereign), `get_will_status`, `get_alignment_status`, `get_directives_status`, `get_introspection_status`, `get_self_status`, `get_archetype_status`, `get_identity_status`.
  - خطأ عودية لا نهائية في `get_early_warnings_list` (تعريف مكرر — الأخير يستدعي نفسه) — أُزيل التعريف العودي.
  - ذاكرة `verify_integrity` كانت تُبطل في كل إضافة حدث → فحص كامل للسجل في كل استدعاء؛ أُضيف إبطال صريح عند الإضافة + TTL 60 ثانية.
  - `_load_index` كان يشير إلى `self.index_file` غير الموجود — أُصلح إلى `self.index.index_file`؛ أُضيف `_rebuild_index` (إعادة بناء الفهرس من السجل) واستُخدم في `reset()`.
  - ترتيب `_save_meta` بعد `index.add_event` — عدّاد الأحداث في meta أصبح متسقاً مع الفهرس.
  - `iterate_events` — مسار ذيل سريع لـ `reverse+limit` (يتجنب قراءة السجل كاملاً في كل استدعاء)؛ `views._background_integration` محدود بـ 1000 حدث حديث.
  - سجل تالف (رأس مقطوع + مفاتيح توقيع مختلطة من تشغيلات اختبار) — أُصلح عبر `reset()` مع نسخة احتياطية `.bak` أولاً؛ `verify_integrity` = VERIFIED.
- **النتيجة**: زمن دورة المنسق ~0.25 ثانية (من ~11 ثانية، ~44×)؛ صفر فشل `prev_hash غير متطابق` في التشغيل.
- أضيفت 5 اختبارات (`tests/test_performance_r606.py`)؛ `pytest`: 35 passed.
- أُغلق RK-10 وسُجل القرار D-019.


## [M6] — R-607 — 2026-10-13 — Revive dead frontend code

- **التحقيق**: 43 ملف JS (26,880 سطراً) على القرص غير محمّلة في index.html — تشكّل نظام "Sovereign Runtime" الفرعي الكامل (محرك الإدراك، النواة السيادية، إدارة الجلسات، حوكمة التنفيذ، العدالة، قياس التدفق، الوعي الذاتي، الحفظ الذاتي، تطور الحضارة، الضغط، التوجيه، الجدولة، التتبع، السببية). النواة (runtime-kernel, runtime-orchestrator-ai, runtime-consciousness-core, runtime-init) محمّلة بالفعل؛ الوحدات الميتة صُممت للتسجيل فيها عبر `window.SOVEREIGN` (السجل الموحد، runtime-unified-registry.js).
- **أُضيف**: 43 وسم `<script defer>` في index.html بترتيب اعتماديات طوبولوجي محسوب (الطبقة الأساسية أولاً: system-state, mode-manager, flow-telemetry, fairness-engine, execution-domains, session-*, access-control, context, contracts, causality-graph, cognitive-memory, sandboxes, zones, timeline, trace — ثم المحركات الأعلى: cognition-engine, cognitive-orchestrator, identity-core, meta-intelligence, self-awareness, sovereign-core, layer-manager, structural-integrity, evolution-governor, autonomous-preservation, civilization-registry, pressure-governor, domain-router, domain-scheduler, backpressure-engine, adaptive-scheduler, execution-scheduler, queue-intelligence).
- **أُصلح** (3 أخطاء حقيقية في الكود الميت لم تُختبر أبداً):
  - `runtime-cognition-engine.js`: دالة `startCognitiveLoop()` مفقودة — أُضيفت (حلقة معرفية كل 3 ثوانٍ تستدعي `evaluateRuntime()`، مع تنظيف في `destroy()`).
  - `runtime-sovereign-core.js`: دالة `registerLaw()` مفقودة — أُضيفت (تسجيل قانون في `this.laws` Map مع أولوية وثبات).
  - `runtime-autonomous-preservation.js`: خطأ مطبعي `self.selfQuarantine` → `this.selfQuarantine` (كان يقرأ `this.selfQuarantine.enabled` على undefined).
- **التحقق**: اختبار تحميل jsdom — **122/122 ملف تُحمَّل، 0 فشل**؛ **40/40 وحدة ميتة سُجّلت** في `window.SOVEREIGN` (52 نظاماً إجمالاً، من 17 سابقاً)؛ `node --check` يمر على الملفات الثلاثة المُصلحة؛ `python -m pytest tests/ -q`: **35 passed**.
- أُغلق RF-03 وS-6 وسُجل القرار D-020.


## [M6] — R-608 — 2026-10-13 — Revive safety layer (full)

- **التحقيق** (أمر السيد: "نفذ احياء طبقة الامان بكل مكوناتها لابد أن تكون ضمن المشروع، بروتوكول الموت الذاتي يبقى محمي بالقرار، احذف أحد النسخ المكرره الأصغر، وابق الأكبر، وأحيها"): 3 مكونات ميتة في الخلفية — `backend/safety.py` (SafetyGuard، 520 سطراً، غير مستورد)، `nexus/api_gateway/` (NexusRouter + RateLimiter، غير مستورد)، `memory/compress.py` (SovereignCompressor، مستورد فقط عبر `memory/__init__.py` غير المستورد). اكتشاف إضافي: طريقة `reset` في `compress.py` كانت على العمود 0 (خارج الفئة) — ابتلعت `__init__` و`compress` و`get_stats` كدوال متداخلة، فكانت الفئة بلا أي طرق وتتعطل عند أي استخدام.
- **أُحيي**:
  - `safety.py`: `SafetyGuard` مربوط في `/chat` (فحص كل رسالة قبل المعالجة — الرسائل الخطيرة تُحجب برد أمني `status: blocked`)، في WebSocket (`sir_command` + `chat_message`)، وفي `/sovereign/command` و`/sovereign/reset` (الأوامر الممنوعة تماماً تُحجب حتى للسيد). نقطتان جديدتان: `/security/status` و`/security/log`.
  - `api_gateway`: `NexusRouter` مربوط في التطبيق — 6 نقاط جديدة: `/nexus/status`, `/nexus/analyze/text`, `/nexus/ingest`, `/nexus/health`, `/nexus/budget/analyze`, `/nexus/recommendations`. إجمالي المسارات: 37 → 45.
  - `compress.py`: أُصلح الخطأ البنيوي (إزاحة `reset` إلى داخل الفئة) — الفئة كاملة الآن (6 أبعاد ضغط + `compress_from_core` + `get_stats`). مربوط في `orchestrator._update_memory` — ضغط دوري للسجل السيادي كل 50 دورة.
- **حُذف** (النسخ المكررة الأصغر — أمر السيد): `archive/root_strays/memory_defense_polymorphic_duplicate.py` (756 سطراً — v3.0.0 أقدم من الحية v4.0.0) و`archive/root_strays/backend_biological_init_duplicate.py` (25 سطراً). أُبقي الأكبر: النسخة الحية `backend/memory/defense/polymorphic.py` (798 سطراً) + النسخة الاحتياطية الكبرى في guardian (4.5MB، 204 ملفات).
- **التحقق**: `python -m pytest tests/ -q`: **44 passed** (35 + 9 جديدة في `tests/test_safety_layer.py`)؛ رسالة خطيرة في `/chat` → `status: blocked`؛ `/security/status` → `safety_guard.active: True`؛ `/nexus/health` → `200 healthy`؛ ضغط 3 أحداث → وعي 16 بايت.
- أُغلق RK-04 وسُجل القرار D-021.

## [M6] — R-609 — 2026-10-14 — Comprehensive full-repo audit

- **التحقيق** (أمر السيد: "اريد ان تختبر المشروع كماهو مصمم له سيادي... تختبر كل ملف كل مجلد كل مسمى... هل كل شئ يعمل، هل كل شي مترابط، هل هناك أخطاء أو نقص، هل هناك أخطاء نحويه أو غيرها، ثم اصلح كل شي وادفع كل شي إلى المستودع"): تدقيق شامل لكل ملف ومجلد واسم في المستودع — 245 JS + 215 Python + 17 وثيقة + كل المسارات والمكونات والمراجع.
- **أُصلح (6 أخطاء حقيقية)**:
  1. `/components/predictive` → 500: `PredictiveController.get_controller_status()` غير موجودة (الموجودة: `get_stats`, `get_mode`, `get_last_decision`) — استُبدلت بدالة تجميع.
  2. `orchestrator._update_memory`: `ingest(..., importance=0.5)` — التوقيع `intensity=0.5` → TypeError "فشل استدعاء ingest" كل دورة.
  3. نفس الاستدعاء: 3 وسائط موضعية (`"system", f"cycle_{id}", str(record)`) لكن `ingest(user_id, text)` وسيطان — حُذفت الوسيطة الثالثة.
  4. `PredictiveEngine.reset()`: `self._load_index()` غير موجودة — استُبدلت بـ `_load_state()` + `_load_forecasts()`.
  5. `PredictiveEngine.reset()`: `_now_iso()` غير معرّفة — استُبدلت بـ `time.time()`.
  6. WebSocket `/ws/{user_id}` (مسار المحادثة الحي في الواجهة) لم يكن مفحوصاً بطبقة الأمان — أُضيف فحص `enforce_input_safety` (الرسائل الخطيرة → `blocked=True` + `cycle_id="safety-block"`).
- **فجوة أمان**: `pycryptodome` لم يكن في `requirements.txt` — التشفير كان يتراجع إلى XOR-DEV. أُضيف `pycryptodome==3.24.1` — تحقق: AES-256-CBC يعمل (encrypt/decrypt round-trip).
- **نظافة**: `data/security_log.json` و`data/approval_cache.json` (بيانات وقت تشغيل) أُضيفا إلى `.gitignore`.
- **التحقق**: `python -m pytest tests/ -q`: **48 passed** (44 + 4 جديدة)؛ كل نقاط `/components/*` و`/security/*` و`/nexus/*` تعيد 200؛ WebSocket خطير → `blocked=True`؛ كل 54 وحدة backend + 51 وحدة nexus + 4 وحدات guardian تُستورد بنجاح؛ `main.py --test` يمر؛ لا أخطاء نحوية عربية؛ لا TODO/FIXME.
- سُجل القرار D-022.

---

## [ROADMAP_V2] — 2026-10-16 — المرحلة 1 (KeyRing): الحالة على الكود + بدء المرحلة 6 (سجل إجراءات الوكيل)

### أُضيف
- `forensics/PHASE1_STATUS.md`: تقرير حالة المرحلة ١ على الكود (كل المكونات موجودة وكاملة — 33 اختبارًا ناجحًا؛ لا ناقص ولا مكسور).
- `forensics/agent_ledger.jsonl`: سجل إجراءات الوكيل (المرحلة ٦) — سطر لكل إجراء من هذه الجولة وما بعدها (ts/phase/action/files_touched/before_hash/after_hash/reason/verified_by).

### تحقق
- `python -m pytest tests/test_sovereign_keys.py tests/test_key_selection_rotation.py tests/test_return_none_security.py tests/test_ledger_anchor.py tests/test_ledger_verify_endpoint.py -q` → **33 passed**.

---

## [ROADMAP_V2] — 2026-10-16 — المرحلة 2 (مرساة اليدجر): الحالة على الكود

### أُضيف
- `forensics/PHASE2_STATUS.md`: تقرير حالة المرحلة ٢ على الكود (compute_merkle_root + anchor_batch + verify_anchor + `/ledger/verify` — كلها موجودة وكاملة؛ المراسي الفعلية تغطي 0–116909).
- تحديث `forensics/agent_ledger.jsonl`: تثبيت after_hash للإدخال الأول (42446ac) + إدخال المرحلة ٢.

### تحقق
- 33 اختبارًا ناجحًا (منها كشف تغيير البايت الواحد وحقول تقرير `/ledger/verify`).
- عائق بيانات موثق: `ledger.jsonl` الخام غائب عن clone — لا يعطل الكود.

---

## [PHASE0] — 2026-10-16 — تصويح رقمي: 50 لا 33 + حارس نزاهة للأرقام الموثقة

### أُصلح
- **ادعاء غير دقيق من سلف (اكتُشف في مرحلة صفر)**: تقارير `PHASE1_STATUS.md` و`PHASE2_STATUS.md` (وكل توثيق تبعها) أدّعت «33 passed» للأمر الموثق (الملفات الخمسة) بينما التشغيل الفعلي يعطي **50 passed** — أُثبت على الالتزامين `42446ac` و`dfd5a16` نفسيهما (توزيع الملفات: 11+5+17+12+5). صُححت كل المواضع: التقريران + `docs/PROJECT_STATE.md` + `docs/ROADMAP.md` + هذا السجل (الإدخالات التاريخية أعلاه أبقيت كما هي — هذا الإدخال يصححها صراحة).
- جوهر الادعاء (كل المكونات موجودة وكاملة وعاملة) صحيح ومُعاد التحقق منه — الرقم فقط كان خطأ.

### أُضيف
- `tests/invariants/test_phase_status_numbers_match_reality.py`: حارس نزاهة — كل «N passed» موثق في `forensics/PHASE*_STATUS.md` يجب أن يطابق تشغيل الأمر الموثق نفسه. RED مثبت فعليًا قبل التصويب (فشل: «المُعلن 33 لا يطابق الفعلي 50»)، GREEN بعده.
- `forensics/PHASE0_ROUND_2026-10-16.md`: سجل جولة مرحلة الصفر الكاملة (فحص الحالة + الاكتشاف + الإثبات + دورة التحقق النهائية).
- قيد في `forensics/DELETED_LINES_AUDIT.md` لهذا الالتزام + إدخال في `forensics/agent_ledger.jsonl`.

### تحقق
- الحزمة الكاملة بعد إضافة الحارس (على شجرة التصويح قبل الالتزام، Python 3.11.17): `timeout 600 python -m pytest tests/ backend/tests/ -q -m "not operational"` → **430 passed / 0 failed / exit=0** (424 + 6 اختبارات الحارس)؛ `--collect-only` بنطاق ومرشّح الأمر نفسهما → **431 collected / 1 deselected**.
- دورة التحقق النهائية قبل التصويح (على `dfd5a16`): `verify.sh --full` نجح — تطابق ثلاثي كامل 424/0/0 (محلي + CI 38836206439 + clone نظيف مثبت على SHA) — السجل الكامل: `forensics/verify_full_dfd5a16.log` + الأثر `forensics/pytest_results_dfd5a16.xml`.

---

## [PHASE0-2] — 2026-10-16 — استكمال مطالب المراجعة للتسليم

### أُصلح
- تقييد مصادقات التصويح في التقريرين لما فُحص فعليًا: «ما تحقق منه فعليًا» صراحةً في كل تقرير (الملفات + الأمر الموثق = 50؛ المراسي غير قابلة للمطابقة ضد الأحداث الأصلية الغائبة عن clone).
- 4 روابط معطوبة لـIssue #8 في `forensics/` (اسم مستودع خاطئ `reeverero-tech` → `reeveero-tech`): OWNER_DECISIONS / THIS_ROUND_VIOLATIONS / CONTRACT_EXCEPTION_1 / FINAL_CLOSURE_R-682.

### أُضيف
- `forensics/verify_full_dfd5a16.log` في المستودع فعليًا (إضافة مستهدفة `git add -f` — قاعدة `*.log` العامة لم تُعطل؛ كان مشارًا إليه في الالتزام السابق دون أن يكون متاحًا).
- جرد ادعاءات `forensics/` المفتوحة (PHASE0_ROUND قسم 6): لا ادعاء «مغلق» زائف آخر عدا 33 (صُحح)؛ المفتوح فعليًا: قرار Ed25519 المعلق، عائق البيانات، بند القبول 1 (غير قابل للتحقق داخل clone)، وقائمة القبول النهائية غير معلَّمة.
- التحقق من Issue #8 من أصله (gh): موجود بتوقيع المالك؛ قرارا المخالفات السبع ونطاق الادعاء موثقان داخل المستودع فقط (لا أصل خارجي قابل للفحص لهما).
- إفصاح فجوة قياس بصمات الشجرة للتعديلات الأولى + بدء القياس الفعلي (before_tree للاختيارات اللاحقة موثق في agent_ledger ورسالة الالتزام).

### تحقق
- الحزمة الكاملة على شجرة هذا الالتزام (Python 3.11.17): 430 passed / 0 failed / exit=0 — البوابة خضراء قبل الالتزام (تشغيل فعلي على الشجرة النهائية المُجهَّزة).
- دورة التسليم الكاملة (الدفع + CI فعلي + الأمر الخارجي الحرفي من clone نظيف مستقل على الالتزام النهائي) — نتيجتها موثقة في الالتزام اللاحق لها مباشرة.

---

## [PHASE0-3] — 2026-10-16 — إصلاح عدّ الحارس مع المرشحات + سحب ادعاءات غير مُثبتة

### أُصلح
- **حارس النزاهة — عدّ المرشحات:** `_collect` كان يقرأ المقام من صيغة «N/M tests collected (K deselected)» (يعيد 16 بدل 6 مع `-k`) — صُحح ليعدّ المُختار (البسط) + اختبار سلوكي حقيقي بمسار `-k` (تشغيل فعلي: 6/16).
- **سحب ادعاءات غير مُثبتة من سجل الجولة:** «7 من 8 مثبتة» (الدرجة موثقة ولم تُعِد حسابها؛ «سطر لكل إجراء» غير مُثبت) و«لا ادعاء مغلق زائف آخر» — استُبدلت بجرد معلن الحدود: لكل بند موضعه وآخر قرار نافذ وما فُحص فعليًا ونتيجته، مع نص صريح أن الجرد ليس مكتملًا.
- **ادعاء إثبات مستقبلي:** سجل الجولة قال إن نتيجة الأمر الخارجي «موثقة في الالتزام نفسه» قبل تنفيذه — صُحح: تشغيلات ما بعد الدفع تُرفق بأثر تحقق مستقل (SHA + رمز خروج) ولا تُنسب إلى التزامات لا تحتويها.
- **مصادقات مطلقة في تقريري المرحلتين:** «لا ناقص ولا مكسور» استُبدلت بنتيجة محددة (الملفات المطلوبة موجودة + الأمر الموثق 50 passed؛ المرحلة 2: المطابقة ضد الأصل لم تُنفّذ لغيابه).

### تحقق
- الحارس: 7 اختبارات خضراء (6 سابقة + عدّ المُختار الجديد). الحزمة الكاملة على شجرة هذا الالتزام: 430 passed / 0 failed / exit=0 (تشغيل فعلي قبل الالتزام).

---

## [PHASE0-4] — 2026-10-16 — تصويب رقمي داخلي (430→431) + استكمال الجرد + إفصاح فجوات القياس

### أُصلح
- **تصويح رقمي:** إدخال [PHASE0-3] أعلاه قال «430 passed» للحزمة بعد إصلاح الحارس — الصحيح **431** (430 + اختبار عدّ المرشحات الجديد). رسالة الالتزام 831c61f كانت صحيحة؛ هذا القيد يصحح إدخال السجل صراحة. (كذلك إدخال agent_ledger المقابل صُحح بإدخال لاحق — السجل لا يُعاد كتابته.)
- إفصاح فجوات قياس بصمة الشجرة للجولة الثالثة (لا before_tree قبل تعديلاتها + إعادة استخدام وقت سابق في الإدخال) — لا يوصف امتثال لم يحدث.

### أُضيف
- استكمال جرد الادعاءات: فحص الملفات المتبقية (OPERATIONAL_TESTS «ما يبقى مفتوحًا» — بنوده الثلاثة متجاوزة بقرار المالك/إصلاحات R-682 ولا أثر للأخطاء في خرج التحقق الحالي؛ SECURITY_FIXES_R682 — 9/9 CLOSED؛ RETURN_NONE_AUDIT بمصدريه — متجاوز بالتدقيق اللاحق؛ key_state_duality — محلول باختبار ترجمة؛ clean_build_skips — تاريخي (الحالي صفر skips)؛ SHA_RECONCILIATION — محلول؛ AWARENESS_561 — منفذ؛ rotation/ — أثر تاريخي). الجدول الكامل في PHASE0_ROUND قسم 6.
- سجل تحقق مستقل خارج المستودع للأوامر الخارجية (SHA كامل + الأمر + رمز الخروج + معرّف CI) — يُرفق مع التسليم لا يُنسب للالتزامات.

### تحقق
- الحزمة الكاملة على شجرة هذا الالتزام: تشغيل فعلي قبل الالتزام (الرقم في رسالة الالتزام من التشغيل الفعلي نفسه).

---

## [PHASE0-5] — 2026-10-16 — تصحيح نسب قرار النطاق + أدلة الجرد الكاملة + أول قياس حي قبل التعديل

### أُصلح
- **تصحيح نسب (بناء على اعتراض المراجعة):** قرار نطاق الادعاء التشغيلي ليس من Issue #8 (بنوده تخص استثناء الحذوفات والالتزامات الـ212) — يُوصف بدقة: قرار منقول داخل المستودع، أصله غير متحقق. سحبت المصادقة على تجاوز مطلب إثبات التدوير بذلك القرار.
- سحب عبارة «القياس الحي يبدأ من هذه الدفعة» السابقة — الجولة الرابعة عدّلت قبل قياسها (فجوة موثقة في PHASE0_ROUND قسم 7).

### أُضيف
- أدلة الجرد الكاملة (بدل الاقتطاف): قراءة سجلي rotation/ كاملين (تدوير فعلي 2026-10-14: بصمة قبل `c0081032` وبعد `96265b6e`)، وقسم «ما يبقى مفتوحًا» في OPERATIONAL_TESTS كاملًا مع ربط بند الخيوط/KeyRing بتوكيدات الاختبارات الفعلية: `test_lifecycle_real_threads_stop_and_join` (يؤكد `still_alive_after == 0`) و`test_stopper_failure_collected_and_others_still_stopped` (إخفاق الموقفة يُجمع ويُظهر) و`test_writer_without_keyring_rejects_append` — وخريطة مواقع return-None (25 موقعًا: 9 عالية بوسم [SECURITY] + 27 اختبارًا سلوكيًا للمواقع منخفضة الخطورة — لا إسناد عام للـ25 في الـ17).
- **أول قياس حي فعلي قبل التعديل:** الشجرة نظيفة + `tree(daa05a6)=fe6013e...` قيس 04:37:26Z قبل أي تعديل في هذه الدفعة (موثق في إدخال agent_ledger المقابل).

### تحقق
- الحزمة الكاملة على شجرة هذا الالتزام: تشغيل فعلي قبل الالتزام (الرقم في رسالة الالتزام من التشغيل الفعلي نفسه).
