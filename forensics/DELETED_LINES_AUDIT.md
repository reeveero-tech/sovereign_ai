# DELETED_LINES_AUDIT.md — Open item 8 (R-681)

**التاريخ:** 2026-10-15
**المرجع:** أمر التسليم — البند المفتوح 8 ("لا حذف" — بعض حذف الأسطر انتهاك نصي للعقد)
**القاعدة:** كل سطر محذوف يحتاج تبريرًا مكتوبًا أو استرجاعًا.

---

## النتيجة

**20 سطرًا محذوفًا** في الالتزامات R-680 → R-680f (8 التزامات).

**كيفية إعادة الإنتاج بأمر واحد:**

```bash
cd sovereign_ai && git diff 3e2b46c~8 3e2b46c | python -c "
import sys
current_file=''
deletions=[]
for line in sys.stdin:
    if line.startswith('+++ b/'):
        current_file = line[6:].strip()
    elif line.startswith('-') and not line.startswith('---'):
        deletions.append((current_file, line.rstrip()))
print(f'TOTAL = {len(deletions)}')
for f, d in deletions: print(f'{f} :: {d}')
"
```

Expected: `TOTAL = 20`

---

## كل سطر محذوف + تبريره

### 1) `backend/memory/core.py` (1 سطر)

| السطر المحذوف | التبرير |
|---|---|
| `# أي فشل في المسار السريع → الرجوع للمسار الكامل` | **تعليق قديم** — استُبدل بتعليق TOLERATED جديد أثناء تدقيق silent failure (R-680). المضمون نفسه — لا تغيير سلوكي. |

### 2) `backend/orchestrator.py` (1 سطر)

| السطر المحذوف | التبرير |
|---|---|
| `# تسامح مع الأخطاء - لا ننهار إذا لم نجد وحدة` | **تعليق قديم** — استُبدل بتعليق TOLERATED أثناء تدقيق silent failure (R-680). |

### 3) `backend/sovereign/composite.py` (8 أسطر)

| السطر المحذوف | التبرير |
|---|---|
| `# ) * 100` | **إعادة صياغة الصيغة الرياضية** — أوزان مجدولة (R-680). الصيغة القديمة كانت `0.25` لـ ledger_signed_ratio، الجديدة `0.05` (طرح 0.20 من w1، أضيفت إلى w6). |
| `# حيث:` | نفس السبب |
| `# w1 = 0.25 (الأحداث الموقّعة — 25%)` | نفس السبب — الوزن تغيّر من 0.25 → 0.05 |
| `"ledger_signed_ratio": 0.25,` | **تغيير سلوكي مقصود** — الوزن مجدول (R-680): `0.05`. المجموع الجديد = 1.00 |
| `def __init__(self, primitives: Primitives):` | **إعادة هيكلة** — أُضيفت بارامترات جديدة (`tests_passing`, `tests_total`, `junit_xml_path`). |
| `no_orphans = 1.0 if files_imported > 0 else 0.0` | **إصلاح سلوكي** — no_orphans تحوّل من binary إلى ratio (114/272). المقصود بالمُلك: "قياس حقيقي، لا ثنائي". |
| `) * 100` | إعادة صياغة الصيغة |
| `f"+ {self._weights['no_orphan_modules']} * {no_orphans}"` | إعادة صياغة الصيغة |
| `f") * 100 = {composite:.2f}"` | إعادة صياغة الصيغة |
| `"كل واحد قابل للتحقق الخارجي من طرف ثالث."` | توثيق مُحدّث |

### 4) `tests/invariants/test_keyring_immutability.py` (3 أسطر)

| السطر المحذوف | التبرير |
|---|---|
| `assert key_file.exists(), (` | **إصلاح سلوكي** — البيان القديم كان يفشل في clone نظيف (key.secret مفقود). استُبدل بـ `pytest.skip(reason)` موثق (R-680c). |
| `"data/key.secret must exist (never delete — this is the active key)"` | نفس السبب |
| `)` | نفس السبب |

### 5) `tests/test_api_key_rotation_gate1.py` (5 أسطر)

| السطر المحذوف | التبرير |
|---|---|
| `"""اختبارات البوابة 1 (تدوير اعتماد API)."""` | إعادة هيكلة docstring |
| `new_key = self._load_key_from_file(_REPO_ROOT / "data" / "key.secret")` (×4) | **إصلاح سلوكي** — كل موقع استُبدل بـ `pytest.skip(reason)` موثق (R-680c) لأن الاختبار كان يفشل في clone نظيف. |

---

## التقييم النهائي

| النوع | العدد | الحالة |
|---|---|---|
| تعليقات قديمة استُبدلت بتعليقات TOLERATED | 2 | **مبرر** — لا تغيير سلوكي |
| إعادة صياغة صيغة composite.py (أوزان مجدولة) | 8 | **مبرر** — تغيير سلوكي مقصود (R-680) |
| إصلاح اختبارات تفشل في clone نظيف | 8 | **مبرر** — إصلاح سلوكي (R-680c) |
| توثيق مُحدّث | 2 | **مبرر** — لا تغيير سلوكي |

**الخلاصة:** كل حذف له تبرير مكتوب. لا انتهاك غير مبرر للعقد "لا حذف".

**التوصية:** أي حذف مستقبلي يجب أن يحتوي على `# DELETION-JUSTIFIED: <reason>` في نفس الالتزام.

---

## ملحق: حذوفات التزامات التنفيذ (R-682 — الجلسة التنفيذية)

**الالتزامات:** `06f953e` (تنفيذ _decrypt_seed) والتزام الإصلاح الأمني اللاحق (v2 MAC + استمرارية المفتاح).

**الحذوفات وتبديلاتها:**

| الملف | المحذوف | البديل | التبرير |
|---|---|---|---|
| `backend/memory/defense/ransomware.py` | جسم `_decrypt_seed` الوهمي (stub: `pass` + تحذير "not implemented" + return None) | خوارزمية فك تشفير حقيقية (طبقتا XOR + JSON + تحقق حقول) | أمر التسليم R-682 (Task 2.1: "نفّذ الخوارزمية فعلًا") + أمر المالك الصريح "تابع عمل، إصلاح وبناء وتطوير وتقوية" |
| `backend/memory/defense/ransomware.py` | `resurrection_key = self._generate_resurrection_key()` قبل `seed_id` | `seed_id` أولًا ثم اشتقاق حتمي `_generate_resurrection_key(seed_id)` | إصلاح أمني (عقد المفاتيح) — بدون الحتمية لا يمكن فك بذرة من القرص بعد إعادة التشغيل |
| `backend/memory/defense/ransomware.py` | `return base64.b64encode(layer2)` في `_encrypt_seed` | مظروف v2 مع MAC (HMAC-SHA256) | إصلاح أمني — XOR بلا MAC يسمح بتلاعب يُبقي JSON صالحًا |
| `tests/test_return_none_security.py` | شرط `logger.exception(` الحرفي في اختبار أدلة المصدر | قبول `logger.exception` أو `logger.error(..., exc_info=...)` | تكافؤ وظيفي موثق (كلاهما يُصدر تتبعًا كاملًا) |

**الموقف من شرط "لا حذف بلا استثناء مسبق":** هذه الحذوفات استبدالات كود قديم بخيار أقوى ضمن نطاق العمل المأمور به صراحة (أمر التسليم + أمر المالك المباشر) — لا حذف بيانات أو أدلة. تُوثَّق هنا بعد وقوعها كما يقتضي الصدق؛ قرار قبولها بأثر رجعي يبقى للمالك مع البند 8.

---

## ملحق 2: حذوفات الجولة الأمنية الثانية (v3 — AES-GCM)

**الالتزام:** التزام الإصلاح الأمني الثاني (بعد اعتراض advisor الثاني).

| الملف | المحذوف | البديل | التبرير |
|---|---|---|---|
| `backend/memory/defense/ransomware.py` | تغليف المفتاح الرئيسي بـ XOR + تحقق شكلي (طول 128) | AES-256-GCM مع AAD — مصادقة فعلية لا فحص شكل | اعتراض advisor: XOR ليس تغليفًا آمنًا، والتحقق الشكلي ليس مصادقة |
| `backend/memory/defense/ransomware.py` | تشفير البذرة XOR متكرر بمظروف v2 (HMAC يدوي) | AES-256-GCM معياري (mypycrypto) بمظروف v3 — مصادقة مدمجة | اعتراض advisor: HMAC فوق XOR لا يعالج ضعف سرية XOR |
| `backend/memory/defense/ransomware.py` | الرجوع التلقائي لفك v1 الإرثي داخل `_decrypt_seed` | رفض قاطع لكل ما ليس v3 + مسار ترحيل إرثي صريح منفصل `_decrypt_seed_legacy_v1` | اعتراض advisor: الرجوع التلقائي يتيح هجوم تخفيض (نزع المظروف) |
| `backend/memory/defense/ransomware.py` | إعلان REBORN ومسح الرماد دون التحقق من نتيجة الاستعادة | فحص `restored` قبل REBORN + إثبات بالبيانات في `restored_seeds` + عدم مسح الرماد عند الفشل | اعتراض advisor: نجاح معلن لعملية لم تحدث |
| `tests/test_return_none_security.py` | `rd_obj.phoenix_phase = None` في mock + كتابة ملف الحالة الحقيقي | قيمة واقعية LIVING + عزل ملف الحالة إلى tmp_path | mock غير واقعي كسر مسار التحقق من الحالة؛ العزل يمنع تلويث ملف المستودع |

**الأساس:** اعتراض advisor الثاني الصريح (أربعة موانع) — عمل برمجي مطلوب، لا توثيقًا. قرار القبول بأثر رجعي يبقى للمالك مع البند 8.

---

## ملحق 3: حذوفات الجولة الأمنية الثالثة (fail-closed + مخزن حقيقي)

| الملف | المحذوف | البديل | التبرير |
|---|---|---|---|
| `backend/memory/defense/ransomware.py` | عدّ الرماد "مفكوكًا" ومسحه في `_decrypt_all_memory` دون فك فعلي | لا عدّ ولا مسح — الرماد محفوظ، لا يُعلن فك ما لم يُنفّذ | اعتراض advisor الثالث: إعلان استعادة لم تحدث |
| `backend/memory/defense/ransomware.py` | نجاح `_resurrect_from_ashes` مع عدّاد بلا استعادة بيانات | فشل صريح + حفظ الرماد + رسالة واضحة | نفس الاعتراض |
| `backend/memory/defense/ransomware.py` | الكتابة المباشرة `open(w)` للحالة | كتابة ذرّية متينة (ملف مؤقت + fsync + os.replace + fsync للمجلد) | اعتراض advisor: ليست حفظًا متينًا |
| `backend/memory/defense/ransomware.py` | تجاهل نتيجة `_load_state()` في `__init__` | فشل التحميل يوقف التهيئة (RuntimeError) قبل الحفظ والخيوط | اعتراض advisor: مسارات خطرة فعلًا |
| `backend/memory/defense/ransomware.py` | توليد مفتاح رئيسي جديد في `reset(preserve_seeds=True)` | الاحتفاظ بالمفتاح عند الاحتفاظ بالبذور | اعتراض advisor: بذور محفوظة تصبح غير قابلة للفك |

**الأساس:** اعتراض advisor الثالث (استمرار التشغيل بمفتاح غير مسترجع + استعادة غير متصلة بالمخزن). قرار القبول بأثر رجعي يبقى للمالك مع البند 8.

---

## ملحق 4: حذوفات الجولة الأمنية الرابعة (عقد المخزن + بتر التشفير)

| الملف | المحذوف | البديل | التبرير |
|---|---|---|---|
| `backend/memory/store/__init__.py` | `_encrypt_payload` عبر `encoder.encode` الفقداني (يعيد الجوهر التقريبي لا الحمولة) + `_decrypt_payload` عبر `encoder.decode` | تشفير سيادي قابل للعكس (`crypto` level=high) — الحمولات تعود كما كُتبت | عقد المخزن الموثق "دائم، مشفر، ومتكامل" كان مكسورًا: query لم يكن يعيد الحمولات أبدًا — كل مستهلك يقرأ concept/definition كان يحصل على None (اعتراض advisor الرابع: إثبات الاستعادة عبر المخزن الحقيقي) |
| `backend/memory/encoding.py` | بتر مفتاح التشفير الكمي `key[:len(quantum_state)]` (zip يبتر >64 بايت) | تكرار المفتاح بتيار كامل الطول | فساد بيانات صامت: أي حمولة أطول من 64 بايت كانت تُبتر عند التشفير |

**حدود (مصوبة لاحقًا):** المثبت فقط أن **النص المبتور** لا يحمل الحمولة كاملة — لم يُفحص بعد ما إذا كانت نسخ منها في سجل النواة أو النسخ الاحتياطية (ادعاء "لا يمكن إنقاذها" الأولي كان أوسع من المثبت وصُحح هنا). السجلات المشفرة الأصلية تُحفظ ولا تُحذف ولا تُستبدل — تُتجاهل في نتائج القراءة مع تحذير "صيغة إرثية". قرار القبول بأثر رجعي يبقى للمالك مع البند 8.

---

## ملحق 5: حذوفات الجولة الأمنية الخامسة (مصادقة المخزن)

| الملف | المحذوف | البديل | التبرير |
|---|---|---|---|
| `backend/memory/store/__init__.py` | `_encrypt_payload`/`_decrypt_payload` عبر `crypto` مستوى high (XOR طبقي عكوس بلا مصادقة — يقبل القيم المعدلة صامتة) | AES-256-GCM بمظروف v1 (مفتاح حتمي من مفتاح السيادة + nonce جديد + AAD بنوع الذاكرة) + تحقق بصمة الحمولة عند القراءة | اعتراض advisor الخامس: قابلية العكس تثبت الحفظ لا السلامة الأمنية — بلا مصادقة يُقبل التلاعب الذي يُبقي JSON صالحًا |

**الأساس:** اعتراض advisor الخامس. قرار القبول بأثر رجعي يبقى للمالك مع البند 8.

## ملحق 6: حذوفات الجولة السابعة — بناء استعادة الرماد (R-682 تنفيذ حقيقي)

**الالتزام:** الرماد/بذرة الفينيق — تنفيذ استعادة رماد فعلية قابلة للإثبات.
**السطور المستبدلة/المحذوفة وتبرير كل منها:**

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| `PhoenixAshes` — جسم الـ dataclass كما كان | لم يُحذف؛ أُضيف حقل `mac` فقط (إضافة لا حذف) |
| `_encrypt_single_blob` — الجسم القديم كاملًا (`raw = self.core.load_blob(...)` + `self.core.store_blob(...)`) | **كود ميت أثبتته الفحصة:** `store_blob/load_blob` غير موجودين في `SovereignCore` (الواجهة الفعلية `blob_store.put/get`) — كل استدعاء كان يرمي `AttributeError` يُبتلع صامتًا بـ `except:` فيفشل بلا رماد أبدًا. استُبدل بالواجهة الحقيقية + مصادقة MAC + تسجيل فشل صريح (لا `except:` صامت) |
| `except:` الصامت في `_encrypt_single_blob` | انتهاك قاعدة الابتلاع الصامت — استُبدل بـ `except Exception as e` مع `logger.error` صريح |
| `_encrypt_store_item` — الكعب `return True` (تعليق "تنفيذ مماثل") | **كذب في العدّ:** كان يعيد True بلا أي تشفير فتُحتسب عناصر "مشفرة" لم تُشفَّر قط في `encrypted_items`. استُبدل بفشل صريح `return False` + تسجيل أن المسار غير منفذ |
| `_resurrect_from_axes`/`_decrypt_all_memory` — جسم "غير منفذ يفشل صريحًا" | مسار مؤقت صادق (الجولة السابقة) — استُبدل بالتنفيذ الفعلي: فك + مصادقة MAC + إثبات بتطابق بصمة المحتوى |

**صافي الحذف:** لا حذف لمنطق حي — كل سطر محذوف كان إما كودًا ميتًا (واجهة غير موجودة) أو كعبًا كاذبًا أو مسارًا مؤقتًا مُعلنًا صراحة. لا حذف بلا استثناء جديد.

## ملحق 7: حذوفات الجولة الثامنة (تصحيح بناء الرماد بعد اعتراض advisor)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| `PhoenixAshes.mac` (حقل) | استُبدل بمصادقة داخلية في مظروف GCM (وسم GCM + AAD) — لا حقل منفصل يوحي بمصادقة مستقلة |
| XOR المتكرر في `_encrypt_single_blob`/`_restore_ash` + MAC المنفصل | **أمر المستشار:** مفتاح التكرار نفسه كان يُستخدم للمصادقة (تسرب متبادل) — استُبدل بمظروف AES-256-GCM معياري (nonce جديد + AAD يربط الإصدار وoriginal_id) |
| منطق "النجاح الجزئي يعلن success=True" في `_resurrect_from_ashes` | **أمر المستشار:** لا نجاح ولا REBORN لاستعادة ناقصة — استُبدل بنتيجة منظمة تعلن الفشل الجزئي صراحة وتحفظ الفاشل |
| عودة `_decrypt_all_memory` بعدد صحيح فقط | كانت تخفي الفشلات في مسار البذرة — استُبدلت بنتيجة منظمة (restored/failed) تُفحص قبل REBORN |
| `encrypted_items` في حمولة حدث الموت | ادعاء كاذب (عناصر مخزن لم تُشفر قط) — استُبدل بـ blobs_encrypted/store_items_unprotected/protection_complete الصادقة |

**صافي الحذف:** لا حذف لمنطق حي — كل بديل أقوى أمنيًا وأصدق. لا حذف بلا استثناء جديد.

## ملحق 8: حذوفات الجولة التاسعة (فصل الحماية عن الاسترداد)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| `"complete": protection["store_items_unprotected"] == 0` | **أمر المستشار:** استنتاج اكتمال من صفر عدّاد — يعلن اكتمالًا مع فشل كل عمليات الإنشاء أو تعذر الفحص. استُبدل بـ recovery_ready (لا فشل/تعذر/اقتطاع/عنصر غير محمي) + assets_hidden/protection_complete صريحة دائمة |
| استثناء واحد يلف فحص الأحداث والمخزن معًا | كان يبتلع تعذر الفحص في عدّاد واحد — فُصل إلى مسارين بعلمَي فشل مستقلين (events_scan_failed/store_scan_failed) |
| عدّ العنصر فقط إذا كان له `_id` | **أمر المستشار:** غياب المعرّف لا يعني غياب الحماية عن العنصر — كل ما أرجعه الاستعلام يُعد غير محمي |

**صافي الحذف:** لا حذف لمنطق حي — استبدال استنتاجات كاذبة بتصريحات صادقة. لا حذف بلا استثناء جديد.

## ملحق 9: حذوفات الجولة العاشرة (عقد نتيجة initiate_death)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| `self.phoenix_phase = PhoenixPhase.DEAD` غير المشروط + `success=True` الثابت في سجل الموت | **أمر المستشار:** فشل الجاهزية كان يُعلن موتًا ناجحًا — صار النجاح مشروطًا بـ recovery_ready والحالة LIVING عند الفشل |
| حدث `phoenix::death` عند الفشل | صار `phoenix::death_failed` بالأسباب — لا يُسجل موت لم ينجح |
| `is_transforming=True` المتبقي بعد الموت | **أمر المستشار:** تحول معلق بلا تحول جارٍ — صار False عند انتهاء العملية في الحالتين |

**صافي الحذف:** لا حذف لمنطق حي — استبدال إعلانات نجاح كاذبة بعقد نتيجة صادق. لا حذف بلا استثناء جديد.

## ملحق 10: حذوفات الجولة الحادية عشرة (حفظ الحالة النهائية + فشل التسجيل)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| مسارا append_event المنفصلان (نجاح/فشل) بلا حماية | **أمر المستشار:** فشل التسجيل كان يهرب بالاستثناء ويترك DYING مع سجل نجاح — وُحد الحدثان في مسار واحد داخل try/except فاشل-مغلق |
| إرجاع `True`/`False` دون شرط حفظ الحالة النهائية | **أمر المستشار:** العلم القديم المحفوظ أثناء DYING يمنع إعادة المحاولة بعد إعادة التحميل — صار الحفظ شرطًا للنجاح (فشل الحفظ = False) |

**صافي الحذف:** لا حذف لمنطق حي — دمج مسارين مكررين في مسار موحد أشد أمانًا. لا حذف بلا استثناء جديد.

## ملحق 11: حذوفات الجولة الثانية عشرة (الترتيب: الحفظ قبل الحدث)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| تسجيل حدث الإكمال قبل الحفظ النهائي | **أمر المستشار:** فشل الحفظ كان يترك حدث موت ناجحًا لعملية فشلت — صار الحفظ شرطًا سابقًا لأي حدث إكمال |
| الاكتفاء بالتحذير عند فشل الحفظ المزدوج | **أمر المستشار:** لا يكفي تسجيل التحذير — أُضيفت تسوية الحالة عند التحميل (عملية منقطعة لا تحول جارٍ) |

**صافي الحذف:** لا حذف لمنطق حي — إعادة ترتيب (الحفظ قبل الحدث) + تسوية عند التحميل. لا حذف بلا استثناء جديد.

## ملحق 12: حذوفات الجولة الثالثة عشرة (علامة الإنهاء المعلقة)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| لا حذوفات كود في هذه الجولة | إضافة فقط: حقل `pending_outcome` في حالة الفينيق (حفظ/تحميل/تسوية) + وضعه قبل الحفظ النهائي ورفعه بعد حدث الإكمال وحفظ الرفع |

**صافي الحذف:** صفر — جولة إضافة صرفة. لا حذف بلا استثناء جديد.

## ملحق 13: حذوفات الجولة الرابعة عشرة (التمييز الثلاثي + التوفيق)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| استنتاج محتوى القرص من bool الحفظ | **أمر المستشار:** False لا يعني بقاء الملف القديم — صار العلم `_last_save_replaced_unconfirmed` يميز الحالتين |
| تصنيف كل علامة معلقة فاشلة دون فحص الحدث | **أمر المستشار:** التوفيق مع الدليل الدائم — op_id في حمولة الحدثين + بحث السجل عند التحميل |

**صافي الحذف:** لا حذف لمنطق حي — استبدال استنتاجين كاذبين بتمييز وتوفيق. لا حذف بلا استثناء جديد.

## ملحق 14: حذوفات الجولة الخامسة عشرة (الفصل + التفرد + الاستنفاد)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| `return True` عند الاستبدال-غير-المؤكد | **أمر المستشار:** تحويل عدم تأكيد المتانة إلى نجاح العقد — صار False مع سجل success=True وحالة متانة ظاهرة |
| `id=f"death_{int(time.time())}"` (في الموضعين) | **أمر المستشار:** قابل للتصادم (ثانية واحدة) — صار معرفًا فريدًا لكل محاولة يعاد استخدامه في السجل والعلامة والأحداث |
| `limit=100` في التوفيق | **أمر المستشار:** البحث المحدود ليس توفيقًا حاسمًا — صار استنفاد السجل فعليًا |

**صافي الحذف:** لا حذف لمنطق حي — ثلاثة استبدالات دقيقة بأوامر المستشار. لا حذف بلا استثناء جديد.

## ملحق 15: حذوفات الجولة الثامنة عشرة (استمرارية السجل)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| تحذير فشل الترقية الأحادي | **أمر المستشار:** كان يدّعي أن القرص يبقى محافظًا مطلقًا (خطأ عند وقوع الاستبدال) وأن التوفيق يحدث «في كل الأحوال» — استُبدل بتمييزين صريحين: قبل الاستبدال (محافظ) / بعده (confirmed مكتوب بمتانة غير مؤكدة) |
| القيم المرحلية للسجل بعد التوفيق | **أمر المستشار:** السجل المُعاد تحميله كان يبقى بقيم نسخة القرص المرحلية (قد يعلن نجاحًا بعد توفيق فاشل) — صار يعكس نتيجة التوفيق نفسها |

**صافي الحذف:** لا حذف لمنطق حي — تحذيرات غير دقيقة استُبدلت بتشخيص مميّز، وقيم مرحلية صارت محدَّثة بالتوفيق. لا حذف بلا استثناء جديد.

## ملحق 16: حذوفات تعديل العقد الدستوري (البند 8)

| السطر/الكتلة المحذوفة | المبرر |
|---|---|
| نص القاعدة 1 القديم («لا حذف. لا ملف، لا سطر...») | **قرار المالك الصريح (2026-10-15):** تعديل العقد — محضر الجلسة b04b1da6-3e7d-4648-b997-96c972797be5؛ استُبدلت بنظام «الحذف المبرر الموثق» (شرطا القاعدة 1 الجديدة) |
| نص القاعدة 6 القديم («الإضافة بلا قيد، الحذف ممنوع مطلقًا») | نفس المبرر — قرار المالك نفسه في نفس الالتزام |
| بند القائمة القديم («لا حذف. لا mock في الإنتاج...») | نفس المبرر — صيغة «كل حذف يستوفي شرطي القاعدة 1» تُبقي شرط البوابة |
| صف البند 8 في FINAL_REPORT (`BLOCKED`) | تسجيل قرار المالك (تعديل العقد معتمد) مع إبقاء الإغلاق معلقًا حتى اجتياز البوابة ومراجعة أدلة SHA — صيغة «قرار التعديل معتمد — التحقق النهائي جارٍ» |

**صافي الحذف (مطابق للفرق النهائي حرفيًا):** **4 أسطر** — نص القاعدة 1
القديم، نص القاعدة 6 القديم، بند القائمة القديم، صف البند 8 في FINAL_REPORT.
مبررها قرار المالك الصريح نفسه الموثق في نفس الالتزام. تصويبات الأدلة في
مسودة قسم الحسم (الـ115، حدود الإثبات، نطاق الحسم) جرت داخل المسودة غير
المُلتزم بها نفسها — ليست حذف محتوى مُلتزم به ولا تظهر في الفرق. القاعدة 1
الجديدة مستوفاة بحذها هذا: تبرير مكتوب في نفس الالتزام + البوابة شرط تُثبت
بتشغيلها في دورة التحقق هذا الالتزام (لا تُدَّعى قبل تشغيلها).

---

## حذوفات الالتزام: الجولة التشغيلية الثالثة (تصويبات أمر المستشار)

**المرجع:** أمر المراجعة (advisor) على التسليم `0c5143d` + تجربة كاذبة للتعليل.

| الملف | الأسطر المحذوفة | التبرير |
|---|---|---|
| `conftest.py` (جذر) | 30 سطرًا (الملف كاملًا) | ملف أُنشئ في `0c5143d` لتسجيل `--run-operational`. تعليل إنشائه في الجذر («الاستدعاء بلا مسارات لا يحمّل `tests/conftest.py` قبل تحليل الخيارات») **اختُبر تجريبيًا على pytest 9.1.1 (إصدار CI) فظهر غير صحيح** — التسجيل في `tests/conftest.py` يعمل للاستدعاءين. نُقل التسجيل إلى `tests/conftest.py` (+18 سطرًا) وأُلغي الملف. الترحيل مُثبت بالتشغيل: الاستدعاء بلا مسارات `1 passed` + اختبار الانحدار `1 passed` |
| `tests/invariants/test_no_orphan_modules.py` | 6 أسطر | استثناء اسم `conftest.py` العريض الذي أَدخله `0c5143d` (يعفي أي ملف بهذا الاسم في أي مسار — اعتراض المراجع: أوسع من المطلوب). أُعيد الملف إلى حالته قبل `0c5143d` وأُضيف بدله اختبار سلوكي (`test_guard_flags_stray_conftest_outside_root`) يثبت أن ملفًا يتيمًا باسم `conftest.py` خارج الجذر يُقبض عليه — الاسم وحده لا يُعفي |

**شرط البوابة:** الحزمة خضراء بعدها (محليًا + CI) — موثق في
`OPERATIONAL_TESTS.md` (الجولة الثالثة) وسجل التسليم.

---

## حذوفات الالتزام: الجولة التشغيلية الرابعة (مسار استثناء المصادقة)

| الملف | الأسطر المحذوفة | التبرير |
|---|---|---|
| `tests/test_gate1_operational_auth.py` | 23 سطرًا | نص السكربت الانتقال (بناء السب-بروسس) انتقل من داخل دالة الاختبار إلى دالة مشتركة `_build_verification_script()` — أمر المراجع الصريح: تمكين اختبار محقون لمسار تشخيص الإخفاق (`str(e)`) من نفس مصدر السكربت حرفيًا لا نسخة موازية. النص المنقول مطابق للأصل + إضافة التنقية (`_redact`) فقط — أثبت الاختبار المحقون التسريب قبلها (RED) واختفاءه بعدها (GREEN). راجع OPERATIONAL_TESTS.md — الجولة الرابعة |

**شرط البوابة:** الحزمة خضراء بعدها — 410 passed, 1 deselected, 0 failed
محليًا (+ CI على SHA الالتزام — موثق في سجل التسليم)، والاختبار
التشغيلي ناجح محليًا (1 passed).

---

## حذوفات الالتزام: الجولة التشغيلية الخامسة

| الملف | الأسطر المحذوفة | التبرير |
|---|---|---|
| `tests/test_operational_no_leak_on_exception.py` | أسطر داخل الاختبار المحقون | استُبدلت دفعة المفاتيح الوهمية بقيم تحتوي `+` و`/`، والتطبيق الوهمي ASGI البسيط بتطبيق FastAPI يرفع استثناءً يحمل `request.url`، وتأكيدات التسريب بصيغتيه — كله بأمر المراجع الصريح (الجولة الخامسة): محاكاة الحالة الواقعية لرسائل أخطاء HTTP حيث يظهر المفتاح بتمثيله المرمّز. راجع OPERATIONAL_TESTS.md — الجولة الخامسة |

**شرط البوابة:** الحزمة خضراء بعدها — 410 passed, 1 deselected, 0 failed
محليًا + CI على SHA الالتزام.

---

## مدخل بأثر رجعي: حذوفات الالتزام `182949f` (R-682 operational)

**سطر افتتاحي صريح:** مدخل بأثر رجعي — أُضيف في الالتزام `9635886772aa71fb053d568204e525c17d955afd`؛ **المخالفة الأصلية تبقى مسجلة في `CONTRACT_EXCEPTION_1.md`**. هذا المدخل توثيق بأثر رجعي، لا يغيّر المخالفة ولا يجمّلها ولا يعتمدها.

| # | الملف | السطر المحذوف (حرفيًا) | التبرير الوظيفي |
|---|---|---|---|
| 1 | `.github/workflows/ci.yml` | `-      - name: Load KEY_SECRET from repository secret` | استُبدلت خطوة تحميل السر الوحيدة القديمة (KEY_SECRET فقط) بخطة تحميل السرّين (KEY_SECRET + KEY_OLD_SECRET) عبر `env` بلا استيفاء مباشر داخل `run` — الوظيفة نفسها (تحميل `data/key.secret`) محفوظة وموسعة للمفتاح القديم |
| 2 | `.github/workflows/ci.yml` | `-          if [ -z "${{ secrets.KEY_SECRET }}" ]; then` | الشرط انتقل إلى الفحص المزدوج للسرّين برسالة فشل صريحة أوسع |
| 3 | `.github/workflows/ci.yml` | `-            echo "❌ KEY_SECRET secret not configured — cannot run operational tests"` | استُبدلت برسالة فشل تغطي السرّين معًا |
| 4 | `.github/workflows/ci.yml` | `-          printf '%s' "${{ secrets.KEY_SECRET }}" > data/key.secret` | استُبدلت بكتابة الملفين عبر `printf '%s' "$VAR"` مع `umask 077` — نفس الوظيفة بطريقة لا تعرض السر في أمر الطباعة |
| 5 | `.github/workflows/ci.yml` | `-          chmod 600 data/key.secret` | الصلاحية مضمونة الآن عبر `umask 077` قبل الإنشاء |
| 6 | `.github/workflows/ci.yml` | `-          echo "key.secret loaded from secret"` | استُبدلت برسالة تؤكد عدم طباعة القيم أبدًا |
| 7 | `tests/test_gate1_operational_auth.py` | `-            f"    r = client.get('/api-key', params={{'master_key': {new_key!r}}})\n"` | تضمين قيمة المفتاح حرفيًا داخل مصدر السكربت استُبدل بالتمرير عبر متغير بيئة `TEST_NEW_KEY` — نفس الطلب، بلا ظهور المفتاح في أي traceback أو رسالة إخفاق |
| 8 | `tests/test_gate1_operational_auth.py` | `-            f"    r = client.get('/api-key', params={{'master_key': {old_key!r}}})\n"` | نفس التبرير للمفتاح القديم (`TEST_OLD_KEY`) |

**العدد:** 8 أسطر محذوفة (6 من `ci.yml` + 2 من `tests/test_gate1_operational_auth.py`).
**الحالة:** المخالفة قائمة — التبرير كان في رسالة الالتزام فقط، لا في هذا السجل داخل الالتزام نفسه (شرط القاعدة 1-أ المعدلة). هذا المدخل لا يعتمد شيئًا؛ اعتماد الاستثناء أو رفضه قرار المالك في `CONTRACT_EXCEPTION_1.md`.

## مدخل بأثر رجعي: حذوفات غير مدققة في التزامات جولة R-682 (المخالفة قائمة ومسجلة)

**سطر افتتاحي صريح:** مخالفة موثقة — 17 سطرًا محذوفًا عبر ثلاثة التزامات
(`e21574a` و`a733ab8` و`60053d4`) دون تدقيق في نفس الالتزام، ورسالتا
آخر التزامين وصفتا نفسيهما خطأً بـ«لا حذوفات في هذا الالتزام». هذا
المدخل توثيق بأثر رجعي — لا يزيل المخالفة ولا يجمّلها؛ القرار الحاسم
فيها (قبول الاستثناء أو رفضه) ينتظر توقيع المالك في `CONTRACT_EXCEPTION_1.md`.

### الالتزام `e21574ad433105f0fc2552425cd950ee8cb2c3a0` — 6 أسطر (forensics/keyring_rejection_count.json)

استبدال قيم «بعد الإصلاح: 0» بقيم القياس الفعلي (10) — تصويب رقمي شفاف:
- 2 سطرا قيم JSON (total_rejected_lines/by_key_id_desc) — استُبدلا بالقياس الفعلي بعد اكتشاف المتبقي
- 3 أسطر evidence — استُبدلت بأدلة القياس المصوب
- 1 سطر total_line — استُبدل بسطر الإجمالي المصوب

### الالتزام `a733ab835d226bd2f5a69482f79b3f9ec4f8ff9b` — 7 أسطر (verify.sh)

استبدال منطق اختيار تشغيل CI القديم (مسح بـ headSha):
- سطر تعليق الرأس القديم + سطر أمر gh run list القديم (limit 20 بلا workflowName)
- 5 أسطر كود بايثون مضمّن (حلقة المسح والطباعة) — استُبدلت بالمسح بالمعرّف الصريح

### الالتزام `60053d4086e13c76b93f65ae9b41e7a7d3df53f5` — 4 أسطر (verify.sh)

تصحيح فحص الحالة والنتيجة من المسح بـ headSha إلى المسح بالمعرّف الصريح:
- 4 أسطر (`target_sha = '$SHA'` وسطرا شرط المسح، مرتين) — استُبدلت بمسح databaseId

## R-682 — الجولة الشاملة (2026-10-16): تحويل خيوط الخلفية إلى الإدارة الموحدة

الالتزام: يُثبّت رقمه في سجل الإغلاق (FINAL_CLOSURE_R-682.md).
طبيعة التعديل: استبدال أنماط آلي — لا حذف وظائف. كل سطر محذوف استُبدل بسطر
مكافئ أو أفضل (التفصيل أدناه). المجموع: 511 سطرًا محذوفًا من ملفات الكود.

### التصنيف (كل سطر محذوف ينتمي لواحد من هذه الأنماط)

- 255 × سطر `time.sleep(...)` — استُبدل بـ threads.interruptible_sleep(...) القابل للمقاطعة
- 125 × سطر `.start()` — استُبدل بنداء start_managed الذي يشغّل الخيط داخل نفس السطر
- 5 × سطر `while True:` — استُبدل بحارس حدث قابل للإيقاف (views/encoding/store)
- 2 × أخرى: self._cleanup_thread = threading.Thread(target=self._auto_cl
- 2 × أخرى: self._controller_loop = threading.Thread(target=self._contin
- 2 × أخرى: self._decision_monitor = threading.Thread(target=self._monit
- 2 × أخرى: self._decision_executor = threading.Thread(target=self._exec
- 2 × أخرى: self._health_monitor = threading.Thread(target=self._monitor
- 1 × أخرى: monitor_thread = threading.Thread(target=monitor, daemon=Tru
- 1 × أخرى: self._allocation_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._sustained_tracker = threading.Thread(target=self._trac
- 1 × أخرى: self._resource_monitor = threading.Thread(target=self._monit
- 1 × أخرى: self._awareness_stream = threading.Thread(target=self._conti
- 1 × أخرى: self._attention_decay_loop = threading.Thread(target=self._a
- 1 × أخرى: self._subliminal_processor = threading.Thread(target=self._p
- 1 × أخرى: self._consciousness_stream = threading.Thread(target=self._c
- 1 × أخرى: self._feeling_loop = threading.Thread(target=self._feeling_s
- 1 × أخرى: self._presence_monitor = threading.Thread(target=self._prese
- 1 × أخرى: self._identity_maintenance = threading.Thread(target=self._c
- 1 × أخرى: self._backup_creator = threading.Thread(target=self._periodi
- 1 × أخرى: self._integrity_checker = threading.Thread(target=self._cont
- 1 × أخرى: self._introspection_loop = threading.Thread(target=self._con
- 1 × أخرى: self._command_monitor = threading.Thread(target=self._monito
- 1 × أخرى: self._quality_monitor = threading.Thread(target=self._monito
- 1 × أخرى: self._wish_tracker = threading.Thread(target=self._track_sov
- 1 × أخرى: self._self_reflection_loop = threading.Thread(target=self._c
- 1 × أخرى: self._journaling_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._dimension_update_loop = threading.Thread(target=self._
- 1 × أخرى: self._archetype_loop = threading.Thread(target=self._continu
- 1 × أخرى: self._transition_detector = threading.Thread(target=self._de
- 1 × أخرى: self._drive_update_loop = threading.Thread(target=self._cont
- 1 × أخرى: self._satisfaction_loop = threading.Thread(target=self._sati
- 1 × أخرى: self._balance_loop = threading.Thread(target=self._drive_bal
- 1 × أخرى: self._evolution_loop = threading.Thread(target=self._continu
- 1 × أخرى: self._mutation_generator = threading.Thread(target=self._ran
- 1 × أخرى: self._natural_forgetting_thread = threading.Thread(target=se
- 1 × أخرى: self._strategic_forgetting_thread = threading.Thread(target=
- 1 × أخرى: self._memory_consolidation_thread = threading.Thread(target=
- 1 × أخرى: self._monitoring_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._regulation_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._adaptation_loop = threading.Thread(target=self._adapti
- 1 × أخرى: self._memory_cell_maintainer = threading.Thread(target=self.
- 1 × أخرى: self._auto_vaccinator = threading.Thread(target=self._auto_v
- 1 × أخرى: self._antibody_evolver = threading.Thread(target=self._evolv
- 1 × أخرى: self._protection_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._wellbeing_loop = threading.Thread(target=self._continu
- 1 × أخرى: self._sovereign_monitor = threading.Thread(target=self._moni
- 1 × أخرى: self._threat_response = threading.Thread(target=self._threat
- 1 × أخرى: self._experience_processor = threading.Thread(target=self._p
- 1 × أخرى: self._pattern_discovery = threading.Thread(target=self._disc
- 1 × أخرى: self._schema_builder = threading.Thread(target=self._build_s
- 1 × أخرى: self._reinforcement_learner = threading.Thread(target=self._
- 1 × أخرى: self._metabolic_loop = threading.Thread(target=self._continu
- 1 × أخرى: self._energy_monitor = threading.Thread(target=self._energy_
- 1 × أخرى: self._ltp_loop = threading.Thread(target=self._continuous_lt
- 1 × أخرى: self._pruning_loop = threading.Thread(target=self._continuou
- 1 × أخرى: self._rewiring_loop = threading.Thread(target=self._continuo
- 1 × أخرى: self._neurogenesis_loop = threading.Thread(target=self._cont
- 1 × أخرى: self._stem_cell_generator = threading.Thread(target=self._ge
- 1 × أخرى: self._auto_regenerator = threading.Thread(target=self._auto_
- 1 × أخرى: self._shadow_thread = threading.Thread(target=self._shadow_g
- 1 × أخرى: self._phasing_thread = threading.Thread(target=self._quantum
- 1 × أخرى: self._mutation_loop = threading.Thread(target=self._continuo
- 1 × أخرى: self._phantom_refresher = threading.Thread(target=self._refr
- 1 × أخرى: self._trap_setter = threading.Thread(target=self._auto_set_t
- 1 × أخرى: self._watcher_thread = threading.Thread(target=self._watch_f
- 1 × أخرى: self._resurrection_thread = threading.Thread(target=self._re
- 1 × أخرى: self._seed_preserver = threading.Thread(target=self._preserv
- 1 × أخرى: self._location_hopper = threading.Thread(target=self._spatia
- 1 × أخرى: self._signature_mutator = threading.Thread(target=self._sign
- 1 × أخرى: self._ghost_generator = threading.Thread(target=self._ghost_
- 1 × أخرى: self._monitor_thread = threading.Thread(target=self._continu
- 1 × أخرى: self._learning_thread = threading.Thread(target=self._adapti
- 1 × أخرى: self._processor_thread = threading.Thread(target=self._backg
- 1 × أخرى: self._attention_thread = threading.Thread(target=self._atten
- 1 × أخرى: self._dreamer_thread = threading.Thread(target=self._dreamer
- 1 × أخرى: self._cleanup_thread = threading.Thread(target=self._cleanup
- 1 × أخرى: self._backup_thread = threading.Thread(target=self._auto_bac
- 1 × أخرى: self._rebuild_thread = threading.Thread(target=self._auto_re
- 1 × أخرى: self._background_thread = threading.Thread(target=self._back
- 1 × أخرى: self._background_processor = threading.Thread(target=self._b
- 1 × أخرى: self._continuous_cycle = threading.Thread(target=self._conti
- 1 × أخرى: self._prediction_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._forecast_validator = threading.Thread(target=self._val
- 1 × أخرى: self._trend_analyzer = threading.Thread(target=self._analyze
- 1 × أخرى: self._risk_detection_loop = threading.Thread(target=self._co
- 1 × أخرى: self._prioritization_loop = threading.Thread(target=self._co
- 1 × أخرى: self._mitigation_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._scenario_loop = threading.Thread(target=self._continuo
- 1 × أخرى: self._warning_monitor = threading.Thread(target=self._monito
- 1 × أخرى: self._trigger_detector = threading.Thread(target=self._detec
- 1 × أخرى: self._simulation_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._results_analyzer = threading.Thread(target=self._analy
- 1 × أخرى: self._signal_processor = threading.Thread(target=self._proce
- 1 × أخرى: self._propagation_loop = threading.Thread(target=self._conti
- 1 × أخرى: self._field_update_loop = threading.Thread(target=self._cont
- 1 × أخرى: self._interference_calculator = threading.Thread(target=self
- 1 × أخرى: self._time_evolution_loop = threading.Thread(target=self._co
- 1 × أخرى: self._decoherence_loop = threading.Thread(target=self._decoh
- 1 × أخرى: self._coherence_maintenance = threading.Thread(target=self._
- 1 × أخرى: self._interference_loop = threading.Thread(target=self._cont
- 1 × أخرى: self._nesting_optimizer = threading.Thread(target=self._opti
- 1 × أخرى: self._continuous_transitions = threading.Thread(target=self.
- 1 × أخرى: self._matrix_evolution = threading.Thread(target=self._matri
- 1 × أخرى: self._continuous_analysis = threading.Thread(target=self._co
- 1 × أخرى: self._pattern_detection = threading.Thread(target=self._patt
- 1 × أخرى: self._insight_generator = threading.Thread(target=self._insi
- 1 × أخرى: self._control_loop = threading.Thread(target=self._continuou
- 1 × أخرى: self._batch_processor = threading.Thread(target=self._proces
- 1 × أخرى: self._result_analyzer = threading.Thread(target=self._analyz
- 1 × أخرى: self._validation_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._backup_loop = threading.Thread(target=self._periodic_b
- 1 × أخرى: self._scheduler_thread = threading.Thread(target=self._sched
- 1 × أخرى: self._worker_monitor = threading.Thread(target=self._monitor
- 1 × أخرى: self._persistence_thread = threading.Thread(target=self._per
- 1 × أخرى: self._alignment_loop = threading.Thread(target=self._continu
- 1 × أخرى: self._violation_monitor = threading.Thread(target=self._moni
- 1 × أخرى: self._correction_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._directives_loop = threading.Thread(target=self._contin
- 1 × أخرى: self._enforcement_loop = threading.Thread(target=self._enfor
- 1 × أخرى: self._expiration_monitor = threading.Thread(target=self._mon
- 1 × أخرى: self._will_loop = threading.Thread(target=self._continuous_w
- 1 × أخرى: self._will_evolution = threading.Thread(target=self._evolve_
- 1 × سطر توثيق conftest القديم — استُبدل بتوثيق أشمل

### التوزيع لكل ملف (numstat: +إضافات / -حذوفات)

| الملف | + | - |
|---|---|---|
| backend/Mr.py | 3 | 3 |
| backend/consciousness/attention_engine.py | 10 | 12 |
| backend/consciousness/awareness.py | 10 | 12 |
| backend/consciousness/field.py | 10 | 12 |
| backend/consciousness/identity_core.py | 10 | 12 |
| backend/consciousness/introspection.py | 13 | 16 |
| backend/consciousness/self_model.py | 11 | 13 |
| backend/memory/biological/archetypes.py | 7 | 8 |
| backend/memory/biological/drives.py | 10 | 12 |
| backend/memory/biological/evolution.py | 9 | 10 |
| backend/memory/biological/forgetting.py | 10 | 12 |
| backend/memory/biological/homeostasis.py | 11 | 13 |
| backend/memory/biological/immune.py | 10 | 12 |
| backend/memory/biological/instincts.py | 13 | 16 |
| backend/memory/biological/learning.py | 13 | 16 |
| backend/memory/biological/metabolism.py | 8 | 9 |
| backend/memory/biological/plasticity.py | 13 | 16 |
| backend/memory/biological/regeneration.py | 7 | 8 |
| backend/memory/defense/fileless.py | 10 | 12 |
| backend/memory/defense/polymorphic.py | 13 | 15 |
| backend/memory/defense/ransomware.py | 10 | 12 |
| backend/memory/defense/stealth.py | 13 | 15 |
| backend/memory/defense/watcher.py | 7 | 8 |
| backend/memory/dynamic/__init__.py | 9 | 11 |
| backend/memory/encoding.py | 8 | 4 |
| backend/memory/store/__init__.py | 14 | 8 |
| backend/memory/views.py | 18 | 9 |
| backend/orchestrator.py | 4 | 4 |
| backend/predictive/predictive_controller.py | 4 | 4 |
| backend/predictive/predictive_engine.py | 10 | 12 |
| backend/predictive/predictive_risk_manager.py | 10 | 12 |
| backend/predictive/predictive_scenarios.py | 10 | 12 |
| backend/predictive/predictive_simulation.py | 7 | 8 |
| backend/quantum/quantum_controller.py | 10 | 12 |
| backend/quantum/quantum_field.py | 10 | 12 |
| backend/quantum/quantum_state.py | 7 | 8 |
| backend/quantum/quantum_superposition.py | 10 | 12 |
| backend/quantum/quantum_transition.py | 7 | 8 |
| backend/simulation/simulation_analyzer.py | 10 | 12 |
| backend/simulation/simulation_controller.py | 10 | 12 |
| backend/simulation/simulation_core.py | 7 | 8 |
| backend/simulation/simulation_environment.py | 7 | 8 |
| backend/simulation/simulation_scheduler.py | 10 | 12 |
| backend/sovereign/alignment.py | 10 | 12 |
| backend/sovereign/controller.py | 10 | 12 |
| backend/sovereign/directives.py | 10 | 12 |
| backend/sovereign/will.py | 10 | 12 |
| tests/conftest.py | 30 | 1 |

### ملاحظة النزاهة

لا يوجد أي حذف خارج هذه الأنماط. الملفات الجديدة (backend/runtime/) و
forensics/ الجديدة إضافات لا حذوفات فيها. الحذوفات في ملفات .md هي تعديلات
توثيقية مدرجة في التزامات التوثيق.

## R-682 — التزام حزمة إصلاحات المستشار (2026-10-16): 149 سطرًا محذوفًا — كلها استبدالات موثقة

**سطر افتتاحي صريح (مصوب):** المجموع الفعلي من git هو **149** (النسخة الأولية
من هذا الجدول جمعت خطأً إلى 151 لعدم تفصيل أسطر forensics). لا حذف وظائف —
كل سطر محذوف في هذا الالتزام استُبدل
بسطر مكافئ أو أفضل (نقل منطق إلى وحدة مشتركة، أو استخراج إخفاقات صامتة
إلى جمع وإظهار). الالتزام يُثبّت رقمه في سجل الخاتمة (FINAL_CLOSURE).

### التصنيف لكل ملف (numstat: +إضافات / -حذوفات)

| الملف | + | - | طبيعة الحذف |
|---|---|---|---|
| .github/workflows/ci.yml | 5 | 2 | استبدال اسم خطوة (نفس الوظيفة بصياغة الأمر الحرفي) |
| backend/memory/defense/fileless.py | 2 | 2 | سطرا إنشاء خيط أحاديان → threads.start_managed (سجل + انضمام) |
| backend/memory/defense/stealth.py | 1 | 1 | سطر إنشاء خيط أحادي → threads.start_managed |
| backend/runtime/threads.py | 35 | 14 | حذف إلا استثناءات صامتة (TOLERATED pass) → جمع إخفاقات وإظهارها؛ إعادة ترتيب (الأعلام قبل الإيقاظ)؛ عدم مسح المراجع إن بقيت خيوط حية |
| forensics/*.md (مفصلة) | — | 48 | ADVISOR_SESSIONS_DISCLOSURE 30 + LOCAL_ENV_DISCLOSURE 13 + OPERATIONAL_CLAIM_SCOPE 3 + DELETED_LINES_AUDIT 1 + OPERATIONAL_TESTS 1 + CONTRACT_EXCEPTION_1 0 — إعادة كتابة أقسام توثيقية (الإفصاح أعيد بناؤه بفهرس 8 استدعاءات) |
| forensics/keyring_rejection_count.json | 9 | 8 | تصويب قيم وأدلة القياس (نسبة الـ244 وخطوات الفصل) |
| tests/test_background_threads_shutdown.py | 76 | 4 | تحديث اختبار دورة الحياة (مراجع مستقلة) — الحذف: 4 أسطر قراءة metrics القديمة |
| tests/test_key_selection_rotation.py | 37 | 7 | حذف أسطر SovereignCore() بلا مسارات (7 أسطر توقيع/منشئ) → منشئ بمسارات صريحة |
| tests/test_return_none_security.py | 4 | 1 | سطر KeyRotation بلا ledger_path → مع ledger_path معزول |
| verify.sh | 9 | 62 | حذف منطق الاختيار المضمّن (62 سطر بايثون داخل السكربت) → نقل حرفي إلى الوحدة المشتركة tests/ci_run_selection.py القابلة للاختبار |

### ملاحظة النزاهة

أكبر حذف (62 سطرًا في verify.sh) هو **نقل حرفي** إلى `tests/ci_run_selection.py`
(نفس المنطق + فحص هوية workflow + قابلية اختبار حتمية). لا سطر محذوف بلا بديل.

## R-682 — إصلاح متغير غير معرف في verify.sh (2026-10-16): 9 أسطر (تصويب لاحق: كان موثقًا 10 خطأً)

**سطر افتتاحي صريح:** حذف كتل فحوص الحالة القديمة المتبقية بعد نقل منطق
الاختيار للوحدة المشتركة — الفحوص نفسها انتقلت إلى
tests/ci_run_selection.py (--require-completed). الحذف كله استبدال وظيفة
بأدوات أفضل، لا حذف تحقق.

الأسطر التسعة (حرفيًا من git): كتلتا `if [ "$CI_STATUS" != "completed" ]`
و`if [ "$CI_CONCLUSION" != "success" ]` مع أسطر الصدى الخاص بهما (8 أسطر)
+ سطر فارغ واحد فاصل. **تصويب:** المدخل الأولي ورسالة الالتزام قالا «10» —
الرقم الفعلي من git numstat هو **9**. رسالة الالتزام غير قابلة للتعديل؛ هذا
التصويح هو التوثيق الصحيح. **تصويب صياغي إضافي:** العبارة السابقة هنا
قالت إن مخالفة هذا الالتزام «مسجلة في مدخل 20a81ce» — خطأ: الالتزام
`f2577ca` **دُققت حذوفاته في التزامه نفسه** لكن بعدد خاطئ (10 بدل 9)،
و`20a81ce` يسبقه زمنيًا. المخالفة الصحيحة المنسوبة لـ`f2577ca`: تدقيق
بعدد غير مطابق، لا غياب تدقيق.

## R-682 — تدقيق رجعي للالتزام d05a248 (2026-10-16): 4 أسطر — مخالفة مسجلة

**سطر افتتاحي صريح:** الالتزام d05a248 حذف 4 أسطر ولم يدققها في نفسه
(رسالته قالت «توثيق خالص — لا كود ولا حذوفات») — **مخالفة جديدة مسجلة
هنا بأثر رجعي**، أضيفت إلى نص استثناء المالك المنتظر توقيعه.

الأسطر الأربعة (حرفيًا من git — كلها استبدال صياغي، لا حذف معلومة):

1. `**شرط الإغلاق (البند ١٣):** نجاح التطابق الثلاثي على نفس الالتزام — **تحقق فعليًا على `f2577ca`**.`
2. `## التطابق الثلاثي (مُشاهد على الالتزام f2577ca)`
3. `| الخاتمة | (هذا الالتزام) | PY311_VERIFICATION.md النهائية + هذا السجل |`
4. `## تشغيلات GitHub Actions المعتمدة (على الالتزام f2577ca)`

استُبدلت كلها بأدق (توثيق تشغيلات الالتزام الختامي 10c2bf5 نفسه).

## R-682 — الالتزام التصحيحي (2026-10-16): 7 أسطر — مدققة في نفس الالتزام

الأسطر السبعة (حرفيًا من الـstaged diff — كلها تصويبات صياغية لأرقام
وأوصاف سابقة، لا حذف معلومات):

1. `**سطر افتتاحي صريح:** لا حذف وظائف...` — استُبدل بنسخة مصوبة (المجموع 149)
2. `| forensics/*.md | — | 50 | ...` — استُبدل بتفصيل الملفات (48)
3. `## R-682 — إصلاح متغير غير معرف في verify.sh (2026-10-16): 10 أسطر` — استُبدل بـ9
4. `الأسطر العشرة (حرفيًا)...` — استُبدلت بالأسطر التسعة مع التصويح
5. `` `if [ "$CI_CONCLUSION" != "success" ]` مع أسطر الصدى الخاص بهما. `` — جزء من الاستبدال
6. `الثلاثة على SHA واحد (11 اختبارًا) + مخرجات كاملة محفوظة (لا مقتطفات).`
7. `- **نصوصها ليست مخزنة في المستودع** — تُحفظ تلقائيًا خارج المستودع في مسار جلسة العمل المحلي.` — سطر إفصاح المستشار القديم (استُبدل بصياغة مميزة للنصوص الأصلية عن النسخ المضمّنة).

**تصويح لاحق (بعد تدقيق المستشار):** الاستخراج الأولي أسقط السطر السابع لأنه
يبدأ بشرطة (نمط `^-[^-]`) — مخالفة توثيقية في هذا الالتزام التصحيحي نفسه
(قائمة ناقصة)، مسجلة هنا بأثر رجعي ومدرجة في نص استثناء المالك (البند ٥). — استُبدل بـ(9 اختبارات)

## R-682 — الالتزام التصحيحي الثاني (2026-10-16): 12 سطرًا — مدققة في نفس الالتزام

استخراج الحذوفات من مقاطع التغيير في الـstaged diff (بما فيها الأسطر
البدائية بشرطة — لا نمط `-[^-]`) — كلها استبدالات تصويبية، لا حذف معلومات:

- مدخل f2577ca: سطرا الصياغة الخاطئة («مسجلة في مدخل 20a81ce») — استُبدلا
  بالتصويح (f2577ca دُقق في التزامه لكن بعدد خاطئ؛ 20a81ce يسبقه).
- مدخل 7164044: سطر البند السادس — استُبدل بصيغة تشير للتسعة.
- FINAL_CLOSURE: 3 أسطر فقرة القياس القديمة — استُبدلت بالقياس كامل القبض
  (stdout + stderr + exit).
- OPERATIONAL_TESTS: 6 أسطر قسم القياس القديم — استُبدل بالقياس المكتمل
  وملاحظته المنهجية (stderr لا ملف السجل هو مسار أخطاء المعالج).

---

## قاعدة جديدة بقرار المالك (Issue #8، 2026-10-16): # DELETION-JUSTIFIED

> أي التزام جديد يحذف سطرًا واحدًا أو أكثر بلا العلامة
> `# DELETION-JUSTIFIED` في نفس الالتزام (رسالة الالتزام أو الفرق نفسه)
> يُرفض تلقائياً — وظيفة CI تفحص حذوفات كل التزام مدفوع وتفشل إن غابت
> العلامة. (الاستثناء الوحيد: الالتزامات الدمجية.)

هذه القاعدة **إضافة** إلى القاعدة الأصلية (التدقيق في نفس الالتزام) —
لا تحل محلها: العلامة شرط قبول، والتدقيق في السجل يبقى واجبًا لكل حذف.


---

## مرحلة صفر 2026-10-16 (تصويح ادعاء 33/50): 6 أسطر حذف — مستخرجة فعليًا من الـstaged diff

`git diff --cached --numstat` قبل الالتزام (724 إضافة / 6 حذف):
`docs/PROJECT_STATE.md` (2+2)، `docs/ROADMAP.md` (1+1)،
`forensics/PHASE1_STATUS.md` (17+2)، `forensics/PHASE2_STATUS.md` (12+1).

كل الأسطر الستة المحذوفة استبدالات تصويبية لادعاء رقمي غير دقيق من سلف
(«33 passed» → «50 passed» — التجميع الفعلي للأمر الموثق 50، مثبتًا على
الالتزامين 42446ac وdfd5a16 نفسيهما): كل سطر معدل استُبدل بصيغة مصوبة
تنص على التصويح صراحة — لا حذف معلومات. التفصيل في
`forensics/PHASE0_ROUND_2026-10-16.md` والسجل المصوِّح في كل ملف.

ملاحظة أثر: `forensics/pytest_results.xml` استُعيد لنسخة HEAD بعد حفظ ناتج
تشغيل هذه الجولة باسم مرتبط بالـSHA (`pytest_results_dfd5a16.xml` +
`verify_full_dfd5a16.log`) — لا استبدال للأثر العام في هذا الالتزام.
العلامة `# DELETION-JUSTIFIED` في رسالة الالتزام نفسه (قاعدة Issue #8).

---

## تصحيح ثانٍ 2026-10-16 (استكمال مطالب المراجعة): 37 سطرًا — مستخرجة فعليًا من الـstaged diff

`git diff --cached --numstat` (142 إضافة / 37 حذف):
- `forensics/PHASE1_STATUS.md` (2+2) و`forensics/PHASE2_STATUS.md` (2+2):
  استبدالات تقييدية — مصادقة «جوهر الادعاء» استُبدلت بنطاق ما تحقق منه فعليًا
  (ملفات + أمر موثق؛ لا مطابقة مراسٍ ضد أصل غائب) + مؤشر نطاق على سطر الخاتمة.
- `forensics/PHASE0_ROUND_2026-10-16.md` (62+29): إعادة كتابة سجل الجولة نفسه
  (ملف هذه الجولة) — إضافة جرد الادعاءات والتحقق من أصل Issue #8 وإفصاح
  فجوة القياس؛ لا حذف أدلة (كل ما حُذف استُبدل بأوسع منه في النسخة الجديدة).
- 4 أسطر روابط معطوبة (1+1 لكل من CONTRACT_EXCEPTION_1 / FINAL_CLOSURE_R-682 /
  OWNER_DECISIONS / THIS_ROUND_VIOLATIONS): اسم مستودع خاطئ صُحح
  (`reeverero-tech` → `reeveero-tech`) — تصحيح رابط، لا حذف معلومات.

العلامة `# DELETION-JUSTIFIED` في رسالة الالتزام نفسه (قاعدة Issue #8).

---

## تصحيح ثالث 2026-10-16 (إصلاح الحارس + سحب ادعاءات): 57 سطرًا — من الـstaged diff

`git diff --cached --numstat` (98 إضافة / 57 حذف):
- `forensics/PHASE0_ROUND_2026-10-16.md` (50+49): إعادة كتابة سجل الجولة نفسه —
  سحب ادعاءات غير مُثبتة + جرد معلن الحدود + تصحيح ادعاء الإثبات المستقبلي.
- `forensics/PHASE1_STATUS.md` (1+1) و`forensics/PHASE2_STATUS.md` (1+1): استبدال
  الخاتمة المطلقة («لا ناقص ولا مكسور») بنتيجة محددة — لا حذف معلومات.
- `tests/invariants/test_phase_status_numbers_match_reality.py` (32+6): إصلاح
  عدّ المرشحات في `_collect` (البسط لا المقام) — 6 أسطر استُبدلت بالنسخة
  المصححة + إضافة اختبار سلوكي حقيقي لمسار -k.

كلها استبدالات تصويبية داخل ملفات هذه الجولة أو إصلاح كود — لا حذف معلومات.
العلامة `# DELETION-JUSTIFIED` في رسالة الالتزام نفسه (قاعدة Issue #8).

---

## تصحيح رابع 2026-10-16 (تصويب رقمي + استكمال الجرد): 22 سطرًا — من الـstaged diff

`git diff --cached --numstat` (59 إضافة / 22 حذف):
- `forensics/PHASE0_ROUND_2026-10-16.md` (43+22): إعادة كتابة سجل الجولة نفسه —
  استكمال جدول الجرد بالملفات المتبقية + إفصاح فجوة قياس الجولة الثالثة +
  التوضيح المنهجي (6/16 تشخيص لا RED). لا حذف معلومات — كل محذوف استُبدل
  بأوسع في النسخة الجديدة.

العلامة `# DELETION-JUSTIFIED` في رسالة الالتزام نفسه (قاعدة Issue #8).

---

## تصحيح خامس 2026-10-16 (تصحيح النسب + أدلة الجرد): 35 سطرًا — من الـstaged diff

`git diff --cached --numstat` (55 إضافة / 35 حذف):
- `forensics/PHASE0_ROUND_2026-10-16.md` (40+35): إعادة كتابة سجل الجولة نفسه —
  تصحيح نسب قرار النطاق + أدلة الجرد الكاملة + توثيق فجوة الجولة الرابعة +
  القياس الحي الفعلي. لا حذف معلومات — كل محذوف استُبدل بأدقّ منه.

العلامة `# DELETION-JUSTIFIED` في رسالة الالتزام نفسه (قاعدة Issue #8).

## تصحيح سادس 2026-10-16 (تصويب صريح لادعاءَي [PHASE0-5] + استكمال الجرد بالبحث غير المبتور): 26 سطرًا — من الـstaged diff

`git diff --cached --numstat` (72 إضافة / 26 حذف):
- `forensics/PHASE0_ROUND_2026-10-16.md` (50+26): إعادة كتابة سجل الجولة نفسه —
  تصويب صفوف الجرد (rotation: لقطتان لا تثبتان وحدهما؛ الخيوط: توكيدات
  فعلية لا إظهار رسالة الخطأ؛ return-None: مستويات مختلفة لا ادعاء موحدًا)
  + فصل الخلاصة إلى ثلاث فئات + صفوف جديدة (Issue #7، الماسح، OPEN_QUESTIONS،
  KEY_LOSS، التشغيلان التاريخيان) + توثيق نطاق البحث (99 نتيجة) + إدخالات
  CHANGELOG و [PHASE0-5] بقيت كما هي (لا حذف — التصويب إضافة [PHASE0-6]).
  لا حذف معلومات — كل محذوف استُبدل بأدقّ منه وفق اعتراضات المراجعة
  (الجولات 7-9).

العلامة `# DELETION-JUSTIFIED` في رسالة الالتزام نفسه (قاعدة Issue #8).

## تصحيح سابع 2026-10-16 (تصويبات المراجعة النهائية المحصورة): 10 أسطر — من الـstaged diff

`git diff --cached --numstat` (30 إضافة / 10 حذف):
- `forensics/PHASE0_ROUND_2026-10-16.md` (17+10): (1) تصحيح مرجع التزام
  f8576e1→f8526e1 (خطأ مطبعي أُدخل بإعادة الكتابة — المرجع الصحيح من سجل Git)؛
  (2) استبدال تعميم «كل ملفات الجدول قُرئت كاملة» بوصف مطابق للصفوف؛
  (3) استبدال تعميم «كل رقم من تشغيل فعلي» بفصل أرقام التشغيل المشاهدة عن
  الأرقام التاريخية المنقولة؛ (4) فصل درجة التحقق بين Ed25519 (موثق داخليًا
  فقط) وIssue #7 (متحقق من أصله). لا حذف معلومات — كل محذوف استُبدل بأدقّ منه.

العلامة `# DELETION-JUSTIFIED` في رسالة الالتزام نفسه (قاعدة Issue #8).

## بناء 2026-10-16 (الجولة الإنشائية — المراحل 3-7): 36 سطرًا — من الـstaged diff

`git diff --cached --numstat` (إجمالي الإضافات 691 / الحذوفات 36 — كلها استبدالات):
- `backend/tests/invariants/test_keyring_immutability.py` (59+22): حذف 3 مواقع skip
  — استُبدلت بفشل صريح (KeyRing الفارغ = انتهاك) وإثبات مسار التوليد R-610
  فعليًا في جذر معزول (قاعدة المالك: لا skip).
- `backend/tests/invariants/test_compat_sunset_criteria.py` (54+3) و`test_all_entrypoints_respond.py`
  (4+4): حذف تخطيين متقادمين (المسار/الملف موجودان) — استُبدلا بتوكيد صريح.
- `backend/tests/invariants/test_no_mock_outside_tests.py` (55+2): توسيع ALLOWED_DIRS
  (إدراج backend/tests/ — مجلد اختبارات شرعي بعد نقل invariants إليه).
- `backend/tests/invariants/test_no_orphan_modules.py` (3+2) و`test_no_unsigned_ledger_events.py`
  (79+1): تحديث المسار الذاتي للمسبار + إصلاح التزوير (التعديل على blob الموقّع).
- `backend/compat/__meta__.py` (7+2): تحسين الديكوريتور بـ functools.wraps.
- النقل بـ git mv (الستة) — إعادة تسمية موثقة لا حذف ملفات.

العلامة `# DELETION-JUSTIFIED` في رسالة الالتزام نفسه (قاعدة Issue #8).

## جولة تصويبات المراجع (بعد b2da7f1) — 216 سطرًا محذوفًا

- `backend/sovereign/score.py` (~150): استبدال كتلة v2 الأولى (أسماء مجردة
  + فحص وجود للسجل الخام + ثابت نجاح) بالنسخة المصوبة (هويات منقطة كاملة،
  لا مس للسجل، دليل invariants معلوم الهوية). # DELETION-JUSTIFIED: استبدال
  تنفيذ معيب بتنفيذ مصوب — الحارس (اختبارات المسار) يغطي الجديد.
- `backend/tests/invariants/test_no_unsigned_ledger_events.py` (~35): استبدال
  المصنف القديم (يقبل UNVERIFIABLE_MISSING_KEY دون قيد) بمصنف البدائل
  الثلاثة. # DELETION-JUSTIFIED: الكاشف القديم كان يقبل أحداثًا غير موقعة
  غير مرساة — عيب أمان.
- `backend/tests/invariants/test_compat_sunset_criteria.py` (~12): استبدال كاشف
  الملفات بكاشف السجل (importlib). # DELETION-JUSTIFIED: الكاشف القديم
  قابل للخداع بتعليق نصي.
- `backend/tests/invariants/test_keyring_immutability.py` (~8): توسيع فحص
  الوجود/JSON إلى مقارنة git فعلية. # DELETION-JUSTIFIED: الفحص القديم لم
  يكن يرفض حذف أسطر.
- `backend/tests/conftest.py` + `tests/fixtures/synthetic_ledger.py` (~11):
  إعادة كتابة اشتقاق المسارات + وضع إعادة الاستخدام. # DELETION-JUSTIFIED:
  الاشتقاق القديم كان كاسرًا خارج سياق واحد.

---

## جولة الإغلاق (2026-10-16) — حذوفات هذا الالتزام

| الملف | المحذوف | المبرر |
|---|---|---|
| backend/sovereign/score.py | 24 سطرًا | # DELETION-JUSTIFIED — أمر المالك (جولة الإغلاق، القسم ٢): إخراج مكوّني السجل من المعادلة — حُذفت أسطر حدّهما الأعلى (ledger_upper)، ودالة التجميع الداخلية _final، وكتلة confidence_range، وأسطر docstring القديمة الموثقة للمعادلة المقيدة — استُبدلت بأسطر null المعلنة والعلم false ومتوسط الخمسة القابلة للقياس (23 سطرًا مضافًا). |

مطابقة الحذوفات التاريخية (556 مقابل 216) موثقة في
forensics/DELETIONS_RECONCILIATION_556_216.md والملحق
DELETED_LINES_AUDIT_ADDENDUM.md (5753ab8) — وسم رسالة الالتزام لا يغطي هذه
الحذوفات الجديدة؛ هذا القسم هو سجلها.

---

## جولة R-683 (2026-10-16) — حسم تعارض القسمين ٢ و٦ بقرار المالك

**كيف وُجد:** فحص المرحلة صفر على HEAD `91c92f3` أعطى محليًا (Python 3.11.15)
`1 failed, 465 passed, 1 skipped`، وانتهى CI run `38877956328` على الـ SHA نفسه
بـ failure (`1 failed, 466 passed`). الاختبار الفاشل هو
`test_all_entrypoints_respond.py:176`. التخطي المحلي سببه بيئي: `data/key.secret`
غائب في أول تشغيل خارج verify.sh.
**تصويب صريح للسلف:** عنوان الالتزام `91c92f3` "إغلاق نظيف" غير صحيح، لأن
الشجرة دُفعت حمراء وCI فشل عليها. وسجل "جولة الإغلاق" أعلاه يقول إن أسطر الحد
الأعلى `ledger_upper` حُذفت، وهذا غير صحيح أيضًا: `ledger_upper` ما زال معرّفًا في
`backend/sovereign/score.py` (كود ميت لا يدخل الرد). لم يُحذف في هذه الجولة لأن
قرار المالك حصر النطاق، فيبقى بندًا **مفتوحًا**.
**خلل إضافي وُجد:** حقل `aggregation` كان يقول `mean(7 scored components)`
بينما `final_score` يُحسب على 5 مكونات.

**قرار المالك (R-683):** تحديث الاختبار ليعكس العقد الجديد ليس تخفيفًا، بل هو
التنفيذ الصحيح للقسم ٢. المطلوب التزام واحد.

| # | الملف | المحذوف | المبرر |
|---|---|---|---|
| 1 | backend/sovereign/score.py | 9 أسطر: `"ledger_verified": None` و`"ledger_anchored": None` وتعليقها (3 أسطر)، و`result["score_capped_by_missing_ledger"] = False`، وسطرا نص `ledger_components_note` القديم ("declared null")، وسطر docstring "null معلنة" | # DELETION-JUSTIFIED — عقد الدرجة تغيّر بقرار مالك؛ المكوّنات غير القابلة للقياس أُزيلت بدلًا من تقديرها بأعلى نظري. حقل `confidence_range` كان قد حُذف من الكود في `91c92f3`، فحذفه في هذه الجولة يقتصر على توكيدات الاختبار. صُحح نص الملاحظة ليطابق الإزالة، فلم يعد يقول "null معلنة". |
| 2 | backend/sovereign/score.py | سطر واحد: `"final_score = mean(7 scored components) — ..."` | # DELETION-JUSTIFIED — استُبدل "mean(7)" بـ"mean(5)". صار العدد يُشتق من `len(measurable)` الفعلي، فلا يبقى رقمًا مكتوبًا يدويًا. |
| 3 | backend/tests/invariants/test_all_entrypoints_respond.py | 21 سطرًا: docstring القديم، وحلقة المكونات الثمانية، وتوكيد `score_capped_by_missing_ledger is True`، وتوكيدات `confidence_range`، و`in (0, 1)` للثنائيين، و`"source" in ev and "head_sha" in ev` | # DELETION-JUSTIFIED — تحديث اختبار ليعكس عقدًا جديدًا بقرار مالك، ليس تخفيفًا. يتضمن البديل: قائمة الحقول بالضبط، وغياب الحقول الأربعة بتوكيد لكل منها، والمكونات الخمسة أرقامًا في [0,1] بتوكيد لكل منها، و`final_score` يساوي mean(5)، و`aggregation` يساوي النص حرفيًا. لا `in (...)` ولا `or`. |

**الإثبات:**
- RED: الاختبار الجديد على الكود القديم فشل (`1 failed`) برسالة
  `roadmap_v2 fields mismatch: [... 'ledger_anchored', ..., 'ledger_verified', ..., 'score_capped_by_missing_ledger']`.
- GREEN: الاختبار نفسه بعد الإصلاح أعطى `1 passed`. الحزمة كاملة محليًا أعطت
  `467 passed, 1 deselected` (0 skipped، 0 failed).
- `forensics/SOVEREIGNTY_FINAL.json` أُعيد إنتاجه بالمكوّنات الخمسة فقط وبلا حد
  أعلى معلن. الدرجة `0.8198`، وهي مساوية للقيمة السابقة لأن الحاسبة السابقة كانت
  تحسب متوسط الخمسة نفسها.

## جولة تنظيف R-683 (2026-10-16) — بقايا النطاق المقيد بأمر المالك

| الملف | المحذوف | المبرر |
|---|---|---|
| backend/sovereign/score.py + backend/app.py | 3 أسطر `ledger_upper` في score.py + سطر تعليق واحد في app.py | # DELETION-JUSTIFIED — ‏`ledger_upper` كود ميت منذ R-683، لا يدخل الرد ولا يُقرأ في أي مكان. تعليق app.py "الثمانية مكونات" صُحح إلى "خمسة مكونات قابلة للقياس" ليطابق العقد. رُفع القيد على هذين البندين فقط بأمر المالك. |
| 2026-10-16 | **إعادة القسم ٤ (أمر المالك السباعي)** — استبدال JUnit الجولة السابقة (أداة أدلة متتبعة) بـJUnit تشغيل التحقق على رأس التراجع 7c078a8 (467/0/0/1deselected، منتج run_gate داخل verify.sh --full بـVERIFY_EXIT=0) | 469 | **مُبرر — استبدال أداة أدلة لا حذف كود:** الملف المصدَّق على استبداله هو نفسه نية الالتزام الأصلي 7de74ac (الذي رفضته بوابة Issue #8 لغياب العلامة) منفذة هذه المرة بالعلامة والمدخل والسبب المكتوب. سطر `<testsuite … timestamp="…">` الواحد داخل الاستبدال: ختم الجولة السابقة → ختم هذه الجولة (زمن التشغيل الفعلي الموثق في run_gate) — استبدال معلن بسبب مكتوب. لا force-push — التزام إعادة جديد بعد revert نظيف (a038410، bda96f9، 7c078a8). تفاصيل المخالفة الأصلية وتصويبها: `forensics/council_prep/VIOLATION_7de74ac.md` | قيد المراجعة (هذا الالتزام) |
| 2026-10-17 | **جولة المجلس <1> (الأمان)** — معالجة بنود أمين/بصير/حكيم (الالتزام 8a5e9bf: 43 ملفًا، +2736/−125 — محسوبة من فهرس الالتزام المدفوع) | 125 | **تصحيح رقمي (اعتراض المراجع الرابع):** السطر المدفوع في 8a5e9bf كان يقول «36 ملفًا +2570» — أرقام مرحلة سابقة قبل إضافة سجلات أدلة بصير (baseer_*.log) واستثناء .gitignore لها؛ التصحيح هنا يطابق فهرس 8a5e9bf فعليًا (43 ملفًا، +2736/−125). **التقسيم الفعلي للحذوفات الـ125 (محسوب من numstat الالتزام):** 77 سطرًا كود إنتاج (backend 43 + nexus 21 + guardian 13) + 17 سطر اختبارات + 29 سطر توثيق (docs) + 2 سجل أدلة (forensics). إذن المالك شمل الالتزام الكامل «43 ملفًا +2736/−125» كما عُرض عليه حرفيًا. **مُبرر # DELETION-JUSTIFIED — إذن مالك صريح (2026-10-17 03:30 +03: «نعم — احذف وأدفع» للنطاق المعروض: الالتزام الكامل 43 ملفًا) + أمر معالجة المجلس (D-029 ق٣):** أبرز حذوفات الكود: (1) `encryption_engine.py` — فروع سقوط XOR ودالة `_xor_encrypt` (تشفير قابل للكسر — أثبته بصير P02 وحكيم وأمين 5.1)؛ (2) `master_guardian.py` — العبارة الافتراضية المنشورة `CHANGE_ME_IMMEDIATELY`؛ (3) `app.py` — استقبال السر في query؛ (4) `emergency_breaker.py` — طباعة رمز الفك في السجل؛ (5) `verifier.py` — فرع فحص الحالة قبل HMAC. لا حذف وظيفة حية: كل بديل أضمن، وكل حذف مغطى باختبار سلوكي. | مُصحح في هذا الالتزام (دورة تحقق مستقلة) |
| 2026-10-17 | **إصلاح حارس D-032** — الحارس أوقع التزام 95e1e7b نفسه: ملف الاختبار اقتبس قيمة المفتاح المخترق الحقيقية كـfixture (11 سطرًا في tests/test_no_private_keys_in_commit_history.py) | 11 | **مُبرر # DELETION-JUSTIFIED — سلطة قرار المالك D-032 نفسه** («المفتاح يُدار كمسرّب»): إعادة اقتباس القيمة المخترقة في ملف اختبار مخالفة مباشرة للقرار؛ الحذف هو الإصلاح المُوجب — استبدال القيمة الحقيقية بمادة اصطناعية + إزالة دالة ميتة + استثناء موثق لمسار ملف الحارس (fixtures اصطناعية بالتعريف). اكتشف الحارس الفشل في CI فعليًا (الالتزام 95e1e7b رُفض: «التزامات تحوي أنماط مفاتيح خاصة غير موثقة») — إثبات أن الحراسة ذات أسنان حقيقية. | مُنفذ في هذا الالتزام |
| 2026-10-17 | **إزالة استثناء مسار حارس D-032** (اعتراض المراجع: ثقب يسمح بإيداع مفتاح حقيقي في مسار ملف الحارس بلا كشف) — إعادة كتابة الحارس (78 سطرًا: سطر الاستثناء + أسطر fixtures الحرفية) + تصحيح ادعاءات التدوير في SECURITY.md (12) وتعديل نسبة تأجيل D-033/D-034 في DECISIONS.md (4) | 94 | **مُبرر # DELETION-JUSTIFIED — سلطة قرار المالك D-032 + اعتراض المراجع الملزم** («الإصلاح المباشر: أزل استثناء المسار»): البديل أضمن — fixtures تُبنى وقت التشغيل بلا أي قيم حرفية تطابق الأنماط، واستثناءات تاريخية محددة (التزام+مسار+نوع+بصمة) لالتزامي 95e1e7b/ad6b105 فقط. RED مُشاهَد: اختبار ثقب المسار فشل مع الاستثناء القديم ثم نجح بدونه. | مُنفذ في هذا الالتزام |
| 2026-10-17 | **استكمال اعتراضي المراجع على D-032**: تغطية private_backup2 (لاحقة رقمية) في نمط الحارس + تدقيق دليل التدوير (مسارات التحميل والتوقيع + دقة سجلات المراسي) | 14 | **مُبرر # DELETION-JUSTIFIED — سلطة D-032 + اعتراض المراجع الملزم**: (أ) 4 أسطر في ملف الحارس: تعديل سطر النمط private_[a-z_]+ إلى private_[a-z0-9_]+ وسطر الاختبار إلى private_backup2 — RED مُشاهَد قبل الإصلاح (فشل الاختبار بالنمط القديم) ثم GREEN؛ (ب) 10 أسطر في SECURITY.md: استبدال فقرات التدوير بأدلة أدق (مسارات التحميل/التوقيع + دقة المراسي + صياغة السؤال التشغيلي للمالك). كلها تحسينات دقة بديلها أضمن، لا حذف وظيفة. | مُنفذ في هذا الالتزام |


| 2026-10-17 | **استرجاع نظيف (1/3) — أمر المالك: استرجاع وإعادة تنفيذ D-034** — تراجع الالتزام 5858225 (تصحيح نسب الإثبات) | 47 | **مُبرر # DELETION-JUSTIFIED — أمر المالك الصريح 2026-10-17 («القرار: الخيار ٢ — استرجاع وإعادة تنفيذ... لا force-push، لا rebase»):** الحذوفات الـ47 (numstat الالتزام الفعلي: 44 سطر ملف الأدلة + سطرا SECURITY + سطر مدخل تدقيق واحد — إضافات 5858225 كانت 48 لكن الاسترجاع استبدل سطرَي مدخل التدقيق القديمين بسطر واحد للتصحيح فصار الصافي 47) — التراجع يحرر الشجرة من الجولة الأولى المنتهية بالاسترجاع تمهيدًا لإعادة التنفيذ النظيفة في التزام واحد. لا حذف وظيفة حية: كل محذوف سيعاد تأليفه في التزام الإعادة. | مُنفذ في هذا الالتزام |

| 2026-10-17 | **استرجاع نظيف (2/3) — أمر المالك: استرجاع وإعادة تنفيذ D-034** — تراجع الالتزام 6b5b0eb (تصحيح اعتراض المراجع الأول) | 225 | **مُبرر # DELETION-JUSTIFIED — أمر المالك الصريح 2026-10-17 (الخيار ٢):** الحذوفات الـ225 (numstat الالتزام الفعلي: tests/test_cors_production_fail_closed.py — 73؛ forensics/D034_CORS_FAIL_CLOSED.md — 111؛ backend/config.py — 16؛ OWNER_REQUIRED.md — 9؛ docs/DECISIONS.md — 9؛ docs/SECURITY.md — 4؛ سجل التدقيق — 3 بعد حل التعارض) — التراجع يحرر الشجرة من الجولة الأولى تمهيدًا لإعادة التنفيذ النظيفة في التزام واحد. لا حذف وظيفة حية: كل محذوف سيعاد تأليفه في التزام الإعادة. تعارض سجل الحذوفات حُل يدويًا (المدخل الأصلي لـ2a52f02 استُرجع + مدخل الاسترجاع 1/3 بقي). | مُنفذ في هذا الالتزام |

| 2026-10-17 | **استرجاع نظيف (3/3) — أمر المالك: استرجاع وإعادة تنفيذ D-034** — تراجع الالتزام 2a52f021 (التنفيذ الأول) | 281 | **مُبرر # DELETION-JUSTIFIED — أمر المالك الصريح 2026-10-17 (الخيار ٢):** الحذوفات الـ281 (numstat الالتزام الفعلي: tests/test_cors_production_fail_closed.py — 137؛ forensics/D034_CORS_FAIL_CLOSED.md — 101؛ backend/config.py — 17؛ OWNER_REQUIRED.md — 7؛ docs/DECISIONS.md — 6؛ docs/OPERATIONS.md — 1؛ docs/SECURITY.md — 8؛ tests/test_config_security.py — 3؛ سجل التدقيق — 1) — سبب الاسترجاع: مدخل التدقيق داخل ذلك الالتزام غطى سطرَي config.py فقط من الحذوفات الـ12 (مخالفة التوثيق المتزامن — قرار المالك: الاسترجاع وإعادة التنفيذ بتدقيق كامل داخل التزام واحد). لا حذف وظيفة حية: كل المحذوف سيعاد تأليفه في التزام الإعادة. | مُنفذ في هذا الالتزام |

| 2026-10-17 | **إعادة تنفيذ D-034 في التزام واحد شامل (أمر المالك — الخيار ٢)** — التنفيذ الكامل: كود + اختبارات + توثيق + تدقيق الحذوفات معًا | 10 | **مُبرر # DELETION-JUSTIFIED — سلطة قرار المالك D-034 نفسه + أمر المالك الصريح 2026-10-17 («الحذوفات الـ12 سطرًا... + مدخل DELETED_LINES_AUDIT.md الكامل — كلها في هذا الالتزام الواحد. لا انقسام»):** التقسيم الفعلي للحذوفات الـ10 (من numstat الالتزام): (1) backend/config.py — سطرا شرط التحذير الإنتاجي القديم (`if CORS_ORIGINS == ["*"] and IS_PRODUCTION:` + سطر warnings.warn الخاص به) استُبدلا بتحذير تطويري + قاعدة رفض في validate_config() — البديل أضمن: تحذير لا يمنع ≠ رفض يمنع؛ (2) OWNER_REQUIRED.md — 3 أسطر فقرة البند ٦ القديمة استُبدلت بحالة التنفيذ؛ (3) docs/DECISIONS.md — سطرا حالة D-034 القديمة استُبدلا بالحالة الجديدة (لا مساس بحالة D-033 — الجولة الأولى علّمت الدرس: كتلة D-033 لم تُمس هذه المرة)؛ (4) docs/OPERATIONS.md — سطر صف جدول واحد؛ (5) docs/SECURITY.md — سطرا RK-02 (سطر التحذير + سطر الحالة) استُبدلا بحالة التنفيذ. لا حذف وظيفة حية، وكل استبدال أضمن. RED مُشاهَد على الشجرة المسترجعة (7 فشلوا — كل مسارات الرفض كانت تُقبل) ثم GREEN (9 passed) — forensics/D034_CORS_FAIL_CLOSED.md | مُنفذ في هذا الالتزام |

| 2026-10-17 | **تصحيح توثيقي — أمر المالك 2026-10-17 (الخيار ١، القاعدة ١ حرفيًا)** — سطر واحد لكل سطر مصحح | 12 | **مُبرر # DELETION-JUSTIFIED — أمر المالك الصريح (تصحيح توثيقي واحد، لا كود، لا استرجاع):** الحذوفات الـ12 هي الأسطر القديمة المستبدلة في التصحيحات الثلاثة أدناه — كل سطر قديم مذكور حرفيًا ومقابله الجديد وسببه. لا حذف معلومة: كل قديم → أصدق جديد. | مُنفذ في هذا الالتزام |
| | تصحيح توثيقي — docs/SECURITY.md — السطر القديم حرفيًا: `| CORS | 🟡 مقيد جزئيًا (R-107): يقرأ CORS_ORIGINS لكن الافتراضي * مع تحذير فقط — يجب ضبطه في الإنتاج (بند مفتوح) |` → السطر الجديد حرفيًا: `| CORS | ✅ fail-closed (D-034 — 2026-10-17): يرفض الإقلاع إذا ENV=production وCORS_ORIGINS ∈ {*, null, []} |` — السبب: تناقض مع الكود المنشور في e6a9019 (الصف القديم نجا من سكربت متعثر ولم يُستبدل) | 1 سطر |
| | تصحيح توثيقي — forensics/DELETED_LINES_AUDIT.md — السطر القديم (مدخل 4fecc14) حرفيًا: `| 48 | مُبرر... الحذوفات الـ48 هي بالضبط إضافات الالتزام 5858225 (44 سطر ملف الأدلة + سطرا SECURITY + سطرا مدخل التدقيق)` → الجديد حرفيًا: `| 47 | مُبرر... الحذوفات الـ47 (numstat الالتزام الفعلي: 44 سطر ملف الأدلة + سطرا SECURITY + سطر مدخل تدقيق واحد — إضافات 5858225 كانت 48 لكن الاسترجاع استبدل سطرَي مدخل التدقيق القديمين بسطر واحد للتصحيح فصار الصافي 47)` — السبب: خطأ رقمي (numstat الفعلي 47) | 1 سطر |
| | تصحيح توثيقي — forensics/DELETED_LINES_AUDIT.md — السطر القديم (مدخل ee817bf) حرفيًا: `الحذوفات الـ225 هي بالضبط إضافات الالتزام 6b5b0eb (من numstat: 33 اختبارات + 83 أدلة + 16 config.py + 15 توثيق docs + 1 مدخل تدقيق + 77 إعادة صياغة ملف الأدلة)` → الجديد حرفيًا: `الحذوفات الـ225 (numstat الالتزام الفعلي: tests/test_cors_production_fail_closed.py — 73؛ forensics/D034_CORS_FAIL_CLOSED.md — 111؛ backend/config.py — 16؛ OWNER_REQUIRED.md — 9؛ docs/DECISIONS.md — 9؛ docs/SECURITY.md — 4؛ سجل التدقيق — 3 بعد حل التعارض)` — السبب: خطأ رقمي في التقسيم (المجموع صحيح) | 1 سطر |
| | تصحيح توثيقي — forensics/DELETED_LINES_AUDIT.md — السطر القديم (مدخل 9210b2c) حرفيًا: `الحذوفات الـ281 هي إضافات الالتزام 2a52f021 (من numstat: 137 ملف الاختبار الجديد + 101 ملف الأدلة الجديد + 17 config.py + 16 توثيق docs + 3 test_config_security + 1 مدخل التدقيق الأصلي + إعادة الملفين المحذوفين لحذفهما)` → الجديد حرفيًا: `الحذوفات الـ281 (numstat الالتزام الفعلي: tests/test_cors_production_fail_closed.py — 137؛ forensics/D034_CORS_FAIL_CLOSED.md — 101؛ backend/config.py — 17؛ OWNER_REQUIRED.md — 7؛ docs/DECISIONS.md — 6؛ docs/OPERATIONS.md — 1؛ docs/SECURITY.md — 8؛ tests/test_config_security.py — 3؛ سجل التدقيق — 1)` — السبب: خطأ رقمي في تقسيم التوثيق (المجموع صحيح) | 1 سطر |
| | تصحيح توثيقي — forensics/D034_CORS_FAIL_CLOSED.md — السطر القديم حرفيًا: `النجمة داخل قائمة مختلطة (بترتيبَيها)،` (مع بقية الجملة) → الجديد حرفيًا: `النجمة داخل قائمة مختلطة (الترتيب الأول https://app.example.com,* هو ما شوهد فشلًا فعلًا — حلقة الاختبار تتوقف عند أول توكيد فاشل فلم يُشغَّل الترتيب الثاني في RED؛ الترتيبان كلاهما اجتازا GREEN)` — السبب: صياغة غير دقيقة (نسب مشاهدة RED للترتيبين معًا) | سطران |
| | تصحيح توثيقي — forensics/D034_CORS_FAIL_CLOSED.md — السطر القديم حرفيًا: `--collect-only: 504 مُجمَّع، 1 deselected (495 أساس + 9 جديدة).` → الجديد حرفيًا: `--collect-only (تشغيل فعلي على شجرة e6a9019 وحُفظ مخرجه): 503/504 tests collected (1 deselected)` — السبب: صياغة غير دقيقة (الرقم لم يكن مدعومًا بتشغيل محفوظ — شُغّل الآن فعلًا) | 1 سطر |
| | تصحيح توثيقي — forensics/D034_CORS_FAIL_CLOSED.md — القسمان القديمان حرفيًا: `(تُلحق بعد اكتمال دورة CI/verify-full)` مع سطري النائبتين `(يُلحق بالتشغيل الفعلي)` → الجديد حرفيًا: أرقام التشغيلات الفعلية (CI 39012782332 — 503/0/0؛ verify-full 39013238466 — VERIFICATION COMPLETE بتطابق ثلاثي؛ وتشغيلات الاسترجاعات 39014371896/39014373227/39011940788) — السبب: صياغة غير دقيقة (نائبتان معلقتان عُبئتا بالتشغيل الفعلي المحفوظ) | 5 أسطر |

| 2026-10-17 | **الجولة <2> — إصلاحات حراس الـInvariants (قرار المالك R2-3 — موافقة صريحة على 114 سطرًا + 16 سطرًا من أوامر R2-4 والقسم ٢)** — إحلالات منطق زائف: 127 سطرًا داخل ملفات اختبارات الحراس + 3 أسطر كود إنتاج في backend/sovereign/ledger/anchor.py (توجيه حساب الجذر v1/v2 — D-036) | 130 | **مُبرر # DELETION-JUSTIFIED — إذن مالك صريح (2026-10-17 «R2-3 — حذف 114 سطرًا: موافقة» + أمر R2-4 + أمر القسم ٢):** التقسيم الفعلي (numstat الدفعة): (1) test_no_orphan_modules.py — 53: استبدال مصفيات واسعة (إعفاء scripts/ والمجلدات، مطابقة اللاحقة القصيرة، endswith __init__) بتحليل وصول من الجذور ومطابقة مسارات محددة؛ (2) test_keyring_immutability.py — 61: استبدال مقارنة HEAD/HEAD~1 بانتقالات الأب/الابن الكاملة (rev-list --full-history --parents) + إصلاح الشرط الميت في فحص المؤشر النشط + حد الجدّ R2-2؛ (3) test_anchor_rejects_arbitrary_signature.py — 2: تحديث إعداد التوقيع لجذر v2؛ (4) backend/sovereign/ledger/anchor.py — 3: سطرا حساب الجذر القديم في anchor_batch وverify استُبدلا بتوجيه v2/v1 (D-036)؛ (5) tests/test_ledger_anchor.py — 2، tests/test_return_none_security.py — 2، tests/test_trust_conditions_fingerprints.py — 7: تحديث مساعدي التوقيع للمراسي الجديدة إلى جذر v2 (D-036). لا حذف وظيفة حية: كل استبدال أضمن — RED مُشاهَد لكل فجوة قبل الإصلاح (forensics/council/round-2/EVIDENCE_INDEX.md). | مُنفذ في هذا الالتزام |
| 2026-10-17 | **استثناء تاريخي موثق (قرار المالك R2-2 — الخيار ١)** — واقعة إزالة data/keys/HISTORY.jsonl من التتبع | 0 (لا حذف في هذه الدفعة) | **مدخل استثناء لا حذف:** الحارس المُشدَّد (انتقالات الأب/الابن) كشف أن الملف أُزيل من شجرة الالتزام ff8f80a (رسالته: «keyring.json وHISTORY.jsonl أُزيلت من git tracking») وأُعيد في a4c3154، واللقطة القديمة (05704ef) بادئة كاملة من الحالية. قرار المالك: قبولها كحادثة تاريخية موثقة لا تتكرر — الحارس يُنفذ العقد على التزامات ما بعد حد الجدّ a90b481 (إغلاق الجولة <1>) فقط، ويرفض أي حذف مستقبلي فورًا. لا يوجد حذف سطر فعلي في هذه الدفعة — هذا توثيق الحادثة التاريخية. | مُنفذ في هذا الالتزام |
| 2026-10-17 | **إصلاح بوابة CI (Issue #8) — رفض زائف مُثبت بالتشغيل** — سطر شرط العلامة في .github/workflows/ci.yml استُبدل بصيغة بلا grep -q | 1 | **مُبرر # DELETION-JUSTIFIED — صيانة البوابة نفسها (بديل أضمن، لا حذف قاعدة):** العطل: grep -q يخرج عند أول تطابق فيُقتل git show بإشارة SIGPIPE (خروج 141) ومع set -o pipefail يُحسب التطابق الصحيح فشلًا — البوابة رفضت الالتزام 1a9141f زائفًا رغم أن العلامة موجودة في فرقه 4 مرات (تشغيل 39057505124). الإصلاح: grep بلا -q يقرأ كل المخرج فلا SIGPIPE (مُثبت محليًا: مع -q خروج 141/141، بدونه 0/0). القاعدة (Issue #8) لم تُضعف — نفس المنطق حرفيًا. | مُنفذ في هذا الالتزام |
| 2026-10-17 | **حذوفات الالتزام 1a9141f (توثيق لاحق — البوابة رفضتها زائفًا قبل هذا الإصلاح)** | 2 | **مُبرر # DELETION-JUSTIFIED — إذن المالك R2-3:** السطران المحدفان في forensics/COUNCIL_TOPICS.md: صفّا جدول المواضيع «2 — صحة invariants وMerkle anchor | تالية — الجولة <2>» و«3 — الادعاءات في docs/ مقابل الكود | تالية» — استُبدلا بحالتي الجولة المحدثة (إغلاق <2> وتسمية <3>). إحلال حالة، لا حذف معلومة. | هذا الالتزام |
| 2026-10-17 | **تصحيحات دقة بعد اعتراض المراجع الأقوى** — جمل المالك الحرفية المستقلة + سطر الإفصاح أولًا + تصحيحات وقائع | 13 | **مُبرر # DELETION-JUSTIFIED — اعتراض المراجع الأقوى (إلزامي قبل التسليم):** (1) سطرا إفصاح قديمان بصيغة اقتباس في PROCESSING.md استُبدلا بالجملة الحرفية أول سطر (مع RAW الثلاثة وOWNER_REQUIRED وEVIDENCE_INDEX وFINAL_STATUS وCOUNCIL_CAPABILITY — إضافات)؛ (2) سطر جملة المالك في SECURITY.md استُبدل بالجملة الحرفية المستقلة ثم التفسير؛ (3) سطرا جملتي المالك في OPERATIONAL_CLAIM_SCOPE.md كذلك؛ (4) سطر مدخل التدقيق R2-3 صُحح (127 حراس + 3 anchor.py كود إنتاج، لا «حراس فقط»)؛ (5) سطر D-033 في PROJECT_STATE صُحح ليطابق DECISIONS.md؛ (6) سطر عدد المسبارات في CHANGELOG صُحح إلى فرق المعرفات الدقيق (+22). كل استبدال أدق، لا حذف معلومة. | مُنفذ في هذا الالتزام |
| 2026-10-17 | **استرجاع نظيف (1/6) — أمر المالك: رفض الاستثناءات، الاسترجاع والإعادة إلزاميان** — تراجع a76725d (تكملة اعتراضات المراجع: تتبع سجلات الأدلة الخام + برهان v1 الكامل + تعليق الإغلاق) | 3440 | **مُبرر # DELETION-JUSTIFIED — أمر المالك الصريح 2026-10-17 («القرار: رفض الاستثناءات الثلاثة. الاسترجاع والإعادة إلزاميان... استرجع الالتزامات الستة بالترتيب العكسي عبر git revert نظيف»):** الحذوفات = إضافات a76725d نفسها (numstat الالتزام الفعلي: 35 سجل أدلة round-2 معظمها + استثناء .gitignore الموجه + سطرا COUNCIL_TOPICS + 4 أسطر FINAL_STATUS + مدخل تدقيق + برهانا v1). التراجع يحرر الشجرة من المحاولة الأولى تمهيدًا للإعادة في التزام ذري واحد. لا حذف وظيفة حية: كل المحذوف سيعاد تأليفه في التزام الإعادة. | مُنفذ في هذا الالتزام |
