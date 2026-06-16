/* ============================================================
   Sovereign AI — runtime-causality-graph.js
   الإصدار: 8.0.0
   مخطط السببية السيادي
   ============================================================ */

class SovereignRuntimeCausalityGraph {

    constructor() {

        this.graph = new Map();

        console.log(
            '🕸 Runtime Causality Graph Initialized'
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
                '⚠️ Causality Graph Missing Bus'
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

        const context =
            message.meta
                ?.context;

        if (!context) {

            return;
        }

        const traceId =
            context.traceId;

        const parent =
            context.parentTraceId;

        if (
            !this.graph.has(traceId)
        ) {

            this.graph.set(
                traceId,
                {

                    traceId,

                    parent,

                    children:
                        [],

                    channel:
                        message.channel,

                    source:
                        message.source,

                    timestamp:
                        message.timestamp
                }
            );
        }

        /* =========================================
           LINK PARENT
        ========================================= */

        if (
            parent &&
            this.graph.has(parent)
        ) {

            this.graph
                .get(parent)
                .children
                .push(traceId);
        }

        console.log(
            `
🕸 Runtime Causality Updated
Trace:
${traceId}

Parent:
${parent || 'ROOT'}
            `
        );
    }

    /* ========================================================
       GET NODE
    ======================================================== */

    getNode(traceId) {

        return this.graph.get(
            traceId
        );
    }

    /* ========================================================
       GET CHILDREN
    ======================================================== */

    getChildren(traceId) {

        return this.graph
            .get(traceId)
            ?.children || [];
    }

    /* ========================================================
       BUILD TREE
    ======================================================== */

    buildTree(traceId) {

        const node =
            this.getNode(traceId);

        if (!node) {

            return null;
        }

        return {

            ...node,

            children:
                node.children.map(

                    child =>

                        this.buildTree(
                            child
                        )
                )
        };
    }

    /* ========================================================
       EXPORT
    ======================================================== */

    exportGraph() {

        const data =
            [...this.graph.values()];

        const blob =
            new Blob(

                [
                    JSON.stringify(
                        data,
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
            `runtime-causality-${Date.now()}.json`;

        link.click();

        URL.revokeObjectURL(
            url
        );

        window.SOVEREIGN_ACCESS
            ?.notify?.()
            ?.success(
                'Runtime Causality Graph Exported'
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
            'causality:ready',
            {

                nodes:
                    this.graph.size,

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

            nodes:
                this.graph.size
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

const sovereignCausalityGraph =
    new SovereignRuntimeCausalityGraph();

/* =========================================
   Legacy Global
========================================= */

window.SOVEREIGN_CAUSALITY =
    sovereignCausalityGraph;

/* =========================================
   Unified Registry
========================================= */

window.SOVEREIGN
    ?.register(
        'causality-graph',
        sovereignCausalityGraph
    );
