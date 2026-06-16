/* ============================================================
   Sovereign AI — runtime-session-manager.js
   الإصدار: 8.0.0
   مدير الجلسات السيادي
   ============================================================ */

class SovereignRuntimeSessionManager {

    constructor() {

        this.sessions = new Map();

        this.activeSession = null;

        console.log(
            '🪪 Runtime Session Manager Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.createInitialSession();

        this.bindBus();

        this.publishReady();
    }

    /* ========================================================
       CREATE SESSION
    ======================================================== */

    createSession({

        scope = 'runtime',

        owner = 'system'
    } = {}) {

        const session = {

            id:
                crypto.randomUUID(),

            scope,

            owner,

            createdAt:
                Date.now(),

            traces:
                [],

            state:
                'active'
        };

        this.sessions.set(
            session.id,
            session
        );

        this.activeSession =
            session.id;

        console.log(
            `
🪪 Runtime Session Created
Session:
${session.id}
            `
        );

        return session;
    }

    /* ========================================================
       INITIAL SESSION
    ======================================================== */

    createInitialSession() {

        this.createSession({

            scope:
                'runtime-bootstrap',

            owner:
                'runtime-system'
        });
    }

    /* ========================================================
       BIND BUS
    ======================================================== */

    bindBus() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (!bus) {

            console.warn(
                '⚠️ Session Manager Missing Bus'
            );

            return;
        }

        bus.subscribe(

            'analytics:capture',

            (message) => {

                this.attachTrace(
                    message
                );
            }
        );

        bus.subscribe(

            'runtime:errors',

            (message) => {

                this.attachTrace(
                    message
                );
            }
        );
    }

    /* ========================================================
       ATTACH TRACE
    ======================================================== */

    attachTrace(message) {

        const traceId =
            message.meta
                ?.context
                ?.traceId;

        if (
            !traceId ||
            !this.activeSession
        ) {

            return;
        }

        const session =
            this.sessions.get(
                this.activeSession
            );

        if (!session) {

            return;
        }

        session.traces.push(
            traceId
        );
    }

    /* ========================================================
       CLOSE SESSION
    ======================================================== */

    closeSession(sessionId) {

        const session =
            this.sessions.get(
                sessionId
            );

        if (!session) {

            return;
        }

        session.state =
            'closed';

        session.closedAt =
            Date.now();

        console.log(
            `
🪪 Runtime Session Closed
Session:
${sessionId}
            `
        );
    }

    /* ========================================================
       GET SESSION
    ======================================================== */

    getSession(sessionId) {

        return this.sessions.get(
            sessionId
        );
    }

    /* ========================================================
       GET ACTIVE
    ======================================================== */

    getActiveSession() {

        return this.sessions.get(
            this.activeSession
        );
    }

    /* ========================================================
       LIST
    ======================================================== */

    listSessions() {

        return [
            ...this.sessions.values()
        ];
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publish(
            'session:ready',
            {

                sessions:
                    this.sessions.size,

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

            sessions:
                this.sessions.size,

            activeSession:
                this.activeSession
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignSessionManager =
    new SovereignRuntimeSessionManager();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_SESSION =
    sovereignSessionManager;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'session-manager',
        sovereignSessionManager
    );
