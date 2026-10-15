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
2. يُنشئ `data/key.secret.old_rotated_*` اصطناعيًا
3. يُشغّل: `pytest -m operational --run-operational`

**الحالة:** مُنفَّذ (isolation) — الاختبار لم يُحذف، فقط عُزل.
