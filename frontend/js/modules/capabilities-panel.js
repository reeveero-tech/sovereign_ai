/**
 * R-750 (ROADMAP_V5 §١.٢ — بأمر المالك D-042): جرد القدرات الصادق في الواجهة.
 * مستهلك حي لنقطة /capabilities: كل قدرة بمستوى دليلها المحسوب من الحالة
 * الحية (سجل الأدوات + الأعلام + مفتاح التوقيع + القرص السحابي). لا نصوص
 * مزروعة — ما لم تصل إليه الشبكة يظهر «غير متصل» بصدق، ولا مستوى «مثبت
 * حيًا» من داخل العملية.
 */
(function () {
    "use strict";

    var LABELS = {
        enabled: "مفعّل",
        blocked: "محجوب",
        implemented_disabled: "مبني — غير مفعّل",
        deferred: "مؤجل بقرار المالك",
        missing: "غير مبني"
    };

    function escapeHtml(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&" + "amp;")
            .replace(/</g, "&" + "lt;")
            .replace(/>/g, "&" + "gt;")
            .replace(/"/g, "&" + "quot;");
    }

    function ensureContainer() {
        var el = document.getElementById("sovereign-capabilities");
        if (!el) {
            el = document.createElement("div");
            el.id = "sovereign-capabilities";
            var host = document.getElementById("sovereign-section-tools");
            if (host) { host.appendChild(el); }
            else { document.body.appendChild(el); }
        }
        return el;
    }

    function render(data) {
        var el = ensureContainer();
        if (!data || !Array.isArray(data.capabilities)) {
            el.innerHTML = "<b>جرد القدرات</b><div>⚠️ غير متصل</div>";
            return;
        }
        var rows = data.capabilities.map(function (c) {
            return "<tr><td>" + escapeHtml(c.name) + "</td>" +
                "<td>" + escapeHtml(LABELS[c.level] || c.level) + "</td>" +
                "<td>" + escapeHtml(c.roadmap) + "</td>" +
                "<td>" + escapeHtml(c.note) + "</td></tr>";
        }).join("");
        el.innerHTML =
            "<b>جرد القدرات الصادق (" + data.capabilities.length + ")</b>" +
            "<div>" + escapeHtml(data.live_proof) + "</div>" +
            "<table style='width:100%;border-collapse:collapse'>" +
            "<thead><tr><th>القدرة</th><th>المستوى</th><th>المرجع</th><th>ملاحظة</th></tr></thead>" +
            "<tbody>" + rows + "</tbody></table>";
    }

    async function pull() {
        try {
            render(await (await fetch("/capabilities")).json());
        } catch (e) {
            render(null);  /* بلا بيانات = غير متصل — بصدق */
        }
    }

    pull();
    setInterval(pull, 30000);
})();
