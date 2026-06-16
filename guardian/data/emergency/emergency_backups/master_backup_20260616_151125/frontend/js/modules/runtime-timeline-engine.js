/* ============================================================
   Sovereign AI — runtime-timeline-engine.js
   الإصدار: 8.0.0
   محرك الخط الزمني السيادي
   ============================================================ */

class SovereignRuntimeTimelineEngine {

    constructor() {

        this.timelines = new Map();

        console.log(
            '🕒 Runtime Timeline Engine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindTraceEngine();

        this.publishReady();
    }

    /* ========================================================
       BIND TRACE ENGINE
    ======================================================== */

    bindTraceEngine() {

        const bus =
            window.SOVEREIGN_ACCESS
                ?.bus?.();

        if (!bus) {

            console.warn(
                '⚠️ Timeline Engine Missing Bus'
            );

            return;
        }

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

                    this.processMessage(
                        message
                    );
                }
            );
        });
    }

    /* ========================================================
       PROCESS
    ======================================================== */

    processMessage(message) {

        const traceId =
            message.meta
                ?.context
                ?.traceId;

        if (!traceId) {

            return;
        }

        if (
            !this.timelines.has(traceId)
        ) {

            this.timelines.set(
                traceId,
                []
            );
        }

        this.timelines
            .get(traceId)
            .push({

                channel:
                    message.channel,

                type:
                    message.type,

                source:
                    message.source,

                timestamp:
                    message.timestamp
            });

        console.log(
            `
🕒 Timeline Updated
Trace:
${traceId}
            `
        );
    }

    /* ========================================================
       GET TIMELINE
    ======================================================== */

    getTimeline(traceId) {

        return this.timelines.get(
            traceId
        ) || [];
    }

    /* ========================================================
       EXPORT
    ======================================================== */

    exportTimeline(traceId) {

        const timeline =
            this.getTimeline(
                traceId
            );

        const blob =
            new Blob(

                [
                    JSON.stringify(
                        timeline,
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
            `timeline-${traceId}.json`;

        link.click();

        URL.revokeObjectURL(
            url
        );

        window.SOVEREIGN_ACCESS
            ?.notify?.()
            ?.success(
                'Timeline Exported'
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            timelines:
                this.timelines.size
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
            'timeline:ready',
            {

                timelines:
                    this.timelines.size,

                timestamp:
                    Date.now()
            }
        );
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignTimelineEngine =
    new SovereignRuntimeTimelineEngine();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_TIMELINE =
    sovereignTimelineEngine;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'timeline-engine',
        sovereignTimelineEngine
    );
