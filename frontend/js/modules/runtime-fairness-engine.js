/* ============================================================
   Sovereign AI — runtime-fairness-engine.js
   الإصدار: 9.0.0
   محرك العدالة التنفيذية السيادي
   ============================================================ */

class SovereignRuntimeFairnessEngine {

    constructor() {

        /* =========================================
           FAIRNESS
        ========================================= */

        this.starvationThreshold =
            15000;

        this.maxDeferrals =
            5;

        this.fairnessBoost =
            3;

        /* =========================================
           ESCALATION SYSTEM (نظام التصعيد)
        ========================================= */

        this.escalation = {

            enabled: true,
            levels: {
                1: { deferrals: 3, boost: 5 },   // أول تحذير
                2: { deferrals: 6, boost: 10 },  // تصعيد متوسط
                3: { deferrals: 10, boost: 20 }  // تصعيد شديد (تنفيذ فوري)
            },
            activeEscalations: new Map()  // taskId -> escalation level
        };

        /* =========================================
           STARVATION MEMORY (ذاكرة الجوع)
        ========================================= */

        this.starvationMemory = {

            history: [],           // تاريخ المهام التي عانت من الجوع
            patterns: new Map(),   // أنماط الجوع المتكررة
            maxMemory: 100
        };

        /* =========================================
           CHANNEL FAIRNESS (توازن القنوات)
        ========================================= */

        this.channelFairness = {

            enabled: true,
            weights: new Map(),     // كل قناة لها وزن تنفيذي
            executionCounts: new Map(),  // عدد مرات تنفيذ كل قناة
            targetBalance: 0.3,    // تفاوت أقصى 30% بين القنوات
            adjustments: new Map()
        };

        /* =========================================
           DEFERRAL LOOP DETECTION (كشف حلقات التأجيل)
        ========================================= */

        this.loopDetection = {

            enabled: true,
            windows: new Map(),      // taskId -> window of deferral times
            maxWindowSize: 10,
            threshold: 3             // 3 تأجيلات في دقيقة واحدة = حلقة
        };

        /* =========================================
           TRACKING
        ========================================= */

        this.deferredTasks =
            new Map();

        this.executionHistory =
            [];

        this.maxHistory =
            300;

        /* =========================================
           CRITICAL CHANNELS
        ========================================= */

        this.criticalChannels =
            new Set([

                'runtime:errors',

                'scheduler:task:failed',

                'sandbox:violation',

                'kernel:heartbeat'
            ]);

        /* =========================================
           METRICS (محسن)
        ========================================= */

        this.metrics = {

            starvationPreventions:
                0,

            fairnessBoosts:
                0,

            deferredExecutions:
                0,

            forcedExecutions:
                0,

            protectedCriticalTasks:
                0,

            escalationsTriggered: 0,
            loopsDetected: 0,
            channelRebalances: 0,
            starvationPatternsDetected: 0
        };

        console.log('⚖️ Runtime Fairness Engine Initialized (Sovereign Justice Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindSchedulerSignals();
        this.bindPressureSignals();
        this.startStarvationMemoryCleanup();
        this.startLoopDetectionSweep();
        this.publishReady();
    }

    /* ========================================================
       SCHEDULER
    ======================================================== */

    bindSchedulerSignals() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('scheduler:task:executed', payload => {
            this.recordExecution(payload);
            this.updateChannelBalance(payload);
        });

        bus.subscribe('scheduler:task:deferred', payload => {
            this.trackDeferral(payload);
            this.detectDeferralLoop(payload);
        });
    }

    /* ========================================================
       PRESSURE SIGNALS (للسياسات التكيفية)
    ======================================================== */

    bindPressureSignals() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:pressure:changed', payload => {
            this.adaptFairnessToPressure(payload);
        });
    }

    /* ========================================================
       ADAPTIVE FAIRNESS (سياسات تكيفية)
    ======================================================== */

    adaptFairnessToPressure(payload) {

        const pressure = payload.pressure;

        switch (pressure) {
            case 'extreme':
                // في الضغط الشديد، نزيد العدالة للمهام الحرجة
                this.fairnessBoost = 5;
                this.starvationThreshold = 8000;  // نخفض العتبة
                break;

            case 'high':
                this.fairnessBoost = 4;
                this.starvationThreshold = 10000;
                break;

            case 'moderate':
                this.fairnessBoost = 3;
                this.starvationThreshold = 15000;
                break;

            default:
                this.fairnessBoost = 2;
                this.starvationThreshold = 20000;
        }

        this.publishFairnessUpdate('pressure_adaptation', { pressure, fairnessBoost: this.fairnessBoost });
    }

    /* ========================================================
       ESCALATION SYSTEM (نظام التصعيد)
    ======================================================== */

    checkAndEscalate(task) {

        if (!this.escalation.enabled) return false;

        const deferCount = task.deferCount || 0;
        let escalationLevel = 0;

        for (const [level, config] of Object.entries(this.escalation.levels)) {
            if (deferCount >= config.deferrals) {
                escalationLevel = parseInt(level);
            }
        }

        if (escalationLevel > 0) {

            const currentLevel = this.escalation.activeEscalations.get(task.id) || 0;

            if (escalationLevel > currentLevel) {

                this.escalation.activeEscalations.set(task.id, escalationLevel);
                this.metrics.escalationsTriggered++;

                console.log(`⚖️ Task ${task.id} escalated to level ${escalationLevel} (deferrals: ${deferCount})`);

                // تطبيق التصعيد على أولوية المهمة
                if (escalationLevel >= 3) {
                    // تصعيد شديد: تنفيذ فوري
                    task.forceExecute = true;
                }

                this.publishEscalation(task, escalationLevel);
                return true;
            }
        }

        return false;
    }

    /* ========================================================
       DEFERRAL LOOP DETECTION (كشف حلقات التأجيل)
    ======================================================== */

    detectDeferralLoop(payload) {

        if (!this.loopDetection.enabled) return;

        const taskId = payload.taskId;
        const now = Date.now();

        if (!this.loopDetection.windows.has(taskId)) {
            this.loopDetection.windows.set(taskId, []);
        }

        const window = this.loopDetection.windows.get(taskId);
        window.push(now);

        // الاحتفاظ بآخر N من التأجيلات
        while (window.length > this.loopDetection.maxWindowSize) {
            window.shift();
        }

        // كشف الحلقة: X تأجيلات في دقيقة واحدة
        const oneMinuteAgo = now - 60000;
        const recentDeferrals = window.filter(t => t > oneMinuteAgo);

        if (recentDeferrals.length >= this.loopDetection.threshold) {

            this.metrics.loopsDetected++;

            console.warn(`⚠️ Deferral loop detected for task ${taskId}: ${recentDeferrals.length} deferrals in last minute`);

            this.publishLoopDetected(taskId, recentDeferrals.length);

            // كسر الحلقة: إجبار التنفيذ
            this.forceBreakLoop(taskId);
        }
    }

    forceBreakLoop(taskId) {

        // نشر حدث لكسر الحلقة
        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:fairness:break-loop', {
                taskId,
                action: 'force_execution',
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       CHANNEL FAIRNESS (توازن القنوات)
    ======================================================== */

    updateChannelBalance(payload) {

        if (!this.channelFairness.enabled) return;

        const channel = payload.metadata?.channel || 'default';

        const currentCount = this.channelFairness.executionCounts.get(channel) || 0;
        this.channelFairness.executionCounts.set(channel, currentCount + 1);

        // إعادة التوازن كل 100 تنفيذ
        const totalExecutions = Array.from(this.channelFairness.executionCounts.values()).reduce((a, b) => a + b, 0);

        if (totalExecutions > 0 && totalExecutions % 100 === 0) {
            this.rebalanceChannels();
        }
    }

    rebalanceChannels() {

        const counts = this.channelFairness.executionCounts;
        if (counts.size === 0) return;

        const values = Array.from(counts.values());
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const maxDeviation = Math.max(...values.map(v => Math.abs(v - avg) / avg)) || 0;

        if (maxDeviation > this.channelFairness.targetBalance) {

            this.metrics.channelRebalances++;

            // إعادة حساب الأوزان
            for (const [channel, count] of counts) {
                const deviation = count / avg;
                let weight = 1;

                if (deviation > 1.3) {
                    weight = 0.7;  // قناة مستهلكة كثيراً → تقليل وزنها
                } else if (deviation < 0.7) {
                    weight = 1.3;  // قناة مهملة → زيادة وزنها
                }

                this.channelFairness.weights.set(channel, weight);
            }

            this.publishFairnessUpdate('channel_rebalance', { deviation: maxDeviation, weights: Array.from(this.channelFairness.weights.entries()) });
        }
    }

    getChannelWeight(channel) {

        if (!this.channelFairness.enabled) return 1;
        return this.channelFairness.weights.get(channel) || 1;
    }

    /* ========================================================
       STARVATION MEMORY (ذاكرة الجوع)
    ======================================================== */

    recordStarvationEvent(task) {

        const event = {
            taskId: task.id,
            taskType: task.type,
            channel: task.metadata?.channel,
            deferrals: task.deferCount,
            waitingTime: Date.now() - (task.createdAt || Date.now()),
            timestamp: Date.now()
        };

        this.starvationMemory.history.push(event);

        if (this.starvationMemory.history.length > this.starvationMemory.maxMemory) {
            this.starvationMemory.history.shift();
        }

        // كشف الأنماط
        const patternKey = `${event.taskType}:${event.channel}`;
        const pattern = this.starvationMemory.patterns.get(patternKey) || { count: 0, totalDeferrals: 0 };
        pattern.count++;
        pattern.totalDeferrals += event.deferrals;
        this.starvationMemory.patterns.set(patternKey, pattern);

        if (pattern.count >= 3 && pattern.totalDeferrals / pattern.count > 3) {
            this.metrics.starvationPatternsDetected++;
            this.publishStarvationPattern(patternKey, pattern);
        }
    }

    startStarvationMemoryCleanup() {

        setInterval(() => {
            // تنظيف الذاكرة القديمة (أكثر من 10 دقائق)
            const tenMinutesAgo = Date.now() - 600000;
            this.starvationMemory.history = this.starvationMemory.history.filter(e => e.timestamp > tenMinutesAgo);
        }, 120000);
    }

    startLoopDetectionSweep() {

        setInterval(() => {
            // تنظيف نوافذ الكشف القديمة
            const fiveMinutesAgo = Date.now() - 300000;
            for (const [taskId, window] of this.loopDetection.windows) {
                const filtered = window.filter(t => t > fiveMinutesAgo);
                if (filtered.length === 0) {
                    this.loopDetection.windows.delete(taskId);
                } else {
                    this.loopDetection.windows.set(taskId, filtered);
                }
            }
        }, 60000);
    }

    /* ========================================================
       PRIORITY (محسن مع التصعيد وتوازن القنوات)
    ======================================================== */

    calculateFairPriority(task = {}) {

        let priority = task.priority || 10;

        const waitingTime = Date.now() - (task.createdAt || Date.now());

        /* =========================================
           STARVATION BOOST
        ========================================= */

        if (waitingTime > this.starvationThreshold) {

            const boostMultiplier = Math.floor(waitingTime / this.starvationThreshold);
            priority -= this.fairnessBoost * Math.min(boostMultiplier, 3);

            this.metrics.starvationPreventions++;
            this.metrics.fairnessBoosts++;

            this.recordStarvationEvent(task);
        }

        /* =========================================
           ESCALATION BOOST (من نظام التصعيد)
        ========================================= */

        const escalationLevel = this.escalation.activeEscalations.get(task.id) || 0;
        if (escalationLevel > 0) {
            const escalationConfig = this.escalation.levels[escalationLevel];
            if (escalationConfig) {
                priority -= escalationConfig.boost;
            }
        }

        /* =========================================
           CRITICAL CHANNELS
        ========================================= */

        const channel = task.metadata?.channel;

        if (this.criticalChannels.has(channel)) {
            priority = 0;
            this.metrics.protectedCriticalTasks++;
        }

        /* =========================================
           CHANNEL FAIRNESS WEIGHT
        ========================================= */

        const channelWeight = this.getChannelWeight(channel);
        if (channelWeight !== 1 && priority > 0) {
            priority = priority * (1 / channelWeight);
        }

        /* =========================================
           FORCED EXECUTION (منع الحلقات)
        ========================================= */

        if (task.forceExecute || task.deferCount > this.maxDeferrals) {
            priority = 0;
            this.metrics.forcedExecutions++;
        }

        return Math.max(priority, 0);
    }

    /* ========================================================
       SORT (محسن)
    ======================================================== */

    sortQueue(queue = []) {

        // تحديث التصعيدات قبل الفرز
        for (const task of queue) {
            this.checkAndEscalate(task);
        }

        return queue.sort((a, b) =>
            this.calculateFairPriority(a) - this.calculateFairPriority(b)
        );
    }

    /* ========================================================
       SHOULD DEFER (محسن)
    ======================================================== */

    shouldDefer(task = {}) {

        const system = window.SOVEREIGN_SYSTEM_STATE?.getStatus?.();

        if (!system) return false;

        const channel = task.metadata?.channel;

        // Critical bypass
        if (this.criticalChannels.has(channel)) return false;

        // Forced execution (من التصعيد أو الحلقات)
        if (task.forceExecute || task.deferCount >= this.maxDeferrals) return false;

        // Critical mode
        if (system.mode === 'critical') {
            return task.priority > 4;
        }

        // Degraded mode
        if (system.mode === 'degraded') {
            return task.priority > 7;
        }

        // Elevated mode
        if (system.mode === 'elevated') {
            return task.priority > 9;
        }

        return false;
    }

    /* ========================================================
       DEFERRAL (محسن)
    ======================================================== */

    applyDeferral(task = {}) {

        task.deferCount = (task.deferCount || 0) + 1;
        task.deferredAt = Date.now();

        this.metrics.deferredExecutions++;

        this.deferredTasks.set(task.id, {
            count: task.deferCount,
            timestamp: task.deferredAt,
            priority: task.priority
        });

        // التحقق من التصعيد بعد كل تأجيل
        this.checkAndEscalate(task);

        this.publishDeferral(task);

        return task;
    }

    /* ========================================================
       EXECUTION
    ======================================================== */

    recordExecution(payload = {}) {

        // تنظيف المهام المنفذة من التتبع
        if (payload.taskId) {
            this.deferredTasks.delete(payload.taskId);
            this.escalation.activeEscalations.delete(payload.taskId);
            this.loopDetection.windows.delete(payload.taskId);
        }

        this.executionHistory.push({
            type: 'execution',
            payload,
            timestamp: Date.now()
        });

        if (this.executionHistory.length > this.maxHistory) {
            this.executionHistory.shift();
        }
    }

    /* ========================================================
       TRACK DEFERRAL
    ======================================================== */

    trackDeferral(payload = {}) {

        this.executionHistory.push({
            type: 'deferral',
            payload,
            timestamp: Date.now()
        });

        if (this.executionHistory.length > this.maxHistory) {
            this.executionHistory.shift();
        }
    }

    /* ========================================================
       FAIRNESS SCORE (محسن)
    ======================================================== */

    calculateFairnessScore() {

        let score = 100;

        const deferred = this.metrics.deferredExecutions;
        const starvation = this.metrics.starvationPreventions;
        const loops = this.metrics.loopsDetected;
        const imbalances = this.metrics.channelRebalances;

        // Excessive deferrals
        if (deferred > 50) score -= 25;
        else if (deferred > 30) score -= 10;

        // Starvation events
        if (starvation > 20) score -= 15;
        else if (starvation > 10) score -= 5;

        // Loops detected (خطيرة)
        if (loops > 5) score -= 30;
        else if (loops > 0) score -= 10;

        // Channel imbalances
        if (imbalances > 10) score -= 10;

        // Bonus: good channel balance
        if (imbalances === 0 && this.channelFairness.executionCounts.size > 1) {
            score += 5;
        }

        return Math.max(score, 0);
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishDeferral(task) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:fairness:deferral', {
                taskId: task.id,
                deferCount: task.deferCount,
                priority: task.priority,
                escalationLevel: this.escalation.activeEscalations.get(task.id) || 0,
                timestamp: Date.now()
            });
        }
    }

    publishEscalation(task, level) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:fairness:escalation', {
                taskId: task.id,
                level,
                deferrals: task.deferCount,
                timestamp: Date.now()
            });
        }
    }

    publishLoopDetected(taskId, frequency) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:fairness:loop-detected', {
                taskId,
                frequency,
                action: 'force_execution_scheduled',
                timestamp: Date.now()
            });
        }
    }

    publishStarvationPattern(patternKey, pattern) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:fairness:starvation-pattern', {
                pattern: patternKey,
                occurrences: pattern.count,
                avgDeferrals: pattern.totalDeferrals / pattern.count,
                timestamp: Date.now()
            });
        }
    }

    publishFairnessUpdate(type, data) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:fairness:update', {
                type,
                data,
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

            bus.publishWithoutMiddleware('runtime-fairness-engine:ready', {
                threshold: this.starvationThreshold,
                maxDeferrals: this.maxDeferrals,
                escalationEnabled: this.escalation.enabled,
                loopDetectionEnabled: this.loopDetection.enabled,
                channelFairnessEnabled: this.channelFairness.enabled,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        return {
            fairnessScore: this.calculateFairnessScore(),
            deferred: this.deferredTasks.size,
            history: this.executionHistory.length,
            criticalChannels: this.criticalChannels.size,
            metrics: { ...this.metrics },
            escalation: {
                enabled: this.escalation.enabled,
                active: this.escalation.activeEscalations.size
            },
            loops: {
                detected: this.metrics.loopsDetected,
                activeWindows: this.loopDetection.windows.size
            },
            channelFairness: {
                enabled: this.channelFairness.enabled,
                channels: this.channelFairness.executionCounts.size,
                rebalances: this.metrics.channelRebalances
            },
            starvationMemory: {
                historySize: this.starvationMemory.history.length,
                patterns: this.starvationMemory.patterns.size
            }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        this.deferredTasks.clear();
        this.escalation.activeEscalations.clear();
        this.loopDetection.windows.clear();
        this.starvationMemory.history = [];
        this.starvationMemory.patterns.clear();

        console.log('⚖️ Runtime Fairness Engine Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeFairnessEngine =
    new SovereignRuntimeFairnessEngine();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_FAIRNESS_ENGINE =
    sovereignRuntimeFairnessEngine;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register('fairness-engine', sovereignRuntimeFairnessEngine);
}
