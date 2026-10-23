/**
 * R-731 (البند ١.٥ — بأمر المالك): وضع تجريبي صريح.
 * كل عنصر موسوم data-live="experimental" (أي غير مربوط بمصدر حي — انظر
 * frontend/LIVE_BINDINGS.json) يُظهر بجانبه شارة «تجريبي» مرئية مع السبب،
 * فلا يعرض شيء ثابت أو فارغ وكأنه حي. لا بيانات هنا — وسم فقط.
 */
(function () {
    "use strict";

    var REPLACED = { CANVAS: true, IMG: true, INPUT: true, VIDEO: true };

    function badgeFor(el) {
        var b = document.createElement("span");
        b.className = "sovereign-experimental-badge";
        var reason = el.getAttribute("data-live-reason") || "غير مربوط بمصدر حي";
        b.textContent = "تجريبي — " + reason;
        b.title = "R-731: هذا العنصر لا يعرض بيانات حية";
        return b;
    }

    function apply() {
        var nodes = document.querySelectorAll('[data-live="experimental"]');
        for (var i = 0; i < nodes.length; i++) {
            var el = nodes[i];
            if (el.getAttribute("data-live-badged") === "1") continue;
            var badge = badgeFor(el);
            if (REPLACED[el.tagName]) {
                el.insertAdjacentElement("afterend", badge);
            } else {
                el.appendChild(badge);
            }
            el.setAttribute("data-live-badged", "1");
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", apply);
    } else {
        apply();
    }
})();
