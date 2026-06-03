/* ============================================================
   Sovereign AI — runtime-hooks.js
   الإصدار: 6.0.0
   طبقة الخطافات العصبية
   ============================================================ */

class SovereignRuntimeHooks {

    constructor() {

        console.log(
            '🪝 Runtime Hooks Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindChatHooks();

        this.bindPerformanceHooks();

        this.bindCommandHooks();

        this.bindConnectionHooks();
    }

    /* ========================================================
       CHAT HOOKS
    ======================================================== */

    bindChatHooks() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        /* =========================================
           USER MESSAGE
        ========================================= */

        events.on(
            'chat:user_message',
            (payload) => {

                window.SOVEREIGN_CINEMA
                    ?.pulse(1.05);

                window.SOVEREIGN_NOTIFY
                    ?.info(
                        'Neural Message Sent'
                    );
            }
        );

        /* =========================================
           AI RESPONSE
        ========================================= */

        events.on(
            'chat:ai_response',
            (payload) => {

                window.SOVEREIGN_FX
                    ?.cinematicFlash(0.8);

                window.SOVEREIGN_CINEMA
                    ?.enterScene(
                        'response'
                    );
            }
        );
    }

    /* ========================================================
       PERFORMANCE HOOKS
    ======================================================== */

    bindPerformanceHooks() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        events.on(
            'performance:critical',
            () => {

                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'Critical Performance Detected'
                    );

                document.body.classList.add(
                    'runtime-critical'
                );
            }
        );

        events.on(
            'performance:stable',
            () => {

                document.body.classList.remove(
                    'runtime-critical'
                );
            }
        );
    }

    /* ========================================================
       COMMAND HOOKS
    ======================================================== */

    bindCommandHooks() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        events.on(
            'command:executed',
            (payload) => {

                window.SOVEREIGN_NOTIFY
                    ?.success(
                        `Command Executed: ${payload.command}`
                    );

                window.SOVEREIGN_CINEMA
                    ?.createMoment(
                        'epic'
                    );
            }
        );
    }

    /* ========================================================
       CONNECTION HOOKS
    ======================================================== */

    bindConnectionHooks() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        events.on(
            'socket:connected',
            () => {

                window.SOVEREIGN_NOTIFY
                    ?.success(
                        'Neural Link Established'
                    );
            }
        );

        events.on(
            'socket:disconnected',
            () => {

                window.SOVEREIGN_NOTIFY
                    ?.error(
                        'Neural Link Lost'
                    );
            }
        );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_HOOKS =
    new SovereignRuntimeHooks();
