# ARCHITECTURE.md — البنية المعمارية

> كيف بُني المشروع؟ وصف صادق للبنية الفعلية كما رُصدت في مسح M0.
> آخر تحديث: 2026-10-12 (الدفعة M0)

---

## 1) نظرة عامة

المشروع يتكون من **نواتين منفصلتين** + نظام طوارئ + بيانات:

1. **النواة الرئيسية (SOVRA)** — `backend/` + `frontend/`: نظام "ذكاء سيادي" تجريبي بواجهة عربية.
2. **منصة NexusCore** — `nexus/`: منصة تحليلات/أتمتة، **مدمجة في النواة** (R-301) كمكوّن orchestrator.
3. **نظام الطوارئ (guardian)** — `guardian/`: قفل طوارئ + نسخ احتياطي كامل.
4. **البيانات** — `data/` (blobs مشفرة zlib) + `nexus_data/nexus.db` (SQLite فارغ).

---

## 2) النواة الرئيسية (backend/)

### نقطة الدخول
- `backend/app.py` — تطبيق FastAPI، 16 مساراً (راجع `API.md`).
- `backend/api.py` — APIRouter تحت `/api/*` (11 مساراً)، يُدمج في app.py عبر `include_router`.
- `backend/orchestrator.py` — "العقل المنسق": حلقة دورات، اتخاذ قرار، تنفيذ.
- `backend/config.py` — الإعدادات من متغيرات البيئة.
- `backend/safety.py` — طبقة "السيادة": أنواع أفعال تتطلب موافقة السيد.

### الوحدات الفرعية
| الوحدة | الدور | الملفات |
|---|---|---|
| `consciousness/` | "الوعي": حقل، هوية، نموذج ذاتي، وعي، انتباه، استبطان | 6 ملفات |
| `memory/` | الذاكرة: core, views, compress, encoding + biological/ (غرائز، دوافع، أنماط) + defense/ (دفاعات) + dynamic/ + store/ | ~20 ملف |
| `predictive/` | التنبؤ: محرك، متحكم، سيناريوهات، محاكاة، إدارة مخاطر | 5 ملفات |
| `simulation/` | المحاكاة: نواة، بيئة، مجدول، محلل، متحكم | 5 ملفات |
| `quantum/` | "الكم" (محاكاة مفاهيمية): حالة، حقل، تراكب، انتقال، متحكم | 5 ملفات |
| `sovereign/` | "السيادة": إرادة، تحكم، توجيهات، مواءمة | 4 ملفات |
| `biological/` | ⚠️ **مكسور**: `__init__.py` يستورد ملفات غير موجودة → ModuleNotFoundError | 1 ملف |

> ملاحظة: orchestrator يستخدم `memory.biological` (يعمل) وليس `backend/biological` (مكسور).

### كيف يعمل "الذكاء" (الحقيقة)
- القرارات تُتخذ عبر **قواعد** في `orchestrator._make_decision`: تحليل مخاطر/فرص → `monitor` / `continue` / `explore` / `activate_defense`.
- `CORE_MODEL_NAME` (Phi-3-mini) معرّف في config لكن **لا يُستورد ولا يوجد في الاعتماديات** — لا يوجد LLM فعلي.
- "الوعي" و"الكم" و"السيادة" هي **محاكاة مفاهيمية** (فئات/حلقات)، ليست نماذج حقيقية.

---

## 3) الواجهة (frontend/)

- `index.html` — صفحة عربية RTL واحدة، تحمّل **79 ملف JS** عبر `<script defer>`.
- `js/modules/` — 89 ملف (runtime-*, neural-*, engine-*, إلخ).
- `js/system/` — 27 ملف (system-*, runtime-layer-registry, إلخ).
- `css/` + `ui/` (cognitive-input.js).
- **43 ملف JS غير محمّل** في index.html (كود ميت محتمل — راجع OPEN_QUESTIONS س-6).
- **ملفان مكسوران** محمّلان: `system-thought-nebula.js` (مقطوع) و `system-runtime-consciousness-loop.js` (خطأ صياغة) — راجع ROADMAP R-101/R-102.

---

## 4) منصة NexusCore (nexus/) — مدمجة (R-301)

منصة تحليلات/أتمتة كاملة (71 ملف) — **مدمجة في النواة منذ R-301**:
- `core/engine.py` — المحرك الرئيسي (138 سطراً).
- `analytics/`, `api_gateway/`, `automation/`, `connectors/`, `data_pipeline/`, `decision_engine/`, `encryption/`, `file_manager/`, `forecasting/`, `nlp/`, `performance/`, `resource_manager/`, `security/`, `storage/`, `task_scheduler/`, `user_management/`, `visualization/`, `dashboard/`.
- `main.py` — `initialize_nexus()` يُستورد بنجاح.
- **مدمجة**: `orchestrator._load_nexus()` يحمّل NexusCore كمكوّن (46 مكوّناً فرعياً مسجلاً). يُكشف عبر `/components/nexus`.
- `nexus_data/nexus.db` — SQLite (جدولا events, kv_store) — **فارغ** (0 صف).

---

## 5) نظام الطوارئ (guardian/)

- 204 ملف، 4.6MB.
- `data/emergency/SYSTEM_LOCKED.lock` — قفل نشط: `{"SYSTEM_LOCKED": true, "incident_id": "38d75b88bc2c", "unlock_requires": "MASTER_REACTIVATION_CODE"}`.
- `ALERT_38d75b88bc2c.json` — سبب القفل: `PROTECTED_ACTION_WITHOUT_MASTER_TOKEN` (محاولة تجاوز صلاحيات السيد).
- `AI_FROZEN.flag` — تجميد الذكاء الاصطناعي.
- `emergency_backups/master_backup_20260616_151125/` — نسخة كاملة من backend+frontend (مطابقة للنسخة الحالية في عينة فحصها).
- `emergency_events.jsonl` — سجل الأحداث الطارئة.

---

## 6) البيانات (data/)

- `data/sovereign_core/blobs/` — 2297 ملف blob (11MB)، **مضغوطة zlib** (فك ضغط عينة أظهر JSON داخلي). تُكتب بواسطة `backend/memory/core.py`.
- `data/memory_store/backup_1781622498.json` — نسخة ذاكرة فارغة (كل الأقسام `[]`).
- `data/simulation/` — حالة مجدول/بيئة (فارغة).
- `data/config_backup.json` — نسخة إعدادات (تتحدث تلقائياً عند كل إقلاع — تُعدّل في git).
- مجلدات فارغة كثيرة: consciousness, self_model, homeostasis, instincts, quantum, phoenix, sovereign_requests, sovereign_responses, regeneration, stealth, identity.

---

## 7) الملفات الجذرية الشاذة (بعد M1/M2)

| الملف | الحقيقة | الحالة |
|---|---|---|
| `Fff` (28KB) | نص تعليمات AI | ✅ حُذف نهائيًا مع الأرشيف (R-685، بأمر المالك — نسخة احتياطية عند المالك + تاريخ git) |
| `IDs.py` (61KB) | كود TypeScript/JS بامتداد .py | ✅ حُذف نهائيًا مع الأرشيف (R-685) |
| `encryption.py` (74KB) | "موسوعة تشفير" Python | ✅ حُذف نهائيًا مع الأرشيف (R-685) |
| `investigation.py` (103KB) | نظام CIKMS استخباراتي | ✅ حُذف نهائيًا مع الأرشيف (R-685) |
| `Mr.py` | "محرك ولاء" | ✅ نُزع فتيله في R-686 (بأمر المالك): `LoyaltyContract` معقّم — `death_paths=0`، حارس AST، غير مربوط بـapp.py (تصويب R-714) |
| `main.py` (41KB) | نقطة تشغيل بديلة | نشط (أُصلح في R-105) |
| `memory/` | نسخة قديمة من polymorphic.py | ✅ أُرشف (R-110) + أُزيلت البقايا (R-201) |
| `infrastructure/` | Dockerfile + requirements فارغان | ✅ أُرشف (R-110) |
| `attached_assets/` | ملفان نصيان بتعليمات AI | ✅ أُرشف (R-110) |
| `dockerignore` (صغير) | تكرار لـ `.dockerignore` بمحتوى مختلف | ✅ أُرشف (R-201) |

---

## 8) التشغيل والنشر

| نقطة | المنفذ | الحالة |
|---|---|---|
| `start.sh` (Replit) | `PORT` (8000) | ✅ موحد (R-104) |
| `fly.toml` (Fly.io) | 8080 | app: sovereign-ai-k20elq, region ams |
| `Dockerfile` | 8080 | ✅ أُصلح (R-105): `WORKDIR /app/backend`, `uvicorn app:app` |
| `app.py` (مباشر) | `PORT` (8000) | ✅ يعمل |
| `.replit` | `PORT` (8000) | ✅ موحد (R-104) |

---

## 9) مخطط التبعيات (ملخص)

```
frontend/ (JS) ──HTTP/WS──▶ backend/app.py ──▶ orchestrator.py
                                              ├── consciousness/*
                                              ├── memory/* (core, biological, defense)
                                              ├── predictive/*
                                              ├── simulation/*
                                              ├── quantum/*
                                              └── sovereign/*
nexus/ (مدمجة R-301) ── orchestrator._load_nexus() ──▶ /components/nexus
guardian/ ── يراقب/ينسخ ──▶ backend+frontend
```

---

## 10) سجل التحديثات

| التاريخ | التغيير | الدفعة |
|---|---|---|
| 2026-10-12 | إنشاء وثيقة البنية من مسح M0 | M0 |
| 2026-10-12 | تحديث: الملفات الشاذة مؤرشفة، المنافذ موحدة (M1/M2) | M1/M2 |
| 2026-10-12 | تحديث: NexusCore مدمجة في النواة (R-301) | M3 |
