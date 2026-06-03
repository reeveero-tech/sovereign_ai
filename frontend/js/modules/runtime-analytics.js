/* ============================================================
   Sovereign AI — runtime-analytics.js
   الإصدار: 7.0.0
   طبقة التحليلات السيادية
   ============================================================ */

class SovereignRuntimeAnalytics {

    constructor() {

        this.records = [];

        this.maxRecords = 500;

        console.log(
            '📈 Runtime Analytics Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.startAnalytics();

        this.bindSignals();
    }

    /* ========================================================
       START
    ======================================================== */

    startAnalytics() {

        const scheduler =
            window.SOVEREIGN_SCHEDULER;

        if (!scheduler) {

            console.warn(
                'Scheduler Missing'
            );

            return;
        }

        scheduler.registerTask(

            'runtime-analytics',

            () => {

                this.captureAnalytics();

            },

            6000
        );
    }

    /* ========================================================
       CAPTURE
    ======================================================== */

    captureAnalytics() {

        const metrics =
            window.SOVEREIGN_METRICS
                ?.getMetrics();

        const kernel =
            window.SOVEREIGN_KERNEL
                ?.getStatus();

        const intelligence =
            window.SOVEREIGN_INTELLIGENCE
                ?.getStatus();

        const power =
            window.SOVEREIGN_POWER
                ?.getStatus();

        const snapshot = {

            timestamp:
                Date.now(),

            fps:
                metrics?.fps || 0,

            cycles:
                metrics?.cycles || 0,

            health:
                kernel?.health || 0,

            runtimeState:
                kernel?.state || 'unknown',

            intelligence:
                intelligence?.state || 'unknown',

            powerMode:
                power?.mode || 'balanced'
        };

        this.records.push(
            snapshot
        );

        if (
            this.records.length >
            this.maxRecords
        ) {

            this.records.shift();
        }

        this.cacheAnalytics(
            snapshot
        );
    }

    /* ========================================================
       CACHE
    ======================================================== */

    cacheAnalytics(snapshot) {

        window.SOVEREIGN_CACHE
            ?.set(
                `analytics-${snapshot.timestamp}`,
                snapshot,
                300000
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
            'runtime:intelligence_changed',
            ({ current }) => {

                console.log(
                    `📊 Intelligence Shift: ${current}`
                );
            }
        );

        events.on(
            'kernel:degraded',
            () => {

                this.captureAnalytics();
            }
        );
    }

    /* ========================================================
       REPORT
    ======================================================== */

    generateReport() {

        if (
            !this.records.length
        ) {

            return null;
        }

        const latest =
            this.records[
                this.records.length - 1
            ];

        const averageFPS =
            (
                this.records.reduce(
                    (sum, item) =>
                        sum + item.fps,
                    0
                ) /
                this.records.length
            ).toFixed(2);

        return {

            records:
                this.records.length,

            averageFPS,

            latest
        };
    }

    /* ========================================================
       EXPORT
    ======================================================== */

    exportAnalytics() {

        const blob =
            new Blob(
                [
                    JSON.stringify(
                        this.records,
                        null,
                        2
                    )
                ],
                {
                    type:
                        'application/json'
                }
            );

        const url =
            URL.createObjectURL(blob);

        const link =
            document.createElement('a');

        link.href = url;

        link.download =
            'sovereign-runtime-analytics.json';

        link.click();

        URL.revokeObjectURL(url);

        window.SOVEREIGN_NOTIFY
            ?.success(
                'Analytics Exported'
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            records:
                this.records.length,

            maxRecords:
                this.maxRecords
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_ANALYTICS =
    new SovereignRuntimeAnalytics();
