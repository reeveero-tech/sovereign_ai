/**
 * R-726 (البند ١.٤/١.٦ — الربط الحي): لوحة حالة حية تستقي بياناتها من نقاط
 * API فعلية فقط (/health + /disk/status + /brain/status) بتحديث دوري — لا
 * نصوص مزروعة ولا نشاط وهمي. ما لم تصل إليه الشبكة يظهر «غير متصل» بصدق.
 *
 * R-735 (١.٣ — عزل الأقسام): اللوحة تُعرض داخل قسم «قرص وأدوات» لا طافية
 * بموضع ثابت فوق كل الأقسام. وأُزيل سطر «الصحة» (/health): الصحة بيانات
 * قسم المراقبة وتظهر في الرأس العام. نقاط هذا القسم: القرص/العقل/المجدول.
 */
(function () {
    "use strict";

    function ensureContainer() {
        // R-735: الحاوية ثابتة في index.html داخل قسم الأدوات — لا إنشاء طافٍ
        return document.getElementById("live-system-status");
    }

    function render(disk, brain, sched) {
        var el = ensureContainer();
        if (!el) return;
        var d = disk && disk.enabled ? "☁️ مفعّل" : disk ? "💾 القرص معطل" : "⚠️ غير متصل";
        var b;
        if (!brain) {
            b = "⚠️ غير متصل";
        } else if (!brain.enabled) {
            b = "📋 ردود القوالب (لا عقل)";
        } else {
            // R-736 (دقة): المضبوط معروض (النموذج) + المرصود (آخر استدعاء) —
            // لا ادعاء نجاح قبل أول استدلال فعلي
            var lastTxt = "لم يُستدعَ بعد";
            if (brain.last_call && brain.last_call.result === "ok") lastTxt = "ناجح";
            else if (brain.last_call && brain.last_call.result === "error") lastTxt = "فاشل (سقوط للقوالب)";
            else if (brain.last_call && brain.last_call.result === "misconfigured") lastTxt = "إعداد غير معروف";
            b = "🧠 عقل: " + (brain.model || "نموذج؟") + " · آخر استدعاء: " + lastTxt;
        }
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
        [["", "حالة القرص والعقل والمجدول"], ["القرص: ", d],
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
        var disk = null, brain = null, sched = null;
        try { disk = await (await fetch("/disk/status")).json(); } catch (e) { /* بلا بيانات = غير متصل */ }
        try { brain = await (await fetch("/brain/status")).json(); } catch (e) { /* بلا بيانات = غير متصل */ }
        try { sched = await (await fetch("/scheduler/status")).json(); } catch (e) { /* بلا بيانات = غير متصل */ }
        render(disk, brain, sched);
    }

    pull();
    setInterval(pull, 10000);
})();
