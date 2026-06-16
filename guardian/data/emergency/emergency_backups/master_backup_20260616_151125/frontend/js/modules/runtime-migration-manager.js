/* ============================================================
   Sovereign AI — runtime-migration-manager.js
   الإصدار: 8.0.0
   مدير الهجرة السيادي
   ============================================================ */

class SovereignRuntimeMigrationManager {

    constructor() {

        this.migrations = [];

        this.completed = [];

        console.log(
            '🔄 Runtime Migration Manager Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.registerDefaultMigrations();

        this.runMigrations();
    }

    /* ========================================================
       DEFAULT MIGRATIONS
    ======================================================== */

    registerDefaultMigrations() {

        this.registerMigration({

            name:
                'kernel-registry-sync',

            execute: () => {

                if (
                    window.SOVEREIGN_KERNEL &&
                    window.SOVEREIGN?.register
                ) {

                    window.SOVEREIGN.register(

                        'kernel',

                        window.SOVEREIGN_KERNEL
                    );
                }
            }
        });

        this.registerMigration({

            name:
                'bus-registry-sync',

            execute: () => {

                if (
                    window.SOVEREIGN_BUS &&
                    window.SOVEREIGN?.register
                ) {

                    window.SOVEREIGN.register(

                        'bus',

                        window.SOVEREIGN_BUS
                    );
                }
            }
        });

        this.registerMigration({

            name:
                'events-registry-sync',

            execute: () => {

                if (
                    window.SOVEREIGN_EVENTS &&
                    window.SOVEREIGN?.register
                ) {

                    window.SOVEREIGN.register(

                        'events',

                        window.SOVEREIGN_EVENTS
                    );
                }
            }
        });

        this.registerMigration({

            name:
                'cache-registry-sync',

            execute: () => {

                if (
                    window.SOVEREIGN_CACHE &&
                    window.SOVEREIGN?.register
                ) {

                    window.SOVEREIGN.register(

                        'cache',

                        window.SOVEREIGN_CACHE
                    );
                }
            }
        });
    }

    /* ========================================================
       REGISTER
    ======================================================== */

    registerMigration(
        migration
    ) {

        this.migrations.push(
            migration
        );

        console.log(
            `📦 Migration Registered: ${migration.name}`
        );
    }

    /* ========================================================
       RUN
    ======================================================== */

    runMigrations() {

        this.migrations.forEach(
            migration => {

                try {

                    migration.execute();

                    this.completed.push(
                        migration.name
                    );

                    console.log(
                        `✅ Migration Completed: ${migration.name}`
                    );

                } catch (error) {

                    console.error(
                        `❌ Migration Failed: ${migration.name}`,
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

            total:
                this.migrations.length,

            completed:
                this.completed
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignMigrationManager =
    new SovereignRuntimeMigrationManager();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_MIGRATION =
    sovereignMigrationManager;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'migration-manager',
        sovereignMigrationManager
    );
