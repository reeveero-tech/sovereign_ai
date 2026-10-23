/* ============================================================
   Sovereign AI — sovereign-orchestrator.js
   الإصدار: 5.0.0
   العقل السيادي المنسق
   ============================================================ */

class SovereignOrchestrator {

    constructor() {

        this.systems = {};

        this.cycles = 0;

        this.isRunning = false;

        console.log(
            '👑 Sovereign Orchestrator Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerSystems();

        this.bindEvents();

        this.start();
    }

    /* ========================================================
       REGISTER SYSTEMS
    ======================================================== */

    registerSystems() {

        this.systems = {

            core:
                window.SOVEREIGN_CORE,

            state:
                window.SOVEREIGN_STATE,

            render:
                window.SOVEREIGN_RENDER,

            fx:
                window.SOVEREIGN_FX,

            cinema:
                window.SOVEREIGN_CINEMA,

            animation:
                window.SOVEREIGN_ANIMATION_ENGINE,

            ai:
                window.SOVEREIGN_AI,

            memory:
                window.SOVEREIGN_MEMORY,

            ui:
                window.SOVEREIGN_UI
        };

        console.log(
            '🧩 Systems Registered:',
            Object.keys(this.systems)
        );
    }

    /* ========================================================
       BIND EVENTS
    ======================================================== */

    bindEvents() {

        const core =
            this.systems.core;

        if (!core) return;

        core.on(
            'memory:updated',
            (data) => {

                this.handleMemoryUpdate(
                    data
                );
            }
        );

        core.on(
            'performance:critical',
            () => {

                this.handleCriticalPerformance();
            }
        );
    }

    /* ========================================================
       START
    ======================================================== */

    start() {

        this.isRunning = true;

        this.runCycle();

        console.log(
            '🚀 Sovereign Runtime Active'
        );
    }

    /* ========================================================
       MAIN LOOP
    ======================================================== */

    runCycle() {

        if (!this.isRunning) return;

        this.cycles++;

        this.syncSystems();

        this.updateMetrics();

        requestAnimationFrame(() => {

            this.runCycle();
        });
    }

    /* ========================================================
       SYNC
    ======================================================== */

    syncSystems() {

        const state =
            this.systems.state;

        if (!state) return;

        state.mergeState(
            'metrics',
            {
                cycles:
                    this.cycles
            }
        );
    }

    /* ========================================================
       METRICS
    ======================================================== */

    updateMetrics() {

        /* R-730 (البند ١.٤): لا كتابة في عدّاد الدورات — this.cycles عدّاد
           إطارات محلي لا دورات النظام؛ المصدر الوحيد total_cycles من /status
           (main.js — LIVE_BINDINGS.json). */
    }

    /* ========================================================
       MEMORY UPDATE
    ======================================================== */

    handleMemoryUpdate(data) {

        console.log(
            '🧠 Memory Updated',
            data
        );

        if (
            this.systems.cinema
        ) {

            this.systems.cinema
                .pulse(1.1);
        }
    }

    /* ========================================================
       PERFORMANCE CRITICAL
    ======================================================== */

    handleCriticalPerformance() {

        console.warn(
            '⚠️ Critical Performance'
        );

        if (
            this.systems.fx
        ) {

            this.systems.fx
                .reduceEffects();
        }
    }

    /* ========================================================
       SEND TO AI
    ======================================================== */

    async askAI(message) {

        if (
            !this.systems.ai
        ) return;

        await this.systems.ai
            .sendMessage(message);
    }

    /* ========================================================
       SAVE MEMORY
    ======================================================== */

    saveMemory(user, ai) {

        if (
            !this.systems.memory
        ) return;

        this.systems.memory
            .saveInteraction(
                user,
                ai
            );
    }

    /* ========================================================
       SHUTDOWN
    ======================================================== */

    shutdown() {

        this.isRunning = false;

        console.warn(
            '🛑 Sovereign Shutdown'
        );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_ORCHESTRATOR =
    new SovereignOrchestrator();
