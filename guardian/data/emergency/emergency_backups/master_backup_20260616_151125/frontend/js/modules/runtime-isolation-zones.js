/* ============================================================
   Sovereign AI — runtime-isolation-zones.js
   الإصدار: 8.0.0
   مناطق العزل السيادية
   ============================================================ */

class SovereignRuntimeIsolationZones {

    constructor() {

        this.zones = new Map();

        console.log(
            '🛡 Runtime Isolation Zones Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerCoreZones();

        this.publishReady();
    }

    /* ========================================================
       REGISTER CORE ZONES
    ======================================================== */

    registerCoreZones() {

        this.registerZone({

            id:
                'telemetry-zone',

            domains: [

                'analytics-domain'
            ],

            isolationLevel:
                'medium'
        });

        this.registerZone({

            id:
                'security-zone',

            domains: [

                'security-domain'
            ],

            isolationLevel:
                'high'
        });

        this.registerZone({

            id:
                'transport-zone',

            domains: [

                'transport-domain'
            ],

            isolationLevel:
                'critical'
        });

        this.registerZone({

            id:
                'governance-zone',

            domains: [

                'governance-domain'
            ],

            isolationLevel:
                'high'
        });
    }

    /* ========================================================
       REGISTER ZONE
    ======================================================== */

    registerZone({

        id,

        domains = [],

        isolationLevel =
            'medium'
    }) {

        this.zones.set(

            id,

            {

                id,

                domains,

                isolationLevel,

                state:
                    'active',

                createdAt:
                    Date.now()
            }
        );

        console.log(
            `
🛡 Isolation Zone Registered
Zone:
${id}
            `
        );
    }

    /* ========================================================
       SUSPEND ZONE
    ======================================================== */

    suspendZone(zoneId) {

        const zone =
            this.zones.get(
                zoneId
            );

        if (!zone) {

            return;
        }

        zone.state =
            'suspended';

        zone.suspendedAt =
            Date.now();

        console.warn(
            `
🛑 Isolation Zone Suspended
Zone:
${zoneId}
            `
        );

        this.publishState(
            zoneId,
            'suspended'
        );
    }

    /* ========================================================
       RESUME ZONE
    ======================================================== */

    resumeZone(zoneId) {

        const zone =
            this.zones.get(
                zoneId
            );

        if (!zone) {

            return;
        }

        zone.state =
            'active';

        zone.resumedAt =
            Date.now();

        console.log(
            `
✅ Isolation Zone Resumed
Zone:
${zoneId}
            `
        );

        this.publishState(
            zoneId,
            'active'
        );
    }

    /* ========================================================
       GET ZONE
    ======================================================== */

    getZone(zoneId) {

        return this.zones.get(
            zoneId
        );
    }

    /* ========================================================
       LIST
    ======================================================== */

    listZones() {

        return [
            ...this.zones.values()
        ];
    }

    /* ========================================================
       CHECK DOMAIN
    ======================================================== */

    isDomainAllowed(domain) {

        for (
            const zone
            of this.zones.values()
        ) {

            if (
                zone.domains.includes(
                    domain
                )
            ) {

                return (
                    zone.state ===
                    'active'
                );
            }
        }

        return true;
    }

    /* ========================================================
       PUBLISH STATE
    ======================================================== */

    publishState(
        zoneId,
        state
    ) {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publish(
            'zone:state:changed',
            {

                zoneId,

                state,

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

        bus?.publish(
            'zones:ready',
            {

                zones:
                    this.zones.size,

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

            zones:
                this.zones.size
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignZones =
    new SovereignRuntimeIsolationZones();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_ZONES =
    sovereignZones;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'isolation-zones',
        sovereignZones
    );
