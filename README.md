# SOVRA · Sovereign Cognitive Operating System

> الاسم الرسمي: **Sovereign AI (SOVRA)** — نظام تشغيل معرفي سيادي (قرار R-202).

هذا المشروع يمثل نواة "ذكاء سيادي" تجريبي، يعمل على:
- GitHub (للكود)
- Railway (للتشغيل)
- Google(للتخزين المشفر)
- جهاز المستخدم (للسيادة الكاملة لاحقاً)

## هيكل المشروع

```
sovereign_ai/
├── backend/          # النواة (FastAPI): app.py, orchestrator.py, api.py, config.py
│   ├── consciousness/  # الوعي
│   ├── memory/         # الذاكرة (core, biological, defense, store)
│   ├── predictive/     # التنبؤ
│   ├── simulation/     # المحاكاة
│   ├── quantum/        # الكم
│   └── sovereign/      # السيادة
├── frontend/         # الواجهة (RTL عربي)
├── docs/             # الوثائق الحاكمة (15 ملفاً)
├── guardian/         # الحارس (أمان/نسخ احتياطي)
├── archive/          # الملفات المؤرشفة
├── nexus/            # منصة منفصلة (NexusCore)
├── main.py           # نقطة تشغيل بديلة
└── data/             # بيانات وقت التشغيل (غير متتبعة)
```
## الهدف
بناء عقل سيادي:
- يتعلم
- يتطور
- يطلب إذن السيد قبل أي تعديل
- يعمل على منصات خارجية مؤقتاً
- ينتقل لاحقاً إلى تشغيل سيادي كامل

---

## 📚 الوثائق الحاكمة (docs/)

هذا المشروع يخضع لقاعدة **الدفعة الذرية**: لا يُدفع/يُدمج أي شيء دون تحديث الحالة والوثائق والخارطة في نفس الدفعة.

- [PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md) — لماذا المشروع؟
- [PROJECT_STATE.md](docs/PROJECT_STATE.md) — أين نحن الآن؟
- [ROADMAP.md](docs/ROADMAP.md) — إلى أين نذهب؟
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — كيف بُني؟
- [GOVERNANCE.md](docs/GOVERNANCE.md) — الحوكمة وقاعدة الدفعة الذرية
- [RISKS.md](docs/RISKS.md) — المخاطر
- [OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) — الأسئلة المفتوحة
- [DECISIONS.md](docs/DECISIONS.md) — القرارات المعمارية
- [API.md](docs/API.md) — الواجهات
- [DATA_MODEL.md](docs/DATA_MODEL.md) — البيانات
- [OPERATIONS.md](docs/OPERATIONS.md) — التشغيل والنشر
- [SECURITY.md](docs/SECURITY.md) — الأمان
- [QUALITY.md](docs/QUALITY.md) — الجودة والاختبارات
- [DOMAIN.md](docs/DOMAIN.md) — منطق العمل
- [CHANGELOG.md](docs/CHANGELOG.md) — سجل التغييرات
