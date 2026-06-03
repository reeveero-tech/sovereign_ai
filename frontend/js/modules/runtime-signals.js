/* ============================================================
   Sovereign AI — runtime-signals.js
   الإصدار: 6.0.0
   نظام الإشارات السيادي
   ============================================================ */

class SovereignRuntimeSignals {

    constructor() {

        this.initialized = false;

        console.log(
            '🧬 Runtime Signals Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindPerformanceSignals();

        this.bindChatSignals();

        this.bindSocketSignals();

        this.bindCommandSignals();

        this.initialized = true;
    }

    /* ========================================================
       PERFORMANCE
    ======================================================== */

    bindPerformanceSignals() {

        const events =
            window.SOVEREIGN_EVENTS;

        if (!events) return;

        setInterval(() => {

            const fps =
                window.SOVEREIGN_ANIMATION_ENGINE
                    ?.fps || 60;

            if (fps < 30) {

                events.emit(
                    'performance:critical',
                    { fps }
                );

            } else {

                events.emit(
                    'performance:stable',
                    { fps }
                );
            }

        }, 2000);
    }

    /* ========================================================
       CHAT
    ======================================================== */

    bindChatSignals() {

        const originalSend =
            window.SOVEREIGN_CHAT
                ?.sendMessage;

        if (!originalSend) return;

        window.SOVEREIGN_CHAT.sendMessage =
            async (text) => {

                window.SOVEREIGN_EVENTS
                    ?.emit(
                        'chat:user_message',
                        { text }
                    );

                return await originalSend.call(
                    window.SOVEREIGN_CHAT,
                    text
                );
            };
    }

    /* ========================================================
       SOCKET
    ======================================================== */

    bindSocketSignals() {

        const socket =
            window.SOVEREIGN_SOCKET;

        if (!socket) return;

        const originalConnect =
            socket.connect.bind(socket);

        socket.connect = () => {

            window.SOVEREIGN_EVENTS
                ?.emit(
                    'socket:connecting'
                );

            return originalConnect();
        };

        /* =========================================
           CONNECTED
        ========================================= */

        const originalUpdate =
            socket.updateConnectionState
                .bind(socket);

        socket.updateConnectionState =
            (connected) => {

                originalUpdate(
                    connected
                );

                if (connected) {

                    window.SOVEREIGN_EVENTS
                        ?.emit(
                            'socket:connected'
                        );

                } else {

                    window.SOVEREIGN_EVENTS
                        ?.emit(
                            'socket:disconnected'
                        );
                }
            };
    }

    /* ========================================================
       COMMANDS
    ======================================================== */

    bindCommandSignals() {

        const commands =
            window.SOVEREIGN_COMMANDS;

        if (!commands) return;

        const originalExecute =
            commands.execute.bind(
                commands
            );

        commands.execute = () => {

            const command =
                commands.input?.value?.trim();

            originalExecute();

            if (command) {

                window.SOVEREIGN_EVENTS
                    ?.emit(
                        'command:executed',
                        {
                            command
                        }
                    );
            }
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_SIGNALS =
    new SovereignRuntimeSignals();
