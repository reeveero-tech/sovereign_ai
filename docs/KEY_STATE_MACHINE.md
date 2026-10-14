# عقد آلة حالة المفتاح (Key State Machine)

**التاريخ:** 2026-10-14
**البوابة:** 5 — سياسة المفاتيح التاريخية (LOST/EXPIRED/COMPROMISED/ROTATED)
**القاعدة الحاكمة:** الحالة شيء صريح، ليس ضمنياً. مفتاح بلا حالة = فشل.

هذا الملف هو **عقد** — الكود يُطبّقه، الاختبار يحرسه.

---

## الحالات الخمس

| الحالة | التوقيع | التحقق التاريخي | ملاحظات |
|---|---|---|---|
| `ACTIVE` | ✅ نعم | ✅ نعم | المفتاح الحالي — يُستخدم للتوقيع و التحقق |
| `ROTATED` | ❌ لا | ✅ نعم | مُستبدل — تحقق تاريخي فقط، لا توقيع جديد |
| `LOST` | ❌ لا | ⚠️ مشروط | مفقود — لا يُستخدم لأي شيء، النظام يعرف |
| `COMPROMISED` | ❌ لا | ⚠️ مشروط | مُوسوم — يُسجَّل، لا توقيع جديد، تحقق تاريخي مشروط |
| `EXPIRED` | ❌ لا | ❌ لا | حالة نهائية — لا يُستخدم لأي شيء |

---

## الانتقالات المسموحة (7)

```
ACTIVE       → ROTATED
ACTIVE       → LOST
ACTIVE       → COMPROMISED
ACTIVE       → EXPIRED
ROTATED      → EXPIRED
LOST         → EXPIRED
COMPROMISED  → EXPIRED
EXPIRED      → (لا انتقال — نهائي)
```

**ملاحظة:** `EXPIRED` حالة نهائية — لا انتقال منها إلى أي شيء.

---

## الانتقالات الممنوعة صريحاً (5+)

```
EXPIRED      → ACTIVE       (ممنوع — لا عودة من النهاية)
EXPIRED      → ROTATED      (ممنوع — نهائي)
EXPIRED      → LOST         (ممنوع — نهائي)
EXPIRED      → COMPROMISED  (ممنوع — نهائي)
LOST         → ACTIVE       (ممنوع — لا يُستخدم مفتاح مفقود)
ROTATED      → ACTIVE       (ممنوع — لا يُستخدم مفتاح مُستبدل للتوقيع)
COMPROMISED  → ACTIVE       (ممنوع — لا يُستخدم مفتاح مُخترق)
COMPROMISED  → ROTATED      (ممنوع — COMPROMISED أقوى من ROTATED)
```

**كل انتقال غير موجود في قائمة الانتقالات المسموحة = ممنوع و يجب أن يفشل صراحة.**

---

## سلوك التوقيع و التحقق

### التوقيع (signing)
- `ACTIVE`: **مسموح** — المفتاح يُستخدم للتوقيع
- `ROTATED`: **ممنوع** — `KeyStateError: ROTATED key cannot sign`
- `LOST`: **ممنوع** — `KeyStateError: LOST key cannot sign`
- `COMPROMISED`: **ممنوع** — `KeyStateError: COMPROMISED key cannot sign`
- `EXPIRED`: **ممنوع** — `KeyStateError: EXPIRED key cannot sign`

### التحقق (verification)
- `ACTIVE`: **مسموح** — يُستخدم للتحقق
- `ROTATED`: **مسموح** — تحقق تاريخي (المفتاح صالح للتوقيع القديم)
- `LOST`: **مشروط** — يُعيد `UNVERIFIABLE_MISSING_KEY` (ليس `False` — الفرق جوهري)
- `COMPROMISED`: **مشروط** — يُعيد `UNVERIFIABLE_COMPROMISED` (تحقق تاريخي مشروط)
- `EXPIRED`: **ممنوع** — يُعيد `UNVERIFIABLE_EXPIRED`

---

## ملاحظات إلزامية

1. **كل مفتاح في `keyring.json` يجب أن يحمل حقل `state` صريحاً.**
   إذا لم يحمله → **فشل عند التحميل** — لا default، لا "ACTIVE ضمنياً".
2. **المفاتيح التاريخية (LOST/EXPIRED) تبقى في السجل للأبد — لا حذف.**
3. **لا انتقال من EXPIRED** — إنهاء نهائي.
4. **الاختبار يحرس العقد** — `backend/tests/invariants/test_key_state_transitions.py`
