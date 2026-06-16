/* ============================================================
   Sovereign AI — runtime-trace-engine.js
   الإصدار: 8.0.0
   محرك التتبع السيادي
   ============================================================ */

class SovereignRuntimeTraceEngine {

    constructor() {

        this.traces = [];

        this.maxTraces = 5000;

        console.log(
            '🧬 Runtime Trace Engine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindBus();

        this.publishReady();
    }

    /* ========================================================
       BIND BUS
    ======================================================== */

    bindBus() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (!bus) {

            console.warn(
                '⚠️ Trace Engine Missing Bus'
            );

            return;
        }

        /* =========================================
           TRACE ALL MAJOR CHANNELS
        ========================================= */

        const channels = [

            'analytics:capture',

            'intelligence:state:changed',

            'policy:activated',

            'health:update',

            'runtime:errors'
        ];

        channels.forEach(channel => {

            bus.subscribe(
                channel,
                (message) => {

                    this.recordTrace(
                        message
                    );
                }
            );
        });
    }

    /* ========================================================
       RECORD TRACE
    ======================================================== */

    recordTrace(message) {

        const trace = {

            id:
                message.id,

            traceId:
                message.meta
                    ?.context
                    ?.traceId,

            sessionId:
                message.meta
                    ?.context
                    ?.sessionId,

            channel:
                message.channel,

            type:
                message.type,

            source:
                message.source,

            timestamp:
                message.timestamp,

            context:
                message.meta
                    ?.context
        };

        this.traces.push(trace);

        if (
            this.traces.length >
            this.maxTraces
        ) {

            this.traces.shift();
        }

        console.log(
            `
🧬 Runtime Trace Recorded
Channel:
${trace.channel}

Trace:
${trace.traceId}
            `
        );
    }

    /* ========================================================
       GET TRACE
    ======================================================== */

    getTrace(traceId) {

        return this.traces.filter(

            trace =>

                trace.traceId ===
                traceId
        );
    }

    /* ========================================================
       GET SESSION TRACES
    ======================================================== */

    getSessionTraces(sessionId) {

        return this.traces.filter(

            trace =>

                trace.sessionId ===
                sessionId
        );
    }

    /* ========================================================
       TIMELINE
    ======================================================== */

    buildTimeline(traceId) {

        return this.getTrace(traceId)

            .sort(
                (a, b) =>
                    a.timestamp -
                    b.timestamp
            );
    }

    /* ========================================================
       EXPORT
    ======================================================== */

    exportTraces() {

        const blob =
            new Blob(

                [
                    JSON.stringify(
                        this.traces,
                        null,
                        2
                    )
                ],

                {
                    type:
                        'application/json'
                }
            );

        const url =
            URL.createObjectURL(
                blob
            );

        const link =
            document.createElement('a');

        link.href =
            url;

        link.download =
            `runtime-traces-${Date.now()}.json`;

        link.click();

        URL.revokeObjectURL(
            url
        );

        window.SOVEREIGN_ACCESS
            ?.notify?.()
            ?.success(
                'Runtime Traces Exported'
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
            'trace:ready',
            {

                maxTraces:
                    this.maxTraces,

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

            traces:
                this.traces.length,

            maxTraces:
                this.maxTraces
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignTraceEngine =
    new SovereignRuntimeTraceEngine();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_TRACE =
    sovereignTraceEngine;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'trace-engine',
        sovereignTraceEngine
    );
