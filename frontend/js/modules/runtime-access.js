/* ============================================================
   Sovereign AI — runtime-access.js
   الإصدار: 8.0.0
   طبقة الوصول السيادية
   ============================================================ */

class SovereignRuntimeAccess {

    constructor() {

        console.log(
            '🔑 Runtime Access Layer Initialized'
        );
    }

    /* ========================================================
       CORE
    ======================================================== */

    kernel() {

        return window.SOVEREIGN
            ?.get('kernel');
    }

    scheduler() {

        return window.SOVEREIGN
            ?.get('scheduler');
    }

    /* ========================================================
       COMMUNICATION
    ======================================================== */

    bus() {

        return window.SOVEREIGN
            ?.get('bus');
    }

    events() {

        return window.SOVEREIGN
            ?.get('events');
    }

    /* ========================================================
       INTELLIGENCE
    ======================================================== */

    intelligence() {

        return window.SOVEREIGN
            ?.get('intelligence');
    }

    analytics() {

        return window.SOVEREIGN
            ?.get('analytics');
    }

    orchestrator() {

        return window.SOVEREIGN
            ?.get('orchestrator-ai');
    }

    /* ========================================================
       SYSTEMS
    ======================================================== */

    cache() {

        return window.SOVEREIGN
            ?.get('cache');
    }

    security() {

        return window.SOVEREIGN
            ?.get('security');
    }

    persistence() {

        return window.SOVEREIGN
            ?.get('persistence');
    }

    resources() {

        return window.SOVEREIGN
            ?.get('resources');
    }

    health() {

        return window.SOVEREIGN
            ?.get('health');
    }

    /* ========================================================
       STATUS
    ======================================================== */

    status() {

        return {

            registry:
                !!window.SOVEREIGN,

            systems:
                window.SOVEREIGN
                    ?.status()
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignAccess =
    new SovereignRuntimeAccess();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_ACCESS =
    sovereignAccess;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'access',
        sovereignAccess
    );
