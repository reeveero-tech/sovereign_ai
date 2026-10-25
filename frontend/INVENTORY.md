# جرد واجهة سوفره — البند ١.١ (ROADMAP_V4 / R-723)

**التاريخ:** 2026-10-22 — **الطريقة:** تحليل آلي (استهلاك API مباشر / اشتراك أحداث / لا هذا ولا ذاك) لكل ملف JS في الواجهة. مصدر الأدلة: نصوص الملفات نفسها.

## الخلاصة الصادقة

| التصنيف | العدد | المعنى |
|---|---|---|
| تستهلك API مباشرة | 10 | حقيقية — تصل إلى backend فعلًا |
| تعمل بالأحداث (اشتراك/نشر) | 69 | وسيطة — **مصدر أحداثها يحتاج تدقيقًا (بند ١.٢)**: إن كان المصدر إحدى الوحدات الحقيقية فهي حية؛ إن كان مصطنعًا داخليًا فهي زخرفية مقنّعة |
| زخرفية بحتة (لا API ولا أحداث) | 0 | الـ11 الأصلية أزيلت (R-724) |
| ميتة (غير محمّلة) | 0 | — |
| **المجموع** | **79** | |

> هذا الجرد يفسر إحساس المالك «الردود المزروعة»: 69/76 وحدة لا تستهلك
> backend مباشرة — الواجهة تعرض حركة ونشاطًا مصدرها غالبًا داخلي، لا النظام.

### الوحدات الحقيقية (تستهلك API مباشرة) — 8 وحدة

هذه وحدها تلمس النظام الفعلي (fetch/WebSocket إلى نقاط backend).

| الوحدة | التصنيف | الحكم |
|---|---|---|
| `main.js` | حقيقية | حقيقية |
| `live-ai-engine.js` | حقيقية | حقيقية |
| `websocket-runtime.js` | حقيقية | حقيقية |
| `websocket.js` | حقيقية | حقيقية |
| `section-router.js` | أزيلت — R-735 | أزيلت — R-735 | R-727 (١.٣) موجّه أقسام بشريط ثانٍ تبيّن قياسًا أنه أسفل التطبيق (غير مرئي)، ونقل حقل المحادثة من مكانه. الأقسام صارت تبويبات في الشريط الرئيسي (`main.js` `switchTab`) فلا حاجة لموجّه — حارس `test_section_isolation.py` |

| `memory-viewer.js` | حقيقية | حقيقية | R-728 (١.٣): عارض الذاكرة — يستهلك /components/memory ويعرض إحصاءات core/dynamic/store الحية |
| `tools-registry.js` | حقيقية | حقيقية | R-729 (٣.١): سجل الأدوات الحي — يستهلك /tools/list (سجل backend الحقيقي) ويعرض الأدوات المسجلة فعلًا بتحديث دوري |
| `capabilities-panel.js` | حقيقية | حقيقية | R-750 (V5 ١.٢): جرد القدرات الصادق — يستهلك /capabilities ويعرض مستوى دليل كل قدرة من الحالة الحية (لا «مثبت حيًا» من الداخل) |
| `experimental-badges.js` | وسم صدق (١.٥) | حقيقية | R-731 (١.٥): لا بيانات — تُظهر شارة «تجريبي» مرئية بجانب كل عنصر `data-live="experimental"` (غير مربوط في LIVE_BINDINGS.json) |
| `live-health-chart.js` | حقيقية | حقيقية | R-733 (١.٤): يستهلك `/health` كل 10 ثوانٍ — خانة «سلامة المكونات» + رسم حي (المكونات السليمة + زمن الاستجابة المقاس)؛ الفشل فجوة معلنة |

### الوحدات الوسيطة (تعمل بالأحداث) — 80 وحدة أصلية (11 أزيلت R-725 + 1 أزيلت R-729 — 68 متبقية)

> R-725 (١.٢ مرحلة ٢): الناشرون الاصطناعيون (مؤقتات/عشوائية + نشر أحداث — بلا أي
> استخدام فعلي من الكود المتبقي، والوحدات الحقيقية الأربع لا تلمسهم) أزيلت.
> العارضون المتبقون سيهدأون طبيعيًا (لا مصدر لأحداثهم المصطنعة) ويُعاد
> تقييمهم في ١.٣/١.٤ مع الربط الحي.

تشترك أو تنشر أحداثًا. حكمها النهائي يتحدد في البند ١.٢ بتتبع مصدر كل حدث: حقيقي (من الوحدات الأربع) أم مصطنع (self-generated).

| الوحدة | التصنيف | الحكم |
|---|---|---|
| `animations.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `bootstrap.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `core.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `adaptive-effects.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `chat-runtime.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `cinematic-engine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `command-runtime.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `interface-runtime.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `metrics-engine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `neural-memory.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `neural-ui-controller.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `notification-runtime.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-access-control.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-adaptive-scheduler.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-analytics.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-autonomous-preservation.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-backpressure-engine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-bus.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-capability-registry.js` | أزيلت (R-729 — ٣.١) | أزيلت (R-729 — ٣.١) |
| `runtime-causality-graph.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-civilization-registry.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-cognition-engine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-cognitive-memory.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-cognitive-orchestrator.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-consciousness-core.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-context.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-contracts.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-dependency-graph.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-devtools.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-diagnostics.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-domain-router.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-domain-scheduler.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-envelope.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-events.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-evolution-governor.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-execution-domains.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-execution-scheduler.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-fairness-engine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-flow-telemetry.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-health-matrix.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-hooks.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-identity-core.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-init.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-intelligence.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-isolation-zones.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-kernel.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-layer-manager.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-lifecycle.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-message-contracts.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-message-schema.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-meta-intelligence.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-middleware.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-mode-manager.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-orchestrator-ai.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-ownership-domains.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-pacing-policies.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-persistence.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-policy-engine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-power-manager.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-pressure-governor.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-recovery.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-resource-manager.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-security.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-self-awareness.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-session-manager.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-session-policies.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-session-state-machine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-signals.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-sovereign-core.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-state-replicator.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-structural-integrity.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-sync.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-system-state.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-task-registry.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-timeline-engine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `runtime-trace-engine.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `sovereign-orchestrator.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `state-manager.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `system-bridge.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `cognitive-input.js` | وسيطة — تدقيق ١.٢ | وسيطة — تدقيق ١.٢ |
| `live-system-status.js` | حقيقية | حقيقية | R-726 (١.٤/١.٦): لوحة حالة حية بتحديث دوري، لا نصوص مزروعة. R-735: داخل قسم «قرص وأدوات» لا طافية؛ تستهلك /disk/status و/brain/status و/scheduler/status (الصحة لقسم المراقبة والرأس) |
| `voice-output.js` | حقيقية | حقيقية | R-740 (٢.٤): زر تبديل النطق (btn-tts-toggle) + نطق ردود الذكاء عبر POST /tts — فشل صادق (503/502 يُعلنان) ولا صوت مختلق |
| `vision-input.js` | حقيقية | حقيقية | R-741 (٢.٢ — الجولة اللاحقة): رفع الصور في الواجهة — زر btn-vision-upload + مدخل ملف بأنواع الصور المسموحة + وصف عبر POST /vision يسلّم في مسار المحادثة الحقيقي (receiveVisionDescription) — فشل صادق (503/502/413/415/429 تُعلن) ولا وصف مختلق |
| `stt-input.js` | حقيقية | حقيقية | R-742 (٢.٣ — الجولة اللاحقة): زر الميكروفون btn-stt-mic — تسجيل MediaRecorder بنوع مطبَّع (بلا codecs) ضمن عقد الخادم → POST /stt → النص في chat-input للمراجعة (لا إرسال آلي) — فشل صادق (503/502/413/415/429) ولا نص مختلق |

### الوحدات الزخرفية البحتة — 11 وحدة

لا API ولا أحداث — حركة بلا بيانات. **أزيلت بأمر المالك (البند ١.٢ — R-724):**
حُذفت ملفاتها وسوم تحميلها من index.html بعد تحليل آلي أثبت أنه لا يوجد
استدعاء فعلي لها من أي وحدة (المراجع الظاهرة كانت تعليقات وسلاسل نصية
فقط). حارس `test_removed_decorative_modules_stay_removed` يمنع عودتها
بلا أمر المالك. الملفات المحذوفة موثقة في DELETED_LINES_AUDIT.

| الوحدة (أزيلت — R-724) | الحكم |
|---|---|
| `dialogue-engine.js` | أزيلت |
| `legacy-cleanup.js` | أزيلت |
| `neural-animation-engine.js` | أزيلت |
| `render-engine.js` | أزيلت |
| `runtime-access.js` | أزيلت |
| `runtime-cache.js` | أزيلت |
| `runtime-execution-sandboxes.js` | أزيلت |
| `runtime-migration-manager.js` | أزيلت |
| `runtime-queue-intelligence.js` | أزيلت |
| `runtime-scheduler.js` | أزيلت |
| `runtime-unified-registry.js` | أزيلت |
| `runtime-adaptive-scheduler.js` | أزيلت (R-725) |
| `runtime-analytics.js` | أزيلت (R-725) |
| `runtime-bus.js` | أزيلت (R-725) |
| `runtime-domain-router.js` | أزيلت (R-725) |
| `runtime-execution-scheduler.js` | أزيلت (R-725) |
| `runtime-intelligence.js` | أزيلت (R-725) |
| `runtime-kernel.js` | أزيلت (R-725) |
| `runtime-lifecycle.js` | أزيلت (R-725) |
| `runtime-policy-engine.js` | أزيلت (R-725) |
| `runtime-session-policies.js` | أزيلت (R-725) |
| `runtime-signals.js` | أزيلت (R-725) |
| `runtime-capability-registry.js` | أزيلت (R-729 — البند ٣.١: استُبدل بسجل backend حقيقي /tools/list + /tools/invoke + واجهة حية tools-registry.js) |

| الوحدة | التصنيف | الحكم |
|---|---|---|
| `dialogue-engine.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `legacy-cleanup.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `neural-animation-engine.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `render-engine.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `runtime-access.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `runtime-cache.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `runtime-execution-sandboxes.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `runtime-migration-manager.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `runtime-queue-intelligence.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `runtime-scheduler.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |
| `runtime-unified-registry.js` | زخرفية — إزالة مرشحة | زخرفية — إزالة مرشحة |

## القواعد المستقبلية (حراسة هذا الجرد)

- أي وحدة JS جديدة تُضاف للواجهة يجب أن تُدرج هنا في نفس الالتزام (يفرضه
  حارس `tests/test_frontend_inventory.py`) — وحدة غير مجرودة = رفض.
- أي تغيير تصنيف وحدة يتطلب تحديث هذا الملف معه في نفس الالتزام (D-040).
