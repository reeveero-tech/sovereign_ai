# forensics/11777_BREAKDOWN.md — تفكيك رقم 11,777

**التاريخ:** 2026-10-16 — جولة تحقق للمالك (قراءة فقط — لا تعديل تنفيذي)
**الالتزام المرجعي:** `d56e24e8b0dfc7279befe48deb9c4bb9abcb2dad` (رأس main)

## مصدر الرقم بالضبط

الرقم 11,777 ليس ناتج أمر git — إنه **عدّ أحداث ملف محلي غير متتبع**:
`data/sovereign_core/ledger.jsonl` وقت كتابة `forensics/KEY_LOSS_TIMELINE.md`
(الالتزام `0fdc91b3f935f7aa5f723996ebb010e54c22daff`)، بإحصاء أسطر JSONL
(حدث واحد لكل سطر). أقرب أمر معادِل:

```
wc -l data/sovereign_core/ledger.jsonl   # = 11,777 وقت القياس (2026-10-14)
```

القياس موثق حرفيًا داخل الملف الملتزم:
`git show 0fdc91b:forensics/KEY_LOSS_TIMELINE.md` (جدول «الحالة العامة»:
11,777 حدثًا / 0 صالح التوقيع بالمفتاح الحالي / 11,777 فاشل).

## الحد التقني الصريح (قراءة إلزامية قبل الأرقام)

**الملف الخام غير متاح في clone الحالي** — `data/sovereign_core/ledger.jsonl`
غير متتبع في git (`.gitignore`) وغير موجود على قرص مساحة العمل الحالية،
وموثق غيابه في `forensics/NEW_AGENT_INITIAL_AUDIT.md` («ledger.jsonl موجود
(116,910 حدث) — غير موجود في clone»). لذلك:

- **التفكيك لكل حدث (كم فشل توقيعه فعليًا مقابل كم لم يُتحقق أصلًا) غير متاح** —
  يتطلب الأحداث نفسها (نص/توقيع كل حدث) وقد غابت مع الملف.
- **ملف CSV/JSONL يدرج كل حدث (event_id, timestamp, key_id, status): غير متاح** —
  لنفس السبب. البدائل أدناه مستمدة من ملف المراسي المتتبع فقط.

## ما هو متاح بدلًا منه: المحاسبة من ملف المراسي (متتبع على d56e24e)

المصدر: `data/sovereign_core/ledger.anchors.jsonl` (متتبع في git —
`git ls-files data/` يثبته) — محتواه الكامل مرفق أدناه حرفيًا.

| البند | القيمة | الدليل (من المراسي) |
|---|---|---|
| إجمالي الأحداث التي بلغها السجل قبل غياب الملف | **116,910** (الفهارس 0–116,909) | المرساة R643_FULL_COVERAGE_V2: batch 0–116909 |
| الأحداث داخل نطاق مرساة Merkle | **116,910 (كلها)** | المرساة النهائية تغطي 0–116909 بالكامل |
| الأحداث خارج نطاق المرساة | **0** | نفس الدليل |
| أحداث مرتبطة بالمفتاح المفقود `b8bf12ab28abfc01` | **116,452** (الفهارس 0–116,451) | 3 مراسات: PRE_KEYRING_UNSIGNED_BATCH (13,487) + BATCH_2 (90,837) + BATCH_3 (12,128) — ملاحظات المراسي: «unverifiable signatures due to lost key» |
| أحداث مرتبطة بالمفتاح `433759679aca9268` | **458** (الفهارس 116,452–116,909) | مرساتا R640/R641 (batch 116452–116909) |

**تصنيف «مفقود المفتاح» مقابل «موجود لكن غير قابل للتحقق»:** من المراسي
وحدها لا يمكن الفصل لكل حدث (المراسي تغطي نطاقات لا أحداثًا مفردة) —
الحد التقني مذكور أعلاه. كل الأحداث المرصوصة تحت المفتاح المفقود موصوفة
في ملاحظات المراسي نفسها بـ«unverifiable signatures due to lost key».

## تناقض يجب أن يعرفه المالك (إفصاح صريح)

الرقم 11,777 في `forensics/OPERATIONAL_CLAIM_SCOPE.md` هو **لقطة مبكرة**:
السجل استمر في النمو بعد القياس (توثيق conftest: «نما السجل من 11,777 إلى
116,452+ حدثًا — تلوث الدليل الجنائي») وبلغ 116,910 قبل غياب الملف من
الـclone. المحاسبة الكاملة الموثقة أعلاه (116,910) هي المرجع؛ الـ11,777
تبقى الرقم التاريخي لتوقيت التحقيق الأول.

## محتوى ملف المراسي حرفيًا (على d56e24e)

الأمر: `git show d56e24e:data/sovereign_core/ledger.anchors.jsonl`

```
{"anchor_id": "fca2fc72bb8818e0", "batch_start": 0, "batch_end": 13486, "event_count": 13487, "merkle_root": "sha256:5f39a10a3bb02e47128f808bb71d8fdb67a38bcba5346a0f2b6bbfc007b090f3", "reason": "PRE_KEYRING_UNSIGNED_BATCH", "key_id": "b8bf12ab28abfc01", "signature": "eeff46957c24d3a080549d480bdf282e44f1a85fac563a09ba8d23211b802be1", "anchored_at": "2026-10-14T06:49:28Z", "notes": "13487 events with unverifiable signatures due to lost key. Merkle root anchors their exact content. Any future modification of any event in this range will change the root and be detectable."}
{"anchor_id": "22644d499a5a962c", "batch_start": 13487, "batch_end": 104323, "event_count": 90837, "merkle_root": "sha256:03a5a37c4acf80a7df2f0639ab53ae04db29eca31b6f49320f7d10f61c3f0895", "reason": "CONTINUOUS_ANCHORING_BATCH_2", "key_id": "b8bf12ab28abfc01", "signature": "932b0109b25fabd15017246a3c967dea788b26e51fdad4dfb12f4f7697312cbd", "anchored_at": "2026-10-14T10:14:53Z", "notes": "90837 events with unverifiable signatures due to lost key. Merkle root anchors their exact content. Any future modification of any event in this range will change the root and be detectable."}
{"anchor_id": "9a46809d4ecc2f60", "batch_start": 104324, "batch_end": 116451, "event_count": 12128, "merkle_root": "sha256:d667fd97979a2c63514a0317138365549efb3dc867da3c4db16d750069310c38", "reason": "CONTINUOUS_ANCHORING_BATCH_3", "key_id": "b8bf12ab28abfc01", "signature": "5ec1bc7c0999ba10e2d5ccdb38b577dd136f5b2ae41f444dbf4369d187b9b779", "anchored_at": "2026-10-14T10:59:33Z", "notes": "12128 events with unverifiable signatures due to lost key. Merkle root anchors their exact content. Any future modification of any event in this range will change the root and be detectable."}
{"anchor_id": "5767b314b752e152", "batch_start": 116452, "batch_end": 116909, "event_count": 458, "merkle_root": "sha256:bbc6d7481900629566833e21662fcf6f75cede0a2f4947c9cebf6606e0276603", "reason": "R640_COVER_REMAINING_EVENTS", "key_id": "433759679aca9268", "signature": "8cd4eb49bfb30387fcfc536c8e352a78b7eebcde8f980879b7025120003b7f8f", "anchored_at": "2026-10-14T11:48:04Z", "notes": "Anchor covering remaining uncovered events (no modification to past)"}
{"anchor_id": "5767b314b752e152", "batch_start": 116452, "batch_end": 116909, "event_count": 458, "merkle_root": "sha256:bbc6d7481900629566833e21662fcf6f75cede0a2f4947c9cebf6606e0276603", "reason": "R641_ANCHOR_V2_ROOT_SIGNED", "key_id": "433759679aca9268", "signature": "715b7fe375f67017bf0589d7aaec03be8866ff548114529217e7d614d6d73490", "anchored_at": "2026-10-14T11:56:35Z", "notes": "Anchor v2: signature covers merkle_root, batch range, event_count, and key_id (corrected from v1 which only signed batch range)", "sig_format": "v2", "sig_data_v2": "anchor_sig_v2|116452|116909|458|bbc6d7481900629566833e21662fcf6f75cede0a2f4947c9cebf6606e0276603|433759679aca9268"}
{"anchor_id": "4891c7ce824fdc68", "batch_start": 0, "batch_end": 116909, "event_count": 116910, "merkle_root": "sha256:24a8cd6ad69b20f7b19edf09d57aada0c6e938483ee4bf883b36004a981d4a27", "reason": "R643_FULL_COVERAGE_V2", "key_id": "433759679aca9268", "signature": "a2a7ed72c12d43da87a1a421fe38419f0b4fe877b0029506f2d89a7d487f1d20", "anchored_at": "2026-10-14T12:00:32Z", "notes": "Anchor v2 covering ALL events (0 to end) with root-signed signature (covers merkle_root + range + event_count + key_id)", "sig_format": "v2", "sig_data_v2": "anchor_sig_v2|0|116909|116910|24a8cd6ad69b20f7b19edf09d57aada0c6e938483ee4bf883b36004a981d4a27|433759679aca9268"}
```
