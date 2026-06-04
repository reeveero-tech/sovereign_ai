/* ============================================================
   Sovereign AI — runtime-flow-telemetry.js
   الإصدار: 9.0.0
   نظام المراقبة الزمنية والتدفق السيادي
   ============================================================ */

class SovereignRuntimeFlowTelemetry {

    constructor() {

        /* =========================================
           STORAGE
        ========================================= */

        this.timeline = [];

        this.maxTimeline =
            500;

        /* =========================================
           METRICS
        ========================================= */

        this.metrics = {

            stateTransitions:
                0,

            pressureTransitions:
                0,

            modeTransitions:
                0,

            healthChanges:
                0,

            throttlingEvents:
                0,

            safeModeActivations:
                0,

            queueProtectionEvents:
                0
        };

        /* =========================================
           SNAPSHOTS
        ========================================= */

        this.snapshots = [];

        this.maxSnapshots =
            120;

        /* =========================================
           RUNTIME STABILITY
        ========================================= */

        this.stabilityScore =
            100;

        this.stabilityHistory = [];

        /* =========================================
           TEMPORAL PATTERNS (الأنماط الزمنية)
        ========================================= */

        this.patterns = {

            detected: [],      // الأنماط المكتشفة
            cycles: new Map(), // الدورات الزمنية
            rhythms: []        // إيقاعات السلوك
        };

        /* =========================================
           ANOMALY DETECTION (كشف الشذوذ)
        ========================================= */

        this.anomalies = {

            detected: [],
            thresholds: {
                healthDropThreshold: 15,   // انخفاض الصحة بأكثر من 15 نقطة
                rapidStateChange: 5,       // 5 تغييرات حالة في دقيقة
                pressureSpike: 2           // ارتفاعين سريعين للضغط
            }
        };

        /* =========================================
           CAUSAL TRACING (التتبع السببي)
        ========================================= */

        this.causalChains = [];  // سلاسل الأسباب والنتائج

        /* =========================================
           PREDICTIVE STABILITY (تنبؤ بالاستقرار)
        ========================================= */

        this.predictions = {

            stabilityIn5min: 100,
            stabilityIn10min: 100,
            confidence: 0,
            trend: 'stable' // improving, degrading, stable
        };

        console.log(
            '📊 Runtime Flow Telemetry Initialized (Temporal Awareness Edition)'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindRuntimeState();

        this.startSnapshotLoop();

        this.startStabilityMonitoring();

        this.startPatternDetection();

        this.startAnomalyDetection();

        this.startCausalTracing();

        this.publishReady();
    }

    /* ========================================================
       RUNTIME STATE
    ======================================================== */

    bindRuntimeState() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (!bus) {

            return;
        }

        /* =========================================
           STATE
        ========================================= */

        bus.subscribe(

            'runtime:state:changed',

            payload => {

                this.metrics.stateTransitions++;

                this.recordEvent(

                    'state-transition',

                    payload
                );
            }
        );

        /* =========================================
           MODE
        ========================================= */

        bus.subscribe(

            'runtime:mode:changed',

            payload => {

                this.metrics.modeTransitions++;

                this.recordEvent(

                    'mode-transition',

                    payload
                );
            }
        );

        /* =========================================
           PRESSURE
        ========================================= */

        bus.subscribe(

            'runtime:pressure:changed',

            payload => {

                this.metrics.pressureTransitions++;

                this.recordEvent(

                    'pressure-transition',

                    payload
                );

                if (
                    payload.pressure ===
                    'high'
                    ||
                    payload.pressure ===
                    'extreme'
                ) {

                    this.metrics.throttlingEvents++;
                }
            }
        );

        /* =========================================
           HEALTH
        ========================================= */

        bus.subscribe(

            'runtime:health:changed',

            payload => {

                this.metrics.healthChanges++;

                this.recordEvent(

                    'health-change',

                    payload
                );
            }
        );

        /* =========================================
           FLAGS
        ========================================= */

        bus.subscribe(

            'runtime:flag:changed',

            payload => {

                this.recordEvent(

                    'flag-change',

                    payload
                );
            }
        );
    }

    /* ========================================================
       RECORD EVENT (محسن مع تحليل فوري)
    ======================================================== */

    recordEvent(

        type,

        payload = {}

    ) {

        const entry = {

            id:
                crypto.randomUUID(),

            type,

            payload,

            timestamp:
                Date.now()
        };

        this.timeline.push(
            entry
        );

        if (
            this.timeline.length >
            this.maxTimeline
        ) {

            this.timeline.shift();
        }

        this.evaluateBehavioralMetrics(
            entry
        );

        this.updateRhythmDetection(entry);

        this.publishTelemetry(
            entry
        );
    }

    /* ========================================================
       PATTERN DETECTION (كشف الأنماط الزمنية)
    ======================================================== */

    startPatternDetection() {

        this.patternInterval = setInterval(() => {

            this.detectTemporalPatterns();

        }, 15000); // كل 15 ثانية
    }

    detectTemporalPatterns() {

        const recentEvents = this.timeline.slice(-100);

        if (recentEvents.length < 20) return;

        // 1. كشف الدورات (Cycles)
        const stateSequence = recentEvents
            .filter(e => e.type === 'state-transition')
            .map(e => e.payload.state);

        this.detectCycles(stateSequence);

        // 2. كشف الإيقاعات (Rhythms)
        const timeDiffs = [];

        for (let i = 1; i < recentEvents.length; i++) {

            const diff = recentEvents[i].timestamp - recentEvents[i-1].timestamp;
            timeDiffs.push(diff);
        }

        if (timeDiffs.length > 10) {

            const avgDiff = timeDiffs.reduce((a,b) => a+b, 0) / timeDiffs.length;
            const stdDev = Math.sqrt(
                timeDiffs.map(d => Math.pow(d - avgDiff, 2)).reduce((a,b) => a+b, 0) / timeDiffs.length
            );

            const rhythmDetected = {
                averageInterval: Math.round(avgDiff),
                consistency: Math.max(0, 100 - (stdDev / avgDiff) * 100),
                detectedAt: Date.now()
            };

            this.patterns.rhythms.push(rhythmDetected);

            if (this.patterns.rhythms.length > 20) {
                this.patterns.rhythms.shift();
            }
        }
    }

    detectCycles(sequence) {

        // كشف أنماط متكررة بطول 2-4
        for (let len = 2; len <= 4; len++) {

            for (let i = 0; i <= sequence.length - len * 2; i++) {

                const pattern = sequence.slice(i, i + len);
                const next = sequence.slice(i + len, i + len * 2);

                if (JSON.stringify(pattern) === JSON.stringify(next)) {

                    const patternKey = pattern.join('->');

                    if (!this.patterns.cycles.has(patternKey)) {
                        this.patterns.cycles.set(patternKey, 0);
                    }

                    this.patterns.cycles.set(patternKey, this.patterns.cycles.get(patternKey) + 1);
                }
            }
        }

        // تنظيف الخريطة
        for (const [key, count] of this.patterns.cycles) {
            if (count < 2) {
                this.patterns.cycles.delete(key);
            }
        }
    }

    /* ========================================================
       ANOMALY DETECTION (كشف الشذوذ)
    ======================================================== */

    startAnomalyDetection() {

        this.anomalyInterval = setInterval(() => {

            this.detectAnomalies();

        }, 8000);
    }

    detectAnomalies() {

        const recentHealthEvents = this.timeline
            .slice(-20)
            .filter(e => e.type === 'health-change');

        // كشف الانخفاض السريع في الصحة
        for (let i = 1; i < recentHealthEvents.length; i++) {

            const prev = recentHealthEvents[i-1].payload.health;
            const curr = recentHealthEvents[i].payload.health;
            const drop = prev - curr;

            if (drop >= this.anomalies.thresholds.healthDropThreshold) {

                this.recordAnomaly({
                    type: 'rapid_health_drop',
                    severity: Math.min(100, drop * 2),
                    from: prev,
                    to: curr,
                    timestamp: recentHealthEvents[i].timestamp
                });
            }
        }

        // كشف التغييرات السريعة في الحالة
        const recentStateEvents = this.timeline
            .slice(-60) // آخر دقيقة تقريباً
            .filter(e => e.type === 'state-transition');

        if (recentStateEvents.length >= this.anomalies.thresholds.rapidStateChange) {

            this.recordAnomaly({
                type: 'rapid_state_changes',
                severity: Math.min(100, recentStateEvents.length * 10),
                count: recentStateEvents.length,
                timespan: 60000,
                timestamp: Date.now()
            });
        }

        // كشف ارتفاع الضغط المتكرر
        const recentPressureEvents = this.timeline
            .slice(-30)
            .filter(e => e.type === 'pressure-transition' && 
                   (e.payload.pressure === 'high' || e.payload.pressure === 'extreme'));

        if (recentPressureEvents.length >= this.anomalies.thresholds.pressureSpike) {

            this.recordAnomaly({
                type: 'pressure_spike',
                severity: 70,
                count: recentPressureEvents.length,
                timestamp: Date.now()
            });
        }
    }

    recordAnomaly(anomaly) {

        this.anomalies.detected.push({
            ...anomaly,
            stabilityAtTime: this.stabilityScore,
            id: crypto.randomUUID()
        });

        // الاحتفاظ بآخر 50 شذوذ فقط
        if (this.anomalies.detected.length > 50) {
            this.anomalies.detected.shift();
        }

        this.publishTelemetry({
            type: 'anomaly_detected',
            payload: anomaly
        });

        console.warn(`⚠️ Anomaly detected: ${anomaly.type} (severity: ${anomaly.severity})`);
    }

    /* ========================================================
       CAUSAL TRACING (التتبع السببي)
    ======================================================== */

    startCausalTracing() {

        this.causalInterval = setInterval(() => {

            this.traceCausalChains();

        }, 20000);
    }

    traceCausalChains() {

        const events = this.timeline.slice(-50);

        if (events.length < 10) return;

        const chains = [];
        let currentChain = [];

        for (let i = 0; i < events.length; i++) {

            const event = events[i];
            currentChain.push(event);

            // إذا كان الحدث يمثل تدهوراً، أغلقه كسلسلة
            if (event.type === 'state-transition' && 
                (event.payload.state === 'degraded' || event.payload.state === 'shutdown')) {

                if (currentChain.length > 1) {
                    chains.push({
                        events: [...currentChain],
                        duration: currentChain[currentChain.length-1].timestamp - currentChain[0].timestamp,
                        endedAt: event.timestamp
                    });
                }
                currentChain = [];
            }
        }

        this.causalChains = chains.slice(-20);
    }

    getCausalAnalysis() {

        if (this.causalChains.length === 0) return null;

        const lastChain = this.causalChains[this.causalChains.length - 1];

        return {
            totalChains: this.causalChains.length,
            lastChainDuration: lastChain.duration,
            lastChainEvents: lastChain.events.map(e => ({ type: e.type, timestamp: e.timestamp })),
            averageChainDuration: this.causalChains.reduce((a,b) => a + b.duration, 0) / this.causalChains.length
        };
    }

    /* ========================================================
       SNAPSHOTS
    ======================================================== */

    startSnapshotLoop() {

        // استخدام polling آمن بدلاً من الاعتماد على scheduler
        this._snapshotInterval = setInterval(() => {

            this.captureSnapshot();

        }, 5000);
    }

    /* ========================================================
       CAPTURE (محسن)
    ======================================================== */

    captureSnapshot() {

        const system =
            window.SOVEREIGN_SYSTEM_STATE
                ?.getStatus?.();

        const resources =
            window.SOVEREIGN_RESOURCES
                ?.getStatus?.();

        const health =
            window.SOVEREIGN_HEALTH
                ?.getStatus?.();

        const orchestrator =
            window.SOVEREIGN_ORCHESTRATOR_AI
                ?.getStatus?.();

        const snapshot = {

            timestamp:
                Date.now(),

            system,

            resources,

            health,

            orchestrator,

            stability:
                this.stabilityScore,

            patterns: {
                cyclesCount: this.patterns.cycles.size,
                rhythmsCount: this.patterns.rhythms.length
            },

            anomaliesCount: this.anomalies.detected.length
        };

        this.snapshots.push(
            snapshot
        );

        if (
            this.snapshots.length >
            this.maxSnapshots
        ) {

            this.snapshots.shift();
        }

        this.publishSnapshot(
            snapshot
        );
    }

    /* ========================================================
       STABILITY (محسن مع التاريخ والتنبؤ)
    ======================================================== */

    startStabilityMonitoring() {

        this._stabilityInterval = setInterval(() => {

            this.calculateStability();

            this.updateStabilityHistory();

            this.predictFutureStability();

        }, 4000);
    }

    updateStabilityHistory() {

        this.stabilityHistory.push({
            score: this.stabilityScore,
            timestamp: Date.now()
        });

        if (this.stabilityHistory.length > 100) {
            this.stabilityHistory.shift();
        }
    }

    predictFutureStability() {

        if (this.stabilityHistory.length < 10) {
            this.predictions.confidence = 0;
            return;
        }

        // حساب التوجه (trend) بناءً على آخر 10 قيم
        const recent = this.stabilityHistory.slice(-10);
        const firstAvg = recent.slice(0, 5).reduce((a,b) => a + b.score, 0) / 5;
        const lastAvg = recent.slice(-5).reduce((a,b) => a + b.score, 0) / 5;
        const change = lastAvg - firstAvg;

        if (change > 5) {
            this.predictions.trend = 'improving';
        } else if (change < -5) {
            this.predictions.trend = 'degrading';
        } else {
            this.predictions.trend = 'stable';
        }

        // التنبؤ (خطي بسيط)
        const avgChangePerInterval = change / 10; // لكل 4 ثوانٍ
        const intervalsIn5min = 75; // 5 دقائق / 4 ثوانٍ
        const intervalsIn10min = 150;

        let predicted5min = this.stabilityScore + (avgChangePerInterval * intervalsIn5min);
        let predicted10min = this.stabilityScore + (avgChangePerInterval * intervalsIn10min);

        this.predictions.stabilityIn5min = Math.max(0, Math.min(100, Math.round(predicted5min)));
        this.predictions.stabilityIn10min = Math.max(0, Math.min(100, Math.round(predicted10min)));

        // حساب الثقة بناءً على استقرار التوجه
        const volatility = Math.abs(change) / 100;
        this.predictions.confidence = Math.max(0, Math.min(100, Math.round(100 - (volatility * 100))));

        // نشر التنبؤ
        this.publishTelemetry({
            type: 'stability_prediction',
            payload: { ...this.predictions }
        });
    }

    /* ========================================================
       RHYTHM DETECTION (كشف الإيقاع الفوري)
    ======================================================== */

    updateRhythmDetection(entry) {

        // تتبع توقيت الأحداث المتكررة
        const lastSameType = this.timeline
            .slice(-10)
            .filter(e => e.type === entry.type && e !== entry)
            .pop();

        if (lastSameType) {

            const interval = entry.timestamp - lastSameType.timestamp;

            if (!this.patterns.cycles.has(`${entry.type}_interval`)) {
                this.patterns.cycles.set(`${entry.type}_interval`, []);
            }

            const intervals = this.patterns.cycles.get(`${entry.type}_interval`);
            intervals.push(interval);

            if (intervals.length > 20) intervals.shift();
        }
    }

    /* ========================================================
       CALCULATE (محسن)
    ======================================================== */

    calculateStability() {

        let score = 100;

        const system =
            window.SOVEREIGN_SYSTEM_STATE
                ?.getStatus?.();

        if (!system) {

            return;
        }

        /* =========================================
           HEALTH
        ========================================= */

        score -= (
            100 - system.health
        ) * 0.4;

        /* =========================================
           PRESSURE
        ========================================= */

        switch (
            system.pressure
        ) {

            case 'moderate':

                score -= 10;
                break;

            case 'high':

                score -= 25;
                break;

            case 'extreme':

                score -= 45;
                break;
        }

        /* =========================================
           MODES
        ========================================= */

        switch (
            system.mode
        ) {

            case 'elevated':

                score -= 5;
                break;

            case 'degraded':

                score -= 20;
                break;

            case 'critical':

                score -= 40;
                break;
        }

        /* =========================================
           ANOMALY PENALTY (خصم الشذوذ)
        ========================================= */

        const recentAnomalies = this.anomalies.detected.filter(
            a => a.timestamp > Date.now() - 60000
        );

        score -= recentAnomalies.length * 5;

        /* =========================================
           RHYTHM CONSISTENCY BONUS (مكافأة الإيقاع)
        ========================================= */

        if (this.patterns.rhythms.length > 0) {
            const lastRhythm = this.patterns.rhythms[this.patterns.rhythms.length - 1];
            if (lastRhythm.consistency > 80) {
                score += 5;
            }
        }

        this.stabilityScore =
            Math.max(
                0,
                Math.round(score)
            );

        this.syncBodyState();
    }

    /* ========================================================
       BODY (محسن)
    ======================================================== */

    syncBodyState() {

        if (typeof document === 'undefined') return;

        document.body.dataset.runtimeStability =
            this.stabilityScore;

        document.body.dataset.stabilityTrend =
            this.predictions.trend;

        if (
            this.stabilityScore < 50
        ) {

            document.body.classList.add(
                'runtime-unstable'
            );

        } else {

            document.body.classList.remove(
                'runtime-unstable'
            );
        }
    }

    /* ========================================================
       BEHAVIORAL METRICS
    ======================================================== */

    evaluateBehavioralMetrics(entry) {

        const flags =
            entry.payload
                ?.flags;

        if (!flags) {

            return;
        }

        if (
            flags.safeMode
        ) {

            this.metrics.safeModeActivations++;
        }

        if (
            flags.queueProtection
        ) {

            this.metrics.queueProtectionEvents++;
        }
    }

    /* ========================================================
       TELEMETRY STREAM
    ======================================================== */

    publishTelemetry(entry) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware(

                'telemetry:event',

                {

                    entry,

                    stability:
                        this.stabilityScore,

                    predictions: this.predictions,

                    timestamp:
                        Date.now()
                }
            );
        }
    }

    /* ========================================================
       SNAPSHOT STREAM
    ======================================================== */

    publishSnapshot(snapshot) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware(

                'telemetry:snapshot',

                {

                    snapshot,

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

                'telemetry:ready',

                {

                    timeline:
                        this.timeline.length,

                    temporalAwareness: true,
                    patternDetection: true,
                    anomalyDetection: true,
                    causalTracing: true,
                    predictiveStability: true,

                    timestamp:
                        Date.now()
                }
            );
        }
    }

    /* ========================================================
       EXPORT (محسن)
    ======================================================== */

    exportTelemetry() {

        return {

            metrics:
                this.metrics,

            stability:
                this.stabilityScore,

            timeline:
                this.timeline,

            snapshots:
                this.snapshots,

            patterns: {
                cycles: Array.from(this.patterns.cycles.entries()),
                rhythms: this.patterns.rhythms.slice(-10)
            },

            anomalies: this.anomalies.detected.slice(-20),

            causalChains: this.causalChains.slice(-10),

            predictions: this.predictions
        };
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        return {

            stability:
                this.stabilityScore,

            timeline:
                this.timeline.length,

            snapshots:
                this.snapshots.length,

            metrics:
                this.metrics,

            patterns: {
                cyclesDetected: this.patterns.cycles.size,
                rhythmsCaptured: this.patterns.rhythms.length
            },

            anomalies: {
                totalDetected: this.anomalies.detected.length,
                lastAnomaly: this.anomalies.detected[this.anomalies.detected.length - 1] || null
            },

            predictions: this.predictions,

            causalChains: this.causalChains.length
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._snapshotInterval) {
            clearInterval(this._snapshotInterval);
            this._snapshotInterval = null;
        }

        if (this._stabilityInterval) {
            clearInterval(this._stabilityInterval);
            this._stabilityInterval = null;
        }

        if (this.patternInterval) {
            clearInterval(this.patternInterval);
            this.patternInterval = null;
        }

        if (this.anomalyInterval) {
            clearInterval(this.anomalyInterval);
            this.anomalyInterval = null;
        }

        if (this.causalInterval) {
            clearInterval(this.causalInterval);
            this.causalInterval = null;
        }

        console.log('📊 Runtime Flow Telemetry Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeFlowTelemetry =
    new SovereignRuntimeFlowTelemetry();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_FLOW_TELEMETRY =
    sovereignRuntimeFlowTelemetry;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register(

        'flow-telemetry',

        sovereignRuntimeFlowTelemetry
    );
}
