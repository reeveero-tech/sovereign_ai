/* ============================================================
   Sovereign AI — runtime-bus.js
   الإصدار: 7.2.0 (Enterprise Runtime Bus)
   ناقل الاتصال السيادي - العمود الفقري للـ Runtime
   الوظيفة: Transport, Routing, Middleware, Telemetry, Error Handling
   ============================================================ */

class SovereignRuntimeBus {

    constructor() {

        this.channels = new Map();

        this.middlewares = [];

        // REFACTOR: قائمة القنوات الأساسية التي لا يمكن حذفها أبداً
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
            'runtime:errors'  // ✅ إضافة قناة الأخطاء كلاحقة
        ]);

        // ✅ Telemetry counters (للـ Runtime Observability المستقبلية)
        this.telemetry = {
            messagesProcessed: 0,
            messagesFailed: 0,
            totalDispatchTime: 0,
            averageDispatchTime: 0
        };

        // تجنب استخدام window.SOVEREIGN_BUS داخل الكلاس نفسه
        console.log(
            '🛰 Runtime Bus Initialized (Enterprise Hybrid Mode)'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {
        this.registerDefaultChannels();
        this.setupSelfTelemetry();
    }

    /* ========================================================
       DEFAULT CHANNELS REGISTRATION
    ======================================================== */

    registerDefaultChannels() {
        // ✅ استخدام defaultChannels Set بدلاً من array عادي
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
        // الاشتراك في قناة الأخطاء لمراقبة صحة Bus نفسه
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
        
        // ✅ Enterprise-grade: إرجاع دالة unsubscribe
        return () => this.unsubscribe(channel, listener);
    }

    /* ========================================================
       PUBLISH (Message Lifecycle كامل)
    ======================================================== */
    publish(channel, payload = {}) {
        // بدء计时 لحساب الـ dispatch time
        const startTime = performance.now();

        if (!this.channels.has(channel)) {
            console.warn(`Bus: Channel "${channel}" does not exist. Message ignored.`);
            return;
        }

        let message = {
            channel,
            payload,
            timestamp: Date.now(),
            id: this.generateMessageId()
        };

        // ============================================
        // 1. MIDDLEWARE PIPELINE
        // ============================================
        let processedMessage = message;
        
        for (const middleware of this.middlewares) {
            try {
                const result = middleware(processedMessage);
                if (result) {
                    processedMessage = result;
                }
            } catch (error) {
                console.error(`Bus Middleware Error on channel "${channel}":`, error);
            }
        }

        // ============================================
        // 2. LISTENER DISPATCH
        // ============================================
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

        // ============================================
        // 3. TELEMETRY UPDATE
        // ============================================
        const endTime = performance.now();
        const dispatchTime = endTime - startTime;
        
        this.telemetry.messagesProcessed++;
        this.telemetry.totalDispatchTime += dispatchTime;
        this.telemetry.averageDispatchTime = 
            this.telemetry.totalDispatchTime / this.telemetry.messagesProcessed;

        // ============================================
        // 4. ERROR HANDLING (مع Guard ضد الـ Recursion)
        // ============================================
        // ✅ مهم جداً: منع الـ recursion في error channel
        if (errors.length > 0 && channel !== 'runtime:errors') {
            if (this.hasChannel('runtime:errors')) {
                // استخدام publish مباشرة (مع تجنب الـ middleware لتجنب الـ loops)
                this.publishWithoutMiddleware('runtime:errors', {
                    sourceChannel: channel,
                    errors: errors.map(e => e.message),
                    originalPayload: payload,
                    telemetry: {
                        messagesProcessed: this.telemetry.messagesProcessed,
                        messagesFailed: this.telemetry.messagesFailed
                    }
                });
            } else {
                console.error('CRITICAL: errors occurred but runtime:errors channel not available', errors);
            }
        }
    }

    /* ========================================================
       PUBLISH WITHOUT MIDDLEWARE (للأخطاء الحرجة)
       لتجنب الـ infinite loops
    ======================================================== */
    publishWithoutMiddleware(channel, payload = {}) {
        if (!this.channels.has(channel)) return;

        const message = {
            channel,
            payload,
            timestamp: Date.now(),
            id: this.generateMessageId(),
            isErrorEvent: true
        };

        const listeners = this.channels.get(channel);
        for (const listener of listeners) {
            try {
                listener(message);
            } catch (error) {
                console.error(`CRITICAL: Error in runtime:errors listener`, error);
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
        
        // ✅ الحماية: لا تحذف القنوات الأساسية أبداً
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
       ENHANCED STATUS (مع Telemetry)
    ======================================================== */
    getStatus() {
        const status = {
            channels: [...this.channels.keys()],
            middlewaresCount: this.middlewares.length,
            totalListeners: 0,
            isHybrid: true,
            registeredInRegistry: !!window.SOVEREIGN?.get('bus'),
            defaultChannelsProtected: [...this.defaultChannels],
            telemetry: {
                messagesProcessed: this.telemetry.messagesProcessed,
                messagesFailed: this.telemetry.messagesFailed,
                averageDispatchTimeMs: parseFloat(this.telemetry.averageDispatchTime.toFixed(2)),
                totalDispatchTimeMs: parseFloat(this.telemetry.totalDispatchTime.toFixed(2))
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
        // ✅ حذف القنوات التي ليست أساسية فقط
        for (const [channel, listeners] of this.channels.entries()) {
            if (!this.defaultChannels.has(channel)) {
                this.channels.delete(channel);
            } else {
                // تنظيف الـ listeners فقط للقنوات الأساسية (تفريغها)
                this.channels.set(channel, []);
            }
        }
        
        // إعادة التسجيل الافتراضي للقنوات الأساسية
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
            averageDispatchTime: 0
        };
        console.log('📊 Bus telemetry reset');
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
   - Legacy Global: للتوافق مع الأنظمة القديمة
   - Unified Registry: للبدء في توحيد النظام الجديد
============================================================ */

const sovereignBus = new SovereignRuntimeBus();

/* =========================================
   Legacy Global (للتوافق مع الأنظمة القديمة)
========================================= */

window.SOVEREIGN_BUS = sovereignBus;

/* =========================================
   Unified Registry (التسجيل في النواة الموحدة)
========================================= */

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('bus', sovereignBus);
    console.log('✅ Bus registered in Unified Registry');
} else {
    console.warn('⚠️ Unified Registry not yet available. Bus registered as legacy global only (Hybrid Mode).');
}

// ============================================================
// إشعار Legacy Systems (Migration Support)
// ============================================================
if (window.SOVEREIGN_EVENTS) {
    window.SOVEREIGN_EVENTS.emit('bus:ready', {
        timestamp: Date.now(),
        status: sovereignBus.getStatus()
    });
}
