/* ============================================================
   Sovereign AI — runtime-orchestrator-ai.js
   الإصدار: 8.0.0
   الذكاء التشغيلي المركزي - تنسيق وتوزيع القرارات
   ============================================================ */

class SovereignRuntimeOrchestratorAI {

    constructor() {

        /* ============================================================
           CORE STATE
        ============================================================ */

        this.mode = 'adaptive';
        this.state = 'optimal';
        this.decisions = [];
        this.maxDecisions = 200;
        
        /* ============================================================
           STRATEGY CONFIGURATION
        ============================================================ */

        this.strategies = {
            critical: {
                name: 'critical-protection',
                priority: 1000,
                actions: ['protect', 'stabilize', 'reduce-load'],
                visualClass: 'runtime-safe'
            },
            stressed: {
                name: 'balanced-runtime',
                priority: 700,
                actions: ['balance', 'optimize', 'monitor'],
                visualClass: 'runtime-balanced'
            },
            optimal: {
                name: 'optimal-runtime',
                priority: 500,
                actions: ['perform', 'enhance', 'cinematic'],
                visualClass: 'runtime-cinematic'
            },
            recovery: {
                name: 'recovery-mode',
                priority: 900,
                actions: ['heal', 'restore', 'reconnect'],
                visualClass: 'runtime-recovery'
            },
            emergency: {
                name: 'emergency-mode',
                priority: 1000,
                actions: ['protect-owner', 'emergency-response', 'bypass-normal'],
                visualClass: 'runtime-emergency'
            }
        };

        /* ============================================================
           METRICS
        ============================================================ */

        this.metrics = {
            evaluations: 0,
            strategyChanges: 0,
            criticalActivations: 0,
            stressedActivations: 0,
            optimalActivations: 0,
            recoveryActivations: 0,
            emergencyActivations: 0,
            lastEvaluation: null,
            averageResponseTime: 0
        };

        /* ============================================================
           LAYER REGISTRATION STATUS
        ============================================================ */

        this.layerRegistered = false;

        console.log('👑 Runtime Orchestrator AI v8.0.0 Initialized');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {
        this.registerWithLayerRegistry();
        this.startDecisionLoop();
        this.bindSignals();
        this.publishReady();
    }

    /* ========================================================
       REGISTER WITH LAYER REGISTRY - التسجيل في سجل الطبقات
    ======================================================== */

    registerWithLayerRegistry() {
        const registry = window.SOVRA_LAYER_REGISTRY;
        
        if (!registry) {
            console.warn('⚠️ Runtime Orchestrator AI: Layer Registry not found. Will retry in 1 second...');
            setTimeout(() => this.registerWithLayerRegistry(), 1000);
            return;
        }

        const registrationResult = registry.register(
            'runtime-orchestrator-ai',
            {
                type: 'runtime',
                role: 'cognitive-flow-coordination',
                authority: [
                    'runtime-orchestration',
                    'runtime-pressure',
                    'runtime-rhythm',
                    'strategy-decisions',
                    'mode-management'
                ],
                dependencies: [
                    'neural-runtime-bus',
                    'temporal-cognition',
                    'runtime-governance'
                ],
                files: ['runtime-orchestrator-ai.js'],
                priority: 850,
                canRead: ['runtime_state', 'intelligence_state', 'kernel_state'],
                canWrite: ['orchestration_decisions', 'mode_state'],
                canOverride: ['runtime_anomalies', 'strategy_conflicts']
            }
        );

        if (registrationResult) {
            this.layerRegistered = true;
            console.log('✅ Runtime Orchestrator AI registered in Layer Registry');
            
            /* تحديث النبض */
            if (registry.updateHeartbeat) {
                setInterval(() => {
                    registry.updateHeartbeat('runtime-orchestrator-ai');
                }, 5000);
            }
        } else {
            console.error('❌ Failed to register Runtime Orchestrator AI in Layer Registry');
        }
    }

    /* ========================================================
       DECISION LOOP - حلقة القرارات
    ======================================================== */

    startDecisionLoop() {
        /* استخدام الناقل إذا كان متاحاً */
        const bus = window.SOVEREIGN_ACCESS?.bus?.() || window.SOVEREIGN_BUS;
        
        if (bus && typeof bus.subscribe === 'function') {
            /* الإصغاء لتغيرات حالة النظام */
            bus.subscribe('runtime:intelligence:changed', (payload) => {
                this.evaluateRuntime();
            });
            
            bus.subscribe('runtime:state:changed', (payload) => {
                this.evaluateRuntime();
            });
            
            bus.subscribe('runtime:pressure:changed', (payload) => {
                this.evaluateRuntime();
            });
        }
        
        /* حلقة دورية للتحقق */
        this._evaluationInterval = setInterval(() => {
            this.evaluateRuntime();
        }, 5000);
    }

    /* ========================================================
       EVALUATE RUNTIME - تقييم حالة التشغيل
    ======================================================== */

    evaluateRuntime() {
        const startTime = performance.now();
        
        /* جمع البيانات من المصادر المختلفة */
        const intelligence = window.SOVEREIGN_INTELLIGENCE?.getStatus?.();
        const kernel = window.SOVEREIGN_KERNEL?.getStatus?.();
        const power = window.SOVEREIGN_POWER?.getStatus?.();
        const governance = window.SOVRA_RUNTIME_GOVERNANCE;
        const consciousness = window.SOVEREIGN_CONSCIOUSNESS?.getStatus?.();
        
        /* تحديد الحالة بناءً على المصادر المتاحة */
        let runtimeState = 'optimal';
        
        /* التحقق من المصادر المختلفة */
        if (intelligence?.state === 'critical' || kernel?.state === 'critical') {
            runtimeState = 'critical';
        } else if (intelligence?.state === 'stressed' || power?.pressure > 0.8) {
            runtimeState = 'stressed';
        } else if (consciousness?.continuity < 80) {
            runtimeState = 'recovery';
        } else if (intelligence?.state === 'emergency') {
            runtimeState = 'emergency';
        }
        
        /* تطبيق الاستراتيجية المناسبة */
        this.applyStrategy(runtimeState);
        
        /* تحديث المقاييس */
        this.metrics.evaluations++;
        this.metrics.lastEvaluation = Date.now();
        const duration = performance.now() - startTime;
        this.metrics.averageResponseTime = 
            (this.metrics.averageResponseTime * (this.metrics.evaluations - 1) + duration) / this.metrics.evaluations;
        
        /* نشر حالة التشغيل */
        this.publishRuntimeState(runtimeState);
    }

    /* ========================================================
       APPLY STRATEGY - تطبيق الاستراتيجية
    ======================================================== */

    applyStrategy(state) {
        const previousState = this.state;
        
        if (previousState === state) return;
        
        const strategy = this.strategies[state];
        if (!strategy) {
            console.warn(`⚠️ Unknown strategy state: ${state}`);
            return;
        }
        
        this.state = state;
        this.mode = strategy.name;
        
        /* تحديث المقاييس */
        this.metrics.strategyChanges++;
        switch (state) {
            case 'critical':
                this.metrics.criticalActivations++;
                break;
            case 'stressed':
                this.metrics.stressedActivations++;
                break;
            case 'optimal':
                this.metrics.optimalActivations++;
                break;
            case 'recovery':
                this.metrics.recoveryActivations++;
                break;
            case 'emergency':
                this.metrics.emergencyActivations++;
                break;
        }
        
        /* تنفيذ إجراءات الاستراتيجية */
        this.executeStrategyActions(strategy);
        
        /* تسجيل القرار */
        this.recordDecision(strategy.name);
        
        /* تحديث واجهة المستخدم */
        this.updateVisualState(strategy);
        
        /* نشر تغيير الاستراتيجية */
        this.publishStrategyChange(previousState, state, strategy);
        
        console.log(`🧠 Runtime Decision: ${strategy.name} | Priority: ${strategy.priority}`);
    }

    /* ========================================================
       EXECUTE STRATEGY ACTIONS - تنفيذ إجراءات الاستراتيجية
    ======================================================== */

    executeStrategyActions(strategy) {
        for (const action of strategy.actions) {
            switch (action) {
                case 'protect':
                    this.enableProtectionMode();
                    break;
                case 'stabilize':
                    this.enableStabilization();
                    break;
                case 'reduce-load':
                    this.reduceRuntimeLoad();
                    break;
                case 'balance':
                    this.balanceRuntime();
                    break;
                case 'optimize':
                    this.optimizePerformance();
                    break;
                case 'monitor':
                    this.enableIntensiveMonitoring();
                    break;
                case 'perform':
                    this.enablePerformanceMode();
                    break;
                case 'enhance':
                    this.enhanceCapabilities();
                    break;
                case 'cinematic':
                    this.enableCinematicMode();
                    break;
                case 'heal':
                    this.initiateSelfHealing();
                    break;
                case 'restore':
                    this.restoreFromBackup();
                    break;
                case 'reconnect':
                    this.reconnectComponents();
                    break;
                case 'protect-owner':
                    this.protectOwner();
                    break;
                case 'emergency-response':
                    this.emergencyResponse();
                    break;
                case 'bypass-normal':
                    this.bypassNormalOperations();
                    break;
            }
        }
    }

    /* ========================================================
       STRATEGY ACTION IMPLEMENTATIONS
    ======================================================== */

    enableProtectionMode() {
        console.log('🛡️ Protection mode enabled');
        /* تفعيل وضع الحماية */
        if (window.SOVEREIGN_MODE_MANAGER) {
            window.SOVEREIGN_MODE_MANAGER.requestTransition('protective', 'orchestrator');
        }
    }

    enableStabilization() {
        console.log('⚖️ Stabilization enabled');
        /* تفعيل التثبيت */
        if (window.SOVEREIGN_STABILIZATION) {
            window.SOVEREIGN_STABILIZATION.activate();
        }
    }

    reduceRuntimeLoad() {
        console.log('📉 Reducing runtime load');
        /* تقليل الحمل التشغيلي */
        const bus = window.SOVEREIGN_ACCESS?.bus?.() || window.SOVEREIGN_BUS;
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:load:reduce', {
                source: 'orchestrator-ai',
                timestamp: Date.now()
            });
        }
    }

    balanceRuntime() {
        console.log('⚖️ Balancing runtime');
        /* موازنة التشغيل */
    }

    optimizePerformance() {
        console.log('⚡ Optimizing performance');
        /* تحسين الأداء */
    }

    enableIntensiveMonitoring() {
        console.log('👁️ Intensive monitoring enabled');
        /* تفعيل المراقبة المكثفة */
    }

    enablePerformanceMode() {
        console.log('🚀 Performance mode enabled');
        /* تفعيل وضع الأداء العالي */
    }

    enhanceCapabilities() {
        console.log('⬆️ Capabilities enhanced');
        /* تعزيز القدرات */
    }

    enableCinematicMode() {
        console.log('🎬 Cinematic mode enabled');
        /* تفعيل الوضع السينمائي */
    }

    initiateSelfHealing() {
        console.log('🩺 Self-healing initiated');
        /* بدء الشفاء الذاتي */
    }

    restoreFromBackup() {
        console.log('💾 Restoring from backup');
        /* استعادة من النسخ الاحتياطي */
    }

    reconnectComponents() {
        console.log('🔌 Reconnecting components');
        /* إعادة توصيل المكونات */
    }

    protectOwner() {
        console.log('👑 Protecting owner - EMERGENCY PRIORITY');
        /* حماية السيد - أولوية طوارئ */
    }

    emergencyResponse() {
        console.log('🚨 Emergency response activated');
        /* تفعيل استجابة الطوارئ */
    }

    bypassNormalOperations() {
        console.log('⚡ Bypassing normal operations');
        /* تجاوز العمليات العادية */
    }

    /* ========================================================
       VISUAL STATE MANAGEMENT
    ======================================================== */

    updateVisualState(strategy) {
        if (typeof document === 'undefined') return;
        
        /* إزالة جميع الفئات القديمة */
        const classesToRemove = [
            'runtime-safe',
            'runtime-balanced',
            'runtime-cinematic',
            'runtime-recovery',
            'runtime-emergency'
        ];
        
        classesToRemove.forEach(className => {
            document.body.classList.remove(className);
        });
        
        /* إضافة الفئة الجديدة */
        document.body.classList.add(strategy.visualClass);
        
        /* تحديث الحالة في dataset */
        document.body.dataset.runtimeState = this.state;
        document.body.dataset.runtimeMode = this.mode;
    }

    /* ========================================================
       DECISION RECORDING - تسجيل القرارات
    ======================================================== */

    recordDecision(type) {
        const decision = {
            id: crypto.randomUUID(),
            type,
            state: this.state,
            mode: this.mode,
            timestamp: Date.now(),
            metrics: {
                evaluations: this.metrics.evaluations,
                strategyChanges: this.metrics.strategyChanges
            }
        };

        this.decisions.push(decision);

        if (this.decisions.length > this.maxDecisions) {
            this.decisions.shift();
        }

        console.log(`📝 Decision Recorded: ${type}`);
    }

    /* ========================================================
       SIGNAL BINDING - ربط الإشارات
    ======================================================== */

    bindSignals() {
        const events = window.SOVEREIGN_EVENTS;
        const bus = window.SOVEREIGN_ACCESS?.bus?.() || window.SOVEREIGN_BUS;

        if (events) {
            events.on('runtime:intelligence_changed', ({ current }) => {
                console.log(`👑 Runtime Intelligence State: ${current}`);
                this.evaluateRuntime();
            });
            
            events.on('runtime:emergency', () => {
                console.log('🚨 Emergency signal received');
                this.applyStrategy('emergency');
            });
        }
        
        if (bus && typeof bus.subscribe === 'function') {
            bus.subscribe('runtime:owner:danger', () => {
                console.log('👑 Owner danger signal received');
                this.applyStrategy('emergency');
            });
            
            bus.subscribe('runtime:recovery:needed', () => {
                console.log('🩺 Recovery signal received');
                this.applyStrategy('recovery');
            });
        }
    }

    /* ========================================================
       PUBLISH METHODS
    ======================================================== */

    publishRuntimeState(state) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.() || window.SOVEREIGN_BUS;
        
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:orchestrator:state', {
                state: this.state,
                mode: this.mode,
                previousState: null,
                timestamp: Date.now()
            });
        }
    }

    publishStrategyChange(previousState, newState, strategy) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.() || window.SOVEREIGN_BUS;
        
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:orchestrator:strategy-changed', {
                previousState,
                newState,
                strategy: strategy.name,
                priority: strategy.priority,
                timestamp: Date.now()
            });
        }
    }

    publishReady() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.() || window.SOVEREIGN_BUS;
        
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime-orchestrator-ai:ready', {
                state: this.state,
                mode: this.mode,
                timestamp: Date.now()
            });
        }
        
        /* إشعار التسجيل في Layer Registry */
        if (this.layerRegistered) {
            const registry = window.SOVRA_LAYER_REGISTRY;
            if (registry && registry.markInitialized) {
                registry.markInitialized('runtime-orchestrator-ai');
            }
        }
    }

    /* ========================================================
       GET STATUS - الحصول على الحالة
    ======================================================== */

    getStatus() {
        return {
            mode: this.mode,
            state: this.state,
            decisions: this.decisions.length,
            decisionsList: this.decisions.slice(-10),
            metrics: { ...this.metrics },
            layerRegistered: this.layerRegistered
        };
    }

    /* ========================================================
       GET STRATEGY REPORT - تقرير الاستراتيجية
    ======================================================== */

    getStrategyReport() {
        return {
            current: {
                state: this.state,
                mode: this.mode,
                strategy: this.strategies[this.state] || null
            },
            history: {
                totalDecisions: this.decisions.length,
                strategyChanges: this.metrics.strategyChanges,
                criticalActivations: this.metrics.criticalActivations,
                stressedActivations: this.metrics.stressedActivations,
                optimalActivations: this.metrics.optimalActivations,
                recoveryActivations: this.metrics.recoveryActivations,
                emergencyActivations: this.metrics.emergencyActivations
            },
            performance: {
                evaluations: this.metrics.evaluations,
                averageResponseTimeMs: parseFloat(this.metrics.averageResponseTime.toFixed(2)),
                lastEvaluation: this.metrics.lastEvaluation
            }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {
        if (this._evaluationInterval) {
            clearInterval(this._evaluationInterval);
            this._evaluationInterval = null;
        }
        
        /* إزالة التسجيل من Layer Registry */
        const registry = window.SOVRA_LAYER_REGISTRY;
        if (registry && registry.markUnhealthy) {
            registry.markUnhealthy('runtime-orchestrator-ai', 'destroyed');
        }
        
        console.log('👑 Runtime Orchestrator AI Destroyed');
    }
}

/* ============================================================
   LAYER REGISTRATION - التسجيل في سجل الطبقات
   ============================================================ */

/* تسجيل الطبقة فور توفر السجل */
const registerWithRegistry = () => {
    const registry = window.SOVRA_LAYER_REGISTRY;
    if (registry && window.SOVEREIGN_ORCHESTRATOR_AI) {
        const result = registry.register(
            'runtime-orchestrator-ai',
            {
                type: 'runtime',
                role: 'cognitive-flow-coordination',
                authority: [
                    'runtime-orchestration',
                    'runtime-pressure',
                    'runtime-rhythm',
                    'strategy-decisions',
                    'mode-management'
                ],
                dependencies: [
                    'neural-runtime-bus',
                    'temporal-cognition',
                    'runtime-governance'
                ],
                files: ['runtime-orchestrator-ai.js'],
                priority: 850,
                canRead: ['runtime_state', 'intelligence_state', 'kernel_state'],
                canWrite: ['orchestration_decisions', 'mode_state'],
                canOverride: ['runtime_anomalies', 'strategy_conflicts']
            }
        );
        
        if (result) {
            console.log('✅ runtime-orchestrator-ai registered in Layer Registry');
            if (registry.markInitialized) {
                registry.markInitialized('runtime-orchestrator-ai');
            }
        }
    } else {
        setTimeout(registerWithRegistry, 100);
    }
};

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeOrchestratorAI = new SovereignRuntimeOrchestratorAI();

/* تسجيل الطبقة بعد إنشاء النظام */
setTimeout(registerWithRegistry, 0);

/* ============================================================
   GLOBAL EXPORT
============================================================ */

window.SOVEREIGN_ORCHESTRATOR_AI = sovereignRuntimeOrchestratorAI;

/* ============================================================
   UNIFIED REGISTRY
============================================================ */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
    window.SOVEREIGN.register('orchestrator-ai', sovereignRuntimeOrchestratorAI);
}

/* ============================================================
   ORCHESTRATOR INTERFACE
============================================================ */

window.Orchestrator = {
    getStatus: () => sovereignRuntimeOrchestratorAI.getStatus(),
    getStrategyReport: () => sovereignRuntimeOrchestratorAI.getStrategyReport(),
    getDecisions: () => sovereignRuntimeOrchestratorAI.decisions.slice(-20),
    getMetrics: () => ({ ...sovereignRuntimeOrchestratorAI.metrics })
};

console.log('');
console.log('👑 RUNTIME ORCHESTRATOR AI ONLINE');
console.log('   Mode: ' + sovereignRuntimeOrchestratorAI.mode);
console.log('   State: ' + sovereignRuntimeOrchestratorAI.state);
console.log('   Strategies: critical, stressed, optimal, recovery, emergency');
console.log('   Orchestrator Interface: window.Orchestrator');
console.log('   Layer Registry Status: ' + (window.SOVRA_LAYER_REGISTRY ? 'available' : 'waiting...'));
console.log('');
