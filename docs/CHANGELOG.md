# CHANGELOG.md — سجل التغييرات

> كل تغيير يُسجل هنا (قاعدة الدفعة الذرية).
> آخر تحديث: 2026-10-12 (الدفعة M2)

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
- كل الأخطاء المكتشفة موثقة في PROJECT_STATE.md و RISKS.md، وتُعالج في M1.
