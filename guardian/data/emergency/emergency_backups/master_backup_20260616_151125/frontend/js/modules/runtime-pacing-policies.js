/* ============================================================
   Sovereign AI — runtime-pacing-policies.js
   الإصدار: 8.0.0
   سياسات الإيقاع السيادية
   ============================================================ */

class SovereignRuntimePacingPolicies {

    constructor() {

        this.mode =
            'normal';

        this.policies =
            new Map();

        console.log(
            '🎛 Runtime Pacing Policies Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerDefaultPolicies();

        this.bindBackpressure();

        this.publishReady();
    }

    /* ========================================================
       DEFAULT POLICIES
    ======================================================== */

    registerDefaultPolicies() {

        this.registerPolicy({

            id:
                'critical-tasks',

            channels: [

                'runtime:errors',

                'scheduler:task:failed'
            ],

            bypass:
                true,

            delay:
                0
        });

        this.registerPolicy({

            id:
                'analytics-flow',

            channels: [

                'analytics:capture'
            ],

            bypass:
                false,

            delay:
                100
        });

        this.registerPolicy({

            id:
                'governance-flow',

            channels: [

                'policy:activated'
            ],

            bypass:
                false,

            delay:
                50
        });
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    registerPolicy({

        id,

        channels = [],

        bypass = false,

        delay = 0
    }) {

        this.policies.set(

            id,

            {

                id,

                channels,

                bypass,

                delay,

                createdAt:
                    Date.now()
            }
        );

        console.log(
            `
🎛 Pacing Policy Registered
Policy:
${id}
            `
        );
    }

    /* ========================================================
       BIND BACKPRESSURE
    ======================================================== */

    bindBackpressure() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (!bus) {

            return;
        }

        bus.subscribe(

            'scheduler:mode:changed',

            (message) => {

                this.mode =
                    message.payload
                        ?.current
                    ||
                    'normal';
            }
        );
    }

    /* ========================================================
       GET POLICY
    ======================================================== */

    getPolicy(channel) {

        for (
            const policy
            of this.policies.values()
        ) {

            if (
                policy.channels.includes(
                    channel
                )
            ) {

                return policy;
            }
        }

        return null;
    }

    /* ========================================================
       GET DELAY
    ======================================================== */

    getDelay(channel) {

        const policy =
            this.getPolicy(
                channel
            );

        if (!policy) {

            return 0;
        }

        if (
            policy.bypass
        ) {

            return 0;
        }

        switch (
            this.mode
        ) {

            case 'critical':

                return (
                    policy.delay * 4
                );

            case 'degraded':

                return (
                    policy.delay * 2
                );

            case 'elevated':

                return (
                    policy.delay
                );

            default:

                return 0;
        }
    }

    /* ========================================================
       SHOULD BYPASS
    ======================================================== */

    shouldBypass(channel) {

        const policy =
            this.getPolicy(
                channel
            );

        return (
            policy?.bypass
            || false
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

                'pacing:ready',

                {

                    policies:
                        this.policies.size,

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

            mode:
                this.mode,

            policies:
                this.policies.size
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignPacingPolicies =
    new SovereignRuntimePacingPolicies();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_PACING =
    sovereignPacingPolicies;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'pacing-policies',
        sovereignPacingPolicies
    );
