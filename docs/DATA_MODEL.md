# DATA_MODEL.md — نموذج البيانات

> كل مصادر البيانات في المشروع، كما رُصدت في مسح M0.
> آخر تحديث: 2026-10-12 (الدفعة M0)

---

## 1) مصادر البيانات

| المصدر | النوع | الموقع | الحالة |
|---|---|---|---|
| Blob store | ملفات JSON مضغوطة zlib | `data/sovereign_core/blobs/` (2297 ملف، 11MB) | نشط — تُكتب بواسطة memory/core.py |
| SQLite | قاعدة بيانات | `nexus_data/nexus.db` (20KB) | فارغ (0 صف) |
| JSON | نسخة ذاكرة | `data/memory_store/backup_1781622498.json` | فارغ (كل الأقسام `[]`) |
| JSON | حالة مجدول | `data/simulation/scheduler/scheduler_state.json` | فارغ |
| JSON | حالة بيئة | `data/simulation/environments/environment_state.json` | فارغ |
| JSON | نسخة إعدادات | `data/config_backup.json` | يتحدث تلقائياً عند كل إقلاع |
| JSON | قفل طوارئ | `guardian/data/emergency/SYSTEM_LOCKED.lock` | نشط (مقفل) |
| JSONL | سجل طوارئ | `guardian/data/emergency/emergency_events.jsonl` | نشط |

---

## 2) Blob store (data/sovereign_core/blobs/)

- **البنية**: مجلدات فرعية بأول حرفين من الـ hash (52/, ae/, 8c/, ...).
- **الضغط**: zlib.
- **المحتوى**: JSON داخلي (فك ضغط عينة أظهر رسائل خطأ/تحذيرات مثل `فشل استدعاء get_will_status`).
- **الكتابة**: `backend/memory/core.py` + `backend/memory/defense/ransomware.py`.
- **التجزئة**: sha256.

### مثال (عينة مفكوكة)
```json
{"level": "warning", "message": "فشل استدعاء get_will_status", "payload": {"error": "'MemoryWatcher' object has no attribute 'get_status'"}}
```

---

## 3) SQLite (nexus_data/nexus.db)

- **الجدولان**: `events`, `kv_store`.
- **الحالة**: 0 صف في كل منهما.
- **الاستخدام**: منصة NexusCore (غير موصولة بالنواة).

---

## 4) بيانات guardian

- `SYSTEM_LOCKED.lock`:
```json
{"SYSTEM_LOCKED": true, "incident_id": "38d75b88bc2c", "locked_at": 1781622686, "unlock_requires": "MASTER_REACTIVATION_CODE", "reactivation_code_hash": "d87c05f2..."}
```
- `AI_FROZEN.flag`: `{"frozen_at": 1781622685, "reason": "emergency_breaker"}`.
- `emergency_events.jsonl`: سجل أحداث (تجميد، عزل شبكة، نسخ احتياطي، تنبيه).

---

## 5) ملاحظات

- 🟠 **بيانات وقت التشغيل متتبعة في git** (2233 ملف) — تضخم + تعديلات تلقائية (R-112).
- 🟢 مجلدات بيانات فارغة كثيرة (consciousness, self_model, homeostasis, instincts, quantum, phoenix, sovereign_requests, sovereign_responses, regeneration, stealth, identity).

---

## 6) سجل التحديثات

| التاريخ | التغيير | الدفعة |
|---|---|---|
| 2026-10-12 | توثيق نموذج البيانات من مسح M0 | M0 |
