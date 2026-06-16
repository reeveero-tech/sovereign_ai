/* ============================================================
   Sovereign AI — runtime-policy-engine.js
   الإصدار: 7.2.0 (Runtime Governance Service)
   
   الوظيفة: تقييم وتطبيق السياسات بناءً على حالة Runtime.
   الحدود: 
     - يقوم ONLY بتقييم السياسات وتطبيق الإجراءات.
     - لا يحتوي على منطق أعمال (Business Logic) ثقيل.
     - لا يدير الموارد مباشرة.
     - لا يتخذ قرارات Orchestration.
     
   مستقبلاً: قد ينقسم إلى:
     - PolicyEvaluator
     - PolicyExecutor
     - PolicyTelemetry
     - PolicyLifecycleManager
   ============================================================ */

class SovereignRuntimePolicyEngine {

    constructor() {

        this.policies = new Map();

        // Cache for access layer
        this._access = null;

        console.log(
            '📜 Runtime Policy Engine Initialized (Governance Service)'
        );

        this.init();
    }

    /* ========================================================
       ACCESS HELPER (Runtime Access Layer)
    ======================================================== */
    get access() {
        if (!this._access && window.SOVEREIGN_ACCESS) {
            this._access = window.SOVEREIGN_ACCESS;
            console.log('✅ Policy Engine connected to Runtime Access Layer');
        }
        return this._access;
    }

    /* ========================================================
       SAFE ACCESS TO LEGACY SYSTEMS (Migration Fallback)
       تستخدم فقط للأنظمة التي لم تُهاجر بعد إلى Access Layer
    ======================================================== */
    getLegacy(systemName) {
        // محاولة الوصول عبر Unified Registry أولاً
        if (window.SOVEREIGN?.get) {
            const system = window.SOVEREIGN.get(systemName);
            if (system) return system;
        }
        
        // Fallback إلى الـ globals القديمة
        const legacyMap = {
            'kernel': window.SOVEREIGN_KERNEL,
            'bus': window.SOVEREIGN_BUS,
            'resources': window.SOVEREIGN_RESOURCES,
            'recovery': window.SOVEREIGN_RECOVERY,
            'scheduler': window.SOVEREIGN_SCHEDULER,
            'notify': window.SOVEREIGN_NOTIFY
        };
        
        return legacyMap[systemName];
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.registerDefaultPolicies();
        this.startPolicyEvaluation();
        this.emitReady();
    }

    /* ========================================================
       EMIT READY (للـ Runtime Observability)
    ======================================================== */
    emitReady() {
        const access = this.access;
        const bus = access?.bus();
        
        if (bus) {
            bus.publish('policy:ready', {
                timestamp: Date.now(),
                policiesCount: this.policies.size,
                source: 'policy-engine'
            });
        }
        
        // Legacy event للتوافق
        window.SOVEREIGN_EVENTS?.emit('policy:ready', {
            timestamp: Date.now()
        });
    }

    /* ========================================================
       DEFAULT POLICIES (مع تحسين التكرار)
    ======================================================== */
    registerDefaultPolicies() {
        const access = this.access;
        const bus = access?.bus();
        
        /* =========================================
           POLICY 1: PERFORMANCE PROTECTION
           يعتمد على Kernel عبر Access Layer
        ========================================= */
        this.registerPolicy(
            'performance-protection',
            () => {
                const kernel = access?.kernel?.()?.getStatus?.();
                return kernel?.health < 50;
            },
            () => {
                document.body.classList.add('runtime-safe');
                
                const notify = access?.notify?.();
                if (notify?.warning) {
                    notify.warning('Performance Protection Policy Activated');
                } else {
                    this.getLegacy('notify')?.warning('Performance Protection Policy Activated');
                }
                
                bus?.publish('policy:activated', {
                    policy: 'performance-protection',
                    reason: 'kernel_health_low',
                    health: access?.kernel?.()?.getStatus?.()?.health,
                    timestamp: Date.now()
                });
            }
        );

        /* =========================================
           POLICY 2: RESOURCE LIMITER
           يعتمد على Resources عبر Access Layer
        ========================================= */
        this.registerPolicy(
            'resource-limiter',
            () => {
                const resources = access?.resources?.()?.getStatus?.();
                return resources?.pressure > 40;
            },
            () => {
                document.body.classList.add('runtime-low-effects');
                
                bus?.publish('policy:activated', {
                    policy: 'resource-limiter',
                    reason: 'resource_pressure_high',
                    timestamp: Date.now()
                });
            }
        );

        /* =========================================
           POLICY 3: SECURITY HARDENING
           ملاحظة: Recovery ليس ضمن Runtime Access Layer بعد.
           يستخدم getLegacy مع توثيق النقص.
        ========================================= */
        this.registerPolicy(
            'security-hardening',
            () => {
                // TODO: إضافة recovery() إلى Runtime Access Layer لاحقاً
                const recovery = this.getLegacy('recovery');
                const recoveryStatus = recovery?.getStatus?.();
                return recoveryStatus?.attempts > 2;
            },
            () => {
                document.body.classList.add('runtime-secure');
                
                const notify = access?.notify?.();
                if (notify?.warning) {
                    notify.warning('Security Hardening Enabled');
                } else {
                    this.getLegacy('notify')?.warning('Security Hardening Enabled');
                }
                
                bus?.publish('policy:activated', {
                    policy: 'security-hardening',
                    reason: 'recovery_attempts_exceeded',
                    timestamp: Date.now()
                });
            }
        );
        
        /* =========================================
           POLICY 4: CONNECTION STABILITY
        ========================================= */
        this.registerPolicy(
            'connection-stability',
            () => {
                const connectionStatus = document.body.dataset.runtimeState;
                return connectionStatus === 'offline' || connectionStatus === 'degraded';
            },
            () => {
                document.body.classList.add('runtime-connection-warning');
                
                bus?.publish('policy:activated', {
                    policy: 'connection-stability',
                    reason: 'unstable_connection',
                    state: document.body.dataset.runtimeState,
                    timestamp: Date.now()
                });
            }
        );
    }

    /* ========================================================
       REGISTER POLICY
    ======================================================== */
    registerPolicy(name, condition, action) {
        if (this.policies.has(name)) {
            console.warn(`Policy "${name}" already registered. Overwriting.`);
        }
        
        this.policies.set(name, {
            condition,
            action,
            active: false,
            activatedAt: null,
            deactivatedAt: null,
            activationCount: 0
        });

        console.log(`📜 Policy Registered: ${name}`);
    }

    /* ========================================================
       EVALUATION LOOP (باستخدام Scheduler مع Fallback)
    ======================================================== */
    startPolicyEvaluation() {
        const access = this.access;
        let scheduler = access?.scheduler?.();
        
        if (!scheduler && window.SOVEREIGN?.get) {
            scheduler = window.SOVEREIGN.get('scheduler');
        }
        
        if (!scheduler) {
            scheduler = this.getLegacy('scheduler');
        }

        if (!scheduler?.registerTask) {
            console.warn('⚠️ Scheduler not available. Policy evaluation using fallback interval.');
            setInterval(() => this.evaluatePolicies(), 5000);
            return;
        }

        scheduler.registerTask(
            'runtime-policy-engine',
            () => this.evaluatePolicies(),
            5000
        );
    }

    /* ========================================================
       EVALUATE POLICIES (CORE LOGIC)
       ملاحظة: هذا الجزء سيُنقل مستقبلاً إلى PolicyEvaluator منفصل
    ======================================================== */
    evaluatePolicies() {
        const access = this.access;
        const bus = access?.bus();
        let activatedCount = 0;
        let deactivatedCount = 0;
        
        for (const [name, policy] of this.policies.entries()) {
            try {
                const shouldActivate = policy.condition();

                if (shouldActivate && !policy.active) {
                    policy.active = true;
                    policy.activatedAt = Date.now();
                    policy.activationCount++;
                    policy.action();
                    activatedCount++;
                    console.log(`✅ Policy Activated: ${name}`);

                } else if (!shouldActivate && policy.active) {
                    policy.active = false;
                    policy.deactivatedAt = Date.now();
                    deactivatedCount++;
                    console.log(`♻️ Policy Released: ${name}`);
                }
            } catch (error) {
                console.error(`Policy Error (${name})`, error);
                
                bus?.publish('policy:error', {
                    policy: name,
                    error: error.message,
                    timestamp: Date.now()
                });
            }
        }
        
        // إرسال تحديث الحالة إذا كانت هناك تغييرات
        if ((activatedCount > 0 || deactivatedCount > 0) && bus) {
            bus.publish('policy:state:changed', {
                activated: activatedCount,
                deactivated: deactivatedCount,
                timestamp: Date.now(),
                activePolicies: this.getActivePolicyNames()
            });
        }
    }

    /* ========================================================
       GET ACTIVE POLICY NAMES
    ======================================================== */
    getActivePolicyNames() {
        return [...this.policies.entries()]
            .filter(([_, policy]) => policy.active)
            .map(([name]) => name);
    }

    /* ========================================================
       STATUS (مع Telemetry محسّنة)
    ======================================================== */
    getStatus() {
        const activePolicies = this.getActivePolicyNames();
        const policiesSummary = [...this.policies.entries()].map(([name, policy]) => ({
            name,
            active: policy.active,
            activationCount: policy.activationCount,
            activatedAt: policy.activatedAt
        }));
        
        return {
            totalPolicies: this.policies.size,
            activeCount: activePolicies.length,
            active: activePolicies,
            policies: [...this.policies.keys()],
            policiesSummary,
            accessLayerConnected: !!this._access,
            timestamp: Date.now()
        };
    }
    
    /* ========================================================
       MANUAL POLICY CONTROL (Administrative API)
       للاستخدام في Dashboards و Runtime Inspector
    ======================================================== */
    triggerPolicy(policyName) {
        const policy = this.policies.get(policyName);
        if (!policy) {
            console.warn(`Policy "${policyName}" not found`);
            return false;
        }
        
        if (!policy.active) {
            policy.active = true;
            policy.activatedAt = Date.now();
            policy.activationCount++;
            policy.action();
            console.log(`🔧 Manual Policy Activated: ${policyName}`);
            return true;
        }
        return false;
    }
    
    releasePolicy(policyName) {
        const policy = this.policies.get(policyName);
        if (!policy) {
            console.warn(`Policy "${policyName}" not found`);
            return false;
        }
        
        if (policy.active) {
            policy.active = false;
            policy.deactivatedAt = Date.now();
            console.log(`🔧 Manual Policy Released: ${policyName}`);
            return true;
        }
        return false;
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
   - Legacy Global: للتوافق مع الأنظمة القديمة
   - Unified Registry: للتسجيل في النواة الموحدة
============================================================ */

const sovereignPolicyEngine = new SovereignRuntimePolicyEngine();

window.SOVEREIGN_POLICY = sovereignPolicyEngine;

if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('policy', sovereignPolicyEngine);
    console.log('✅ Policy Engine registered in Unified Registry');
} else {
    console.warn('⚠️ Unified Registry not yet available. Policy Engine registered as legacy global only.');
}

// إشهار النظام للأنظمة القديمة
window.SOVEREIGN_EVENTS?.emit('policy:ready', {
    timestamp: Date.now(),
    status: sovereignPolicyEngine.getStatus()
});
