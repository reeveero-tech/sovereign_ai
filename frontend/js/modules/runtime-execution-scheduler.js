/* ============================================================
   Sovereign AI — runtime-execution-scheduler.js
   الإصدار: 8.0.0
   مجدول التنفيذ السيادي
   ============================================================ */

class SovereignRuntimeExecutionScheduler {

    constructor() {

        this.queue = [];

        this.processing = false;

        this.maxConcurrent =
            5;

        this.activeTasks =
            0;

        console.log(
            '⏱ Runtime Execution Scheduler Initialized'
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
       SCHEDULE
    ======================================================== */

    schedule({

        id =
            crypto.randomUUID(),

        priority =
            10,

        task,

        metadata = {}
    }) {

        if (
            typeof task !==
            'function'
        ) {

            console.warn(
                '⚠️ Invalid Scheduled Task'
            );

            return false;
        }

        this.queue.push({

            id,

            priority,

            task,

            metadata,

            state:
                'queued',

            createdAt:
                Date.now()
        });

        /* =========================================
           SORT PRIORITY
        ========================================= */

        this.queue.sort(
            (a, b) =>
                a.priority -
                b.priority
        );

        console.log(
            `
⏱ Task Scheduled
Task:
${id}
            `
        );

        this.processQueue();

        return id;
    }

    /* ========================================================
       PROCESS
    ======================================================== */

    async processQueue() {

        if (
            this.processing
        ) {

            return;
        }

        this.processing =
            true;

        while (
            this.queue.length &&
            this.activeTasks <
            this.maxConcurrent
        ) {

            const item =
                this.queue.shift();

            if (!item) {

                continue;
            }

            this.executeTask(
                item
            );
        }

        this.processing =
            false;
    }

    /* ========================================================
       EXECUTE
    ======================================================== */

    async executeTask(item) {

        this.activeTasks++;

        item.state =
            'running';

        const start =
            performance.now();

        try {

            await item.task();

            item.state =
                'completed';

            const duration =
                performance.now() -
                start;

            this.publishCompleted(
                item,
                duration
            );

        } catch (error) {

            item.state =
                'failed';

            console.error(
                `
⚠️ Scheduled Task Failed
Task:
${item.id}
                `,
                error
            );

            this.publishFailed(
                item,
                error
            );
        }

        this.activeTasks--;

        this.processQueue();
    }

    /* ========================================================
       COMPLETED
    ======================================================== */

    publishCompleted(
        item,
        duration
    ) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus
            ?.publishWithoutMiddleware?.(

                'scheduler:task:completed',

                {

                    task:
                        item.id,

                    priority:
                        item.priority,

                    duration,

                    timestamp:
                        Date.now()
                }
            );
    }

    /* ========================================================
       FAILED
    ======================================================== */

    publishFailed(
        item,
        error
    ) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus
            ?.publishWithoutMiddleware?.(

                'scheduler:task:failed',

                {

                    task:
                        item.id,

                    error:
                        error.message,

                    timestamp:
                        Date.now()
                }
            );
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

                'scheduler:ready',

                {

                    maxConcurrent:
                        this.maxConcurrent,

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

            queued:
                this.queue.length,

            active:
                this.activeTasks,

            maxConcurrent:
                this.maxConcurrent,

            processing:
                this.processing
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignScheduler =
    new SovereignRuntimeExecutionScheduler();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_EXECUTION_SCHEDULER =
    sovereignScheduler;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'execution-scheduler',
        sovereignScheduler
    );
