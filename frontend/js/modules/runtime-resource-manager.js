/* ============================================================
   Sovereign AI — runtime-resource-manager.js
   الإصدار: 7.0.0
   مدير الموارد السيادي
   ============================================================ */

class SovereignRuntimeResourceManager {

    constructor() {

        this.resourceState = 'balanced';

        this.memoryPressure = 0;

        this.effectLevel = 'high';

        console.log(
            '📦 Runtime Resource Manager Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.startMonitoring();

        this.bindSignals();
    }

    /* ========================================================
       MONITORING
    ======================================================== */

    startMonitoring() {

        const scheduler =
            window.SOVEREIGN_SCHEDULER;

        if (!scheduler) {

            console.warn(
                'Scheduler Missing'
            );

            return;
        }

        scheduler.registerTask(

            'runtime-resource-monitor',

            () => {

                this.evaluateResources();

            },

            5000
        );
    }

    /* ========================================================
       EVALUATE
    ======================================================== */

    evaluateResources() {

        const cache =
            window.SOVEREIGN_CACHE
                ?.getStats();

        const analytics =
            window.SOVEREIGN_ANALYTICS
                ?.getStatus();

        const kernel =
            window.SOVEREIGN_KERNEL
                ?.getStatus();

        if (
            !cache ||
            !kernel
        ) return;

        let pressure = 0;

        /* =========================================
           CACHE PRESSURE
        ========================================= */

        if (
            cache.entries >
            150
        ) {

            pressure += 20;
        }

        /* =========================================
           HEALTH
        ========================================= */

        if (
            kernel.health < 70
        ) {

            pressure += 30;
        }

        /* =========================================
           ANALYTICS LOAD
        ========================================= */

        if (
            analytics?.records > 300
        ) {

            pressure += 15;
        }

        this.memoryPressure =
            pressure;

        this.applyResourceStrategy();
    }

    /* ========================================================
       STRATEGY
    ======================================================== */

    applyResourceStrategy() {

        /* =========================================
           HIGH PRESSURE
        ========================================= */

        if (
            this.memoryPressure >= 40
        ) {

            this.resourceState =
                'constrained';

            this.effectLevel =
                'low';

            document.body.classList.add(
                'runtime-low-effects'
            );

            window.SOVEREIGN_NOTIFY
                ?.warning(
                    'Runtime Resource Protection Enabled'
                );

            return;
        }

        /* =========================================
           NORMAL
        ========================================= */

        this.resourceState =
            'balanced';

        this.effectLevel =
            'high';

        document.body.classList.remove(
            'runtime-low-effects'
        );
    }

    /* ========================================================
       SIGNALS
    ======================================================== */

    bindSignals() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        events.on(
            'performance:critical',
            () => {

                this.memoryPressure += 10;

                this.applyResourceStrategy();
            }
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            state:
                this.resourceState,

            pressure:
                this.memoryPressure,

            effects:
                this.effectLevel
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_RESOURCES =
    new SovereignRuntimeResourceManager();
