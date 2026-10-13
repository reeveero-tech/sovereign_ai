# CHANGELOG.md — سجل التغييرات

> كل تغيير يُسجل هنا (قاعدة الدفعة الذرية).
> آخر تحديث: 2026-10-13 (الدفعة M6 — R-606)

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
