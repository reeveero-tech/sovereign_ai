/**
 * R-729 (البند ٣.١ — بأمر المالك): سجل الأدوات الحقيقي في الواجهة.
 * استبدال runtime-capability-registry.js الزخرفي (كان يسجل «قدرات» وهمية
 * بلا أي استهلاك حقيقي — جرد ١.١/R-723) بمستهلك حي لنقطة /tools/list:
 * كل ما يعرض هنا أدوات مسجلة فعلًا في backend. لا نصوص مزروعة — ما لم
 * تصل إليه الشبكة يظهر «غير متصل» بصدق.
 */
(function () {
    "use strict";

    function escapeHtml(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&" + "amp;")
            .replace(/</g, "&" + "lt;")
            .replace(/>/g, "&" + "gt;")
            .replace(/"/g, "&" + "quot;");
    }

    function ensureContainer() {
        var el = document.getElementById("sovereign-tools-registry");
        if (!el) {
            el = document.createElement("div");
            el.id = "sovereign-tools-registry";
            var host = document.getElementById("sovereign-section-tools");
            if (host) { host.appendChild(el); }
            else { document.body.appendChild(el); }
        }
        return el;
    }

    function render(tools) {
        var el = ensureContainer();
        if (!tools) {
            el.innerHTML = "<b>سجل الأدوات</b><div>⚠️ غير متصل</div>";
            return;
        }
        var rows = tools.map(function (t) {
            return "<tr><td>" + escapeHtml(t.name) + "</td>" +
                "<td>" + escapeHtml(t.description) + "</td>" +
                "<td>" + escapeHtml(t.permission) + "</td></tr>";
        }).join("");
        el.innerHTML =
            "<b>سجل الأدوات (" + tools.length + ")</b>" +
            "<table style='width:100%;border-collapse:collapse'>" +
            "<thead><tr><th>الأداة</th><th>الوصف</th><th>الصلاحية</th></tr></thead>" +
            "<tbody>" + rows + "</tbody></table>";
    }

    async function pull() {
        try {
            var data = await (await fetch("/tools/list")).json();
            render(Array.isArray(data.tools) ? data.tools : null);
        } catch (e) {
            render(null);  /* بلا بيانات = غير متصل — بصدق */
        }
    }

    pull();
    setInterval(pull, 30000);
})();
