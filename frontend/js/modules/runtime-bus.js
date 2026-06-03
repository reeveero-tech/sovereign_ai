/* ============================================================
   Sovereign AI — runtime-bus.js
   الإصدار: 7.6.0 (Distributed Runtime Operating System Kernel)
   
   ⚠️ IMPORTANT: This file is approaching "Bus Saturation Point"
   Future decomposition required:
     - TransportEngine (النقل الأساسي)
     - ProtocolGateway (normalization & validation)
     - ContextManager (propagation & lineage)
     - TelemetryEngine (metrics & rolling windows)
     - MiddlewareOrchestrator (pipeline management)
     - ErrorIsolationLayer (fault boundaries)
   
   المرحلة القادمة (بعد التقسيم):
     - Runtime Trace Engine
     - Distributed Trace Collector
     - Runtime Session Manager
     - Unified Runtime Envelope
     - Runtime Priority Routing
     - Service Lifecycle Enforcement
   ============================================================ */

class SovereignRuntimeBus {

    constructor() {

        this.channels = new Map();

        this.middlewares = [];

        // قائمة القنوات الأساسية
        this.defaultChannels = new Set([
            'runtime', 'system', 'security', 'analytics', 'chat',
            'performance', 'kernel', 'lifecycle', 'orchestrator',
            'policy', 'health', 'state', 'migration', 'runtime:errors'
        ]);

        // ✅ Telemetry مع rolling window فعال
        this.telemetry = {
            messagesProcessed: 0,
            messagesFailed: 0,
            totalDispatchTime: 0,
            averageDispatchTime: 0,
            messagesNormalized: 0,
            messagesRejected: 0,
            messagesWithContext: 0,
            messagesMissingContext: 0,
            rollingWindowSize: 1000,
            recentDispatchTimes: [],      // ✅ الآن سيتم استخدامها
            rollingAverageDispatchTime: 0  // ✅ rolling average الحقيقي
        };

        // Cache for access layer
        this._access = null;

        // ✅ تخزين آخر traceId للـ parent-child relationship
        this.lastTraceId = null;

        console.log(
            '🛰 Runtime Bus Initialized (Distributed Runtime Kernel)'
        );

        this.init();
    }

    /* ========================================================
       ACCESS HELPER
    ======================================================== */
    get access() {
        if (!this._access && window.SOVEREIGN_ACCESS) {
            this._access = window.SOVEREIGN_ACCESS;
            console.log('✅ Runtime Bus connected to Runtime Access Layer');
        }
        return this._access;
    }

    /* ========================================================
       GET SCHEMA & CONTEXT MANAGER
    ======================================================== */
    getSchema() {
        return this.access?.legacy?.('schema') || window.SOVEREIGN_SCHEMA;
    }

    getContextManager() {
        return this.access?.legacy?.('context') || window.SOVEREIGN_CONTEXT;
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.registerDefaultChannels();
        this.setupSelfTelemetry();
        this.emitReady();
    }

    emitReady() {
        this.publishWithoutMiddleware('bus:ready', {
            timestamp: Date.now(),
            channelsCount: this.defaultChannels.size,
            version: '7.6.0',
            source: 'runtime-bus',
            contextSupported: !!this.getContextManager()
        });
    }

    registerDefaultChannels() {
        for (const channel of this.defaultChannels) {
            if (!this.channels.has(channel)) {
                this.channels.set(channel, []);
            }
        }
        console.log(`✅ Bus: ${this.defaultChannels.size} default channels registered`);
    }

    setupSelfTelemetry() {
        this.subscribe('runtime:errors', (message) => {
            this.telemetry.messagesFailed++;
        });
    }

    createChannel(name) {
        if (this.channels.has(name)) return;
        this.channels.set(name, []);
        console.log(`📡 Bus channel created: ${name}`);
    }

    subscribe(channel, listener) {
        if (!this.channels.has(channel)) this.createChannel(channel);
        this.channels.get(channel).push(listener);
        return () => this.unsubscribe(channel, listener);
    }

    generateMessageId() {
        return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateTraceId() {
        return `trace_${Date.now()}_${Math.random().toString(36).substr(2, 12)}`;
    }

    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
    }

    /* ========================================================
       NORMALIZE MESSAGE
    ======================================================== */
    normalizeMessage(rawChannel, rawPayload, rawId) {
        const schema = this.getSchema();
        const messageId = rawId || this.generateMessageId();
        
        if (schema?.create) {
            const standardizedMessage = schema.create({
                type: `runtime.${rawChannel}`,
                source: 'runtime-bus',
                channel: rawChannel,
                payload: rawPayload,
                meta: {
                    busManaged: true,
                    normalizedAt: Date.now(),
                    busVersion: '7.6.0'
                }
            });
            this.telemetry.messagesNormalized++;
            return standardizedMessage;
        }
        
        return {
            id: messageId,
            type: `runtime.${rawChannel}`,
            version: 'legacy',
            source: 'runtime-bus',
            channel: rawChannel,
            payload: rawPayload,
            meta: { legacy: true, normalizedAt: Date.now(), busVersion: '7.6.0' },
            timestamp: Date.now()
        };
    }
    
    /* ========================================================
       ATTACH RUNTIME CONTEXT (مع Distributed Lineage)
       
       ✅ FIX 1: Lineage الحقيقي مع causality chain
    ======================================================== */
    attachRuntimeContext(message, channel) {
        const contextManager = this.getContextManager();
        const currentTraceId = this.generateTraceId();
        const parentTraceId = this.lastTraceId;  // للحفاظ على causality chain
        
        if (contextManager?.attach) {
            const attachedMessage = contextManager.attach(message, {
                source: 'runtime-bus',
                scope: channel,
                parentTraceId: parentTraceId  // ✅ تمرير الـ parent للـ lineage
            });
            this.telemetry.messagesWithContext++;
            this.lastTraceId = attachedMessage.meta?.context?.traceId || currentTraceId;
            return attachedMessage;
        }
        
        // ✅ Fallback مع lineage كامل
        if (!message.meta) message.meta = {};
        
        // ✅ FIX 3: تقسيم meta إلى أقسام (Runtime Envelope)
        message.meta = {
            context: {
                sessionId: this.generateSessionId(),
                traceId: currentTraceId,
                parentTraceId: parentTraceId,
                scope: channel,
                source: 'runtime-bus-fallback',
                lineage: [
                    {
                        service: 'runtime-bus',
                        timestamp: Date.now(),
                        action: 'attach_fallback',
                        traceId: currentTraceId,
                        parentTraceId: parentTraceId
                    }
                ]
            },
            telemetry: {
                createdAt: Date.now(),
                busVersion: '7.6.0'
            },
            governance: {
                validated: false,
                contractChecked: false
            },
            transport: {
                priority: 'normal',
                retryCount: 0,
                ttl: 30000
            }
        };
        
        this.telemetry.messagesWithContext++;
        this.lastTraceId = currentTraceId;
        return message;
    }
    
    /* ========================================================
       VALIDATE MESSAGE
    ======================================================== */
    validateMessage(message) {
        const schema = this.getSchema();
        
        if (schema?.validate && !schema.validate(message)) {
            this.telemetry.messagesRejected++;
            console.warn(`🚫 Schema Rejected: ${message.channel}`);
            return false;
        }
        
        // ✅ Context validation مع التحقق من lineage
        if (!message.meta?.context?.traceId) {
            this.telemetry.messagesMissingContext++;
            console.warn(`⚠️ Context Missing: ${message.channel}`);
            return false;
        }
        
        return true;
    }

    /* ========================================================
       UPDATE TELEMETRY (مع Rolling Average الحقيقي)
       
       ✅ FIX 2: تفعيل recentDispatchTimes وحساب rolling average
    ======================================================== */
    updateTelemetry(dispatchTime) {
        this.telemetry.messagesProcessed++;
        this.telemetry.totalDispatchTime += dispatchTime;
        this.telemetry.averageDispatchTime = 
            this.telemetry.totalDispatchTime / this.telemetry.messagesProcessed;
        
        // ✅ Rolling window implementation
        this.telemetry.recentDispatchTimes.push(dispatchTime);
        
        if (this.telemetry.recentDispatchTimes.length > this.telemetry.rollingWindowSize) {
            this.telemetry.recentDispatchTimes.shift();
        }
        
        // ✅ Calculate rolling average
        if (this.telemetry.recentDispatchTimes.length > 0) {
            const sum = this.telemetry.recentDispatchTimes.reduce((a, b) => a + b, 0);
            this.telemetry.rollingAverageDispatchTime = sum / this.telemetry.recentDispatchTimes.length;
        }
    }

    /* ========================================================
       PUBLISH (Core Pipeline)
    ======================================================== */
    publish(channel, payload = {}) {
        const startTime = performance.now();

        if (!this.channels.has(channel)) {
            console.warn(`Bus: Channel "${channel}" does not exist.`);
            return;
        }

        let message = this.normalizeMessage(channel, payload);
        message = this.attachRuntimeContext(message, channel);
        
        if (!this.validateMessage(message)) return;

        let processedMessage = message;
        
        for (const middleware of this.middlewares) {
            try {
                const result = middleware(processedMessage);
                if (result === null) {
                    console.warn(`🚫 Blocked: ${channel} | Trace: ${message.meta?.context?.traceId}`);
                    this.telemetry.messagesRejected++;
                    return;
                }
                processedMessage = result || processedMessage;
            } catch (error) {
                console.error(`Middleware Error (${channel}):`, error);
            }
        }

        const listeners = this.channels.get(channel);
        const errors = [];

        for (const listener of listeners) {
            try {
                listener(processedMessage);
            } catch (error) {
                console.error(`Listener Error (${channel}):`, error);
                errors.push(error);
            }
        }

        this.updateTelemetry(performance.now() - startTime);

        if (errors.length > 0 && channel !== 'runtime:errors' && this.hasChannel('runtime:errors')) {
            this.publishWithoutMiddleware('runtime:errors', {
                sourceChannel: channel,
                errors: errors.map(e => e.message),
                originalPayload: payload,
                context: message.meta?.context,
                telemetry: {
                    messagesProcessed: this.telemetry.messagesProcessed,
                    messagesFailed: this.telemetry.messagesFailed,
                    messagesRejected: this.telemetry.messagesRejected,
                    messagesWithContext: this.telemetry.messagesWithContext,
                    rollingAverageDispatchTime: this.telemetry.rollingAverageDispatchTime
                }
            });
        }
    }

    /* ========================================================
       PUBLISH WITHOUT MIDDLEWARE (Priority Channel)
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
                context: payload.context || {
                    sessionId: `system_${Date.now()}`,
                    traceId: `system_trace_${Date.now()}`,
                    scope: channel,
                    source: 'runtime-bus-critical',
                    lineage: [{ service: 'runtime-bus-critical', timestamp: Date.now() }]
                },
                telemetry: { createdAt: Date.now(), priority: 'system' },
                governance: { bypassed: true },
                transport: { priority: 'system', bypassedMiddleware: true, isErrorEvent: true }
            },
            timestamp: Date.now()
        };

        const listeners = this.channels.get(channel);
        for (const listener of listeners) {
            try {
                listener(message);
            } catch (error) {
                console.error(`CRITICAL: Error in ${channel}`, error);
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

    hasChannel(channel) {
        return this.channels.has(channel);
    }

    getChannelListenersCount(channel) {
        return this.channels.get(channel)?.length || 0;
    }

    /* ========================================================
       STATUS (مع Telemetry محسّنة)
    ======================================================== */
    getStatus() {
        const status = {
            channels: [...this.channels.keys()],
            middlewaresCount: this.middlewares.length,
            totalListeners: 0,
            protocolGateway: true,
            contextPropagation: true,
            registeredInRegistry: !!window.SOVEREIGN?.get('bus'),
            defaultChannelsProtected: [...this.defaultChannels],
            contextManagerAvailable: !!this.getContextManager(),
            telemetry: {
                messagesProcessed: this.telemetry.messagesProcessed,
                messagesFailed: this.telemetry.messagesFailed,
                messagesNormalized: this.telemetry.messagesNormalized,
                messagesRejected: this.telemetry.messagesRejected,
                messagesWithContext: this.telemetry.messagesWithContext,
                messagesMissingContext: this.telemetry.messagesMissingContext,
                averageDispatchTimeMs: parseFloat(this.telemetry.averageDispatchTime.toFixed(2)),
                rollingAverageDispatchTimeMs: parseFloat(this.telemetry.rollingAverageDispatchTime?.toFixed(2) || 0),
                rollingWindowSize: this.telemetry.rollingWindowSize,
                rollingWindowFill: this.telemetry.recentDispatchTimes.length
            }
        };

        for (const listeners of this.channels.values()) {
            status.totalListeners += listeners.length;
        }

        return status;
    }

    clearAllChannels() {
        for (const [channel] of this.channels.entries()) {
            if (!this.defaultChannels.has(channel)) {
                this.channels.delete(channel);
            } else {
                this.channels.set(channel, []);
            }
        }
        this.registerDefaultChannels();
        console.log('🧹 Bus: Non-default channels cleared');
    }

    clearMiddleware() {
        this.middlewares = [];
        console.log('🧹 Bus: All middleware cleared');
    }

    resetTelemetry() {
        this.telemetry = {
            messagesProcessed: 0,
            messagesFailed: 0,
            totalDispatchTime: 0,
            averageDispatchTime: 0,
            messagesNormalized: 0,
            messagesRejected: 0,
            messagesWithContext: 0,
            messagesMissingContext: 0,
            rollingWindowSize: 1000,
            recentDispatchTimes: [],
            rollingAverageDispatchTime: 0
        };
        console.log('📊 Bus telemetry reset');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignBus = new SovereignRuntimeBus();

window.SOVEREIGN_BUS = sovereignBus;

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('bus', sovereignBus);
    console.log('✅ Bus registered in Unified Registry');
}

if (window.SOVEREIGN_EVENTS) {
    window.SOVEREIGN_EVENTS.emit('bus:ready', {
        timestamp: Date.now(),
        status: sovereignBus.getStatus()
    });
}
