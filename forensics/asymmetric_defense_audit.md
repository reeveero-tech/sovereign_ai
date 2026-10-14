# تدقيق: Asymmetric Defense (الدفاع غير المتماثل) (R-670)

**التاريخ:** 2026-10-14
**السبب:** النمط تكرر مرتين:
1. **البوابة 4 (R-665):** `verify_anchor` يُعيد `True` دون التحقق من التوقيع
2. **البوابة 5 (R-668):** `verify_event` يفحص فقط `LOST` (لا يفحص `COMPROMISED/EXPIRED/RETIRED`)

**النمط:** مسار الكتابة محمي، مسار القراءة/التحقق مكشوف.
**الاسم:** Asymmetric Defense (غير متماثل دفاعياً).

---

## المنهجية (تدقيق واسع — 1768 دالة)

1. **بحث AST:** كل ملفات `backend/` (استثناء `tests/`, `__pycache__`, `.git`, `.pytest_cache`, `node_modules`)
2. **فئة 1:** لكل مسار كتابة (`create/sign/append/insert/register/store/save/write/put/add`)، ابحث عن المسار المقابل في القراءة (`verify/check/validate/assert/confirm/is_/has_/can_/should_/get/lookup/resolve/retrieve/read`)
3. **فئة 2:** كل دالة اسمها يبدأ بـ `verify/check/validate/assert/confirm` — تُعيد `True` بشروط أضعف؟
4. **فئة 3:** كل دالة اسمها يبدأ بـ `is_/has_/can_/should_` — تُعيد `True` بشروط أضعف من الفعل الموصوف؟
5. **فحص يدوي:** لكل زوج write/read، مقارنة الشروط (status, signature, keyring, api_key, master)

---

## النتائج

### الأزواج المتناظرة (لا ثغرة)

| Write Path | Read/Verify Path | Write Guard | Read Guard | Asymmetric? |
|------------|------------------|-------------|------------|-------------|
| `anchor_batch()` | `verify_anchor()` | signature required | signature verified | ✅ FIXED R-664/R-665 |
| `_compute_signature()` | `verify_event()` | key must be ACTIVE | all states rejected (LOST/COMPROMISED/EXPIRED/RETIRED) | ✅ FIXED R-668 |
| `generate_new_key()` | `get_active_key()` | creates new ACTIVE | returns only ACTIVE | ✅ Symmetric |
| `generate_signature()` | `_verify_signature()` | HMAC with key | HMAC verification | ✅ Symmetric |
| `create_master_code_shield()` | `verify_master()` | master code set | master code verified | ✅ Symmetric |
| `append_event()` | `verify_integrity()` | key must be ACTIVE (R-635) | key_id from event, compare_digest | ✅ Symmetric |
| `append_event()` | `get_payload()` | key must be ACTIVE (R-635) | raw retrieval (no trust claim) | ✅ Symmetric |
| `encrypt()` | `decrypt()` | key required | key required | ✅ Symmetric |

### المرشحون للفحص اليدوي (5)

| Function | File | Concern | Verdict |
|----------|------|---------|---------|
| `check_action()` | `backend/safety.py:284` | returns True without signature guard | ✅ SAFE — simple boolean policy (no key/crypto path) |
| `verify_master()` | `backend/Mr.py:404` | returns True without signature guard | ✅ SAFE — master code verification (not key/crypto path) |
| `is_anomalous()` | `backend/memory/defense/watcher.py:164` | returns True without raise | ✅ SAFE — statistical predicate (z-score > 3) |
| `is_known_threat()` | `backend/memory/biological/immune.py:575` | returns True without raise | ✅ SAFE — fingerprint lookup (not crypto) |
| `verify_identity_integrity()` | `backend/consciousness/identity_core.py:645` | returns True without signature guard | ✅ SAFE — coherence check (not key/crypto path) |

### الخلاصة

**0 من 1768 دالة** تعاني من Asymmetric Defense لم تُصلح بعد.
- الثغرتان الأصليتان (R-664/R-665 و R-668) أُصلحتا.
- 5 مرشحين فُحصوا يدويًا — كلهم آمنون (ليسوا مسارات تشفير/مفاتيح).

---

## ما لم يُفحص (حدود التدقيق)

### الملفات المُستثنى
- `tests/` (كل ملفات الاختبارات)
- `__pycache__/`, `.git/`, `.pytest_cache/`, `node_modules/`
- الملفات التي فشل تحليلها بـ AST

### الفئة غير المُدققة
- **الدوال التي تُعيد قيمة دون رسالة** (906 من 1027) — لا يمكن أن تكون Asymmetric (لا رسالة)، لكن قد تحمل أخطاء أخرى.
- **الدوال المُنشأة ديناميكيًا** (decorators, closures, `getattr`, `exec`) — لا تُفحص بـ AST.
- **الأزواج الضمنية** — إذا كان مسار الكتابة و القراءة في ملفين مختلفين و لم يُكتشف بالاسم (مثل `save_X()` و `load_X()`)، قد لا تُكتشف.

### الحدود المنطقية
1. التدقيق يعتمد على **أسماء الدوال** (prefix match) — دالة بلا اسم مطابق قد لا تُكتشف.
2. التدقيق لا يفحص **الشروط الداخلية بدقة** — يفحص فقط وجود كلمات مفتاحية (`signature`, `keyring`, `status`, `ACTIVE`).
3. **5 مرشحين** فُحصوا يدويًا — لم يكن أحدهم ثغرة حقيقية (كانوا مسارات سياسة/إحصاء، لا تشفير).
