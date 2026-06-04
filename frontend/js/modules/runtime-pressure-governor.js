/* ============================================================
   Sovereign AI — runtime-pressure-governor.js
   الإصدار: 9.0.0
   الحاكم المركزي للضغط والاستقرار السيادي
   ============================================================ */

class SovereignRuntimePressureGovernor {

    constructor() {

        /* =========================================
           GOVERNOR STATE
        ========================================= */

        this.mode =
            'balanced';

        this.level =
            'normal';

        this.lastDecision =
            null;

        /* =========================================
           PRESSURE HISTORY
        ========================================= */

        this.history = [];

        this.maxHistory =
            200;

        /* =========================================
           STABILIZATION
        ========================================= */

        this.stabilizationEnabled =
            true;

        this.recoveryMode =
            false;

        /* =========================================
           HYSTERESIS (منع التذبذب)
        ========================================= */

        this.hysteresis = {

            enabled: true,
            thresholds: {
                degradedToNormal: 45,    // العودة للطبيعي عند ضغط < 45
                criticalToDegraded: 35,  // العودة للتدهور عند ضغط < 35
                elevatedToBalanced: 25   // العودة للتوازن عند ضغط < 25
            },
            lastModeChange: null,
            cooldownPeriod: 5000,        // 5 ثواني بين تغييرات الوضع
            pendingChange: null
        };

        /* =========================================
           DEGRADATION CEILING (حدود التدهور)
        ========================================= */

        this.degradationCeiling = {

            maxDegradationLevel: 80,     // أقصى تدهور مسموح (0-100)
            currentDegradation: 0,
            escalationHistory: []
        };

        /* =========================================
           ADAPTIVE POLICIES (سياسات تكيفية)
        ========================================= */

        this.policies = {

            aggressive: false,            // وضع عدواني عند الضغط العالي
            conservative: false,          // وضع متحفظ عند الاستقرار
            learnedThresholds: {
                highPressure: 60,         // يتم تعديلها بناءً على التاريخ
                extremePressure: 85
            }
        };

        /* =========================================
           METRICS
        ========================================= */

        this.metrics = {

            throttles:
                0,

            degradations:
                0,

            recoveries:
                0,

            escalations:
                0,

            cinematicSuppressions:
                0,

            hysteresisBlocks: 0,           // عدد المرات التي منع فيها التذبذب
            adaptiveAdjustments: 0         // عدد تعديلات السياسات التكيفية
        };

        console.log(
            '⚖️ Runtime Pressure Governor Initialized (Hysteresis + Adaptive Edition)'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindTelemetry();

        this.startGovernorLoop();

        this.learnAdaptivePolicies();

        this.publishReady();
    }

    /* ========================================================
       TELEMETRY
    ======================================================== */

    bindTelemetry() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (!bus) {

            return;
        }

        if (typeof bus.subscribe === 'function') {

            bus.subscribe(

                'runtime:pressure:changed',

                payload => {

                    this.handlePressure(
                        payload
                    );
                }
            );

            bus.subscribe(

                'runtime:health:changed',

                payload => {

                    this.handleHealth(
                        payload
                    );
                }
            );

            bus.subscribe(

                'telemetry:event',

                ({ entry }) => {

                    this.observeTelemetry(
                        entry
                    );
                }
            );
        }
    }

    /* ========================================================
       GOVERNOR LOOP
    ======================================================== */

    startGovernorLoop() {

        // استخدام polling آمن بدلاً من الاعتماد على scheduler
        this._governorInterval = setInterval(() => {

            this.evaluateRuntimePressure();

        }, 4000);
    }

    /* ========================================================
       ADAPTIVE POLICY LEARNING (تعلم السياسات التكيفية)
    ======================================================== */

    learnAdaptivePolicies() {

        this._learningInterval = setInterval(() => {

            this.updateAdaptiveThresholds();

        }, 30000); // كل 30 ثانية
    }

    updateAdaptiveThresholds() {

        // تحليل تاريخ الضغط لتعديل العتبات
        const pressureEvents = this.history.filter(
            h => h.type === 'pressure-event' || h.type === 'governor-decision'
        );

        if (pressureEvents.length < 20) return;

        // حساب متوسط الضغط خلال فترات التدهور
        const degradationEvents = this.history.filter(
            h => h.mode === 'degraded' || h.mode === 'critical'
        );

        if (degradationEvents.length > 5) {

            // إذا كان التدهور يحدث عند ضغط أقل من المتوقع، نخفض العتبات
            const avgPressureAtDegradation = degradationEvents.reduce(
                (sum, e) => sum + (e.pressureValue || 60), 0
            ) / degradationEvents.length;

            if (avgPressureAtDegradation < 50) {

                this.policies.learnedThresholds.highPressure = Math.max(
                    40,
                    this.policies.learnedThresholds.highPressure - 5
                );

                this.metrics.adaptiveAdjustments++;
            }
        }

        // تحليل فعالية القرارات السابقة
        const recentDecisions = this.history.slice(-10).filter(
            h => h.type === 'governor-decision'
        );

        const recoveryRate = recentDecisions.filter(
            d => d.mode === 'recovery' && d.timestamp > Date.now() - 60000
        ).length;

        if (recoveryRate > 2) {

            // إذا كنا نتعافى كثيراً، ربما السياسات عدوانية جداً
            this.policies.aggressive = false;
            this.policies.conservative = true;
        }
    }

    /* ========================================================
       HYSTERESIS CHECK (منع التذبذب)
    ======================================================== */

    shouldTransition(proposedMode, pressureValue) {

        if (!this.hysteresis.enabled) return true;

        const now = Date.now();

        // منع التغييرات السريعة المتكررة
        if (this.hysteresis.lastModeChange &&
            (now - this.hysteresis.lastModeChange) < this.hysteresis.cooldownPeriod) {

            this.metrics.hysteresisBlocks++;
            return false;
        }

        // قواعد منع التذبذب حسب الوضع الحالي والمرشح
        if (this.mode === 'degraded' && proposedMode === 'balanced') {

            // لا ننتقل من degraded إلى balanced إلا إذا انخفض الضغط كثيراً
            if (pressureValue > this.hysteresis.thresholds.degradedToNormal) {
                return false;
            }
        }

        if (this.mode === 'critical' && proposedMode === 'degraded') {

            if (pressureValue > this.hysteresis.thresholds.criticalToDegraded) {
                return false;
            }
        }

        if (this.mode === 'elevated' && proposedMode === 'balanced') {

            if (pressureValue > this.hysteresis.thresholds.elevatedToBalanced) {
                return false;
            }
        }

        return true;
    }

    applyPendingChange() {

        if (this.hysteresis.pendingChange) {

            const change = this.hysteresis.pendingChange;
            this.hysteresis.pendingChange = null;
            this.executeModeChange(change.mode, change.reason, change.pressureValue);
        }
    }

    /* ========================================================
       PRESSURE
    ======================================================== */

    handlePressure(payload = {}) {

        const pressure =
            payload.pressure;

        let pressureValue = 0;

        switch (pressure) {
            case 'low': pressureValue = 10; break;
            case 'moderate': pressureValue = 35; break;
            case 'high': pressureValue = 65; break;
            case 'extreme': pressureValue = 90; break;
            default: pressureValue = 0;
        }

        // منع التذبذب
        let proposedMode = null;

        switch (pressure) {

            case 'extreme':
                proposedMode = 'critical';
                break;

            case 'high':
                proposedMode = 'degraded';
                break;

            case 'moderate':
                proposedMode = 'elevated';
                break;

            default:
                proposedMode = 'balanced';
        }

        if (this.shouldTransition(proposedMode, pressureValue)) {

            this.executeModeChange(proposedMode, `pressure-${pressure}`, pressureValue);

        } else {

            // جدولة التغيير بعد فترة التهدئة
            this.hysteresis.pendingChange = {
                mode: proposedMode,
                reason: `pressure-${pressure}`,
                pressureValue
            };

            setTimeout(() => this.applyPendingChange(), this.hysteresis.cooldownPeriod);
        }
    }

    /* ========================================================
       EXECUTE MODE CHANGE (تنفيذ تغيير الوضع)
    ======================================================== */

    executeModeChange(mode, reason, pressureValue = 0) {

        switch (mode) {

            case 'critical':

                this.activateCriticalProtection(reason, pressureValue);
                break;

            case 'degraded':

                this.activateDegradedMode(reason, pressureValue);
                break;

            case 'elevated':

                this.activateElevatedMode(reason, pressureValue);
                break;

            case 'balanced':

                this.activateBalancedMode(reason, pressureValue);
                break;

            case 'recovery':

                this.activateRecoveryMode(reason, pressureValue);
                break;
        }

        this.hysteresis.lastModeChange = Date.now();
    }

    /* ========================================================
       HEALTH
    ======================================================== */

    handleHealth(payload = {}) {

        const health =
            payload.health || 100;

        if (health <= 25) {

            this.executeModeChange('critical', 'critical-health', 95);
            return;
        }

        if (health <= 55) {

            this.executeModeChange('degraded', 'health-degradation', 70);
            return;
        }

        if (health >= 85 && this.mode === 'degraded') {

            this.executeModeChange('recovery', 'health-recovered', 30);
        }
    }

    /* ========================================================
       TELEMETRY OBSERVER
    ======================================================== */

    observeTelemetry(entry = {}) {

        if (entry.type === 'pressure-transition') {

            this.recordHistory({

                type: 'pressure-event',

                payload: entry.payload,

                pressureValue: this.getPressureValue(entry.payload.pressure)
            });
        }

        if (entry.type === 'anomaly_detected') {

            // الاستجابة للشذوذات بشكل استباقي
            if (entry.payload.type === 'rapid_health_drop') {

                this.executeModeChange('degraded', 'anomaly-rapid-health-drop', 75);
            }
        }
    }

    getPressureValue(pressure) {

        switch (pressure) {
            case 'low': return 10;
            case 'moderate': return 35;
            case 'high': return 65;
            case 'extreme': return 90;
            default: return 0;
        }
    }

    /* ========================================================
       RUNTIME EVALUATION (محسن)
    ======================================================== */

    evaluateRuntimePressure() {

        const telemetry =
            window.SOVEREIGN_FLOW_TELEMETRY
                ?.getStatus?.();

        const system =
            window.SOVEREIGN_SYSTEM_STATE
                ?.getStatus?.();

        if (!telemetry || !system) return;

        const anomalyCount = telemetry.anomalies?.totalDetected || 0;
        const recentAnomalies = anomalyCount - (this._lastAnomalyCount || 0);

        this._lastAnomalyCount = anomalyCount;

        /* =========================================
           INSTABILITY مع مراعاة التدرج
        ========================================= */

        if (telemetry.stability < 30) {

            this.executeModeChange('critical', 'runtime-severe-instability', 95);
            return;
        }

        if (telemetry.stability < 50) {

            this.executeModeChange('degraded', 'runtime-instability', 75);
            return;
        }

        if (telemetry.stability < 70 && system.pressure !== 'low') {

            this.executeModeChange('elevated', 'runtime-moderate-instability', 50);
            return;
        }

        /* =========================================
           SAFE RECOVERY (محسن)
        ========================================= */

        if (telemetry.stability > 85 &&
            system.health > 70 &&
            (system.mode === 'degraded' || system.mode === 'critical')) {

            this.executeModeChange('recovery', 'runtime-stabilized', 20);
            return;
        }

        /* =========================================
           الاستجابة للشذوذات الحديثة
        ========================================= */

        if (recentAnomalies >= 2 && this.mode !== 'critical') {

            this.executeModeChange('degraded', 'recent-anomalies-detected', 70);
        }
    }

    /* ========================================================
       BALANCED
    ======================================================== */

    activateBalancedMode(reason, pressureValue = 0) {

        this.mode = 'balanced';
        this.level = 'normal';
        this.recoveryMode = false;

        // تخفيف حدود التدهور
        this.degradationCeiling.currentDegradation = Math.max(
            0,
            this.degradationCeiling.currentDegradation - 10
        );

        this.updateSystemState({

            mode: 'normal',
            throttled: false,
            cinematicEffects: true,
            queueProtection: false
        });

        this.recordDecision('balanced', reason, pressureValue);
    }

    /* ========================================================
       ELEVATED
    ======================================================== */

    activateElevatedMode(reason, pressureValue = 0) {

        this.mode = 'elevated';
        this.level = 'elevated';

        this.updateSystemState({

            mode: 'elevated',
            throttled: false,
            cinematicEffects: true,
            queueProtection: false
        });

        this.recordDecision('elevated', reason, pressureValue);
    }

    /* ========================================================
       DEGRADED (محسن مع حدود التدهور)
    ======================================================== */

    activateDegradedMode(reason, pressureValue = 0) {

        this.mode = 'degraded';
        this.level = 'high-pressure';

        // تحديث حدود التدهور (لا نتدهور أكثر من المسموح)
        this.degradationCeiling.currentDegradation = Math.min(
            this.degradationCeiling.maxDegradationLevel,
            this.degradationCeiling.currentDegradation + 15
        );

        this.metrics.degradations++;
        this.metrics.throttles++;

        this.updateSystemState({

            mode: 'degraded',
            throttled: true,
            cinematicEffects: false,
            queueProtection: true
        });

        this.recordDecision('degraded', reason, pressureValue);
        this.applyVisualProtection();
    }

    /* ========================================================
       CRITICAL (محسن)
    ======================================================== */

    activateCriticalProtection(reason, pressureValue = 0) {

        this.mode = 'critical';
        this.level = 'critical-pressure';

        this.degradationCeiling.currentDegradation = this.degradationCeiling.maxDegradationLevel;

        this.metrics.escalations++;
        this.metrics.throttles++;
        this.metrics.cinematicSuppressions++;

        this.updateSystemState({

            mode: 'critical',
            throttled: true,
            safeMode: true,
            cinematicEffects: false,
            queueProtection: true
        });

        this.recordDecision('critical', reason, pressureValue);
        this.applyCriticalProtection();
    }

    /* ========================================================
       RECOVERY (محسن)
    ======================================================== */

    activateRecoveryMode(reason, pressureValue = 0) {

        this.mode = 'recovery';
        this.level = 'recovery';
        this.recoveryMode = true;

        // تخفيف حدود التدهور تدريجياً
        this.degradationCeiling.currentDegradation = Math.max(
            0,
            this.degradationCeiling.currentDegradation - 25
        );

        this.metrics.recoveries++;

        this.updateSystemState({

            mode: 'normal',
            throttled: false,
            safeMode: false,
            cinematicEffects: true,
            queueProtection: false
        });

        this.recordDecision('recovery', reason, pressureValue);
        this.applyRecoveryEffects();

        // إعادة تعيين مؤقت التهدئة للتغييرات القادمة
        setTimeout(() => {
            this.recoveryMode = false;
        }, 5000);
    }

    /* ========================================================
       SYSTEM STATE
    ======================================================== */

    updateSystemState({

        mode,

        throttled,

        safeMode,

        cinematicEffects,

        queueProtection
    }) {

        const system =
            window.SOVEREIGN_SYSTEM_STATE;

        if (!system) return;

        if (mode && typeof system.setMode === 'function') {
            system.setMode(mode, 'pressure-governor');
        }

        if (throttled !== undefined && typeof system.setFlag === 'function') {
            system.setFlag('throttled', throttled);
        }

        if (safeMode !== undefined && typeof system.setFlag === 'function') {
            system.setFlag('safeMode', safeMode);
        }

        if (cinematicEffects !== undefined && typeof system.setFlag === 'function') {
            system.setFlag('cinematicEffects', cinematicEffects);
        }

        if (queueProtection !== undefined && typeof system.setFlag === 'function') {
            system.setFlag('queueProtection', queueProtection);
        }
    }

    /* ========================================================
       VISUAL PROTECTION (محسن)
    ======================================================== */

    applyVisualProtection() {

        if (typeof document === 'undefined') return;

        document.body.classList.add('runtime-protected');
        document.body.classList.remove('runtime-cinematic');
        document.body.dataset.governorMode = this.mode;
    }

    /* ========================================================
       CRITICAL VISUALS (محسن)
    ======================================================== */

    applyCriticalProtection() {

        if (typeof document === 'undefined') return;

        document.body.classList.add('runtime-critical');
        document.body.classList.remove('runtime-cinematic');
        document.body.classList.add('runtime-safe');
        document.body.dataset.governorMode = 'critical';
    }

    /* ========================================================
       RECOVERY (محسن)
    ======================================================== */

    applyRecoveryEffects() {

        if (typeof document === 'undefined') return;

        document.body.classList.remove('runtime-critical');
        document.body.classList.remove('runtime-safe');
        document.body.classList.add('runtime-recovery');
        document.body.dataset.governorMode = 'recovery';

        setTimeout(() => {

            if (typeof document !== 'undefined') {
                document.body.classList.remove('runtime-recovery');
            }

        }, 4000);
    }

    /* ========================================================
       DECISIONS (محسن)
    ======================================================== */

    recordDecision(mode, reason, pressureValue = 0) {

        this.lastDecision = {
            mode,
            reason,
            pressureValue,
            timestamp: Date.now()
        };

        this.recordHistory({
            type: 'governor-decision',
            mode,
            reason,
            pressureValue
        });

        console.log(`⚖️ Runtime Governor | MODE: ${mode} | REASON: ${reason} | PRESSURE: ${pressureValue}`);

        this.publishDecision();
    }

    /* ========================================================
       HISTORY
    ======================================================== */

    recordHistory(entry = {}) {

        this.history.push({
            ...entry,
            timestamp: Date.now()
        });

        if (this.history.length > this.maxHistory) {
            this.history.shift();
        }
    }

    /* ========================================================
       PUBLISH
    ======================================================== */

    publishDecision() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:governor:decision', {
                mode: this.mode,
                level: this.level,
                decision: this.lastDecision,
                metrics: this.metrics,
                degradationCeiling: this.degradationCeiling.currentDegradation,
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

            bus.publishWithoutMiddleware('runtime-pressure-governor:ready', {
                mode: this.mode,
                hysteresisEnabled: this.hysteresis.enabled,
                adaptivePolicies: true,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        return {
            mode: this.mode,
            level: this.level,
            stabilization: this.stabilizationEnabled,
            recovery: this.recoveryMode,
            metrics: { ...this.metrics },
            history: this.history.length,
            lastDecision: this.lastDecision,
            hysteresis: {
                enabled: this.hysteresis.enabled,
                lastModeChange: this.hysteresis.lastModeChange,
                pendingChange: this.hysteresis.pendingChange
            },
            degradationCeiling: {
                current: this.degradationCeiling.currentDegradation,
                max: this.degradationCeiling.maxDegradationLevel
            },
            policies: {
                aggressive: this.policies.aggressive,
                conservative: this.policies.conservative,
                learnedThresholds: this.policies.learnedThresholds
            }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._governorInterval) {
            clearInterval(this._governorInterval);
            this._governorInterval = null;
        }

        if (this._learningInterval) {
            clearInterval(this._learningInterval);
            this._learningInterval = null;
        }

        console.log('⚖️ Runtime Pressure Governor Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignPressureGovernor =
    new SovereignRuntimePressureGovernor();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_PRESSURE_GOVERNOR =
    sovereignPressureGovernor;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register(
        'pressure-governor',
        sovereignPressureGovernor
    );
}
