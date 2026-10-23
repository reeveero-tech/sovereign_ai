/**
 * R-728 (١.٣ توسيع — بأمر المالك): عارض الذاكرة — يربط قسم الذاكرة فعليًا
 * بنقطة /components/memory ويعرض إحصاءاتها الحقيقية (core/dynamic/store)
 * بتحديث دوري. لا بيانات وهمية: عند غياب الشبكة يعرض «غير متصل» بصدق.
 */
(function () {
    "use strict";

    function fmt(x) {
        if (x === null || x === undefined) return "—";
        return String(x);
    }

    function renderRow(name, stats) {
        var body = stats && typeof stats === "object" ?
                Object.keys(stats).map(function (k) {
                    return k + ": " + fmt(stats[k]);
                }).join(" · ") : fmt(stats);
        return "<div><b>" + name + ":</b> " + (body || "لا إحصاءات") + "</div>";
    }

    function render(data) {
        var el = document.getElementById("sovereign-section-memory");
        if (!el) return;
        el.innerHTML =
            "<h3>الذاكرة — إحصاءات حية</h3>" +
            renderRow("Core", data && data.core) +
            renderRow("Dynamic", data && data.dynamic) +
            renderRow("Store", data && data.store) +
            "<div style='opacity:.6;font-size:11px'>مصدرها: /components/memory</div>";
    }

    async function pull() {
        var el = document.getElementById("sovereign-section-memory");
        try {
            var data = await (await fetch("/components/memory")).json();
            render(data);
        } catch (e) {
            if (el) el.innerHTML = "<h3>الذاكرة</h3><div>⚠️ غير متصل — لا بيانات وهمية</div>";
        }
    }

    pull();
    setInterval(pull, 10000);
})();
