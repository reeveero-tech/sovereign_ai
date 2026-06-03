/* ============================================================
   Sovereign AI — runtime-intelligence.js
   الإصدار: 7.0.0
   مدير الذكاء التشغيلي السيادي
   ============================================================ */

class SovereignRuntimeIntelligence {

    constructor() {

        this.state = 'optimal';

        this.analysisHistory = [];

        console.log(
            '🧠 Runtime Intelligence Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.startAnalysisLoop();

        this.bindSignals();
    }

    /* ========================================================
       ANALYSIS LOOP
    ======================================================== */

    startAnalysisLoop() {

        const scheduler =
            window.SOVEREIGN_SCHEDULER;

        if (!scheduler) {

            console.warn(
                'Scheduler Missing'
            );

            return;
        }

        scheduler.registerTask(

            'runtime-intelligence',

            () => {

                this.analyzeRuntime();

            },

            4000
        );
    }

    /* ========================================================
       ANALYZE
    ======================================================== */

    analyzeRuntime() {

        const metrics =
            window.SOVEREIGN_METRICS
                ?.getMetrics();

        const kernel =
            window.SOVEREIGN_KERNEL
                ?.getStatus();

        const power =
            window.SOVEREIGN_POWER
                ?.getStatus();

        const recovery =
            window.SOVEREIGN_RECOVERY
                ?.getStatus();

        if (
            !metrics ||
            !kernel
        ) return;

        let score = 100;

        /* =========================================
           FPS
        ========================================= */

        if (
            metrics.fps < 30
        ) {

            score -= 25;
        }

        /* =========================================
           HEALTH
        ========================================= */

        if (
            kernel.health < 70
        ) {

            score -= 20;
        }

        /* =========================================
           RECOVERY
        ========================================= */

        if (
            recovery?.attempts > 2
        ) {

            score -= 15;
        }

        /* =========================================
           POWER
        ========================================= */

        if (
            power?.mode === 'safe'
        ) {

            score -= 10;
        }

        this.evaluateState(score);

        this.storeAnalysis({
            score,
            metrics,
            kernel,
            power,
            recovery
        });
    }

    /* ========================================================
       EVALUATE
    ======================================================== */

    evaluateState(score) {

        let nextState =
            'optimal';

        if (
            score < 80
        ) {

            nextState =
                'stable';
        }

        if (
            score < 60
        ) {

            nextState =
                'stressed';
        }

        if (
            score < 40
        ) {

            nextState =
                'critical';
        }

        if (
            nextState !== this.state
        ) {

            this.transitionState(
                nextState
            );
        }
    }

    /* ========================================================
       TRANSITION
    ======================================================== */

    transitionState(state) {

        const previous =
            this.state;

        this.state =
            state;

        console.log(
            `
🧠 Runtime Intelligence
FROM: ${previous}
TO:   ${state}
            `
        );

        document.body.dataset.intelligence =
            state;

        window.SOVEREIGN_EVENTS
            ?.emit(
                'runtime:intelligence_changed',
                {
                    previous,
                    current: state
                }
            );

        this.applyAdaptiveLogic(state);
    }

    /* ========================================================
       ADAPTIVE LOGIC
    ======================================================== */

    applyAdaptiveLogic(state) {

        switch (state) {

            case 'critical':

                document.body.classList.add(
                    'runtime-safe'
                );

                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'Runtime Critical Mode'
                    );

                break;

            case 'stressed':

                document.body.classList.add(
                    'runtime-balanced'
                );

                break;

            case 'optimal':

                document.body.classList.remove(
                    'runtime-safe'
                );

                document.body.classList.remove(
                    'runtime-balanced'
                );

                break;
        }
    }

    /* ========================================================
       STORE
    ======================================================== */

    storeAnalysis(data) {

        this.analysisHistory.push({

            timestamp:
                Date.now(),

            ...data
        });

        if (
            this.analysisHistory.length >
            100
        ) {

            this.analysisHistory.shift();
        }
    }

    /* ========================================================
       SIGNALS
    ======================================================== */

    bindSignals() {

        window.SOVEREIGN_EVENTS
            ?.on(
                'performance:critical',
                () => {

                    this.transitionState(
                        'critical'
                    );
                }
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            state:
                this.state,

            history:
                this.analysisHistory.length
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_INTELLIGENCE =
    new SovereignRuntimeIntelligence();
