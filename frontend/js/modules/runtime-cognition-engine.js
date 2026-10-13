/* ============================================================
   Sovereign AI — runtime-cognition-engine.js
   الإصدار: 10.0.0
   المحرك الإدراكي السيادي للـ Runtime
   العقل المركزي الذي يتوقع, يتعلم, ويتكيف مسبقاً
   ============================================================ */

class SovereignRuntimeCognitionEngine {

    constructor() {

        /* =========================================
           COGNITIVE STATE
        ========================================= */

        this.state = 'observing';  // observing, learning, predicting, acting, recovering
        this.lastPrediction = null;
        this.lastAnomaly = null;
        this.cognitiveConfidence = 100;  // ثقة العقل في قراراته

        /* =========================================
           PATTERN MEMORY (ذاكرة الأنماط المتقدمة)
        ========================================= */

        this.patterns = [];
        this.maxPatterns = 500;
        this.patternLibrary = new Map();  // أنماط متكررة مع ثقتها
        this.sequenceMemory = [];         // تتبع التسلسلات الزمنية للسلوك

        /* =========================================
           PREDICTIONS (تنبؤات كمية)
        ========================================= */

        this.predictions = [];
        this.maxPredictions = 200;
        this.activePredictions = new Map();  // تنبؤات نشطة لم تتحقق بعد
        this.predictionAccuracy = 100;        // دقة التنبؤات السابقة

        /* =========================================
           ANOMALIES (شذوذات مصنفة)
        ========================================= */

        this.anomalies = [];
        this.maxAnomalies = 200;
        this.anomalyLibrary = new Map();      // أنواع الشذوذ المتكررة

        /* =========================================
           BEHAVIORAL FORECAST (التنبؤ السلوكي)
        ========================================= */

        this.forecast = {
            stabilityIn30s: 100,
            stabilityIn60s: 100,
            pressureTrend: 'stable',     // rising, falling, stable
            healthTrend: 'stable',
            confidence: 0,
            lastUpdate: null
        };

        /* =========================================
           ADAPTIVE RECOVERY (استراتيجيات التعافي)
        ========================================= */

        this.recoveryStrategies = {
            active: null,
            history: [],
            successRate: 100
        };

        /* =========================================
           METRICS (محسن)
        ========================================= */

        this.metrics = {
            predictions: 0,
            anomalies: 0,
            recoveries: 0,
            preventiveActions: 0,
            stabilizations: 0,
            patternsLearned: 0,
            accuratePredictions: 0,
            falsePredictions: 0,
            cognitiveDecisions: 0
        };

        console.log('🧠 Runtime Cognition Engine Initialized (Sovereign Cognitive Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindTelemetry();
        this.bindSystemState();
        this.bindGovernor();
        this.startCognitiveLoop();
        this.startForecastUpdater();
        this.startPatternLearner();
        this.publishReady();
    }

    /* ========================================================
       TELEMETRY (محسن)
    ======================================================== */

    bindTelemetry() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('telemetry:event', payload => {
            this.learnFromEvent(payload);
        });

        bus.subscribe('telemetry:snapshot', payload => {
            this.analyzeSnapshot(payload);
        });

        bus.subscribe('runtime:mode:transition', payload => {
            this.observeModeTransition(payload);
            this.updateBehavioralSequence(payload);
        });
    }

    /* ========================================================
       SYSTEM STATE
    ======================================================== */

    bindSystemState() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:state:changed', payload => {
            this.updateCognitiveState(payload);
        });

        bus.subscribe('runtime:pressure:changed', payload => {
            this.updatePressureForecast(payload);
        });

        bus.subscribe('runtime:health:changed', payload => {
            this.updateHealthForecast(payload);
        });
    }

    /* ========================================================
       GOVERNOR
    ======================================================== */

    bindGovernor() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:governor:decision', payload => {
            this.evaluateGovernorDecision(payload);
        });
    }

    /* ========================================================
       COGNITIVE LOOP (الحلقة المعرفية الدورية)
    ======================================================== */

    startCognitiveLoop() {

        this._cognitiveInterval = setInterval(() => {

            this.evaluateRuntime();

        }, 3000); // كل 3 ثوانٍ
    }

    /* ========================================================
       FORECAST UPDATER (تحديث التنبؤات المستمر)
    ======================================================== */

    startForecastUpdater() {

        this._forecastInterval = setInterval(() => {

            this.updateBehavioralForecast();

        }, 5000);
    }

    updateBehavioralForecast() {

        const system = window.SOVEREIGN_SYSTEM_STATE?.getStatus?.();
        const telemetry = window.SOVEREIGN_FLOW_TELEMETRY?.getStatus?.();
        const fairness = window.SOVEREIGN_FAIRNESS_ENGINE?.getStatus?.();

        if (!system || !telemetry || !fairness) return;

        // تحليل التوجهات
        const recentStability = telemetry.stability || 100;
        const recentHealth = system.health || 100;
        const recentPressure = system.pressure;

        // توقع الاستقرار بعد 30 ثانية
        let stability30s = recentStability;
        let stability60s = recentStability;

        // اتجاه الضغط
        let pressureTrend = 'stable';
        if (recentPressure === 'high') pressureTrend = 'rising';
        else if (recentPressure === 'extreme') pressureTrend = 'rising';
        else if (recentPressure === 'low' && this.forecast.pressureTrend === 'rising') pressureTrend = 'falling';

        // اتجاه الصحة
        let healthTrend = 'stable';
        if (recentHealth < 50) healthTrend = 'falling';
        else if (recentHealth > 80 && this.forecast.healthTrend === 'falling') healthTrend = 'rising';

        // حساب التوقعات بناءً على الاتجاهات
        if (pressureTrend === 'rising') {
            stability30s -= 15;
            stability60s -= 30;
        } else if (pressureTrend === 'falling') {
            stability30s += 10;
            stability60s += 15;
        }

        if (healthTrend === 'falling') {
            stability30s -= 10;
            stability60s -= 20;
        }

        // ثقة التنبؤ
        const confidence = Math.min(100, 70 + (this.predictionAccuracy / 2));

        this.forecast = {
            stabilityIn30s: Math.max(0, Math.min(100, stability30s)),
            stabilityIn60s: Math.max(0, Math.min(100, stability60s)),
            pressureTrend,
            healthTrend,
            confidence,
            lastUpdate: Date.now()
        };

        // إذا كان التدهور متوقعاً، قم بإجراء استباقي
        if (this.forecast.stabilityIn30s < 40 && this.state !== 'acting') {
            this.triggerPreventiveAction('forecasted-degradation', { stability30s: this.forecast.stabilityIn30s });
        }

        this.publishCognitiveUpdate('forecast', this.forecast);
    }

    /* ========================================================
       PATTERN LEARNER (تعلم الأنماط المتقدم)
    ======================================================== */

    startPatternLearner() {

        this._patternInterval = setInterval(() => {

            this.learnBehavioralPatterns();

        }, 30000); // كل 30 ثانية
    }

    learnBehavioralPatterns() {

        if (this.sequenceMemory.length < 10) return;

        // كشف التسلسلات المتكررة
        const sequences = this.extractSequences(this.sequenceMemory, 3); // طول 3

        for (const [seq, count] of sequences) {
            if (count >= 2) {
                const patternKey = seq.join('→');
                const existing = this.patternLibrary.get(patternKey) || { count: 0, confidence: 0 };
                existing.count = count;
                existing.confidence = Math.min(100, (count / 5) * 100);
                existing.lastSeen = Date.now();

                this.patternLibrary.set(patternKey, existing);
                this.metrics.patternsLearned++;
            }
        }

        // تنظيف الأنماط القديمة (أكثر من ساعة)
        const oneHourAgo = Date.now() - 3600000;
        for (const [key, pattern] of this.patternLibrary) {
            if (pattern.lastSeen < oneHourAgo && pattern.count < 3) {
                this.patternLibrary.delete(key);
            }
        }
    }

    extractSequences(array, length) {

        const sequences = new Map();

        for (let i = 0; i <= array.length - length; i++) {
            const seq = array.slice(i, i + length);
            const key = JSON.stringify(seq);
            sequences.set(key, (sequences.get(key) || 0) + 1);
        }

        return sequences;
    }

    updateBehavioralSequence(payload) {

        this.sequenceMemory.push({
            type: 'mode_transition',
            from: payload.previous,
            to: payload.current,
            timestamp: Date.now()
        });

        if (this.sequenceMemory.length > 200) {
            this.sequenceMemory.shift();
        }
    }

    /* ========================================================
       COGNITIVE UPDATE
    ======================================================== */

    updateCognitiveState(payload) {

        const newState = payload.state;

        switch (newState) {
            case 'booting':
                this.state = 'observing';
                break;
            case 'active':
                this.state = 'learning';
                break;
            case 'degraded':
                this.state = 'predicting';
                break;
            case 'recovery':
                this.state = 'recovering';
                break;
            default:
                this.state = 'observing';
        }

        this.publishCognitiveUpdate('state', { cognitiveState: this.state, runtimeState: newState });
    }

    updatePressureForecast(payload) {

        const pressure = payload.pressure;

        if (pressure === 'extreme') {

            this.predictRisk('pressure-cascade', 'high', {
                currentPressure: pressure,
                expectedImpact: 'stability_drop'
            });

            // إجراء استباقي قبل فوات الأوان
            if (this.forecast.stabilityIn30s > 30) {
                this.triggerPreventiveAction('pressure-escalating', { pressure });
            }
        }
    }

    updateHealthForecast(payload) {

        const health = payload.health;

        if (health < 40 && this.forecast.healthTrend === 'falling') {

            this.predictRisk('health-decline', 'critical', {
                currentHealth: health,
                expectedStability: this.forecast.stabilityIn30s
            });
        }
    }

    evaluateGovernorDecision(payload) {

        const decision = payload.mode;

        // تتبع دقة التنبؤات
        if (this.activePredictions.has('degradation-risk')) {
            const prediction = this.activePredictions.get('degradation-risk');
            if (decision === 'degraded' || decision === 'critical') {
                this.metrics.accuratePredictions++;
                this.predictionAccuracy = Math.min(100, this.predictionAccuracy + 2);
            } else {
                this.metrics.falsePredictions++;
                this.predictionAccuracy = Math.max(0, this.predictionAccuracy - 1);
            }
            this.activePredictions.delete('degradation-risk');
        }

        this.metrics.cognitiveDecisions++;
    }

    /* ========================================================
       LEARNING (محسن)
    ======================================================== */

    learnFromEvent(payload = {}) {

        const entry = {
            type: payload.entry?.type,
            timestamp: Date.now(),
            payload,
            cognitiveImportance: this.calculateImportance(payload)
        };

        this.patterns.push(entry);

        if (this.patterns.length > this.maxPatterns) {
            this.patterns.shift();
        }
    }

    calculateImportance(payload) {

        // حساب الأهمية الإدراكية للحدث
        let importance = 1;

        if (payload.entry?.type === 'anomaly_detected') importance = 10;
        else if (payload.entry?.type === 'mode-transition') importance = 5;
        else if (payload.entry?.type === 'pressure-transition') importance = 3;
        else if (payload.entry?.type === 'health-change' && payload.entry?.payload?.health < 50) importance = 4;

        return Math.min(10, importance);
    }

    /* ========================================================
       SNAPSHOT ANALYSIS (محسن)
    ======================================================== */

    analyzeSnapshot(payload = {}) {

        const snapshot = payload.snapshot;
        if (!snapshot) return;

        const stability = snapshot.stability || 100;
        const systemHealth = snapshot.system?.health || 100;

        // كشف الشذوذ مع تصنيف
        if (stability < 35) {
            this.registerAnomaly({
                type: 'runtime-instability',
                severity: 'critical',
                stability,
                systemHealth,
                predictedRecovery: stability < 20 ? 'unlikely' : 'possible'
            });
        } else if (stability < 55) {
            this.registerAnomaly({
                type: 'runtime-instability',
                severity: 'warning',
                stability,
                systemHealth
            });
        }

        // توقع الانهيار الكامل
        if (stability < 50 && systemHealth < 40) {
            this.predictRisk('complete-collapse', 'critical', {
                stability,
                health: systemHealth,
                timeToCollapse: this.estimateTimeToCollapse(stability, systemHealth)
            });
        }
    }

    estimateTimeToCollapse(stability, health) {

        // تقدير وقت الانهيار بالثواني
        const stabilityFactor = Math.max(0, stability - 30) / 70;
        const healthFactor = health / 100;
        const timeSeconds = Math.floor(60 * (1 - (stabilityFactor * healthFactor)));

        return Math.max(10, Math.min(60, timeSeconds));
    }

    /* ========================================================
       MODE TRANSITIONS
    ======================================================== */

    observeModeTransition(payload = {}) {

        const current = payload.current;
        const previous = payload.previous;

        // تعلم الأنماط الخطرة
        if (previous === 'normal' && current === 'critical') {
            this.patternLibrary.set('normal→critical', {
                count: (this.patternLibrary.get('normal→critical')?.count || 0) + 1,
                confidence: 60,
                lastSeen: Date.now()
            });
        }

        if (current === 'critical') {
            this.predictRisk('critical-runtime', 'extreme', {
                from: previous,
                to: current,
                timestamp: Date.now()
            });
        }

        if (current === 'recovery') {
            this.metrics.recoveries++;
            this.recoveryStrategies.history.push({
                from: previous,
                to: current,
                success: true,
                timestamp: Date.now()
            });

            // تحديث معدل نجاح التعافي
            const recentRecoveries = this.recoveryStrategies.history.slice(-10);
            const successes = recentRecoveries.filter(r => r.success).length;
            this.recoveryStrategies.successRate = (successes / recentRecoveries.length) * 100;
        }
    }

    /* ========================================================
       COGNITIVE EVALUATION (محسن)
    ======================================================== */

    evaluateRuntime() {

        const telemetry = window.SOVEREIGN_FLOW_TELEMETRY?.getStatus?.();
        const fairness = window.SOVEREIGN_FAIRNESS_ENGINE?.getStatus?.();
        const system = window.SOVEREIGN_SYSTEM_STATE?.getStatus?.();

        if (!telemetry || !fairness || !system) return;

        const fairnessScore = fairness.fairnessScore || 100;
        const stability = telemetry.stability || 100;
        const health = system.health || 100;
        const pressure = system.pressure;

        // تحليل معرفي متكامل
        const cognitiveRisk = this.calculateCognitiveRisk({
            fairnessScore,
            stability,
            health,
            pressure
        });

        // Fairness Collapse
        if (fairnessScore < 50 && cognitiveRisk > 60) {
            this.triggerPreventiveAction('fairness-collapse', {
                fairnessScore,
                cognitiveRisk,
                recommendation: 'increase_fairness_boost'
            });
        }

        // Stability Collapse
        if (stability < 40 && cognitiveRisk > 70) {
            this.triggerPreventiveAction('stability-collapse', {
                stability,
                cognitiveRisk,
                forecast30s: this.forecast.stabilityIn30s
            });
        }

        // Extreme Pressure
        if (pressure === 'extreme' && cognitiveRisk > 80) {
            this.triggerPreventiveAction('extreme-pressure', {
                pressure,
                cognitiveRisk,
                stabilityForecast: this.forecast.stabilityIn30s
            });
        }

        // تحديث الثقة المعرفية
        this.cognitiveConfidence = Math.max(0, 100 - cognitiveRisk);
    }

    calculateCognitiveRisk({ fairnessScore, stability, health, pressure }) {

        let risk = 0;

        // عامل العدالة
        risk += (100 - fairnessScore) * 0.3;

        // عامل الاستقرار
        risk += (100 - stability) * 0.35;

        // عامل الصحة
        risk += (100 - health) * 0.2;

        // عامل الضغط
        const pressureRisk = { low: 0, moderate: 20, high: 50, extreme: 80 };
        risk += pressureRisk[pressure] || 0;

        // عامل التنبؤ (من الـ forecast)
        if (this.forecast.stabilityIn30s < 50) {
            risk += (50 - this.forecast.stabilityIn30s) * 0.3;
        }

        return Math.min(100, risk);
    }

    /* ========================================================
       PREDICTIONS (محسن مع تتبع النشاط)
    ======================================================== */

    predictRisk(type, severity, metadata = {}) {

        const prediction = {
            id: crypto.randomUUID(),
            type,
            severity,
            metadata,
            timestamp: Date.now(),
            expectedWindow: this.estimateRiskWindow(type, severity)
        };

        this.predictions.push(prediction);
        this.activePredictions.set(type, prediction);

        if (this.predictions.length > this.maxPredictions) {
            this.predictions.shift();
        }

        // تنظيف التنبؤات النشطة القديمة (أكثر من دقيقة)
        setTimeout(() => {
            if (this.activePredictions.get(type) === prediction) {
                this.activePredictions.delete(type);
            }
        }, 60000);

        this.metrics.predictions++;
        this.lastPrediction = prediction;

        this.publishPrediction(prediction);

        // إذا كان التنبؤ شديداً، اتخذ إجراءً استباقياً
        if (severity === 'critical' || severity === 'extreme') {
            this.triggerPreventiveAction(`predicted-${type}`, metadata);
        }
    }

    estimateRiskWindow(type, severity) {

        // تقدير النافذة الزمنية لحدوث الخطر (بالثواني)
        const windows = {
            'degradation-risk': severity === 'critical' ? 15 : 30,
            'complete-collapse': 20,
            'critical-runtime': 10,
            'health-decline': 25,
            'pressure-cascade': 12
        };

        return windows[type] || 30;
    }

    /* ========================================================
       ANOMALIES (محسن مع تصنيف)
    ======================================================== */

    registerAnomaly(anomaly = {}) {

        const entry = {
            id: crypto.randomUUID(),
            ...anomaly,
            cognitiveImpact: this.calculateCognitiveImpact(anomaly),
            timestamp: Date.now()
        };

        this.anomalies.push(entry);

        // تحديث مكتبة الشذوذ
        const anomalyType = anomaly.type;
        const existing = this.anomalyLibrary.get(anomalyType) || { count: 0, lastSeen: null };
        existing.count++;
        existing.lastSeen = Date.now();
        this.anomalyLibrary.set(anomalyType, existing);

        if (this.anomalies.length > this.maxAnomalies) {
            this.anomalies.shift();
        }

        this.metrics.anomalies++;
        this.lastAnomaly = entry;

        this.publishAnomaly(entry);
    }

    calculateCognitiveImpact(anomaly) {

        // حساب التأثير المعرفي للشذوذ (0-100)
        let impact = 30;

        if (anomaly.severity === 'critical') impact = 80;
        else if (anomaly.severity === 'warning') impact = 50;

        if (anomaly.type === 'runtime-instability') impact += 10;
        if (anomaly.stability < 30) impact += 20;

        return Math.min(100, impact);
    }

    /* ========================================================
       PREVENTIVE ACTIONS (محسن)
    ======================================================== */

    triggerPreventiveAction(reason, metadata = {}) {

        this.metrics.preventiveActions++;
        this.state = 'acting';

        console.log(`🛡 Cognitive Preventive Action | REASON: ${reason} | METADATA:`, metadata);

        const actionMap = {
            'stability-collapse': () => this.activateStabilization(metadata),
            'fairness-collapse': () => this.activateFairnessProtection(metadata),
            'extreme-pressure': () => this.activatePressureProtection(metadata),
            'forecasted-degradation': () => this.activatePreventiveDegradation(metadata),
            'pressure-escalating': () => this.activateThrottlingPreparation(metadata),
            'predicted-critical-runtime': () => this.activateCriticalPreparation(metadata)
        };

        const action = actionMap[reason];
        if (action) {
            action();
            this.publishCognitiveAction(reason, metadata);
        }

        // العودة إلى حالة الملاحظة بعد ثانية
        setTimeout(() => {
            if (this.state === 'acting') {
                this.state = 'observing';
            }
        }, 1000);
    }

    /* ========================================================
       PREVENTIVE ACTIONS (إجراءات استباقية جديدة)
    ======================================================== */

    activatePreventiveDegradation(metadata) {

        console.log(`🛡 Activating preventive degradation (forecasted stability: ${metadata.stability30s})`);

        window.SOVEREIGN_MODE_MANAGER?.requestTransition('degraded', 'cognition-engine');

        document.body.classList.add('runtime-preventive');
        this.metrics.stabilizations++;
    }

    activateThrottlingPreparation(metadata) {

        console.log(`🛡 Preparing throttling before pressure becomes extreme`);

        window.SOVEREIGN_SYSTEM_STATE?.setFlag('adaptivePacing', false);
        window.SOVEREIGN_SYSTEM_STATE?.setFlag('cinematicEffects', false);

        this.publishCognitiveUpdate('throttling_prepared', metadata);
    }

    activateCriticalPreparation(metadata) {

        console.log(`🛡 Preparing for critical mode transition`);

        // إجراءات تحضيرية قبل الدخول في الوضع الحرج
        window.SOVEREIGN_SYSTEM_STATE?.setFlag('queueProtection', true);
        window.SOVEREIGN_SYSTEM_STATE?.setFlag('safeMode', true);
    }

    /* ========================================================
       STABILIZATION (محسن)
    ======================================================== */

    activateStabilization(metadata = {}) {

        this.metrics.stabilizations++;

        window.SOVEREIGN_MODE_MANAGER?.requestTransition('degraded', 'cognition-engine');

        document.body.classList.add('runtime-stabilizing');
        document.body.classList.add('runtime-cognitive-action');

        setTimeout(() => {
            if (typeof document !== 'undefined') {
                document.body.classList.remove('runtime-stabilizing');
                document.body.classList.remove('runtime-cognitive-action');
            }
        }, 3000);

        this.publishCognitiveAction('runtime-stabilization', metadata);
    }

    /* ========================================================
       FAIRNESS PROTECTION (محسن)
    ======================================================== */

    activateFairnessProtection(metadata = {}) {

        if (typeof document !== 'undefined') {
            document.body.classList.add('runtime-fairness-protection');
            document.body.classList.add('runtime-cognitive-action');
        }

        // طلب تعزيز العدالة
        const fairness = window.SOVEREIGN_FAIRNESS_ENGINE;
        if (fairness && fairness.escalation) {
            // محاولة تصعيد أولويات المهام
            fairness.metrics.escalationsTriggered++;
        }

        setTimeout(() => {
            if (typeof document !== 'undefined') {
                document.body.classList.remove('runtime-fairness-protection');
                document.body.classList.remove('runtime-cognitive-action');
            }
        }, 2000);

        this.publishCognitiveAction('fairness-protection', metadata);
    }

    /* ========================================================
       PRESSURE PROTECTION (محسن)
    ======================================================== */

    activatePressureProtection(metadata = {}) {

        window.SOVEREIGN_MODE_MANAGER?.requestTransition('critical', 'cognition-engine');

        if (typeof document !== 'undefined') {
            document.body.classList.add('runtime-pressure-protection');
            document.body.classList.add('runtime-cognitive-action');
        }

        setTimeout(() => {
            if (typeof document !== 'undefined') {
                document.body.classList.remove('runtime-pressure-protection');
                document.body.classList.remove('runtime-cognitive-action');
            }
        }, 5000);

        this.publishCognitiveAction('pressure-protection', metadata);
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishCognitiveAction(action, metadata = {}) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:cognition:action', {
                action,
                metadata,
                confidence: this.cognitiveConfidence,
                timestamp: Date.now()
            });
        }
    }

    publishCognitiveUpdate(type, data) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:cognition:update', {
                type,
                data,
                timestamp: Date.now()
            });
        }
    }

    publishPrediction(prediction) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:cognition:prediction', {
                prediction,
                confidence: this.predictionAccuracy,
                timestamp: Date.now()
            });
        }
    }

    publishAnomaly(anomaly) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:cognition:anomaly', {
                anomaly,
                cognitiveImpact: anomaly.cognitiveImpact,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime-cognition-engine:ready', {
                state: this.state,
                capabilities: ['prediction', 'anomaly_detection', 'pattern_learning', 'forecasting', 'preventive_action'],
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        return {
            state: this.state,
            cognitiveConfidence: this.cognitiveConfidence,
            predictionAccuracy: this.predictionAccuracy,
            patterns: this.patterns.length,
            patternLibrary: this.patternLibrary.size,
            predictions: this.predictions.length,
            activePredictions: this.activePredictions.size,
            anomalies: this.anomalies.length,
            anomalyLibrary: this.anomalyLibrary.size,
            forecast: this.forecast,
            recoveryStrategies: {
                successRate: this.recoveryStrategies.successRate,
                total: this.recoveryStrategies.history.length
            },
            lastPrediction: this.lastPrediction,
            lastAnomaly: this.lastAnomaly,
            metrics: { ...this.metrics }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._cognitiveInterval) {
            clearInterval(this._cognitiveInterval);
            this._cognitiveInterval = null;
        }

        if (this._forecastInterval) {
            clearInterval(this._forecastInterval);
            this._forecastInterval = null;
        }

        if (this._patternInterval) {
            clearInterval(this._patternInterval);
            this._patternInterval = null;
        }

        this.activePredictions.clear();
        this.patternLibrary.clear();
        this.anomalyLibrary.clear();

        console.log('🧠 Runtime Cognition Engine Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeCognitionEngine =
    new SovereignRuntimeCognitionEngine();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_COGNITION =
    sovereignRuntimeCognitionEngine;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register('cognition-engine', sovereignRuntimeCognitionEngine);
}
