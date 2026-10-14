# تداخل KeyStatus و KeyState (R-668)

**التاريخ:** 2026-10-14
**المشكلة:** يوجد enumان لوصف حالة المفتاح — `KeyStatus` (في `keyring.py`) و `KeyState` (في `state_machine.py`).

## الاكتشاف

### أين يُستخدم KeyStatus؟
- `backend/sovereign/keys/keyring.py` — تعريف + كل الدوال (`get_active_key`, `mark_key_lost`, `mark_key_compromised`)
- `backend/sovereign/keys/verifier.py` — يفحص `KeyStatus.LOST` فقط (لا يفحص COMPROMISED/EXPIRED/RETIRED)
- `backend/memory/core.py` — يفحص `active.status != KeyStatus.ACTIVE`

### أين يُستخدم KeyState؟
- `backend/sovereign/keys/state_machine.py` — تعريف + `ALLOWED_TRANSITIONS`
- `backend/tests/invariants/test_key_state_transitions.py` — اختبارات البوابة 5

### هل يمكن أن يحمل مفتاح واحد كليهما؟
- **لا** — مفتاح واحد يحمل `status` (من نوع `KeyStatus`) في `keyring.json`.
- `KeyState` هو مفهوم آلة الحالة — يُشتق من `KeyStatus` عبر الترجمة.

### أي كود يقرأ RETIRED؟ أي كود يقرأ ROTATED؟
- `RETIRED` يُقرأ في: `keyring.py` (retire_key، get_active_key)، `memory/core.py` (`status != ACTIVE`)
- `ROTATED` يُقرأ في: `state_machine.py` فقط (لا يقرأه `keyring.py` أو `verifier.py`)

### كيف يُترجمان؟
- تُعرّف دالة ترجمة صريحة `translate_status_to_state()` في `state_machine.py`:
  - `RETIRED` → `ROTATED` (مُستبدل — تحقق تاريخي فقط)
  - `ACTIVE` → `ACTIVE`
  - `LOST` → `LOST`
  - `COMPROMISED` → `COMPROMISED`
  - `EXPIRED` → `EXPIRED`

## القرار: دالة ترجمة صريحة (توحيد مُؤجل)

**القرار:** تُعرَّف دالة ترجمة صريحة `KeyStatus → KeyState` مع اختبار يحرس التحويل.

**التبرير:**
- توحيد الـ enumين يتطلب تغيير `keyring.json` (البيانات الحقيقية) و كل الكود الذي يقرأ `KeyStatus` — توسيع كبير خارج نطاق البوابة 5.
- دالة ترجمة صريحة تُحقق نفس الهدف (واجهة واحدة للحالة) دون تغيير البيانات أو كسر الاختبارات.
- التوحيد الكامل يُسجّل كقرار معلّق (مثل الهجرة إلى Ed25519).

## جدول المفاتيح الحقيقية (data/keys/keyring.json)

| key_id | KeyStatus value | KeyState value | Consistent? |
|--------|-----------------|----------------|-------------|
| b8bf12ab28abfc01 | COMPROMISED | COMPROMISED | ✅ YES |
| 433759679aca9268 | ACTIVE | ACTIVE | ✅ YES |

## الترجمة (RETIRED → ROTATED)

| KeyStatus | KeyState | المعنى |
|-----------|----------|--------|
| ACTIVE | ACTIVE | مفتاح حالي — توقيع + تحقق |
| RETIRED | ROTATED | مُستبدل — تحقق تاريخي فقط |
| LOST | LOST | مفقود — لا شيء |
| COMPROMISED | COMPROMISED | مخترق — لا توقيع، تحقق مشروط |
| EXPIRED | EXPIRED | نهائي — لا شيء |

## اختبار الترجمة

`backend/tests/invariants/test_key_state_transitions.py` — اختبار جديد:
`test_23_key_status_translates_to_key_state` — أي مفتاح يُحمّل من `keyring.json`
يجب أن تكون حالته قابلة للترجمة إلى `KeyState`. إذا وُجد مفتاح بحالة لا تُترجم — فشل صريح.
