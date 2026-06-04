/* ============================================================
   Sovereign AI — runtime-execution-domains.js
   الإصدار: 10.0.0
   نطاقات التنفيذ السيادية
   عزل كامل للفشل وحماية الموارد بين الأنظمة
   ============================================================ */

class SovereignRuntimeExecutionDomains {

    constructor() {

        /* =========================================
           DOMAINS
        ========================================= */

        this.domains =
            new Map();

        /* =========================================
           DOMAIN RESOURCE LIMITS (حدود الموارد)
        ========================================= */

        this.resourceLimits = new Map();  // الحد الأقصى لكل domain

        /* =========================================
           DOMAIN HEALTH
        ========================================= */

        this.domainHealth =
            new Map();

        /* =========================================
           DOMAIN LOAD
        ========================================= */

        this.domainLoad =
            new Map();

        /* =========================================
           DOMAIN FAILURE ISOLATION (عزل الفشل)
        ========================================= */

        this.failureZones = new Map();     // مناطق العزل عند الفشل
        this.isolatedFailures = [];        // سجل الأعطال المعزولة

        /* =========================================
           CROSS-DOMAIN COMMUNICATION RULES
        ========================================= */

        this.communicationRules = {
            allowedPairs: new Map(),       // domain → Set(domains it can talk to)
            defaultPolicy: 'deny',         // deny, allow, quarantine
            blockedCommunications: []      // سجل الاتصالات الممنوعة
        };

        /* =========================================
           DOMAIN PRIORITY ESCALATION
        ========================================= */

        this.escalationPolicies = new Map();  // سياسات الطوارئ لكل domain

        /* =========================================
           DOMAIN ISOLATION
        ========================================= */

        this.isolationEnabled =
            true;

        /* =========================================
           METRICS (محسن)
        ========================================= */

        this.metrics = {

            domains: 0,
            isolatedExecutions: 0,
            domainRecoveries: 0,
            domainFailures: 0,
            overloadProtections: 0,
            crossDomainBlocks: 0,      // اتصالات ممنوعة بين domains
            failureIsolations: 0,      // عدد المرات التي تم فيها عزل فشل
            resourceLimitHits: 0       // عدد مرات تجاوز حدود الموارد
        };

        console.log('🌐 Runtime Execution Domains Initialized (Sovereign Isolation Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerDefaultDomains();
        this.registerDefaultCommunicationRules();
        this.registerDefaultEscalationPolicies();
        this.setDefaultResourceLimits();
        this.startMonitoring();
        this.bindCognitiveSignals();
        this.publishReady();
    }

    /* ========================================================
       COGNITIVE SIGNALS (للاستجابة الذكية)
    ======================================================== */

    bindCognitiveSignals() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:cognition:prediction', (payload) => {
            const prediction = payload.prediction;
            if (prediction?.type === 'domain-saturation') {
                this.handlePredictedSaturation(prediction);
            }
        });

        bus.subscribe('runtime:governor:decision', (payload) => {
            if (payload.mode === 'critical') {
                this.activateCriticalDomainPolicies();
            } else if (payload.mode === 'recovery') {
                this.activateRecoveryDomainPolicies();
            }
        });
    }

    /* ========================================================
       DEFAULT DOMAINS (محسن مع حدود الموارد)
    ======================================================== */

    registerDefaultDomains() {

        const domains = [
            { id: 'core', priority: 0, isolated: true, critical: true, maxLoad: 100, maxConcurrent: 10 },
            { id: 'governance', priority: 1, isolated: true, critical: true, maxLoad: 90, maxConcurrent: 8 },
            { id: 'telemetry', priority: 2, isolated: false, critical: false, maxLoad: 70, maxConcurrent: 20 },
            { id: 'cognition', priority: 3, isolated: true, critical: true, maxLoad: 85, maxConcurrent: 6 },
            { id: 'ui', priority: 4, isolated: false, critical: false, maxLoad: 60, maxConcurrent: 30 },
            { id: 'network', priority: 5, isolated: true, critical: true, maxLoad: 75, maxConcurrent: 15 },
            { id: 'sandbox', priority: 6, isolated: true, critical: true, maxLoad: 80, maxConcurrent: 12 },
            { id: 'ai', priority: 7, isolated: false, critical: false, maxLoad: 65, maxConcurrent: 25 }
        ];

        for (const domain of domains) {
            this.registerDomain(domain);
            this.resourceLimits.set(domain.id, {
                maxLoad: domain.maxLoad,
                maxConcurrent: domain.maxConcurrent
            });
        }
    }

    /* ========================================================
       DEFAULT COMMUNICATION RULES (قواعد التواصل)
    ======================================================== */

    registerDefaultCommunicationRules() {

        // core يمكنه التواصل مع الجميع
        this.allowCommunication('core', ['core', 'governance', 'telemetry', 'cognition', 'ui', 'network', 'sandbox', 'ai']);

        // cognition يمكنه التواصل مع core, governance, telemetry
        this.allowCommunication('cognition', ['core', 'governance', 'telemetry']);

        // governance يمكنه التواصل مع core, cognition, telemetry
        this.allowCommunication('governance', ['core', 'cognition', 'telemetry']);

        // telemetry يمكنه التواصل مع الجميع (للقراءة فقط)
        this.allowCommunication('telemetry', ['core', 'governance', 'cognition', 'ui', 'network', 'sandbox', 'ai']);

        // sandbox معزول تماماً (إلا مع core للإبلاغ)
        this.allowCommunication('sandbox', ['core']);

        // ui لا يمكنه التواصل مع governance, cognition مباشرة (عبر telemetry فقط)
        this.allowCommunication('ui', ['core', 'telemetry', 'network']);

        // ai لا يمكنه التواصل مع sandbox
        this.allowCommunication('ai', ['core', 'governance', 'telemetry', 'ui', 'network']);
    }

    allowCommunication(fromDomain, toDomains) {

        if (!this.communicationRules.allowedPairs.has(fromDomain)) {
            this.communicationRules.allowedPairs.set(fromDomain, new Set());
        }

        const allowedSet = this.communicationRules.allowedPairs.get(fromDomain);
        for (const toDomain of toDomains) {
            allowedSet.add(toDomain);
        }
    }

    canCommunicate(fromDomain, toDomain) {

        if (!this.communicationRules.allowedPairs.has(fromDomain)) {
            return this.communicationRules.defaultPolicy === 'allow';
        }

        const allowed = this.communicationRules.allowedPairs.get(fromDomain);
        return allowed.has(toDomain);
    }

    /* ========================================================
       DEFAULT ESCALATION POLICIES (سياسات الطوارئ)
    ======================================================== */

    registerDefaultEscalationPolicies() {

        const policies = [
            { domain: 'core', onCritical: 'protect', maxDegradation: 100 },
            { domain: 'cognition', onCritical: 'reduce_load', maxDegradation: 70 },
            { domain: 'governance', onCritical: 'protect', maxDegradation: 90 },
            { domain: 'telemetry', onCritical: 'reduce_sampling', maxDegradation: 50 },
            { domain: 'ui', onCritical: 'reduce_framerate', maxDegradation: 40 },
            { domain: 'sandbox', onCritical: 'quarantine', maxDegradation: 30 },
            { domain: 'network', onCritical: 'throttle', maxDegradation: 60 },
            { domain: 'ai', onCritical: 'reduce_complexity', maxDegradation: 50 }
        ];

        for (const policy of policies) {
            this.escalationPolicies.set(policy.domain, policy);
        }
    }

    /* ========================================================
       RESOURCE LIMITS
    ======================================================== */

    setDefaultResourceLimits() {

        // يمكن تخصيصها لاحقاً
    }

    checkResourceLimit(domain, currentLoad) {

        const limits = this.resourceLimits.get(domain);
        if (!limits) return true;

        if (currentLoad >= limits.maxLoad) {
            this.metrics.resourceLimitHits++;
            this.publishDomainWarning(domain, 'resource_limit_exceeded', { currentLoad, maxLoad: limits.maxLoad });
            return false;
        }

        return true;
    }

    /* ========================================================
       REGISTER (محسن)
    ======================================================== */

    registerDomain({ id, priority = 10, isolated = false, critical = false, maxLoad = 100, maxConcurrent = 10 }) {

        this.domains.set(id, {
            id,
            priority,
            isolated,
            critical,
            maxConcurrent,
            createdAt: Date.now(),
            status: 'active'  // active, degraded, quarantined, recovering
        });

        this.domainHealth.set(id, 100);
        this.domainLoad.set(id, 0);
        this.failureZones.set(id, { isolated: false, isolatedAt: null, reason: null });

        this.metrics.domains++;

        console.log(`🌐 Runtime Domain Registered | DOMAIN: ${id} | ISOLATED: ${isolated} | CRITICAL: ${critical}`);
    }

    /* ========================================================
       GET DOMAIN
    ======================================================== */

    getDomain(id) {
        return this.domains.get(id);
    }

    /* ========================================================
       EXECUTION ACCESS (محسن مع عزل الفشل)
    ======================================================== */

    canExecute({ domain, task, sourceDomain = null }) {

        const info = this.domains.get(domain);
        if (!info) return false;

        // التحقق من العزل
        const failureZone = this.failureZones.get(domain);
        if (failureZone?.isolated) {
            this.metrics.domainFailures++;
            this.publishDomainWarning(domain, 'domain_isolated', { reason: failureZone.reason });
            return false;
        }

        // التحقق من الصحة
        const health = this.domainHealth.get(domain) || 100;
        if (health <= 15) {
            this.metrics.domainFailures++;
            this.isolateDomain(domain, 'health_critical');
            return false;
        }

        // التحقق من الحمل
        const load = this.domainLoad.get(domain) || 0;
        if (!this.checkResourceLimit(domain, load)) {
            return false;
        }

        // التحقق من الحمل الزائد
        if (load >= 90 && !info.critical) {
            this.metrics.overloadProtections++;
            return false;
        }

        // التحقق من أمان التواصل بين domains
        if (sourceDomain && !this.canCommunicate(sourceDomain, domain)) {
            this.metrics.crossDomainBlocks++;
            this.communicationRules.blockedCommunications.push({
                from: sourceDomain,
                to: domain,
                timestamp: Date.now()
            });

            // الاحتفاظ بآخر 100 اتصال ممنوع
            if (this.communicationRules.blockedCommunications.length > 100) {
                this.communicationRules.blockedCommunications.shift();
            }

            return false;
        }

        return true;
    }

    /* ========================================================
       DOMAIN ISOLATION (عزل الفشل)
    ======================================================== */

    isolateDomain(domain, reason) {

        const info = this.domains.get(domain);
        if (!info) return;

        const failureZone = this.failureZones.get(domain);
        if (failureZone?.isolated) return;

        this.failureZones.set(domain, {
            isolated: true,
            isolatedAt: Date.now(),
            reason
        });

        this.metrics.failureIsolations++;

        this.isolatedFailures.push({
            domain,
            reason,
            timestamp: Date.now(),
            health: this.domainHealth.get(domain),
            load: this.domainLoad.get(domain)
        });

        // الاحتفاظ بآخر 50 عزل
        if (this.isolatedFailures.length > 50) {
            this.isolatedFailures.shift();
        }

        console.warn(`⚠️ Domain ISOLATED: ${domain} | REASON: ${reason}`);

        this.publishDomainIsolation(domain, reason);

        // جدولة محاولة التعافي بعد 30 ثانية
        setTimeout(() => {
            this.attemptDomainRecovery(domain);
        }, 30000);
    }

    attemptDomainRecovery(domain) {

        const failureZone = this.failureZones.get(domain);
        if (!failureZone?.isolated) return;

        const health = this.domainHealth.get(domain) || 100;

        if (health > 40) {
            this.failureZones.set(domain, {
                isolated: false,
                isolatedAt: null,
                reason: null
            });

            // تحديث حالة domain
            const info = this.domains.get(domain);
            if (info) {
                info.status = 'recovering';
                setTimeout(() => {
                    if (info.status === 'recovering') info.status = 'active';
                }, 5000);
            }

            console.log(`🌐 Domain RECOVERED: ${domain}`);
            this.publishDomainRecovery(domain);
        }
    }

    /* ========================================================
       LOAD MANAGEMENT
    ======================================================== */

    increaseLoad(domain, amount = 5) {

        const current = this.domainLoad.get(domain) || 0;
        const next = Math.min(100, current + amount);
        this.domainLoad.set(domain, next);

        this.evaluateDomain(domain);
    }

    releaseLoad(domain, amount = 5) {

        const current = this.domainLoad.get(domain) || 0;
        const next = Math.max(0, current - amount);
        this.domainLoad.set(domain, next);

        this.evaluateDomain(domain);
    }

    /* ========================================================
       DOMAIN EVALUATION (محسن)
    ======================================================== */

    evaluateDomain(domain) {

        const load = this.domainLoad.get(domain) || 0;
        let health = 100;

        // حساب الصحة بناءً على الحمل
        if (load >= 80) {
            health -= 50;
        } else if (load >= 60) {
            health -= 25;
        } else if (load >= 40) {
            health -= 10;
        }

        // تطبيق سياسات الطوارئ
        const info = this.domains.get(domain);
        if (info?.status === 'degraded') {
            health -= 20;
        }

        this.domainHealth.set(domain, Math.max(0, health));

        // إشعار عند الضغط
        if (health <= 40) {
            this.publishDomainPressure(domain, health);
        }

        // عزل تلقائي عند الانهيار
        if (health <= 10 && !this.failureZones.get(domain)?.isolated) {
            this.isolateDomain(domain, 'health_collapse');
        }
    }

    /* ========================================================
       CRITICAL / RECOVERY POLICIES
    ======================================================== */

    activateCriticalDomainPolicies() {

        for (const [domain, info] of this.domains) {
            const policy = this.escalationPolicies.get(domain);
            if (policy) {
                info.status = 'degraded';
                console.log(`🌐 Domain ${domain} degraded due to critical mode (policy: ${policy.onCritical})`);
            }
        }
    }

    activateRecoveryDomainPolicies() {

        for (const [domain, info] of this.domains) {
            if (info.status === 'degraded') {
                info.status = 'recovering';
                setTimeout(() => {
                    if (this.domains.get(domain)?.status === 'recovering') {
                        this.domains.get(domain).status = 'active';
                    }
                }, 10000);
            }
        }
    }

    handlePredictedSaturation(prediction) {

        const domain = prediction.metadata?.domain;
        if (domain) {
            console.log(`🌐 Cognitive prediction: domain ${domain} may saturate. Preparing isolation.`);
            // إجراءات استباقية
            this.increaseLoad(domain, 20); // تسجيل حمل وهمي للتحضير
        }
    }

    /* ========================================================
       MONITORING (محسن)
    ======================================================== */

    startMonitoring() {

        this._monitorInterval = setInterval(() => {
            this.monitorDomains();
        }, 5000);
    }

    monitorDomains() {

        for (const domain of this.domains.keys()) {
            this.recoverDomain(domain);
        }
    }

    recoverDomain(domain) {

        const load = this.domainLoad.get(domain) || 0;

        // تقليل الحمل تدريجياً
        if (load > 0) {
            this.releaseLoad(domain, 3);
        }

        // استعادة الصحة
        const health = this.domainHealth.get(domain) || 100;
        if (health < 100) {
            const newHealth = Math.min(100, health + 2);
            this.domainHealth.set(domain, newHealth);
            this.metrics.domainRecoveries++;
        }

        // محاولة إلغاء العزل إذا كان ممكناً
        const failureZone = this.failureZones.get(domain);
        if (failureZone?.isolated && health > 30) {
            this.attemptDomainRecovery(domain);
        }
    }

    /* ========================================================
       ISOLATED EXECUTION (محسن)
    ======================================================== */

    executeInDomain({ domain, callback, sourceDomain = null, taskId = null }) {

        const info = this.domains.get(domain);
        if (!info) {
            console.error(`❌ Domain not found: ${domain}`);
            return false;
        }

        if (!this.canExecute({ domain, sourceDomain })) {
            console.warn(`❌ Domain Execution Denied | DOMAIN: ${domain} | SOURCE: ${sourceDomain || 'unknown'}`);
            return false;
        }

        // تسجيل بدء التنفيذ
        const startTime = performance.now();

        try {
            this.increaseLoad(domain);

            const result = callback?.();

            this.metrics.isolatedExecutions++;

            // تسجيل وقت التنفيذ للتحليل
            const executionTime = performance.now() - startTime;
            if (executionTime > 100) {
                this.publishDomainWarning(domain, 'slow_execution', { executionTime, taskId });
            }

            return result;

        } catch (error) {
            console.error(`❌ Domain Failure | DOMAIN: ${domain} | ERROR:`, error);

            this.metrics.domainFailures++;

            // عزل domain عند فشل متكرر
            const failureCount = this.isolatedFailures.filter(f => f.domain === domain && f.timestamp > Date.now() - 60000).length;
            if (failureCount >= 3) {
                this.isolateDomain(domain, 'repeated_failures');
            }

            return false;

        } finally {
            this.releaseLoad(domain);
        }
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishDomainPressure(domain, health) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:domain:pressure', {
                domain,
                health,
                load: this.domainLoad.get(domain),
                status: this.domains.get(domain)?.status,
                timestamp: Date.now()
            });
        }
    }

    publishDomainWarning(domain, type, metadata = {}) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:domain:warning', {
                domain,
                type,
                metadata,
                timestamp: Date.now()
            });
        }
    }

    publishDomainIsolation(domain, reason) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:domain:isolated', {
                domain,
                reason,
                timestamp: Date.now()
            });
        }
    }

    publishDomainRecovery(domain) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:domain:recovered', {
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
            bus.publishWithoutMiddleware('runtime-execution-domains:ready', {
                domains: this.domains.size,
                isolationEnabled: this.isolationEnabled,
                communicationPolicy: this.communicationRules.defaultPolicy,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        const domainsStatus = [];

        for (const [id, info] of this.domains) {
            domainsStatus.push({
                id,
                priority: info.priority,
                isolated: info.isolated,
                critical: info.critical,
                status: info.status,
                health: this.domainHealth.get(id),
                load: this.domainLoad.get(id),
                failureIsolated: this.failureZones.get(id)?.isolated || false
            });
        }

        return {
            domains: this.domains.size,
            isolation: this.isolationEnabled,
            metrics: { ...this.metrics },
            loads: Object.fromEntries(this.domainLoad),
            health: Object.fromEntries(this.domainHealth),
            isolatedFailures: this.isolatedFailures.slice(-10),
            blockedCommunications: this.communicationRules.blockedCommunications.slice(-10),
            domainsStatus
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._monitorInterval) {
            clearInterval(this._monitorInterval);
            this._monitorInterval = null;
        }

        this.domains.clear();
        this.domainHealth.clear();
        this.domainLoad.clear();
        this.failureZones.clear();
        this.resourceLimits.clear();
        this.communicationRules.allowedPairs.clear();
        this.escalationPolicies.clear();

        console.log('🌐 Runtime Execution Domains Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeExecutionDomains =
    new SovereignRuntimeExecutionDomains();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_EXECUTION_DOMAINS =
    sovereignRuntimeExecutionDomains;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register('execution-domains', sovereignRuntimeExecutionDomains);
}
