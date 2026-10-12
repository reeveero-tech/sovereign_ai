# API.md — الواجهات البرمجية

> كل نقاط API في النواة، كما رُصدت في مسح M0 + تحديث M4 (R-403).
> آخر تحديث: 2026-10-13 (الدفعة M4)
> **توثيق حي**: Swagger على `/docs`، ReDoc على `/redoc`، OpenAPI على `/openapi.json` (26 مساراً).

---

## 1) النواة (backend/app.py) — 26 مساراً (OpenAPI)

### عام
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| GET | `/` | الواجهة (HTML عربي RTL) | لا |
| GET | `/health` | فحص الصحة (23 مكوّناً) | لا |
| GET | `/status` | حالة النظام | لا |
| GET | `/api-key` | 🔴 **يعيد مفتاح API بلا مصادقة** | لا (خطر — R-106) |

### محادثة
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/chat` | محادثة (body: text, user_id?, session_id?) | لا |
| WS | `/ws/{user_id}` | محادثة WebSocket | لا |

### أوامر السيد (تتطلب api_key في body)
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/sovereign/command` | أمر سيادي | api_key |
| POST | `/sovereign/reset` | إعادة تعيين | api_key |

### أخرى
| الطريقة | المسار | الوصف | المصادقة |
|---|---|---|---|
| POST | `/orchestrator/cycle` | 🔴 تشغيل دورة (بلا مصادقة) | لا (خطر — R-108) |
| GET | `/components/consciousness` | حالة الوعي | لا |
| GET | `/components/memory` | حالة الذاكرة | لا |
| GET | `/components/predictive` | حالة التنبؤ | لا |
| GET | `/components/simulation` | حالة المحاكاة | لا |
| GET | `/components/sovereign` | حالة السيادة | لا |
| GET | `/components/quantum` | حالة الكم | لا |
| GET | `/components/nexus` | حالة NexusCore المدمجة (R-301) | لا |
| GET | `/components/defense` | حالة الدفاع | لا |

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
| WS | `/api/ws` | WebSocket |

---

## 3) نماذج الطلبات/الاستجابات

### POST /chat
```json
// طلب
{"text": "مرحباً", "user_id": "user1", "session_id": "abc"}
// استجابة
{"reply": "تم تنفيذ القرار: monitor", "status": "ok", "cycle_id": "...", "processing_time_ms": 12.3, "timestamp": 1234.5}
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

---

## 4) ملاحظات أمنية (راجع RISKS.md)

- 🔴 `/api-key` بلا مصادقة (RK-01).
- 🔴 `/orchestrator/cycle` بلا مصادقة (RK-04).
- 🔴 CORS `*` (RK-02).
- المفتاح يتولد عشوائياً عند كل إقلاع — لا يُحفظ.

---

## 5) سجل التحديثات

| التاريخ | التغيير | الدفعة |
|---|---|---|
| 2026-10-12 | توثيق نقاط API من مسح M0 | M0 |
