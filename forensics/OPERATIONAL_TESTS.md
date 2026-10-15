# OPERATIONAL_TESTS.md — R-682 (Task 3.3)

**التاريخ:** 2026-10-15
**المرجع:** أمر التسليم — Task 3.3
**القرار:** عزل الاختبارات التشغيلية تحت marker `operational` — لا تُحسب كـ skip.

---

## السياق

الاختبار `tests/test_gate1_operational_auth.py` يتطلب:
1. قراءة أسرار المضيف (`data/key.secret`, `data/key.secret.old_rotated_*`)
2. كتابة في البيانات الحقيقية (subprocess يُحمّل التطبيق بالإعدادات الحقيقية)
3. تشغيل يدوي بـ `--run-operational` flag

**لماذا لا يمكن إصلاحه بـ fixture اصطناعي:**
- الاختبار مُصمم للتحقق من **التشغيل الفعلي** — لا من بيانات اصطناعية.
- استخدام fixture اصطناعي سيُلغي الغرض من الاختبار (التحقق أن العملية الحقيقية تُحمّل المفتاح الصحيح).

---

## الحل المُنفَّذ (مسار ب: marker صريح)

### 1) `pytest.ini`

```ini
[pytest]
markers =
    operational: requires --run-operational flag (reads host secrets, writes real data)
```

### 2) `tests/test_gate1_operational_auth.py`

```python
pytestmark = pytest.mark.operational  # R-682 (Task 3.3)
```

### 3) CI

```bash
python -m pytest tests/ backend/tests/ -v -m "not operational" ...
```

---

## النتيجة

- الاختبار **مُعزل** (deselected) — لا يظهر كـ `skipped` في JUnit.
- يُشغّل يدويًا: `pytest tests/test_gate1_operational_auth.py --run-operational`
- في CI يُشغّل فقط في job مستقل عند تفعيله يدويًا (workflow_dispatch).

---

## CI Job المستقل (workflow_dispatch)

لا يُنشأ تلقائيًا — يتطلب تفعيل يدوي. عند التفعيل:
1. يُحمّل `data/key.secret` من secret `KEY_SECRET` (متاح للمالك)
2. يُشغّل: `pytest -m operational --run-operational`
3. يُنتج JUnit في `forensics/pytest_operational.xml`

**تصحيح (advisor R-682 final):** الإصدار السابق كان يقول إن الـ job "يُنشئ `data/key.secret.old_rotated_*` اصطناعيًا" — هذا **غير صحيح**. `ci.yml` لا يُنشئ ملفات `old_rotated` — يُحمّل `key.secret` فقط من secret `KEY_SECRET`. الاختبارات التشغيلية نفسها تقرأ أي ملفات `old_rotated` موجودة في المضيف (إن وُجدت).

**خطوة `sha` (تصحيح R-682 final):** كان الـ workflow يشير إلى `steps.sha.outputs.short` في job `operational` بدون وجود step `sha` — أُضيف step `sha` لتفادي فشل تسمية artifact.

**الحالة:** مُنفَّذ (isolation) — الاختبار لم يُحذف، فقط عُزل.

---

## الجولة التشغيلية (2026-10-15) — إعداد التشغيل الفعلي بعد إضافة المالك `KEY_SECRET`

**فجوة التصميم المكتشفة قبل التشغيل:** الاختبار التشغيلي يتطلب ملفين —
`data/key.secret` (المفتاح الحالي، متاح من `KEY_SECRET`) **و**
`data/key.secret.old_rotated_2026_10_14` (المفتاح القديم — أثر التدوير
الجنائي) — والوظيفة في `ci.yml` لم تكن توفر الثاني إطلاقًا، فأي تشغيل كان
سيفشل حتمًا عند `assert old_key_path.exists()` (فشل زائف لا يقيس سلوك
المصادقة). القيمة الجنائية للاختبار تتطلب المفتاح القديم **الحقيقي** — لا
بديل اصطناعي (مفتاح اصطناعي يُضعفه إلى «أي مفتاح خاطئ يُرفض»).

**الإصلاحات (أوامر المستشار):**
1. **`ci.yml`:** خطوة التحميل صارت تمرّر السرين عبر `env` (لا استيفاء مباشر
   داخل `run`)، وتكتب الملفين بـ `umask 077` + `printf '%s' "$VAR"`، وتفشل
   برسالة صريحة إذا غاب أحدهما، ولا تطبع القيم ولا تدخل الملفان أي artifact.
2. **الاختبار:** المفتاحان يُمرَّران إلى السب-بروسس عبر متغيرات بيئة
   (`TEST_NEW_KEY`/`TEST_OLD_KEY`) — لا يُضمَّنان في مصدر السكربت، فلا يظهران
   في أي traceback أو رسالة إخفاق أو مخرجات pytest.

**السران المطلوبان (قرار المالك):**
| السر | المحتوى | الملف الذي يُنشأه |
|---|---|---|
| `KEY_SECRET` | المفتاح الرئيسي الحالي | `data/key.secret` |
| `KEY_OLD_SECRET` | محتوى ملف `data/key.secret.old_rotated_2026_10_14` من مضيف المالك | الملف نفسه |

**نطاق الادعاء (تصويب أمر المستشار):** الوظيفة الاعتيادية (`test`) **لا
تستخدم** سر المستودع — تُولّد مفتاحًا مؤقتًا ذاتيًا. ونجاح الوظيفة
التشغيلية يثبت المصادقة **داخل بيئة CI المحمّلة بالمفتاحين الحقيقيين** —
لا حالة خادم الإنتاج.

**الإغلاق يتطلب (أمر المستشار):** تشغيل الوظيفة نفسها بـ
`run_operational=true` على SHA محدد + نجاح job الـoperational + JUnit يثبت
تنفيذ الاختبار الواحد بنجاح (200/403) دون فشل أو تخطٍّ — لا يُغلق البند
قبل ظهور هذه الأدلة.
