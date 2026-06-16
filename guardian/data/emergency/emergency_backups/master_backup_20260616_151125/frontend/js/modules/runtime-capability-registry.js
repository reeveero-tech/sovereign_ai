/* ============================================================
   Sovereign AI — runtime-capability-registry.js
   الإصدار: 7.0.0
   سجل القدرات السيادي
   ============================================================ */

class SovereignRuntimeCapabilityRegistry {

    constructor() {

        this.capabilities = new Map();

        console.log(
            '📚 Runtime Capability Registry Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerCoreCapabilities();

        this.publishRegistryReady();
    }

    /* ========================================================
       REGISTER CORE
    ======================================================== */

    registerCoreCapabilities() {

        this.register(

            'runtime-kernel',

            {
                version: '7.0.0',

                status: 'active',

                dependencies: [],

                type: 'core'
            }
        );

        this.register(

            'runtime-intelligence',

            {
                version: '7.0.0',

                status: 'active',

                dependencies: [

                    'runtime-kernel',

                    'runtime-analytics'
                ],

                type: 'intelligence'
            }
        );

        this.register(

            'runtime-security',

            {
                version: '7.0.0',

                status: 'active',

                dependencies: [

                    'runtime-events'
                ],

                type: 'security'
            }
        );

        this.register(

            'runtime-orchestrator-ai',

            {
                version: '7.0.0',

                status: 'active',

                dependencies: [

                    'runtime-intelligence',

                    'runtime-policy-engine'
                ],

                type: 'governance'
            }
        );
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    register(
        name,
        metadata = {}
    ) {

        this.capabilities.set(

            name,

            {
                name,

                registeredAt:
                    Date.now(),

                ...metadata
            }
        );

        console.log(
            `✅ Capability Registered: ${name}`
        );
    }

    /* ========================================================
       GET
    ======================================================== */

    get(name) {

        return this.capabilities.get(
            name
        );
    }

    /* ========================================================
       HAS
    ======================================================== */

    has(name) {

        return this.capabilities.has(
            name
        );
    }

    /* ========================================================
       LIST
    ======================================================== */

    list() {

        return [
            ...this.capabilities.values()
        ];
    }

    /* ========================================================
       REMOVE
    ======================================================== */

    remove(name) {

        this.capabilities.delete(
            name
        );

        console.warn(
            `⚠️ Capability Removed: ${name}`
        );
    }

    /* ========================================================
       READY
    ======================================================== */

    publishRegistryReady() {

        window.SOVEREIGN_BUS
            ?.publish(
                'system',
                {
                    type:
                        'capability-registry-ready',

                    capabilities:
                        this.capabilities.size
                }
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            capabilities:
                this.capabilities.size
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_CAPABILITIES =
    new SovereignRuntimeCapabilityRegistry();
