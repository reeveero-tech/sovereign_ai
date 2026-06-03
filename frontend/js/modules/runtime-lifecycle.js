/* ============================================================
   Sovereign AI — runtime-lifecycle.js
   الإصدار: 7.0.0
   مدير دورة الحياة السيادي
   ============================================================ */

class SovereignRuntimeLifecycle {

    constructor() {

        this.state = 'booting';

        this.previousState = null;

        console.log(
            '🌌 Runtime Lifecycle Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindVisibilityLifecycle();

        this.bindConnectionLifecycle();

        this.bindKernelLifecycle();

        this.completeBoot();
    }

    /* ========================================================
       STATE
    ======================================================== */

    setState(newState) {

        if (
            this.state === newState
        ) return;

        this.previousState =
            this.state;

        this.state =
            newState;

        console.log(
            `
🔄 Runtime Lifecycle
FROM: ${this.previousState}
TO:   ${this.state}
            `
        );

        document.body.dataset.lifecycle =
            newState;

        window.SOVEREIGN_EVENTS
            ?.emit(
                'lifecycle:changed',
                {
                    previous:
                        this.previousState,

                    current:
                        this.state
                }
            );
    }

    /* ========================================================
       VISIBILITY
    ======================================================== */

    bindVisibilityLifecycle() {

        document.addEventListener(
            'visibilitychange',
            () => {

                if (
                    document.hidden
                ) {

                    this.setState(
                        'suspended'
                    );

                } else {

                    this.setState(
                        'active'
                    );
                }
            }
        );
    }

    /* ========================================================
       CONNECTION
    ======================================================== */

    bindConnectionLifecycle() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        events.on(
            'socket:disconnected',
            () => {

                this.setState(
                    'offline'
                );
            }
        );

        events.on(
            'socket:connected',
            () => {

                this.setState(
                    'active'
                );
            }
        );
    }

    /* ========================================================
       KERNEL
    ======================================================== */

    bindKernelLifecycle() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        events.on(
            'kernel:degraded',
            () => {

                this.setState(
                    'degraded'
                );
            }
        );
    }

    /* ========================================================
       COMPLETE BOOT
    ======================================================== */

    completeBoot() {

        setTimeout(() => {

            this.setState(
                'active'
            );

            document.body.classList.remove(
                'runtime-loading'
            );

            document.body.classList.add(
                'runtime-ready'
            );

            window.SOVEREIGN_NOTIFY
                ?.success(
                    'Runtime Lifecycle Active'
                );

        }, 1200);
    }

    /* ========================================================
       SHUTDOWN
    ======================================================== */

    shutdown() {

        this.setState(
            'shutdown'
        );

        window.SOVEREIGN_NOTIFY
            ?.warning(
                'Runtime Shutdown'
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            current:
                this.state,

            previous:
                this.previousState
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_LIFECYCLE =
    new SovereignRuntimeLifecycle();
