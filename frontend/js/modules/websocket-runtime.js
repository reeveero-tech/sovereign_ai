/* ============================================================
   Sovereign AI — websocket-runtime.js
   الإصدار: 5.0.0
   طبقة الاتصال السيادية الحية
   ============================================================ */

class SovereignWebSocketRuntime {

    constructor() {

        this.socket = null;

        this.connected = false;

        this.connecting = false;

        this.reconnectAttempts = 0;

        this.maxReconnectAttempts = 10;

        this.latency = 0;

        this.heartbeat = null;

        console.log(
            '🌐 WebSocket Runtime Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.connect();
    }

    /* ========================================================
       CONNECT
    ======================================================== */

    connect() {

        if (
            this.connected ||
            this.connecting
        ) return;

        this.connecting = true;

        const protocol =
            window.location.protocol === 'https:'
                ? 'wss:'
                : 'ws:';

        const url =
            `${protocol}//${window.location.host}/ws/sovereign`;

        console.log(
            '🔌 Connecting:',
            url
        );

        try {

            this.socket =
                new WebSocket(url);

            this.bindSocketEvents();

        } catch (error) {

            console.error(
                'Socket Creation Failed',
                error
            );

            this.scheduleReconnect();
        }
    }

    /* ========================================================
       SOCKET EVENTS
    ======================================================== */

    bindSocketEvents() {

        this.socket.onopen = () => {

            console.log(
                '✅ WebSocket Connected'
            );

            this.connected = true;

            this.connecting = false;

            this.reconnectAttempts = 0;

            this.updateConnectionState(
                true
            );

            this.startHeartbeat();

            if (
                window.SOVEREIGN_CINEMA
            ) {

                window.SOVEREIGN_CINEMA
                    .createMoment(
                        'success'
                    );
            }
        };

        this.socket.onmessage = (
            event
        ) => {

            this.handleMessage(
                event.data
            );
        };

        this.socket.onerror = (
            error
        ) => {

            console.error(
                'WebSocket Error',
                error
            );
        };

        this.socket.onclose = () => {

            console.warn(
                '❌ WebSocket Closed'
            );

            this.connected = false;

            this.connecting = false;

            this.updateConnectionState(
                false
            );

            this.stopHeartbeat();

            this.scheduleReconnect();

            if (
                window.SOVEREIGN_CINEMA
            ) {

                window.SOVEREIGN_CINEMA
                    .enterScene(
                        'critical'
                    );
            }
        };
    }

    /* ========================================================
       HANDLE MESSAGE
    ======================================================== */

    handleMessage(raw) {

        try {

            const data =
                JSON.parse(raw);

            switch (data.type) {

                case 'chat_reply':

                    this.handleAIReply(
                        data
                    );

                    break;

                case 'metrics':

                    this.handleMetrics(
                        data
                    );

                    break;

                case 'system':

                    this.handleSystem(
                        data
                    );

                    break;

                default:

                    console.log(
                        'Unhandled Message',
                        data
                    );
            }

        } catch (error) {

            console.error(
                'Message Parse Failed',
                error
            );
        }
    }

    /* ========================================================
       AI REPLY
    ======================================================== */

    handleAIReply(data) {

        if (
            window.SOVEREIGN_DIALOGUE
        ) {

            window.SOVEREIGN_DIALOGUE
                .addAIMessage(
                    data.message ||
                    data.reply ||
                    '...'
                );
        }
    }

    /* ========================================================
       METRICS
    ======================================================== */

    handleMetrics(data) {

        if (
            window.SOVEREIGN_METRICS
        ) {

            Object.entries(data.metrics || {})
                .forEach(([key, value]) => {

                    window.SOVEREIGN_METRICS
                        .updateMetric(
                            key,
                            value
                        );
                });
        }
    }

    /* ========================================================
       SYSTEM
    ======================================================== */

    handleSystem(data) {

        console.log(
            '⚙️ System Event',
            data
        );
    }

    /* ========================================================
       SEND
    ======================================================== */

    send(type, payload = {}) {

        if (
            !this.connected
        ) {

            console.warn(
                'Socket Not Connected'
            );

            return;
        }

        this.socket.send(
            JSON.stringify({
                type,
                payload,
                timestamp:
                    Date.now()
            })
        );
    }

    /* ========================================================
       CHAT
    ======================================================== */

    sendChat(text) {

        if (
            window.SOVEREIGN_DIALOGUE
        ) {

            window.SOVEREIGN_DIALOGUE
                .addUserMessage(
                    text
                );
        }

        this.send(
            'chat_message',
            {
                text
            }
        );

        if (
            window.SOVEREIGN_CINEMA
        ) {

            window.SOVEREIGN_CINEMA
                .enterScene(
                    'thinking'
                );
        }
    }

    /* ========================================================
       HEARTBEAT
    ======================================================== */

    startHeartbeat() {

        this.heartbeat =
            setInterval(() => {

                const start =
                    performance.now();

                this.send(
                    'ping'
                );

                this.latency =
                    Math.round(
                        performance.now() - start
                    );

            }, 5000);
    }

    stopHeartbeat() {

        clearInterval(
            this.heartbeat
        );
    }

    /* ========================================================
       RECONNECT
    ======================================================== */

    scheduleReconnect() {

        if (
            this.reconnectAttempts >=
            this.maxReconnectAttempts
        ) {

            console.error(
                'Max Reconnect Attempts'
            );

            return;
        }

        this.reconnectAttempts++;

        const delay =
            Math.min(
                1000 *
                this.reconnectAttempts,
                10000
            );

        console.warn(
            `Reconnect in ${delay}ms`
        );

        setTimeout(() => {

            this.connect();

        }, delay);
    }

    /* ========================================================
       CONNECTION STATE
    ======================================================== */

    updateConnectionState(
        connected
    ) {

        if (
            window.SOVEREIGN_STATE
        ) {

            window.SOVEREIGN_STATE
                .mergeState(
                    'system',
                    {
                        connected
                    }
                );
        }

        const chip =
            document.getElementById(
                'ws-status-chip'
            );

        if (chip) {

            chip.textContent =
                connected
                    ? 'متصل'
                    : 'غير متصل';

            chip.classList.toggle(
                'online',
                connected
            );

            chip.classList.toggle(
                'offline',
                !connected
            );
        }
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_SOCKET =
    new SovereignWebSocketRuntime();
