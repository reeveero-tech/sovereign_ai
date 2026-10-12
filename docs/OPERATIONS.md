# OPERATIONS.md — التشغيل والنشر

> كيف يُشغَّل المشروع ويُنشر؟ الحالة الفعلية كما رُصدت.
> آخر تحديث: 2026-10-13 (الدفعة M5)

---

## 1) التشغيل المحلي

### الطريقة الوحيدة التي تعمل حالياً
```bash
cd backend
pip install -r requirements.txt   # أو من الجذر
uvicorn app:app --host 0.0.0.0 --port 8000
```

### الطرق المكسورة
- ❌ `python main.py` من الجذر → `No module named 'orchestrator'` (يجب التشغيل من داخل backend).
- ❌ `docker build` + `uvicorn backend.app:app` → `No module named 'orchestrator'` (استيراد نسبي).

---

## 2) تعارض المنافذ

| نقطة | المنفذ | الحالة |
|---|---|---|
| `start.sh` (Replit) | 5000 | يعمل |
| `fly.toml` (Fly.io) | 8080 | app: sovereign-ai-k20elq, region ams |
| `Dockerfile` | 8080 | ⚠️ يفشل (استيراد) |
| `app.py` (مباشر) | 8000 | يعمل |
| `.replit` | 5000→80 | يعمل |

> بند R-104: توحيد المنافذ.

---

## 3) متغيرات البيئة (config.py)

| المتغير | الافتراضي | ملاحظة |
|---|---|---|
| `SOVEREIGN_KEY` | مفتاح افتراضي غير آمن | 🔴 يجب تغييره |
| `DRIVE_ENABLED` | false | — |
| `AI_ENVIRONMENT` | — | — |
| `CORE_MODEL_NAME` | microsoft/Phi-3-mini-4k-instruct | لا يُستخدم فعلياً |
| `CORE_MODEL_LOAD_ON_START` | true | لا يُستخدم فعلياً |
| `MAX_USER_MESSAGES_PER_MINUTE` | 30 | غير مفعّل في الكود |
| `MAX_CONCURRENT_USERS` | 100 | — |
| `CORS_ORIGINS` | `*` | 🔴 خطر في الإنتاج |

---

## 4) النشر

### Fly.io
- `fly.toml`: app `sovereign-ai-k20elq`, region `ams`, health check `/health`, 512MB/1CPU.
- ⚠️ Dockerfile الحالي لا يبني (R-105).

### Replit
- `.replit`: python-3.12, nodejs-20, port 5000→80.

### GitHub/Railway/Google/device
- مذكورة في README كمنصات مستهدفة، دون إعدادات نشر موثقة.

---

## 5) سجل التحديثات

| التاريخ | التغيير | الدفعة |
|---|---|---|
| 2026-10-12 | توثيق التشغيل والنشر من مسح M0 | M0 |

## ملاحظات M1 (R-112)

- `.gitignore` أُنشئ — يمنع تتبع `__pycache__` وبيانات وقت التشغيل.
- إزالة 2233 ملف بيانات متتبع سابقاً قرار منفصل (M2).

## 6) الأداء (R-502)

### تحسين مطبّق
- أُضيف `GZipMiddleware` إلى `backend/app.py` للاستجابات الأكبر من 1,024 بايت، بمستوى ضغط 6.
- استجابة الصفحة الرئيسية `/`: **35,240 بايت → 4,727 بايت** مع `Accept-Encoding: gzip` (خفض 86.6%).

### قياسات warm محلية
| المسار | median | p95 |
|---|---:|---:|
| `/health` | 3.71 ms | 10.31 ms |
| `/status` | 1.34 ms | 9.50 ms |
| `/components/nexus` | 1.31 ms | 6.21 ms |

> القياسات محلية على بيئة التطوير، وليست SLA إنتاجياً. أعد القياس بعد النشر على بيئة الإنتاج.
