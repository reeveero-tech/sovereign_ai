# API.md — الواجهات البرمجية

> كل نقاط API في النواة، كما رُصدت في مسح M0 + تحديث M6 (R-608).
> آخر تحديث: 2026-10-14 (الدفعة M6 — R-608/R-609)
> **توثيق حي**: Swagger على `/docs`، ReDoc على `/redoc`، OpenAPI على `/openapi.json` (45 مساراً).

---

## 1) النواة (backend/app.py) — 45 مساراً

### عام
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/` | الواجهة (HTML عربي RTL) | لا |
| GET | `/health` | فحص الصحة (23 مكوّناً) | لا |
| GET | `/status` | حالة النظام | لا |
| GET | `/api-key` | بصمة مفتاح API (لا يُكشف المفتاح) | رأس `X-API-Key` (جولة المجلس <1> — صيغة الاستعلام أُزيلت) |

### محادثة
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/chat` | محادثة؛ حد 30 طلباً/دقيقة لكل IP افتراضياً + فحص طبقة الأمان | لا؛ حد معدل |
| WS | `/ws/{user_id}` | محادثة WebSocket (مع فحص طبقة الأمان) | لا |

### أوامر السيد (تتطلب api_key في body)
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/sovereign/command` | أمر سيادي (فحص أمان حتى للسيد) | api_key |
| POST | `/sovereign/reset` | إعادة تعيين (فحص أمان) | api_key |

### أخرى
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/orchestrator/cycle` | تشغيل دورة | `api_key` في الجسم |
| GET | `/components/consciousness` | حالة الوعي | لا |
| GET | `/components/memory` | حالة الذاكرة | لا |
| GET | `/components/predictive` | حالة التنبؤ | لا |
| GET | `/components/simulation` | حالة المحاكاة | لا |
| GET | `/components/sovereign` | حالة السيادة | لا |
| GET | `/components/quantum` | حالة الكم | لا |
| GET | `/components/nexus` | حالة NexusCore المدمجة (R-301) | لا |
| GET | `/components/defense` | حالة الدفاع | لا |

### طبقة الأمان (R-608)
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/security/status` | حالة SafetyGuard (نشط/قوائم/سجل) | لا |
| GET | `/security/log` | آخر أحداث سجل الأمان (limit 1-500) | لا |

### NexusCore REST API (R-608)
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/nexus/status` | حالة محرك NexusCore | لا |
| POST | `/nexus/analyze/text` | تحليل نص (مشاعر/نية/لغة) | لا |
| POST | `/nexus/ingest` | إدخال بيانات عبر DataCollector | لا |
| GET | `/nexus/health` | صحة NexusCore | لا |
| POST | `/nexus/budget/analyze` | تحليل ميزانية (قائمة) | لا |
| GET | `/nexus/recommendations` | توصيات | لا |

---

## 2) واجهة /api/* (backend/api.py) — 11 مساراً

| الطريقة | المسار | الوصف |
|---|---|---|
| GET | `/api/health` | صحة (version 3.0.0) |
| POST | `/api/run` | تشغيل دورة |
| POST | `/api/reset` | إعادة تعيين |
| GET | `/api/state` | الحالة |
| GET | `/api/history` | التاريخ |
| POST | `/api/event` | حدث |
| GET | `/api/components` | المكوّنات |
| GET | `/api/connections` | الاتصالات |
| GET | `/api/mode` | الوضع |
| POST | `/api/mode/{mode}` | تعيين الوضع |
| WS | `/api/ws` | WebSocket (مع فحص طبقة الأمان) |

---

## 3) نماذج الطلبات/الاستجابات

### POST /chat
```json
// طلب
{"text": "مرحباً", "user_id": "user1", "session_id": "abc"}
// استجابة عادية
{"reply": "تم تنفيذ القرار: monitor", "status": "ok", "cycle_id": "...", "processing_time_ms": 12.3, "timestamp": 1234.5}
// استجابة محجوبة (طبقة الأمان)
{"reply": "هذا الأمر محظور...", "status": "blocked", "cycle_id": "safety-block", ...}
```

### POST /sovereign/command
```json
// طلب (يتطلب api_key)
{"api_key": "...", "command": "get_status"}
```

### POST /orchestrator/cycle
```json
// استجابة
{"cycle_id": "...", "success": true, "duration": 0.22, "decision": {"action": "monitor", "confidence": 0.6, ...}}
```

### POST /nexus/analyze/text
```json
// طلب
{"text": "نص للتحليل"}
// استجابة
{"sentiment": {...}, "intent": {...}, "language": {...}}
```

### GET /security/status
```json
// استجابة
{"safety_guard": {"active": true, "forbidden_absolute": 6, "dangerous_patterns": [...], ...}, "rate_limiter": {...}, "nexus_api": {...}}
```

---

## 4) ملاحظات أمنية (راجع RISKS.md)

- `GET /api-key` يتطلب رأس `X-API-Key` (R-106 — وصيغة الاستعلام `master_key` أُزيلت في جولة المجلس <1> لأنها تُسجّل في سجلات الوصول).
- `POST /orchestrator/cycle` يتطلب `api_key` (R-108).
- `POST /chat` لا يتطلب تسجيل دخول؛ يطبق حداً انزلاقياً per-IP (30/60 ثانية افتراضياً)، ويرد بـ 429 و`Retry-After` عند التجاوز (R-603).
- محدد `/chat` في الذاكرة داخل كل عملية؛ ليس حداً موزعاً بين workers أو الخوادم.
- **طبقة الأمان (R-608)**: كل مدخلات `/chat` وWebSocket و`/sovereign/*` تُفحص عبر `SafetyGuard` — الأوامر الممنوعة تماماً (تدمير ذاتي، مسح ذاكرة...) تُحجب حتى للسيد.
- راجع `CORS_ORIGINS` في `SECURITY.md` قبل النشر.

---

## 5) سجل التحديثات

| التاريخ | التغيير | الدفعة |
|---|---|---|
| 2026-10-12 | توثيق نقاط API من مسح M0 | M0 |
| 2026-10-13 | R-603: توثيق تقييد معدل `/chat` وحالة المصادقة الفعلية | M6 |
| 2026-10-14 | R-608: توثيق نقاط `/nexus/*` و`/security/*` وفحص طبقة الأمان | M6 |
