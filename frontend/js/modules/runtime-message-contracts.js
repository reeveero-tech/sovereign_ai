/* ============================================================
   Sovereign AI — runtime-message-contracts.js
   الإصدار: 10.0.0
   عقود الرسائل السيادية للـ Runtime
   ============================================================ */

class SovereignRuntimeMessageContracts {

    constructor() {

        /* =========================================
           CONTRACTS (محسن مع schema كامل)
        ========================================= */

        this.contracts =
            new Map();

        /* =========================================
           VALIDATION
        ========================================= */

        this.strictMode =
            true;

        /* =========================================
           REJECTION LOG (سجل الرسائل المرفوضة)
        ========================================= */

        this.rejectionLog = [];
        this.maxRejectionLog = 200;

        /* =========================================
           SCHEMA VERSIONS (للتطور الآمن)
        ========================================= */

        this.schemaVersions = new Map();  // channel → version

        /* =========================================
           METRICS (محسن)
        ========================================= */

        this.metrics = {

            validated: 0,
            rejected: 0,
            normalized: 0,
            malformed: 0,
            secured: 0,
            versionMismatches: 0,
            sizeExceeded: 0,
            typeMismatches: 0
        };

        /* =========================================
           SIZE LIMITS (حدود الحجم)
        ========================================= */

        this.sizeLimits = new Map();  // channel → maxSize in bytes

        console.log('📜 Runtime Message Contracts Initialized (Sovereign Contract Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerDefaultContracts();
        this.registerDefaultSizeLimits();
        this.bindRuntimeBus();
        this.startMetricsReporter();
        this.publishReady();
    }

    /* ========================================================
       DEFAULT CONTRACTS (محسن مع أنواع الحقول)
    ======================================================== */

    registerDefaultContracts() {

        this.registerContract({
            channel: 'telemetry:event',
            version: '1.0.0',
            required: ['entry', 'timestamp'],
            fields: {
                entry: { type: 'object', required: true },
                timestamp: { type: 'number', required: true },
                stability: { type: 'number', required: false, default: 100 }
            }
        });

        this.registerContract({
            channel: 'telemetry:snapshot',
            version: '1.0.0',
            required: ['snapshot', 'timestamp'],
            fields: {
                snapshot: { type: 'object', required: true },
                timestamp: { type: 'number', required: true },
                metrics: { type: 'object', required: false, default: {} }
            }
        });

        this.registerContract({
            channel: 'runtime:cognition:prediction',
            version: '2.0.0',
            required: ['prediction', 'timestamp'],
            fields: {
                prediction: { type: 'object', required: true },
                timestamp: { type: 'number', required: true },
                confidence: { type: 'number', required: false, default: 50 }
            }
        });

        this.registerContract({
            channel: 'runtime:cognition:anomaly',
            version: '1.0.0',
            required: ['anomaly', 'timestamp'],
            fields: {
                anomaly: { type: 'object', required: true },
                timestamp: { type: 'number', required: true },
                severity: { type: 'string', required: false, default: 'warning' }
            }
        });

        this.registerContract({
            channel: 'runtime:governor:decision',
            version: '1.0.0',
            required: ['mode', 'decision', 'timestamp'],
            fields: {
                mode: { type: 'string', required: true },
                decision: { type: 'object', required: true },
                timestamp: { type: 'number', required: true },
                level: { type: 'string', required: false, default: 'normal' }
            }
        });

        this.registerContract({
            channel: 'runtime:mode:transition',
            version: '1.0.0',
            required: ['previous', 'current', 'timestamp'],
            fields: {
                previous: { type: 'string', required: true },
                current: { type: 'string', required: true },
                timestamp: { type: 'number', required: true },
                source: { type: 'string', required: false, default: 'unknown' }
            }
        });

        this.registerContract({
            channel: 'runtime:domain:pressure',
            version: '1.0.0',
            required: ['domain', 'health', 'load', 'timestamp'],
            fields: {
                domain: { type: 'string', required: true },
                health: { type: 'number', required: true },
                load: { type: 'number', required: true },
                timestamp: { type: 'number', required: true }
            }
        });

        this.registerContract({
            channel: 'runtime:domain:isolated',
            version: '1.0.0',
            required: ['domain', 'reason', 'timestamp'],
            fields: {
                domain: { type: 'string', required: true },
                reason: { type: 'string', required: true },
                timestamp: { type: 'number', required: true }
            }
        });

        this.registerContract({
            channel: 'runtime:fairness:deferral',
            version: '1.0.0',
            required: ['taskId', 'deferCount', 'timestamp'],
            fields: {
                taskId: { type: 'string', required: true },
                deferCount: { type: 'number', required: true },
                timestamp: { type: 'number', required: true },
                priority: { type: 'number', required: false, default: 10 }
            }
        });
    }

    /* ========================================================
       SIZE LIMITS
    ======================================================== */

    registerDefaultSizeLimits() {

        this.sizeLimits.set('telemetry:snapshot', 1024 * 100);  // 100KB
        this.sizeLimits.set('telemetry:event', 1024 * 10);      // 10KB
        this.sizeLimits.set('runtime:cognition:prediction', 1024 * 5);   // 5KB
        this.sizeLimits.set('runtime:governor:decision', 1024 * 2);      // 2KB
        // باقي القنوات حد افتراضي 10KB
    }

    checkSizeLimit(channel, payload) {

        const maxSize = this.sizeLimits.get(channel) || 10240; // 10KB default
        const payloadStr = JSON.stringify(payload);
        const size = new Blob([payloadStr]).size;

        if (size > maxSize) {
            this.metrics.sizeExceeded++;
            this.logRejection(channel, `size_exceeded: ${size} > ${maxSize}`);
            return false;
        }

        return true;
    }

    /* ========================================================
       REGISTER CONTRACT (محسن)
    ======================================================== */

    registerContract({ channel, version = '1.0.0', required = [], fields = {} }) {

        this.contracts.set(channel, {
            channel,
            version,
            required,
            fields,
            createdAt: Date.now()
        });

        this.schemaVersions.set(channel, version);

        console.log(`📜 Message Contract Registered | CHANNEL: ${channel} | VERSION: ${version}`);
    }

    /* ========================================================
       LOG REJECTION (تسجيل الرفض)
    ======================================================== */

    logRejection(channel, reason, payload = null) {

        this.rejectionLog.push({
            channel,
            reason,
            payload: payload ? JSON.stringify(payload).substring(0, 500) : null,
            timestamp: Date.now()
        });

        if (this.rejectionLog.length > this.maxRejectionLog) {
            this.rejectionLog.shift();
        }
    }

    /* ========================================================
       BUS (محسن وآمن)
    ======================================================== */

    bindRuntimeBus() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus) return;

        this._originalPublish = bus.publishWithoutMiddleware;

        bus.publishWithoutMiddleware = (channel, payload = {}) => {

            // 1. التحقق من الحجم
            if (!this.checkSizeLimit(channel, payload)) {
                console.warn(`❌ Contract Size Failed | CHANNEL: ${channel} | size limit exceeded`);
                return false;
            }

            // 2. التحقق من صحة الرسالة حسب العقد
            const validation = this.validateMessage({ channel, payload });

            if (!validation.valid) {
                this.metrics.rejected++;
                console.warn(`❌ Contract Validation Failed | CHANNEL: ${channel} | REASON: ${validation.reason}`);
                return false;
            }

            // 3. تطبيع الرسالة
            const normalized = this.normalizeMessage({ channel, payload });

            // 4. تأمين الحمولة
            const secured = this.securePayload(normalized);

            this.metrics.validated++;
            this.metrics.secured++;

            // 5. نشر الرسالة
            return this._originalPublish.call(bus, channel, secured);
        };
    }

    /* ========================================================
       VALIDATION (محسن مع أنواع الحقول)
    ======================================================== */

    validateMessage({ channel, payload }) {

        const contract = this.contracts.get(channel);

        if (!contract) {
            if (this.strictMode) {
                this.logRejection(channel, 'no_contract_found', payload);
                return { valid: false, reason: 'no_contract_found' };
            }
            return { valid: true, reason: 'no_contract_strict_disabled' };
        }

        // 1. التحقق من الحقول المطلوبة
        for (const field of contract.required) {
            if (payload[field] === undefined) {
                this.metrics.malformed++;
                this.logRejection(channel, `missing_required_field: ${field}`, payload);
                return { valid: false, reason: `missing_required_field: ${field}` };
            }
        }

        // 2. التحقق من أنواع الحقول
        for (const [field, config] of Object.entries(contract.fields)) {
            const value = payload[field];
            
            if (config.required && value === undefined) {
                this.metrics.typeMismatches++;
                this.logRejection(channel, `missing_field: ${field}`, payload);
                return { valid: false, reason: `missing_field: ${field}` };
            }

            if (value !== undefined) {
                const actualType = Array.isArray(value) ? 'array' : typeof value;
                const expectedType = config.type;

                if (actualType !== expectedType) {
                    this.metrics.typeMismatches++;
                    this.logRejection(channel, `type_mismatch: ${field} expected ${expectedType} got ${actualType}`, payload);
                    return { valid: false, reason: `type_mismatch: ${field}` };
                }
            }
        }

        // 3. التحقق من التوافق الدلالي (semantic versioning)
        const payloadVersion = payload.__runtime?.version || payload.version;
        if (payloadVersion && payloadVersion !== contract.version) {
            this.metrics.versionMismatches++;
            // لا نرفض، فقط نسجل
            console.warn(`⚠️ Version mismatch | CHANNEL: ${channel} | expected: ${contract.version} | got: ${payloadVersion}`);
        }

        return { valid: true, reason: null };
    }

    /* ========================================================
       NORMALIZATION (محسن)
    ======================================================== */

    normalizeMessage({ channel, payload }) {

        const contract = this.contracts.get(channel);
        const context = window.SOVEREIGN_CONTEXT;

        // إضافة القيم الافتراضية للحقول المفقودة
        let normalizedPayload = { ...payload };

        if (contract) {
            for (const [field, config] of Object.entries(contract.fields)) {
                if (normalizedPayload[field] === undefined && config.default !== undefined) {
                    normalizedPayload[field] = config.default;
                }
            }
        }

        // إضافة metadata التتبع
        const normalized = {
            ...normalizedPayload,
            __runtime: {
                channel,
                normalizedAt: Date.now(),
                traceId: context?.createTraceId?.() || this.generateTraceId(),
                environment: 'runtime',
                version: contract?.version || '10.0.0',
                contractValidated: true
            }
        };

        this.metrics.normalized++;

        return normalized;
    }

    generateTraceId() {

        return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
    }

    /* ========================================================
       SECURE PAYLOAD (محسن)
    ======================================================== */

    securePayload(payload = {}) {

        // تجميد عميق (deep freeze) للحماية
        const deepFreeze = (obj) => {
            Object.freeze(obj);
            Object.values(obj).forEach(value => {
                if (value && typeof value === 'object' && !Object.isFrozen(value)) {
                    deepFreeze(value);
                }
            });
            return obj;
        };

        return deepFreeze({ ...payload });
    }

    /* ========================================================
       CONTRACT INFO
    ======================================================== */

    hasContract(channel) {
        return this.contracts.has(channel);
    }

    getContract(channel) {
        return this.contracts.get(channel);
    }

    getContractVersion(channel) {
        return this.schemaVersions.get(channel);
    }

    /* ========================================================
       METRICS REPORTER
    ======================================================== */

    startMetricsReporter() {

        this._metricsInterval = setInterval(() => {
            this.publishMetrics();
        }, 60000); // كل دقيقة
    }

    publishMetrics() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:contracts:metrics', {
                metrics: { ...this.metrics },
                contractsCount: this.contracts.size,
                rejectionLogSize: this.rejectionLog.length,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       EXPORT
    ======================================================== */

    exportContracts() {
        return Array.from(this.contracts.entries()).map(([channel, contract]) => ({
            channel,
            version: contract.version,
            required: contract.required,
            fields: contract.fields
        }));
    }

    exportRejectionLog(limit = 50) {
        return this.rejectionLog.slice(-limit);
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime-message-contracts:ready', {
                contracts: this.contracts.size,
                strict: this.strictMode,
                schemaVersions: Array.from(this.schemaVersions.entries()),
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        return {
            contracts: this.contracts.size,
            strict: this.strictMode,
            rejectionLogSize: this.rejectionLog.length,
            schemaVersions: Array.from(this.schemaVersions.entries()),
            metrics: { ...this.metrics },
            sizeLimits: Array.from(this.sizeLimits.entries())
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._metricsInterval) {
            clearInterval(this._metricsInterval);
            this._metricsInterval = null;
        }

        // استعادة دالة النشر الأصلية
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (bus && this._originalPublish) {
            bus.publishWithoutMiddleware = this._originalPublish;
        }

        this.contracts.clear();
        this.schemaVersions.clear();
        this.sizeLimits.clear();
        this.rejectionLog = [];

        console.log('📜 Runtime Message Contracts Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeMessageContracts =
    new SovereignRuntimeMessageContracts();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_MESSAGE_CONTRACTS =
    sovereignRuntimeMessageContracts;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register('message-contracts', sovereignRuntimeMessageContracts);
}
