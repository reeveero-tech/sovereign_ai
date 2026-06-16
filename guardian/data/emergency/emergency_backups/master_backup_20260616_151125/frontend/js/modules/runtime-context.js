/* ============================================================
   Sovereign AI — runtime-context.js
   الإصدار: 8.0.0
   السياق التشغيلي السيادي
   ============================================================ */

class SovereignRuntimeContext {

    constructor() {

        this.sessionId =
            crypto.randomUUID();

        this.traceCounter = 0;

        this.environment =
            'runtime';

        this.version =
            '8.0.0';

        console.log(
            '🧭 Runtime Context Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.publishReady();
    }

    /* ========================================================
       CREATE TRACE ID
    ======================================================== */

    createTraceId() {

        this.traceCounter++;

        return `trace-${Date.now()}-${this.traceCounter}`;
    }

    /* ========================================================
       CREATE CONTEXT
    ======================================================== */

    create({

        source = 'unknown',

        scope = 'runtime',

        parentTraceId = null
    } = {}) {

        return {

            sessionId:
                this.sessionId,

            traceId:
                this.createTraceId(),

            parentTraceId,

            source,

            scope,

            environment:
                this.environment,

            version:
                this.version,

            createdAt:
                Date.now()
        };
    }

    /* ========================================================
       ATTACH CONTEXT
    ======================================================== */

    attach(
        message,
        context = {}
    ) {

        if (
            !message.meta
        ) {

            message.meta = {};
        }

        message.meta.context =
            this.create(context);

        return message;
    }

    /* ========================================================
       GET SESSION
    ======================================================== */

    getSession() {

        return {

            sessionId:
                this.sessionId,

            traces:
                this.traceCounter
        };
    }

    /* ========================================================
       READY
    ======================================================== */

    publishReady() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        bus?.publish(
            'context:ready',
            {

                sessionId:
                    this.sessionId,

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

            sessionId:
                this.sessionId,

            traces:
                this.traceCounter,

            environment:
                this.environment
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignContext =
    new SovereignRuntimeContext();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_CONTEXT =
    sovereignContext;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'context',
        sovereignContext
    );
