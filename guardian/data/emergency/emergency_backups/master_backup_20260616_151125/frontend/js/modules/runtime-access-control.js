/* ============================================================
   Sovereign AI — runtime-access-control.js
   الإصدار: 8.0.0
   التحكم بالوصول السيادي
   ============================================================ */

class SovereignRuntimeAccessControl {

    constructor() {

        this.permissions = new Map();

        console.log(
            '🔐 Runtime Access Control Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerDefaultPermissions();

        this.publishReady();
    }

    /* ========================================================
       DEFAULT PERMISSIONS
    ======================================================== */

    registerDefaultPermissions() {

        this.allow(

            'analytics-domain',

            [

                'telemetry.read',

                'telemetry.write'
            ]
        );

        this.allow(

            'security-domain',

            [

                'security.validate',

                'security.enforce'
            ]
        );

        this.allow(

            'transport-domain',

            [

                'transport.publish',

                'transport.subscribe'
            ]
        );

        this.allow(

            'governance-domain',

            [

                'policy.enforce',

                'runtime.control'
            ]
        );
    }

    /* ========================================================
       ALLOW
    ======================================================== */

    allow(
        domain,
        permissions = []
    ) {

        this.permissions.set(
            domain,
            new Set(permissions)
        );

        console.log(
            `
🔐 Permissions Granted
Domain:
${domain}
            `
        );
    }

    /* ========================================================
       CHECK
    ======================================================== */

    check(
        domain,
        permission
    ) {

        return this.permissions
            .get(domain)
            ?.has(permission)
            || false;
    }

    /* ========================================================
       GRANT
    ======================================================== */

    grant(
        domain,
        permission
    ) {

        if (
            !this.permissions.has(domain)
        ) {

            this.permissions.set(
                domain,
                new Set()
            );
        }

        this.permissions
            .get(domain)
            .add(permission);
    }

    /* ========================================================
       REVOKE
    ======================================================== */

    revoke(
        domain,
        permission
    ) {

        this.permissions
            .get(domain)
            ?.delete(permission);
    }

    /* ========================================================
       LIST
    ======================================================== */

    listPermissions(domain) {

        return [

            ...(
                this.permissions
                    .get(domain)
                || []
            )
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
            'access-control:ready',
            {

                domains:
                    this.permissions.size,

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

            domains:
                this.permissions.size
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignAccessControl =
    new SovereignRuntimeAccessControl();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_ACL =
    sovereignAccessControl;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'access-control',
        sovereignAccessControl
    );
