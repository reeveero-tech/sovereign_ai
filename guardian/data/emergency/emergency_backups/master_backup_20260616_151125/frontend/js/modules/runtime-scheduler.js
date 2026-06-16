/* ============================================================
   Sovereign AI — runtime-scheduler.js
   الإصدار: 7.0.0
   مجدول النظام السيادي
   ============================================================ */

class SovereignRuntimeScheduler {

    constructor() {

        this.tasks = new Map();

        this.running = false;

        this.lastFrame = performance.now();

        console.log(
            '⏱ Runtime Scheduler Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.running = true;

        this.startLoop();
    }

    /* ========================================================
       MAIN LOOP
    ======================================================== */

    startLoop() {

        const loop = (time) => {

            if (!this.running) return;

            const delta =
                time - this.lastFrame;

            this.lastFrame = time;

            this.executeTasks(
                delta
            );

            requestAnimationFrame(loop);
        };

        requestAnimationFrame(loop);
    }

    /* ========================================================
       REGISTER TASK
    ======================================================== */

    registerTask(
        name,
        callback,
        interval = 1000
    ) {

        this.tasks.set(name, {

            callback,

            interval,

            lastRun: 0
        });

        console.log(
            `📌 Task Registered: ${name}`
        );
    }

    /* ========================================================
       EXECUTE
    ======================================================== */

    executeTasks(delta) {

        const now =
            performance.now();

        this.tasks.forEach(
            (task, name) => {

                if (
                    now - task.lastRun >=
                    task.interval
                ) {

                    try {

                        task.callback();

                    } catch (error) {

                        console.error(
                            `Task Failed: ${name}`,
                            error
                        );
                    }

                    task.lastRun = now;
                }
            }
        );
    }

    /* ========================================================
       REMOVE TASK
    ======================================================== */

    removeTask(name) {

        this.tasks.delete(name);
    }

    /* ========================================================
       STOP
    ======================================================== */

    stop() {

        this.running = false;

        console.warn(
            '🛑 Scheduler Stopped'
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            running:
                this.running,

            tasks:
                [...this.tasks.keys()]
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_SCHEDULER =
    new SovereignRuntimeScheduler();
