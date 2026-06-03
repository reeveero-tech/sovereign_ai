/* ============================================================
   Sovereign AI — runtime-middleware.js
   الإصدار: 7.8.0 (Runtime Governance Kernel with Lifecycle Enforcement)
   
   الوظيفة: 
     - إدارة Middleware Pipeline للـ Bus مع أولويات تنفيذية
     - إدارة Lifecycle State للـ Middlewares مع Enforcement فعلي
     - تنفيذ Core, Security, Analytics, Contract, ACL, Isolation, Sandbox Middlewares
     
   ✅ NEW: Middleware state now affects actual execution
     - suspended middleware → skipped
     - failed middleware → skipped
     - degraded middleware → allowed (with telemetry)
   
   التقسيم المستقبلي للملف (Runtime Governance Kernel):
     - MiddlewareRegistry (تسجيل وإدارة الـ Middlewares مع الأولويات والحالة)
     - ExecutionScheduler (ترتيب وتنفيذ الـ Middlewares مع Lifecycle Enforcement) ✅ جاري
     - GovernanceEngine (Enforcement & Policy)
     - IsolationLayer (Fault Containment & Zone Enforcement)
     - AuthorizationLayer (ACL & Permission Validation)
     - ResourceContainmentLayer (Sandbox & Quota Enforcement)
     - TelemetryLayer (Profiling & Metrics)
   
   المرحلة القادمة (Runtime Execution Scheduler):
     - Queue Prioritization
     - Deferred Execution
     - Degraded Scheduling
     - Execution Pacing
     - Adaptive Runtime Scheduling
   ============================================================ */

class SovereignRuntimeMiddleware {

    constructor() {

        this.middlewareCount = 0;
        
        // Store middlewares locally with priority for sorting
        this.pendingMiddlewares = new Map();  // name -> { handler, priority }
        
        // Prevent duplicate application
        this.middlewaresApplied = false;
        
        // Cache for access layer
        this._access = null;
        
        // Dynamic contract mappings (Runtime Configuration)
        this.contractMappings = new Map();
        
        // Debug mode to prevent noisy telemetry
        this.debugMode = false;
        
        // Registered middlewares with lifecycle state
        this.registeredMiddlewares = new Map();

        console.log(
            '🧩 Runtime Middleware Initialized (Lifecycle Enforcement Active)'
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
       CHECK IF MIDDLEWARE SHOULD EXECUTE (Lifecycle Enforcement)
       
       ✅ FIX: Middleware states now affect actual execution
       - suspended → skip execution
       - failed → skip execution
       - degraded → execute but log warning
       - active → execute normally
       - pending → execute normally (transitional)
    ======================================================== */
    shouldExecuteMiddleware(name) {
        const middleware = this.registeredMiddlewares.get(name);
        if (!middleware) return true; // If not found, allow execution (safety)
        
        const state = middleware.state;
        
        switch (state) {
            case 'active':
            case 'pending':
                return true;
            case 'degraded':
                if (this.debugMode) {
                    console.warn(`⚠️ Middleware "${name}" is in degraded state, but executing (debug mode)`);
                }
                return true;
            case 'suspended':
                console.warn(`⏸️ Middleware "${name}" is suspended, skipping execution`);
                this.emitMiddlewareSkipped(name, 'suspended');
                return false;
            case 'failed':
                console.error(`💀 Middleware "${name}" is failed, skipping execution`);
                this.emitMiddlewareSkipped(name, 'failed');
                return false;
            default:
                return true;
        }
    }
    
    /* ========================================================
       EMIT MIDDLEWARE SKIPPED EVENT
    ======================================================== */
    emitMiddlewareSkipped(name, reason) {
        const bus = this.access?.bus?.();
        bus?.publishWithoutMiddleware?.('middleware:skipped', {
            name,
            reason,
            timestamp: Date.now()
        });
    }

    /* ========================================================
       APPLY PENDING MIDDLEWARES (with priority sorting)
       
       ✅ FIX: Wrap middleware handler with lifecycle check
    ======================================================== */
    applyPendingMiddlewares() {
        if (this.middlewaresApplied) {
            console.warn('⚠️ Middlewares already applied. Skipping duplicate application.');
            return true;
        }
        
        const bus = this.access?.bus?.() || window.SOVEREIGN_BUS;
        
        if (!bus) {
            console.warn('⚠️ Cannot apply middlewares: Bus not available');
            return false;
        }
        
        // Sort by priority (lower number = higher priority)
        const sorted = [...this.pendingMiddlewares.entries()]
            .sort((a, b) => a[1].priority - b[1].priority);
        
        for (const [name, { handler, priority }] of sorted) {
            // ✅ Wrap handler with lifecycle enforcement
            const wrappedHandler = (message) => {
                // Check if middleware should execute based on lifecycle state
                if (!this.shouldExecuteMiddleware(name)) {
                    return message; // Skip this middleware
                }
                
                // Execute the actual middleware
                return handler(message);
            };
            
            bus.use(wrappedHandler);
            console.log(`🔧 Middleware applied: ${name} (Priority: ${priority})`);
            
            // Update state to active
            const reg = this.registeredMiddlewares.get(name);
            if (reg) {
                reg.state = 'active';
                reg.stateChangedAt = Date.now();
                this.registeredMiddlewares.set(name, reg);
            }
        }
        
        this.middlewaresApplied = true;
        console.log(`✅ All ${sorted.length} middlewares applied (sorted by priority, lifecycle enforcement active)`);
        return true;
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.initContractMappings();
        this.registerCoreMiddleware();           // Priority 1
        this.registerSecurityMiddleware();       // Priority 2
        this.registerAccessControlMiddleware();  // Priority 4
        this.registerContractMiddleware();       // Priority 5
        this.registerIsolationMiddleware();      // Priority 6
        this.registerSandboxMiddleware();        // Priority 7
        this.registerAnalyticsMiddleware();      // Priority 8
        
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
       UPDATE MIDDLEWARE STATE (Lifecycle Management)
       
       ✅ Now with execution impact via shouldExecuteMiddleware
    ======================================================== */
    updateMiddlewareState(name, state, error = null) {
        if (!this.registeredMiddlewares.has(name)) {
            console.warn(`⚠️ Cannot update state for unknown middleware: ${name}`);
            return false;
        }
        
        const reg = this.registeredMiddlewares.get(name);
        const validStates = ['active', 'suspended', 'failed', 'degraded', 'pending'];
        
        if (!validStates.includes(state)) {
            console.warn(`⚠️ Invalid state: ${state} for middleware ${name}`);
            return false;
        }
        
        const oldState = reg.state;
        reg.state = state;
        reg.stateChangedAt = Date.now();
        if (error) {
            reg.errorCount = (reg.errorCount || 0) + 1;
            reg.lastError = error;
        }
        
        this.registeredMiddlewares.set(name, reg);
        
        console.log(`📊 Middleware state changed: ${name} → ${state} (was ${oldState})`);
        
        // Publish state change event
        const bus = this.access?.bus?.();
        bus?.publishWithoutMiddleware?.('middleware:state:changed', {
            name,
            oldState,
            newState: state,
            timestamp: Date.now()
        });
        
        return true;
    }

    /* ========================================================
       UNIFIED MIDDLEWARE REGISTRATION
    ======================================================== */
    registerMiddleware(name, handler, priority = 10) {
        if (typeof handler !== 'function') {
            console.warn(`⚠️ Cannot register "${name}" middleware: Handler must be a function`);
            return false;
        }
        
        this.pendingMiddlewares.set(name, {
            handler,
            priority,
            registeredAt: Date.now()
        });
        
        this.registeredMiddlewares.set(name, {
            name,
            priority,
            registeredAt: Date.now(),
            state: 'pending',
            stateChangedAt: Date.now(),
            errorCount: 0,
            lastError: null
        });
        
        this.middlewareCount++;
        
        console.log(`✅ Middleware Registered: ${name} (Priority: ${priority})`);
        
        const bus = this.access?.bus?.();
        bus?.publishWithoutMiddleware?.('middleware:registered', {
            name,
            priority,
            timestamp: Date.now()
        });
        
        return true;
    }
    
    /* ========================================================
       SUSPEND MIDDLEWARE (Runtime Lifecycle Management)
    ======================================================== */
    suspendMiddleware(name) {
        return this.updateMiddlewareState(name, 'suspended');
    }
    
    /* ========================================================
       RESUME MIDDLEWARE
    ======================================================== */
    resumeMiddleware(name) {
        return this.updateMiddlewareState(name, 'active');
    }
    
    /* ========================================================
       MARK MIDDLEWARE FAILED
    ======================================================== */
    markMiddlewareFailed(name, error) {
        return this.updateMiddlewareState(name, 'failed', error);
    }
    
    /* ========================================================
       MARK MIDDLEWARE DEGRADED
    ======================================================== */
    markMiddlewareDegraded(name, error) {
        return this.updateMiddlewareState(name, 'degraded', error);
    }
    
    /* ========================================================
       UNREGISTER MIDDLEWARE
    ======================================================== */
    unregisterMiddleware(name) {
        console.warn(`⚠️ Unregister middleware "${name}" not yet supported (needs bus.unuse())`);
        return false;
    }

    /* ========================================================
       EMIT READY
    ======================================================== */
    emitReady() {
        const bus = this.access?.bus?.();
        
        if (bus?.publishWithoutMiddleware) {
            bus.publishWithoutMiddleware('middleware:ready', {
                timestamp: Date.now(),
                middlewareCount: this.middlewareCount,
                contractMappingsCount: this.contractMappings.size,
                source: 'runtime-middleware',
                version: '7.8.0',
                lifecycleEnforcement: true
            });
        } else {
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
            if (!message.meta) message.meta = {};
            message.meta.core = {
                runtimeId: message.runtimeId,
                processedAt: message.processedAt,
                middlewareVersion: '7.8.0'
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
                if (security?.validateInput && !security.validateInput(payload)) {
                    console.warn(`🛡️ Security Middleware Blocked: ${message.channel}`);
                    return null;
                }
                if (message.meta) message.meta.security = { validated: true, validatedAt: Date.now() };
                return message;
            } catch (error) {
                console.error('Security Middleware Error:', error);
                return null;
            }
        }, 2);
    }

    /* ========================================================
       ACCESS CONTROL MIDDLEWARE (Priority 4)
    ======================================================== */
    registerAccessControlMiddleware() {
        const acl = this.access?.legacy?.('acl') || window.SOVEREIGN_ACL;
        
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
            if (!rule) return message;
            if (!acl?.check) return message;
            
            if (!acl.check(rule.domain, rule.permission)) {
                console.warn(`🚫 Access Denied: ${message.channel} (${rule.domain}:${rule.permission})`);
                const bus = this.access?.bus?.();
                bus?.publishWithoutMiddleware?.('security:access:denied', {
                    channel: message.channel, domain: rule.domain, permission: rule.permission, timestamp: Date.now()
                });
                return null;
            }
            
            if (message.envelope) {
                message.envelope.governance = { ...message.envelope.governance, domain: rule.domain, permission: rule.permission, authorized: true, authorizedAt: Date.now() };
            }
            return message;
        }, 4);
    }

    /* ========================================================
       CONTRACT VALIDATION MIDDLEWARE (Priority 5)
    ======================================================== */
    registerContractMiddleware() {
        this.registerMiddleware('contract', (message) => {
            const contractName = this.contractMappings.get(message.channel);
            if (!contractName) return message;
            
            const contracts = this.access?.legacy?.('contracts') || window.SOVEREIGN_CONTRACTS;
            if (!contracts?.validate) return message;
            
            if (!contracts.validate(contractName, message.payload)) {
                console.warn(`⚠️ Contract Rejected: ${message.channel} (${contractName})`);
                return null;
            }
            
            if (!message.meta) message.meta = {};
            message.meta.contract = { validated: true, name: contractName, validatedAt: Date.now(), version: '1.0.0' };
            return message;
        }, 5);
    }
    
    /* ========================================================
       ISOLATION ZONE MIDDLEWARE (Priority 6)
    ======================================================== */
    registerIsolationMiddleware() {
        const zones = this.access?.legacy?.('zones') || window.SOVEREIGN_ZONES;
        
        const domainMappings = {
            'analytics:capture': 'analytics-domain',
            'analytics:ready': 'analytics-domain',
            'analytics:export': 'analytics-domain',
            'policy:activated': 'governance-domain',
            'policy:ready': 'governance-domain',
            'runtime:errors': 'transport-domain',
            'bus:ready': 'transport-domain',
            'intelligence:state:changed': 'intelligence-domain',
            'intelligence:ready': 'intelligence-domain',
            'intelligence:analysis:completed': 'intelligence-domain',
            'health:update': 'health-domain',
            'system:health:request': 'health-domain',
            'system:health:response': 'health-domain',
            'kernel:heartbeat': 'kernel-domain',
            'kernel:degraded': 'kernel-domain',
            'middleware:ready': 'middleware-domain',
            'middleware:registered': 'middleware-domain'
        };
        
        this.registerMiddleware('isolation-zones', (message) => {
            const domain = domainMappings[message.channel];
            if (!domain) return message;
            if (!zones?.isDomainAllowed) return message;
            
            if (!zones.isDomainAllowed(domain)) {
                console.warn(`🛑 Zone Blocked: ${message.channel} (${domain})`);
                const bus = this.access?.bus?.();
                bus?.publishWithoutMiddleware?.('isolation:zone:blocked', { channel: message.channel, domain, timestamp: Date.now() });
                if (message.envelope) {
                    message.envelope.governance = { ...message.envelope.governance, isolated: true, blockedDomain: domain, blockedReason: 'zone_inactive', blockedAt: Date.now() };
                }
                return null;
            }
            
            if (message.envelope) {
                message.envelope.governance = { ...message.envelope.governance, isolated: false, domain, zoneValidated: true, zoneValidatedAt: Date.now() };
            }
            return message;
        }, 6);
    }

    /* ========================================================
       SANDBOX ENFORCEMENT MIDDLEWARE (Priority 7)
    ======================================================== */
    registerSandboxMiddleware() {
        const sandboxes = this.access?.legacy?.('sandbox') || window.SOVEREIGN_SANDBOX;
        
        const domainMappings = {
            'analytics:capture': 'analytics-domain',
            'analytics:ready': 'analytics-domain',
            'analytics:export': 'analytics-domain',
            'policy:activated': 'governance-domain',
            'policy:ready': 'governance-domain',
            'runtime:errors': 'transport-domain',
            'bus:ready': 'transport-domain',
            'intelligence:state:changed': 'intelligence-domain',
            'intelligence:ready': 'intelligence-domain',
            'intelligence:analysis:completed': 'intelligence-domain',
            'health:update': 'health-domain',
            'system:health:request': 'health-domain',
            'system:health:response': 'health-domain',
            'kernel:heartbeat': 'kernel-domain',
            'kernel:degraded': 'kernel-domain',
            'middleware:ready': 'middleware-domain',
            'middleware:registered': 'middleware-domain'
        };
        
        this.registerMiddleware('sandbox-enforcement', (message) => {
            const domain = domainMappings[message.channel];
            if (!domain) return message;
            if (!sandboxes?.isAllowed) return message;
            
            if (sandboxes.trackMessage) sandboxes.trackMessage(domain);
            
            const allowed = sandboxes.isAllowed(domain);
            
            if (!allowed) {
                const sandboxState = sandboxes.getState ? sandboxes.getState(domain) : {};
                const reason = sandboxState.throttled ? 'throttled' : (sandboxState.quotaExceeded ? 'quota_exceeded' : 'blocked');
                
                console.warn(`📦 Sandbox Blocked: ${domain} (${reason})`);
                const bus = this.access?.bus?.();
                bus?.publishWithoutMiddleware?.('sandbox:execution:blocked', { domain, channel: message.channel, reason, timestamp: Date.now() });
                
                if (message.envelope) {
                    message.envelope.governance = { ...message.envelope.governance, sandboxed: true, throttled: sandboxState.throttled || false, quotaExceeded: sandboxState.quotaExceeded || false, sandboxDomain: domain, blockedReason: reason, blockedAt: Date.now() };
                }
                if (message.meta) {
                    message.meta.sandbox = { blocked: true, domain, reason, blockedAt: Date.now() };
                }
                return null;
            }
            
            if (message.envelope) {
                message.envelope.governance = { ...message.envelope.governance, sandboxed: false, sandboxDomain: domain, sandboxValidated: true, sandboxValidatedAt: Date.now() };
            }
            return message;
        }, 7);
    }

    /* ========================================================
       ANALYTICS MIDDLEWARE (Priority 8)
    ======================================================== */
    registerAnalyticsMiddleware() {
        this.registerMiddleware('analytics', (message) => {
            if (message.isErrorEvent || message.isBlocked) return message;
            
            const cache = this.access?.cache?.() || window.SOVEREIGN_CACHE;
            if (cache?.set) {
                cache.set(`bus-${message.timestamp}-${message.channel}`, {
                    channel: message.channel,
                    runtimeId: message.runtimeId,
                    timestamp: message.timestamp,
                    hasContract: !!message.meta?.contract?.validated,
                    authorized: !!message.envelope?.governance?.authorized,
                    zoneValidated: !!message.envelope?.governance?.zoneValidated,
                    sandboxValidated: !!message.envelope?.governance?.sandboxValidated
                }, 120000);
            }
            return message;
        }, 8);
    }
    
    /* ========================================================
       GET CONTRACT MAPPING
    ======================================================== */
    getContractForChannel(channel) {
        return this.contractMappings.get(channel) || null;
    }
    
    getAllContractMappings() {
        return Object.fromEntries(this.contractMappings);
    }

    /* ========================================================
       GET MIDDLEWARE EXECUTION ORDER
    ======================================================== */
    getMiddlewareExecutionOrder() {
        return [...this.pendingMiddlewares.entries()]
            .sort((a, b) => a[1].priority - b[1].priority)
            .map(([name, { priority }]) => ({ name, priority }));
    }

    /* ========================================================
       GET MIDDLEWARE LIFECYCLE DETAILS
    ======================================================== */
    getMiddlewareLifecycleDetails() {
        const details = [];
        for (const [name, reg] of this.registeredMiddlewares.entries()) {
            details.push({
                name: reg.name,
                priority: reg.priority,
                state: reg.state,
                registeredAt: reg.registeredAt,
                stateChangedAt: reg.stateChangedAt,
                errorCount: reg.errorCount,
                lastError: reg.lastError,
                isApplied: this.middlewaresApplied,
                isExecuting: reg.state === 'active' || (reg.state === 'degraded' && this.debugMode)
            });
        }
        return details;
    }

    /* ========================================================
       STATUS
    ======================================================== */
    getStatus() {
        const stateCounts = { pending: 0, active: 0, suspended: 0, failed: 0, degraded: 0 };
        for (const [, reg] of this.registeredMiddlewares.entries()) {
            stateCounts[reg.state] = (stateCounts[reg.state] || 0) + 1;
        }
        
        return {
            middlewaresCount: this.middlewareCount,
            registeredMiddlewares: [...this.registeredMiddlewares.keys()],
            middlewareExecutionOrder: this.getMiddlewareExecutionOrder(),
            middlewareLifecycleDetails: this.getMiddlewareLifecycleDetails(),
            stateCounts,
            lifecycleEnforcement: true,
            prioritiesEnabled: true,
            middlewaresApplied: this.middlewaresApplied,
            contractMappingsCount: this.contractMappings.size,
            debugMode: this.debugMode,
            accessLayerConnected: !!this._access,
            authorizationEnabled: true,
            isolationEnabled: true,
            sandboxEnabled: true,
            timestamp: Date.now()
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignMiddleware = new SovereignRuntimeMiddleware();

window.SOVEREIGN_MIDDLEWARE = sovereignMiddleware;

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('middleware', sovereignMiddleware);
    console.log('✅ Runtime Middleware registered in Unified Registry');
}

window.SOVEREIGN_EVENTS?.emit('middleware:ready', {
    timestamp: Date.now(),
    status: sovereignMiddleware.getStatus()
});
