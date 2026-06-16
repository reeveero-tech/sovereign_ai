/* ============================================================
   Sovereign AI — runtime-dependency-graph.js
   الإصدار: 7.0.0
   مخطط الاعتماد السيادي
   ============================================================ */

class SovereignRuntimeDependencyGraph {

    constructor() {

        this.graph = new Map();

        console.log(
            '🕸 Runtime Dependency Graph Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.buildGraph();

        this.publishGraphReady();
    }

    /* ========================================================
       BUILD GRAPH
    ======================================================== */

    buildGraph() {

        this.addNode(
            'runtime-kernel',
            []
        );

        this.addNode(
            'runtime-scheduler',
            [
                'runtime-kernel'
            ]
        );

        this.addNode(
            'runtime-intelligence',
            [
                'runtime-kernel',
                'runtime-analytics'
            ]
        );

        this.addNode(
            'runtime-orchestrator-ai',
            [
                'runtime-intelligence',
                'runtime-policy-engine'
            ]
        );

        this.addNode(
            'runtime-policy-engine',
            [
                'runtime-resource-manager',
                'runtime-security'
            ]
        );

        this.addNode(
            'runtime-state-replicator',
            [
                'runtime-bus',
                'runtime-cache'
            ]
        );

        this.addNode(
            'runtime-middleware',
            [
                'runtime-bus',
                'runtime-security'
            ]
        );
    }

    /* ========================================================
       ADD NODE
    ======================================================== */

    addNode(
        name,
        dependencies = []
    ) {

        this.graph.set(

            name,

            {
                dependencies,

                createdAt:
                    Date.now()
            }
        );

        console.log(
            `🧩 Dependency Registered: ${name}`
        );
    }

    /* ========================================================
       GET NODE
    ======================================================== */

    getNode(name) {

        return this.graph.get(name);
    }

    /* ========================================================
       GET DEPENDENCIES
    ======================================================== */

    getDependencies(name) {

        return (
            this.graph.get(name)
                ?.dependencies || []
        );
    }

    /* ========================================================
       CHECK CIRCULAR
    ======================================================== */

    hasCircularDependency() {

        const visited =
            new Set();

        const stack =
            new Set();

        const visit = (node) => {

            if (
                stack.has(node)
            ) {

                return true;
            }

            if (
                visited.has(node)
            ) {

                return false;
            }

            visited.add(node);

            stack.add(node);

            const dependencies =
                this.getDependencies(node);

            for (
                const dependency
                of dependencies
            ) {

                if (
                    visit(dependency)
                ) {

                    return true;
                }
            }

            stack.delete(node);

            return false;
        };

        for (
            const node
            of this.graph.keys()
        ) {

            if (
                visit(node)
            ) {

                return true;
            }
        }

        return false;
    }

    /* ========================================================
       TOPOLOGY
    ======================================================== */

    getTopology() {

        return [
            ...this.graph.entries()
        ].map(
            ([name, config]) => ({

                name,

                dependencies:
                    config.dependencies
            })
        );
    }

    /* ========================================================
       READY
    ======================================================== */

    publishGraphReady() {

        window.SOVEREIGN_BUS
            ?.publish(
                'system',
                {
                    type:
                        'dependency-graph-ready',

                    nodes:
                        this.graph.size
                }
            );
    }

    /* ========================================================
       STATUS
    ======================================================== */

    getStatus() {

        return {

            nodes:
                this.graph.size,

            circular:
                this.hasCircularDependency()
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_DEPENDENCIES =
    new SovereignRuntimeDependencyGraph();
