/* ============================================================
   Sovereign AI — runtime-middleware.js
   الإصدار: 7.4.0 (Runtime Governance Engine)
   
   الوظيفة: 
     - إدارة Middleware Pipeline للـ Bus مع أولويات تنفيذية
     - تنفيذ Core Middleware (إضافة runtimeId, processedAt)
     - تنفيذ Security Middleware (التحقق من صحة المدخلات)
     - تنفيذ Analytics Middleware (تخزين مؤقت للرسائل)
     - تنفيذ Contract Validation Middleware (التحقق من صحة العقود)
     - تنفيذ Access Control Middleware (التحقق من صلاحيات Runtime)
     
   التقسيم المستقبلي للملف (Runtime Governance Engine):
     - MiddlewareRegistry (تسجيل وإدارة الـ Middlewares مع الأولويات)
     - AuthorizationLayer (ACL & Permission Validation)
     - ContractsLayer (Contract Validation)
     - SecurityLayer (Input Validation & Protection)
     - TelemetryLayer (Profiling & Metrics)
     - GovernanceLayer (Enforcement & Policy)
   
   المرحلة القادمة (بعد التقسيم):
     - Runtime Isolation Zones (fault containment)
     - Execution Isolation (subsystem sandboxing)
     - Domain Separation (runtime partitioning)
     - Subsystem Sandboxing (capability boundaries)
   ============================================================ */

class SovereignRuntimeMiddleware {

    constructor() {

        this.middlewareCount = 0;
        
        // ✅ FIX 1: Store middlewares locally with priority for sorting
        this.pendingMiddlewares = new Map();  // name -> { handler, priority }
        
        // Cache for access layer
        this._access = null;
        
        // Dynamic contract mappings (Runtime Configuration)
        this.contractMappings = new Map();
        
        // Debug mode to prevent noisy telemetry
        this.debugMode = false;
        
        // Registered middlewares for telemetry
        this.registeredMiddlewares = new Map();

        console.log(
            '🧩 Runtime Middleware Initialized (Governance Engine Ready)'
        );

        this.init();
    }

    /* ========================================================
       ACCESS HELPER (Runtime Access Layer)
    ======================================================== */
    get access() {
        if (!this._access && window.SOVEREIGN_ACCESS) {
            this._access = window.SOVEREIGN_ACCESS;
            console.log('✅ Runtime Middleware connected to Runtime Access Layer');
        }
        return this._access;
    }

    /* ========================================================
       APPLY PENDING MIDDLEWARES (with priority sorting)
       
       ✅ FIX 1: Sort middlewares by priority before applying to bus
    ======================================================== */
    applyPendingMiddlewares() {
        const bus = this.access?.bus?.() || window.SOVEREIGN_BUS;
        
        if (!bus) {
            console.warn('⚠️ Cannot apply middlewares: Bus not available');
            return false;
        }
        
        // Sort by priority (lower number = higher priority)
        const sorted = [...this.pendingMiddlewares.entries()]
            .sort((a, b) => a[1].priority - b[1].priority);
        
        for (const [name, { handler }] of sorted) {
            bus.use(handler);
            console.log(`🔧 Middleware applied: ${name}`);
        }
        
        console.log(`✅ All ${sorted.length} middlewares applied (sorted by priority)`);
        return true;
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.initContractMappings();
        this.registerCoreMiddleware();
        this.registerSecurityMiddleware();
        this.registerAnalyticsMiddleware();
        this.registerContractMiddleware();
        this.registerAccessControlMiddleware();
        
        // ✅ Apply all registered middlewares with priority sorting
        this.applyPendingMiddlewares();
        
        this.emitReady();
    }

    /* ========================================================
       INIT CONTRACT MAPPINGS (Runtime Configuration)
    ======================================================== */
    initContractMappings() {
        const mappings = {
            'analytics:capture': 'analytics.capture',
            'intelligence:state:changed': 'intelligence.state.change',
            'health:update': 'health.update',
            'policy:activated': 'policy.activation',
            'kernel:heartbeat': 'kernel.heartbeat',
            'kernel:degraded': 'kernel.degraded',
            'system:health:request': 'system.health.request',
            'system:health:response': 'system.health.response',
            'intelligence:analysis:completed': 'intelligence.analysis.completed',
            'analytics:ready': 'analytics.ready',
            'middleware:ready': 'middleware.ready',
            'policy:ready': 'policy.ready',
            'intelligence:ready': 'intelligence.ready',
            'bus:ready': 'bus.ready'
        };
        
        for (const [channel, contract] of Object.entries(mappings)) {
            this.contractMappings.set(channel, contract);
        }
        
        console.log(`✅ Contract mappings initialized: ${this.contractMappings.size} mappings`);
    }
    
    /* ========================================================
       ADD CONTRACT MAPPING (Dynamic Runtime Configuration)
    ======================================================== */
    addContractMapping(channel, contractName) {
        if (!channel || !contractName) {
            console.warn('⚠️ Invalid contract mapping:', { channel, contractName });
            return false;
        }
        
        this.contractMappings.set(channel, contractName);
        console.log(`📝 Contract mapping added: ${channel} → ${contractName}`);
        return true;
    }
    
    /* ========================================================
       REMOVE CONTRACT MAPPING
    ======================================================== */
    removeContractMapping(channel) {
        if (this.contractMappings.delete(channel)) {
            console.log(`🗑️ Contract mapping removed: ${channel}`);
            return true;
        }
        return false;
    }
    
    /* ========================================================
       SET DEBUG MODE
    ======================================================== */
    setDebugMode(enabled) {
        this.debugMode = enabled;
        console.log(`🐛 Debug mode: ${enabled ? 'ON' : 'OFF'}`);
        
        const bus = this.access?.bus?.();
        bus?.publishWithoutMiddleware?.('middleware:debug:changed', {
            debugMode: enabled,
            timestamp: Date.now()
        });
    }

    /* ========================================================
       UNIFIED MIDDLEWARE REGISTRATION (with priority)
       
       ✅ FIX 1: Store middleware locally instead of direct bus.use()
    ======================================================== */
    registerMiddleware(name, handler, priority = 10) {
        if (typeof handler !== 'function') {
            console.warn(`⚠️ Cannot register "${name}" middleware: Handler must be a function`);
            return false;
        }
        
        // Store for later sorting and application
        this.pendingMiddlewares.set(name, {
            handler,
            priority,
            registeredAt: Date.now()
        });
        
        // Store metadata for telemetry
        this.registeredMiddlewares.set(name, {
            name,
            priority,
            registeredAt: Date.now(),
            active: true
        });
        
        this.middlewareCount++;
        
        console.log(`✅ Middleware Registered: ${name} (Priority: ${priority})`);
        
        // Emit telemetry (without middleware to avoid loops)
        const bus = this.access?.bus?.();
        bus?.publishWithoutMiddleware?.('middleware:registered', {
            name,
            priority,
            timestamp: Date.now()
        });
        
        return true;
    }
    
    /* ========================================================
       UNREGISTER MIDDLEWARE (Future enhancement)
    ======================================================== */
    unregisterMiddleware(name) {
        console.warn(`⚠️ Unregister middleware "${name}" not yet supported (needs bus.unuse())`);
        return false;
    }

    /* ========================================================
       EMIT READY (مع تجنب الـ recursion)
    ======================================================== */
    emitReady() {
        const bus = this.access?.bus?.();
        
        // ✅ Use publishWithoutMiddleware to avoid recursive governance loops
        if (bus?.publishWithoutMiddleware) {
            bus.publishWithoutMiddleware('middleware:ready', {
                timestamp: Date.now(),
                middlewareCount: this.middlewareCount,
                contractMappingsCount: this.contractMappings.size,
                source: 'runtime-middleware',
                version: '7.4.0'
            });
        } else {
            // Fallback to legacy events
            window.SOVEREIGN_EVENTS?.emit('middleware:ready', {
                timestamp: Date.now(),
                middlewareCount: this.middlewareCount
            });
        }
    }

    /* ========================================================
       CORE MIDDLEWARE (Priority 1)
    ======================================================== */
    registerCoreMiddleware() {
        this.registerMiddleware('core', (message) => {
            if (!message.runtimeId) {
                message.runtimeId = crypto.randomUUID();
            }
            message.processedAt = Date.now();
            
            if (!message.meta) {
                message.meta = {};
            }
            
            message.meta.core = {
                runtimeId: message.runtimeId,
                processedAt: message.processedAt,
                middlewareVersion: '7.4.0'
            };
            
            return message;
        }, 1);
    }

    /* ========================================================
       SECURITY MIDDLEWARE (Priority 2)
    ======================================================== */
    registerSecurityMiddleware() {
        this.registerMiddleware('security', (message) => {
            try {
                const payload = JSON.stringify(message.payload || {});
                const security = this.access?.security?.() || window.SOVEREIGN_SECURITY;
                
                if (security?.validateInput) {
                    const safe = security.validateInput(payload);
                    if (!safe) {
                        console.warn(`🛡️ Security Middleware Blocked: ${message.channel}`);
                        return null;
                    }
                }
                
                if (message.meta) {
                    message.meta.security = {
                        validated: true,
                        validatedAt: Date.now()
                    };
                }
                
                return message;
            } catch (error) {
                console.error('Security Middleware Error:', error);
                return null;
            }
        }, 2);
    }

    /* ========================================================
       ANALYTICS MIDDLEWARE (Priority 8)
    ======================================================== */
    registerAnalyticsMiddleware() {
        this.registerMiddleware('analytics', (message) => {
            if (message.isErrorEvent || message.isBlocked) {
                return message;
            }
            
            const cache = this.access?.cache?.() || window.SOVEREIGN_CACHE;
            
            if (cache?.set) {
                cache.set(
                    `bus-${message.timestamp}-${message.channel}`,
                    {
                        channel: message.channel,
                        runtimeId: message.runtimeId,
                        timestamp: message.timestamp,
                        hasContract: !!message.meta?.contract?.validated,
                        authorized: !!message.envelope?.governance?.authorized
                    },
                    120000
                );
            }
            
            return message;
        }, 8);
    }

    /* ========================================================
       CONTRACT VALIDATION MIDDLEWARE (Priority 5)
    ======================================================== */
    registerContractMiddleware() {
        this.registerMiddleware('contract', (message) => {
            if (!message.meta) {
                message.meta = {};
            }
            
            const contractName = this.contractMappings.get(message.channel);
            
            if (!contractName) {
                if (this.debugMode && !message.channel?.startsWith('runtime:')) {
                    console.debug(`📝 No contract defined for channel: ${message.channel}`);
                }
                return message;
            }
            
            const contracts = this.access?.legacy?.('contracts') || window.SOVEREIGN_CONTRACTS;
            
            if (!contracts?.validate) {
                if (this.debugMode) {
                    console.debug(`⚠️ Contract validation skipped for ${contractName}`);
                }
                return message;
            }
            
            const isValid = contracts.validate(contractName, message.payload);
            
            if (!isValid) {
                console.warn(`
⚠️ Runtime Contract Rejected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Channel: ${message.channel}
Contract: ${contractName}
RuntimeId: ${message.runtimeId}
Timestamp: ${message.timestamp}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                `);
                return null;
            }
            
            message.meta.contract = {
                validated: true,
                name: contractName,
                validatedAt: Date.now(),
                version: '1.0.0'
            };
            
            return message;
        }, 5);
    }
    
    /* ========================================================
       ACCESS CONTROL MIDDLEWARE (Priority 4)
       
       ✅ FIX 2: Use publishWithoutMiddleware to avoid recursive loops
    ======================================================== */
    registerAccessControlMiddleware() {
        const bus = this.access?.bus?.();
        
        // ✅ FIX 3: TODO - add access.acl() to Runtime Access Layer
        // Target: const acl = this.access?.acl?.() || window.SOVEREIGN_ACL;
        const acl = this.access?.legacy?.('acl') || window.SOVEREIGN_ACL;
        
        if (!bus || !acl) {
            console.warn('⚠️ Access Control Middleware Missing Dependencies (ACL not available)');
            console.log('📝 Access Control Middleware will register but authorization will be skipped until ACL is ready');
        }
        
        // Channel → Permission Mapping (Runtime Authorization Rules)
        const rules = {
            'analytics:capture': { domain: 'analytics-domain', permission: 'telemetry.write' },
            'analytics:ready': { domain: 'analytics-domain', permission: 'telemetry.read' },
            'analytics:export': { domain: 'analytics-domain', permission: 'telemetry.export' },
            'runtime:errors': { domain: 'transport-domain', permission: 'transport.publish' },
            'bus:ready': { domain: 'transport-domain', permission: 'transport.observe' },
            'policy:activated': { domain: 'governance-domain', permission: 'policy.enforce' },
            'policy:ready': { domain: 'governance-domain', permission: 'policy.read' },
            'intelligence:state:changed': { domain: 'intelligence-domain', permission: 'intelligence.read' },
            'intelligence:ready': { domain: 'intelligence-domain', permission: 'intelligence.observe' },
            'intelligence:analysis:completed': { domain: 'intelligence-domain', permission: 'intelligence.analyze' },
            'health:update': { domain: 'health-domain', permission: 'health.write' },
            'system:health:request': { domain: 'health-domain', permission: 'health.read' },
            'system:health:response': { domain: 'health-domain', permission: 'health.read' },
            'kernel:heartbeat': { domain: 'kernel-domain', permission: 'kernel.observe' },
            'kernel:degraded': { domain: 'kernel-domain', permission: 'kernel.observe' },
            'middleware:ready': { domain: 'middleware-domain', permission: 'middleware.read' },
            'middleware:registered': { domain: 'middleware-domain', permission: 'middleware.observe' }
        };
        
        this.registerMiddleware('access-control', (message) => {
            const rule = rules[message.channel];
            
            if (!rule) {
                if (this.debugMode) {
                    console.debug(`📝 No ACL rule defined for channel: ${message.channel}`);
                }
                return message;
            }
            
            if (!acl?.check) {
                if (this.debugMode) {
                    console.debug(`⚠️ ACL check skipped for ${message.channel} (ACL not ready)`);
                }
                return message;
            }
            
            const allowed = acl.check(rule.domain, rule.permission);
            
            if (!allowed) {
                console.warn(`
🚫 Runtime Access Denied
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Channel: ${message.channel}
Domain: ${rule.domain}
Permission: ${rule.permission}
RuntimeId: ${message.runtimeId}
TraceId: ${message.meta?.context?.traceId}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                `);
                
                // ✅ FIX 2: Use publishWithoutMiddleware to avoid recursive governance loops
                const bus2 = this.access?.bus?.();
                if (bus2?.publishWithoutMiddleware) {
                    bus2.publishWithoutMiddleware('security:access:denied', {
                        channel: message.channel,
                        domain: rule.domain,
                        permission: rule.permission,
                        traceId: message.meta?.context?.traceId,
                        timestamp: Date.now()
                    });
                }
                
                return null;
            }
            
            // Governance Enrichment
            if (message.envelope) {
                message.envelope.governance = {
                    ...message.envelope.governance,
                    domain: rule.domain,
                    permission: rule.permission,
                    authorized: true,
                    authorizedAt: Date.now(),
                    authVersion: '1.0.0'
                };
            }
            
            if (message.meta) {
                message.meta.authorization = {
                    domain: rule.domain,
                    permission: rule.permission,
                    authorized: true,
                    authorizedAt: Date.now()
                };
            }
            
            return message;
        }, 4);
        
        console.log('✅ Access Control Middleware Enabled (Runtime Authorization)');
    }
    
    /* ========================================================
       GET CONTRACT MAPPING FOR CHANNEL
    ======================================================== */
    getContractForChannel(channel) {
        return this.contractMappings.get(channel) || null;
    }
    
    /* ========================================================
       GET ALL CONTRACT MAPPINGS
    ======================================================== */
    getAllContractMappings() {
        return Object.fromEntries(this.contractMappings);
    }

    /* ========================================================
       GET MIDDLEWARE EXECUTION ORDER (للمراقبة)
    ======================================================== */
    getMiddlewareExecutionOrder() {
        const sorted = [...this.pendingMiddlewares.entries()]
            .sort((a, b) => a[1].priority - b[1].priority)
            .map(([name, { priority }]) => ({ name, priority }));
        
        return sorted;
    }

    /* ========================================================
       STATUS (مع Authorization Telemetry)
    ======================================================== */
    getStatus() {
        const activeMiddlewares = [...this.registeredMiddlewares.keys()];
        const executionOrder = this.getMiddlewareExecutionOrder();
        
        return {
            middlewaresCount: this.middlewareCount,
            registeredMiddlewares: activeMiddlewares,
            middlewareExecutionOrder: executionOrder,
            prioritiesEnabled: true,
            contractMappingsCount: this.contractMappings.size,
            contractMappings: this.getAllContractMappings(),
            debugMode: this.debugMode,
            accessLayerConnected: !!this._access,
            authorizationEnabled: true,
            timestamp: Date.now()
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
============================================================ */

const sovereignMiddleware = new SovereignRuntimeMiddleware();

window.SOVEREIGN_MIDDLEWARE = sovereignMiddleware;

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('middleware', sovereignMiddleware);
    console.log('✅ Runtime Middleware registered in Unified Registry');
} else {
    console.warn('⚠️ Unified Registry not yet available. Middleware registered as legacy global only.');
}

window.SOVEREIGN_EVENTS?.emit('middleware:ready', {
    timestamp: Date.now(),
    status: sovereignMiddleware.getStatus()
});
