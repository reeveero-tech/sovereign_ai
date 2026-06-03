/* ============================================================
   Sovereign AI — runtime-unified-registry.js
   الإصدار: 8.0.0
   السجل السيادي الموحد
   ============================================================ */

class SovereignUnifiedRegistry {

    constructor() {

        this.systems = new Map();

        console.log(
            '🧬 Unified Runtime Registry Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        window.SOVEREIGN = this;
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    register(
        name,
        instance
    ) {

        if (
            this.systems.has(name)
        ) {

            console.warn(
                `⚠️ System already registered: ${name}`
            );
        }

        this.systems.set(
            name,
            instance
        );

        console.log(
            `✅ Unified System Registered: ${name}`
        );
    }

    /* ========================================================
       GET
    ======================================================== */

    get(name) {

        return this.systems.get(name);
    }

    /* ========================================================
       HAS
    ======================================================== */

    has(name) {

        return this.systems.has(name);
    }

    /* ========================================================
       REMOVE
    ======================================================== */

    remove(name) {

        this.systems.delete(name);

        console.warn(
            `⚠️ Unified System Removed: ${name}`
        );
    }

    /* ========================================================
       LIST
    ======================================================== */

    list() {

        return [
            ...this.systems.keys()
        ];
    }

    /* ========================================================
       STATUS
    ======================================================== */

    status() {

        return {

            systems:
                this.list(),

            total:
                this.systems.size
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN =
    new SovereignUnifiedRegistry();
