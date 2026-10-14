# تدقيق .gitignore (R-670)

**التاريخ:** 2026-10-14
**السبب:** سؤال المالك — "baseline و true_red كانا مستثنيين. استثناء من ماذا؟"

**الجواب:** الاستثناء كان من `*.log` في `.gitignore` (السطر 53). أي ملف بلا استثناء صريح `!` لم يُدفع. هذا يعني أن أي ملف جنائي بامتداد `.log` كان يُفقد تلقائياً.

---

## المشكلة

`.gitignore` يحتوي على `*.log` — يُطبق على **كل** ملف بامتداد `.log`. لذلك أي ملف جنائي جديد في `forensics/` بامتداد `.log` لا يُدفع إلا إذا أُضيف استثناء صريح `!forensics/<file>.log`.

**النتيجة:** كل ملف جنائي جديد يجب أن يُضاف يدوياً إلى `.gitignore` — عملية خطرة (نسيان = فقدان دليل).

---

## الحالة (قبل الإصلاح)

| الملف | المُستثنى؟ | السبب |
|---|---|---|
| `forensics/rotation/before.log` | ✅ tracked | استثناء صريح (R-651) |
| `forensics/rotation/after.log` | ✅ tracked | استثناء صريح (R-651) |
| `forensics/gate4_red.log` | ✅ tracked | استثناء صريح (R-664) |
| `forensics/gate4_green.log` | ✅ tracked | استثناء صريح (R-664) |
| `forensics/gate4_red_v3.log` | ✅ tracked | استثناء صريح (R-664) |
| `forensics/gate4_green_v3.log` | ✅ tracked | استثناء صريح (R-664) |
| `forensics/gate5_baseline.log` | ✅ tracked | استثناء صريح (R-667) |
| `forensics/gate5_green.log` | ✅ tracked | استثناء صريح (R-667) |
| `forensics/gate5_true_red.log` | ✅ tracked | استثناء صريح (R-669) |
| `data/keys/keyring.json` | ❌ ignored | سر فعلي (private_key) — لا يُدفع |
| `data/keys/HISTORY.jsonl` | ❌ ignored | ❌ خطأ — مفاتيح عامة فقط، يجب أن يُدفع |
| `data/identity/identity_seal.bin` | ❌ ignored | سر فعلي (ختم تشفيري) — لا يُدفع |

---

## الإصلاح (R-670)

1. **`data/keys/HISTORY.jsonl`** — أُضيف استثناء `!data/keys/HISTORY.jsonl`. يحتوي على مفاتيح عامة فقط (لا private). سجل جنائي — يجب أن يُدفع.

2. **`data/keys/keyring.json`** — بقي مستثنى (صحيح). يحتوي على `private_key` — سر فعلي، لا يجوز دفعه.

3. **`data/identity/identity_seal.bin`** — بقي مستثنى (صحيح). ختم تشفيري — سر فعلي.

---

## التوصية (غير مُنفذة)

استبدال `*.log` في `.gitignore` بقاعدة أكثر أماناً:

```
# بدلاً من: *.log (خطير — يستثني كل السجلات الجنائية)
logs/
nohup.out
```

هذا يسمح بكل ملفات `forensics/*.log` أن تُدفع تلقائياً، و يُبقي فقط مجلدات السجلات (logs/) و ملفات التشغيل (nohup.out) مستثناة.

**الحالة:** موثقة كتوصية، غير مُنفذة (تحتاج قرار المالك).
