/* ============================================================
   Sovereign AI — bootstrap.js
   الإصدار: 4.0.0
   مولد النظام السيادي
   ============================================================ */

class SovereignBootstrap {

    constructor() {

        this.modules = [];

        this.initialized = false;

        console.log(
            '🚀 Sovereign Bootstrap Starting...'
        );

        this.boot();
    }

    /* ========================================================
       BOOT
    ======================================================== */

    async boot() {

        try {

            this.initializeCore();

            this.initializeState();

            this.initializeRenderer();

            this.initializeEffects();

            this.initializeCinema();

            this.initializeAnimations();

            this.initializeAI();

            this.bindGlobalSystems();

            this.finishBoot();

        } catch (error) {

            console.error(
                'BOOT FAILURE:',
                error
            );
        }
    }

    /* ========================================================
       INITIALIZE SYSTEMS
    ======================================================== */

    initializeCore() {

        if (!window.SOVEREIGN_CORE) {

            throw new Error(
                'Core Missing'
            );
        }

        this.modules.push(
            'core'
        );
    }

    initializeState() {

        if (!window.SOVEREIGN_STATE) {

            throw new Error(
                'State Manager Missing'
            );
        }

        this.modules.push(
            'state'
        );
    }

    initializeRenderer() {

        if (!window.SOVEREIGN_RENDER) {

            throw new Error(
                'Render Engine Missing'
            );
        }

        this.modules.push(
            'renderer'
        );
    }

    initializeEffects() {

        if (!window.SOVEREIGN_FX) {

            throw new Error(
                'Adaptive FX Missing'
            );
        }

        this.modules.push(
            'effects'
        );
    }

    initializeCinema() {

        if (!window.SOVEREIGN_CINEMA) {

            throw new Error(
                'Cinema Engine Missing'
            );
        }

        this.modules.push(
            'cinema'
        );
    }

    initializeAnimations() {

        if (
            !window.SOVEREIGN_ANIMATION_ENGINE
        ) {

            throw new Error(
                'Animation Engine Missing'
            );
        }

        this.modules.push(
            'animations'
        );
    }

    initializeAI() {

        if (!window.SOVEREIGN_AI) {

            throw new Error(
                'Live AI Missing'
            );
        }

        this.modules.push(
            'ai'
        );
    }

    /* ========================================================
       GLOBAL BINDINGS
    ======================================================== */

    bindGlobalSystems() {

        const state =
            window.SOVEREIGN_STATE;

        const render =
            window.SOVEREIGN_RENDER;

        /* =========================================
           ACTIVE TAB SYNC
        ========================================= */

        state.subscribe(
            'ui',
            ({ newValue }) => {

                if (
                    newValue.activeTab
                ) {

                    document.body.dataset.activeTab =
                        newValue.activeTab;
                }
            }
        );

        /* =========================================
           PERFORMANCE SYNC
        ========================================= */

        state.subscribe(
            'metrics',
            ({ newValue }) => {

                if (
                    newValue.fps
                ) {

                    render.updateText(
                        'metric-fps',
                        newValue.fps
                    );
                }
            }
        );

        /* =========================================
           SYSTEM CONNECTION
        ========================================= */

        state.subscribe(
            'system',
            ({ newValue }) => {

                if (
                    newValue.connected
                ) {

                    document.body.classList.add(
                        'system-online'
                    );

                } else {

                    document.body.classList.remove(
                        'system-online'
                    );
                }
            }
        );
    }

    /* ========================================================
       FINISH BOOT
    ======================================================== */

    finishBoot() {

        this.initialized = true;

        document.body.classList.add(
            'sovereign-ready'
        );

        console.log(
            `
            🧠 SOVEREIGN AI ONLINE
            =====================
            Modules:
            ${this.modules.join('\n')}
            `
        );

        if (
            window.SOVEREIGN_CINEMA
        ) {

            window.SOVEREIGN_CINEMA
                .createMoment(
                    'epic'
                );
        }
    }
}

/* ============================================================
   START SYSTEM
============================================================ */

window.SOVEREIGN_BOOT =
    new SovereignBootstrap();
