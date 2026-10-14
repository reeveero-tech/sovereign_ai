# ROADMAP_V2.md — خارطة طريق المرحلة الثانية: الطبقة السيادية

## الأصل

هذا المستند توثيق نصّي للمرحلة الثانية من المهمة (المستلمة من المالك).
هو **خارطة طريق ملزمة**، وليس مصدر حقيقة تقني — الحقيقة هي الكود
والاختبارات والتشغيل. هذا المستند يصف *ما يجب بناؤه*، والكود يثبت *أنه بُني*.

---

## الحالة الحالية (قبل بدء المرحلة الثانية)

- الفرع: `main`، آخر التزام: `213b224` (مُدفع إلى origin).
- الاختبارات: **96 ناجحة** في مجموعة واحدة (`EXITCODE=0`).
- العطل المُصلح في المرحلة الأولى: nexus lifecycle (state=running)،
  المسار الأصلي `GET /nexus/recommendations`، عزل بيانات الاختبار
  (`SOVEREIGN_DATA_ROOT`).
- **الجرح المفتوح**: `data/sovereign_core/ledger.jsonl` يحتوي 7344 حدثًا
  كل توقيعاتها فاشلة. السبب الجذري مُحدد (اختبار سابق حذف المفتاح،
  ثم أُنشئ مفتاح جديد). المفتاح الأصلي فُقد.
- المكونات المُحيَاة في المرحلة الأولى: `backend/Mr.py` (محرك الولاء)،
  `guardian/` (نقطة `/guardian/status`)، `archive/root_strays` (جرد).

---

## المبدأ الحاكم

> **"لا نُصلح الماضي، بل نُثبّته. لا نُخفي الجرح، بل نُطوّقه بختم جديد."**

7344 حدثًا بتوقيعات فاشلة ليست "بيانات تالفة" — هي **دليل جنائي**.
المفتاح الأصلي فُقد. هذا حدث تاريخي حقيقي. إعادة التوقيع بالمفتاح
الجديد = **تزوير**. الحذف = **إنكار**. الحل السيادي الوحيد:
نُبقيها كما هي، ونُضيف فوقها **طبقة إثبات جديدة** (مرساة تشفيرية).

---

## القواعد الدستورية (موروثة من المرحلة الأولى، مؤكدة)

1. **لا حذف**. لا ملف، لا سطر، لا اختبار، لا تعليق، لا تبعية.
2. **لا تعليق** كود. **لا أرشفة**. **لا stub دائم**. **لا mock خارج الاختبارات**.
3. **لا رجوع إلى المالك**. الوكيل صاحب القرار التقني.
4. **لا اعتماد على .md كمصدر حقيقة** — الكود والاختبارات والتشغيل هي الحقيقة.
5. **التوثيق يُدفع مع العمل في نفس الالتزام** — لا دفعات منفصلة.
6. **الإضافة بلا قيد، الحذف ممنوع مطلقًا**.

---

## المراحل والبنود

### المرحلة صفر: التحقق من الجريمة قبل بناء السجن

**الملف الناتج**: `forensics/KEY_LOSS_TIMELINE.md`

يجب الإجابة بالأدلة من الكود قبل أي إصلاح:

| # | السؤال | مصدر الدليل |
|---|--------|-------------|
| 1 | متى فُقد المفتاح الأصلي؟ | تواريخ الأحداث في ledger، git log، وجود/غياب `data/key.secret` |
| 2 | هل فُقد مرة أم عدة مرات؟ | توزيع التوقيعات الفاشلة (متجاورة زمنيًا أم متقطعة) |
| 3 | هل `test_persistent_key_survives_restart` موجود في main؟ | فحص git — إن لم يكن موجودًا، يُعاد إنشاؤه كأولوية قصوى |
| 4 | هل هناك مسار آخر يحذف/يكتب فوق `key.secret`؟ | فحص كل `os.remove`، `shutil.rmtree`، `Path.unlink`، `open(...,'w')` على مسارات `key/secret/data/` |
| 5 | هل يكتب الكود على ledger.jsonl بعد فشل التوقيع؟ | فحص مسارات الكتابة — إن نعم، جريمة أعمق (نظام يكتب أحداثًا يعرف أنها فاشلة) |

**القاعدة**: لا يبدأ الإصلاح قبل اكتمال هذا الملف. هو السند القانوني.

---

### المرحلة الأولى: المفتاح السيادي (Key Sovereignty)

**الملفات الناتجة**:

```
backend/sovereign/keys/__init__.py
backend/sovereign/keys/keyring.py
backend/sovereign/keys/verifier.py
backend/sovereign/keys/rotation.py
data/keys/HISTORY.jsonl          (سجل لا يُحذف منه شيء أبدًا)
```

**المكونات**:

1. **`KeyRing`** — يحمل كل المفاتيح التاريخية، لكل مفتاح:
   - `key_id` فريد (sha256 أول 16 حرفًا من المفتاح العام)
   - `valid_from`, `valid_until` (ISO8601)
   - `public_key`, `private_key` (مشفر أو ملف 0600 منفصل)
   - `reason_for_retirement`: `"lost" | "rotated" | "compromised" | "expired"`
   - `notes` (نص حر)

2. **`KeyRing.load_from_disk()` / `save_to_disk()`** — تخزين في `data/keys/`
   مع سجل `HISTORY.jsonl` **لا يُحذف منه سطر أبداً**.

3. **`SignatureVerifier`** — يستخرج `key_id` من الحدث، يبحث في KeyRing، يتحقق:
   - إذا وُجد المفتاح → تحقق فعلي
   - إذا لم يوجد → `UNVERIFIABLE_MISSING_KEY` (وليس `INVALID`)
   - **الفرق جوهري**: `UNVERIFIABLE_MISSING_KEY` = "لا نعرف"، `INVALID` = "نعرف أنه مزوّر". لا خلط بينهما أبدًا.

4. **`KeyRotation`** — واجهة `rotate(reason)`:
   - تُنتج مفتاحًا جديدًا
   - تُسجّل القديم كـ `retired`
   - تكتب حدث `KEY_ROTATED` في ledger موقّعًا بالمفتاح الجديد

**القاعدة الصارمة**: أي حدث جديد في ledger من الآن يجب أن يحمل `key_id`.
أي حدث قديم بدون `key_id` يُعامل كـ `LEGACY_PRE_KEYRING` — لا يُعاد
توقيعه، لا يُحذف، لا يُخفى.

---

### المرحلة الثانية: مرساة اليدجر (Ledger Anchoring)

**الملف الناتج**: `backend/sovereign/ledger/anchor.py`

**المكونات**:

1. **`compute_merkle_root(events)`** — شجرة Merkle (كل حدث يُجزّأ بـ sha256).

2. **`anchor_batch(batch_range, keyring)`** — يأخذ نطاقًا (مثلاً 0–7343)،
   يحسب Merkle root، ويُنتج سجلًا في `data/sovereign_core/ledger.anchors.jsonl`:

```json
{
  "anchor_id": "...",
  "batch_start": 0,
  "batch_end": 7343,
  "merkle_root": "sha256:...",
  "reason": "PRE_KEYRING_UNSIGNED_BATCH",
  "key_id": "<key_id الجديد>",
  "signature": "<توقيع المرساة بالمفتاح الجديد>",
  "anchored_at": "ISO8601",
  "notes": "7344 events with unverifiable signatures due to lost key. Merkle root anchors their exact content. Any future modification of any event in this range will change the root and be detectable."
}
```

3. **`verify_anchor(anchor, ledger)`** — يتحقق أن الأحداث في النطاق لا تزال
   تُنتج نفس Merkle root. إذا تغيّر أي بايت في أي حدث، تفشل المرساة.
   **هذا يعني**: لم "نُصلح" التوقيعات القديمة، لكن التلاعب بها صار
   مستحيلًا دون كشفه.

4. **مسار `/ledger/verify`** — يُعيد تقريرًا:
   - عدد الأحداث المُتحقَّق منها بالمفتاح
   - عدد المراسي
   - عدد الأحداث المحمية بمرساة
   - عدد الأحداث المجهولة

**الفكرة الجوهرية**: لا نكذب على التاريخ، ولا نُلغيه — نُطوّقه بختم يشهد عليه.

---

### المرحلة الثالثة: الاختبارات الثابتة (Invariants)

**المجلد الناتج**: `backend/tests/invariants/`

هذه اختبارات تتحقق من **بنية المشروع نفسه** — تفشل ليس عندما "يعمل
الكود خطأً"، بل عندما "يختل شكل المشروع".

| # | الملف | ما يتحقق منه |
|---|-------|--------------|
| 1 | `test_no_orphan_modules.py` | كل ملف .py في `backend/` و `guardian/` إما مستدعى، أو نقطة دخول، أو مُدرج في `INVENTORY.py` بسببه. يتيم جديد = فشل |
| 2 | `test_no_unsigned_ledger_events.py` | كل حدث إما موقّع بمفتاح في KeyRing، أو داخل نطاق مرساة، أو مُعلَّم `legacy_unverified: true`. أي حدث لا ينتمي للثلاثة = فشل |
| 3 | `test_compat_sunset_criteria.py` | كل وحدة في `backend/compat/` لها `SUNSET_CRITERIA` موثقة. وحدة جديدة بدون معيار إزالة = فشل |
| 4 | `test_no_mock_outside_tests.py` | بحث عن `Mock()`, `MagicMock`, `patch(` خارج `tests/`. أي وجود = فشل |
| 5 | `test_keyring_immutability.py` | `data/keys/HISTORY.jsonl` لا يُحذف منه سطر أبدًا (مقارنة لقطة حالية بلقطة سابقة عبر git). نقص الأسطر = فشل |
| 6 | `test_all_entrypoints_respond.py` | كل مسار HTTP مسجّل في FastAPI يُعيد رمزًا غير 500. يكشف المسارات الميتة |

**الغرض**: هذه هي "جهاز المناعة السيادي". بعد كتابتها، أي جولة مستقبلية
من الوكيل ستُفشل نفسها إذا انحرفت عن الدستور.

---

### المرحلة الرابعة: نمط التين الخانق (Strangler Fig) لطبقة التوافق

**الملف الناتج**: `backend/compat/__meta__.py`

**المكونات**:

1. **قاموس `COMPAT_LIFECYCLE`** عالمي:

```python
COMPAT_LIFECYCLE = {
    "nexus_lifecycle": {
        "created": "ISO8601",
        "reason": "initialize_nexus لا يستدعي engine.start()",
        "target_replacement": "backend/nexus/core/engine.py:initialize_nexus",
        "sunset_criteria": "engine.start() مُدمج في initialize_nexus + 30 يوماً بدون استدعاء لـ compat",
        "call_count": <يُقاس تلقائياً>,
        "status": "active" | "pending_sunset" | "legacy_retained"
    },
    ...
}
```

2. **Decorator `@compat_tracked(name)`** على كل دالة/كلاس في compat
   يُسجّل عدد الاستدعاءات.

3. **مسار `/compat/status`** يعرض الجدول.

4. **اختبار دوري في invariants**: أي compat له `call_count == 0` لمدة
   30 يومًا يجب أن ينتقل إلى `pending_sunset` ويُوثّق.

**القاعدة الصارمة**: حتى بعد sunset، **لا يُحذف الملف**. يُنقل إلى
`backend/compat/_legacy/` ويُبقى. الدستور يمنع الحذف.

---

### المرحلة الخامسة: نقاط السيادة (Sovereignty Score)

**الملف الناتج**: `backend/sovereign/score.py`

**المعادلة**:

```
SOVEREIGNTY_SCORE = {
  "files_reachable": 0.0-1.0,        # % ملفات مستدعاة
  "modules_tested": 0.0-1.0,        # % وحدات لها اختبار
  "ledger_verified": 0.0-1.0,      # % أحداث موثقة (بمفتاح أو مرساة)
  "ledger_anchored": 0.0-1.0,      # % أحداث داخل مرساة
  "compat_pending_sunset": 0.0-1.0, # % compat مع sunset criteria
  "no_mocks_in_prod": 0/1,          # ثنائي
  "invariants_passing": 0/1,        # ثنائي
  "final_score": 0.0-1.0
}
```

**التوثيق المطلوب**:
- `forensics/SOVEREIGNTY_BEFORE.json` — قبل التعديلات
- `forensics/SOVEREIGNTY_AFTER.json` — بعد التعديلات
- الفرق بينهما = دليل التقدم الحقيقي

**المسار**: `/sovereignty/score` (قراءة فقط).

---

### المرحلة السادسة: ليدجر الوكيل (Self-Audit Ledger)

**الملف الناتج**: `forensics/agent_ledger.jsonl`

منفصل عن ledger المشروع. سطر لكل إجراء يقوم به الوكيل:

```json
{"ts":"ISO8601","phase":"1","action":"created KeyRing","files_touched":[...], "before_hash":"sha256:...", "after_hash":"sha256:...", "reason":"...", "verified_by":["test_keyring_immutability"]}
```

**القاعدة**: قبل كل تعديل `before_hash` لشجرة الملفات، بعد كل تعديل
`after_hash`. هذا يجعل عمل الوكيل قابلًا للتدقيق بعد سنوات.

---

### المرحلة السابعة: التحقق النهائي

**الخطوات**:

1. شغّل كل الاختبارات — يجب أن يرتفع العدد من 96 إلى 120+ على الأقل.
2. شغّل invariants كلها — يجب أن تمر جميعها.
3. احسب Sovereignty Score — يجب أن يكون `AFTER > BEFORE`.
4. اضغط المشروع نظيفًا — `git status` نظيف، كل توثيق مدفوع مع عمله.
5. اكتب `REPORT_V2.md` في جذر المستودع يشرح:
   - ماذا فعلت، لماذا
   - ما الفرق في الدرجة (BEFORE vs AFTER)
   - القرارات السيادية (خصوصًا قرار عدم إعادة التوقيع)

---

## معايير القبول النهائية

- [ ] لا حدث واحد في ledger بدون تصنيف (موقّع / مرساة / legacy_unverified)
- [ ] KeyRing يعمل ويحفظ التاريخ كاملاً
- [ ] `verify_anchor` يفشل إذا غُيّر أي بايت في نطاق مُرسى
- [ ] الاختبارات الثابتة (invariants) كلها تمر
- [ ] كل compat له sunset criteria موثقة
- [ ] Sovereignty Score `AFTER > BEFORE` بفرق موثق
- [ ] `agent_ledger.jsonl` موجود ويحتوي سطرًا لكل إجراء
- [ ] لا حذف. لا mock في الإنتاج. لا توثيق مؤجل

---

## ترتيب التنفيذ (غير قابل للتفاوض)

```
المرحلة صفر  →  forensics/KEY_LOSS_TIMELINE.md     (يجب أن يكتمل أولًا)
المرحلة 1   →  KeyRing + SignatureVerifier + Rotation
المرحلة 2   →  Merkle anchor + /ledger/verify
المرحلة 3   →  invariants (6 اختبارات)
المرحلة 4   →  compat lifecycle + __meta__.py + /compat/status
المرحلة 5   →  Sovereignty Score + BEFORE/AFTER
المرحلة 6   →  agent_ledger.jsonl (يُكتب خلال كل المراحل)
المرحلة 7   →  التحقق النهائي + REPORT_V2.md + push
```

**الدور**: أنت لست مصلحًا. أنت **أمين السيادة**.
