/* ============================================================
   Sovereign AI — runtime-init.js
   الإصدار: 6.0.0
   نقطة الإقلاع السيادية الحديثة
   ============================================================ */

class SovereignRuntimeInit {

    constructor() {

        this.systemsReady = false;

        this.bootStarted = false;

        console.log(
            '🚀 Sovereign Runtime Init'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        if (
            document.readyState === 'loading'
        ) {

            document.addEventListener(
                'DOMContentLoaded',
                () => {

                    this.boot();
                }
            );

        } else {

            this.boot();
        }
    }

    /* ========================================================
       BOOT
    ======================================================== */

    async boot() {

        if (
            this.bootStarted
        ) return;

        this.bootStarted = true;

        console.log(
            '⚡ Boot Sequence Started'
        );

        this.verifySystems();

        this.initializeRuntime();

        this.bindRuntimeEvents();

        this.startNeuralPresence();

        this.completeBoot();
    }

    /* ========================================================
       VERIFY
    ======================================================== */

    verifySystems() {

        const required = [

            'SOVEREIGN_CORE',

            'SOVEREIGN_STATE',

            'SOVEREIGN_RENDER',

            'SOVEREIGN_FX',

            'SOVEREIGN_CINEMA',

            'SOVEREIGN_AI',

            'SOVEREIGN_DIALOGUE',

            'SOVEREIGN_SOCKET',

            'SOVEREIGN_MEMORY',

            'SOVEREIGN_COMMANDS',

            'SOVEREIGN_NOTIFY'
        ];

        const missing = [];

        required.forEach(system => {

            if (!window[system]) {

                missing.push(system);
            }
        });

        if (missing.length) {

            console.error(
                '❌ Missing Systems:',
                missing
            );

            return;
        }

        console.log(
            '✅ All Runtime Systems Ready'
        );

        this.systemsReady = true;
    }

    /* ========================================================
       INITIALIZE
    ======================================================== */

    initializeRuntime() {

        if (
            !this.systemsReady
        ) return;

        document.body.classList.add(
            'runtime-online'
        );

        window.SOVEREIGN_NOTIFY
            ?.success(
                'وحدات الواجهة جاهزة (محليًا — حالة الخادم في لوحة الحالة)'
            );

        window.SOVEREIGN_CINEMA
            ?.createMoment(
                'epic'
            );
    }

    /* ========================================================
       EVENTS
    ======================================================== */

    bindRuntimeEvents() {

        const chatButton =
            document.getElementById(
                'btn-send-chat'
            );

        const chatInput =
            document.getElementById(
                'chat-input'
            );

        /* =========================================
           CHAT
        ========================================= */

        if (
            chatButton
        ) {

            chatButton.onclick = () => {

                const text =
                    chatInput?.value?.trim();

                if (!text) return;

                this.handleChat(text);

                chatInput.value = '';
            };
        }

        /* =========================================
           ENTER
        ========================================= */

        if (
            chatInput
        ) {

            chatInput.onkeydown = (e) => {

                if (
                    e.key === 'Enter' &&
                    !e.shiftKey
                ) {

                    e.preventDefault();

                    const text =
                        chatInput.value.trim();

                    if (!text) return;

                    this.handleChat(text);

                    chatInput.value = '';
                }
            };
        }
    }

    /* ========================================================
       CHAT HANDLER
    ======================================================== */

    handleChat(text) {

        window.SOVEREIGN_DIALOGUE
            ?.addUserMessage(
                text
            );

        if (
            window.SOVEREIGN_SOCKET
                ?.connected
        ) {

            window.SOVEREIGN_SOCKET
                .sendChat(
                    text
                );

        } else {

            window.SOVEREIGN_AI
                ?.sendMessage(
                    text
                );
        }

        window.SOVEREIGN_NOTIFY
            ?.info(
                'أُرسلت الرسالة — مصدر الرد يظهر في لوحة الحالة'
            );
    }

    /* ========================================================
       NEURAL PRESENCE
    ======================================================== */

    startNeuralPresence() {

        setInterval(() => {

            document.body.style.setProperty(
                '--runtime-random',
                Math.random()
            );

        }, 2000);
    }

    /* ========================================================
       COMPLETE
    ======================================================== */

    completeBoot() {

        console.log(
            `
            👑 SOVEREIGN RUNTIME ACTIVE
            ===========================
            STATUS: ONLINE
            MODE: CINEMATIC
            AI: ACTIVE
            MEMORY: READY
            RENDER: STABLE
            `
        );
    }
}

/* ============================================================
   START RUNTIME
============================================================ */

window.SOVEREIGN_RUNTIME =
    new SovereignRuntimeInit();
