# NEW_AGENT_INITIAL_AUDIT.md — التدقيق الأولي للوكيل الجديد

**التاريخ:** 2026-10-14 (Asia/Riyadh)
**الوكيل:** وكيل جديد (بدون تاريخ سابق في المشروع)
**المنهج:** قراءة العقد كاملاً، ثم فحص الحالة الفعلية قبل أي تعديل (قانون التحقق).

---

## 1) تشغيل الاختبارات (الحالة الفعلية)

**الأمر:** `python3 -m pytest tests/ backend/tests/ -q`

| الفئة | العدد |
|---|---|
| مجموع الاختبارات المجمَّعة | **278** |
| ناجحة (passed) | **271** |
| متخطاة (skipped) | **7** |
| فاشلة (failed) | **0** |

**ملف الاختبارات المجمَّعة (كل مسارات):** 222 في `tests/` + 56 في `backend/tests/` = 278.

**الاختلاف عن تقارير سابقين:** 277 vs 278. الفرق = 1 اختبار واحد. تحقق لاحقاً في `clean_build_skips.md`.

---

## 2) بنية المستودع

| البند | القيمة |
|---|---|
| ملفات متتبعة (git ls-files) | **591** |
| ملفات .py متتبعة | **272** |
| ملفات .py على القرص | **272** (لا فرق) |
| ملفات غير متتبعة (untracked) | **0** |
| __pycache__ على القرص (غير متتبع) | 40 |
| مجلدات كبيرة | `data/` (runtime، معظمها مُتتبع جزئياً) |
| جذر المشروع | `/home/user/workspace/repo` |

**مجلدات main:** `backend/`, `nexus/`, `guardian/`, `frontend/`, `tests/`, `archive/`, `docs/`, `forensics/`, `audit/`, `scripts/`, `data/`.

**التوزيع:**
- `backend/`: نواة FastAPI (app.py, orchestrator.py, api.py, config.py)
- `nexus/`: NexusCore (منصة منفصلة — معطلة جزئياً، مربوطة عبر compat)
- `guardian/`: الحارس (أمان/نسخ احتياطي)
- `frontend/`: واجهة RTL عربية (245+ ملف JS)

---

## 3) آخر 30 التزاماً (git log)

آخر الالتزامات (رؤوسها):
- `bccc5d17` — fix: Gate 2 CLOSED — R-672 clean clone run (277/271 tests pass)
- سابقون: Gate 1/3/4/5 CLOSED, R-616 (Merkle anchor), R-669 (KeyStatus duality), R-620 (HMAC قلق موثق).

النمط الملاحظ: كل بوابة أُغلقت بـ "CLOSED" مع تحقق موثق (log جنائي). لا عيوب واضحة في الرسائل — لكن يجب التحقق من الادعاءات قبل تصديقها.

---

## 4) فحص forensics/

**ملفات forensics الموجودة (14):**
- `GITIGNORE_AUDIT.md`
- `KEY_LOSS_TIMELINE.md` — التحقيق في فقدان المفتاح الأصلي (11,777 حدث فاشل التوقيع)
- `asymmetric_defense_audit.md` — 1768 دالة، 5 مرشحين فقط، 0 ثغرة متبقية
- `boolean_message_audit.md` — 30 دالة، 0 تناقض
- `gate4_green.log`, `gate4_green_v3.log`, `gate4_red.log`, `gate4_red_v3.log`
- `gate5_baseline.log`, `gate5_green.log`, `gate5_true_red.log`
- `key_state_duality.md`
- `rotation/after.log`, `rotation/before.log`

**ملاحظة مهمة:** تقرير `asymmetric_defense_audit.md` صرّح بحدوده (0.3% فقط فُحص يدوياً — 5 من 1768). هذه المسألة الثالثة في المهمة.

---

## 5) فحص .gitignore

**البند الحرج:** `.gitignore` يتجاهل `data/` و `__pycache__/` و `node_modules/` و `venv/`. لا ملفات "جنائية" مستثناة — التدقيق السابق (R-670) أصلح HISTORY.jsonl.

**البيانات الحقيقية على القرص (غير متتبعة):**
- `data/sovereign_core/ledger.jsonl` — **غير موجود** (هذا اكتشاف مهم — الحجم المذكور 45MB ليس موجوداً في clone)
- `data/keys/keyring.json` — **غير موجود** (السر الخاص — مبرر)
- `data/identity/identity_seal.bin` — **غير موجود** (الختم — مذكور كـ polluted)
- `data/key.secret` — موجود (43 حرفاً base64url)

**تناقض مكتشف:** تقارير سابقين تقول "ledger.jsonl موجود بـ 116,910 حدث" و "identity_seal.bin موجود لكنه polluted". الحقيقة: **كلا الملفين غير موجودين على القرص في clone الجديد**. هذا يجب أن يُوثق.

---

## 6) محاولة البناء من الصفر (clone نظيف)

**النتيجة:** 271 passed + 7 skipped = 278 اختبار. **لا فشل واحد.**

**لكن:** انظر المسألة 2 (أدناه) — الاختلاف 277 → 271 + 7 = 6 اختبارات تحولت. تحقق في `clean_build_skips.md`.

---

## 7) المسائل الثلاث في تقرير الوكيل السابق (الجزء الخامس من العقد)

### المسألة 1: composite.py هو مرآة، لا مقياس
**تحقق فعلي:** `composite.py` يستخدم `primitives` ويعيد `composite_score`. الصيغة الحالية (خط 82-97):
```
composite = (
    0.25 * keys_ratio +
    0.20 * ledger_ratio +
    0.15 * anchors_verified_ratio +
    0.15 * no_mocks_in_production +
    0.15 * no_orphan_modules +
    0.10 * files_imported_count_normalized
)
```

**تحليل العيوب:**
1. `files_imported_count` (114 من 272) يُدخل الصيغة كـ `no_orphan_modules` (ثنائي) — يُجمّد الفرق بين 114 و 272. **موثق صحيحاً في العقد.**
2. `tests_passing_count` غير مُدرج في الصيغة — العقد صحيح.
3. `mocks_outside_tests_count` غير موجود كعامل ضارب — العقد صحيح.

**الاختيار:** يجب تحليل الخيارات الثلاثة (أ/ب/ج) واختيار واحد مع توثيق.

### المسألة 2: 277 → 271 + 7 skips في clone نظيف
**تحقق فعلي:**
- clone نظيف: 271 passed + 7 skipped (إجمالي 278)
- المشروع الأصلي: 277 passed + 1 skip (إجمالي 278)
- الفرق = 6 (ليس 4 كما قال سابقون — عقد المستخدم قال "4 اختبارات عُدّلت")

تحتاج `clean_build_skips.md` بجدول كامل.

### المسألة 3: تدقيق Asymmetric Defense ضيق
**تحقق فعلي:**
- `forensics/asymmetric_defense_audit.md` يوثق حدود التدقيق (5 مرشحين فقط)
- 0 ثغرة Asymmetric Defense متبقية (موثقة)

**لكن:** العقد يطلب تدقيق "Silent Failure" أوسع (except: pass, except Exception: continue, return None, if cond: pass). هذا لم يُنفذ بعد.

**نتيجة المسح المبدئي:** 75 موقع `except: pass` في كود الإنتاج (باستثناء الاختبارات):
- 16 لديها تعليق تبرير (5 ملفات)
- **59 بلا تعليق تبرير** (12+ ملفات)
- أعلى الملفات: `backend/predictive/predictive_engine.py` (16), `backend/config.py` (7), `backend/memory/core.py` (7)

---

## 8) محاولة كشف الغاية (الجزء السادس من العقد)

**القراءة الأولية (من docs/):**
- `docs/PROJECT_CHARTER.md` يقول: "Sovereign AI (SOVRA) مشروع تجريبي لبناء 'عقل سيادي' — نظام ذكاء اصطناعي يتعلم ويتطور ذاتياً."
- الواجهة: "SOVRA · Sovereign Cognitive Operating System"
- المكونات: `consciousness/` (awareness, introspection, identity_core, self_model), `memory/` (biological, defense, store, core), `predictive/`, `simulation/`, `quantum/`, `sovereign/` (keys, ledger, agent_ledger, controller, will, alignment, directives), `nexus/` (NexusCore), `guardian/` (master_guardian, self_evolve, emergency_breaker, integrity_checker), `Mr.py` (محرك ولاء).

**الغاية المعلنة (من docs):** بناء "عقل سيادي" — نظام ذكاء اصطناعي يتعلم، يتطور، يطلب إذن السيد قبل أي تعديل ذاتي، يعمل على منصات خارجية مؤقتاً، ينتقل لاحقاً إلى تشغيل سيادي كامل.

**الغاية الفعلية (من الكود — تحقق لاحقاً في GOAL_DISCOVERY.md):** ستُكتشف في التقرير المخصص.

---

## 9) ملخص الحالة (فرضية، لا حقيقة — سيُتحقق منها)

| الادعاء (من تقارير سابقين) | الحقيقة الفعلية |
|---|---|
| 277 اختبار ناجح | **271 passed + 7 skipped** (فرق 6) |
| ledger.jsonl موجود (116,910 حدث) | **غير موجود في clone** |
| identity_seal.bin موجود (polluted) | **غير موجود في clone** |
| keyring.json موجود | **غير موجود في clone** (مبرر — سر) |
| 8 invariants | تحقق لاحقاً |
| 6 compat modules | تحقق لاحقاً |
| primitives.py يعيد 8 مؤشرات | **موثق في composite.py — لا يُعاد 100 بسهولة (الدرجة الفعلية 55.0)** |
| composite.py يعيد 100.0 | **الدرجة الفعلية 55.0** (راجع المسألة 1) |

**ملاحظة مهمة:** الدرجة الفعلية `composite_score = 55.0` وليس 100.0. هذا يتعارض مع ادعاء "100.0" في بعض التقارير. تحقق لاحقاً.

---

## 10) خطوات العمل (الجزء الخامس من العقد)

1. ✅ تشغيل كل الاختبارات (فوق)
2. ✅ فحص بنية المستودع (فوق)
3. ✅ فحص آخر 30 التزاماً (فوق)
4. ✅ فحص forensics/ (فوق)
5. ✅ فحص .gitignore (فوق)
6. ✅ محاولة البناء من الصفر (فوق)
7. ✅ كتابة هذا التقرير (هذا الملف)

**التالي:** تنفيذ المسائل الثلاث (الجزء الخامس) — composite.py, clean_build_skips.md, silent_failure_audit.md, test_no_silent_exceptions.py.

---

## 11) حدود هذا التقرير

- التقرير لا يوثق "النجاح" — يوثق الحالة الفعلية فقط.
- ادعاءات "CLOSED" من سابقين لم تُصدق دون تحقق — انظر القسم 9.
- التقرير مكتوب **قبل** أي تعديل على الكود (كما يطلب العقد).

