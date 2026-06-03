/* ============================================================
   Sovereign AI — runtime-diagnostics.js
   الإصدار: 7.0.0
   نظام التشخيص السيادي
   ============================================================ */

class SovereignRuntimeDiagnostics {

    constructor() {

        this.snapshots = [];

        this.maxSnapshots = 50;

        console.log(
            '🩺 Runtime Diagnostics Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.startDiagnostics();

        this.bindSignals();
    }

    /* ========================================================
       START
    ======================================================== */

    startDiagnostics() {

        const scheduler =
            window.SOVEREIGN_SCHEDULER;

        if (!scheduler) {

            console.warn(
                'Scheduler Missing'
            );

            return;
        }

        scheduler.registerTask(

            'runtime-diagnostics',

            () => {

                this.captureSnapshot();

            },

            5000
        );
    }

    /* ========================================================
       SNAPSHOT
    ======================================================== */

    captureSnapshot() {

        const snapshot = {

            timestamp:
                Date.now(),

            kernel:
                window.SOVEREIGN_KERNEL
                    ?.getStatus(),

            lifecycle:
                window.SOVEREIGN_LIFECYCLE
                    ?.getStatus(),

            power:
                window.SOVEREIGN_POWER
                    ?.getStatus(),

            metrics:
                window.SOVEREIGN_METRICS
                    ?.getMetrics(),

            recovery:
                window.SOVEREIGN_RECOVERY
                    ?.getStatus(),

            scheduler:
                window.SOVEREIGN_SCHEDULER
                    ?.getStatus()
        };

        this.snapshots.push(
            snapshot
        );

        if (
            this.snapshots.length >
            this.maxSnapshots
        ) {

            this.snapshots.shift();
        }

        console.log(
            '📸 Runtime Snapshot',
            snapshot
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
            'kernel:degraded',
            () => {

                this.captureSnapshot();
            }
        );

        events.on(
            'performance:critical',
            () => {

                this.captureSnapshot();
            }
        );
    }

    /* ========================================================
       REPORT
    ======================================================== */

    generateReport() {

        const latest =
            this.snapshots[
                this.snapshots.length - 1
            ];

        return {

            snapshots:
                this.snapshots.length,

            latest
        };
    }

    /* ========================================================
       EXPORT
    ======================================================== */

    exportDiagnostics() {

        const data = JSON.stringify(
            this.snapshots,
            null,
            2
        );

        const blob =
            new Blob(
                [data],
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
            'sovereign-runtime-diagnostics.json';

        link.click();

        URL.revokeObjectURL(url);

        window.SOVEREIGN_NOTIFY
            ?.success(
                'Diagnostics Exported'
            );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_DIAGNOSTICS =
    new SovereignRuntimeDiagnostics();
