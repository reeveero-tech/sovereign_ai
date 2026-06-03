/* ============================================================
   Sovereign AI — runtime-cache.js
   الإصدار: 7.0.0
   طبقة التخزين السيادية
   ============================================================ */

class SovereignRuntimeCache {

    constructor() {

        this.cache = new Map();

        this.maxEntries = 200;

        console.log(
            '🧠 Runtime Cache Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.startCleanupCycle();
    }

    /* ========================================================
       SET
    ======================================================== */

    set(
        key,
        value,
        ttl = 60000
    ) {

        if (
            this.cache.size >=
            this.maxEntries
        ) {

            this.evictOldest();
        }

        this.cache.set(key, {

            value,

            expires:
                Date.now() + ttl,

            created:
                Date.now()
        });
    }

    /* ========================================================
       GET
    ======================================================== */

    get(key) {

        const item =
            this.cache.get(key);

        if (!item) return null;

        if (
            Date.now() >
            item.expires
        ) {

            this.cache.delete(key);

            return null;
        }

        return item.value;
    }

    /* ========================================================
       HAS
    ======================================================== */

    has(key) {

        return this.get(key) !== null;
    }

    /* ========================================================
       DELETE
    ======================================================== */

    delete(key) {

        this.cache.delete(key);
    }

    /* ========================================================
       CLEAR
    ======================================================== */

    clear() {

        this.cache.clear();

        console.log(
            '🧹 Runtime Cache Cleared'
        );
    }

    /* ========================================================
       EVICT
    ======================================================== */

    evictOldest() {

        const oldest =
            [...this.cache.entries()]
                .sort(
                    (a, b) =>
                        a[1].created -
                        b[1].created
                )[0];

        if (oldest) {

            this.cache.delete(
                oldest[0]
            );
        }
    }

    /* ========================================================
       CLEANUP
    ======================================================== */

    startCleanupCycle() {

        const scheduler =
            window.SOVEREIGN_SCHEDULER;

        if (!scheduler) return;

        scheduler.registerTask(

            'runtime-cache-cleanup',

            () => {

                const now =
                    Date.now();

                this.cache.forEach(
                    (item, key) => {

                        if (
                            now >
                            item.expires
                        ) {

                            this.cache.delete(
                                key
                            );
                        }
                    }
                );

            },

            30000
        );
    }

    /* ========================================================
       STATS
    ======================================================== */

    getStats() {

        return {

            entries:
                this.cache.size,

            maxEntries:
                this.maxEntries
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_CACHE =
    new SovereignRuntimeCache();
