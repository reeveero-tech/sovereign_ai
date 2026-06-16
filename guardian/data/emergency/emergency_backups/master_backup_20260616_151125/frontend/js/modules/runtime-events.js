/* ============================================================
   Sovereign AI — runtime-events.js
   الإصدار: 6.0.0
   ناقل الأحداث السيادي
   ============================================================ */

class SovereignRuntimeEvents {

    constructor() {

        this.events = new Map();

        console.log(
            '📡 Runtime Events Initialized'
        );
    }

    /* ========================================================
       ON
    ======================================================== */

    on(
        event,
        callback
    ) {

        if (
            !this.events.has(event)
        ) {

            this.events.set(
                event,
                []
            );
        }

        this.events
            .get(event)
            .push(callback);
    }

    /* ========================================================
       EMIT
    ======================================================== */

    emit(
        event,
        payload = {}
    ) {

        const listeners =
            this.events.get(event);

        if (!listeners) return;

        listeners.forEach(listener => {

            try {

                listener(payload);

            } catch (error) {

                console.error(
                    `Event Error: ${event}`,
                    error
                );
            }
        });
    }

    /* ========================================================
       OFF
    ======================================================== */

    off(
        event,
        callback
    ) {

        const listeners =
            this.events.get(event);

        if (!listeners) return;

        this.events.set(

            event,

            listeners.filter(
                cb => cb !== callback
            )
        );
    }

    /* ========================================================
       ONCE
    ======================================================== */

    once(
        event,
        callback
    ) {

        const wrapper = (
            payload
        ) => {

            callback(payload);

            this.off(
                event,
                wrapper
            );
        };

        this.on(
            event,
            wrapper
        );
    }

    /* ========================================================
       CLEAR
    ======================================================== */

    clear(event) {

        if (event) {

            this.events.delete(
                event
            );

        } else {

            this.events.clear();
        }
    }

    /* ========================================================
       DEBUG
    ======================================================== */

    debug() {

        console.table(
            [...this.events.entries()]
                .map(
                    ([name, listeners]) => ({

                        event: name,

                        listeners:
                            listeners.length
                    })
                )
        );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_EVENTS =
    new SovereignRuntimeEvents();
