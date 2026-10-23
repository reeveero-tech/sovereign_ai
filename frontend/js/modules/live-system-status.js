/**
 * R-726 (البند ١.٤/١.٦ — الربط الحي): لوحة حالة حية تستقي بياناتها من نقاط
 * API فعلية فقط (/health + /disk/status + /brain/status) بتحديث دوري — لا
 * نصوص مزروعة ولا نشاط وهمي. ما لم تصل إليه الشبكة يظهر «غير متصل» بصدق.
 */
(function () {
    "use strict";

    function ensureContainer() {
        var el = document.getElementById("live-system-status");
        if (!el) {
            el = document.createElement("section");
            el.id = "live-system-status";
            el.style.cssText = "position:fixed;bottom:8px;right:8px;z-index:9999;" +
                "background:rgba(10,14,20,.92);color:#e8e8e8;padding:10px 14px;" +
                "border-radius:8px;font:12px/1.6 monospace;border:1px solid #2a3a4a;" +
                "max-width:340px;text-align:right;direction:rtl;";
            document.body.appendChild(el);
        }
        return el;
    }

    function render(health, disk, brain, sched) {
        var el = ensureContainer();
        var h = health && health.status === "healthy" ? "✅ حي" :
                health ? "❌ " + (health.status || "غير معروف") : "⚠️ غير متصل";
        var d = disk && disk.enabled ? "☁️ مفعّل" : disk ? "💾 القرص معطل" : "⚠️ غير متصل";
        var b = brain && brain.enabled ?
                "🧠 عقل: " + (brain.model || "نموذج؟") :
                brain ? "📋 ردود القوالب (لا عقل)" : "⚠️ غير متصل";
        // R-732 (البند ٣.٦): حالة المجدول من /scheduler/status — عدد التشغيلات الفعلية
        var s;
        if (!sched) {
            s = "⚠️ غير متصل";
        } else if (!sched.enabled) {
            s = "⏸️ معطل (التفعيل بيد المالك)";
        } else {
            var runs = 0, failed = 0;
            (sched.tasks || []).forEach(function (t) {
                runs += t.runs || 0;
                if (t.last_ok === false) failed += 1;
            });
            s = "⏱️ يعمل — " + runs + " تشغيل" + (failed ? " (فشل آخر تشغيل لـ" + failed + ")" : "");
        }
        // R-732: نص لا HTML (قيم من الخادم — نمط إصلاح الحقن في R-731)
        el.textContent = "";
        [["", "حالة سوفره الحية"], ["الصحة: ", h], ["القرص: ", d],
         ["مصدر الرد: ", b], ["المجدول: ", s]].forEach(function (row, i) {
            var div = document.createElement("div");
            if (i === 0) {
                var strong = document.createElement("b");
                strong.textContent = row[1];
                div.appendChild(strong);
            } else {
                div.textContent = row[0] + row[1];
            }
            el.appendChild(div);
        });
    }

    async function pull() {
        var health = null, disk = null, brain = null, sched = null;
        try { health = await (await fetch("/health")).json(); } catch (e) { /* بلا بيانات = غير متصل */ }
        try { disk = await (await fetch("/disk/status")).json(); } catch (e) { /* بلا بيانات = غير متصل */ }
        try { brain = await (await fetch("/brain/status")).json(); } catch (e) { /* بلا بيانات = غير متصل */ }
        try { sched = await (await fetch("/scheduler/status")).json(); } catch (e) { /* بلا بيانات = غير متصل */ }
        render(health, disk, brain, sched);
    }

    pull();
    setInterval(pull, 10000);
})();
