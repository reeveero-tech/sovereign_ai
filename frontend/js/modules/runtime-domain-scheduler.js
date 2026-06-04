/* ============================================================
   Sovereign AI — runtime-domain-scheduler.js
   الإصدار: 10.0.0
   المجدول السيادي الموزع للنطاقات التشغيلية
   ============================================================ */

class SovereignRuntimeDomainScheduler {

    constructor() {

        /* =========================================
           DOMAIN QUEUES
        ========================================= */

        this.queues =
            new Map();

        /* =========================================
           EXECUTION STATE
        ========================================= */

        this.active =
            true;

        this.processing =
            false;

        /* =========================================
           DOMAIN PRIORITIES (ديناميكية)
        ========================================= */

        this.domainPriority = {
            core: 0,
            governance: 1,
            cognition: 2,
            telemetry: 3,
            network: 4,
            ui: 5,
            ai: 6,
            sandbox: 7
        };

        /* =========================================
           BASE PRIORITIES (للرجوع عند الحاجة)
        ========================================= */

        this.basePriority = { ...this.domainPriority };

        /* =========================================
           LOAD BALANCING (توزيع الحمل)
        ========================================= */

        this.loadBalancing = {
            enabled: true,
            thresholds: {
                highLoad: 70,    // 70% load triggers balancing
                criticalLoad: 85  // 85% triggers redistribution
            },
            redistributionHistory: [],
            domainLoadScores: new Map()  // domain → current load %
        };

        /* =========================================
           PRIORITY INHERITANCE (وراثة الأولويات)
        ========================================= */

        this.priorityInheritance = {
            enabled: true,
            inheritanceMap: new Map(),  // taskId → inheritedFrom
            maxInheritanceDepth: 3
        };

        /* =========================================
           WORKLOAD FORECASTING (التنبؤ بالحمل)
        ========================================= */

        this.workloadForecast = {
            enabled: true,
            predictions: new Map(),     // domain → predicted load in 5s/10s/30s
            lastUpdate: null,
            accuracy: 80
        };

        /* =========================================
           DISTRIBUTED BACKPRESSURE
        ========================================= */

        this.backpressure = {
            enabled: true,
            active: false,
            throttledDomains: new Set(),
            pressureLevels: new Map(),  // domain → pressure level (0-100)
            propagationDelay: 500       // ms
        };

        /* =========================================
           METRICS (محسن)
        ========================================= */

        this.metrics = {
            scheduled: 0,
            executed: 0,
            deferred: 0,
            rejected: 0,
            isolated: 0,
            balanced: 0,
            redistributed: 0,
            priorityInherited: 0,
            backpressureTriggered: 0,
            forecastAdjusted: 0
        };

        console.log('🧩 Runtime Domain Scheduler Initialized (Distributed Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.initializeQueues();
        this.startProcessingLoop();
        this.startLoadBalancingLoop();
        this.startWorkloadForecasting();
        this.bindCognitiveEvents();
        this.bindBackpressureEvents();
        this.publishReady();
    }

    /* ========================================================
       COGNITIVE EVENTS (للتوقع)
    ======================================================== */

    bindCognitiveEvents() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:cognition:prediction', (payload) => {
            const prediction = payload.prediction;
            if (prediction?.type === 'domain-saturation' && prediction.metadata?.domain) {
                this.handlePredictedSaturation(prediction.metadata.domain, prediction.severity);
            }
        });
    }

    /* ========================================================
       BACKPRESSURE EVENTS
    ======================================================== */

    bindBackpressureEvents() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:domain:pressure', ({ domain, load }) => {
            this.updateBackpressure(domain, load);
        });
    }

    /* ========================================================
       QUEUES
    ======================================================== */

    initializeQueues() {

        Object.keys(this.domainPriority).forEach(domain => {
            this.queues.set(domain, []);
            this.loadBalancing.domainLoadScores.set(domain, 0);
            this.workloadForecast.predictions.set(domain, { 5: 0, 10: 0, 30: 0 });
            this.backpressure.pressureLevels.set(domain, 0);
        });
    }

    /* ========================================================
       LOAD BALANCING LOOP (توزيع الحمل التلقائي)
    ======================================================== */

    startLoadBalancingLoop() {

        this._loadBalanceInterval = setInterval(() => {

            if (!this.loadBalancing.enabled) return;

            this.calculateDomainLoads();
            this.redistributeTasks();

        }, 3000);
    }

    calculateDomainLoads() {

        for (const [domain, queue] of this.queues) {
            const queueLength = queue.length;
            const maxQueueSize = this.getMaxQueueSize(domain);
            const loadPercent = Math.min(100, (queueLength / maxQueueSize) * 100);
            
            this.loadBalancing.domainLoadScores.set(domain, loadPercent);
            
            // تحديث backpressure تلقائياً
            if (loadPercent > this.loadBalancing.thresholds.criticalLoad) {
                this.updateBackpressure(domain, loadPercent);
            }
        }
    }

    getMaxQueueSize(domain) {
        // سعة الطابور حسب نوع المجال
        const limits = {
            core: 100,
            governance: 150,
            cognition: 50,
            telemetry: 300,
            network: 200,
            ui: 200,
            ai: 100,
            sandbox: 50
        };
        return limits[domain] || 100;
    }

    redistributeTasks() {

        const overloadedDomains = [];
        const underloadedDomains = [];

        for (const [domain, load] of this.loadBalancing.domainLoadScores) {
            if (load > this.loadBalancing.thresholds.highLoad) {
                overloadedDomains.push({ domain, load });
            } else if (load < 30) {
                underloadedDomains.push({ domain, load });
            }
        }

        if (overloadedDomains.length === 0 || underloadedDomains.length === 0) return;

        // إعادة توزيع المهام من المجالات المثقلة إلى الخفيفة
        for (const overloaded of overloadedDomains) {
            const sourceQueue = this.queues.get(overloaded.domain);
            if (!sourceQueue || sourceQueue.length === 0) continue;

            const tasksToMove = Math.min(3, Math.floor(sourceQueue.length * 0.2));
            
            for (let i = 0; i < tasksToMove && sourceQueue.length > 0; i++) {
                const task = sourceQueue.shift();
                if (!task) continue;

                // العثور على domain مناسب
                const targetDomain = this.findBestTargetDomain(task, underloadedDomains);
                if (targetDomain) {
                    task.metadata = task.metadata || {};
                    task.metadata.redistributedFrom = overloaded.domain;
                    task.metadata.redistributedAt = Date.now();
                    
                    const targetQueue = this.queues.get(targetDomain);
                    if (targetQueue) {
                        targetQueue.push(task);
                        this.metrics.redistributed++;
                    } else {
                        sourceQueue.unshift(task); // إعادة إذا لم نجد هدف
                    }
                } else {
                    sourceQueue.unshift(task);
                    break;
                }
            }
        }
    }

    findBestTargetDomain(task, underloadedDomains) {

        // تفضيل المجالات ذات الأولوية المشابهة
        const taskDomain = task.domain;
        const taskPriority = this.domainPriority[taskDomain] || 5;

        const compatibleDomains = underloadedDomains.filter(({ domain }) => {
            const domainPriority = this.domainPriority[domain] || 5;
            return Math.abs(domainPriority - taskPriority) <= 2;
        });

        if (compatibleDomains.length === 0) return null;

        // اختيار أقلها حملاً
        compatibleDomains.sort((a, b) => a.load - b.load);
        return compatibleDomains[0].domain;
    }

    /* ========================================================
       WORKLOAD FORECASTING (التنبؤ بالحمل)
    ======================================================== */

    startWorkloadForecasting() {

        this._forecastInterval = setInterval(() => {

            if (!this.workloadForecast.enabled) return;

            this.updateWorkloadForecasts();

        }, 5000);
    }

    updateWorkloadForecasts() {

        for (const [domain, queue] of this.queues) {
            const currentLoad = this.loadBalancing.domainLoadScores.get(domain) || 0;
            const queueGrowthRate = this.calculateQueueGrowthRate(domain, queue);
            
            // التنبؤ بعد 5, 10, 30 ثانية
            const predictions = {
                5: Math.min(100, currentLoad + (queueGrowthRate * 5)),
                10: Math.min(100, currentLoad + (queueGrowthRate * 10)),
                30: Math.min(100, currentLoad + (queueGrowthRate * 30))
            };

            this.workloadForecast.predictions.set(domain, predictions);

            // إذا كان التوقع يشير إلى حمل حرج خلال 5 ثوانٍ، اتخذ إجراءً استباقياً
            if (predictions[5] > this.loadBalancing.thresholds.criticalLoad) {
                this.handlePredictedSaturation(domain, 'high');
                this.metrics.forecastAdjusted++;
            }
        }

        this.workloadForecast.lastUpdate = Date.now();
    }

    calculateQueueGrowthRate(domain, queue) {

        // تقدير معدل النمو بناءً على آخر 10 مهام
        const recentTasks = queue.slice(-10);
        if (recentTasks.length < 5) return 0;

        // حساب متوسط الوقت بين الإضافات
        const timestamps = recentTasks.map(t => t.createdAt).filter(Boolean);
        if (timestamps.length < 2) return 0;

        const avgInterval = (timestamps[timestamps.length - 1] - timestamps[0]) / timestamps.length;
        const tasksPerSecond = 1000 / avgInterval;

        // مساهمة كل مهمة في الحمل
        const taskWeight = 5; // كل مهمة تساهم بـ 5% من الحمل
        return tasksPerSecond * taskWeight;
    }

    handlePredictedSaturation(domain, severity) {

        console.log(`🧩 Predicted saturation for domain ${domain} (severity: ${severity})`);

        // إجراءات استباقية
        if (severity === 'high' || severity === 'critical') {
            // زيادة أولوية المجال لمعالجته بشكل أسرع
            this.domainPriority[domain] = Math.max(0, (this.domainPriority[domain] || 5) - 1);
            
            // تفعيل backpressure على المجالات التي ترسل إليه
            this.propagateBackpressure(domain);
        }
    }

    /* ========================================================
       DISTRIBUTED BACKPRESSURE
    ======================================================== */

    updateBackpressure(domain, load) {

        const pressureLevel = Math.min(100, load);
        this.backpressure.pressureLevels.set(domain, pressureLevel);

        if (pressureLevel > 80 && !this.backpressure.throttledDomains.has(domain)) {
            this.backpressure.throttledDomains.add(domain);
            this.backpressure.active = true;
            this.metrics.backpressureTriggered++;
            
            console.log(`🧩 Backpressure activated for domain: ${domain} (${pressureLevel}%)`);
            
            // نشر إشعار backpressure
            const bus = window.SOVEREIGN_ACCESS?.bus?.();
            if (bus && typeof bus.publishWithoutMiddleware === 'function') {
                bus.publishWithoutMiddleware('runtime:backpressure:activated', {
                    domain,
                    pressureLevel,
                    timestamp: Date.now()
                });
            }
        } else if (pressureLevel < 50 && this.backpressure.throttledDomains.has(domain)) {
            this.backpressure.throttledDomains.delete(domain);
            
            if (this.backpressure.throttledDomains.size === 0) {
                this.backpressure.active = false;
            }
        }
    }

    propagateBackpressure(sourceDomain) {

        // إعلام المجالات التي ترسل مهام إلى sourceDomain
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:backpressure:propagate', {
                sourceDomain,
                pressureLevel: this.backpressure.pressureLevels.get(sourceDomain) || 80,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       PRIORITY INHERITANCE (وراثة الأولويات)
    ======================================================== */

    inheritPriority(parentTaskId, childTaskId, childDomain) {

        if (!this.priorityInheritance.enabled) return;

        const parentQueue = this.findTaskQueue(parentTaskId);
        if (!parentQueue) return;

        const parentTask = parentQueue.find(t => t.id === parentTaskId);
        if (!parentTask) return;

        const childQueue = this.queues.get(childDomain);
        if (!childQueue) return;

        const childTask = childQueue.find(t => t.id === childTaskId);
        if (!childTask) return;

        // توريث الأولوية إذا كانت أولوية الطفل أقل
        if (childTask.priority > parentTask.priority) {
            const oldPriority = childTask.priority;
            childTask.priority = parentTask.priority;
            childTask.inheritedFrom = parentTaskId;
            
            this.priorityInheritance.inheritanceMap.set(childTaskId, {
                from: parentTaskId,
                originalPriority: oldPriority,
                inheritedAt: Date.now()
            });
            
            this.metrics.priorityInherited++;
            
            console.log(`🧩 Priority inherited | CHILD: ${childTaskId} | NEW PRIORITY: ${childTask.priority}`);
            
            // إعادة ترتيب الطابور
            this.sortQueue(childDomain);
        }
    }

    findTaskQueue(taskId) {

        for (const [domain, queue] of this.queues) {
            const found = queue.find(t => t.id === taskId);
            if (found) return queue;
        }
        return null;
    }

    sortQueue(domain) {

        const queue = this.queues.get(domain);
        if (!queue) return;

        const fairness = window.SOVEREIGN_FAIRNESS_ENGINE;
        if (fairness?.sortQueue) {
            queue.sort((a, b) => fairness.calculateFairPriority(a) - fairness.calculateFairPriority(b));
        } else {
            queue.sort((a, b) => a.priority - b.priority);
        }
    }

    /* ========================================================
       TASK SCHEDULING (محسن)
    ======================================================== */

    scheduleTask({ domain = 'core', task = null, priority = 10, metadata = {}, parentTaskId = null }) {

        if (!task) return false;

        const domains = window.SOVEREIGN_EXECUTION_DOMAINS;

        if (!domains?.canExecute?.({ domain, task })) {
            this.metrics.rejected++;
            return false;
        }

        const queue = this.queues.get(domain);
        if (!queue) {
            this.metrics.rejected++;
            return false;
        }

        const entry = {
            id: crypto.randomUUID(),
            domain,
            task,
            priority,
            metadata,
            createdAt: Date.now(),
            deferCount: 0,
            inheritedFrom: null
        };

        queue.push(entry);
        this.metrics.scheduled++;

        // وراثة الأولوية إذا وُجد مهمة أب
        if (parentTaskId) {
            this.inheritPriority(parentTaskId, entry.id, domain);
        }

        // إعادة ترتيب الطابور
        this.sortQueue(domain);

        this.publishScheduled(entry);
        return true;
    }

    /* ========================================================
       PROCESSING LOOP (محسن)
    ======================================================== */

    startProcessingLoop() {

        this._processInterval = setInterval(() => {
            this.processDomains();
        }, 100);
    }

    async processDomains() {

        if (this.processing || !this.active) return;

        this.processing = true;

        try {
            // تحديث الأولويات الديناميكية
            this.updateDynamicPriorities();

            const orderedDomains = Object.entries(this.domainPriority)
                .sort((a, b) => a[1] - b[1])
                .map(([domain]) => domain);

            for (const domain of orderedDomains) {
                // التحقق من backpressure قبل المعالجة
                if (this.backpressure.throttledDomains.has(domain)) {
                    // معالجة فقط مهمة واحدة كل دورة للمجالات المختنقة
                    await this.processDomain(domain, true);
                } else {
                    await this.processDomain(domain, false);
                }
            }

            // تحديث توازن الطوابير بعد كل دورة
            this.rebalanceQueues();

        } finally {
            this.processing = false;
        }
    }

    updateDynamicPriorities() {

        // تعديل الأولويات بناءً على الضغط والحمل المتوقع
        for (const [domain, load] of this.loadBalancing.domainLoadScores) {
            const forecast = this.workloadForecast.predictions.get(domain);
            const predictedLoad = forecast?.[5] || load;
            
            if (predictedLoad > this.loadBalancing.thresholds.criticalLoad) {
                // رفع أولوية المجالات المثقلة
                const currentPriority = this.domainPriority[domain] || 5;
                this.domainPriority[domain] = Math.max(0, currentPriority - 2);
            } else if (predictedLoad < 20 && this.domainPriority[domain] < (this.basePriority[domain] || 5)) {
                // إعادة الأولوية الأصلية للمجالات الخفيفة
                this.domainPriority[domain] = this.basePriority[domain] || 5;
            }
        }
    }

    async processDomain(domain, throttled = false) {

        const queue = this.queues.get(domain);
        if (!queue || !queue.length) return;

        const fairness = window.SOVEREIGN_FAIRNESS_ENGINE;

        if (fairness?.sortQueue) {
            fairness.sortQueue(queue);
        }

        const itemsToProcess = throttled ? 1 : Math.min(3, queue.length);

        for (let i = 0; i < itemsToProcess && queue.length > 0; i++) {
            const item = queue.shift();
            if (!item) continue;

            // التحقق من التأجيل
            if (fairness?.shouldDefer?.(item)) {
                fairness.applyDeferral(item);
                queue.push(item);
                this.metrics.deferred++;
                continue;
            }

            // التنفيذ في المجال المناسب
            const domains = window.SOVEREIGN_EXECUTION_DOMAINS;
            const result = domains?.executeInDomain?.({
                domain: item.domain,
                callback: () => item.task?.(),
                sourceDomain: 'domain-scheduler',
                taskId: item.id
            });

            if (result !== false) {
                this.metrics.executed++;
                this.metrics.isolated++;
                this.publishExecuted(item);
            } else {
                // إعادة المهمة إلى الطابور إذا فشل التنفيذ
                queue.unshift(item);
            }
        }
    }

    /* ========================================================
       REBALANCE (محسن)
    ======================================================== */

    rebalanceQueues() {

        const telemetry = window.SOVEREIGN_FLOW_TELEMETRY?.getStatus?.();
        
        if (telemetry?.stability < 50) {
            this.metrics.balanced++;
            this.prioritizeCriticalDomains();
        }

        // إعادة توزيع الحمل إذا لزم الأمر
        if (this.loadBalancing.enabled) {
            this.redistributeTasks();
        }
    }

    prioritizeCriticalDomains() {
        // الحفاظ على أولويات المجالات الحرجة
        this.domainPriority.core = 0;
        this.domainPriority.governance = 1;
        this.domainPriority.cognition = 2;
        
        // خفض أولوية المجالات غير الحرجة مؤقتاً
        this.domainPriority.ui = Math.min(10, (this.domainPriority.ui || 5) + 2);
        this.domainPriority.ai = Math.min(10, (this.domainPriority.ai || 6) + 2);
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishExecuted(item) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('scheduler:task:executed', {
                taskId: item.id,
                domain: item.domain,
                priority: item.priority,
                inheritedFrom: item.inheritedFrom,
                timestamp: Date.now()
            });
        }
    }

    publishScheduled(item) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('scheduler:task:scheduled', {
                taskId: item.id,
                domain: item.domain,
                priority: item.priority,
                timestamp: Date.now()
            });
        }
    }

    publishReady() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime-domain-scheduler:ready', {
                domains: this.queues.size,
                loadBalancing: this.loadBalancing.enabled,
                backpressure: this.backpressure.enabled,
                workloadForecast: this.workloadForecast.enabled,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        const queueLengths = {};
        for (const [domain, queue] of this.queues) {
            queueLengths[domain] = queue.length;
        }

        const domainLoads = {};
        for (const [domain, load] of this.loadBalancing.domainLoadScores) {
            domainLoads[domain] = load;
        }

        const forecasts = {};
        for (const [domain, pred] of this.workloadForecast.predictions) {
            forecasts[domain] = pred;
        }

        const pressureLevels = {};
        for (const [domain, pressure] of this.backpressure.pressureLevels) {
            pressureLevels[domain] = pressure;
        }

        return {
            active: this.active,
            processing: this.processing,
            queues: queueLengths,
            domainLoads,
            workloadForecasts: forecasts,
            backpressure: {
                active: this.backpressure.active,
                throttledDomains: Array.from(this.backpressure.throttledDomains),
                pressureLevels
            },
            priorityInheritance: {
                enabled: this.priorityInheritance.enabled,
                activeInheritances: this.priorityInheritance.inheritanceMap.size
            },
            metrics: { ...this.metrics }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._processInterval) {
            clearInterval(this._processInterval);
            this._processInterval = null;
        }

        if (this._loadBalanceInterval) {
            clearInterval(this._loadBalanceInterval);
            this._loadBalanceInterval = null;
        }

        if (this._forecastInterval) {
            clearInterval(this._forecastInterval);
            this._forecastInterval = null;
        }

        this.queues.clear();
        this.loadBalancing.domainLoadScores.clear();
        this.workloadForecast.predictions.clear();
        this.backpressure.pressureLevels.clear();
        this.backpressure.throttledDomains.clear();
        this.priorityInheritance.inheritanceMap.clear();

        console.log('🧩 Runtime Domain Scheduler Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeDomainScheduler =
    new SovereignRuntimeDomainScheduler();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_DOMAIN_SCHEDULER =
    sovereignRuntimeDomainScheduler;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register('domain-scheduler', sovereignRuntimeDomainScheduler);
}
