/* ============================================================
   Sovereign AI — runtime-mode-manager.js
   الإصدار: 9.0.0
   مدير الأنماط السلوكية السيادي
   ============================================================ */

class SovereignRuntimeModeManager {

    constructor() {

        /* =========================================
           MODES
        ========================================= */

        this.currentMode =
            'normal';

        this.previousMode =
            null;

        this.transitionLocked =
            false;

        /* =========================================
           SOURCE PRIORITIES (أولويات المصادر)
        ========================================= */

        this.sourcePriority = {

            'pressure-governor': 100,
            'health-system': 90,
            'mode-manager': 85,
            'orchestrator': 80,
            'kernel': 75,
            'lifecycle': 70,
            'runtime': 60,
            'user': 50,
            'unknown': 40
        };

        /* =========================================
           ALLOWED TRANSITIONS (محسن)
        ========================================= */

        this.allowedTransitions = {

            normal: {
                to: ['elevated', 'degraded', 'recovery'],
                requiresHealth: null,
                requiresPressure: null
            },

            elevated: {
                to: ['normal', 'degraded', 'critical'],
                requiresHealth: null,
                requiresPressure: null
            },

            degraded: {
                to: ['recovery', 'critical'],
                requiresHealth: 55,
                requiresPressure: 'high'
            },

            critical: {
                to: ['recovery'],
                requiresHealth: 30,
                requiresPressure: 'extreme'
            },

            recovery: {
                to: ['normal', 'elevated'],
                requiresHealth: 70,
                requiresPressure: 'low'
            }
        };

        /* =========================================
           SMART REDIRECTION (إعادة توجيه ذكية)
        ========================================= */

        this.smartRedirect = {

            enabled: true,
            alternatives: {
                'critical': ['degraded', 'recovery'],
                'degraded': ['elevated', 'normal'],
                'elevated': ['normal'],
                'recovery': ['normal']
            },
            redirectCount: 0
        };

        /* =========================================
           TRANSITION HISTORY
        ========================================= */

        this.transitions = [];

        this.maxTransitions =
            150;

        /* =========================================
           FEEDBACK LOOP (تحسين القواعد)
        ========================================= */

        this.feedbackLoop = {

            enabled: true,
            successRate: 100,
            adjustmentFactor: 0,
            lastAdjustment: null
        };

        /* =========================================
           PROACTIVE WARNING (تحذير استباقي)
        ========================================= */

        this.proactiveWarnings = {

            enabled: true,
            warnings: [],
            lastWarning: null
        };

        /* =========================================
           METRICS
        ========================================= */

        this.metrics = {

            successful: 0,
            blocked: 0,
            escalations: 0,
            recoveries: 0,
            redirected: 0,
            warningsIssued: 0,
            priorityOverrides: 0
        };

        console.log('🎛 Runtime Mode Manager Initialized (Sovereign Edition)');

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindGovernor();
        this.bindSystemState();
        this.bindOrchestrator();
        this.startFeedbackLoop();
        this.startProactiveMonitoring();
        this.publishReady();
    }

    /* ========================================================
       GOVERNOR (محسن)
    ======================================================== */

    bindGovernor() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:governor:decision', payload => {

            const mode = payload?.mode;
            if (!mode) return;

            this.requestTransition(mode, 'pressure-governor', payload);
        });
    }

    /* ========================================================
       SYSTEM STATE
    ======================================================== */

    bindSystemState() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('runtime:health:changed', payload => {

            const health = payload.health || 100;

            if (health <= 25 && this.currentMode !== 'critical') {
                this.requestTransition('critical', 'health-system', { health });
            } else if (health <= 55 && this.currentMode === 'normal') {
                this.requestTransition('degraded', 'health-system', { health });
            } else if (health >= 80 && (this.currentMode === 'degraded' || this.currentMode === 'critical')) {
                this.requestTransition('recovery', 'health-system', { health });
            }
        });
    }

    /* ========================================================
       ORCHESTRATOR
    ======================================================== */

    bindOrchestrator() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (!bus || typeof bus.subscribe !== 'function') return;

        bus.subscribe('orchestrator:mode:request', payload => {

            const mode = payload?.requestedMode;
            if (!mode) return;

            this.requestTransition(mode, 'orchestrator', payload);
        });
    }

    /* ========================================================
       PROACTIVE MONITORING (تحذير استباقي)
    ======================================================== */

    startProactiveMonitoring() {

        this._proactiveInterval = setInterval(() => {

            this.checkProactiveWarnings();

        }, 5000);
    }

    checkProactiveWarnings() {

        const system = window.SOVEREIGN_SYSTEM_STATE?.getStatus?.();
        if (!system) return;

        let warnings = [];

        // تحذير: اقتراب من critical بدون سبب كافٍ
        if (system.health > 50 && system.pressure !== 'extreme' &&
            (this.currentMode !== 'critical' && this.currentMode !== 'degraded')) {

            // لا تحذير، كل شيء طبيعي
        }

        // تحذير: تردد عالي في تغيير الـ modes
        const recentTransitions = this.transitions.slice(-10);
        if (recentTransitions.length >= 8) {

            warnings.push({
                type: 'high_transition_frequency',
                severity: 'warning',
                message: `High mode transition frequency: ${recentTransitions.length} in last ${recentTransitions[0]?.timestamp ? Date.now() - recentTransitions[0].timestamp : 'N/A'}ms`,
                timestamp: Date.now()
            });
        }

        // تحذير: وضع degraded لفترة طويلة
        if (this.currentMode === 'degraded') {

            const degradedTransitions = this.transitions.filter(
                t => t.to === 'degraded' && t.from !== 'degraded'
            );

            if (degradedTransitions.length > 0) {

                const lastDegraded = degradedTransitions[degradedTransitions.length - 1];
                const degradedDuration = Date.now() - lastDegraded.timestamp;

                if (degradedDuration > 30000) { // 30 ثانية

                    warnings.push({
                        type: 'prolonged_degradation',
                        severity: 'info',
                        message: `Prolonged degraded mode: ${Math.round(degradedDuration / 1000)}s`,
                        timestamp: Date.now()
                    });
                }
            }
        }

        if (warnings.length > 0) {

            this.proactiveWarnings.warnings = warnings.slice(-20);
            this.proactiveWarnings.lastWarning = warnings[0];
            this.metrics.warningsIssued += warnings.length;

            // نشر التحذيرات
            const bus = window.SOVEREIGN_ACCESS?.bus?.();
            if (bus && typeof bus.publishWithoutMiddleware === 'function') {

                bus.publishWithoutMiddleware('runtime:mode:warnings', {
                    warnings,
                    currentMode: this.currentMode,
                    timestamp: Date.now()
                });
            }
        }
    }

    /* ========================================================
       FEEDBACK LOOP (حلقة تحسين ذاتية)
    ======================================================== */

    startFeedbackLoop() {

        if (!this.feedbackLoop.enabled) return;

        this._feedbackInterval = setInterval(() => {

            this.updateFeedbackMetrics();

        }, 60000); // كل دقيقة
    }

    updateFeedbackMetrics() {

        const totalAttempts = this.metrics.successful + this.metrics.blocked + this.metrics.redirected;
        if (totalAttempts === 0) return;

        const successRate = (this.metrics.successful / totalAttempts) * 100;
        this.feedbackLoop.successRate = successRate;

        // إذا انخفضت نسبة النجاح، نعدل قواعد الانتقال
        if (successRate < 70 && this.feedbackLoop.adjustmentFactor > -20) {

            this.feedbackLoop.adjustmentFactor -= 5;
            this.feedbackLoop.lastAdjustment = Date.now();

            console.warn(`🎛 Mode Manager: Adjusting transition rules (success rate: ${successRate.toFixed(1)}%)`);

        } else if (successRate > 90 && this.feedbackLoop.adjustmentFactor < 20) {

            this.feedbackLoop.adjustmentFactor += 2;
            this.feedbackLoop.lastAdjustment = Date.now();
        }
    }

    /* ========================================================
       REQUEST (محسن مع الأولويات)
    ======================================================== */

    requestTransition(targetMode, source = 'runtime', metadata = {}) {

        // التحقق من القفل
        if (this.transitionLocked) {
            this.metrics.blocked++;
            this.publishBlocked(targetMode, source, 'transition_locked');
            return false;
        }

        // التحقق من الوضع الحالي
        if (this.currentMode === targetMode) {
            return true;
        }

        // التحقق من صحة الانتقال
        if (!this.canTransition(targetMode, metadata)) {

            // محاولة إعادة التوجيه الذكي
            if (this.smartRedirect.enabled) {
                const redirected = this.attemptSmartRedirect(targetMode, source, metadata);
                if (redirected) return true;
            }

            this.metrics.blocked++;
            this.publishBlocked(targetMode, source, 'invalid_transition');
            return false;
        }

        // التحقق من الأولوية (المصدر ذو الأولوية الأعلى يمكنه تجاوز)
        const sourcePriority = this.sourcePriority[source] || 40;
        const currentSource = this.getLastTransitionSource();

        if (currentSource && sourcePriority < this.sourcePriority[currentSource] - 20) {

            // مصدر ذو أولوية أقل يحاول التغيير بعد مصدر أعلى بفترة قصيرة
            const lastTransitionTime = this.transitions[this.transitions.length - 1]?.timestamp || 0;
            if (Date.now() - lastTransitionTime < 2000) {

                this.metrics.blocked++;
                this.metrics.priorityOverrides++;
                return false;
            }
        }

        return this.applyTransition(targetMode, source, metadata);
    }

    getLastTransitionSource() {

        if (this.transitions.length === 0) return null;
        return this.transitions[this.transitions.length - 1].source || null;
    }

    /* ========================================================
       SMART REDIRECTION (إعادة توجيه ذكية)
    ======================================================== */

    attemptSmartRedirect(targetMode, source, metadata) {

        const alternatives = this.smartRedirect.alternatives[targetMode];
        if (!alternatives || alternatives.length === 0) return false;

        for (const altMode of alternatives) {

            if (this.canTransition(altMode, metadata)) {

                console.log(`🎛 Mode Manager: Redirecting ${targetMode} → ${altMode} (smart redirect)`);

                this.smartRedirect.redirectCount++;
                this.metrics.redirected++;

                return this.applyTransition(altMode, `${source}_redirected`, metadata);
            }
        }

        return false;
    }

    /* ========================================================
       VALIDATION (محسن مع متطلبات الصحة والضغط)
    ======================================================== */

    canTransition(targetMode, metadata = {}) {

        const rules = this.allowedTransitions[this.currentMode];
        if (!rules) return false;

        if (!rules.to.includes(targetMode)) return false;

        // التحقق من متطلبات الصحة
        if (rules.requiresHealth !== null) {

            const currentHealth = metadata.health || window.SOVEREIGN_SYSTEM_STATE?.getStatus?.()?.health || 100;

            if (targetMode === 'degraded' && currentHealth > rules.requiresHealth) {
                // الصحة لا تزال جيدة، لا داعي للتدهور
                return false;
            }

            if (targetMode === 'recovery' && currentHealth < rules.requiresHealth) {
                // الصحة لم تتعافَ بما يكفي
                return false;
            }
        }

        // التحقق من متطلبات الضغط
        if (rules.requiresPressure !== null) {

            const currentPressure = metadata.pressure || window.SOVEREIGN_SYSTEM_STATE?.getStatus?.()?.pressure || 'low';

            const pressurePriority = { low: 0, moderate: 1, high: 2, extreme: 3 };
            const requiredPriority = pressurePriority[rules.requiresPressure] || 0;
            const currentPriority = pressurePriority[currentPressure] || 0;

            if (targetMode === 'critical' && currentPriority < requiredPriority) {
                return false;
            }
        }

        // تطبيق عامل التعديل من حلقة التغذية الراجعة
        if (this.feedbackLoop.adjustmentFactor !== 0 && targetMode === 'critical') {

            // إذا كنا نعدل القواعد، نسمح بانتقالات أسهل قليلاً إلى critical
            if (this.feedbackLoop.adjustmentFactor < -10) {
                // تخفيف القيود
                return true;
            }
        }

        return true;
    }

    /* ========================================================
       APPLY (محسن)
    ======================================================== */

    applyTransition(targetMode, source, metadata = {}) {

        this.lockTransitions();

        this.previousMode = this.currentMode;
        this.currentMode = targetMode;

        this.metrics.successful++;

        // تسجيل التصعيد
        if (targetMode === 'critical' || targetMode === 'degraded') {
            this.metrics.escalations++;
        }

        // تسجيل التعافي
        if (targetMode === 'recovery') {
            this.metrics.recoveries++;
        }

        this.recordTransition({
            from: this.previousMode,
            to: targetMode,
            source,
            metadata
        });

        this.syncSystemState();
        this.syncBodyState();
        this.publishTransition();

        // إلغاء تطبيق السياسات السلوكية هنا (pressure-governor هو المسؤول)
        // Mode Manager فقط يدير الانتقالات ولا يطبق سياسات

        setTimeout(() => {
            this.unlockTransitions();
        }, 800);

        console.log(`🎛 Runtime Mode Transition | FROM: ${this.previousMode} → TO: ${targetMode} | SOURCE: ${source}`);

        return true;
    }

    /* ========================================================
       LOCK / UNLOCK
    ======================================================== */

    lockTransitions() {
        this.transitionLocked = true;
    }

    unlockTransitions() {
        this.transitionLocked = false;
    }

    /* ========================================================
       SYSTEM STATE (محسن)
    ======================================================== */

    syncSystemState() {

        const system = window.SOVEREIGN_SYSTEM_STATE;
        if (system && typeof system.setMode === 'function') {
            system.setMode(this.currentMode, 'mode-manager');
        }
    }

    /* ========================================================
       BODY (محسن)
    ======================================================== */

    syncBodyState() {

        if (typeof document === 'undefined') return;

        document.body.dataset.runtimeMode = this.currentMode;
        document.body.dataset.modeSource = this.getLastTransitionSource() || 'unknown';
    }

    /* ========================================================
       TRANSITIONS
    ======================================================== */

    recordTransition(entry = {}) {

        this.transitions.push({
            ...entry,
            timestamp: Date.now()
        });

        if (this.transitions.length > this.maxTransitions) {
            this.transitions.shift();
        }
    }

    /* ========================================================
       PUBLISH (محسن)
    ======================================================== */

    publishTransition() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:mode:transition', {
                previous: this.previousMode,
                current: this.currentMode,
                metrics: this.metrics,
                timestamp: Date.now()
            });
        }
    }

    publishBlocked(targetMode, source, reason) {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime:mode:blocked', {
                requested: targetMode,
                current: this.currentMode,
                source,
                reason,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus = window.SOVEREIGN_ACCESS?.bus?.();

        if (bus && typeof bus.publishWithoutMiddleware === 'function') {

            bus.publishWithoutMiddleware('runtime-mode-manager:ready', {
                mode: this.currentMode,
                allowedTransitions: this.allowedTransitions,
                smartRedirect: this.smartRedirect.enabled,
                timestamp: Date.now()
            });
        }
    }

    /* ========================================================
       STATUS (محسن)
    ======================================================== */

    getStatus() {

        return {
            current: this.currentMode,
            previous: this.previousMode,
            locked: this.transitionLocked,
            transitions: this.transitions.length,
            metrics: { ...this.metrics },
            smartRedirect: {
                enabled: this.smartRedirect.enabled,
                count: this.smartRedirect.redirectCount
            },
            feedbackLoop: {
                enabled: this.feedbackLoop.enabled,
                successRate: this.feedbackLoop.successRate,
                adjustmentFactor: this.feedbackLoop.adjustmentFactor
            },
            proactiveWarnings: {
                enabled: this.proactiveWarnings.enabled,
                count: this.proactiveWarnings.warnings.length,
                lastWarning: this.proactiveWarnings.lastWarning
            }
        };
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    destroy() {

        if (this._proactiveInterval) {
            clearInterval(this._proactiveInterval);
            this._proactiveInterval = null;
        }

        if (this._feedbackInterval) {
            clearInterval(this._feedbackInterval);
            this._feedbackInterval = null;
        }

        console.log('🎛 Runtime Mode Manager Destroyed');
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignRuntimeModeManager =
    new SovereignRuntimeModeManager();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_MODE_MANAGER =
    sovereignRuntimeModeManager;

/* =========================================
   Unified Registry
========================================= */

if (window.SOVEREIGN && typeof window.SOVEREIGN.register === 'function') {

    window.SOVEREIGN.register('mode-manager', sovereignRuntimeModeManager);
}
