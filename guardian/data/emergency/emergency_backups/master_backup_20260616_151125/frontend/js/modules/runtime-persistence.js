/* ============================================================
   Sovereign AI — runtime-persistence.js
   الإصدار: 7.0.0
   طبقة الاستمرارية السيادية
   ============================================================ */

class SovereignRuntimePersistence {

    constructor() {

        this.storageKey =
            'sovereign-runtime-state';

        console.log(
            '💾 Runtime Persistence Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.restoreRuntime();

        this.bindPersistenceCycle();

        this.bindUnloadProtection();
    }

    /* ========================================================
       SAVE
    ======================================================== */

    saveRuntime() {

        try {

            const snapshot = {

                timestamp:
                    Date.now(),

                lifecycle:
                    window.SOVEREIGN_LIFECYCLE
                        ?.getStatus(),

                power:
                    window.SOVEREIGN_POWER
                        ?.getStatus(),

                intelligence:
                    window.SOVEREIGN_INTELLIGENCE
                        ?.getStatus(),

                metrics:
                    window.SOVEREIGN_METRICS
                        ?.getMetrics(),

                memory:
                    window.SOVEREIGN_MEMORY
                        ?.getStats(),

                cache:
                    window.SOVEREIGN_CACHE
                        ?.getStats()
            };

            localStorage.setItem(

                this.storageKey,

                JSON.stringify(snapshot)
            );

            console.log(
                '💾 Runtime State Saved'
            );

        } catch (error) {

            console.error(
                'Persistence Save Failed',
                error
            );
        }
    }

    /* ========================================================
       RESTORE
    ======================================================== */

    restoreRuntime() {

        try {

            const raw =
                localStorage.getItem(
                    this.storageKey
                );

            if (!raw) return;

            const snapshot =
                JSON.parse(raw);

            console.log(
                '♻️ Runtime State Restored',
                snapshot
            );

            document.body.dataset.restored =
                'true';

            window.SOVEREIGN_NOTIFY
                ?.success(
                    'Runtime Session Restored'
                );

        } catch (error) {

            console.error(
                'Runtime Restore Failed',
                error
            );
        }
    }

    /* ========================================================
       PERSISTENCE CYCLE
    ======================================================== */

    bindPersistenceCycle() {

        const scheduler =
            window.SOVEREIGN_SCHEDULER;

        if (!scheduler) return;

        scheduler.registerTask(

            'runtime-persistence',

            () => {

                this.saveRuntime();

            },

            15000
        );
    }

    /* ========================================================
       UNLOAD
    ======================================================== */

    bindUnloadProtection() {

        window.addEventListener(
            'beforeunload',
            () => {

                this.saveRuntime();
            }
        );
    }

    /* ========================================================
       CLEAR
    ======================================================== */

    clearPersistence() {

        localStorage.removeItem(
            this.storageKey
        );

        console.log(
            '🧹 Runtime Persistence Cleared'
        );

        window.SOVEREIGN_NOTIFY
            ?.info(
                'Runtime Persistence Cleared'
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            storageKey:
                this.storageKey,

            persisted:
                !!localStorage.getItem(
                    this.storageKey
                )
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_PERSISTENCE =
    new SovereignRuntimePersistence();
