/* ============================================================
   Sovereign AI — runtime-bus.js
   الإصدار: 7.0.0
   ناقل الاتصال السيادي
   ============================================================ */

class SovereignRuntimeBus {

    constructor() {

        this.channels = new Map();

        this.middlewares = [];

        console.log(
            '🛰 Runtime Bus Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerDefaultChannels();
    }

    /* ========================================================
       CHANNELS
    ======================================================== */

    registerDefaultChannels() {

        [

            'runtime',

            'system',

            'security',

            'analytics',

            'chat',

            'performance',

            'kernel'

        ].forEach(channel => {

            this.createChannel(channel);
        });
    }

    /* ========================================================
       CREATE CHANNEL
    ======================================================== */

    createChannel(name) {

        if (
            this.channels.has(name)
        ) return;

        this.channels.set(name, []);
    }

    /* ========================================================
       SUBSCRIBE
    ======================================================== */

    subscribe(
        channel,
        listener
    ) {

        if (
            !this.channels.has(channel)
        ) {

            this.createChannel(channel);
        }

        this.channels
            .get(channel)
            .push(listener);
    }

    /* ========================================================
       PUBLISH
    ======================================================== */

    publish(
        channel,
        payload = {}
    ) {

        if (
            !this.channels.has(channel)
        ) {

            return;
        }

        let message = {

            channel,

            payload,

            timestamp:
                Date.now()
        };

        /* =========================================
           MIDDLEWARES
        ========================================= */

        this.middlewares.forEach(
            middleware => {

                try {

                    message =
                        middleware(message)
                        || message;

                } catch (error) {

                    console.error(
                        'Bus Middleware Error',
                        error
                    );
                }
            }
        );

        /* =========================================
           LISTENERS
        ========================================= */

        this.channels
            .get(channel)
            .forEach(listener => {

                try {

                    listener(message);

                } catch (error) {

                    console.error(
                        `Bus Listener Error (${channel})`,
                        error
                    );
                }
            });
    }

    /* ========================================================
       MIDDLEWARE
    ======================================================== */

    use(middleware) {

        this.middlewares.push(
            middleware
        );
    }

    /* ========================================================
       UNSUBSCRIBE
    ======================================================== */

    unsubscribe(
        channel,
        listener
    ) {

        if (
            !this.channels.has(channel)
        ) return;

        const listeners =
            this.channels.get(channel);

        this.channels.set(

            channel,

            listeners.filter(
                l => l !== listener
            )
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            channels:
                [...this.channels.keys()],

            middlewares:
                this.middlewares.length
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_BUS =
    new SovereignRuntimeBus();
