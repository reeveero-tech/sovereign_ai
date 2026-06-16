/* ============================================================
   Sovereign AI — runtime-power-manager.js
   الإصدار: 7.0.0
   مدير الطاقة السيادي
   ============================================================ */

class SovereignRuntimePowerManager {

    constructor() {

        this.mode = 'balanced';

        this.visibilityState =
            document.visibilityState;

        console.log(
            '⚡ Runtime Power Manager Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindVisibility();

        this.bindPerformance();

        this.applyMode(
            'balanced'
        );
    }

    /* ========================================================
       VISIBILITY
    ======================================================== */

    bindVisibility() {

        document.addEventListener(
            'visibilitychange',
            () => {

                this.visibilityState =
                    document.visibilityState;

                if (
                    this.visibilityState === 'hidden'
                ) {

                    this.applyMode(
                        'eco'
                    );

                } else {

                    this.applyMode(
                        'balanced'
                    );
                }
            }
        );
    }

    /* ========================================================
       PERFORMANCE
    ======================================================== */

    bindPerformance() {

        window.SOVEREIGN_EVENTS
            ?.on(
                'performance:critical',
                () => {

                    this.applyMode(
                        'safe'
                    );
                }
            );

        window.SOVEREIGN_EVENTS
            ?.on(
                'performance:stable',
                () => {

                    if (
                        this.visibilityState ===
                        'visible'
                    ) {

                        this.applyMode(
                            'balanced'
                        );
                    }
                }
            );
    }

    /* ========================================================
       APPLY MODE
    ======================================================== */

    applyMode(mode) {

        this.mode = mode;

        document.body.dataset.powerMode =
            mode;

        switch (mode) {

            case 'eco':

                this.enableEcoMode();

                break;

            case 'safe':

                this.enableSafeMode();

                break;

            case 'balanced':

            default:

                this.enableBalancedMode();
        }

        console.log(
            `⚡ Power Mode: ${mode}`
        );

        window.SOVEREIGN_NOTIFY
            ?.info(
                `Power Mode: ${mode}`
            );
    }

    /* ========================================================
       ECO
    ======================================================== */

    enableEcoMode() {

        document.body.classList.add(
            'runtime-eco'
        );

        document.body.classList.remove(
            'runtime-safe'
        );
    }

    /* ========================================================
       SAFE
    ======================================================== */

    enableSafeMode() {

        document.body.classList.add(
            'runtime-safe'
        );

        document.body.classList.remove(
            'runtime-eco'
        );
    }

    /* ========================================================
       BALANCED
    ======================================================== */

    enableBalancedMode() {

        document.body.classList.remove(
            'runtime-safe'
        );

        document.body.classList.remove(
            'runtime-eco'
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            mode:
                this.mode,

            visibility:
                this.visibilityState
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_POWER =
    new SovereignRuntimePowerManager();
