/* ============================================================
   Sovereign AI — runtime-session-state-machine.js
   الإصدار: 8.0.0
   آلة حالات الجلسات السيادية
   ============================================================ */

class SovereignRuntimeSessionStateMachine {

    constructor() {

        this.states = new Map();

        console.log(
            '⚙️ Runtime Session State Machine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindSessionManager();

        this.publishReady();
    }

    /* ========================================================
       BIND SESSION MANAGER
    ======================================================== */

    bindSessionManager() {

        const sessions =
            window.SOVEREIGN_ACCESS
                ?.legacy?.('session')
            ||
            window.SOVEREIGN_SESSION;

        if (!sessions) {

            console.warn(
                '⚠️ Session State Machine Missing Session Manager'
            );

            return;
        }

        const active =
            sessions.getActiveSession?.();

        if (active) {

            this.initializeSession(
                active.id
            );
        }
    }

    /* ========================================================
       INITIALIZE SESSION
    ======================================================== */

    initializeSession(sessionId) {

        this.states.set(

            sessionId,

            {

                state:
                    'created',

                updatedAt:
                    Date.now(),

                transitions:
                    []
            }
        );

        this.transition(
            sessionId,
            'active'
        );
    }

    /* ========================================================
       TRANSITION
    ======================================================== */

    transition(
        sessionId,
        nextState
    ) {

        const machine =
            this.states.get(
                sessionId
            );

        if (!machine) {

            return;
        }

        const previous =
            machine.state;

        machine.state =
            nextState;

        machine.updatedAt =
            Date.now();

        machine.transitions.push({

            from:
                previous,

            to:
                nextState,

            timestamp:
                Date.now()
        });

        console.log(
            `
⚙️ Session State Transition
Session:
${sessionId}

${previous}
→
${nextState}
            `
        );

        this.publishTransition(
            sessionId,
            previous,
            nextState
        );
    }

    /* ========================================================
       PUBLISH
    ======================================================== */

    publishTransition(
        sessionId,
        previous,
        nextState
    ) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publish(
            'session:state:changed',
            {

                sessionId,

                previous,

                current:
                    nextState,

                timestamp:
                    Date.now()
            }
        );
    }

    /* ========================================================
       GET STATE
    ======================================================== */

    getState(sessionId) {

        return this.states.get(
            sessionId
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            sessions:
                this.states.size
        };
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publish(
            'session-machine:ready',
            {

                sessions:
                    this.states.size,

                timestamp:
                    Date.now()
            }
        );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignSessionMachine =
    new SovereignRuntimeSessionStateMachine();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_SESSION_MACHINE =
    sovereignSessionMachine;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'session-state-machine',
        sovereignSessionMachine
    );
