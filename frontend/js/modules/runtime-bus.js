/* ============================================================
   Sovereign AI — runtime-bus.js
   الإصدار: 7.4.0 (Runtime Protocol Gateway)
   
   ناقل الاتصال السيادي - العمود الفقري للـ Runtime
   
   الطبقات المستقبلية (لتجنب Monolith):
     - Transport Engine (نقل الرسائل)
     - Schema Gateway (normalization & validation)
     - Telemetry Layer (القياس والإحصاءات)
     - Middleware Orchestrator (إدارة الـ pipeline)
     - Protocol Validator (التحقق من البروتوكولات)
     - Error Isolation Layer (عزل الأخطاء ومنع الـ recursion)
   
   الأولويات المستقبلية:
     - system channels (أولوية قصوى)
     - critical channels (أولوية عالية)
     - bypass channels (تجاوز الـ middleware)
     - isolated channels (عزل تام)
   ============================================================ */

class SovereignRuntimeBus {

    constructor() {

        this.channels = new Map();

        this.middlewares = [];

        // قائمة القنوات الأساسية التي لا يمكن حذفها أبداً
        this.defaultChannels = new Set([
            'runtime',
            'system',
            'security',
            'analytics',
            'chat',
            'performance',
            'kernel',
            'lifecycle',
            'orchestrator',
            'policy',
            'health',
            'state',
            'migration',
            'runtime:errors'
        ]);

        // ✅ Telemetry counters - مستقبلاً: استخدام rolling window (EWMA) بدلاً من cumulative
        // TODO: استبدال totalDispatchTime بـ rolling average لآخر 1000 رسالة
        this.telemetry = {
            messagesProcessed: 0,
            messagesFailed: 0,
            totalDispatchTime: 0,
            averageDispatchTime: 0,
            messagesNormalized: 0,
            messagesRejected: 0,
            // Future: rollingWindow
            rollingWindowSize: 1000,
            recentDispatchTimes: []  // للاستخدام المستقبلي
        };

        // Cache for access layer
        this._access = null;

        console.log(
            '🛰 Runtime Bus Initialized (Protocol Gateway Mode)'
        );

        this.init();
    }

    /* ========================================================
       ACCESS HELPER (Runtime Access Layer)
    ======================================================== */
    get access() {
        if (!this._access && window.SOVEREIGN_ACCESS) {
            this._access = window.SOVEREIGN_ACCESS;
            console.log('✅ Runtime Bus connected to Runtime Access Layer');
        }
        return this._access;
    }

    /* ========================================================
       GET SCHEMA (Runtime Message Schema)
    ======================================================== */
    getSchema() {
        return this.access?.legacy?.('schema') || window.SOVEREIGN_SCHEMA;
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.registerDefaultChannels();
        this.setupSelfTelemetry();
        this.emitReady();
    }

    /* ========================================================
       EMIT READY (مع تجنب bootstrap race condition)
       
       ✅ FIX 1: استخدام publishWithoutMiddleware بدلاً من this.access?.bus?.()
       لتجنب اعتماد Bus على نفسه أثناء التهيئة
    ======================================================== */
    emitReady() {
        // ✅ مباشرة عبر publishWithoutMiddleware لتجنب الـ race condition
        this.publishWithoutMiddleware('bus:ready', {
            timestamp: Date.now(),
            channelsCount: this.defaultChannels.size,
            version: '7.4.0',
            source: 'runtime-bus'
        });
    }

    /* ========================================================
       DEFAULT CHANNELS REGISTRATION
    ======================================================== */
    registerDefaultChannels() {
        for (const channel of this.defaultChannels) {
            if (!this.channels.has(channel)) {
                this.channels.set(channel, []);
            }
        }
        console.log(`✅ Bus: ${this.defaultChannels.size} default channels registered (protected)`);
    }

    /* ========================================================
       SELF TELEMETRY (مراقبة Bus لنفسه)
    ======================================================== */
    setupSelfTelemetry() {
        this.subscribe('runtime:errors', (message) => {
            this.telemetry.messagesFailed++;
            console.warn(`⚠️ Bus Telemetry: Total failures = ${this.telemetry.messagesFailed}`);
        });
    }

    /* ========================================================
       CREATE CHANNEL
    ======================================================== */
    createChannel(name) {
        if (this.channels.has(name)) return;
        this.channels.set(name, []);
        console.log(`📡 Bus channel created: ${name}`);
    }

    /* ========================================================
       SUBSCRIBE (يُرجع unsubscribe handler)
    ======================================================== */
    subscribe(channel, listener) {
        if (!this.channels.has(channel)) {
            this.createChannel(channel);
        }
        this.channels.get(channel).push(listener);
        return () => this.unsubscribe(channel, listener);
    }

    /* ========================================================
       NORMALIZE MESSAGE (تحويل أي رسالة إلى الشكل القياسي)
       هذه هي "Runtime Protocol Gateway"
    ======================================================== */
    normalizeMessage(rawChannel, rawPayload, rawId) {
        const schema = this.getSchema();
        
        if (schema?.create) {
            const standardizedMessage = schema.create({
                type: `runtime.${rawChannel}`,
                source: 'runtime-bus',
                channel: rawChannel,
                payload: rawPayload,
                meta: {
                    busManaged: true,
                    normalizedAt: Date.now(),
                    busVersion: '7.4.0'
                }
            });
            
            this.telemetry.messagesNormalized++;
            return standardizedMessage;
        }
        
        // Legacy Fallback (Migration Phase)
        const messageId = rawId || this.generateMessageId();
        
        return {
            id: messageId,
            type: `runtime.${rawChannel}`,
            version: 'legacy',
            source: 'runtime-bus',
            channel: rawChannel,
            payload: rawPayload,
            meta: {
                legacy: true,
                normalizedAt: Date.now(),
                busVersion: '7.4.0'
            },
            timestamp: Date.now()
        };
    }
    
    /* ========================================================
       VALIDATE MESSAGE (التحقق من صحة الرسالة حسب الـ Schema)
    ======================================================== */
    validateMessage(message) {
        const schema = this.getSchema();
        
        if (schema?.validate) {
            const isValid = schema.validate(message);
            if (!isValid) {
                this.telemetry.messagesRejected++;
                console.warn(`
🚫 Runtime Message Schema Rejected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Channel: ${message.channel}
Type: ${message.type}
Id: ${message.id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                `);
                return false;
            }
        }
        
        return true;
    }

    /* ========================================================
       UPDATE TELEMETRY (مع دعم rolling window مستقبلاً)
       
       ✅ FIX 2: تمهيد لاستخدام rolling average بدلاً من cumulative
    ======================================================== */
    updateTelemetry(dispatchTime) {
        this.telemetry.messagesProcessed++;
        this.telemetry.totalDispatchTime += dispatchTime;
        this.telemetry.averageDispatchTime = 
            this.telemetry.totalDispatchTime / this.telemetry.messagesProcessed;
        
        // TODO: استبدال cumulative بـ rolling window (EWMA)
        // this.telemetry.recentDispatchTimes.push(dispatchTime);
        // if (this.telemetry.recentDispatchTimes.length > this.telemetry.rollingWindowSize) {
        //     this.telemetry.recentDispatchTimes.shift();
        // }
        // const sum = this.telemetry.recentDispatchTimes.reduce((a, b) => a + b, 0);
        // this.telemetry.averageDispatchTime = sum / this.telemetry.recentDispatchTimes.length;
    }

    /* ========================================================
       PUBLISH (Message Lifecycle كامل مع Protocol Gateway)
       
       الآن: Schema → Normalization → Validation → Middleware → Contracts → Delivery
    ======================================================== */
    publish(channel, payload = {}) {
        const startTime = performance.now();

        if (!this.channels.has(channel)) {
            console.warn(`Bus: Channel "${channel}" does not exist. Message ignored.`);
            return;
        }

        // 1. NORMALIZE MESSAGE
        let message = this.normalizeMessage(channel, payload);
        
        // 2. VALIDATE MESSAGE
        if (!this.validateMessage(message)) {
            return;
        }

        // 3. MIDDLEWARE PIPELINE
        let processedMessage = message;
        
        for (const middleware of this.middlewares) {
            try {
                const result = middleware(processedMessage);
                if (result === null) {
                    console.warn(`🚫 Runtime Message Blocked by Middleware
Channel: ${channel}
MessageId: ${message.id}
                    `);
                    this.telemetry.messagesRejected++;
                    return;
                }
                processedMessage = result || processedMessage;
            } catch (error) {
                console.error(`Bus Middleware Error on channel "${channel}":`, error);
            }
        }

        // 4. LISTENER DISPATCH
        const listeners = this.channels.get(channel);
        const errors = [];

        for (const listener of listeners) {
            try {
                listener(processedMessage);
            } catch (error) {
                console.error(`Bus Listener Error on channel "${channel}":`, error);
                errors.push(error);
            }
        }

        // 5. TELEMETRY UPDATE
        const dispatchTime = performance.now() - startTime;
        this.updateTelemetry(dispatchTime);

        // 6. ERROR HANDLING
        if (errors.length > 0 && channel !== 'runtime:errors') {
            if (this.hasChannel('runtime:errors')) {
                this.publishWithoutMiddleware('runtime:errors', {
                    sourceChannel: channel,
                    errors: errors.map(e => e.message),
                    originalPayload: payload,
                    telemetry: {
                        messagesProcessed: this.telemetry.messagesProcessed,
                        messagesFailed: this.telemetry.messagesFailed,
                        messagesNormalized: this.telemetry.messagesNormalized,
                        messagesRejected: this.telemetry.messagesRejected
                    }
                });
            } else {
                console.error('CRITICAL: errors occurred but runtime:errors channel not available', errors);
            }
        }
    }

    /* ========================================================
       PUBLISH WITHOUT MIDDLEWARE (للأخطاء الحرجة)
       
       ✅ FIX 4: هذا هو الأساس لـ Runtime Priority Channels مستقبلاً
       
       الاستخدامات المستقبلية:
         - system channels (أولوية قصوى، تجاوز كامل)
         - critical channels (أولوية عالية، تجاوز جزئي)
         - bypass channels (تجاوز الـ middleware فقط)
         - isolated channels (عزل تام، قناة منفصلة)
    ======================================================== */
    publishWithoutMiddleware(channel, payload = {}) {
        if (!this.channels.has(channel)) return;

        const message = {
            id: this.generateMessageId(),
            type: `runtime.${channel}`,
            version: 'critical',
            source: 'runtime-bus',
            channel,
            payload,
            meta: {
                isErrorEvent: true,
                bypassedMiddleware: true,
                priority: 'system',  // ✅ الأساس لـ Priority Channels
                timestamp: Date.now()
            },
            timestamp: Date.now()
        };

        const listeners = this.channels.get(channel);
        for (const listener of listeners) {
            try {
                listener(message);
            } catch (error) {
                console.error(`CRITICAL: Error in ${channel} listener`, error);
            }
        }
    }

    /* ========================================================
       MIDDLEWARE MANAGEMENT
    ======================================================== */
    use(middleware) {
        if (typeof middleware !== 'function') {
            console.warn('Bus: Middleware must be a function');
            return;
        }
        this.middlewares.push(middleware);
        console.log(`🔧 Bus middleware added (total: ${this.middlewares.length})`);
    }

    /* ========================================================
       UNSUBSCRIBE (مع حماية القنوات الأساسية)
    ======================================================== */
    unsubscribe(channel, listener) {
        if (!this.channels.has(channel)) return;

        const listeners = this.channels.get(channel);
        const filtered = listeners.filter(l => l !== listener);
        
        if (filtered.length === 0 && !this.defaultChannels.has(channel)) {
            this.channels.delete(channel);
        } else {
            this.channels.set(channel, filtered);
        }
    }

    /* ========================================================
       UTILITIES
    ======================================================== */
    generateMessageId() {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    hasChannel(channel) {
        return this.channels.has(channel);
    }

    getChannelListenersCount(channel) {
        return this.channels.get(channel)?.length || 0;
    }

    /* ========================================================
       ENHANCED STATUS (مع Telemetry محسّنة)
    ======================================================== */
    getStatus() {
        const status = {
            channels: [...this.channels.keys()],
            middlewaresCount: this.middlewares.length,
            totalListeners: 0,
            isHybrid: true,
            protocolGateway: true,
            registeredInRegistry: !!window.SOVEREIGN?.get('bus'),
            defaultChannelsProtected: [...this.defaultChannels],
            telemetry: {
                messagesProcessed: this.telemetry.messagesProcessed,
                messagesFailed: this.telemetry.messagesFailed,
                messagesNormalized: this.telemetry.messagesNormalized,
                messagesRejected: this.telemetry.messagesRejected,
                averageDispatchTimeMs: parseFloat(this.telemetry.averageDispatchTime.toFixed(2)),
                totalDispatchTimeMs: parseFloat(this.telemetry.totalDispatchTime.toFixed(2)),
                rollingWindowSize: this.telemetry.rollingWindowSize  // تمهيد للمستقبل
            }
        };

        for (const listeners of this.channels.values()) {
            status.totalListeners += listeners.length;
        }

        return status;
    }

    /* ========================================================
       CLEANUP (مع الحفاظ على القنوات الأساسية)
    ======================================================== */
    clearAllChannels() {
        for (const [channel] of this.channels.entries()) {
            if (!this.defaultChannels.has(channel)) {
                this.channels.delete(channel);
            } else {
                this.channels.set(channel, []);
            }
        }
        this.registerDefaultChannels();
        console.log('🧹 Bus: Non-default channels cleared, default channels reset');
    }

    clearMiddleware() {
        this.middlewares = [];
        console.log('🧹 Bus: All middleware cleared');
    }

    /* ========================================================
       RESET TELEMETRY
    ======================================================== */
    resetTelemetry() {
        this.telemetry = {
            messagesProcessed: 0,
            messagesFailed: 0,
            totalDispatchTime: 0,
            averageDispatchTime: 0,
            messagesNormalized: 0,
            messagesRejected: 0,
            rollingWindowSize: 1000,
            recentDispatchTimes: []
        };
        console.log('📊 Bus telemetry reset');
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
============================================================ */

const sovereignBus = new SovereignRuntimeBus();

window.SOVEREIGN_BUS = sovereignBus;

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('bus', sovereignBus);
    console.log('✅ Bus registered in Unified Registry');
} else {
    console.warn('⚠️ Unified Registry not yet available. Bus registered as legacy global only (Hybrid Mode).');
}

if (window.SOVEREIGN_EVENTS) {
    window.SOVEREIGN_EVENTS.emit('bus:ready', {
        timestamp: Date.now(),
        status: sovereignBus.getStatus()
    });
}
