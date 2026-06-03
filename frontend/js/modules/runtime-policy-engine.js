/* ============================================================
   Sovereign AI — runtime-policy-engine.js
   الإصدار: 7.0.0
   محرك السياسات السيادي
   ============================================================ */

class SovereignRuntimePolicyEngine {

    constructor() {

        this.policies = new Map();

        console.log(
            '📜 Runtime Policy Engine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerDefaultPolicies();

        this.startPolicyEvaluation();
    }

    /* ========================================================
       DEFAULT POLICIES
    ======================================================== */

    registerDefaultPolicies() {

        /* =========================================
           PERFORMANCE POLICY
        ========================================= */

        this.registerPolicy(

            'performance-protection',

            () => {

                const kernel =
                    window.SOVEREIGN_KERNEL
                        ?.getStatus();

                return (
                    kernel &&
                    kernel.health < 50
                );
            },

            () => {

                document.body.classList.add(
                    'runtime-safe'
                );

                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'Performance Protection Policy Activated'
                    );
            }
        );

        /* =========================================
           RESOURCE POLICY
        ========================================= */

        this.registerPolicy(

            'resource-limiter',

            () => {

                const resources =
                    window.SOVEREIGN_RESOURCES
                        ?.getStatus();

                return (
                    resources &&
                    resources.pressure > 40
                );
            },

            () => {

                document.body.classList.add(
                    'runtime-low-effects'
                );
            }
        );

        /* =========================================
           SECURITY POLICY
        ========================================= */

        this.registerPolicy(

            'security-hardening',

            () => {

                const recovery =
                    window.SOVEREIGN_RECOVERY
                        ?.getStatus();

                return (
                    recovery &&
                    recovery.attempts > 2
                );
            },

            () => {

                document.body.classList.add(
                    'runtime-secure'
                );

                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'Security Hardening Enabled'
                    );
            }
        );
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    registerPolicy(
        name,
        condition,
        action
    ) {

        this.policies.set(name, {

            condition,

            action,

            active: false
        });

        console.log(
            `📜 Policy Registered: ${name}`
        );
    }

    /* ========================================================
       EVALUATION LOOP
    ======================================================== */

    startPolicyEvaluation() {

        const scheduler =
            window.SOVEREIGN_SCHEDULER;

        if (!scheduler) {

            console.warn(
                'Scheduler Missing'
            );

            return;
        }

        scheduler.registerTask(

            'runtime-policy-engine',

            () => {

                this.evaluatePolicies();

            },

            5000
        );
    }

    /* ========================================================
       EVALUATE
    ======================================================== */

    evaluatePolicies() {

        this.policies.forEach(
            (policy, name) => {

                try {

                    const shouldActivate =
                        policy.condition();

                    if (
                        shouldActivate &&
                        !policy.active
                    ) {

                        policy.active = true;

                        policy.action();

                        console.log(
                            `✅ Policy Activated: ${name}`
                        );

                    } else if (
                        !shouldActivate &&
                        policy.active
                    ) {

                        policy.active = false;

                        console.log(
                            `♻️ Policy Released: ${name}`
                        );
                    }

                } catch (error) {

                    console.error(
                        `Policy Error (${name})`,
                        error
                    );
                }
            }
        );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            policies:
                [...this.policies.keys()],

            active:
                [...this.policies.entries()]
                    .filter(
                        ([_, policy]) =>
                            policy.active
                    )
                    .map(
                        ([name]) => name
                    )
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_POLICY =
    new SovereignRuntimePolicyEngine();
