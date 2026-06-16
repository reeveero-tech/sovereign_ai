/* ============================================================
   Sovereign AI — runtime-session-policies.js
   الإصدار: 8.0.0
   سياسات الجلسات السيادية
   ============================================================ */

class SovereignRuntimeSessionPolicies {

    constructor() {

        this.idleTimeout =
            60000;

        this.expirationTimeout =
            300000;

        console.log(
            '📜 Runtime Session Policies Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.startMonitoring();

        this.publishReady();
    }

    /* ========================================================
       MONITOR
    ======================================================== */

    startMonitoring() {

        setInterval(() => {

            this.evaluateSessions();

        }, 5000);
    }

    /* ========================================================
       EVALUATE
    ======================================================== */

    evaluateSessions() {

        const sessions =
            window.SOVEREIGN_ACCESS
                ?.legacy?.('session')
            ||
            window.SOVEREIGN_SESSION;

        const machine =
            window.SOVEREIGN_ACCESS
                ?.legacy?.(
                    'session_machine'
                )
            ||
            window.SOVEREIGN_SESSION_MACHINE;

        if (
            !sessions ||
            !machine
        ) {

            return;
        }

        sessions
            .listSessions?.()
            .forEach(session => {

                this.evaluateSession(
                    session,
                    machine
                );
            });
    }

    /* ========================================================
       EVALUATE SESSION
    ======================================================== */

    evaluateSession(
        session,
        machine
    ) {

        const now =
            Date.now();

        const age =
            now -
            session.createdAt;

        const state =
            machine.getState?.(
                session.id
            );

        if (!state) {

            return;
        }

        /* =========================================
           IDLE
        ========================================= */

        if (
            age >
            this.idleTimeout &&
            state.state === 'active'
        ) {

            machine.transition(
                session.id,
                'idle'
            );
        }

        /* =========================================
           EXPIRED
        ========================================= */

        if (
            age >
            this.expirationTimeout &&
            state.state !== 'closed'
        ) {

            machine.transition(
                session.id,
                'closed'
            );

            sessions.closeSession?.(
                session.id
            );
        }
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publish(
            'session-policies:ready',
            {

                idleTimeout:
                    this.idleTimeout,

                expirationTimeout:
                    this.expirationTimeout,

                timestamp:
                    Date.now()
            }
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            idleTimeout:
                this.idleTimeout,

            expirationTimeout:
                this.expirationTimeout
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignSessionPolicies =
    new SovereignRuntimeSessionPolicies();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_SESSION_POLICIES =
    sovereignSessionPolicies;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'session-policies',
        sovereignSessionPolicies
    );
