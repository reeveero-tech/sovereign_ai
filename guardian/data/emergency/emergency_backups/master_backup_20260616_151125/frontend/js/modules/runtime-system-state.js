/* ============================================================
   Sovereign AI — runtime-system-state.js
   الإصدار: 9.0.0
   النواة السلوكية الموحدة للـ Runtime
   ============================================================ */

class SovereignRuntimeSystemState {

    constructor() {

        /* =========================================
           CORE STATE
        ========================================= */

        this.state =
            'booting';

        this.previousState =
            null;

        this.health =
            100;

        this.pressure =
            'low';

        this.mode =
            'normal';

        this.behavior =
            'cinematic';

        /* =========================================
           FLAGS
        ========================================= */

        this.flags = {

            throttled:
                false,

            safeMode:
                false,

            queueProtection:
                false,

            cinematicEffects:
                true,

            adaptivePacing:
                true
        };

        /* =========================================
           PREDICTIVE STATE (من عام 2200)
           يتوقع الحالة القادمة قبل حدوثها
        ========================================= */

        this.predictions = {

            nextState: null,
            nextMode: null,
            nextPressure: null,
            confidence: 0,
            horizon: 5000, // 5 seconds prediction window
            historyPatterns: []
        };

        /* =========================================
           QUANTUM STATE TRACING (تتبع كمومي)
           الحالات مترابطة عبر الزمن
        ========================================= */

        this.quantumTraces = [];

        this.maxTraces = 50;

        /* =========================================
           ENTANGLED CONTEXT MEMORY
           ذاكرة مترابطة تربط الأحداث ببعضها
        ========================================= */

        this.entangledMemory = new Map();

        /* =========================================
           SELF-FEEDBACK LOOPS
           حلقات تغذية راجعة ذاتية
        ========================================= */

        this.feedbackLoops = {

            enabled: true,
            correctionFactor: 0,
            lastCorrection: null,
            oscillations: 0
        };

        /* =========================================
           AUTONOMOUS PRESSURE EQUILIBRIUM
           توازن تلقائي للضغط
        ========================================= */

        this.pressureEquilibrium = {

            active: true,
            smoothing: 0.3,
            target: 'low',
            history: []
        };

        /* =========================================
           HISTORY
        ========================================= */

        this.history = [];

        this.maxHistory =
            200;

        /* =========================================
           SUBCONSCIOUS COGNITION (الوعي الخفي)
        ========================================= */

        this.subconscious = {

            anxieties: [],      // ما يقلق النظام
            confidence: 100,
            intuition: null,    // إحساس داخلي بما سيحدث
            lastIntuitionUpdate: null
        };

        /* =========================================
           TIMESTAMPS
        ========================================= */

        this.createdAt =
            Date.now();

        this.lastUpdated =
            Date.now();

        /* =========================================
           PROACTIVE SELF-HEALING SCHEDULER
        ========================================= */

        this.healingScheduler = null;

        console.log(
            '🧠 Runtime System State Initialized (Quantum Edition v2200)'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindKernelSignals();

        this.bindLifecycleSignals();

        this.bindResourceSignals();

        this.bindHealthSignals();

        this.initPredictiveEngine();

        this.initQuantumTracing();

        this.initSubconsciousCognition();

        this.initProactiveHealing();

        this.publishReady();
    }

    /* ========================================================
       PREDICTIVE ENGINE (محرك التنبؤ)
    ======================================================== */

    initPredictiveEngine() {

        // تحليل الأنماط السابقة للتنبؤ بالمستقبل
        this.predictiveInterval = setInterval(() => {

            this.updatePredictions();

        }, 1000);
    }

    updatePredictions() {

        // تحليل التاريخ للتنبؤ بالحالة القادمة
        const recentHistory = this.history.slice(-20);

        if (recentHistory.length < 5) {

            this.predictions.confidence = 0;
            return;
        }

        // كشف الأنماط المتكررة
        const patterns = this.detectPatterns(recentHistory);

        if (patterns.length > 0) {

            const mostLikely = patterns[0];

            this.predictions.nextState = mostLikely.predictedState;
            this.predictions.nextMode = mostLikely.predictedMode;
            this.predictions.nextPressure = mostLikely.predictedPressure;
            this.predictions.confidence = mostLikely.confidence;
            this.predictions.historyPatterns = patterns;
        }

        // نشر التوقعات
        this.publishUpdate('runtime:predictions:updated');
    }

    detectPatterns(history) {

        const patterns = [];

        // كشف تسلسلات الحالات المتكررة
        const stateSequence = history.map(h => h.current).filter(Boolean);

        for (let i = 0; i < stateSequence.length - 2; i++) {

            const current = stateSequence[i];
            const next = stateSequence[i + 1];
            const after = stateSequence[i + 2];

            const confidence = this.calculatePatternConfidence(current, next, after);

            patterns.push({

                predictedState: after,
                predictedMode: 'normal', // سيتم تحسينه لاحقاً
                predictedPressure: 'low',
                confidence,
                basedOn: { current, next }
            });
        }

        return patterns.sort((a, b) => b.confidence - a.confidence);
    }

    calculatePatternConfidence(current, next, predicted) {

        // حساب الثقة بناءً على تكرار النمط
        let occurrences = 0;
        let total = 0;

        for (let i = 0; i < this.history.length - 2; i++) {

            const histCurrent = this.history[i]?.current;
            const histNext = this.history[i + 1]?.current;
            const histAfter = this.history[i + 2]?.current;

            if (histCurrent === current && histNext === next) {

                total++;

                if (histAfter === predicted) {

                    occurrences++;
                }
            }
        }

        return total > 0 ? (occurrences / total) * 100 : 0;
    }

    /* ========================================================
       QUANTUM STATE TRACING (تتبع كمومي للحالات)
    ======================================================== */

    initQuantumTracing() {

        this.quantumTraces = [];
    }

    recordQuantumTrace(state, mode, pressure, health) {

        const trace = {

            state,
            mode,
            pressure,
            health,
            timestamp: Date.now(),
            entanglementId: this.generateEntanglementId()
        };

        this.quantumTraces.unshift(trace);

        if (this.quantumTraces.length > this.maxTraces) {

            this.quantumTraces.pop();
        }

        // ربط الحالة بالذاكرة المترابطة
        this.updateEntangledMemory(trace);

        return trace;
    }

    generateEntanglementId() {

        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    updateEntangledMemory(trace) {

        const key = `${trace.state}:${trace.mode}:${trace.pressure}`;

        if (!this.entangledMemory.has(key)) {

            this.entangledMemory.set(key, []);
        }

        const memory = this.entangledMemory.get(key);
        memory.push(trace);

        // الاحتفاظ بآخر 10 حوادث فقط لكل حالة
        if (memory.length > 10) {

            memory.shift();
        }
    }

    findEntangledStates(targetState, limit = 5) {

        const results = [];

        for (const [key, traces] of this.entangledMemory) {

            if (key.includes(targetState)) {

                results.push({

                    key,
                    traces: traces.slice(-limit),
                    frequency: traces.length
                });
            }
        }

        return results.sort((a, b) => b.frequency - a.frequency);
    }

    /* ========================================================
       SUBCONSCIOUS COGNITION (الوعي الخفي للنظام)
    ======================================================== */

    initSubconsciousCognition() {

        this.subconsciousInterval = setInterval(() => {

            this.updateSubconscious();

        }, 3000);
    }

    updateSubconscious() {

        // تحليل "قلق" النظام بناءً على التاريخ
        const anxieties = [];

        if (this.health < 50 && this.health > 30) {

            anxieties.push('health_declining');
        }

        if (this.pressure === 'high' || this.pressure === 'extreme') {

            anxieties.push('pressure_critical');
        }

        if (this.mode === 'degraded' || this.mode === 'critical') {

            anxieties.push('mode_instability');
        }

        // كشف التذبذب (oscillation detection)
        const recentHealthChanges = this.history.slice(-10).filter(h => h.type === 'health');

        let oscillations = 0;

        for (let i = 1; i < recentHealthChanges.length; i++) {

            const prev = recentHealthChanges[i - 1]?.current;
            const curr = recentHealthChanges[i]?.current;

            if (Math.abs(curr - prev) > 15) {

                oscillations++;
            }
        }

        if (oscillations > 3) {

            anxieties.push('health_oscillation');
            this.feedbackLoops.oscillations = oscillations;
        }

        this.subconscious.anxieties = anxieties;

        // حساب الثقة الخفية
        this.subconscious.confidence = Math.max(0, 100 - (anxieties.length * 15) - (oscillations * 5));

        // الحدس: تخمين ذكي للحالة القادمة
        if (this.predictions.confidence > 60) {

            this.subconscious.intuition = {

                predicted: this.predictions.nextState,
                confidence: this.predictions.confidence,
                basedOn: 'predictive_engine'
            };

        } else if (anxieties.length > 0) {

            this.subconscious.intuition = {

                predicted: 'degraded',
                confidence: 40,
                basedOn: 'anxiety_detection'
            };

        } else {

            this.subconscious.intuition = null;
        }

        this.subconscious.lastIntuitionUpdate = Date.now();

        // نشر التحديث
        this.publishUpdate('runtime:subconscious:updated');
    }

    /* ========================================================
       PROACTIVE SELF-HEALING (الشفاء الذاتي الاستباقي)
    ======================================================== */

    initProactiveHealing() {

        this.healingScheduler = setInterval(() => {

            this.attemptProactiveHealing();

        }, 10000);
    }

    attemptProactiveHealing() {

        let healed = false;

        // 1. علاج القلق: إذا كان النظام قلقاً ولكنه ليس في حالة حرجة
        if (this.subconscious.anxieties.length > 0 && this.health > 40) {

            if (this.subconscious.anxieties.includes('health_declining')) {

                // تعزيز الصحة تدريجياً
                this.setHealth(Math.min(100, this.health + 5), 'proactive-healing');
                healed = true;
            }

            if (this.subconscious.anxieties.includes('pressure_critical') && this.pressure !== 'low') {

                // خفض الضغط تدريجياً
                if (this.pressure === 'extreme') this.setPressure('high', 'proactive-healing');
                else if (this.pressure === 'high') this.setPressure('moderate', 'proactive-healing');
                else if (this.pressure === 'moderate') this.setPressure('low', 'proactive-healing');
                healed = true;
            }
        }

        // 2. علاج التذبذب
        if (this.feedbackLoops.oscillations > 3) {

            // تطبيق عامل تصحيح
            this.feedbackLoops.correctionFactor = Math.min(0.5, this.feedbackLoops.correctionFactor + 0.05);
            this.feedbackLoops.lastCorrection = Date.now();
            healed = true;
        }

        // 3. استعادة الثقة
        if (this.subconscious.confidence < 50 && this.health > 60) {

            this.subconscious.confidence = Math.min(100, this.subconscious.confidence + 10);
            healed = true;
        }

        if (healed) {

            this.publishUpdate('runtime:healing:performed');
            console.log('🔄 Proactive self-healing performed');
        }
    }

    /* ========================================================
       AUTONOMOUS PRESSURE EQUILIBRIUM
    ======================================================== */

    applyPressureEquilibrium(newPressure) {

        if (!this.pressureEquilibrium.active) {

            return newPressure;
        }

        const pressureValues = {

            low: 0,
            moderate: 1,
            high: 2,
            extreme: 3
        };

        const reverseValues = ['low', 'moderate', 'high', 'extreme'];

        const currentValue = pressureValues[this.pressure];
        const targetValue = pressureValues[newPressure];
        const smoothing = this.pressureEquilibrium.smoothing;

        const smoothed = Math.round(
            currentValue + (targetValue - currentValue) * smoothing
        );

        const result = reverseValues[Math.max(0, Math.min(3, smoothed))];

        // تسجيل التاريخ
        this.pressureEquilibrium.history.push({

            from: this.pressure,
            to: newPressure,
            smoothed: result,
            timestamp: Date.now()
        });

        if (this.pressureEquilibrium.history.length > 50) {

            this.pressureEquilibrium.history.shift();
        }

        return result;
    }

    /* ========================================================
       STATE UPDATE (محسن مع Quantum Tracing)
    ======================================================== */

    setState(

        newState,

        reason = 'unknown'

    ) {

        if (
            this.state === newState
        ) {

            return;
        }

        this.previousState =
            this.state;

        this.state =
            newState;

        this.lastUpdated =
            Date.now();

        // تسجيل التتبع الكمومي
        this.recordQuantumTrace(

            this.state,
            this.mode,
            this.pressure,
            this.health
        );

        this.recordHistory({

            type:
                'state',

            previous:
                this.previousState,

            current:
                this.state,

            reason
        });

        this.syncBodyState();

        this.publishUpdate(
            'runtime:state:changed'
        );

        // تحديث الحدس بعد تغيير الحالة
        this.updateSubconscious();
    }

    /* ========================================================
       MODE (محسن مع Feedback Loops)
    ======================================================== */

    setMode(

        mode,

        reason = 'runtime'

    ) {

        if (
            this.mode === mode
        ) {

            return;
        }

        const previous =
            this.mode;

        this.mode =
            mode;

        this.lastUpdated =
            Date.now();

        this.recordQuantumTrace(

            this.state,
            this.mode,
            this.pressure,
            this.health
        );

        this.recordHistory({

            type:
                'mode',

            previous,

            current:
                mode,

            reason
        });

        this.syncBodyState();

        this.publishUpdate(
            'runtime:mode:changed'
        );

        // تقليل التذبذب إذا كان موجوداً
        if (this.feedbackLoops.oscillations > 0) {

            this.feedbackLoops.oscillations = Math.max(0, this.feedbackLoops.oscillations - 1);
        }
    }

    /* ========================================================
       HEALTH (محسن مع Self-Healing)
    ======================================================== */

    setHealth(

        value,

        source = 'system'

    ) {

        const newHealth =
            Math.max(
                0,
                Math.min(
                    100,
                    value
                )
            );

        // تطبيق عامل التصحيح من حلقات التغذية الراجعة
        let correctedHealth = newHealth;

        if (this.feedbackLoops.correctionFactor > 0) {

            const correction = (newHealth - this.health) * this.feedbackLoops.correctionFactor;
            correctedHealth = Math.max(0, Math.min(100, newHealth + correction));
        }

        this.health = correctedHealth;

        this.lastUpdated =
            Date.now();

        this.evaluateDerivedState();

        this.recordQuantumTrace(

            this.state,
            this.mode,
            this.pressure,
            this.health
        );

        this.recordHistory({

            type:
                'health',

            current:
                this.health,

            source
        });

        this.syncBodyState();

        this.publishUpdate(
            'runtime:health:changed'
        );
    }

    /* ========================================================
       PRESSURE (محسن مع Autonomous Equilibrium)
    ======================================================== */

    setPressure(

        level,

        source = 'runtime'

    ) {

        const allowed = [

            'low',
            'moderate',
            'high',
            'extreme'
        ];

        if (
            !allowed.includes(
                level
            )
        ) {

            return;
        }

        // تطبيق التوازن التلقائي للضغط
        const equilibrated = this.applyPressureEquilibrium(level);

        this.pressure =
            equilibrated;

        this.lastUpdated =
            Date.now();

        this.evaluatePressurePolicies();

        this.recordQuantumTrace(

            this.state,
            this.mode,
            this.pressure,
            this.health
        );

        this.recordHistory({

            type:
                'pressure',

            current:
                level,

            source
        });

        this.syncBodyState();

        this.publishUpdate(
            'runtime:pressure:changed'
        );
    }

    /* ========================================================
       FLAGS
    ======================================================== */

    setFlag(

        key,

        value

    ) {

        if (
            !(key in this.flags)
        ) {

            return;
        }

        this.flags[key] =
            value;

        this.lastUpdated =
            Date.now();

        this.recordHistory({

            type:
                'flag',

            key,

            value
        });

        this.syncBodyState();

        this.publishUpdate(
            'runtime:flag:changed'
        );
    }

    /* ========================================================
       DERIVED STATE
    ======================================================== */

    evaluateDerivedState() {

        /* =========================================
           CRITICAL
        ========================================= */

        if (
            this.health <= 30
        ) {

            this.setMode(
                'critical',
                'health'
            );

            this.setState(
                'degraded',
                'health'
            );

            this.flags.safeMode =
                true;

            this.flags.throttled =
                true;

            this.flags.queueProtection =
                true;

            return;
        }

        /* =========================================
           DEGRADED
        ========================================= */

        if (
            this.health <= 60
        ) {

            this.setMode(
                'degraded',
                'health'
            );

            this.flags.throttled =
                true;

            return;
        }

        /* =========================================
           STABLE
        ========================================= */

        this.setMode(
            'normal',
            'health'
        );

        this.flags.safeMode =
            false;

        this.flags.throttled =
            false;

        this.flags.queueProtection =
            false;
    }

    /* ========================================================
       PRESSURE POLICIES
    ======================================================== */

    evaluatePressurePolicies() {

        switch (
            this.pressure
        ) {

            case 'extreme':

                this.flags.throttled =
                    true;

                this.flags.cinematicEffects =
                    false;

                this.flags.queueProtection =
                    true;

                this.setMode(
                    'critical',
                    'pressure'
                );

                break;

            case 'high':

                this.flags.throttled =
                    true;

                this.flags.cinematicEffects =
                    false;

                this.setMode(
                    'degraded',
                    'pressure'
                );

                break;

            case 'moderate':

                this.flags.throttled =
                    false;

                this.flags.cinematicEffects =
                    true;

                this.setMode(
                    'elevated',
                    'pressure'
                );

                break;

            default:

                this.flags.cinematicEffects =
                    true;

                this.setMode(
                    'normal',
                    'pressure'
                );
        }
    }

    /* ========================================================
       HISTORY
    ======================================================== */

    recordHistory(entry = {}) {

        this.history.push({

            ...entry,

            timestamp:
                Date.now()
        });

        if (
            this.history.length >
            this.maxHistory
        ) {

            this.history.shift();
        }
    }

    /* ========================================================
       MULTI-DIMENSIONAL INTERFACE SYNC
    ======================================================== */

    syncBodyState() {

        if (typeof document === 'undefined') return;

        document.body.dataset.runtimeState =
            this.state;

        document.body.dataset.runtimeMode =
            this.mode;

        document.body.dataset.runtimePressure =
            this.pressure;

        document.body.dataset.runtimeHealth =
            this.health;

        document.body.dataset.runtimeBehavior =
            this.behavior;

        document.body.dataset.runtimeConfidence =
            this.subconscious.confidence;

        if (this.predictions.confidence > 50) {

            document.body.dataset.runtimePrediction =
                this.predictions.nextState || 'unknown';
        }

        /* =========================================
           FLAGS
        ========================================= */

        Object.entries(
            this.flags
        ).forEach(

            ([key, value]) => {

                document.body.dataset[
                    key
                ] = value;
            }
        );
    }

    /* ========================================================
       KERNEL SIGNALS
    ======================================================== */

    bindKernelSignals() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) {

            return;
        }

        if (typeof events.on === 'function') {

            events.on(

                'kernel:degraded',

                ({ health }) => {

                    this.setHealth(
                        health,
                        'kernel'
                    );
                }
            );

            events.on(

                'kernel:stable',

                ({ health }) => {

                    this.setHealth(
                        health,
                        'kernel'
                    );

                    this.setState(
                        'active',
                        'kernel'
                    );
                }
            );
        }
    }

    /* ========================================================
       LIFECYCLE
    ======================================================== */

    bindLifecycleSignals() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) {

            return;
        }

        if (typeof events.on === 'function') {

            events.on(

                'lifecycle:changed',

                ({ current }) => {

                    this.setState(
                        current,
                        'lifecycle'
                    );
                }
            );
        }
    }

    /* ========================================================
       RESOURCES
    ======================================================== */

    bindResourceSignals() {

        // استخدام polling آمن
        this._resourcePolling = setInterval(() => {

            this.evaluateResources();

        }, 4000);
    }

    /* ========================================================
       HEALTH SIGNALS
    ======================================================== */

    bindHealthSignals() {

        this._healthPolling = setInterval(() => {

            const matrix =
                window.SOVEREIGN_HEALTH
                    ?.getStatus?.();

            if (
                matrix?.globalHealth
            ) {

                this.setHealth(
                    matrix.globalHealth,
                    'health-matrix'
                );
            }
        }, 5000);
    }

    /* ========================================================
       RESOURCE EVALUATION
    ======================================================== */

    evaluateResources() {

        const resources =
            window.SOVEREIGN_RESOURCES
                ?.getStatus?.();

        if (!resources) {

            return;
        }

        const pressure =
            resources.pressure || 0;

        if (
            pressure >= 70
        ) {

            this.setPressure(
                'extreme',
                'resources'
            );

            return;
        }

        if (
            pressure >= 40
        ) {

            this.setPressure(
                'high',
                'resources'
            );

            return;
        }

        if (
            pressure >= 20
        ) {

            this.setPressure(
                'moderate',
                'resources'
            );

            return;
        }

        this.setPressure(
            'low',
            'resources'
        );
    }

    /* ========================================================
       PUBLISH
    ======================================================== */

    publishUpdate(channel) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware(

                channel,

                {

                    state:
                        this.state,

                    mode:
                        this.mode,

                    pressure:
                        this.pressure,

                    health:
                        this.health,

                    flags:
                        this.flags,

                    predictions: {
                        nextState: this.predictions.nextState,
                        confidence: this.predictions.confidence
                    },

                    subconscious: {
                        anxieties: this.subconscious.anxieties,
                        confidence: this.subconscious.confidence,
                        intuition: this.subconscious.intuition
                    },

                    timestamp:
                        Date.now()
                }
            );
        }
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware(

                'runtime-system-state:ready',

                {

                    state:
                        this.state,

                    quantumEnabled: true,
                    predictiveEnabled: true,
                    subconsciousEnabled: true,
                    selfHealingEnabled: true,

                    timestamp:
                        Date.now()
                }
            );
        }
    }

    /* ========================================================
       STATUS (محسن بالكامل)
    ======================================================== */

    getStatus() {

        return {

            state:
                this.state,

            previousState:
                this.previousState,

            mode:
                this.mode,

            pressure:
                this.pressure,

            health:
                this.health,

            behavior:
                this.behavior,

            flags:
                this.flags,

            history:
                this.history.length,

            updated:
                this.lastUpdated,

            // Quantum & Predictive
            predictions: {
                nextState: this.predictions.nextState,
                nextMode: this.predictions.nextMode,
                nextPressure: this.predictions.nextPressure,
                confidence: this.predictions.confidence
            },

            quantumTraces: this.quantumTraces.length,
            entangledStates: this.entangledMemory.size,

            subconscious: {
                anxieties: this.subconscious.anxieties,
                confidence: this.subconscious.confidence,
                intuition: this.subconscious.intuition
            },

            healing: {
                correctionFactor: this.feedbackLoops.correctionFactor,
                oscillations: this.feedbackLoops.oscillations,
                lastCorrection: this.feedbackLoops.lastCorrection
            },

            pressureEquilibrium: {
                active: this.pressureEquilibrium.active,
                smoothing: this.pressureEquilibrium.smoothing,
                historySize: this.pressureEquilibrium.history.length
            }
        };
    }

    /* ========================================================
       CLEANUP (تدمير آمن)
    ======================================================== */

    destroy() {

        if (this._resourcePolling) {
            clearInterval(this._resourcePolling);
            this._resourcePolling = null;
        }

        if (this._healthPolling) {
            clearInterval(this._healthPolling);
            this._healthPolling = null;
        }

        if (this.predictiveInterval) {
            clearInterval(this.predictiveInterval);
            this.predictiveInterval = null;
        }

        if (this.subconsciousInterval) {
            clearInterval(this.subconsciousInterval);
            this.subconsciousInterval = null;
        }

        if (this.healingScheduler) {
            clearInterval(this.healingScheduler);
            this.healingScheduler = null;
        }

        this.publishUpdate('runtime:system:destroyed');
        console.log('🧠 Runtime System State Destroyed (Quantum Edition)');
    }

    /* ========================================================
       GET QUANTUM TRACES (للمراقبة المتقدمة)
    ======================================================== */

    getQuantumTraces(limit = 20) {

        return this.quantumTraces.slice(0, limit);
    }

    /* ========================================================
       GET ENTANGLED MEMORY (لتحليل العلاقات)
    ======================================================== */

    getEntangledMemory(state = null) {

        if (state) {

            return this.findEntangledStates(state);
        }

        const result = {};

        for (const [key, traces] of this.entangledMemory) {

            result[key] = traces.length;
        }

        return result;
    }

    /* ========================================================
       RESET (إعادة تعيين كاملة مع الاحتفاظ بالتطور)
    ======================================================== */

    reset(keepEvolution = true) {

        const oldState = this.state;

        this.state = 'booting';
        this.previousState = oldState;
        this.health = 100;
        this.pressure = 'low';
        this.mode = 'normal';

        this.flags = {

            throttled: false,
            safeMode: false,
            queueProtection: false,
            cinematicEffects: true,
            adaptivePacing: true
        };

        this.lastUpdated = Date.now();

        if (!keepEvolution) {

            this.quantumTraces = [];
            this.entangledMemory.clear();
            this.history = [];
            this.subconscious.anxieties = [];
            this.subconscious.confidence = 100;
            this.feedbackLoops.correctionFactor = 0;
            this.feedbackLoops.oscillations = 0;
            this.pressureEquilibrium.history = [];
        }

        this.syncBodyState();
        this.publishUpdate('runtime:system:reset');

        console.log('🔄 Runtime System State Reset');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeSystemState =
    new SovereignRuntimeSystemState();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_SYSTEM_STATE =
    sovereignRuntimeSystemState;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register(

        'system-state',

        sovereignRuntimeSystemState
    );
}

/* =========================================
   Quantum API للمطورين (واجهة كمومية)
========================================= */

window.SovereignQuantum = {

    getState: () => sovereignRuntimeSystemState.getStatus(),

    getTraces: (limit) => sovereignRuntimeSystemState.getQuantumTraces(limit),

    getEntangledMemory: (state) => sovereignRuntimeSystemState.getEntangledMemory(state),

    getPredictions: () => sovereignRuntimeSystemState.predictions,

    getSubconscious: () => sovereignRuntimeSystemState.subconscious,

    reset: (keepEvolution) => sovereignRuntimeSystemState.reset(keepEvolution)
};
