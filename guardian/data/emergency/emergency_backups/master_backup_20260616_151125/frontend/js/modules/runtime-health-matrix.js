/* ============================================================
   Sovereign AI — runtime-health-matrix.js
   الإصدار: 7.0.0
   مصفوفة الصحة السيادية
   ============================================================ */

class SovereignRuntimeHealthMatrix {

    constructor() {

        this.matrix = new Map();

        this.globalHealth = 100;

        console.log(
            '❤️ Runtime Health Matrix Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerSubsystems();

        this.startMonitoring();
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    registerSubsystems() {

        this.register(
            'kernel'
        );

        this.register(
            'scheduler'
        );

        this.register(
            'security'
        );

        this.register(
            'analytics'
        );

        this.register(
            'intelligence'
        );

        this.register(
            'orchestrator'
        );

        this.register(
            'replication'
        );

        this.register(
            'resources'
        );
    }

    /* ========================================================
       REGISTER NODE
    ======================================================== */

    register(name) {

        this.matrix.set(name, {

            health: 100,

            lastUpdate:
                Date.now(),

            state: 'stable'
        });
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

            'runtime-health-matrix',

            () => {

                this.evaluateHealth();

            },

            4000
        );
    }

    /* ========================================================
       EVALUATE
    ======================================================== */

    evaluateHealth() {

        this.evaluateKernel();

        this.evaluateResources();

        this.evaluateRecovery();

        this.calculateGlobalHealth();

        this.publishHealthState();
    }

    /* ========================================================
       KERNEL
    ======================================================== */

    evaluateKernel() {

        const kernel =
            window.SOVEREIGN_KERNEL
                ?.getStatus();

        if (!kernel) return;

        this.updateHealth(

            'kernel',

            kernel.health
        );
    }

    /* ========================================================
       RESOURCES
    ======================================================== */

    evaluateResources() {

        const resources =
            window.SOVEREIGN_RESOURCES
                ?.getStatus();

        if (!resources) return;

        let health = 100;

        if (
            resources.pressure > 40
        ) {

            health -= 30;
        }

        this.updateHealth(
            'resources',
            health
        );
    }

    /* ========================================================
       RECOVERY
    ======================================================== */

    evaluateRecovery() {

        const recovery =
            window.SOVEREIGN_RECOVERY
                ?.getStatus();

        if (!recovery) return;

        let health = 100;

        if (
            recovery.attempts > 2
        ) {

            health -= 40;
        }

        this.updateHealth(
            'replication',
            health
        );
    }

    /* ========================================================
       UPDATE
    ======================================================== */

    updateHealth(
        subsystem,
        value
    ) {

        const node =
            this.matrix.get(subsystem);

        if (!node) return;

        node.health =
            value;

        node.lastUpdate =
            Date.now();

        node.state =
            value < 50
                ? 'critical'
                : value < 75
                    ? 'degraded'
                    : 'stable';
    }

    /* ========================================================
       GLOBAL
    ======================================================== */

    calculateGlobalHealth() {

        const values =
            [...this.matrix.values()]
                .map(
                    node => node.health
                );

        this.globalHealth =
            Math.round(

                values.reduce(
                    (a, b) => a + b,
                    0
                ) / values.length
            );

        document.body.dataset.globalHealth =
            this.globalHealth;
    }

    /* ========================================================
       PUBLISH
    ======================================================== */

    publishHealthState() {

        window.SOVEREIGN_BUS
            ?.publish(
                'system',
                {
                    type:
                        'health-update',

                    globalHealth:
                        this.globalHealth
                }
            );
    }

    /* ========================================================
       GET
    ======================================================== */

    getSubsystem(name) {

        return this.matrix.get(name);
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            globalHealth:
                this.globalHealth,

            subsystems:
                [...this.matrix.entries()]
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_HEALTH =
    new SovereignRuntimeHealthMatrix();
