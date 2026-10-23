/**
 * R-727 (البند ١.٣): موجّه الأقسام — يبدّل بين أقسام الواجهة المنفصلة
 * (محادثة/ذاكرة/قرص وأدوات/تطور ذاتي) بالنقر. تفاعل حقيقي لا وهم:
 * المحادثة الحالية تُنقل فعليًا داخل قسمها. الأقسام غير المربوطة تحمل
 * data-live="experimental" وتعرض شارة «تجريبي» عبر experimental-badges.js
 * (R-731 — تصويب: data-sovereign-placeholder لم يكن يُقرأ إطلاقًا).
 */
(function () {
    "use strict";
    var SECTIONS = ["chat", "memory", "tools", "evolution"];
    var current = "chat";

    function ensureNav() {
        var nav = document.getElementById("sovereign-section-nav");
        if (!nav) return null;
        return nav;
    }

    function show(name) {
        current = name;
        SECTIONS.forEach(function (s) {
            var el = document.getElementById("sovereign-section-" + s);
            if (el) el.style.display = (s === name) ? "block" : "none";
        });
        var nav = ensureNav();
        if (nav) {
            nav.querySelectorAll("button").forEach(function (b) {
                b.style.fontWeight = (b.getAttribute("data-sovereign-section") === name) ? "bold" : "normal";
            });
        }
    }

    function moveChatIntoSection() {
        var input = document.getElementById("chat-input");
        var chatSection = document.getElementById("sovereign-section-chat");
        if (input && chatSection && !chatSection.contains(input)) {
            var host = input.closest("form,div");
            if (host && host.parentElement) chatSection.appendChild(host);
        }
    }

    function moveLiveStatusIntoTools() {
        var live = document.getElementById("live-system-status");
        var tools = document.getElementById("sovereign-section-tools");
        if (live && tools && !tools.contains(live)) tools.appendChild(live);
    }

    document.addEventListener("DOMContentLoaded", function () {
        var nav = ensureNav();
        if (!nav) return;
        moveChatIntoSection();
        moveLiveStatusIntoTools();
        nav.querySelectorAll("button").forEach(function (b) {
            b.addEventListener("click", function () {
                show(b.getAttribute("data-sovereign-section"));
            });
        });
        show(current);
    });
})();
