/* ============================================================
   Sovereign AI — runtime-adaptive-scheduler.js
   الإصدار: 8.0.0
   المجدول التكيفي السيادي
   ============================================================ */

class SovereignRuntimeAdaptiveScheduler {

    constructor() {

        this.mode =
            'normal';

        this.pressure =
            0;

        this.maxPressure =
            100;

        console.log(
            '🧠 Adaptive Runtime Scheduler Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.startMonitoring();

        this.publishReady();
    }

    /* ========================================================
       MONITOR
    ======================================================== */

    startMonitoring() {

        setInterval(() => {

            this.evaluateRuntime();

        }, 3000);
    }

    /* ========================================================
       EVALUATE
    ======================================================== */

    evaluateRuntime() {

        const scheduler =
            window.SOVEREIGN_ACCESS
                ?.legacy?.(
                    'execution_scheduler'
                )
            ||
            window.SOVEREIGN_EXECUTION_SCHEDULER;

        const analytics =
            window.SOVEREIGN_ACCESS
                ?.legacy?.(
                    'analytics'
                )
            ||
            window.SOVEREIGN_ANALYTICS;

        if (
            !scheduler
        ) {

            return;
        }

        const status =
            scheduler.getStatus?.();

        const queued =
            status?.queued || 0;

        const active =
            status?.active || 0;

        const avgExecution =
            status
                ?.telemetry
                ?.averageExecutionTimeMs
            || 0;

        /* =========================================
           PRESSURE SCORE
        ========================================= */

        let pressure = 0;

        pressure +=
            queued * 2;

        pressure +=
            active * 5;

        pressure +=
            avgExecution / 10;

        this.pressure =
            Math.min(
                pressure,
                this.maxPressure
            );

        this.evaluateMode();
    }

    /* ========================================================
       MODE
    ======================================================== */

    evaluateMode() {

        let next =
            'normal';

        if (
            this.pressure >
            30
        ) {

            next =
                'elevated';
        }

        if (
            this.pressure >
            60
        ) {

            next =
                'degraded';
        }

        if (
            this.pressure >
            85
        ) {

            next =
                'critical';
        }

        if (
            next !==
            this.mode
        ) {

            this.transition(
                next
            );
        }
    }

    /* ========================================================
       TRANSITION
    ======================================================== */

    transition(mode) {

        const previous =
            this.mode;

        this.mode =
            mode;

        console.warn(
            `
🧠 Runtime Scheduling Mode Changed

${previous}
→
${mode}
            `
        );

        this.applyAdaptation(
            mode
        );

        this.publishTransition(
            previous,
            mode
        );
    }

    /* ========================================================
       APPLY ADAPTATION
    ======================================================== */

    applyAdaptation(mode) {

        const scheduler =
            window.SOVEREIGN_ACCESS
                ?.legacy?.(
                    'execution_scheduler'
                )
            ||
            window.SOVEREIGN_EXECUTION_SCHEDULER;

        if (!scheduler) {

            return;
        }

        switch (mode) {

            case 'critical':

                scheduler.setMaxConcurrent?.(
                    2
                );

                break;

            case 'degraded':

                scheduler.setMaxConcurrent?.(
                    3
                );

                break;

            case 'elevated':

                scheduler.setMaxConcurrent?.(
                    4
                );

                break;

            case 'normal':

                scheduler.setMaxConcurrent?.(
                    5
                );

                break;
        }
    }

    /* ========================================================
       TRANSITION EVENT
    ======================================================== */

    publishTransition(
        previous,
        current
    ) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus
            ?.publishWithoutMiddleware?.(

                'scheduler:mode:changed',

                {

                    previous,

                    current,

                    pressure:
                        this.pressure,

                    timestamp:
                        Date.now()
                }
            );
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

                'adaptive-scheduler:ready',

                {

                    mode:
                        this.mode,

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

            mode:
                this.mode,

            pressure:
                this.pressure
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignAdaptiveScheduler =
    new SovereignRuntimeAdaptiveScheduler();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_ADAPTIVE_SCHEDULER =
    sovereignAdaptiveScheduler;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'adaptive-scheduler',
        sovereignAdaptiveScheduler
    );
