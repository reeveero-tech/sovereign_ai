/* ============================================================
   Sovereign AI — runtime-bus.js
   الإصدار: 7.8.0 (Runtime Transport Kernel)
   
   ⚠️ CRITICAL: Bus has reached "Core Saturation Point"
   Future decomposition REQUIRED:
     
     Subsystem  | Responsibility
     -----------|------------------------------------------------
     TransportEngine | النقل الأساسي للرسائل
     ContextPropagator | إدارة التتبع والـ lineage (بدون global state)
     EnvelopeInjector | حقن الأغلفة الموحدة
     TelemetryProfiler | القياس و rolling averages
     ProtocolValidator | التحقق من صحة schema, context, envelope
     MiddlewareOrchestrator | إدارة الـ pipeline
     ErrorIsolationLayer | عزل الأخطاء ومنع الـ recursion
   
   المرحلة القادمة (بعد التقسيم):
     - Runtime Session Manager (session start/end, scopes, domains)
     - Distributed Trace Collector
     - Session Lifecycle Management
     - Execution Domain Isolation
   ============================================================ */

class SovereignRuntimeBus {

    constructor() {

        this.channels = new Map();
        this.middlewares = [];

        // ✅ Removed: this.lastTraceId (global mutable state)
        // ✅ FIX 1: No more global trace ID - using explicit propagation only

        this.defaultChannels = new Set([
            'runtime', 'system', 'security', 'analytics', 'chat',
            'performance', 'kernel', 'lifecycle', 'orchestrator',
            'policy', 'health', 'state', 'migration', 'runtime:errors'
        ]);

        this.telemetry = {
            messagesProcessed: 0,
            messagesFailed: 0,
            totalDispatchTime: 0,
            averageDispatchTime: 0,
            messagesNormalized: 0,
            messagesRejected: 0,
            messagesWithContext: 0,
            messagesMissingContext: 0,
            messagesWithEnvelope: 0,
            messagesMissingEnvelope: 0,
            rollingWindowSize: 1000,
            recentDispatchTimes: [],
            rollingAverageDispatchTime: 0
        };

        this._access = null;

        console.log(
            '🛰 Runtime Bus Initialized (Transport Kernel Mode)'
        );

        this.init();
    }

    get access() {
        if (!this._access && window.SOVEREIGN_ACCESS) {
            this._access = window.SOVEREIGN_ACCESS;
            console.log('✅ Runtime Bus connected to Runtime Access Layer');
        }
        return this._access;
    }

    getSchema() {
        return this.access?.legacy?.('schema') || window.SOVEREIGN_SCHEMA;
    }

    getContextManager() {
        return this.access?.legacy?.('context') || window.SOVEREIGN_CONTEXT;
    }

    getEnvelopeManager() {
        return this.access?.legacy?.('envelope') || window.SOVEREIGN_ENVELOPE;
    }

    init() {
        this.registerDefaultChannels();
        this.setupSelfTelemetry();
        this.emitReady();
    }

    emitReady() {
        this.publishWithoutMiddleware('bus:ready', {
            timestamp: Date.now(),
            channelsCount: this.defaultChannels.size,
            version: '7.8.0',
            source: 'runtime-bus',
            contextSupported: !!this.getContextManager(),
            envelopeSupported: !!this.getEnvelopeManager()
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
        this.subscribe('runtime:errors', () => {
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

    normalizeMessage(rawChannel, rawPayload, rawId) {
        const schema = this.getSchema();
        const messageId = rawId || this.generateMessageId();
        
        if (schema?.create) {
            const msg = schema.create({
                type: `runtime.${rawChannel}`,
                source: 'runtime-bus',
                channel: rawChannel,
                payload: rawPayload,
                meta: {
                    busManaged: true,
                    normalizedAt: Date.now(),
                    busVersion: '7.8.0'
                }
            });
            this.telemetry.messagesNormalized++;
            return msg;
        }
        
        return {
            id: messageId,
            type: `runtime.${rawChannel}`,
            version: 'legacy',
            source: 'runtime-bus',
            channel: rawChannel,
            payload: rawPayload,
            meta: { legacy: true, normalizedAt: Date.now(), busVersion: '7.8.0' },
            timestamp: Date.now()
        };
    }
    
    /* ========================================================
       ATTACH RUNTIME CONTEXT
       
       ✅ FIX 1: No more global lastTraceId
       Using explicit propagation only
    ======================================================== */
    attachRuntimeContext(message, channel) {
        const contextManager = this.getContextManager();
        
        // ✅ Get parent trace ID from message metadata if available
        const parentTraceId = message.meta?.context?.traceId || null;
        const currentTraceId = this.generateTraceId();
        
        if (contextManager?.attach) {
            const attachedMessage = contextManager.attach(message, {
                source: 'runtime-bus',
                scope: channel,
                parentTraceId: parentTraceId  // ✅ explicit propagation
            });
            this.telemetry.messagesWithContext++;
            return attachedMessage;
        }
        
        // ✅ FIX 2: Preserve existing meta instead of replacing
        if (!message.meta) {
            message.meta = {};
        }
        
        message.meta = {
            ...message.meta,  // ✅ Preserve existing metadata
            context: {
                sessionId: this.generateSessionId(),
                traceId: currentTraceId,
                parentTraceId: parentTraceId,
                scope: channel,
                source: 'runtime-bus-fallback',
                lineage: [
                    ...(message.meta.context?.lineage || []),
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
                ...message.meta.telemetry,
                createdAt: Date.now(),
                busVersion: '7.8.0'
            },
            governance: {
                ...message.meta.governance,
                validated: false,
                contractChecked: false
            },
            transport: {
                ...message.meta.transport,
                priority: 'normal',
                retryCount: 0,
                ttl: 30000
            }
        };
        
        this.telemetry.messagesWithContext++;
        return message;
    }
    
    /* ========================================================
       INJECT RUNTIME ENVELOPE
       
       ✅ FIX 4: Enhanced transport semantics (retryable, priority, ttl)
    ======================================================== */
    injectRuntimeEnvelope(message, channel) {
        const envelopeManager = this.getEnvelopeManager();
        const isCritical = channel === 'runtime:errors';
        
        if (envelopeManager?.attach) {
            const envelopedMessage = envelopeManager.attach(message, {
                protocol: {
                    channel: channel,
                    type: message.type || `runtime.${channel}`,
                    version: '7.8.0'
                },
                transport: {
                    reliable: true,
                    priority: isCritical ? 'critical' : 'normal',
                    retryable: !isCritical,      // ✅ critical messages not retryable
                    ttl: isCritical ? 60000 : 30000,  // ✅ different TTL per priority
                    maxRetries: isCritical ? 0 : 3
                },
                governance: {
                    validated: false,
                    contractChecked: false,
                    policyChecked: false
                },
                telemetry: {
                    tracked: true,
                    sourceTimestamp: Date.now(),
                    busVersion: '7.8.0'
                },
                tracing: {
                    traceId: message.meta?.context?.traceId || this.generateTraceId(),
                    sessionId: message.meta?.context?.sessionId,
                    parentTraceId: message.meta?.context?.parentTraceId
                }
            });
            this.telemetry.messagesWithEnvelope++;
            return envelopedMessage;
        }
        
        // ✅ Fallback Envelope with proper transport semantics
        if (!message.envelope) {
            message.envelope = {
                protocol: {
                    channel: channel,
                    type: message.type || `runtime.${channel}`,
                    version: 'legacy'
                },
                transport: {
                    reliable: true,
                    priority: isCritical ? 'critical' : 'normal',
                    retryable: !isCritical,
                    ttl: isCritical ? 60000 : 30000
                },
                governance: {
                    validated: false,
                    contractChecked: false
                },
                telemetry: {
                    tracked: true,
                    sourceTimestamp: Date.now(),
                    busVersion: '7.8.0'
                },
                tracing: {
                    traceId: message.meta?.context?.traceId || this.generateTraceId(),
                    sessionId: message.meta?.context?.sessionId
                }
            };
            this.telemetry.messagesWithEnvelope++;
        }
        
        return message;
    }

    /* ========================================================
       VALIDATE MESSAGE
    ======================================================== */
    validateMessage(message) {
        const schema = this.getSchema();
        const envelopeManager = this.getEnvelopeManager();
        
        if (schema?.validate && !schema.validate(message)) {
            this.telemetry.messagesRejected++;
            console.warn(`🚫 Schema Rejected: ${message.channel}`);
            return false;
        }
        
        if (!message.meta?.context?.traceId) {
            this.telemetry.messagesMissingContext++;
            console.warn(`⚠️ Context Missing: ${message.channel}`);
            return false;
        }
        
        if (envelopeManager?.validate) {
            if (!envelopeManager.validate(message)) {
                this.telemetry.messagesMissingEnvelope++;
                console.warn(`⚠️ Envelope Invalid: ${message.channel}`);
                return false;
            }
        } else if (!message.envelope) {
            this.telemetry.messagesMissingEnvelope++;
            console.warn(`⚠️ Envelope Missing: ${message.channel}`);
            return false;
        }
        
        return true;
    }

    updateTelemetry(dispatchTime) {
        this.telemetry.messagesProcessed++;
        this.telemetry.totalDispatchTime += dispatchTime;
        this.telemetry.averageDispatchTime = 
            this.telemetry.totalDispatchTime / this.telemetry.messagesProcessed;
        
        this.telemetry.recentDispatchTimes.push(dispatchTime);
        
        if (this.telemetry.recentDispatchTimes.length > this.telemetry.rollingWindowSize) {
            this.telemetry.recentDispatchTimes.shift();
        }
        
        if (this.telemetry.recentDispatchTimes.length > 0) {
            const sum = this.telemetry.recentDispatchTimes.reduce((a, b) => a + b, 0);
            this.telemetry.rollingAverageDispatchTime = sum / this.telemetry.recentDispatchTimes.length;
        }
    }

    publish(channel, payload = {}) {
        const startTime = performance.now();

        if (!this.channels.has(channel)) {
            console.warn(`Bus: Channel "${channel}" does not exist.`);
            return;
        }

        let message = this.normalizeMessage(channel, payload);
        message = this.attachRuntimeContext(message, channel);
        message = this.injectRuntimeEnvelope(message, channel);
        
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
                envelope: message.envelope,
                telemetry: {
                    messagesProcessed: this.telemetry.messagesProcessed,
                    messagesFailed: this.telemetry.messagesFailed,
                    messagesRejected: this.telemetry.messagesRejected,
                    messagesWithContext: this.telemetry.messagesWithContext,
                    messagesWithEnvelope: this.telemetry.messagesWithEnvelope,
                    rollingAverageDispatchTime: this.telemetry.rollingAverageDispatchTime
                }
            });
        }
    }

    publishWithoutMiddleware(channel, payload = {}) {
        if (!this.channels.has(channel)) return;

        const message = {
            id: this.generateMessageId(),
            type: `runtime.${channel}`,
            version: 'critical',
            source: 'runtime-bus',
            channel,
            payload,
            envelope: payload.envelope || {
                protocol: { channel, type: `runtime.${channel}`, version: 'critical' },
                transport: { reliable: true, priority: 'critical', retryable: false, ttl: 60000, bypassedMiddleware: true },
                governance: { validated: true, bypassed: true },
                telemetry: { tracked: true, sourceTimestamp: Date.now(), priority: 'system' },
                tracing: { traceId: `critical_${Date.now()}`, sessionId: `system_${Date.now()}` }
            },
            meta: payload.context ? { context: payload.context } : {
                context: {
                    sessionId: `system_${Date.now()}`,
                    traceId: `critical_trace_${Date.now()}`,
                    scope: channel,
                    source: 'runtime-bus-critical',
                    lineage: [{ service: 'runtime-bus-critical', timestamp: Date.now() }]
                }
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

    getStatus() {
        const status = {
            channels: [...this.channels.keys()],
            middlewaresCount: this.middlewares.length,
            totalListeners: 0,
            protocolGateway: true,
            contextPropagation: true,
            envelopeInjection: true,
            registeredInRegistry: !!window.SOVEREIGN?.get('bus'),
            defaultChannelsProtected: [...this.defaultChannels],
            contextManagerAvailable: !!this.getContextManager(),
            envelopeManagerAvailable: !!this.getEnvelopeManager(),
            telemetry: {
                messagesProcessed: this.telemetry.messagesProcessed,
                messagesFailed: this.telemetry.messagesFailed,
                messagesNormalized: this.telemetry.messagesNormalized,
                messagesRejected: this.telemetry.messagesRejected,
                messagesWithContext: this.telemetry.messagesWithContext,
                messagesMissingContext: this.telemetry.messagesMissingContext,
                messagesWithEnvelope: this.telemetry.messagesWithEnvelope,
                messagesMissingEnvelope: this.telemetry.messagesMissingEnvelope,
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
            messagesWithEnvelope: 0,
            messagesMissingEnvelope: 0,
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
