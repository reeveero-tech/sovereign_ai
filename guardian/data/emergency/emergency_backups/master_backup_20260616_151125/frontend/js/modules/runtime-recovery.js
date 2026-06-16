/* ============================================================
   Sovereign AI — runtime-recovery.js
   الإصدار: 7.0.0
   نظام الاستعادة السيادي
   ============================================================ */

class SovereignRuntimeRecovery {

    constructor() {

        this.recoveryAttempts = 0;

        this.maxRecoveryAttempts = 5;

        this.lastHealthyState =
            Date.now();

        console.log(
            '🛡 Runtime Recovery Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.monitorHealth();

        this.bindCriticalSignals();

        this.bindGlobalErrors();
    }

    /* ========================================================
       HEALTH MONITOR
    ======================================================== */

    monitorHealth() {

        setInterval(() => {

            const kernel =
                window.SOVEREIGN_KERNEL;

            if (!kernel) return;

            const status =
                kernel.getStatus();

            if (
                status.health <= 40
            ) {

                this.triggerRecovery(
                    'low-health'
                );

            } else {

                this.lastHealthyState =
                    Date.now();
            }

        }, 5000);
    }

    /* ========================================================
       SIGNALS
    ======================================================== */

    bindCriticalSignals() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        events.on(
            'performance:critical',
            () => {

                this.triggerRecovery(
                    'performance'
                );
            }
        );

        events.on(
            'socket:disconnected',
            () => {

                this.triggerRecovery(
                    'socket'
                );
            }
        );
    }

    /* ========================================================
       GLOBAL ERRORS
    ======================================================== */

    bindGlobalErrors() {

        window.addEventListener(
            'error',
            (event) => {

                console.error(
                    '🚨 Global Error',
                    event.error
                );

                this.triggerRecovery(
                    'runtime-error'
                );
            }
        );

        window.addEventListener(
            'unhandledrejection',
            (event) => {

                console.error(
                    '🚨 Promise Rejection',
                    event.reason
                );

                this.triggerRecovery(
                    'promise-rejection'
                );
            }
        );
    }

    /* ========================================================
       RECOVERY
    ======================================================== */

    triggerRecovery(reason) {

        if (
            this.recoveryAttempts >=
            this.maxRecoveryAttempts
        ) {

            console.error(
                '❌ Recovery Limit Reached'
            );

            window.SOVEREIGN_NOTIFY
                ?.error(
                    'Runtime Recovery Failed'
                );

            return;
        }

        this.recoveryAttempts++;

        console.warn(
            `
🛠 Runtime Recovery
Reason: ${reason}
Attempt: ${this.recoveryAttempts}
            `
        );

        this.applyRecoveryProtocol(
            reason
        );
    }

    /* ========================================================
       RECOVERY PROTOCOL
    ======================================================== */

    applyRecoveryProtocol(reason) {

        document.body.classList.add(
            'runtime-recovery'
        );

        /* =========================================
           Reduce FX
        ========================================= */

        document.body.classList.add(
            'runtime-safe'
        );

        /* =========================================
           Notifications
        ========================================= */

        window.SOVEREIGN_NOTIFY
            ?.warning(
                `Runtime Recovery: ${reason}`
            );

        /* =========================================
           Restart Socket
        ========================================= */

        if (
            reason === 'socket'
        ) {

            try {

                window.SOVEREIGN_SOCKET
                    ?.connect();

            } catch (error) {

                console.error(
                    'Socket Recovery Failed',
                    error
                );
            }
        }

        /* =========================================
           Re-sync State
        ========================================= */

        window.SOVEREIGN_SYNC
            ?.syncMetrics();

        /* =========================================
           Recovery Complete
        ========================================= */

        setTimeout(() => {

            document.body.classList.remove(
                'runtime-recovery'
            );

            this.completeRecovery();

        }, 3000);
    }

    /* ========================================================
       COMPLETE
    ======================================================== */

    completeRecovery() {

        console.log(
            '✅ Runtime Recovery Complete'
        );

        window.SOVEREIGN_NOTIFY
            ?.success(
                'Runtime Stabilized'
            );

        this.recoveryAttempts = 0;
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            attempts:
                this.recoveryAttempts,

            lastHealthy:
                this.lastHealthyState
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_RECOVERY =
    new SovereignRuntimeRecovery();
