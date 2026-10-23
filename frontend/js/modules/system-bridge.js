/* ============================================================
   Sovereign AI — system-bridge.js
   الإصدار: 5.0.0
   جسر الأنظمة السيادي
   ============================================================ */

class SovereignSystemBridge {

    constructor() {

        this.legacyDetected = false;

        console.log(
            '🌉 System Bridge Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.detectLegacy();

        this.bindModernRuntime();

        this.overrideLegacyFunctions();
    }

    /* ========================================================
       DETECT LEGACY
    ======================================================== */

    detectLegacy() {

        if (
            window.sendChatMessage ||
            window.addDialogueMessage
        ) {

            this.legacyDetected = true;

            console.log(
                '🧬 Legacy Runtime Detected'
            );
        }
    }

    /* ========================================================
       MODERN RUNTIME
    ======================================================== */

    bindModernRuntime() {

        const chatButton =
            document.getElementById(
                'btn-send-chat'
            );

        const chatInput =
            document.getElementById(
                'chat-input'
            );

        if (
            chatButton
        ) {

            chatButton.addEventListener(
                'click',
                () => {

                    const text =
                        chatInput?.value?.trim();

                    if (!text) return;

                    this.handleModernChat(
                        text
                    );

                    chatInput.value = '';
                }
            );
        }

        if (
            chatInput
        ) {

            chatInput.addEventListener(
                'keydown',
                (e) => {

                    if (
                        e.key === 'Enter' &&
                        !e.shiftKey
                    ) {

                        e.preventDefault();

                        const text =
                            chatInput.value.trim();

                        if (!text) return;

                        this.handleModernChat(
                            text
                        );

                        chatInput.value = '';
                    }
                }
            );
        }
    }

    /* ========================================================
       MODERN CHAT
    ======================================================== */

    handleModernChat(text) {

        /* =========================================
           R-715: أظهر تبويب الحوار حيث يُعرض الرد
           (كان الرد يُلحق بتبويب مخفي ⇒ "لا استجابة")
        ========================================= */

        if (typeof window.switchTab === 'function') {
            window.switchTab('dialogue');
        }

        /* =========================================
           AI Runtime
           R-715: رسالة المستخدم تُضاف مرة واحدة —
           SOVEREIGN_SOCKET.sendChat يضيفها بنفسه،
           فلا نضيفها هنا إلا في مسار HTTP.
        ========================================= */

        if (
            window.SOVEREIGN_SOCKET
                ?.connected
        ) {

            window.SOVEREIGN_SOCKET
                .sendChat(
                    text
                );

        } else {

            window.SOVEREIGN_DIALOGUE
                ?.addUserMessage(
                    text
                );

            window.SOVEREIGN_AI
                ?.sendMessage(
                    text
                );
        }

        /* =========================================
           Notifications
        ========================================= */

        window.SOVEREIGN_NOTIFY
            ?.info(
                'أُرسلت الرسالة — مصدر الرد يظهر في لوحة الحالة'
            );
    }

    /* ========================================================
       OVERRIDE LEGACY
    ======================================================== */

    overrideLegacyFunctions() {

        /* =========================================
           Legacy addDialogueMessage
        ========================================= */

        window.addDialogueMessage =
            (
                text,
                sender,
                isUser
            ) => {

                if (
                    isUser
                ) {

                    window.SOVEREIGN_DIALOGUE
                        ?.addUserMessage(
                            text
                        );

                } else {

                    window.SOVEREIGN_DIALOGUE
                        ?.addAIMessage(
                            text
                        );
                }
            };

        /* =========================================
           Legacy updateMetrics
        ========================================= */

        window.updateMetrics = () => {

            const metrics =
                window.SOVEREIGN_METRICS
                    ?.getMetrics();

            console.log(
                '📊 Runtime Metrics',
                metrics
            );
        };
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_BRIDGE =
    new SovereignSystemBridge();
