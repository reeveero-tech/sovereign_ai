# CHANGELOG.md — سجل التغييرات

> كل تغيير يُسجل هنا (قاعدة الدفعة الذرية).
> آخر تحديث: 2026-10-12 (الدفعة M3)

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
