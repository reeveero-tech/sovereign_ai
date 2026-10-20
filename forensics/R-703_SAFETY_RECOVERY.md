# R-703 — استعادة الكشف، وحجب الإجراءات الآلية، وتوقيع 256 بت

> بأمر المالك (2026-10-20). التزام ذري واحد فوق `d5f2ea5`، بلا amend ولا
> rebase ولا force-push. الأمر: «يجب أن يكتشف النظام الخطر ويسجله دون أن
> يتحرك تلقائيًا».

## ١) العيب: فحوص سلامة لا ترى التلف (OWNER_REQUIRED بند ١٥)

`IntegrityStatus` تعداد نصي (`str, Enum`) قيمه غير فارغة، لذلك:

```
not IntegrityStatus.CORRUPTED   → False
bool(IntegrityStatus.CORRUPTED) → True
```

| الموضع | الكود قبل R-703 | الأثر |
|---|---|---|
| `backend/memory/biological/instincts.py` (`_detect_threats_to_sovereign`) | `if not self.core.verify_integrity():` | تهديد `core_integrity_compromised` لم يُولَّد قط |
| `backend/memory/defense/watcher.py` (`_detect_integrity_attack`) | `if not self.core.verify_integrity():` | شذوذ `integrity_violation` لم يُسجَّل قط |
| `backend/memory/biological/drives.py` (`update_survival_drive`) | `1.0 if core_integrity else 0.0` | درجة السلامة كانت 1.0 دائمًا |

## ٢) لماذا لا يكفي إصلاح الفحص وحده

الكشف يغذي سلسلة استجابة آلية. جردتُها كلها، وكان بعضها **نشطًا قبل R-703**
من مصدر تهديد آخر (مستوى تهديد ≥3 من الحارس، أو مناعة في حالة قتال):

| المسار الآلي | الإجراء | المُشغِّل |
|---|---|---|
| `instincts._execute_protection_action` | `set_stealth_level(4, mode=3)` + `create_phoenix_seed` + `encrypt_blob` | `protect_sovereign` (حلقة كل 30 ثانية) |
| `instincts.enforce_absolute_security` | `set_stealth_level(4)` + `create_phoenix_seed` | `_threat_response_loop` (كل 10 ثوانٍ عند أي تهديد) |
| `instincts.protect_sovereign_privacy` | `encrypt_blob` + `dynamic.working.clear_user` | `instinct_cycle` |
| `instincts.immortalize_sovereign` | `create_phoenix_seed` لكل حدث للسيد | `instinct_cycle` |
| `ransomware._watch_for_threats` | `create_phoenix_seed` | مستوى تهديد الحارس ≥3 (والكشف المُصلح يرفعه) |
| `controller._execute_action` | `set_stealth_level(4)` + `create_phoenix_seed` | أمر `SYSTEM_COMMAND_EMERGENCY` |

**`encrypt_blob` غير موجودة.** نتيجة `rg -n "def encrypt_blob" backend/` فارغة.
أي مسار يبلغها ينفذ التخفي وphoenix أولًا، ثم يقع في `AttributeError`.

## ٣) الإصلاح

**الوحدة الجديدة `backend/memory/defense/automation_guard.py`:**
- `integrity_compromised(status)`: تحكم بالقيمة (`"corrupted"`)، لا بالصدق
  المنطقي. وتقبل أيضًا `False` المنطقية وtuple. `PARTIAL` ليس تلفًا.
- `report_integrity_violation(source, status)`: تسجل بمستوى CRITICAL
  `R-703 [INTEGRITY]`، ولا تتخذ أي إجراء.
- `block_drastic_action(action, source, /, **context)`: تسجل بمستوى WARNING
  `R-703 [SAFETY]` (سطر لكل مفتاح في الدقيقة) وتعيد True ما دام
  `AUTOMATED_DRASTIC_ACTIONS_ENABLED = False`.
- **الثابت في الكود، وليس متغير بيئة.** إعادة التفعيل قرار مالك بالتزام
  صريح.

**التطبيق:** الفحوص الثلاثة تستعمل `integrity_compromised` و
`report_integrity_violation`. المسارات الست أعلاه تمر بـ`block_drastic_action`
قبل أي إجراء. إجراء الحماية يُوسم `blocked`، والأمن المطلق يعيد
`security_level: detect_only`. الخصوصية والخلود يعودان بلا تنفيذ.

**ما لم يُحجب، عمدًا (مُفصَح عنه):** الاستدعاء اليدوي الصريح لواجهات الدفاع،
وتجديد البذور الدوري (صيانة لا ردة فعل)، و`bootkit.war_boot` و
`initiate_death` (لا مستدعي آليًا لهما).

## ٤) `safety.py`: توقيع الأوامر الخطيرة

| قبل | بعد |
|---|---|
| `sha256(action_id ‖ key).hexdigest()[:16]` (64 بت، بلاحقة سرية وليس HMAC) | `HMAC-SHA256(derive_key("signing"), action_id)`، 64 حرفًا ست عشريًا (256 بت) |
| `signature == expected` | `hmac.compare_digest(...)` (ثابتة الزمن) |
| قبول تواقيع قديمة بمفتاح الجذر (16 حرفًا) | **مرفوضة**. هي تواقيع موافقة مؤقتة لكل أمر، ولا بيانات دائمة تعتمد عليها |

أُزيل استيراد `SOVEREIGN_KEY` من `safety.py` لأنه لم يعد مستعملًا، فنقص
استخدام موسوم `LEGACY-ROOT-KEY` واحد.

**ثبات الزمن، إفصاح صريح:** لا يثبته اختبار ساعة جدارية. الفرق بين مقارنة
`==` ومقارنة ثابتة الزمن لسلسلتين بطول 64 حرفًا ببضع نانوثوانٍ، أي أقل من
ضجيج CI بعدة رتب، فاختبار كهذا يتذبذب أو يمر زورًا. الإثبات بنيوي وقابل
للتكرار:
1. التحقق يستدعي `hmac.compare_digest` (جاسوس `wraps`).
2. حين يُجبَر `compare_digest` على False يُرفض توقيع صحيح، أي أنها الحَكَم
   الفعلي وليس `==` في الخلفية.

`hmac.compare_digest` موثقة في المكتبة القياسية بأنها مصممة ضد هجمات التوقيت.

## ٥) الإثبات: RED ثم GREEN

`backend/tests/invariants/test_r703_safety_recovery.py`، 12 اختبارًا.

- **RED على `d5f2ea5`** (الوحدة موجودة، والمواضع غير موصولة): **10 فشل / 2
  نجاح**. النجاحان هما عدم الإنذار الزائف على VERIFIED/PARTIAL، وكون الثابت
  في الكود. أسباب الفشل كما يلي:
  - الفحوص الثلاثة لا ترى التلف: `not IntegrityStatus.CORRUPTED == False`،
    و`bad=0.0, good=0.0`.
  - مسار الحارس القائم ينفذ التخفي فعلًا: «تخفٍّ آلي نُفّذ».
  - ransomware أنشأ بذرة: `create_phoenix_seed ... Called 1 times`.
  - controller لم يسجل منعًا.
  - التوقيع 64 بت: `assert 16 == 64`.
  - التوقيع المقطوع مقبول.
  - لا `hmac` في `safety`.
- **خطأ اكتشفه الاختبار أثناء التنفيذ:** اسم المعامل `action` تكرر في سياق
  `block_drastic_action`، فوقع إجراء الحماية في «failed» بدل «blocked».
  أُصلح بجعل المعاملين positional-only، وإعادة تسمية مفتاح السياق.
- **GREEN:** 12 نجاح.

## ٦) ما بقي للمالك

1. هل يُعاد تفعيل أي إجراء آلي (كله أو بعضه)؟
2. مصير `encrypt_blob`: تُنفَّذ، أم يُحذف استدعاؤها.
3. أي عميل يكتب ردود موافقة موقعة يجب أن ينتقل إلى HMAC الكامل. لا يوجد
   مولّد آخر في المستودع غير `SafetyGuard.generate_signature`.

البنود ١٦ (السجلات التاريخية) وIssue #7 والنشر والحارس لم تُلمس.
