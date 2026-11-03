/**
 * R-840: واجهة نظام الموصلات — كتالوج ومعالج إعداد وإدارة وحوكمة.
 * مبدأ: كل نوع مصادقة له معالج إعداد، وكل موصل له صفحة إدارة، وكل حالة
 * فشل لها رسالة وإجراء. لا قيمة سرية تعرض هنا أبدًا — البصمة فقط.
 */
(function () {
    "use strict";

    var AUTH_TYPES = {};      // id → تعريف النوع (من /auth-types)
    var CATALOG = [];         // الموصلات من /catalog
    var CREDS = [];           // الاتصالات من /state

    function esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, String.fromCharCode(38) + "amp;")
            .replace(/</g, String.fromCharCode(38) + "lt;")
            .replace(/>/g, String.fromCharCode(38) + "gt;")
            .replace(/"/g, String.fromCharCode(38) + "quot;");
    }

    function root() {
        return document.getElementById("connectors-root");
    }

    function statusChip(status) {
        var map = {
            active: ["متصل", "var(--accent,#2ecc71)"],
            expired: ["منتهٍ — أعد الاتصال", "#e67e22"],
            revoked: ["مُبطل", "#95a5a6"],
            error: ["خطأ", "#e74c3c"],
            preview: ["معاينة", "#3498db"],
            deprecated: ["موقوف تدريجي", "#e67e22"],
            ga: ["عام", "#2ecc71"],
            removed: ["مُزال", "#95a5a6"]
        };
        var m = map[status] || [status, "#95a5a6"];
        return "<span class='conn-status' style='color:" + m[1] + "'>● " + m[0] + "</span>";
    }

    // ------------------------------------------------ بطاقة «يتطلب اتصالًا» (تكامل الوكيل)
    // تُستدعى من أي مكان (محادثة/أداة) لعرض بطاقة اتصال فورية عند الحاجة.
    window.SovereignConnectors = {
        renderAgentCard: function (card) {
            if (!card || card.type !== "requires_connection") { return null; }
            var el = document.createElement("div");
            el.className = "conn-agent-card";
            el.innerHTML =
                "<div class='conn-card-title'>🔗 " + esc(card.connector_name) +
                " — يتطلب اتصالًا</div>" +
                "<div>العملية: <b>" + esc(card.operation) + "</b></div>" +
                "<div>الصلاحيات المطلوبة: <b>" + esc((card.needed_scopes || []).join("، ")) +
                "</b></div>" +
                "<button class='conn-btn' data-setup-connector='" + esc(card.connector) +
                "'>إعداد الاتصال الآن</button>";
            el.querySelector("[data-setup-connector]").addEventListener("click", function () {
                openWizard(card.connector);
            });
            return el;
        }
    };

    // ------------------------------------------------ التحميل
    async function pull() {
        try {
            var cat = await (await fetch("/connectors/system/catalog")).json();
            var types = await (await fetch("/connectors/system/auth-types")).json();
            CATALOG = cat.connectors || [];
            (types.auth_types || []).forEach(function (t) { AUTH_TYPES[t.id] = t; });
            render();
        } catch (e) {
            if (root()) {
                root().innerHTML = "<b>الموصلات</b><div>⚠️ غير متصل بخدمة الموصلات</div>";
            }
        }
    }

    async function pullState() {
        try {
            var st = await (await fetch("/connectors/system/state")).json();
            CREDS = st.credentials || [];
        } catch (e) { CREDS = []; }
    }

    // ------------------------------------------------ الكتالوج
    function render() {
        if (!root()) { return; }
        pullState().then(function () {
            root().innerHTML =
                "<div class='conn-header'>" +
                "<h3>🔌 الموصلات والتكاملات</h3>" +
                "<input id='conn-search' placeholder='بحث…' style='width:180px'>" +
                "<select id='conn-cat'><option value=''>كل الفئات</option>" +
                ["saas", "dev", "database", "internal", "generic"].map(function (c) {
                    return "<option>" + c + "</option>";
                }).join("") + "</select>" +
                "<select id='conn-auth'><option value=''>كل أنواع المصادقة</option>" +
                Object.keys(AUTH_TYPES).map(function (a) {
                    return "<option value='" + a + "'>" + esc(AUTH_TYPES[a].label) + "</option>";
                }).join("") + "</select>" +
                "<button class='conn-btn' id='conn-refresh'>تحديث</button>" +
                "</div>" +
                "<div id='conn-grid'></div>" +
                "<div id='conn-manage'></div>" +
                "<div id='conn-detail'></div>" +
                "<div id='conn-logs'></div>" +
                "<div id='conn-admin'></div>";

            document.getElementById("conn-search").addEventListener("input", renderGrid);
            document.getElementById("conn-cat").addEventListener("change", renderGrid);
            document.getElementById("conn-auth").addEventListener("change", renderGrid);
            document.getElementById("conn-refresh").addEventListener("click", pull);
            renderGrid();
            renderManage();
            renderAdmin();
        });
    }

    function connFor(id) {
        return (CREDS || []).filter(function (c) { return c.connector_id === id; });
    }

    function renderGrid() {
        var q = (document.getElementById("conn-search").value || "").toLowerCase();
        var cat = document.getElementById("conn-cat").value;
        var auth = document.getElementById("conn-auth").value;
        var items = CATALOG.filter(function (c) {
            return (!q || c.name.toLowerCase().indexOf(q) >= 0 ||
                    c.description.indexOf(q) >= 0) &&
                   (!cat || c.category === cat) &&
                   (!auth || (c.auth_types || []).indexOf(auth) >= 0);
        });
        var grid = document.getElementById("conn-grid");
        grid.innerHTML = "<h4>الكتالوج (" + items.length + ")</h4><div class='conn-grid'>" +
            items.map(function (c) {
                var conns = connFor(c.id);
                var st = conns.length ? statusChip(conns[0].status)
                                       : statusChip(c.lifecycle);
                return "<div class='conn-card' data-conn='" + esc(c.id) + "'>" +
                    "<div class='conn-card-title'>" + esc(c.name) +
                    " <small>v" + esc(c.version) + "</small></div>" +
                    "<div class='conn-desc'>" + esc(c.description) + "</div>" +
                    "<div>" + st + " · " + esc(c.category) + "</div>" +
                    "<div class='conn-auths'>مصادقة: " +
                    (c.auth_types || []).map(function (a) {
                        var t = AUTH_TYPES[a];
                        return "<span class='conn-tag'" +
                            (t && t.risk !== "safe" ? " title='" + esc(t.warning || "") + "'" : "") +
                            ">" + esc(t ? t.label : a) + (t && t.risk === "deprecated" ? " ⚠️" : "") +
                            "</span>";
                    }).join(" ") + "</div>" +
                    "<div class='conn-ops'>العمليات: " +
                    Object.keys(c.operations || {}).map(function (o) {
                        return "<span class='conn-tag" +
                            (c.operations[o].is_write ? " conn-write" : "") + "'>" +
                            esc(o) + "</span>";
                    }).join(" ") + "</div>" +
                    "<button class='conn-btn' data-setup-connector='" + esc(c.id) +
                    "'>إعداد / تفاصيل</button></div>";
            }).join("") + "</div>";
        Array.prototype.forEach.call(grid.querySelectorAll("[data-conn]"), function (el) {
            el.addEventListener("click", function () { renderDetail(el.getAttribute("data-conn")); });
        });
        Array.prototype.forEach.call(grid.querySelectorAll("[data-setup-connector]"), function (el) {
            el.addEventListener("click", function (ev) {
                ev.stopPropagation(); openWizard(el.getAttribute("data-setup-connector"));
            });
        });
    }

    // ------------------------------------------------ صفحة التفاصيل
    function renderDetail(id) {
        var c = CATALOG.filter(function (x) { return x.id === id; })[0];
        if (!c) { return; }
        var el = document.getElementById("conn-detail");
        el.innerHTML = "<h4>تفاصيل الموصل: " + esc(c.name) + "</h4>" +
            "<p>" + esc(c.description) + "</p>" +
            "<table class='conn-table'><thead><tr><th>العملية</th><th>النوع</th>" +
            "<th>الصلاحيات المطلوبة</th></tr></thead><tbody>" +
            Object.keys(c.operations || {}).map(function (o) {
                var op = c.operations[o];
                return "<tr><td>" + esc(o) + "</td><td>" + esc(op.kind) +
                    (op.is_write ? " (كتابة)" : "") + "</td><td>" +
                    esc((op.scopes || []).join("، ")) + "</td></tr>";
            }).join("") + "</tbody></table>" +
            "<button class='conn-btn' data-setup-connector='" + esc(id) + "'>إعداد اتصال</button>";
        el.querySelector("[data-setup-connector]").addEventListener("click", function () {
            openWizard(id);
        });
    }

    // ------------------------------------------------ معالج الإعداد (Wizard)
    function openWizard(connectorId) {
        var c = CATALOG.filter(function (x) { return x.id === connectorId; })[0];
        if (!c) { return; }
        var overlay = document.createElement("div");
        overlay.className = "conn-wizard-overlay";
        var authOpts = (c.auth_types || []).map(function (a, i) {
            var t = AUTH_TYPES[a] || {};
            return "<option value='" + a + "'" + (i === 0 ? " selected" : "") + ">" +
                esc(t.label || a) + (t.risk === "deprecated" ? " (⚠️ مهجور)" : "") + "</option>";
        }).join("");
        overlay.innerHTML =
            "<div class='conn-wizard'>" +
            "<h3>إعداد اتصال: " + esc(c.name) + "</h3>" +
            "<label>نوع المصادقة</label><select id='wiz-auth'>" + authOpts + "</select>" +
            "<div id='wiz-fields'></div>" +
            "<label>الصلاحيات (أقل صلاحية تلبي الحاجة)</label>" +
            "<div id='wiz-scopes'></div>" +
            "<div class='conn-warn' id='wiz-warn'></div>" +
            "<div id='wiz-result'></div>" +
            "<div class='conn-wizard-actions'>" +
            "<button class='conn-btn' id='wiz-cancel'>إلغاء</button>" +
            "<button class='conn-btn' id='wiz-test'>اختبار الاتصال</button>" +
            "<button class='conn-btn' id='wiz-save'>مراجعة الصلاحيات وتأكيد</button>" +
            "</div></div>";
        document.body.appendChild(overlay);

        var allScopes = {};
        Object.keys(c.operations || {}).forEach(function (o) {
            (c.operations[o].scopes || []).forEach(function (s) { allScopes[s] = true; });
        });
        var scopeList = Object.keys(allScopes);
        var writeScopes = {};
        Object.keys(c.operations || {}).forEach(function (o) {
            if (c.operations[o].is_write) {
                (c.operations[o].scopes || []).forEach(function (s) { writeScopes[s] = true; });
            }
        });

        function renderFields() {
            var a = document.getElementById("wiz-auth").value;
            var t = AUTH_TYPES[a] || {};
            var fields = t.wizard_fields || [["token", "secret"]];
            document.getElementById("wiz-fields").innerHTML = fields.map(function (f) {
                var name = f[0], kind = f[1];
                var input;
                if (kind === "textarea" || kind === "file") {
                    input = "<textarea id='wiz-f-" + name + "' rows='4'></textarea>";
                } else if (kind.indexOf("select:") === 0) {
                    var opts = kind.slice(7).split("|").map(function (o2) {
                        return "<option>" + o2 + "</option>";
                    }).join("");
                    input = "<select id='wiz-f-" + name + "'>" + opts + "</select>";
                } else {
                    input = "<input id='wiz-f-" + name + "' type='password' autocomplete='off'>";
                }
                return "<label>" + esc(name) + (kind === "secret" || kind === "file" ?
                    " (سري — يخزن مشفرًا ولا يعرض)" : "") + "</label>" + input;
            }).join("");
            document.getElementById("wiz-warn").innerHTML = t.warning ?
                "⚠️ " + esc(t.warning) : "";
            document.getElementById("wiz-scopes").innerHTML = scopeList.map(function (s) {
                return "<label class='conn-scope'><input type='checkbox' value='" + esc(s) +
                    "'" + (writeScopes[s] ? "" : " checked") + "> " + esc(s) +
                    (writeScopes[s] ? " (كتابة)" : " (قراءة)") + "</label>";
            }).join("");
        }
        document.getElementById("wiz-auth").addEventListener("change", renderFields);
        renderFields();

        function collect() {
            var a = document.getElementById("wiz-auth").value;
            var t = AUTH_TYPES[a] || {};
            var fields = {};
            (t.wizard_fields || [["token", "secret"]]).forEach(function (f) {
                var el = document.getElementById("wiz-f-" + f[0]);
                if (el) { fields[f[0]] = el.value; }
            });
            var scopes = Array.prototype.filter.call(
                document.querySelectorAll("#wiz-scopes input:checked"),
                function (x) { return x.checked; }).map(function (x) { return x.value; });
            return { auth_type: a, fields: fields, scopes: scopes };
        }

        document.getElementById("wiz-cancel").addEventListener("click", function () {
            overlay.remove();
        });
        document.getElementById("wiz-save").addEventListener("click", async function () {
            var body = Object.assign(collect(), {
                connector: connectorId, owner_scope: "user", owner: "owner"
            });
            try {
                var r = await fetch("/connectors/system/setup", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body)
                });
                var d = await r.json();
                document.getElementById("wiz-result").innerHTML = r.ok ?
                    "✅ تم الإعداد ونجح اختبار الاتصال — بصمة السر: " +
                    esc((d.credential || {}).fingerprint || "") :
                    "❌ " + esc(typeof d.detail === "string" ? d.detail :
                        JSON.stringify(d.detail));
                if (r.ok) { render(); }
            } catch (e) {
                document.getElementById("wiz-result").textContent = "❌ فشل الطلب: " + e;
            }
        });
        document.getElementById("wiz-test").addEventListener("click", async function () {
            try {
                var r = await fetch("/connectors/system/test", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ connector: connectorId })
                });
                var d = await r.json();
                document.getElementById("wiz-result").textContent =
                    r.ok ? "✅ نجح اختبار الاتصال" : "❌ " + (d.detail || "فشل");
            } catch (e) {
                document.getElementById("wiz-result").textContent = "❌ " + e;
            }
        });
    }

    // ------------------------------------------------ الإدارة
    function renderManage() {
        var el = document.getElementById("conn-manage");
        el.innerHTML = "<h4>الاتصالات النشطة</h4>" +
            (CREDS.length ? "<table class='conn-table'><thead><tr>" +
            "<th>الموصل</th><th>النوع</th><th>الصلاحيات</th><th>الحالة</th>" +
            "<th>آخر استخدام</th><th>إجراءات</th></tr></thead><tbody>" +
            CREDS.map(function (c) {
                return "<tr><td>" + esc(c.connector_id) + "</td>" +
                    "<td>" + esc(c.auth_type) + "</td>" +
                    "<td>" + esc((c.scopes || []).join("، ")) + "</td>" +
                    "<td>" + statusChip(c.status) +
                    (c.last_error ? "<br><small>" + esc(c.last_error) + "</small>" : "") +
                    "</td>" +
                    "<td>" + (c.last_used_at ? new Date(c.last_used_at * 1000).toLocaleString() : "—") + "</td>" +
                    "<td>" +
                    "<button class='conn-btn' data-tst='" + esc(c.connector_id) + "'>اختبار</button> " +
                    "<button class='conn-btn' data-rot='" + esc(c.id) + "'>تدوير</button> " +
                    "<button class='conn-btn conn-danger' data-rvk='" + esc(c.id) + "'>إبطال</button>" +
                    "</td></tr>";
            }).join("") + "</tbody></table>" :
            "<div>لا اتصالات بعد — ابدأ من الكتالوج أعلاه.</div>") +
            "<div id='conn-manage-result'></div>";

        Array.prototype.forEach.call(el.querySelectorAll("[data-tst]"), function (b) {
            b.addEventListener("click", async function () {
                var r = await fetch("/connectors/system/test", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ connector: b.getAttribute("data-tst") })
                });
                var d = await r.json();
                document.getElementById("conn-manage-result").textContent =
                    r.ok ? "✅ الاتصال سليم" : "❌ " + (d.detail || "فشل الاختبار");
            });
        });
        Array.prototype.forEach.call(el.querySelectorAll("[data-rot]"), function (b) {
            b.addEventListener("click", async function () {
                var v = prompt("القيمة الجديدة للسر (تدوير بلا توقف):");
                if (!v) { return; }
                var r = await fetch("/connectors/system/rotate", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ credential_id: b.getAttribute("data-rot"), new_value: v })
                });
                var d = await r.json();
                document.getElementById("conn-manage-result").textContent =
                    r.ok ? "✅ دُوّر السر — الإصدار الجديد نشط" : "❌ " + JSON.stringify(d.detail);
                if (r.ok) { pull(); }
            });
        });
        Array.prototype.forEach.call(el.querySelectorAll("[data-rvk]"), function (b) {
            b.addEventListener("click", async function () {
                if (!confirm("إبطال الاتصال وسحب السر فورًا؟")) { return; }
                var r = await fetch("/connectors/system/revoke", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ credential_id: b.getAttribute("data-rvk") })
                });
                document.getElementById("conn-manage-result").textContent =
                    r.ok ? "تم الإبطال — السر سُحب من الخزينة" : "❌ فشل الإبطال";
                if (r.ok) { pull(); }
            });
        });

        // سجل الاستخدام
        fetch("/connectors/system/logs?limit=50").then(function (r) { return r.json(); })
            .then(function (d) {
                var logs = d.logs || [];
                document.getElementById("conn-logs").innerHTML =
                    "<h4>سجل الاستخدام (آخر " + logs.length + ")</h4>" +
                    (logs.length ? "<table class='conn-table'><thead><tr><th>الوقت</th>" +
                    "<th>الموصل</th><th>العملية</th><th>الفاعل</th><th>النتيجة</th>" +
                    "</tr></thead><tbody>" +
                    logs.slice().reverse().map(function (l) {
                        return "<tr><td>" + new Date(l.ts * 1000).toLocaleString() + "</td>" +
                            "<td>" + esc(l.connector) + "</td><td>" + esc(l.operation) + "</td>" +
                            "<td>" + esc(l.actor) + "</td><td>" + esc(l.status) + "</td></tr>";
                    }).join("") + "</tbody></table>" : "<div>لا استخدامات بعد.</div>");
            }).catch(function () {});
    }

    // ------------------------------------------------ الحوكمة (Admin)
    function renderAdmin() {
        var el = document.getElementById("conn-admin");
        el.innerHTML = "<h4>حوكمة المؤسسة</h4>" +
            "<label>مفتاح API للسيد (لأوامر السياسة)</label>" +
            "<input id='conn-apikey' type='password' autocomplete='off'>" +
            "<div class='conn-admin-actions'>" +
            "<input id='conn-pol-connector' placeholder='معرف الموصل'>" +
            "<button class='conn-btn' data-pol='block'>حظر</button>" +
            "<button class='conn-btn' data-pol='unblock'>رفع الحظر</button>" +
            "<button class='conn-btn' data-pol='require_approval'>طلب موافقة</button>" +
            "<button class='conn-btn' data-pol='approve'>موافقة</button>" +
            "</div><div id='conn-pol-state'></div>";
        fetch("/connectors/system/policy").then(function (r) { return r.json(); })
            .then(function (p) {
                document.getElementById("conn-pol-state").innerHTML =
                    "محظور: <b>" + esc((p.blocked_connectors || []).join("، ") || "—") + "</b> · " +
                    "بانتظار موافقة: <b>" + esc((p.require_approval || []).join("، ") || "—") +
                    "</b> · أنواع مصادقة مسموحة: <b>" +
                    esc((p.allowed_auth_types || ["الكل"]).join("، ")) + "</b> · " +
                    "أحداث تدقيق: <b>" + esc(p.audit_count) + "</b>";
            }).catch(function () {});
        Array.prototype.forEach.call(el.querySelectorAll("[data-pol]"), function (b) {
            b.addEventListener("click", async function () {
                var body = {
                    action: b.getAttribute("data-pol"),
                    connector: document.getElementById("conn-pol-connector").value,
                    api_key: document.getElementById("conn-apikey").value
                };
                var r = await fetch("/connectors/system/policy", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(body)
                });
                var d = await r.json();
                document.getElementById("conn-pol-state").textContent =
                    r.ok ? "✅ نُفذ الأمر" : "❌ " + JSON.stringify(d.detail);
            });
        });
    }

    pull();
    setInterval(pull, 60000);
})();
