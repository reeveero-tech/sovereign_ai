/* ============================================================
   Sovereign AI — runtime-intelligence.js
   الإصدار: 7.2.0 (Cognitive Runtime Coordination Service)
   
   الوظيفة: 
     - تحليل حالة Runtime بشكل دوري
     - اتخاذ قرارات تكيفية بناءً على التحليل
     - إصدار أوامر للتكيف (Adaptation Commands) عبر Bus
     
   المبادئ:
     1. Intelligence "يُقرر" و"يُبلغ" (يقوم بالتحليل وإصدار القرارات)
     2. Intelligence "لا يُنفّذ" تأثيرات DOM مباشرة (يُترك لـ UI Adaptation Layer)
     3. Intelligence يعتمد على Bus-first communication
     
   مستقبلاً:
     - نقل getLegacy() إلى Runtime Access Layer
     - نقل DOM mutations إلى UI Adaptation Layer
     - إضافة Policy-based adaptation
   ============================================================ */

class SovereignRuntimeIntelligence {

    constructor() {

        this.state = 'optimal';

        this.analysisHistory = [];

        // Cache for access layer
        this._access = null;

        console.log(
            '🧠 Runtime Intelligence Initialized (Cognitive Service)'
        );

        this.init();
    }

    /* ========================================================
       ACCESS HELPER (Runtime Access Layer)
    ======================================================== */
    get access() {
        if (!this._access && window.SOVEREIGN_ACCESS) {
            this._access = window.SOVEREIGN_ACCESS;
            console.log('✅ Runtime Intelligence connected to Runtime Access Layer');
        }
        return this._access;
    }

    /* ========================================================
       SAFE ACCESS TO LEGACY SYSTEMS (Migration Fallback)
       
       ⚠️ NOTE: This method is duplicated across services (policy, intelligence).
       ✅ TODO: Move getLegacy() to Runtime Access Layer to eliminate duplication.
       ✅ Target: this.access.legacy('systemName')
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
            'metrics': window.SOVEREIGN_METRICS,
            'power': window.SOVEREIGN_POWER,
            'recovery': window.SOVEREIGN_RECOVERY,
            'scheduler': window.SOVEREIGN_SCHEDULER,
            'notify': window.SOVEREIGN_NOTIFY,
            'events': window.SOVEREIGN_EVENTS,
            'analytics': window.SOVEREIGN_ANALYTICS
        };
        
        return legacyMap[systemName];
    }

    /* ========================================================
       HELPER: SAFE FPS EXTRACTION
       ✅ Fix: Prevents undefined scoring by providing multiple fallbacks
    ======================================================== */
    extractFps(metrics) {
        if (!metrics) return 60;
        
        // Try different possible property names
        const fps = metrics.fps ||
                    metrics.averageFPS ||
                    metrics.latest?.fps ||
                    metrics.currentFps ||
                    60;
        
        return typeof fps === 'number' ? fps : 60;
    }

    /* ========================================================
       INIT
    ======================================================== */
    init() {
        this.startAnalysisLoop();
        this.bindSignals();
        this.emitReady();
    }

    /* ========================================================
       EMIT READY (Runtime Observability)
    ======================================================== */
    emitReady() {
        const access = this.access;
        const bus = access?.bus();
        
        if (bus) {
            bus.publish('intelligence:ready', {
                timestamp: Date.now(),
                state: this.state,
                source: 'runtime-intelligence',
                version: '7.2.0'
            });
        }
        
        window.SOVEREIGN_EVENTS?.emit('intelligence:ready', {
            timestamp: Date.now(),
            state: this.state
        });
    }

    /* ========================================================
       ANALYSIS LOOP (باستخدام Scheduler)
    ======================================================== */
    startAnalysisLoop() {
        const access = this.access;
        let scheduler = access?.scheduler?.();
        
        if (!scheduler && window.SOVEREIGN?.get) {
            scheduler = window.SOVEREIGN.get('scheduler');
        }
        
        if (!scheduler) {
            scheduler = this.getLegacy('scheduler');
        }

        if (!scheduler?.registerTask) {
            console.warn('⚠️ Scheduler not available. Intelligence analysis using fallback interval.');
            setInterval(() => this.analyzeRuntime(), 4000);
            return;
        }

        scheduler.registerTask(
            'runtime-intelligence',
            () => this.analyzeRuntime(),
            4000
        );
    }

    /* ========================================================
       ANALYZE RUNTIME (Core Cognitive Logic)
       
       ✅ This method only ANALYZES and DECIDES.
       ❌ It does NOT mutate DOM directly (delegates to UI Adaptation Layer via Bus)
    ======================================================== */
    analyzeRuntime() {
        const access = this.access;
        const startTime = performance.now();
        
        // Collect data from various sources
        const analytics = access?.analytics?.();
        const metricsReport = analytics?.generateReport?.();
        const metrics = metricsReport || this.getLegacy('metrics')?.getMetrics?.();
        
        const kernel = access?.kernel?.()?.getStatus?.() || this.getLegacy('kernel')?.getStatus?.();
        const power = this.getLegacy('power')?.getStatus?.();
        const recovery = this.getLegacy('recovery')?.getStatus?.();
        const resources = access?.resources?.()?.getStatus?.();

        if (!metrics || !kernel) {
            console.warn('⚠️ Runtime Intelligence: Missing metrics or kernel data');
            return;
        }

        // ✅ Safe FPS extraction with fallbacks
        const fps = this.extractFps(metrics);
        
        let score = 100;
        const factors = [];

        /* =========================================
           FPS ANALYSIS
        ========================================= */
        if (fps < 25) {
            score -= 25;
            factors.push({ factor: 'fps_critical', value: fps, penalty: 25 });
        } else if (fps < 35) {
            score -= 15;
            factors.push({ factor: 'fps_low', value: fps, penalty: 15 });
        } else if (fps < 45) {
            score -= 5;
            factors.push({ factor: 'fps_moderate', value: fps, penalty: 5 });
        }

        /* =========================================
           HEALTH ANALYSIS
        ========================================= */
        if (kernel.health < 40) {
            score -= 30;
            factors.push({ factor: 'health_critical', value: kernel.health, penalty: 30 });
        } else if (kernel.health < 60) {
            score -= 20;
            factors.push({ factor: 'health_low', value: kernel.health, penalty: 20 });
        } else if (kernel.health < 80) {
            score -= 10;
            factors.push({ factor: 'health_moderate', value: kernel.health, penalty: 10 });
        }

        /* =========================================
           RECOVERY ANALYSIS
        ========================================= */
        if (recovery?.attempts > 3) {
            score -= 20;
            factors.push({ factor: 'recovery_high', value: recovery.attempts, penalty: 20 });
        } else if (recovery?.attempts > 2) {
            score -= 15;
            factors.push({ factor: 'recovery_moderate', value: recovery.attempts, penalty: 15 });
        } else if (recovery?.attempts > 1) {
            score -= 5;
            factors.push({ factor: 'recovery_low', value: recovery.attempts, penalty: 5 });
        }

        /* =========================================
           POWER ANALYSIS
        ========================================= */
        if (power?.mode === 'safe') {
            score -= 20;
            factors.push({ factor: 'power_safe', penalty: 20 });
        } else if (power?.mode === 'degraded') {
            score -= 10;
            factors.push({ factor: 'power_degraded', penalty: 10 });
        }

        /* =========================================
           RESOURCE ANALYSIS
        ========================================= */
        if (resources?.pressure > 70) {
            score -= 15;
            factors.push({ factor: 'resource_critical', value: resources.pressure, penalty: 15 });
        } else if (resources?.pressure > 50) {
            score -= 10;
            factors.push({ factor: 'resource_high', value: resources.pressure, penalty: 10 });
        } else if (resources?.pressure > 30) {
            score -= 5;
            factors.push({ factor: 'resource_moderate', value: resources.pressure, penalty: 5 });
        }

        // Ensure score is within bounds
        score = Math.max(0, Math.min(100, score));

        const analysisDuration = performance.now() - startTime;
        const previousState = this.state;
        
        this.evaluateState(score);

        this.storeAnalysis({
            score,
            fps,
            metrics,
            kernel,
            power,
            recovery,
            resources,
            factors,
            analysisDuration,
            timestamp: Date.now()
        });
        
        // ✅ Enhanced Telemetry Stream
        const bus = access?.bus();
        if (bus) {
            bus.publish('intelligence:analysis:completed', {
                score,
                fps,
                previousState,
                newState: this.state,
                stateChanged: previousState !== this.state,
                factors,
                analysisDurationMs: parseFloat(analysisDuration.toFixed(2)),
                timestamp: Date.now(),
                source: 'runtime-intelligence'
            });
        }
    }

    /* ========================================================
       EVALUATE STATE (Decision Logic)
    ======================================================== */
    evaluateState(score) {
        let nextState = 'optimal';

        if (score < 80) nextState = 'stable';
        if (score < 60) nextState = 'stressed';
        if (score < 40) nextState = 'critical';
        if (score < 20) nextState = 'catastrophic';

        if (nextState !== this.state) {
            this.transitionState(nextState);
        }
    }

    /* ========================================================
       TRANSITION STATE (Decision Broadcast)
       
       ✅ Intelligence "decides" and "broadcasts"
       ❌ Intelligence does NOT mutate DOM directly
       ✅ DOM mutations are delegated to UI Adaptation Layer via Bus
    ======================================================== */
    transitionState(state) {
        const previous = this.state;
        const score = this.getCurrentScore();
        this.state = state;

        console.log(`
🧠 Runtime Intelligence Decision
FROM: ${previous}
TO:   ${state}
SCORE: ${score}
        `);

        // ✅ Broadcast decision to Bus (UI Adaptation Layer should listen)
        const access = this.access;
        const bus = access?.bus();
        
        if (bus) {
            bus.publish('intelligence:state:changed', {
                previous,
                current: state,
                score,
                timestamp: Date.now(),
                source: 'runtime-intelligence',
                requiresAdaptation: true,
                recommendedActions: this.getRecommendedActions(state)
            });
        }
        
        // Legacy event for backward compatibility
        window.SOVEREIGN_EVENTS?.emit('runtime:intelligence_changed', {
            previous,
            current: state,
            score
        });
        
        // ⚠️ TEMPORARY: Direct DOM mutation during migration phase
        // ✅ TODO: Move these DOM mutations to UI Adaptation Layer
        // Target: UI Adaptation Layer subscribes to 'intelligence:state:changed'
        this.applyTemporaryDomEffects(state);
    }
    
    /* ========================================================
       TEMPORARY DOM EFFECTS (Migration Phase Only)
       
       ⚠️ WARNING: Direct DOM mutation will be removed in future versions.
       ✅ TODO: Move to UI Adaptation Layer
    ======================================================== */
    applyTemporaryDomEffects(state) {
        // These are temporary during migration
        document.body.dataset.intelligence = state;
        
        const notify = this.access?.notify?.() || this.getLegacy('notify');
        
        switch (state) {
            case 'catastrophic':
                document.body.classList.add('runtime-critical', 'runtime-safe');
                notify?.error('Runtime Catastrophic Mode');
                break;
            case 'critical':
                document.body.classList.add('runtime-safe');
                document.body.classList.remove('runtime-critical');
                notify?.warning('Runtime Critical Mode');
                break;
            case 'stressed':
                document.body.classList.add('runtime-balanced');
                document.body.classList.remove('runtime-safe', 'runtime-critical');
                break;
            case 'optimal':
                document.body.classList.remove('runtime-safe', 'runtime-balanced', 'runtime-critical');
                break;
        }
        
        // Broadcast that UI adaptation is needed (for future UI Adaptation Layer)
        const bus = this.access?.bus();
        if (bus) {
            bus.publish('ui:adaptation:required', {
                state,
                classes: this.getRecommendedClasses(state),
                timestamp: Date.now(),
                source: 'runtime-intelligence'
            });
        }
    }
    
    /* ========================================================
       RECOMMENDED ACTIONS (For UI Adaptation Layer)
    ======================================================== */
    getRecommendedActions(state) {
        const actions = {
            catastrophic: ['enable_safe_mode', 'reduce_effects', 'notify_operator'],
            critical: ['enable_safe_mode', 'reduce_effects'],
            stressed: ['reduce_animations', 'optimize_rendering'],
            stable: ['maintain_current'],
            optimal: ['enable_full_experience']
        };
        return actions[state] || actions.stable;
    }
    
    getRecommendedClasses(state) {
        const classes = {
            catastrophic: ['runtime-critical', 'runtime-safe'],
            critical: ['runtime-safe'],
            stressed: ['runtime-balanced'],
            stable: [],
            optimal: []
        };
        return classes[state] || [];
    }

    /* ========================================================
       GET CURRENT SCORE
    ======================================================== */
    getCurrentScore() {
        const lastAnalysis = this.analysisHistory[this.analysisHistory.length - 1];
        return lastAnalysis?.score || 100;
    }

    /* ========================================================
       STORE ANALYSIS HISTORY
    ======================================================== */
    storeAnalysis(data) {
        this.analysisHistory.push(data);
        if (this.analysisHistory.length > 100) {
            this.analysisHistory.shift();
        }
    }

    /* ========================================================
       SIGNALS BINDING (Bus-first Communication)
    ======================================================== */
    bindSignals() {
        // Legacy events (backward compatibility)
        window.SOVEREIGN_EVENTS?.on('performance:critical', () => {
            this.transitionState('critical');
        });
        
        // ✅ Bus-first communication (primary channel)
        const access = this.access;
        const bus = access?.bus();
        
        if (bus) {
            bus.subscribe('system:health:critical', (payload) => {
                console.log('📡 Intelligence received critical health event via Bus');
                this.transitionState('critical');
            });
            
            bus.subscribe('intelligence:analyze:now', () => {
                this.analyzeRuntime();
            });
            
            bus.subscribe('intelligence:get:status', (payload, meta) => {
                bus.publish('intelligence:status:response', {
                    status: this.getStatus(),
                    requestId: meta?.messageId,
                    timestamp: Date.now()
                });
            });
        }
    }

    /* ========================================================
       STATUS (Enhanced Telemetry)
    ======================================================== */
    getStatus() {
        const lastAnalysis = this.analysisHistory[this.analysisHistory.length - 1];
        
        return {
            state: this.state,
            currentScore: lastAnalysis?.score || 100,
            currentFps: lastAnalysis?.fps || null,
            historyLength: this.analysisHistory.length,
            accessLayerConnected: !!this._access,
            lastAnalysis: lastAnalysis ? {
                timestamp: lastAnalysis.timestamp,
                score: lastAnalysis.score,
                fps: lastAnalysis.fps,
                factors: lastAnalysis.factors
            } : null,
            timestamp: Date.now()
        };
    }
    
    /* ========================================================
       GET ANALYSIS HISTORY (Operational API)
    ======================================================== */
    getHistory(limit = 20) {
        return this.analysisHistory.slice(-limit);
    }
    
    /* ========================================================
       RESET HISTORY
    ======================================================== */
    resetHistory() {
        this.analysisHistory = [];
        console.log('🧹 Runtime Intelligence history reset');
        
        const bus = this.access?.bus();
        bus?.publish('intelligence:history:reset', {
            timestamp: Date.now(),
            source: 'runtime-intelligence'
        });
    }
}

/* ============================================================
   إنشاء النظام العالمي (Hybrid Phase)
   - Legacy Global: للتوافق مع الأنظمة القديمة
   - Unified Registry: للتسجيل في النواة الموحدة
============================================================ */

const sovereignIntelligence = new SovereignRuntimeIntelligence();

// Legacy Global
window.SOVEREIGN_INTELLIGENCE = sovereignIntelligence;

// Unified Registry
if (window.SOVEREIGN?.register) {
    window.SOVEREIGN.register('intelligence', sovereignIntelligence);
    console.log('✅ Runtime Intelligence registered in Unified Registry');
} else {
    console.warn('⚠️ Unified Registry not available. Intelligence registered as legacy global only.');
}

// Legacy announcement
window.SOVEREIGN_EVENTS?.emit('intelligence:ready', {
    timestamp: Date.now(),
    state: sovereignIntelligence.getStatus().state
});
