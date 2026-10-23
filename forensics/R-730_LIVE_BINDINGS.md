# R-730: توسيع البند ١.٤ — الربط الحي وحارس المطابقة الآلي (بأمر المالك «توسيع ١.٤»)

**التاريخ:** 2026-10-23 · **البند:** ١.٤ — جزئي متقدم (معيار الإغلاق محقق لكل عنصر بمعرّف في index.html)

## ١. ما كشفه التدقيق (الحقيقة فوق السمعة)

جرد ١.١ صنّف `main.js` «حقيقية» لأنه يستهلك `/status`. هذا صحيح لكنه ناقص: قراءة
الاستجابة الفعلية حقلًا حقلًا أظهرت أن لوحة المراقبة كانت تعرض أرقامًا مزروعة أو خاطئة
رغم أن الاتصال حقيقي:

| العيب | الأثر على ما يراه المالك | الدليل |
|---|---|---|
| `metrics-engine.js` حلقة `requestAnimationFrame` تزيد `cycles` كل إطار وتكتبه في `metric-cycles` | عدّاد «الدورات» يقفز ~60/ثانية ويطغى على `total_cycles` الحقيقي | الكود: `this.metrics.cycles++` داخل الحلقة |
| `sovereign-orchestrator.js` عدّاد إطارات ثانٍ يكتب في `metric-cycles` | كاتب ثالث على نفس الخانة | `render.updateText('metric-cycles', this.cycles)` |
| «الطاقة» من موجة جيبية (`Math.sin(performance.now())`) ومن `Math.random()*100` عند الفشل | رقم يتحرك بلا أي مصدر في backend | لا حقل طاقة في أي نقطة |
| `main.js` يقرأ `orchestrator.system_health` غير الموجود ويسقط إلى `0.75` | «صحة 75%» مزروعة | استجابة `/status` الفعلية بلا هذا الحقل |
| `main.js` يقارن `components[x] === 'healthy'` والقيمة كائن `{status: ...}` | «الذكاء العصبي: متدهور» زورًا دائمًا حتى والنظام سليم | `components.predictive_engine = {status: "healthy", ...}` |
| `main.js` يقرأ `orchestrator.uptime_seconds` والحقل في الجذر | مدة التشغيل 0 دائمًا | `data.uptime_seconds` |
| `simulateMetricsUpdate()` عند فشل الشبكة | أرقام عشوائية تُعرض كأنها حية بلا خادم | الدالة |
| `runSovereignCycle` عند فشل الشبكة: «تم تشغيل دورة سيادية (محاكاة محلية)» بحالة approved | نجاح مُدّعى بلا خادم | النص |
| الدورة لا ترسل مفتاح API و`/orchestrator/cycle` يتطلبه | الزر يفشل 401 دائمًا | `run_orchestrator_cycle` |
| `fetchHistory` بـGET على `/orchestrator/cycle` (POST فقط) | 405 صامت، لا سجل | مسارات backend |
| `handleLocalCommand('status')` يستدعي `updateMetricsFromSystem` غير المعرّفة | ReferenceError | لا تعريف في أي ملف |
| رأس الصفحة: «Neural Link Active» بنبض ثابت و`v2.0.0` | ادعاء اتصال دائم وإصدار خاطئ (الخادم 4.0.0) | index.html |
| `fps \|\| 60` | 60 مزروعة عند غياب المحرك | metrics-engine.js |

## ٢. المنهج: RED→GREEN (مُشاهَد)

كُتبت الخريطة `frontend/LIVE_BINDINGS.json` والحارس `tests/test_live_bindings.py`
(9 اختبارات) قبل أي إصلاح. RED الأول:

```
FAILED test_every_index_element_is_classified
FAILED test_main_js_config_endpoints_exist          ('/components' غير مسجل)
FAILED test_writer_reads_the_declared_field
FAILED test_single_declared_writer_per_element      (metric-cycles ← metrics-engine.js, sovereign-orchestrator.js)
FAILED test_no_simulated_metrics_in_live_paths
FAILED test_unbound_elements_are_honest_and_unwritten
FAILED test_no_hardcoded_live_claims_in_header
7 failed, 2 passed
```

مرّ اختباران من البداية: كل النقاط المعلنة مسجلة فعلًا، وكل حقل معلن موجود في
الاستجابة الحقيقية. هذا متوقع: الخريطة كُتبت من الاستجابات الفعلية، والعيب كان في
قراءة الواجهة لها لا في الخريطة. واكتشف الحارس كتّابًا لم يذكرهم الجرد: `live-ai-engine.js`
و`websocket-runtime.js` وعدّادات الأحرف وصدى الأوامر. فُحص كل منهم يدويًا
فوُجد مشروعًا (إما يستهلك `/chat` أو WebSocket فعلًا، أو قياس محلي، أو صدى لفعل المالك)،
فأُعلنوا في الخريطة. ووجد الحارس `performanceChart`، وهي لوحة رسم لا يرسم فيها أحد.
وصحّح الحارس خطأً في مسودتي للخريطة: `live-system-status.js` يقرأ `enabled` لا `cloud_disk`،
فصُحّحت الخريطة لتطابق الكود.

GREEN: 9/9.

## ٣. ما يثبته الحارس آليًا (معيار إغلاق ١.٤)

1. **التغطية:** كل عنصر بمعرّف في index.html (45) مصنف: مربوط بنقطة / قياس محلي /
   سجل أفعال المالك / تحكم / حاوية / غير مربوط. أي عنصر جديد بلا تصنيف = رفض الدفعة.
2. **النقاط مسجلة:** كل نقطة مربوطة مسار مسجل فعلًا بنفس الطريقة، وكل مسار في
   `CONFIG.API_ENDPOINTS` في main.js مسجل.
3. **الحقول حقيقية:** كل حقل مربوط يُحل فعلًا في استجابة backend الحية (TestClient).
4. **الكاتب يقرأ الحقل المعلن.**
5. **كاتب واحد معلن:** لا وحدة غير معلنة تكتب في عنصر مربوط.
6. **لا محاكاة:** لا `simulateMetricsUpdate`، لا «محاكاة محلية»، لا `|| 0.75`، لا عدّاد إطارات ولا موجة جيبية.
7. **غير المربوط صادق:** يعلن «غير مربوط» ولا يكتبه أي JS.
8. **رأس الصفحة:** لا «Neural Link Active» ولا `v2.0.0` ثابتين.

## ٤. الإصلاحات

- `main.js`: `updateMetrics` تقرأ الشكل الفعلي (`orchestrator.stats.total_cycles`،
  `components.predictive_engine.status`، `uptime_seconds` من الجذر)؛ وعند الفشل تُكتب «غير متصل»
  بدل الأرقام العشوائية. أُضيفت `updateHeaderFromHealth`: حالة الاتصال والإصدار من `/health`،
  والنبض يتبع الحالة الفعلية. الدورة ترسل `CONFIG.API_KEY` وتعرض سبب الفشل. السجل
  من `GET /api/history`. وأُزيل `COMPONENTS: '/components'` غير المسجل وغير المستخدم.
- `metrics-engine.js`: يكتب FPS المحلي فقط وحين يوجد قياس.
- `sovereign-orchestrator.js`: لا يكتب في عدّاد الدورات.
- `index.html`: «جارٍ الاتصال…» و«—» ابتدائيًا، و`id="version-pill"`، و«الطاقة: غير مربوط».

## ٥. المتبقي في ١.٤ (لماذا ليس «منجزًا» — المادة ٥)

- **3 عناصر غير مربوطة بصدق:** «الطاقة» (لا مصدر في backend)، و`performanceChart`
  (ينتظر ٢.٧)، وقسم التطور (القسم ٤ لم يُبنَ).
- **العناصر الديناميكية:** الحارس يغطي العناصر ذات المعرّف في index.html. أما ما
  تنشئه الوحدات الوسيطة الـ68 ديناميكيًا بلا معرّف ثابت فلم يُطابَق بعد. هذا هو الامتداد
  التالي، ويتقاطع مع ١.٥ (وسم «تجريبي»).
- `CONFIG.API_KEY` فارغ افتراضيًا في الواجهة، فزر الدورة سيعرض «مفتاح API غير صحيح»
  بصدق حتى يُدخل المالك مفتاحه. هذا قرار أمني للمالك (موثق منذ R-715).

## ٦. تصويب على R-729 (المادة الأولى)

وثّقت R-729 اسم الحارس `test_fake_capability_registry_stay_removed`، والاسم الفعلي
`test_fake_capability_registry_stays_replaced`. صُحّح في `R-729_TOOL_REGISTRY.md`
و`DELETED_LINES_AUDIT.md` في هذا الالتزام.
