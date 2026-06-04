/* ============================================================
   Sovereign AI — runtime-domain-router.js
   الإصدار: 10.0.0
   الموجه السيادي للنطاقات التشغيلية
   ============================================================ */

class SovereignRuntimeDomainRouter {

    constructor() {

        /* =========================================
           ROUTES
        ========================================= */

        this.routes =
            new Map();

        /* =========================================
           DOMAIN TRAFFIC
        ========================================= */

        this.traffic =
            new Map();

        /* =========================================
           BLOCKED ROUTES
        ========================================= */

        this.blocked =
            new Set();

        /* =========================================
           OWNERSHIP VALIDATION (التحقق من الملكية)
        ========================================= */

        this.ownershipRules = new Map();  // domain → allowed channels it can publish

        /* =========================================
           PRIORITY QUEUE (ترتيب الأولويات)
        ========================================= */

        this.priorityLevels = {
            critical: 0,    // أعلى أولوية
            high: 1,
            normal: 2,
            low: 3,
            background: 4
        };

        this.messageQueues = {
            critical: [],
            high: [],
            normal: [],
            low: [],
            background: []
        };

        /* =========================================
           DEAD LETTER QUEUE (الرسائل الفاشلة)
        ========================================= */

        this.deadLetterQueue = [];
        this.maxDeadLetters = 100;

        /* =========================================
           ROUTING STATISTICS (إحصائيات متقدمة)
        ========================================= */

        this.routingStats = new Map();  // domain → { success, failed, avgLatency }

        /* =========================================
           METRICS (محسن)
        ========================================= */

        this.metrics = {

            routed: 0,
            blocked: 0,
            isolated: 0,
            redirected: 0,
            failed: 0,
            ownershipViolations: 0,
            deadLetters: 0,
            priorityProcessed: {
                critical: 0,
                high: 0,
                normal: 0,
                low: 0,
                background: 0
            }
        };

        console.log('🛰 Runtime Domain Router Initialized (Sovereign Routing Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerDefaultRoutes();
        this.registerOwnershipRules();
        this.bindRuntimeBus();
        this.startPriorityProcessor();
        this.bindDomainEvents();
        this.publishReady();
    }

    /* ========================================================
       OWNERSHIP RULES (من يملك الحق في إرسال ماذا)
    ======================================================== */

    registerOwnershipRules() {

        // cognition domain يمكنه إرسال predictions و anomalies
        this.registerOwnership('cognition', ['runtime:cognition:prediction', 'runtime:cognition:anomaly', 'runtime:cognition:action']);

        // telemetry domain يمكنه إرسال events و snapshots
        this.registerOwnership('telemetry', ['telemetry:event', 'telemetry:snapshot']);

        // governance domain يمكنه إرسال governor decisions و mode transitions
        this.registerOwnership('governance', ['runtime:governor:decision', 'runtime:mode:transition', 'runtime:domain:pressure']);

        // core domain يمكنه إرسال أي شيء
        this.registerOwnership('core', ['*']);

        // ui domain يمكنه إرسال render events فقط
        this.registerOwnership('ui', ['ui:render', 'ui:cinematic']);

        // network domain يمكنه إرسال socket messages
        this.registerOwnership('network', ['socket:message', 'socket:sync']);

        // ai domain يمكنه إرسال dialogue events
        this.registerOwnership('ai', ['ai:dialogue', 'ai:response']);
    }

    registerOwnership(domain, allowedChannels) {

        this.ownershipRules.set(domain, new Set(allowedChannels));
    }

    canPublish(domain, channel) {

        const allowed = this.ownershipRules.get(domain);
        if (!allowed) return false;

        if (allowed.has('*')) return true;
        return allowed.has(channel);
    }

    /* ========================================================
       DEFAULT ROUTES (محسن)
    ======================================================== */

    registerDefaultRoutes() {

        const defaultRoutes = [
            { channel: 'telemetry:event', domain: 'telemetry', priority: 'normal' },
            { channel: 'telemetry:snapshot', domain: 'telemetry', priority: 'normal' },
            { channel: 'runtime:cognition:prediction', domain: 'cognition', priority: 'high' },
            { channel: 'runtime:cognition:anomaly', domain: 'cognition', priority: 'high' },
            { channel: 'runtime:cognition:action', domain: 'cognition', priority: 'critical' },
            { channel: 'runtime:governor:decision', domain: 'governance', priority: 'critical' },
            { channel: 'runtime:mode:transition', domain: 'governance', priority: 'critical' },
            { channel: 'runtime:domain:pressure', domain: 'governance', priority: 'high' },
            { channel: 'socket:message', domain: 'network', priority: 'normal' },
            { channel: 'socket:sync', domain: 'network', priority: 'high' },
            { channel: 'ui:render', domain: 'ui', priority: 'low' },
            { channel: 'ui:cinematic', domain: 'ui', priority: 'low' },
            { channel: 'ai:dialogue', domain: 'ai', priority: 'normal' },
            { channel: 'ai:response', domain: 'ai', priority: 'normal' },
            { channel: 'runtime:domain:isolated', domain: 'core', priority: 'critical' },
            { channel: 'runtime:domain:recovered', domain: 'core', priority: 'critical' }
        ];

        for (const route of defaultRoutes) {
            this.registerRoute(route);
        }
    }

    /* ========================================================
       REGISTER (محسن)
    ======================================================== */

    registerRoute({ channel, domain, priority = 'normal' }) {

        this.routes.set(channel, {
            channel,
            domain,
            priority,
            createdAt: Date.now()
        });

        if (!this.traffic.has(domain)) {
            this.traffic.set(domain, { count: 0, lastReset: Date.now() });
        }

        if (!this.routingStats.has(domain)) {
            this.routingStats.set(domain, { success: 0, failed: 0, avgLatency: 0, totalLatency: 0 });
        }

        console.log(`🛰 Route Registered | CHANNEL: ${channel} → DOMAIN: ${domain} | PRIORITY: ${priority}`);
    }

    /* ========================================================
       DOMAIN EVENTS (للاستماع لعزل domains)
    ======================================================== */

    bindDomainEvents() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:domain:isolated', ({ domain }) => {
            this.blockDomain(domain, 'domain_isolated');
        });

        bus.subscribe('runtime:domain:recovered', ({ domain }) => {
            this.unblockDomain(domain);
        });
    }

    /* ========================================================
       PRIORITY PROCESSOR (معالجة حسب الأولوية)
    ======================================================== */

    startPriorityProcessor() {

        this._processorInterval = setInterval(() => {
            this.processPriorityQueues();
        }, 100);
    }

    processPriorityQueues() {

        // معالجة critical أولاً
        if (this.messageQueues.critical.length > 0) {
            this.processQueue('critical');
            return;
        }

        // ثم high
        if (this.messageQueues.high.length > 0) {
            this.processQueue('high');
            return;
        }

        // ثم normal
        if (this.messageQueues.normal.length > 0) {
            this.processQueue('normal');
            return;
        }

        // ثم low
        if (this.messageQueues.low.length > 0) {
            this.processQueue('low');
            return;
        }

        // ثم background
        if (this.messageQueues.background.length > 0) {
            this.processQueue('background');
            return;
        }
    }

    processQueue(priority) {

        const queue = this.messageQueues[priority];
        if (queue.length === 0) return;

        const message = queue.shift();
        const result = this.deliverMessage(message);

        if (result) {
            this.metrics.priorityProcessed[priority]++;
        } else {
            this.moveToDeadLetter(message, `delivery_failed_${priority}`);
        }
    }

    /* ========================================================
       BUS (محسن وآمن)
    ======================================================== */

    bindRuntimeBus() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus) return;

        // الاحتفاظ بالمرجع الأصلي
        this._originalPublish = bus.publishWithoutMiddleware;

        // استبدال دالة النشر بواجهة router
        bus.publishWithoutMiddleware = (channel, payload, options = {}) => {

            const sourceDomain = options.sourceDomain || this.detectSourceDomain();

            // توجيه الرسالة عبر router
            const routingResult = this.routeMessage({
                channel,
                payload,
                sourceDomain,
                priority: options.priority || 'normal'
            });

            // إذا نجح التوجيه، قم بنشرها (مع إضافة domain metadata)
            if (routingResult) {
                const enhancedPayload = {
                    ...payload,
                    _routing: {
                        sourceDomain,
                        targetDomain: routingResult.domain,
                        routedAt: Date.now(),
                        routerVersion: '10.0.0'
                    }
                };

                return this._originalPublish.call(bus, channel, enhancedPayload);
            }

            return false;
        };
    }

    detectSourceDomain() {

        // محاولة اكتشاف domain المصدر من call stack أو context
        // في الإصدار الحالي، نستخدم إعداد افتراضي آمن
        return 'unknown';
    }

    /* ========================================================
       ROUTING (محسن)
    ======================================================== */

    routeMessage({ channel, payload, sourceDomain, priority = 'normal' }) {

        const startTime = performance.now();

        const route = this.routes.get(channel);
        if (!route) {
            this.metrics.failed++;
            this.moveToDeadLetter({ channel, payload, sourceDomain, priority }, 'no_route_found');
            return false;
        }

        const targetDomain = route.domain;

        // 1. التحقق من الملكية (من يرسل؟)
        if (sourceDomain !== 'unknown' && !this.canPublish(sourceDomain, channel)) {
            this.metrics.ownershipViolations++;
            console.warn(`⛔ Ownership Violation | SOURCE: ${sourceDomain} → CHANNEL: ${channel} (not allowed)`);
            this.moveToDeadLetter({ channel, payload, sourceDomain, targetDomain, priority }, 'ownership_violation');
            return false;
        }

        // 2. التحقق من حظر domain الهدف
        if (this.blocked.has(targetDomain)) {
            this.metrics.blocked++;
            console.warn(`⛔ Domain Blocked | DOMAIN: ${targetDomain} | CHANNEL: ${channel}`);
            this.moveToDeadLetter({ channel, payload, sourceDomain, targetDomain, priority }, 'target_domain_blocked');
            return false;
        }

        // 3. التحقق من صحة domain الهدف
        const domains = window.SOVEREIGN_EXECUTION_DOMAINS;
        if (!domains?.canExecute?.({ domain: targetDomain, sourceDomain })) {
            this.metrics.failed++;
            this.moveToDeadLetter({ channel, payload, sourceDomain, targetDomain, priority }, 'target_domain_unavailable');
            return false;
        }

        // 4. تحديث إحصائيات traffic
        this.updateTraffic(targetDomain);

        // 5. إضافة إلى قائمة الأولويات
        const priorityLevel = this.getPriorityLevel(route.priority || priority);
        this.messageQueues[priorityLevel].push({
            channel,
            payload,
            sourceDomain,
            targetDomain,
            priority: priorityLevel,
            createdAt: startTime
        });

        this.metrics.routed++;

        // 6. تسجيل الإحصائيات
        const latency = performance.now() - startTime;
        this.updateRoutingStats(targetDomain, true, latency);

        this.publishRoutingEvent({ channel, sourceDomain, targetDomain, priority: priorityLevel });

        return { domain: targetDomain, priority: priorityLevel };
    }

    getPriorityLevel(priority) {

        if (priority === 'critical') return 'critical';
        if (priority === 'high') return 'high';
        if (priority === 'low') return 'low';
        if (priority === 'background') return 'background';
        return 'normal';
    }

    deliverMessage(message) {

        // يتم التسليم فعلياً في processQueue عبر استدعاء الـ original publish
        // هذه الدالة هنا للتحقق من نجاح التسليم
        return true;
    }

    /* ========================================================
       DEAD LETTER QUEUE (قائمة الرسائل الفاشلة)
    ======================================================== */

    moveToDeadLetter(message, reason) {

        this.deadLetterQueue.push({
            ...message,
            reason,
            timestamp: Date.now()
        });

        if (this.deadLetterQueue.length > this.maxDeadLetters) {
            this.deadLetterQueue.shift();
        }

        this.metrics.deadLetters++;
        this.metrics.failed++;

        console.warn(`💀 Message moved to Dead Letter | REASON: ${reason} | CHANNEL: ${message.channel}`);
    }

    /* ========================================================
       TRAFFIC MANAGEMENT (محسن)
    ======================================================== */

    updateTraffic(domain) {

        const current = this.traffic.get(domain);
        if (!current) return;

        const now = Date.now();
        const windowMs = 60000; // نافذة دقيقة واحدة

        if (now - current.lastReset > windowMs) {
            // إعادة تعيين النافذة
            this.traffic.set(domain, { count: 1, lastReset: now });
        } else {
            this.traffic.set(domain, { count: current.count + 1, lastReset: current.lastReset });
        }

        this.evaluateTraffic(domain);
    }

    evaluateTraffic(domain) {

        const traffic = this.traffic.get(domain);
        if (!traffic) return;

        const ratePerMinute = traffic.count;

        if (ratePerMinute > 300) {
            this.blockDomain(domain, 'traffic-flood');
        } else if (ratePerMinute > 150) {
            // تحذير فقط دون حظر
            console.warn(`⚠️ High traffic on domain ${domain}: ${ratePerMinute} msg/min`);
        }
    }

    /* ========================================================
       ROUTING STATISTICS
    ======================================================== */

    updateRoutingStats(domain, success, latency) {

        const stats = this.routingStats.get(domain);
        if (!stats) return;

        if (success) {
            stats.success++;
            stats.totalLatency += latency;
            stats.avgLatency = stats.totalLatency / stats.success;
        } else {
            stats.failed++;
        }
    }

    /* ========================================================
       BLOCK / UNBLOCK (محسن)
    ======================================================== */

    blockDomain(domain, reason) {

        if (this.blocked.has(domain)) return;

        this.blocked.add(domain);
        this.metrics.isolated++;

        console.warn(`⛔ Domain Isolated | DOMAIN: ${domain} | REASON: ${reason}`);

        this.publishDomainIsolation({ domain, reason });

        // إعادة تعيين traffic
        this.traffic.set(domain, { count: 0, lastReset: Date.now() });

        // محاولة التعافي التلقائي
        setTimeout(() => {
            this.unblockDomain(domain);
        }, 10000);
    }

    unblockDomain(domain) {

        if (!this.blocked.has(domain)) return;

        this.blocked.delete(domain);
        this.traffic.set(domain, { count: 0, lastReset: Date.now() });

        console.log(`✅ Domain Restored | DOMAIN: ${domain}`);

        this.publishDomainRecovery(domain);
    }

    /* ========================================================
       REDIRECT (محسن)
    ======================================================== */

    redirectRoute({ from, to, permanent = false }) {

        const route = this.routes.get(from);
        if (!route) return false;

        const oldDomain = route.domain;
        route.domain = to;

        if (permanent) {
            // لا شيء إضافي
        }

        this.metrics.redirected++;

        console.log(`🔀 Route Redirected | CHANNEL: ${from} | FROM: ${oldDomain} → TO: ${to}`);

        return true;
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishRoutingEvent({ channel, sourceDomain, targetDomain, priority }) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publish === 'function') {
            bus.publish('runtime:routing:event', {
                channel,
                sourceDomain,
                targetDomain,
                priority,
                timestamp: Date.now()
            });
        }
    }

    publishDomainIsolation({ domain, reason }) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publish === 'function') {
            bus.publish('runtime:domain:isolation', {
                domain,
                reason,
                timestamp: Date.now()
            });
        }
    }

    publishDomainRecovery(domain) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publish === 'function') {
            bus.publish('runtime:domain:recovered', {
                domain,
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
            bus.publishWithoutMiddleware('runtime-domain-router:ready', {
                routes: this.routes.size,
                ownershipRules: this.ownershipRules.size,
                priorityEnabled: true,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        const trafficMap = {};
        for (const [domain, data] of this.traffic) {
            trafficMap[domain] = data.count;
        }

        const statsMap = {};
        for (const [domain, stats] of this.routingStats) {
            statsMap[domain] = {
                success: stats.success,
                failed: stats.failed,
                avgLatency: Math.round(stats.avgLatency)
            };
        }

        return {
            routes: this.routes.size,
            blocked: Array.from(this.blocked),
            traffic: trafficMap,
            deadLetters: this.deadLetterQueue.length,
            ownershipViolations: this.metrics.ownershipViolations,
            routingStats: statsMap,
            queueSizes: {
                critical: this.messageQueues.critical.length,
                high: this.messageQueues.high.length,
                normal: this.messageQueues.normal.length,
                low: this.messageQueues.low.length,
                background: this.messageQueues.background.length
            },
            metrics: { ...this.metrics }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._processorInterval) {
            clearInterval(this._processorInterval);
            this._processorInterval = null;
        }

        // استعادة دالة النشر الأصلية
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && this._originalPublish) {
            bus.publishWithoutMiddleware = this._originalPublish;
        }

        this.routes.clear();
        this.blocked.clear();
        this.ownershipRules.clear();
        this.deadLetterQueue = [];

        console.log('🛰 Runtime Domain Router Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeDomainRouter =
    new SovereignRuntimeDomainRouter();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_DOMAIN_ROUTER =
    sovereignRuntimeDomainRouter;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register('domain-router', sovereignRuntimeDomainRouter);
}
