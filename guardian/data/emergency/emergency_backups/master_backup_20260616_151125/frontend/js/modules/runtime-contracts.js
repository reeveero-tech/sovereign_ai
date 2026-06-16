/* ============================================================
   Sovereign AI — runtime-contracts.js
   الإصدار: 8.0.0
   عقود التشغيل السيادية
   ============================================================ */

class SovereignRuntimeContracts {

    constructor() {

        this.contracts = new Map();

        console.log(
            '📘 Runtime Contracts Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerCoreContracts();

        this.publishReady();
    }

    /* ========================================================
       REGISTER CORE
    ======================================================== */

    registerCoreContracts() {

        /* =========================================
           ANALYTICS
        ========================================= */

        this.register(

            'analytics.capture',

            {
                payload: {

                    timestamp: 'number',

                    fps: 'number',

                    health: 'number',

                    runtimeState: 'string'
                },

                source:
                    'runtime-analytics'
            }
        );

        /* =========================================
           INTELLIGENCE
        ========================================= */

        this.register(

            'intelligence.state.change',

            {
                payload: {

                    previous: 'string',

                    current: 'string',

                    score: 'number'
                },

                source:
                    'runtime-intelligence'
            }
        );

        /* =========================================
           HEALTH
        ========================================= */

        this.register(

            'health.update',

            {
                payload: {

                    globalHealth:
                        'number'
                },

                source:
                    'runtime-health-matrix'
            }
        );

        /* =========================================
           POLICY
        ========================================= */

        this.register(

            'policy.activation',

            {
                payload: {

                    policy:
                        'string',

                    reason:
                        'string'
                },

                source:
                    'runtime-policy-engine'
            }
        );
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    register(
        name,
        schema
    ) {

        this.contracts.set(

            name,

            {
                ...schema,

                registeredAt:
                    Date.now()
            }
        );

        console.log(
            `📘 Contract Registered: ${name}`
        );
    }

    /* ========================================================
       VALIDATE
    ======================================================== */

    validate(
        contractName,
        payload
    ) {

        const contract =
            this.contracts.get(
                contractName
            );

        if (!contract) {

            console.warn(
                `⚠️ Contract Missing: ${contractName}`
            );

            return false;
        }

        const schema =
            contract.payload;

        for (
            const key in schema
        ) {

            const expected =
                schema[key];

            const actual =
                typeof payload[key];

            if (
                actual !== expected
            ) {

                console.warn(
                    `
⚠️ Contract Validation Failed
Contract: ${contractName}
Field: ${key}
Expected: ${expected}
Actual: ${actual}
                    `
                );

                return false;
            }
        }

        return true;
    }

    /* ========================================================
       GET
    ======================================================== */

    get(contractName) {

        return this.contracts.get(
            contractName
        );
    }

    /* ========================================================
       LIST
    ======================================================== */

    list() {

        return [
            ...this.contracts.keys()
        ];
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publish(
            'contracts:ready',
            {
                contracts:
                    this.contracts.size,

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

            contracts:
                this.contracts.size,

            list:
                this.list()
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignContracts =
    new SovereignRuntimeContracts();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_CONTRACTS =
    sovereignContracts;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'contracts',
        sovereignContracts
    );
