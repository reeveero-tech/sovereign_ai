# R-745 — البند ٤.٥: التحسين بموافقة

**التاريخ:** 2026-10-24 — بأمر المالك «أبدأ بالبند ٤.٥».
**القاعدة:** RED→GREEN حقيقي مُشاهد (المادة ٢) + دفعة ذرية واحدة (المادة ٤).
**معيار الإغلاق:** «اقتراح → موافقة مالك → التزام ذري» — «لا تطوير ذاتي غير مقيّد بموافقة المالك».

## المسار
1. **اقتراح (آلي):** كل دورة `defects.scan` → `ProposalBook.ingest(report)` → اقتراح لكل عيب مفتوح بدليله الحرفي.
2. **موافقة (المالك وحده):** `POST /tools/invoke` → `proposals.decide` بمفتاح API → أثر tool_invoked موقّع → تطبيق.
3. **التزام ذري (خارج النظام):** `GET /proposals/{id}/file` → ملف توصية يُنفَّذ بالدورة الذرية المعتادة → `proposals.decide decision=implemented commit=<SHA>`.

## ما بُني
| الملف | الدور |
|---|---|
| `backend/improvement_proposals.py` | `ProposalBook`: ingest / prepare / apply_prepared / decide / list / render_markdown؛ `OWNER_SUPPRESSIONS` |
| `backend/tool_registry.py` | `ToolSpec.apply` (إلحاق): تطبيق بعد نجاح الأثر الموقّع فقط |
| `backend/app.py` | ingest بعد كل دورة فحص؛ أداة `proposals.decide` (handler=prepare، apply=apply_prepared)؛ `GET /proposals`، `GET /proposals/{id}/file` |
| `tests/test_improvement_proposals.py` | 9 حراس |

## آلة الحالات
`proposed → approved | rejected` ؛ `approved → implemented | rejected` ؛ `suppressed` و`rejected` و`implemented` نهائية. `implemented` يتطلب commit بصيغة 7-40 hex. المرفوض لا يُعاد اقتراحه حتى لو عاد العيب.

## احترام قرارات المالك (المادة ٦)
`supervisor_heartbeat_missing` → `suppressed` بسبب قرار ٤.٧ (الحارس كخدمة: مغلق — خارج النطاق). النظام لا يقترح ما أغلقه المالك، ويعلن سبب الحجب.

## الثغرة المكتشفة والمسدودة
`ToolRegistry.invoke` (R-729) ينفّذ `handler` ثم يكتب الأثر. لأدوات القراءة لا ضرر. لأداة تغيّر حالة: إن رفض السجل التوقيع (R-635) يرتفع RuntimeError **بعد** تطبيق القرار — قرار بلا أثر، خرق «لا أثر = لا تنفيذ». RED مُشاهد بربط مباشر (`test_decision_not_applied_when_ledger_cannot_sign`). الحل إضافي: `ToolSpec.apply` — handler يحضّر (`prepare` بلا تغيير حالة) والتطبيق بعد `append_event` الناجح فقط؛ تغيّر الحالة بين التحضير والتطبيق يُرفض؛ فشل التطبيق يُوثّق بأثر ثانٍ `phase=apply`. أدوات القراءة القائمة (apply=None) لم يتغير سلوكها (حارس test_tools_registry أخضر).

## لا تطوير ذاتي
الوحدة لا تحتوي `open(` ولا `subprocess` ولا `os.system` ولا `exec(`/`eval(` ولا `shutil` ولا أوامر git — حارس ثابت يقرأ مصدرها.

## البرهان
- RED: 8 قبل التنفيذ (2 فشل + 6 أخطاء استيراد) + 1 للثغرة بعد الربط المباشر ← GREEN 9/9 ثابت 3 تشغيلات.
- دليل حي (`forensics/R-745_evidence_RED.txt`): نظام سليم → اقتراح محجوب بقرار ٤.٧؛ مكوّن معطوب محاكى → `P-23997dad` code_fix proposed؛ مفتاح خاطئ 401؛ implemented قبل الموافقة مرفوض؛ موافقة بأثر موقّع؛ ملف التوصية text/markdown؛ رفض توقيع محاكى → الحالة بقيت approved.
- الحزمة 1007→1016. التطابق الثلاثي ورقم الالتزام في مدخل التسليم.

## الحد المعلن (المادة ٥)
- حالة في الذاكرة فقط (المادة ٧ — لا كتابة تحت data/): تضيع القرارات عند إعادة التشغيل؛ الأثر الموقّع يبقى، والعيوب المفتوحة تُقترح من جديد.
- `implemented` يسجّل رقم الالتزام كما يعلنه المالك — لا تحقق من GitHub داخل الإنتاج.
- مصدر الاقتراحات اليوم ٤.٣ وحده؛ ٤.٤ (المقارنة الخارجية) لم يبدأ.
- لا واجهة أمامية للاقتراحات بعد — القراءة عبر API.

## التسليم
- الالتزام `b7830d6` — CI أخضر (تشغيل 40096223924) و`verify.sh --full`: **1016/0/0** محليًا = CI = استنساخ نظيف.
