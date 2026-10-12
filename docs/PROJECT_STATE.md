# PROJECT_STATE.md — حالة المشروع

> أين نحن الآن؟ هذه الوثيقة تُحدَّث في **كل دفعة** (قاعدة الدفعة الذرية).
> آخر تحديث: 2026-10-12 (الدفعة M0)

---

## 1) ملخص الحالة

| البعد | الحالة |
|---|---|
| المرحلة | **M0 — Baseline Audit** (قيد الإنجاز، هذه الدفعة) |
| البناء | ✅ الخادم يُقلع ويستجيب (`/health`, `/status`, `/chat`, `/api/*`) |
| الاختبارات | ❌ لا توجد أي اختبارات |
| CI/CD | ❌ لا يوجد (لا `.github/`) |
| التوثيق | ❌ لم يكن موجوداً — أُنشئ في هذه الدفعة |
| الأمان | 🔴 مخاطر حرجة مفتوحة (راجع `RISKS.md`) |
| الحالة العامة | **تجريبي / غير مستقر / غير موثق** — يعمل جزئياً لكنه هش |

---

## 2) ما الذي يعمل (مُتحقق منه في هذه الدفعة)

- ✅ الخادم يُقلع: `cd backend && uvicorn app:app` → يعمل على المنفذ.
- ✅ `/health` → `{"status":"healthy","version":"4.0.0"}` مع 23 مكوّناً كلها `healthy`.
- ✅ `/status` → `operational`، orchestrator نشط.
- ✅ `/chat` → يستجيب بقرار (مثال: `تم تنفيذ القرار: monitor`).
- ✅ `/api/run`, `/api/state`, `/api/components`, `/api/mode`, `/api/history` → تعمل.
- ✅ `/orchestrator/cycle` → يعمل (بدون مصادقة — خطر، راجع RISKS).
- ✅ `nexus.main.initialize_nexus` → يُستورد بنجاح (لكنه غير موصول بالنواة).
- ✅ 135 ملف Python في backend+nexus+memory: **كلها سليمة نحوياً** (py_compile).
- ✅ 122 ملف JS في frontend: **120 سليمة**، 2 بها أخطاء صياغة (راجع أدناه).

---

## 3) ما الذي لا يعمل / أخطاء مُتحقق منها

### أخطاء وقت التشغيل (تظهر في سجل الخادم أثناء كل دورة)
- ❌ `'MemoryWatcher' object has no attribute 'get_status'` — يتكرر في تيار الوعي (consciousness.field / awareness).
- ❌ `'str' object has no attribute 'value'` — في attention_engine و memory.defense.polymorphic.
- ❌ `السجل غير موجود` (memory.core) — سجل الذاكرة غير مهيأ.

### أخطاء صياغة في الواجهة (تمنع تحميل الملفين)
- ❌ `frontend/js/system/system-thought-nebula.js` — **ملف ناقص/مقطوع** (ينتهي فجأة عند `dreamNebula: {`، 585 سطراً، "Unexpected end of input"). وهو **محمّل** في index.html.
- ❌ `frontend/js/system/system-runtime-consciousness-loop.js` — خطأ صياغة: `owner-related: 'high'` (واصلة في اسم مفتاح غير مقتبس) عند السطر 328. وهو **محمّل** في index.html.

### مشاكل تشغيل/نشر
- ❌ `python main.py` من جذر المستودع يفشل: `No module named 'orchestrator'` (يجب تشغيله من داخل backend).
- ❌ `Dockerfile` يستخدم `uvicorn backend.app:app` لكن `backend/app.py` يستورد `from orchestrator import ...` (مسار نسبي) → **فشل الاستيراد** عند التشغيل من الجذر. (تحقق: `ModuleNotFoundError: No module named 'orchestrator'`).
- ❌ تعارض منافذ: `start.sh`=5000، `fly.toml`=8080، `Dockerfile`=8080، `app.py` (عند التشغيل المباشر)=8000، `.replit`=5000→80.
- ❌ تعارض اعتماديات: `requirements.txt` (جذر) و `backend/requirements.txt` يحددان **إصدارات مختلفة** (fastapi 0.115.0 vs 0.104.1، pydantic 2.9.0 vs 2.4.2، إلخ). الجذر أيضاً يحتوي إدخالات مكررة (مثبتة + غير مثبتة).

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
│   └── biological/     # ⚠️ مجلد فارغ تقريباً (فقط __init__.py يستورد ملفات غير موجودة → كسر)
├── frontend/         # واجهة عربية RTL (index.html + 122 ملف JS + css + ui)
├── nexus/            # منصة منفصلة (NexusCore) — 71 ملف، غير موصولة بالنواة
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

| الملف | الحجم | الحقيقة | الحالة |
|---|---|---|---|
| `Fff` | 28KB | نص تعليمات AI (ليس كوداً) | غير مستورد — قرار مفتوح |
| `IDs.py` | 61KB | كود TypeScript/JS (رغم امتداد .py) — "غرفة التحري" | غير مستورد — قرار مفتوح |
| `encryption.py` | 74KB | "موسوعة التشفير" Python | غير مستورد — قرار مفتوح |
| `investigation.py` | 103KB | نظام CIKMS استخباراتي (أسماء عربية) | غير مستورد — قرار مفتوح |
| `Mr.py` | 44KB | "محرك الولاء" — يحتوي بروتوكول موت/كشف عبث (sys.exit) | غير مستورد — قرار مفتوح |

> كلها **كود ميت** حالياً (لا شيء يستوردها). راجع `OPEN_QUESTIONS.md` و `RISKS.md`.

---

## 6) المخاطر الحالية (ملخص — التفاصيل في RISKS.md)

1. 🔴 **مفتاح API مكشوف**: `/api-key` يعيد المفتاح لأي طلب بدون مصادقة. المفتاح يتولد عشوائياً عند كل إقلاع (لا يُحفظ).
2. 🔴 **CORS مفتوح**: `ALLOWED_ORIGINS = ["*"]` في الإنتاج.
3. 🔴 **مفتاح سيد افتراضي**: `config.py` يحذر من مفتاح افتراضي غير آمن.
4. 🔴 **`/orchestrator/cycle` بدون مصادقة** — يمكن لأي شخص تشغيل دورات.
5. 🟠 **Mr.py**: كود "ولاء" مع بروتوكول موت ذاتي (sys.exit) وكشف عبث — خطر تشغيلي/أمني.
6. 🟠 **guardian/SYSTEM_LOCKED.lock**: النظام "مقفل" بحدث طارئ (PROTECTED_ACTION_WITHOUT_MASTER_TOKEN) — يتطلب رمز إعادة تفعيل. هل هذا مقصود؟
7. 🟠 **لا .gitignore**: `__pycache__` وبيانات وقت التشغيل تُتتبع في git (2233 ملف بيانات).
8. 🟠 **لا اختبارات ولا CI** — أي كسر يمر دون كشف.

---

## 7) القرارات المسجلة

- **D-001**: بدء المشروع بمرحلة M0 (مسح + توثيق) دون إصلاح أي خطأ — بأمر السيد ("لا تصلح أي خطأ الآن").
- **D-002**: اعتماد قاعدة الدفعة الذرية كقاعدة حوكمة وحيدة غير قابلة للتفاوض (راجع `GOVERNANCE.md`).
- **D-003**: إنشاء مجلد `docs/` للوثائق الحاكمة (لم يكن موجوداً).

---

## 8) العوائق الحالية

- لا توجد صلاحية دفع مؤكدة للمستودع من بيئة الوكيل (المستودع عام، لكن الدفع يتطلب مصادقة). **الدفعة M0 تُسلَّم كملفات جاهزة للدمج** — راجع `OPEN_QUESTIONS.md` (س-1).
- ملف `system-thought-nebula.js` مقطوع — لا يمكن إصلاحه في هذه الدفعة (ممنوع الإصلاح الآن).

---

## 9) سجل الحالة

| التاريخ | الحالة | الدفعة |
|---|---|---|
| 2026-10-12 | M0 قيد الإنجاز — مسح مكتمل، وثائق أُنشئت | M0: baseline audit + roadmap bootstrap |
