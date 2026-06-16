/* ============================================================
   Sovereign AI — runtime-adaptive-scheduler.js
   الإصدار: 8.1.0 (Runtime Self-Regulation Infrastructure)
   
   المجدول التكيفي السيادي - Adaptive Runtime Intelligence
   
   الوظيفة:
     - Runtime Pressure Detection (ضغط التنفيذ)
     - Adaptive Concurrency Scaling (توسعة متزامنة)
     - Degraded Runtime Modes (أوضاع التشغيل المتدهورة)
     - Runtime Load Awareness (الوعي بالحمل)
     - Self-Regulating Execution (التنظيم الذاتي)
     - Backpressure Signaling (إشارات الضغط الخلفي)
   
   التقسيم المستقبلي (Runtime Autonomic Control Engine):
     - PressureAnalyzer (تحليل الضغط مع Adaptive Weighting)
     - AdaptivePolicyEngine (قرارات التكيف)
     - ConcurrencyScaler (توسعة التوازي)
     - PacingController (التحكم في الإيقاع)
     - DegradationEngine (أوضاع التدهور)
     - RuntimeRegulator (التنظيم العام)
   
   المرحلة القادمة (Runtime Backpressure Engine):
     - Queue Overload Handling
     - Runtime Pacing
     - Execution Pressure Draining
     - Adaptive Throttling
     - Overload Protection
     - Runtime Flow Stabilization
   ============================================================ */

class SovereignRuntimeAdaptiveScheduler {

    constructor() {

        this.mode = 'normal';
        this.pressure = 0;
        this.maxPressure = 100;

        // ✅ FIX 2: Hysteresis thresholds (منع التبديل السريع)
        this.thresholds = {
            normal: { up: 30, down: 20 },
            elevated: { up: 60, down: 25 },
            degraded: { up: 85, down: 50 },
            critical: { up: 100, down: 70 }
        };

        // ✅ FIX 1: Adaptive Pressure Weights (قابلة للتعديل ديناميكياً)
        this.weightConfig = {
            queuedMultiplier: 2,
            activeMultiplier: 5,
            executionTimeDivider: 10,
            queueGrowthMultiplier: 3,
            failureRateMultiplier: 4
        };

        // ✅ FIX 3: Rolling metrics for pressure calculation
        this.metricsHistory = [];
        this.maxHistorySize = 10;
        this.previousQueueSize = 0;
        this.previousFailureCount = 0;

        // Cooldown to prevent rapid mode changes
        this.lastModeChangeAt = 0;
        this.cooldownMs = 5000;  // 5 seconds cooldown

        // Backpressure signals
        this.backpressureActive = false;
        this.backpressureLevel = 0;

        console.log(
            '🧠 Adaptive Runtime Scheduler Initialized (Self-Regulation Active)'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.startMonitoring();
        this.publishReady();
    }

    /* ========================================================
       MONITORING LOOP
    ======================================================== */
    startMonitoring() {
        setInterval(() => {
            this.evaluateRuntime();
        }, 3000);
    }

    /* ========================================================
       GET EXECUTION SCHEDULER (with fallback)
    ======================================================== */
    getExecutionScheduler() {
        return window.SOVEREIGN_ACCESS?.legacy?.('execution_scheduler') ||
               window.SOVEREIGN_EXECUTION_SCHEDULER;
    }

    /* ========================================================
       GET ANALYTICS (with fallback)
    ======================================================== */
    getAnalytics() {
        return window.SOVEREIGN_ACCESS?.legacy?.('analytics') ||
               window.SOVEREIGN_ANALYTICS;
    }

    /* ========================================================
       GET SANDBOX (for violation metrics)
    ======================================================== */
    getSandbox() {
        return window.SOVEREIGN_ACCESS?.legacy?.('sandbox') ||
               window.SOVEREIGN_SANDBOX;
    }

    /* ========================================================
       CALCULATE QUEUE GROWTH RATE
       
       Measures how fast the queue is growing (backpressure indicator)
    ======================================================== */
    calculateQueueGrowthRate(currentQueueSize) {
        const growthRate = currentQueueSize - this.previousQueueSize;
        this.previousQueueSize = currentQueueSize;
        return Math.max(0, growthRate);
    }

    /* ========================================================
       CALCULATE FAILURE RATE
    ======================================================== */
    calculateFailureRate(schedulerStatus) {
        const total = schedulerStatus?.telemetry?.tasksScheduled || 1;
        const failed = schedulerStatus?.telemetry?.tasksFailed || 0;
        return (failed / total) * 100;
    }

    /* ========================================================
       UPDATE ROLLING METRICS
    ======================================================== */
    updateRollingMetrics(pressure) {
        this.metricsHistory.push({
            timestamp: Date.now(),
            pressure: pressure,
            mode: this.mode
        });

        if (this.metricsHistory.length > this.maxHistorySize) {
            this.metricsHistory.shift();
        }
    }

    /* ========================================================
       GET ROLLING AVERAGE PRESSURE
       
       ✅ FIX 1: Uses historical data for smoother pressure calculation
    ======================================================== */
    getRollingAveragePressure() {
        if (this.metricsHistory.length === 0) return this.pressure;
        const sum = this.metricsHistory.reduce((acc, m) => acc + m.pressure, 0);
        return sum / this.metricsHistory.length;
    }

    /* ========================================================
       EVALUATE RUNTIME PRESSURE (Adaptive Pressure Model)
       
       ✅ FIX 1: Dynamic pressure calculation with configurable weights
    ======================================================== */
    evaluateRuntime() {
        const scheduler = this.getExecutionScheduler();
        const analytics = this.getAnalytics();
        const sandbox = this.getSandbox();

        if (!scheduler) {
            console.warn('⚠️ Adaptive Scheduler: Execution Scheduler not available');
            return;
        }

        const status = scheduler.getStatus?.();
        const queued = status?.queued || 0;
        const active = status?.active || 0;
        const avgExecution = status?.telemetry?.averageExecutionTimeMs || 0;

        // ✅ FIX 1: Queue growth rate (backpressure)
        const queueGrowthRate = this.calculateQueueGrowthRate(queued);
        
        // ✅ FIX 1: Failure rate
        const failureRate = this.calculateFailureRate(status);
        
        // ✅ FIX 1: Sandbox violations (if available)
        const sandboxStatus = sandbox?.getStatus?.();
        const violations = sandboxStatus?.list?.reduce((sum, s) => sum + (s.metrics?.violations || 0), 0) || 0;

        // Dynamic pressure calculation with configurable weights
        let pressure = 0;
        pressure += queued * this.weightConfig.queuedMultiplier;
        pressure += active * this.weightConfig.activeMultiplier;
        pressure += avgExecution / this.weightConfig.executionTimeDivider;
        pressure += queueGrowthRate * this.weightConfig.queueGrowthMultiplier;
        pressure += (violations / 10) * this.weightConfig.failureRateMultiplier;
        pressure += failureRate * 0.5;

        this.pressure = Math.min(pressure, this.maxPressure);
        
        // Update rolling metrics
        this.updateRollingMetrics(this.pressure);
        
        // Calculate backpressure level (0-100)
        this.backpressureLevel = Math.min(100, (queued / 50) * 100);
        this.backpressureActive = this.backpressureLevel > 30;

        this.evaluateMode();
    }

    /* ========================================================
       EVALUATE MODE (مع Hysteresis)
       
       ✅ FIX 2: Hysteresis prevents rapid oscillation
    ======================================================== */
    evaluateMode() {
        const now = Date.now();
        const rollingPressure = this.getRollingAveragePressure();
        
        // Use rolling pressure for smoother transitions
        const effectivePressure = rollingPressure;
        
        let next = this.mode;
        const hysteresis = this.thresholds[this.mode];
        
        if (hysteresis) {
            if (this.mode === 'normal') {
                if (effectivePressure > hysteresis.up) next = 'elevated';
            } else if (this.mode === 'elevated') {
                if (effectivePressure > hysteresis.up) next = 'degraded';
                else if (effectivePressure < hysteresis.down) next = 'normal';
            } else if (this.mode === 'degraded') {
                if (effectivePressure > hysteresis.up) next = 'critical';
                else if (effectivePressure < hysteresis.down) next = 'elevated';
            } else if (this.mode === 'critical') {
                if (effectivePressure < hysteresis.down) next = 'degraded';
            }
        } else {
            // Fallback to simple thresholds
            if (effectivePressure > 85) next = 'critical';
            else if (effectivePressure > 60) next = 'degraded';
            else if (effectivePressure > 30) next = 'elevated';
            else next = 'normal';
        }
        
        // Check cooldown to prevent rapid changes
        const timeSinceLastChange = now - this.lastModeChangeAt;
        if (next !== this.mode && timeSinceLastChange >= this.cooldownMs) {
            this.transition(next);
        } else if (next !== this.mode) {
            console.debug(`⏸️ Mode transition throttled (cooldown): ${this.mode} → ${next}`);
        }
    }

    /* ========================================================
       TRANSITION MODE
    ======================================================== */
    transition(mode) {
        const previous = this.mode;
        this.mode = mode;
        this.lastModeChangeAt = Date.now();

        console.warn(`
🧠 Runtime Scheduling Mode Changed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Previous: ${previous}
Current:  ${mode}
Pressure: ${this.pressure.toFixed(2)}
Backpressure: ${this.backpressureLevel.toFixed(2)}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        `);

        this.applyAdaptation(mode);
        this.publishTransition(previous, mode);
    }

    /* ========================================================
       APPLY ADAPTATION (Adaptive Policies)
       
       ✅ FIX 4: Dynamic concurrency scaling based on mode
    ======================================================== */
    applyAdaptation(mode) {
        const scheduler = this.getExecutionScheduler();

        if (!scheduler) {
            console.warn('⚠️ Adaptive Scheduler: Cannot apply adaptation - scheduler not available');
            return;
        }

        let newMaxConcurrent;
        let newBackpressureThreshold;

        switch (mode) {
            case 'critical':
                newMaxConcurrent = 2;
                newBackpressureThreshold = 10;
                this.emitBackpressureEvent(true, 'critical');
                break;
            case 'degraded':
                newMaxConcurrent = 3;
                newBackpressureThreshold = 20;
                this.emitBackpressureEvent(true, 'degraded');
                break;
            case 'elevated':
                newMaxConcurrent = 4;
                newBackpressureThreshold = 30;
                this.emitBackpressureEvent(false, null);
                break;
            case 'normal':
                newMaxConcurrent = 5;
                newBackpressureThreshold = 50;
                this.emitBackpressureEvent(false, null);
                break;
        }

        if (scheduler.setMaxConcurrent) {
            scheduler.setMaxConcurrent(newMaxConcurrent);
            console.log(`📊 Adaptive Scheduler: Max concurrent set to ${newMaxConcurrent} (${mode} mode)`);
        }

        // Update weight config based on mode (adaptive weighting)
        this.updateWeightConfig(mode);
    }

    /* ========================================================
       UPDATE WEIGHT CONFIG (Adaptive Pressure Weights)
       
       ✅ FIX 1: Different weighting based on runtime mode
    ======================================================== */
    updateWeightConfig(mode) {
        switch (mode) {
            case 'critical':
                // Focus on queue growth and failures
                this.weightConfig.queueGrowthMultiplier = 5;
                this.weightConfig.failureRateMultiplier = 6;
                break;
            case 'degraded':
                // Balance between queue and execution time
                this.weightConfig.queueGrowthMultiplier = 4;
                this.weightConfig.failureRateMultiplier = 4;
                break;
            case 'elevated':
                // Normal weighting
                this.weightConfig.queueGrowthMultiplier = 3;
                this.weightConfig.failureRateMultiplier = 3;
                break;
            case 'normal':
                // Standard weighting
                this.weightConfig.queueGrowthMultiplier = 2;
                this.weightConfig.failureRateMultiplier = 2;
                break;
        }
    }

    /* ========================================================
       EMIT BACKPRESSURE EVENT
       
       ✅ NEW: Backpressure signaling for flow control
    ======================================================== */
    emitBackpressureEvent(active, mode) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        
        if (active) {
            bus?.publishWithoutMiddleware?.('runtime:backpressure:active', {
                level: this.backpressureLevel,
                mode: mode,
                pressure: this.pressure,
                timestamp: Date.now()
            });
        } else {
            bus?.publishWithoutMiddleware?.('runtime:backpressure:resolved', {
                mode: this.mode,
                pressure: this.pressure,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       GET BACKPRESSURE STATUS
    ======================================================== */
    getBackpressureStatus() {
        return {
            active: this.backpressureActive,
            level: this.backpressureLevel,
            mode: this.mode
        };
    }

    /* ========================================================
       MANUAL ADAPTATION (Administrative API)
    ======================================================== */
    forceMode(mode) {
        const validModes = ['normal', 'elevated', 'degraded', 'critical'];
        if (!validModes.includes(mode)) {
            console.warn(`⚠️ Invalid mode: ${mode}`);
            return false;
        }
        this.transition(mode);
        return true;
    }

    /* ========================================================
       UPDATE WEIGHT CONFIGURATION (Runtime Tuning)
    ======================================================== */
    updateWeights(newWeights) {
        this.weightConfig = { ...this.weightConfig, ...newWeights };
        console.log('📊 Adaptive Scheduler weights updated:', this.weightConfig);
        return true;
    }

    /* ========================================================
       TRANSITION EVENT
    ======================================================== */
    publishTransition(previous, current) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        bus?.publishWithoutMiddleware?.('scheduler:mode:changed', {
            previous,
            current,
            pressure: this.pressure,
            rollingPressure: this.getRollingAveragePressure(),
            backpressureLevel: this.backpressureLevel,
            timestamp: Date.now()
        });
    }

    /* ========================================================
       READY EVENT
    ======================================================== */
    publishReady() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        bus?.publishWithoutMiddleware?.('adaptive-scheduler:ready', {
            mode: this.mode,
            thresholds: this.thresholds,
            weightConfig: this.weightConfig,
            version: '8.1.0',
            timestamp: Date.now()
        });
    }

    /* ========================================================
       STATUS (مع Telemetry محسّنة)
    ======================================================== */
    getStatus() {
        return {
            mode: this.mode,
            pressure: this.pressure,
            rollingPressure: this.getRollingAveragePressure(),
            maxPressure: this.maxPressure,
            backpressure: this.getBackpressureStatus(),
            thresholds: this.thresholds,
            weightConfig: this.weightConfig,
            cooldownRemaining: Math.max(0, this.cooldownMs - (Date.now() - this.lastModeChangeAt)),
            metricsHistorySize: this.metricsHistory.length,
            timestamp: Date.now()
        };
    }

    /* ========================================================
       RESET METRICS HISTORY
    ======================================================== */
    resetHistory() {
        this.metricsHistory = [];
        console.log('🧹 Adaptive scheduler metrics history reset');
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
============================================================ */

const sovereignAdaptiveScheduler = new SovereignRuntimeAdaptiveScheduler();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_ADAPTIVE_SCHEDULER = sovereignAdaptiveScheduler;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('adaptive-scheduler', sovereignAdaptiveScheduler);
    console.log('✅ Adaptive Scheduler registered in Unified Registry');
} else {
    console.warn('⚠️ Unified Registry not yet available. Adaptive Scheduler registered as legacy global only.');
}

// ============================================================
// إشهار النظام للأنظمة القديمة
// ============================================================
window.SOVEREIGN_EVENTS?.emit('adaptive-scheduler:ready', {
    timestamp: Date.now(),
    status: sovereignAdaptiveScheduler.getStatus()
});
