# R-746 — البند ٤.٤: المقارنة بالعالم الخارجي

**التاريخ:** 2026-10-24 — بأمر المالك «ابدأ بالبند ٤.٤، وقارن بمراجع عامة مناسبة».
**معيار الإغلاق:** «تقرير مقارنة دوري موثق».

## المراجع العامة المختارة ولماذا
| المعيار | المرجع | الرابط | لماذا هو مناسب |
|---|---|---|---|
| زمن الرد | Nielsen — Response Times: The 3 Important Limits | https://www.nngroup.com/articles/response-times-3-important-limits/ | حدود إدراك بشري مستقرة منذ عقود (0.1/1/10 ث) — مرجع لأي واجهة تفاعلية |
| زمن المعالجة | Google RAIL | https://web.dev/articles/rail | ميزانية معالجة 50ms لرد مرئي خلال 100ms |
| جودة الرد | GSM8K test (openai/grade-school-math، MIT) | https://github.com/openai/grade-school-math | إجابات عددية مرجعية تسمح بتصحيح آلي حتمي بلا حَكَم بشري |
| تغطية الأدوات | OpenAI — Using tools | https://platform.openai.com/docs/guides/tools | قائمة الأدوات المدمجة المعلنة لمنصة عامة رائدة |
| تغطية الأدوات | Claude — Tool reference | https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-reference | قائمة الأدوات الخادمية المعلنة لمنصة عامة ثانية |

تاريخ الاسترجاع لكل المراجع: 2026-10-24.

## تثبيت عينة GSM8K
- المراجعة `3101c7d5072418e28b9008a6636bde82a006892c`، الملف `grade_school_math/data/test.jsonl` (1319 سطرًا).
- sha256 للملف المنزّل: `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14` — **مطابق** للبصمة المنشورة في `dataset_infos.json` على Hugging Face (تحقق مستقل).
- أول 10 مسائل منسوخة آليًا (لا يدويًا) مع إشعار MIT في مصدر الوحدة. الإجابات: 18, 3, 70000, 540, 20, 64, 260, 160, 45, 460.

## كتالوج التغطية (11 قدرة) والحالة الحية
| القدرة | المرجع | الحالة الحية | السبب |
|---|---|---|---|
| function_calling | OpenAI + Claude | available | سجل الأدوات + /tools/invoke |
| web_search | OpenAI + Claude | built_disabled | web.search مسجلة؛ WEB_TOOLS_ENABLED بيد المالك |
| web_fetch | Claude | built_disabled | web.fetch مسجلة؛ نفس العلم |
| remote_mcp | OpenAI | built_disabled | بوابة MCP (R-738)؛ MCP_SERVERS بيد المالك |
| code_execution | OpenAI (Shell) + Claude | deferred | D-041 |
| image_generation | OpenAI | missing | البند ٣.٥ — قيد التنفيذ في الجولة التالية |
| file_search | OpenAI | missing | — |
| tool_search | OpenAI + Claude | missing | /tools/list سرد لا بحث |
| computer_use | OpenAI | missing | خارج الخارطة |
| skills | OpenAI | missing | — |
| programmatic_tool_calling | OpenAI | missing | — |

**الملخص:** 1 متاحة / 3 مبنية معطلة / 1 مؤجلة / 6 غائبة من 11.

## الفجوات → اقتراحات
الفجوات القابلة للقياس فقط (لقطة الصحة فوق 50ms، زمن العقل فوق 1 ث) تصير `benchmark_gap:*` في ProposalBook (٤.٥) بتوصية investigation، وتنتظر قرار المالك. فجوات التغطية قرارات خارطة لا عيوب — تُوثَّق في `coverage_gaps` ولا تُقترح آليًا.

## البرهان
- RED: 8 مُشاهدة ← GREEN 8/8 ثابت 3 تشغيلات. الدليل الحي في `forensics/R-746_evidence_RED.txt`.
- الحزمة 1016→1024. التطابق الثلاثي ورقم الالتزام في مدخل التسليم.

## الحد المعلن (المادة ٥)
- زمن لقطة الصحة يُقاس داخل العملية — لا زمن الشبكة الكامل (عميل ← Fly ← عميل).
- قياس الجودة الحي **لم يُشغَّل قط**: العقل معطل هنا وعلى الإنتاج حتى قرار المالك؛ مختبر بعقل وهمي فقط.
- العينة صغيرة (n ≤ 10، افتراضي 3): مؤشر انحدار بين الدورات، لا مقارنة إحصائية بالدرجات المنشورة للنماذج.
- قوائم أدوات المنصتين لقطة بتاريخ 2026-10-24؛ تغيّرها لاحقًا يتطلب تحديث الكتالوج بدورة ذرية.

## التسليم
- الالتزام `792d779` — CI أخضر (تشغيل 40099735635) و`verify.sh --full`: **1024/0/0** محليًا = CI = استنساخ نظيف.
