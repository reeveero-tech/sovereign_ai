/* ============================================================
   Sovereign AI — runtime-middleware.js
   الإصدار: 7.2.0 (Runtime Governance Enforcement Pipeline)
   
   الوظيفة: 
     - إدارة Middleware Pipeline للـ Bus
     - تنفيذ Core Middleware (إضافة runtimeId, processedAt)
     - تنفيذ Security Middleware (التحقق من صحة المدخلات)
     - تنفيذ Analytics Middleware (تخزين مؤقت للرسائل)
     - تنفيذ Contract Validation Middleware (التحقق من صحة العقود)
     
   المبادئ:
     - Middleware مسؤول عن معالجة الرسائل قبل وصولها إلى المستمعين
     - يمكن لأي Middleware إرجاع null لحظر الرسالة تماماً
     - العقود تحدد هيكل الرسائل المسموح بها
     - الـ Metadata معزولة في message.meta عن payload
     
   مستقبلاً (Runtime Standards & Protocols):
     ✅ Unified Message Schema
     ✅ Runtime Protocol Definitions
     ✅ Runtime Trace IDs
     ✅ Distributed Runtime Context
     ✅ Service Lifecycle Contracts
     
   التقسيم المستقبلي للملف:
     - MiddlewareRegistry (تسجيل وإدارة الـ Middlewares)
     - CoreMiddleware
     - SecurityMiddleware
     - AnalyticsMiddleware
     - ContractMiddleware
   ============================================================ */

class SovereignRuntimeMiddleware {

    constructor() {

        this.middlewareCount = 0;
        
        // Cache for access layer
        this._access = null;
        
        // ✅ FIX 1: Dynamic contract mappings (Runtime Configuration)
        this.contractMappings = new Map();
        
        // ✅ FIX 2: Debug mode to prevent noisy telemetry
        this.debugMode = false;  // Set to true for development only
        
        // Registered middlewares for telemetry
        this.registeredMiddlewares = new Map();

        console.log(
            '🧩 Runtime Middleware Initialized (Governance Pipeline Ready)'
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
       INIT
    ======================================================== */
    init() {
        this.initContractMappings();
        this.registerCoreMiddleware();
        this.registerSecurityMiddleware();
        this.registerAnalyticsMiddleware();
        this.registerContractMiddleware();
        this.emitReady();
    }

    /* ========================================================
       INIT CONTRACT MAPPINGS (Runtime Configuration)
    ======================================================== */
    initContractMappings() {
        // Define all channel → contract mappings
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
       SET DEBUG MODE (Runtime Configuration)
    ======================================================== */
    setDebugMode(enabled) {
        this.debugMode = enabled;
        console.log(`🐛 Debug mode: ${enabled ? 'ON' : 'OFF'}`);
        
        const bus = this.access?.bus?.();
        bus?.publish('middleware:debug:changed', {
            debugMode: enabled,
            timestamp: Date.now()
        });
    }

    /* ========================================================
       UNIFIED MIDDLEWARE REGISTRATION (FIX 3)
       يوحد التسجيل، التليمتري، والـ ordering
    ======================================================== */
    registerMiddleware(name, handler, priority = 10) {
        const bus = this.access?.bus?.() || window.SOVEREIGN_BUS;
        
        if (!bus) {
            console.warn(`⚠️ Cannot register "${name}" middleware: Bus not available`);
            return false;
        }
        
        if (typeof handler !== 'function') {
            console.warn(`⚠️ Cannot register "${name}" middleware: Handler must be a function`);
            return false;
        }
        
        // Store metadata for telemetry
        this.registeredMiddlewares.set(name, {
            name,
            priority,
            registeredAt: Date.now(),
            active: true
        });
        
        // Register the handler
        bus.use(handler);
        this.middlewareCount++;
        
        console.log(`✅ Middleware Registered: ${name} (Priority: ${priority})`);
        
        // Emit telemetry
        const bus2 = this.access?.bus?.();
        bus2?.publish('middleware:registered', {
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
        // Note: Unregistering middleware requires bus.unuse() which is not implemented yet
        console.warn(`⚠️ Unregister middleware "${name}" not yet supported (needs bus.unuse())`);
        return false;
    }

    /* ========================================================
       EMIT READY (للـ Runtime Observability)
    ======================================================== */
    emitReady() {
        const access = this.access;
        const bus = access?.bus?.();
        
        if (bus) {
            bus.publish('middleware:ready', {
                timestamp: Date.now(),
                middlewareCount: this.middlewareCount,
                contractMappingsCount: this.contractMappings.size,
                source: 'runtime-middleware',
                version: '7.2.0'
            });
        }
        
        window.SOVEREIGN_EVENTS?.emit('middleware:ready', {
            timestamp: Date.now(),
            middlewareCount: this.middlewareCount
        });
    }

    /* ========================================================
       CORE MIDDLEWARE
       يضيف runtimeId و processedAt وهيكل meta لكل رسالة
    ======================================================== */
    registerCoreMiddleware() {
        this.registerMiddleware('core', (message) => {
            if (!message.runtimeId) {
                message.runtimeId = crypto.randomUUID();
            }
            message.processedAt = Date.now();
            
            // ✅ FIX 4: Initialize meta structure if not exists
            if (!message.meta) {
                message.meta = {};
            }
            
            // Add core metadata
            message.meta.core = {
                runtimeId: message.runtimeId,
                processedAt: message.processedAt,
                middlewareVersion: '7.2.0'
            };
            
            return message;
        }, 1); // Highest priority (executes first)
    }

    /* ========================================================
       SECURITY MIDDLEWARE
       يتحقق من صحة المدخلات قبل المعالجة
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
                        // ✅ Return null to block the message (Runtime Enforcement)
                        return null;
                    }
                }
                
                // Add security metadata
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
       ANALYTICS MIDDLEWARE
       يخزن نسخة من الرسائل في Cache للتتبع
    ======================================================== */
    registerAnalyticsMiddleware() {
        this.registerMiddleware('analytics', (message) => {
            // Don't store error messages or blocked messages
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
                        hasContract: !!message.meta?.contract?.validated
                    },
                    120000 // 2 minutes TTL
                );
            }
            
            return message;
        }, 8); // Lower priority (executes after contract validation)
    }

    /* ========================================================
       CONTRACT VALIDATION MIDDLEWARE
       يتحقق من أن الرسائل تتبع العقود المحددة مسبقاً
       هذا هو "Runtime Contracts Layer" الحقيقي
    ======================================================== */
    registerContractMiddleware() {
        this.registerMiddleware('contract', (message) => {
            // Initialize meta if not exists
            if (!message.meta) {
                message.meta = {};
            }
            
            // Get contract name from dynamic mappings
            const contractName = this.contractMappings.get(message.channel);
            
            // If no contract defined for this channel
            if (!contractName) {
                // Only log in debug mode to avoid noisy telemetry
                if (this.debugMode && !message.channel?.startsWith('runtime:')) {
                    console.debug(`📝 No contract defined for channel: ${message.channel}`);
                }
                return message;
            }
            
            // Get contracts registry
            const contracts = this.access?.legacy?.('contracts') || window.SOVEREIGN_CONTRACTS;
            
            // If contracts not available, allow message (transitional phase)
            if (!contracts?.validate) {
                if (this.debugMode) {
                    console.debug(`⚠️ Contract validation skipped for ${contractName} (Contracts Registry not ready)`);
                }
                return message;
            }
            
            // Validate message against contract
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
                
                // ✅ Return null to block the message (Runtime Governance Enforcement)
                return null;
            }
            
            // ✅ FIX 4: Add contract metadata to message.meta (isolated from payload)
            message.meta.contract = {
                validated: true,
                name: contractName,
                validatedAt: Date.now(),
                version: '1.0.0'
            };
            
            return message;
        }, 5); // Medium priority (after core/security, before analytics)
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
       STATUS (مع Telemetry محسّنة)
    ======================================================== */
    getStatus() {
        const activeMiddlewares = [...this.registeredMiddlewares.keys()];
        
        return {
            middlewaresCount: this.middlewareCount,
            registeredMiddlewares: activeMiddlewares,
            contractMappingsCount: this.contractMappings.size,
            contractMappings: this.getAllContractMappings(),
            debugMode: this.debugMode,
            accessLayerConnected: !!this._access,
            timestamp: Date.now()
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
   - Legacy Global: للتوافق مع الأنظمة القديمة
   - Unified Registry: للتسجيل في النواة الموحدة
============================================================ */

const sovereignMiddleware = new SovereignRuntimeMiddleware();

/* =========================================
   Legacy Global (للتوافق مع الأنظمة القديمة)
========================================= */

window.SOVEREIGN_MIDDLEWARE = sovereignMiddleware;

/* =========================================
   Unified Registry (التسجيل في النواة الموحدة)
========================================= */

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('middleware', sovereignMiddleware);
    console.log('✅ Runtime Middleware registered in Unified Registry');
} else {
    console.warn('⚠️ Unified Registry not yet available. Middleware registered as legacy global only.');
}

// ============================================================
// إشهار النظام للأنظمة القديمة
// ============================================================
window.SOVEREIGN_EVENTS?.emit('middleware:ready', {
    timestamp: Date.now(),
    status: sovereignMiddleware.getStatus()
});
