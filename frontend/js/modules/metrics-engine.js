/* ============================================================
   Sovereign AI — metrics-engine.js
   الإصدار: 5.0.0
   محرك المقاييس العصبي
   ============================================================ */

class SovereignMetricsEngine {

    constructor() {

        this.metrics = {

            fps: 60,

            cycles: 0,

            latency: 0,

            memory: 0,

            coherence: 100,

            fieldEnergy: 0
        };

        this.initialized = false;

        console.log(
            '📊 Metrics Engine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindPerformance();

        this.startRealtimeUpdates();

        this.initialized = true;
    }

    /* ========================================================
       PERFORMANCE
    ======================================================== */

    bindPerformance() {

        if (
            window.SOVEREIGN_CORE
        ) {

            window.SOVEREIGN_CORE.on(
                'performance:stable',
                () => {

                    this.updateMetric(
                        'coherence',
                        100
                    );
                }
            );

            window.SOVEREIGN_CORE.on(
                'performance:degraded',
                () => {

                    this.updateMetric(
                        'coherence',
                        75
                    );
                }
            );

            window.SOVEREIGN_CORE.on(
                'performance:critical',
                () => {

                    this.updateMetric(
                        'coherence',
                        40
                    );
                }
            );
        }
    }

    /* ========================================================
       UPDATE METRIC
    ======================================================== */

    updateMetric(
        key,
        value
    ) {

        this.metrics[key] = value;

        this.renderMetric(
            key,
            value
        );

        if (
            window.SOVEREIGN_STATE
        ) {

            window.SOVEREIGN_STATE.mergeState(
                'metrics',
                this.metrics
            );
        }
    }

    /* ========================================================
       RENDER METRIC
    ======================================================== */

    renderMetric(
        key,
        value
    ) {

        const render =
            window.SOVEREIGN_RENDER;

        if (!render) return;

        /* R-730: الدورات ملك main.js من /status، والطاقة غير مربوطة —
           هذا المحرك يكتب FPS المحلي فقط (LIVE_BINDINGS.json). */
        const map = {

            fps:
                'metric-fps'
        };

        const target =
            map[key];

        if (!target) return;

        render.updateText(
            target,
            value
        );
    }

    /* ========================================================
       REALTIME LOOP
    ======================================================== */

    startRealtimeUpdates() {

        const loop = () => {

            this.generateLiveMetrics();

            requestAnimationFrame(
                loop
            );
        };

        loop();
    }

    /* ========================================================
       LIVE METRICS
    ======================================================== */

    generateLiveMetrics() {

        /* R-730 (البند ١.٤): FPS فقط — قياس محلي حقيقي من محرك الحركة.
           أزيل: عدّاد الإطارات المتزايد كل إطار الذي كان يُعرض كـ«دورات النظام»
           ويطغى على total_cycles الحقيقي من /status، و«طاقة الحقل» من موجة
           جيبية. ولا 60 افتراضية عند غياب المحرك — لا رقم بلا قياس. */

        const fps =
            window.SOVEREIGN_ANIMATION_ENGINE
                ?.fps;

        if (typeof fps !== 'number') return;

        this.metrics.fps = fps;

        this.renderMetric(
            'fps',
            fps
        );
    }

    /* ========================================================
       GET METRICS
    ======================================================== */

    getMetrics() {

        return this.metrics;
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_METRICS =
    new SovereignMetricsEngine();
