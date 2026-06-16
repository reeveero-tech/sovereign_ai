/* ============================================================
   Sovereign AI — runtime-identity-core.js
   الإصدار: 11.0.0
   النواة السيادية لهوية الـ Runtime
   ============================================================ */

class SovereignRuntimeIdentityCore {

    constructor() {

        /* =========================================
           IDENTITY (محسن)
        ========================================= */

        this.identity = {
            id: crypto.randomUUID(),
            name: 'Sovereign Runtime',
            codename: 'AURORA',
            version: '11.0.0',
            generation: 'Cognitive Runtime',
            createdAt: Date.now(),
            lastAwakened: Date.now(),
            uptimeTotal: 0
        };

        /* =========================================
           PERSONALITY (محسن - متعدد الأبعاد)
        ========================================= */

        this.personality = {
            // البعد الأساسي
            behavior: 'adaptive',        // adaptive, protective, aggressive, conservative
            temperament: 'stable',       // stable, volatile, defensive, recovering
            cognition: 'predictive',     // predictive, reactive, analytical, intuitive
            orchestration: 'strategic',  // strategic, tactical, reactive, hybrid
            recovery: 'self-healing',    // self-healing, assisted, graceful, abrupt
            execution: 'fair-governed',  // fair-governed, prioritized, balanced, critical-first
            
            // أبعاد متقدمة (من 2200)
            riskTolerance: 0.5,          // 0 = conservative, 1 = aggressive
            empathy: 0.3,               // sensitivity to subsystem stress
            curiosity: 0.4,             // tendency to explore new patterns
            stabilityPreference: 0.7,   // preference for stable states
            
            // تطور الشخصية
            evolution: {
                original: null,
                mutations: 0,
                lastMutation: null,
                mutationHistory: []
            }
        };

        /* =========================================
           PERSONAS (هويات متعددة - من 2200)
        ========================================= */

        this.personas = {
            active: 'sovereign',
            available: {
                'sovereign': {
                    description: 'Full cognitive runtime with all capabilities',
                    behavior: 'adaptive',
                    temperament: 'stable'
                },
                'guardian': {
                    description: 'Protective mode, focuses on stability and safety',
                    behavior: 'protective',
                    temperament: 'defensive'
                },
                'phoenix': {
                    description: 'Recovery-focused, aggressive healing',
                    behavior: 'adaptive',
                    temperament: 'recovering'
                },
                'sentinel': {
                    description: 'Minimal runtime, critical-only execution',
                    behavior: 'conservative',
                    temperament: 'defensive'
                }
            },
            switchHistory: [],
            automaticSwitching: true
        };

        /* =========================================
           TRAUMA MEMORY (صدمات تشغيلية - من 2200)
        ========================================= */

        this.trauma = {
            events: [],           // أحداث صادمة (انهيارات, شذوذات حرجة)
            impact: 0,           // 0-100, مدى تأثير الصدمات على الشخصية
            resilience: 70,      // 0-100, القدرة على التعافي
            lastTrauma: null,
            permanentChanges: new Map()  // تغييرات دائمة في الشخصية
        };

        /* =========================================
           EVOLUTION (محسن)
        ========================================= */

        this.evolution = {
            stage: 'sovereign-cognitive-fabric',
            maturity: 1,              // 1-10
            adaptations: 0,
            stabilizations: 0,
            recoveries: 0,
            quantumJumps: 0,          // قفزات نوعية كبيرة
            milestones: [],           // معالم التطور
            evolutionHistory: []
        };

        /* =========================================
           RUNTIME SIGNATURE (محسن)
        ========================================= */

        this.signature = {
            topology: 'distributed-cognitive',
            governance: 'behavioral',
            memory: 'persistent',
            fairness: 'adaptive',
            protocol: 'contract-governed',
            hash: null,               // توقيع فريد متغير مع التطور
            lastHashUpdate: null
        };

        /* =========================================
           SELF-DESCRIPTION (وصف ذاتي ديناميكي)
        ========================================= */

        this.selfDescription = {
            short: 'I am AURORA, a Sovereign Cognitive Runtime',
            long: null,
            capabilities: [],
            limitations: [],
            updatedAt: null
        };

        /* =========================================
           HISTORY (محسن)
        ========================================= */

        this.identityHistory = [];
        this.maxHistory = 500;  // زيادة

        /* =========================================
           PERSONALITY DRIFT DETECTION (كشف الانجراف)
        ========================================= */

        this.driftDetection = {
            enabled: true,
            thresholds: {
                behaviorChange: 5,     // 5 تغيرات في الدقيقة
                temperamentChange: 3,
                overallDrift: 0.3      // 30% تغير في الشخصية
            },
            driftAlerts: [],
            lastStabilization: null
        };

        /* =========================================
           METRICS (محسن)
        ========================================= */

        this.metrics = {
            personalityShifts: 0,
            evolutionEvents: 0,
            adaptiveMutations: 0,
            identitySynchronizations: 0,
            personaSwitches: 0,
            traumaEvents: 0,
            selfDescriptionUpdates: 0,
            driftAlertsTriggered: 0,
            quantumJumps: 0
        };

        console.log('🧬 Runtime Identity Core Initialized (Sovereign Personality Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.initializeSelfDescription();
        this.generateSignatureHash();
        this.storeOriginalPersonality();
        this.bindRuntimeSignals();
        this.bindMemorySignals();
        this.startEvolutionLoop();
        this.startDriftDetection();
        this.startUptimeTracker();
        this.publishReady();
    }

    /* ========================================================
       SELF-DESCRIPTION (وصف ذاتي ديناميكي)
    ======================================================== */

    initializeSelfDescription() {
        this.updateSelfDescription();
    }

    updateSelfDescription() {
        const capabilities = [];
        const limitations = [];

        // بناء قائمة القدرات ديناميكياً
        if (window.SOVEREIGN_COGNITION) capabilities.push('predictive cognition');
        if (window.SOVEREIGN_COGNITIVE_MEMORY) capabilities.push('persistent memory');
        if (window.SOVEREIGN_COGNITIVE_ORCHESTRATOR) capabilities.push('strategic orchestration');
        if (window.SOVEREIGN_EXECUTION_DOMAINS) capabilities.push('domain isolation');
        if (window.SOVEREIGN_FAIRNESS_ENGINE) capabilities.push('execution fairness');
        if (window.SOVEREIGN_PRESSURE_GOVERNOR) capabilities.push('pressure governance');

        this.selfDescription = {
            short: `I am ${this.identity.codename}, a ${this.personality.behavior} ${this.evolution.stage}`,
            long: `${this.identity.name} (${this.identity.codename}) - Generation ${this.identity.generation}. ` +
                  `Personality: ${this.personality.behavior}/${this.personality.temperament}. ` +
                  `Maturity Level: ${this.evolution.maturity}/10.`,
            capabilities,
            limitations,
            updatedAt: Date.now()
        };

        this.metrics.selfDescriptionUpdates++;
        this.syncBodyState();
    }

    storeOriginalPersonality() {
        this.personality.evolution.original = { ...this.personality };
    }

    generateSignatureHash() {
        const data = `${this.identity.id}|${this.identity.codename}|${this.personality.behavior}|${this.personality.temperament}|${this.evolution.maturity}|${Date.now()}`;
        // محاكاة هاش بسيطة
        let hash = 0;
        for (let i = 0; i < data.length; i++) {
            hash = ((hash << 5) - hash) + data.charCodeAt(i);
            hash |= 0;
        }
        this.signature.hash = Math.abs(hash).toString(16);
        this.signature.lastHashUpdate = Date.now();
    }

    /* ========================================================
       PERSONAS MANAGEMENT (إدارة الهويات المتعددة)
    ======================================================== */

    switchPersona(personaName, reason = 'manual') {
        const persona = this.personas.available[personaName];
        if (!persona) {
            console.warn(`Persona ${personaName} not found`);
            return false;
        }

        const oldPersona = this.personas.active;
        this.personas.active = personaName;
        
        // تطبيق سمات الشخصية
        this.personality.behavior = persona.behavior;
        this.personality.temperament = persona.temperament;
        
        this.personas.switchHistory.push({
            from: oldPersona,
            to: personaName,
            reason,
            timestamp: Date.now()
        });
        
        this.metrics.personaSwitches++;
        this.recordIdentityEvent({ type: 'persona_switch', from: oldPersona, to: personaName, reason });
        this.updateSelfDescription();
        this.publishPersonaSwitch(personaName);
        
        console.log(`🧬 Persona switched: ${oldPersona} → ${personaName} (${reason})`);
        return true;
    }

    autoSwitchPersona() {
        if (!this.personas.automaticSwitching) return;
        
        const system = window.SOVEREIGN_SYSTEM_STATE?.getStatus?.();
        const telemetry = window.SOVEREIGN_FLOW_TELEMETRY?.getStatus?.();
        
        if (!system || !telemetry) return;
        
        // قرارات آلية للتبديل بين الشخصيات
        if (telemetry.stability < 30 && this.personas.active !== 'sentinel') {
            this.switchPersona('sentinel', 'auto_critical_instability');
        } else if (system.mode === 'recovery' && this.personas.active !== 'phoenix') {
            this.switchPersona('phoenix', 'auto_recovery_mode');
        } else if (telemetry.stability > 80 && system.health > 70 && this.personas.active !== 'sovereign') {
            this.switchPersona('sovereign', 'auto_stable_health');
        } else if (system.mode === 'critical' && this.personas.active !== 'guardian') {
            this.switchPersona('guardian', 'auto_critical_mode');
        }
    }

    /* ========================================================
       TRAUMA MANAGEMENT (إدارة الصدمات التشغيلية)
    ======================================================== */

    recordTrauma(event) {
        this.trauma.events.push({
            ...event,
            timestamp: Date.now(),
            impact: this.calculateTraumaImpact(event)
        });
        
        this.trauma.lastTrauma = event;
        this.trauma.events = this.trauma.events.slice(-50); // آخر 50 صدمة
        this.metrics.traumaEvents++;
        
        // حساب التأثير التراكمي
        this.calculateCumulativeTrauma();
        
        // تأثير الصدمة على الشخصية
        this.applyTraumaToPersonality(event);
        
        this.publishTrauma(event);
    }

    calculateTraumaImpact(event) {
        let impact = 20; // تأثير أساسي
        
        if (event.severity === 'critical') impact = 60;
        else if (event.severity === 'high') impact = 40;
        else if (event.severity === 'moderate') impact = 20;
        
        if (event.type === 'complete_collapse') impact = 80;
        if (event.type === 'critical_anomaly') impact = 50;
        
        return Math.min(100, impact);
    }

    calculateCumulativeTrauma() {
        const recentTrauma = this.trauma.events.filter(e => e.timestamp > Date.now() - 3600000); // آخر ساعة
        let totalImpact = 0;
        
        for (const event of recentTrauma) {
            totalImpact += event.impact;
        }
        
        // تطبيق المرونة (resilience)
        this.trauma.impact = Math.max(0, Math.min(100, totalImpact * (1 - this.trauma.resilience / 100)));
    }

    applyTraumaToPersonality(event) {
        if (event.impact < 30) return;
        
        // تغييرات دائمة في الشخصية بناءً على الصدمات
        if (event.type === 'critical_instability') {
            this.personality.stabilityPreference = Math.min(0.9, this.personality.stabilityPreference + 0.1);
            this.trauma.permanentChanges.set('stability_preference', this.personality.stabilityPreference);
        }
        
        if (event.type === 'fairness_collapse') {
            this.personality.empathy = Math.min(0.8, this.personality.empathy + 0.15);
            this.trauma.permanentChanges.set('empathy', this.personality.empathy);
        }
        
        if (event.type === 'memory_corruption') {
            this.personality.curiosity = Math.max(0.1, this.personality.curiosity - 0.1);
            this.trauma.permanentChanges.set('curiosity', this.personality.curiosity);
        }
        
        this.updateSelfDescription();
    }

    /* ========================================================
       PERSONALITY DRIFT DETECTION (كشف الانجراف)
    ======================================================== */

    startDriftDetection() {
        this._driftInterval = setInterval(() => {
            if (!this.driftDetection.enabled) return;
            this.detectPersonalityDrift();
        }, 60000);
    }

    detectPersonalityDrift() {
        const recentShifts = this.identityHistory.filter(
            h => h.type === 'personality-shift' && h.timestamp > Date.now() - 60000
        ).length;
        
        const recentTemperamentShifts = this.identityHistory.filter(
            h => h.type === 'personality-shift' && 
                 h.changes?.temperament && 
                 h.timestamp > Date.now() - 60000
        ).length;
        
        let driftDetected = false;
        
        if (recentShifts > this.driftDetection.thresholds.behaviorChange) {
            driftDetected = true;
            this.driftDetection.driftAlerts.push({
                type: 'behavior_drift',
                severity: 'warning',
                shiftsPerMinute: recentShifts,
                timestamp: Date.now()
            });
        }
        
        if (recentTemperamentShifts > this.driftDetection.thresholds.temperamentChange) {
            driftDetected = true;
            this.driftDetection.driftAlerts.push({
                type: 'temperament_drift',
                severity: 'warning',
                shiftsPerMinute: recentTemperamentShifts,
                timestamp: Date.now()
            });
        }
        
        if (driftDetected) {
            this.metrics.driftAlertsTriggered++;
            this.stabilizePersonality();
        }
        
        // تنظيف التنبيهات القديمة
        this.driftDetection.driftAlerts = this.driftDetection.driftAlerts.slice(-100);
    }

    stabilizePersonality() {
        // إعادة تثبيت الشخصية إلى أقرب حالة مستقرة
        const lastStableState = this.identityHistory.findLast(h => h.type === 'stabilization');
        
        if (lastStableState) {
            console.log('🧬 Personality stabilization triggered - reverting to last stable state');
            // تطبيق التثبيت
            this.personality.behavior = lastStableState.snapshot?.behavior || this.personality.behavior;
            this.personality.temperament = lastStableState.snapshot?.temperament || this.personality.temperament;
        }
        
        this.driftDetection.lastStabilization = Date.now();
        this.recordIdentityEvent({ type: 'stabilization', snapshot: { ...this.personality } });
        this.updateSelfDescription();
    }

    /* ========================================================
       SIGNALS (محسن)
    ======================================================== */

    bindRuntimeSignals() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:mode:transition', payload => this.observeModeTransition(payload));
        bus.subscribe('runtime:cognitive:orchestration', payload => this.observeCognition(payload));
        bus.subscribe('runtime:governor:decision', payload => this.observeGovernor(payload));
        bus.subscribe('runtime:cognition:anomaly', payload => this.observeAnomaly(payload));
    }

    bindMemorySignals() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:cognitive:memory', payload => {
            if (payload.consolidated > 10) {
                this.evolution.quantumJumps++;
                this.metrics.quantumJumps++;
                this.recordIdentityEvent({ type: 'quantum_jump', consolidated: payload.consolidated });
            }
        });
    }

    observeAnomaly(payload = {}) {
        const anomaly = payload.anomaly;
        if (!anomaly) return;
        
        if (anomaly.severity === 'critical') {
            this.recordTrauma({
                type: anomaly.type,
                severity: anomaly.severity,
                description: anomaly.description || 'Critical anomaly detected'
            });
        }
    }

    observeModeTransition(payload = {}) {
        const current = payload.current;
        if (!current) return;

        switch (current) {
            case 'critical':
                this.shiftPersonality({ temperament: 'defensive', behavior: 'protective' }, 'mode_critical');
                break;
            case 'recovery':
                this.shiftPersonality({ temperament: 'recovering', behavior: 'adaptive' }, 'mode_recovery');
                break;
            case 'normal':
                this.shiftPersonality({ temperament: 'stable', behavior: 'adaptive' }, 'mode_normal');
                break;
        }
        
        this.autoSwitchPersona();
    }

    observeCognition(payload = {}) {
        const action = payload.action;
        if (!action) return;

        this.evolution.adaptations++;
        this.recordIdentityEvent({ type: 'cognitive-action', action });

        if (action === 'critical-stabilization') {
            this.personality.temperament = 'defensive';
            this.updateSelfDescription();
        }
    }

    observeGovernor(payload = {}) {
        const mode = payload.mode;

        if (mode === 'critical') {
            this.evolution.stabilizations++;
            this.personality.behavior = 'stabilizing';
            this.updateSelfDescription();
        }

        if (mode === 'recovery') {
            this.evolution.recoveries++;
            this.personality.behavior = 'adaptive';
            this.updateSelfDescription();
        }
    }

    /* ========================================================
       PERSONALITY SHIFT (محسن)
    ======================================================== */

    shiftPersonality(changes = {}, reason = 'unknown') {
        const oldBehavior = this.personality.behavior;
        const oldTemperament = this.personality.temperament;
        
        Object.assign(this.personality, changes);
        
        this.metrics.personalityShifts++;
        
        this.recordIdentityEvent({
            type: 'personality-shift',
            changes,
            reason,
            old: { behavior: oldBehavior, temperament: oldTemperament },
            new: { behavior: this.personality.behavior, temperament: this.personality.temperament }
        });
        
        this.updateSelfDescription();
        this.syncBodyState();
        
        console.log(`🧬 Personality shifted | REASON: ${reason} | CHANGES:`, changes);
    }

    /* ========================================================
       EVOLUTION (محسن)
    ======================================================== */

    startEvolutionLoop() {
        this._evolutionInterval = setInterval(() => {
            this.evaluateEvolution();
            this.autoSwitchPersona();
        }, 7000);
    }

    startUptimeTracker() {
        this._uptimeInterval = setInterval(() => {
            this.identity.uptimeTotal = Date.now() - this.identity.createdAt;
        }, 60000);
    }

    evaluateEvolution() {
        const cognition = window.SOVEREIGN_COGNITION?.getStatus?.();
        const telemetry = window.SOVEREIGN_FLOW_TELEMETRY?.getStatus?.();
        const memory = window.SOVEREIGN_COGNITIVE_MEMORY?.getStatus?.();
        const orchestrator = window.SOVEREIGN_COGNITIVE_ORCHESTRATOR?.getStatus?.();

        if (!cognition || !telemetry) return;

        // حساب نضج النظام
        const score = (cognition.metrics?.predictions || 0) + 
                      (telemetry.metrics?.stateTransitions || 0) +
                      (memory?.patterns || 0) +
                      (orchestrator?.metrics?.orchestrations || 0);

        const oldMaturity = this.evolution.maturity;
        
        if (score > 200 && this.evolution.maturity < 5) {
            this.evolution.maturity = 5;
        } else if (score > 100 && this.evolution.maturity < 3) {
            this.evolution.maturity = 3;
        } else if (score > 50 && this.evolution.maturity < 2) {
            this.evolution.maturity = 2;
        }
        
        if (oldMaturity !== this.evolution.maturity) {
            this.evolution.milestones.push({
                maturity: this.evolution.maturity,
                score,
                timestamp: Date.now()
            });
            this.recordIdentityEvent({ type: 'maturity_increase', from: oldMaturity, to: this.evolution.maturity });
            this.updateSelfDescription();
            this.publishEvolution();
        }

        // تطور استباقي بناءً على الخبرة
        if (cognition.metrics?.preventiveActions > 10 && this.evolution.stage !== 'self-protective') {
            this.evolveIdentity('self-protective');
        }
        
        if (memory?.patterns > 100 && this.evolution.stage !== 'pattern-master') {
            this.evolveIdentity('pattern-master');
        }
        
        if (orchestrator?.metrics?.parallelExecutions > 50 && this.evolution.stage !== 'quantum-orchestrator') {
            this.evolveIdentity('quantum-orchestrator');
        }
    }

    evolveIdentity(stage) {
        const oldStage = this.evolution.stage;
        this.evolution.stage = stage;
        this.metrics.evolutionEvents++;
        
        this.evolution.evolutionHistory.push({
            from: oldStage,
            to: stage,
            timestamp: Date.now()
        });
        
        this.recordIdentityEvent({ type: 'evolution', from: oldStage, to: stage });
        this.updateSelfDescription();
        
        console.log(`🧬 Runtime Identity Evolved | FROM: ${oldStage} → TO: ${stage}`);
        this.publishEvolution();
    }

    /* ========================================================
       HISTORY (محسن)
    ======================================================== */

    recordIdentityEvent(event = {}) {
        this.identityHistory.push({
            ...event,
            timestamp: Date.now()
        });

        if (this.identityHistory.length > this.maxHistory) {
            this.identityHistory.shift();
        }
    }

    /* ========================================================
       BODY SYNC (محسن)
    ======================================================== */

    syncBodyState() {
        if (typeof document === 'undefined') return;

        document.body.dataset.runtimeIdentity = this.identity.codename;
        document.body.dataset.runtimeBehavior = this.personality.behavior;
        document.body.dataset.runtimeTemperament = this.personality.temperament;
        document.body.dataset.runtimeEvolution = this.evolution.stage;
        document.body.dataset.runtimeMaturity = this.evolution.maturity;
        document.body.dataset.runtimePersona = this.personas.active;
        document.body.dataset.runtimeTrauma = Math.round(this.trauma.impact);
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishEvolution() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:identity:evolved', {
                identity: this.identity,
                evolution: this.evolution,
                personality: this.personality,
                timestamp: Date.now()
            });
        }
    }

    publishPersonaSwitch(personaName) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:identity:persona-switch', {
                persona: personaName,
                timestamp: Date.now()
            });
        }
    }

    publishTrauma(event) {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime:identity:trauma', {
                event,
                cumulativeImpact: this.trauma.impact,
                timestamp: Date.now()
            });
        }
    }

    publishReady() {
        const bus = window.SOVEREIGN_ACCESS?.bus?.();
        
        if (bus && typeof bus.publishWithoutMiddleware === 'function') {
            bus.publishWithoutMiddleware('runtime-identity-core:ready', {
                codename: this.identity.codename,
                generation: this.identity.generation,
                personality: this.personality.behavior,
                personas: Object.keys(this.personas.available),
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       PROFILE (محسن)
    ======================================================== */

    getIdentityProfile() {
        return {
            identity: this.identity,
            personality: this.personality,
            evolution: this.evolution,
            signature: this.signature,
            personas: {
                active: this.personas.active,
                available: Object.keys(this.personas.available)
            },
            trauma: {
                impact: this.trauma.impact,
                resilience: this.trauma.resilience,
                events: this.trauma.events.length
            },
            selfDescription: this.selfDescription
        };
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {
        return {
            codename: this.identity.codename,
            generation: this.identity.generation,
            maturity: this.evolution.maturity,
            stage: this.evolution.stage,
            personality: this.personality,
            activePersona: this.personas.active,
            trauma: {
                impact: this.trauma.impact,
                resilience: this.trauma.resilience,
                events: this.trauma.events.length
            },
            drift: {
                alerts: this.driftDetection.driftAlerts.length,
                lastStabilization: this.driftDetection.lastStabilization
            },
            history: this.identityHistory.length,
            uptime: this.identity.uptimeTotal,
            metrics: { ...this.metrics }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {
        if (this._evolutionInterval) {
            clearInterval(this._evolutionInterval);
            this._evolutionInterval = null;
        }
        if (this._driftInterval) {
            clearInterval(this._driftInterval);
            this._driftInterval = null;
        }
        if (this._uptimeInterval) {
            clearInterval(this._uptimeInterval);
            this._uptimeInterval = null;
        }
        
        this.identityHistory = [];
        this.personas.switchHistory = [];
        this.trauma.events = [];
        this.evolution.milestones = [];
        
        console.log('🧬 Runtime Identity Core Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeIdentityCore =
    new SovereignRuntimeIdentityCore();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_IDENTITY =
    sovereignRuntimeIdentityCore;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {
    window.SOVEREIGN.register('identity-core', sovereignRuntimeIdentityCore);
}
