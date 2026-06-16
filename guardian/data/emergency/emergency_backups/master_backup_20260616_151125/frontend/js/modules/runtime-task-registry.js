/* ============================================================
   Sovereign AI — runtime-task-registry.js
   الإصدار: 7.0.0
   سجل المهام السيادي
   ============================================================ */

class SovereignRuntimeTaskRegistry {

    constructor() {

        this.scheduler =
            window.SOVEREIGN_SCHEDULER;

        console.log(
            '📚 Runtime Task Registry Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        if (!this.scheduler) {

            console.error(
                'Scheduler Missing'
            );

            return;
        }

        this.registerCoreTasks();

        this.registerRuntimeTasks();

        this.registerMonitoringTasks();
    }

    /* ========================================================
       CORE TASKS
    ======================================================== */

    registerCoreTasks() {

        /* =========================================
           Runtime Health
        ========================================= */

        this.scheduler.registerTask(

            'runtime-health',

            () => {

                const kernel =
                    window.SOVEREIGN_KERNEL;

                if (!kernel) return;

                const status =
                    kernel.getStatus();

                if (
                    status.health < 50
                ) {

                    window.SOVEREIGN_NOTIFY
                        ?.warning(
                            'Runtime Health Low'
                        );
                }

            },

            5000
        );

        /* =========================================
           FPS Monitor
        ========================================= */

        this.scheduler.registerTask(

            'fps-monitor',

            () => {

                const fps =
                    window.SOVEREIGN_ANIMATION_ENGINE
                        ?.fps || 60;

                if (fps < 25) {

                    window.SOVEREIGN_EVENTS
                        ?.emit(
                            'performance:critical',
                            { fps }
                        );
                }

            },

            3000
        );
    }

    /* ========================================================
       RUNTIME TASKS
    ======================================================== */

    registerRuntimeTasks() {

        /* =========================================
           State Sync
        ========================================= */

        this.scheduler.registerTask(

            'state-sync',

            () => {

                const metrics =
                    window.SOVEREIGN_METRICS
                        ?.getMetrics();

                if (!metrics) return;

                window.SOVEREIGN_STATE
                    ?.mergeState(
                        'metrics',
                        metrics
                    );

            },

            1500
        );

        /* =========================================
           Scene Sync
        ========================================= */

        this.scheduler.registerTask(

            'scene-sync',

            () => {

                document.body.dataset.runtimeTime =
                    Date.now();

            },

            2000
        );
    }

    /* ========================================================
       MONITORING
    ======================================================== */

    registerMonitoringTasks() {

        /* =========================================
           Memory Monitor
        ========================================= */

        this.scheduler.registerTask(

            'memory-monitor',

            () => {

                const memory =
                    window.SOVEREIGN_MEMORY
                        ?.getStats();

                console.log(
                    '🧠 Memory Monitor',
                    memory
                );

            },

            10000
        );

        /* =========================================
           Socket Monitor
        ========================================= */

        this.scheduler.registerTask(

            'socket-monitor',

            () => {

                const socket =
                    window.SOVEREIGN_SOCKET;

                if (
                    !socket?.connected
                ) {

                    console.warn(
                        '⚠️ Socket Offline'
                    );
                }

            },

            7000
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getTasks() {

        return this.scheduler
            ?.getStatus();
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_TASKS =
    new SovereignRuntimeTaskRegistry();
