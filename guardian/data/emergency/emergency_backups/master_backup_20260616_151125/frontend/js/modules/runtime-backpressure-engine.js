/* ============================================================
   Sovereign AI — runtime-backpressure-engine.js
   الإصدار: 8.0.0
   محرك الضغط الخلفي السيادي
   ============================================================ */

class SovereignRuntimeBackpressureEngine {

    constructor() {

        this.active =
            false;

        this.level =
            0;

        this.maxLevel =
            100;

        this.pacingDelay =
            0;

        console.log(
            '🌊 Runtime Backpressure Engine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindAdaptiveScheduler();

        this.publishReady();
    }

    /* ========================================================
       BIND
    ======================================================== */

    bindAdaptiveScheduler() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (!bus) {

            return;
        }

        bus.subscribe(

            'runtime:backpressure:active',

            (message) => {

                this.activate(
                    message.payload
                );
            }
        );

        bus.subscribe(

            'runtime:backpressure:resolved',

            () => {

                this.resolve();
            }
        );
    }

    /* ========================================================
       ACTIVATE
    ======================================================== */

    activate(payload = {}) {

        this.active =
            true;

        this.level =
            payload.level || 0;

        this.calculatePacing();

        console.warn(
            `
🌊 Runtime Backpressure Activated

Level:
${this.level}
            `
        );

        this.applyPacing();
    }

    /* ========================================================
       RESOLVE
    ======================================================== */

    resolve() {

        this.active =
            false;

        this.level =
            0;

        this.pacingDelay =
            0;

        console.log(
            '✅ Runtime Backpressure Resolved'
        );

        this.publishResolved();
    }

    /* ========================================================
       CALCULATE PACING
    ======================================================== */

    calculatePacing() {

        if (
            this.level >
            80
        ) {

            this.pacingDelay =
                500;
        }

        else if (
            this.level >
            60
        ) {

            this.pacingDelay =
                250;
        }

        else if (
            this.level >
            30
        ) {

            this.pacingDelay =
                100;
        }

        else {

            this.pacingDelay =
                0;
        }
    }

    /* ========================================================
       APPLY PACING
    ======================================================== */

    applyPacing() {

        const scheduler =
            window.SOVEREIGN_ACCESS
                ?.legacy?.(
                    'execution_scheduler'
                )
            ||
            window.SOVEREIGN_EXECUTION_SCHEDULER;

        if (
            !scheduler
        ) {

            return;
        }

        scheduler.executionDelay =
            this.pacingDelay;

        this.publishApplied();
    }

    /* ========================================================
       APPLIED
    ======================================================== */

    publishApplied() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus
            ?.publishWithoutMiddleware?.(

                'backpressure:applied',

                {

                    level:
                        this.level,

                    pacingDelay:
                        this.pacingDelay,

                    timestamp:
                        Date.now()
                }
            );
    }

    /* ========================================================
       RESOLVED
    ======================================================== */

    publishResolved() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus
            ?.publishWithoutMiddleware?.(

                'backpressure:resolved',

                {

                    timestamp:
                        Date.now()
                }
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            active:
                this.active,

            level:
                this.level,

            pacingDelay:
                this.pacingDelay
        };
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus
            ?.publishWithoutMiddleware?.(

                'backpressure:ready',

                {

                    timestamp:
                        Date.now()
                }
            );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignBackpressure =
    new SovereignRuntimeBackpressureEngine();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_BACKPRESSURE =
    sovereignBackpressure;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'backpressure-engine',
        sovereignBackpressure
    );
