# R-729 — سجل الأدوات الحقيقي (البند ٣.١ — ROADMAP_V4، بأمر المالك)

**التاريخ:** 2026-10-23 · **الالتزام:** (هذه الدفعة) · **البند:** ٣.١ — منجز
**المرجع:** خارطة الطريق V4 (R-722) — «استبدال runtime-capability-registry.js
الزخرفي بسجل backend حقيقي: كل أداة تُعلن وتُفحص صلاحيتها وتُسجل استدعاءاتها
في السجل السيادي».

## ١. الدافع (ما كنا نعاني منه)

جرد الواجهة (١.١/R-723) أثبت أن `runtime-capability-registry.js` وحدة زخرفية:
«سجل قدرات» مكتوب نصًا داخل الملف، بلا أي استهلاك حقيقي — الوهم نفسه الذي
بُنيت الخارطة الجديدة لقتله. البند ٣.١ يستبدلها بمصدر حقيقة واحد في
backend: سجل أدوات حقيقي تعلن فيه كل قدرة فعلًا، وكل استدعاء يترك أثرًا.

## ٢. المنهج — RED→GREEN (مُشاهَد)

**RED (قبل الإصلاح):** كُتب `tests/test_tools_registry.py` (6 اختبارات) + حارس سابع يمنع عودة الوحدة المزالة (`test_fake_capability_registry_stay_removed`)
وشُوهد الفشل الكامل:

```
FAILED test_tools_list_returns_real_registered_tools
FAILED test_tools_invoke_requires_api_key
FAILED test_tools_invoke_health_snapshot_returns_real_data
FAILED test_every_invoke_leaves_sovereign_ledger_trace
FAILED test_frontend_tools_registry_module_is_real_consumer
5 failed, 1 passed
```

(الاختبار السادس — أداة مجهولة → 404 — مرر بالصدفة: المسار غير موجود أصلًا
فيرد 404؛ بعد الإصلاح يمر بالمعنى المقصود: رفض مسجل لا غياب مسار.)

**GREEN (بعد الإصلاح):** 6/6 + الحارس السابع — والحزمة الكاملة أدناه.

## ٣. ما بُني

### backend
- `backend/tool_registry.py` — `ToolSpec` (اسم/وصف/مدخلات/مخرجات/صلاحية/
  معالج) + `ToolRegistry.register/list_tools/invoke`. `list_tools` تعيد
  البيانات الوصفية فقط — لا معالج ولا سر (المادة ٩).
- `backend/app.py` — استخراج دوال حمولة مشتركة (`_health_payload`،
  `_disk_status_payload`، `_brain_status_payload`، `_memory_stats_payload`،
  `_sovereignty_score_payload`) تخدم النقاط الحية وأدوات السجل معًا — مصدر
  واحد لا نسختين تتباعدان. نقطتان جديدتان:
  - `GET /tools/list` — علنية، الأدوات المسجلة فعلًا.
  - `POST /tools/invoke` — أمر مالك (مفتاح API، نمط `/sovereign/command`):
    401 بلا مفتاح/بمفتاح خاطئ، 404 لأداة غير مسجلة.
- `backend/memory/core.py` — نوع حدث جديد `TOOL_INVOKED`.

### الأثر السيادي (معيار إغلاق البند)
كل استدعاء يمر عبر `ToolRegistry.invoke` يُلحق حدث `tool_invoked` في السجل
السيادي عبر `SovereignCore.append_event` بالحمولة: الأداة/المستدعي/ok/
المدة/**بصمة SHA-256 (16 حرفًا)** للنتيجة — لا نتيجة كاملة ولا سر. الاختبار
`test_every_invoke_leaves_sovereign_ledger_trace` يقرأ ذيل السجل فعليًا
ويُثبت الحدث ويثبت عدم ظهور المفتاح فيه.

**fail-closed بنمط R-635:** إن تعذر توقيع السجل (لا مفتاح توقيع نشط)
يرفض الاستدعاء كاملًا بـ503 — «لا أثر = لا تنفيذ»، لا تنفيذ صامت بلا دليل.
هذا صادق مع بيئة Fly الحالية (لا مفتاح توقيع): `/tools/invoke` سيرفض هناك
بوضوح حتى يُفعَّل مفتاح التوقيع — عيب معلن لا ادعاء نجاح زائف (المادة ٥).

### الواجهة
- `frontend/js/modules/tools-registry.js` (جديد) — يستهلك `/tools/list`
  بتحديث دوري (30s) ويعرض الأدوات في قسم «قرص وأدوات» (`#sovereign-section-tools`).
  «غير متصل» بصدق عند غياب الشبكة.
- `frontend/js/modules/runtime-capability-registry.js` — **أزيلت كاملة**
  (انظر DELETED_LINES_AUDIT.md) + تبديل سطر التحميل في index.html.
- الجرد حُدّث: 7 وحدات حقيقية (منها tools-registry.js) من 76.

## ٤. الأدوات المسجلة (كلها حقيقية — لا وهم)

| الأداة | المصدر الحقيقي |
|---|---|
| `health.snapshot` | نفس منطق `/health` |
| `memory.stats` | نفس منطق `/components/memory` |
| `disk.status` | نفس منطق `/disk/status` |
| `brain.status` | نفس منطق `/brain/status` |
| `sovereignty.score` | نفس منطق `/sovereignty/score` |

الأدوات القادمة (٣.٢ بحث/قراءة، ٣.٣ تنفيذ كود، ٣.٥ وسائط...) تُسجل في
`_register_real_tools` عند بنائها — السجل هو نقطة التسجيل الوحيدة.

## ٥. الحدود المعلنة (المادة ٥)

- `/tools/invoke` على Fly سيرفض (503 fail-closed) حتى يُفعَّل مفتاح توقيع
  السجل هناك — معلن أعلاه، لا ادعاء.
- `/tools/list` تعمل بلا مفتاح (بيانات وصفية علنية بلا أسرار).
- الأدوات الخمس كلها قراءة/تقرير — لا أداة تنفيذ فعلًا بعد (٣.٣ يضيفها).

## ٦. التحقق

- الحزمة الكاملة (الأمر الرسمي `pytest tests/ backend/tests/ -m "not operational"`):
  **825 passed, 1 deselected, 0 failed** — محليًا على بيئة مطابقة (Python 3.11.17 +
  requirements المثبتة). تطابق CI يُثبت بالبوابة بعد الدفع (تطابق ثلاثي عبر
  `verify.sh --full`).
- تحقق حي بعد النشر: `/health` أخضر + `/tools/list` تعيد 5 أدوات من مصدر
  مستقل (يُوثق في CHANGELOG/PROJECT_STATE عند النشر).

## ٧. الأمن

- لا سر في أي مخرج: القائمة بيانات وصفية، والأثر بصمة فقط (المادة ٩).
- الاستدعاء أمر مالك بمفتاح API — نفس حراسة `/sovereign/command`.
- HTML في الواجهة يُهرَّب (escapeHtml) — أسماء الأدوات من backend فقط.

---
*RED evidence:* `forensics/R-729_RED_evidence.txt` (حُذف — الدليل منقول
بالكامل إلى §٢ أعلاه في نفس الالتزام).
