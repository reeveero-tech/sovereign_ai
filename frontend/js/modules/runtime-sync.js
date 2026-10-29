/* ============================================================
   Sovereign AI — runtime-sync.js
   الإصدار: 6.0.0
   مزامنة النظام
   ============================================================ */

class SovereignRuntimeSync {

    constructor() {

        console.log(
            '🔄 Runtime Sync Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.syncMetrics();

        this.syncConnection();

        this.syncScenes();

        this.syncMemory();
    }

    /* ========================================================
       METRICS
    ======================================================== */

    syncMetrics() {

        setInterval(() => {

            const metrics =
                window.SOVEREIGN_METRICS
                    ?.getMetrics();

            if (!metrics) return;

            window.SOVEREIGN_STATE
                ?.mergeState(
                    'metrics',
                    metrics
                );

        }, 1000);
    }

    /* ========================================================
       CONNECTION
    ======================================================== */

    syncConnection() {

        const socket =
            window.SOVEREIGN_SOCKET;

        if (!socket) return;

        setInterval(() => {

            window.SOVEREIGN_STATE
                ?.mergeState(
                    'system',
                    {
                        connected:
                            socket.connected,

                        latency:
                            socket.latency
                    }
                );

        }, 1500);
    }

    /* ========================================================
       SCENES
    ======================================================== */

    syncScenes() {

        window.SOVEREIGN_EVENTS
            ?.on(
                'ui:tab_changed',
                ({ tab }) => {

                    document.body.dataset.activeTab =
                        tab;
                }
            );
    }

    /* ========================================================
       MEMORY
    ======================================================== */

    syncMemory() {

        setInterval(() => {

            const stats =
                window.SOVEREIGN_MEMORY
                    ?.getStats();

            if (!stats) return;

            console.log(
                '🧠 Memory Stats',
                stats
            );

        }, 10000);
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_SYNC =
    new SovereignRuntimeSync();
