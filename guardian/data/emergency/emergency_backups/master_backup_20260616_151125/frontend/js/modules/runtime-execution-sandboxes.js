/* ============================================================
   Sovereign AI — runtime-execution-sandboxes.js
   الإصدار: 8.0.0
   صناديق التنفيذ السيادية
   ============================================================ */

class SovereignRuntimeExecutionSandboxes {

    constructor() {

        this.sandboxes = new Map();

        console.log(
            '📦 Runtime Execution Sandboxes Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerCoreSandboxes();

        this.publishReady();
    }

    /* ========================================================
       REGISTER CORE
    ======================================================== */

    registerCoreSandboxes() {

        this.registerSandbox({

            id:
                'analytics-sandbox',

            domain:
                'analytics-domain',

            limits: {

                maxMessages:
                    500,

                maxExecutionTime:
                    50
            }
        });

        this.registerSandbox({

            id:
                'transport-sandbox',

            domain:
                'transport-domain',

            limits: {

                maxMessages:
                    2000,

                maxExecutionTime:
                    10
            }
        });

        this.registerSandbox({

            id:
                'governance-sandbox',

            domain:
                'governance-domain',

            limits: {

                maxMessages:
                    1000,

                maxExecutionTime:
                    25
            }
        });
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    registerSandbox({

        id,

        domain,

        limits = {}
    }) {

        this.sandboxes.set(

            id,

            {

                id,

                domain,

                limits,

                metrics: {

                    messages:
                        0,

                    violations:
                        0
                },

                state:
                    'active',

                createdAt:
                    Date.now()
            }
        );

        console.log(
            `
📦 Sandbox Registered
Sandbox:
${id}
            `
        );
    }

    /* ========================================================
       TRACK MESSAGE
    ======================================================== */

    trackMessage(domain) {

        const sandbox =
            this.findSandbox(
                domain
            );

        if (!sandbox) {

            return;
        }

        sandbox.metrics.messages++;

        /* =========================================
           LIMIT CHECK
        ========================================= */

        if (
            sandbox.metrics.messages >
            sandbox.limits.maxMessages
        ) {

            sandbox.metrics.violations++;

            sandbox.state =
                'throttled';

            console.warn(
                `
⚠️ Sandbox Throttled
Sandbox:
${sandbox.id}
                `
            );

            this.publishViolation(
                sandbox
            );
        }
    }

    /* ========================================================
       FIND
    ======================================================== */

    findSandbox(domain) {

        for (
            const sandbox
            of this.sandboxes.values()
        ) {

            if (
                sandbox.domain ===
                domain
            ) {

                return sandbox;
            }
        }

        return null;
    }

    /* ========================================================
       CHECK
    ======================================================== */

    isAllowed(domain) {

        const sandbox =
            this.findSandbox(
                domain
            );

        if (!sandbox) {

            return true;
        }

        return (
            sandbox.state ===
            'active'
        );
    }

    /* ========================================================
       RESET
    ======================================================== */

    resetSandbox(sandboxId) {

        const sandbox =
            this.sandboxes.get(
                sandboxId
            );

        if (!sandbox) {

            return;
        }

        sandbox.metrics.messages =
            0;

        sandbox.metrics.violations =
            0;

        sandbox.state =
            'active';

        console.log(
            `
✅ Sandbox Reset
Sandbox:
${sandboxId}
            `
        );
    }

    /* ========================================================
       VIOLATION
    ======================================================== */

    publishViolation(sandbox) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publishWithoutMiddleware?.(
            'sandbox:violation',
            {

                sandbox:
                    sandbox.id,

                domain:
                    sandbox.domain,

                violations:
                    sandbox.metrics.violations,

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

        bus?.publishWithoutMiddleware?.(
            'sandbox:ready',
            {

                sandboxes:
                    this.sandboxes.size,

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

            sandboxes:
                this.sandboxes.size,

            list:
                [
                    ...this.sandboxes.values()
                ]
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignSandboxes =
    new SovereignRuntimeExecutionSandboxes();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_SANDBOX =
    sovereignSandboxes;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'execution-sandboxes',
        sovereignSandboxes
    );
