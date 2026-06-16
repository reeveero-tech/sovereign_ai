/* ============================================================
   Sovereign AI — legacy-cleanup.js
   الإصدار: 6.0.0
   تنظيف النظام القديم
   ============================================================ */

class SovereignLegacyCleanup {

    constructor() {

        console.log(
            '🧹 Legacy Cleanup Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.disableLegacyHandlers();

        this.preventDuplicateBindings();

        this.markLegacyLayer();

        this.cleanupIntervals();
    }

    /* ========================================================
       LEGACY HANDLERS
    ======================================================== */

    disableLegacyHandlers() {

        /* =========================================
           تعطيل الدوال القديمة الخطيرة
        ========================================= */

        if (
            window.sendMessage
        ) {

            console.warn(
                '⚠️ Legacy sendMessage disabled'
            );

            window.sendMessage = () => {};
        }

        if (
            window.handleChatSubmit
        ) {

            console.warn(
                '⚠️ Legacy handleChatSubmit disabled'
            );

            window.handleChatSubmit = () => {};
        }

        if (
            window.initializeTabs
        ) {

            console.warn(
                '⚠️ Legacy initializeTabs disabled'
            );

            window.initializeTabs = () => {};
        }
    }

    /* ========================================================
       DUPLICATE BINDINGS
    ======================================================== */

    preventDuplicateBindings() {

        const buttons = [

            'btn-send-chat',

            'btn-send-sir-command'
        ];

        buttons.forEach(id => {

            const element =
                document.getElementById(id);

            if (!element) return;

            element.dataset.runtimeBound =
                'true';
        });
    }

    /* ========================================================
       LEGACY MARK
    ======================================================== */

    markLegacyLayer() {

        document.body.dataset.legacy =
            'controlled';
    }

    /* ========================================================
       INTERVAL CLEANUP
    ======================================================== */

    cleanupIntervals() {

        console.log(
            '🧠 Runtime Cleanup Active'
        );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_LEGACY =
    new SovereignLegacyCleanup();
