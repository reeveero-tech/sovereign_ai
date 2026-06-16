/* ============================================================
   Sovereign AI — runtime-queue-intelligence.js
   الإصدار: 8.0.0
   ذكاء الطوابير السيادي
   ============================================================ */

class SovereignRuntimeQueueIntelligence {

    constructor() {

        this.starvationThreshold =
            15000;

        this.criticalChannels =
            new Set([

                'runtime:errors',

                'scheduler:task:failed',

                'sandbox:violation'
            ]);

        console.log(
            '🧠 Runtime Queue Intelligence Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.publishReady();
    }

    /* ========================================================
       EFFECTIVE PRIORITY
    ======================================================== */

    calculateEffectivePriority(task) {

        let effective =
            task.priority || 10;

        /* =========================================
           WAITING TIME BOOST
        ========================================= */

        const waitingTime =
            Date.now() -
            task.createdAt;

        if (
            waitingTime >
            this.starvationThreshold
        ) {

            effective -= 3;
        }

        /* =========================================
           CRITICAL CHANNEL BOOST
        ========================================= */

        const channel =
            task.metadata
                ?.channel;

        if (
            this.criticalChannels.has(
                channel
            )
        ) {

            effective = 0;
        }

        /* =========================================
           FAIRNESS LIMIT
        ========================================= */

        return Math.max(
            effective,
            0
        );
    }

    /* ========================================================
       SORT QUEUE
    ======================================================== */

    sortQueue(queue = []) {

        return queue.sort(

            (a, b) =>

                this.calculateEffectivePriority(a)
                -
                this.calculateEffectivePriority(b)
        );
    }

    /* ========================================================
       SHOULD DEFER
    ======================================================== */

    shouldDefer(task) {

        const channel =
            task.metadata
                ?.channel;

        if (
            this.criticalChannels.has(
                channel
            )
        ) {

            return false;
        }

        const adaptive =
            window.SOVEREIGN_ACCESS
                ?.legacy?.(
                    'adaptive_scheduler'
                )
            ||
            window.SOVEREIGN_ADAPTIVE_SCHEDULER;

        const mode =
            adaptive
                ?.getStatus?.()
                ?.mode;

        if (
            mode === 'critical'
        ) {

            return (
                task.priority > 5
            );
        }

        return false;
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus
            ?.publishWithoutMiddleware?.(

                'queue-intelligence:ready',

                {

                    starvationThreshold:
                        this.starvationThreshold,

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

            starvationThreshold:
                this.starvationThreshold,

            criticalChannels:
                this.criticalChannels.size
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignQueueIntelligence =
    new SovereignRuntimeQueueIntelligence();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_QUEUE_INTELLIGENCE =
    sovereignQueueIntelligence;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'queue-intelligence',
        sovereignQueueIntelligence
    );
