# AWARENESS_561_DECISION.md — R-682 (open item 3)

**التاريخ:** 2026-10-15
**القرار:** مسار (ب) — إزالة آمنة + issue مُوثّق
**Issue:** #R-682-561

---

## السياق

الموقع الأصلي في `backend/consciousness/awareness.py:561` كان:

```python
# TOLERATED: placeholder for future condition check — no action needed (R-680)
if self.current_moment:
    pass
time.sleep(0.1)
```

هذا كود صامت (pass) — لا يُنفّذ شيئًا. R-681 وسمه بـ TODO. R-682 أمر بإما (أ) تنفيذ فعلي أو (ب) إزالة آمنة + issue.

---

## الخيار (أ): تنفيذ الخوارزمية

**لماذا لم يُنفّذ:**

1. **يتطلب قرارًا معماريًا من المالك** — خوارزمية "معالجة تحت الوعي" (subliminal processing) هي قرار تصميمي، ليس مجرد إصلاح برمجي.
2. لا يوجد مواصفات واضحة في `forensics/GOAL_DISCOVERY.md` أو `docs/ROADMAP.md` عن ماهية هذه المعالجة.
3. كتابة خوارزمية عشوائية ستكون "عقل يتطور" — وهذا يتعارض مع الغاية المعلنة (نظام حوكمة + إثبات نزاهة).

---

## الخيار (ب): إزالة آمنة (المُنفَّذ)

### ما تم

```python
# BEFORE (R-681):
if self.current_moment:
    pass
time.sleep(0.1)

# AFTER (R-682):
time.sleep(0.1)
```

**لا تغيير سلوكي.** الكود كان بالفعل "لا يفعل شيئًا" — إزالة `pass` لا تغيّر أي سلوك. الغموض (السطر الصامت) أُزيل.

### لماذا هذا آمن

- `if self.current_moment:` لم يُقرأ منه شيئًا (لا side effect)
- `pass` لا يُنفّذ شيئًا
- الحلقة كانت (وما زالت) `sleep(0.1)` فقط

---

## Issue #R-682-561

**العنوان:** Implement real subliminal processing algorithm in awareness.py
**الحالة:** OPEN — awaiting owner's architectural decision
**الأولوية:** Medium
**الاعتماديات:** needs spec for "subliminal processing" (no clear definition in docs)

**الخطوة التالية:** المالك يُقرر ماهية المعالجة تحت الوعي — عندئذٍ يُنفَّذ الاختبار RED ثم الخوارزمية.

---

## الحكم النهائي

البند 3: **CLOSED** (الإزالة الآمنة + issue) — قرار مُوثّق، لا يوجد `pass` صامت.
