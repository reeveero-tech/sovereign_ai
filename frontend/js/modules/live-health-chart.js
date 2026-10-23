/**
 * R-733 (توسيع ١.٤ — بأمر المالك): رسم صحة حي من /health الفعلي.
 *
 * - خانة «سلامة المكونات» (#metric-components-health): السليمة/الكل — كل مكون
 *   يُعد من حالته الفعلية components[name].status === "healthy".
 * - اللوحة (#performanceChart): سلسلة زمنية لآخر 30 عينة (كل 10 ثوانٍ):
 *   خط المكونات السليمة + خط زمن استجابة /health المقاس فعلًا بـperformance.now.
 * - فشل الجلب = فجوة معلنة (null) و«غير متصل» — لا نقطة مختلقة ولا تكرار لآخر قيمة.
 * - رسم Canvas 2D مباشر — لا اعتماد على مكتبة خارجية من CDN.
 */
(function () {
    "use strict";

    var MAX_POINTS = 30;
    var INTERVAL_MS = 10000;
    var samples = []; // {t, healthy, total, latency} أو {t, healthy:null, ...} عند الفشل

    function countHealthy(components) {
        var names = Object.keys(components || {});
        var healthy = 0;
        names.forEach(function (n) {
            var c = components[n];
            var status = c && typeof c === "object" ? c.status : c;
            if (status === "healthy") healthy += 1;
        });
        return { healthy: healthy, total: names.length };
    }

    function renderCard(sample) {
        var el = document.getElementById("metric-components-health");
        if (!el) return;
        if (sample.healthy === null) {
            el.textContent = "غير متصل";
        } else {
            el.textContent = sample.healthy + "/" + sample.total;
        }
    }

    function drawLine(ctx, points, x0, y0, w, h, maxV, color) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        var started = false;
        ctx.beginPath();
        points.forEach(function (v, i) {
            var x = x0 + (points.length === 1 ? w : (i / (MAX_POINTS - 1)) * w);
            if (v === null) { // فجوة معلنة: نقطع الخط
                if (started) ctx.stroke();
                ctx.beginPath();
                started = false;
                return;
            }
            var y = y0 + h - (maxV > 0 ? (v / maxV) * h : 0);
            if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
        });
        if (started) ctx.stroke();
    }

    function renderChart() {
        var canvas = document.getElementById("performanceChart");
        if (!canvas || !canvas.getContext) return;
        var width = canvas.clientWidth || canvas.parentNode.clientWidth || 600;
        var height = 180;
        canvas.width = width;
        canvas.height = height;
        var ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, width, height);

        var pad = 28, w = width - pad * 2, h = height - pad * 2;
        ctx.strokeStyle = "rgba(255,255,255,0.15)";
        ctx.strokeRect(pad, pad, w, h);

        var healthy = samples.map(function (s) { return s.healthy; });
        var latency = samples.map(function (s) { return s.latency; });
        var total = samples.reduce(function (m, s) { return Math.max(m, s.total || 0); }, 0);
        var maxLat = latency.reduce(function (m, v) { return v === null ? m : Math.max(m, v); }, 0);

        drawLine(ctx, healthy, pad, pad, w, h, total, "#2ee6a6");
        drawLine(ctx, latency, pad, pad, w, h, maxLat * 1.2, "#7aa2ff");

        var last = samples[samples.length - 1];
        ctx.fillStyle = "#cfd8ff";
        ctx.font = "12px sans-serif";
        ctx.textAlign = "right";
        if ("direction" in ctx) ctx.direction = "rtl"; // نص عربي — اتجاه صحيح للأرقام والرموز
        ctx.fillText(
            last && last.healthy !== null
                ? "المكونات السليمة: " + last.healthy + " من " + last.total +
                  " · زمن الاستجابة: " + Math.round(last.latency) + " ملي ثانية · عينات: " + samples.length
                : "غير متصل — فجوة في السلسلة (لا قيمة مختلقة)",
            width - pad, 18
        );
    }

    async function sample() {
        var t0 = performance.now();
        var s;
        try {
            var r = await fetch("/health", { cache: "no-store" });
            if (!r.ok) throw new Error("HTTP " + r.status);
            var data = await r.json();
            var latency = performance.now() - t0;
            var c = countHealthy(data.components);
            s = { t: Date.now(), healthy: c.healthy, total: c.total, latency: latency };
        } catch (e) {
            s = { t: Date.now(), healthy: null, total: null, latency: null };
        }
        samples.push(s);
        if (samples.length > MAX_POINTS) samples.shift();
        renderCard(s);
        renderChart();
    }

    function start() {
        sample();
        setInterval(sample, INTERVAL_MS);
        window.addEventListener("resize", renderChart);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
