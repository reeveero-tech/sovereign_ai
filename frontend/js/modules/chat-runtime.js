/* ============================================================
   Sovereign AI — chat-runtime.js
   الإصدار: 6.0.0
   طبقة المحادثة السيادية الموحدة
   ============================================================ */

class SovereignChatRuntime {

    constructor() {

        this.activeConversation = [];

        this.isProcessing = false;

        this.typingState = false;

        console.log(
            '💬 Chat Runtime Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindInputCounter();
    }

    /* ========================================================
       INPUT COUNTER
    ======================================================== */

    bindInputCounter() {

        const input =
            document.getElementById(
                'chat-input'
            );

        const counter =
            document.getElementById(
                'chat-input-count'
            );

        if (
            !input ||
            !counter
        ) return;

        input.addEventListener(
            'input',
            () => {

                counter.textContent =
                    `${input.value.length}`;
            }
        );
    }

    /* ========================================================
       SEND MESSAGE
    ======================================================== */

    async sendMessage(text) {

        if (
            !text ||
            this.isProcessing
        ) return;

        this.isProcessing = true;

        /* =========================================
           USER MESSAGE
        ========================================= */

        window.SOVEREIGN_DIALOGUE
            ?.addUserMessage(
                text
            );

        this.activeConversation.push({

            role: 'user',

            content: text,

            timestamp:
                Date.now()
        });

        /* =========================================
           THINKING
        ========================================= */

        this.setTypingState(
            true
        );

        /* =========================================
           SOCKET
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

            await this.localRuntimeResponse(
                text
            );
        }

        this.isProcessing = false;
    }

    /* ========================================================
       LOCAL RESPONSE
    ======================================================== */

    async localRuntimeResponse(text) {

        try {

            const response =
                await window.SOVEREIGN_AI
                    ?.sendMessage(
                        text
                    );

            return response;

        } catch (error) {

            console.error(
                'Local Runtime Failed',
                error
            );

            window.SOVEREIGN_NOTIFY
                ?.error(
                    'Neural Runtime Failure'
                );
        }
    }

    /* ========================================================
       RECEIVE AI
    ======================================================== */

    receiveMessage(text) {

        this.setTypingState(
            false
        );

        window.SOVEREIGN_DIALOGUE
            ?.addAIMessage(
                text
            );

        this.activeConversation.push({

            role: 'assistant',

            content: text,

            timestamp:
                Date.now()
        });

        /* =========================================
           MEMORY
        ========================================= */

        const lastUser =
            this.activeConversation
                .filter(
                    item =>
                        item.role === 'user'
                )
                .slice(-1)[0];

        if (
            lastUser
        ) {

            window.SOVEREIGN_MEMORY
                ?.saveInteraction(
                    lastUser.content,
                    text
                );
        }

        /* =========================================
           NOTIFY
        ========================================= */

        window.SOVEREIGN_NOTIFY
            ?.success(
                'Neural Response Received'
            );

        /* =========================================
           VOICE — R-740 (البند ٢.٤): نطق الرد إن كان
           التبديل مفعّلًا (زر btn-tts-toggle)
        ========================================= */

        window.SOVEREIGN_VOICE
            ?.speak(
                text
            );
    }

    /* ========================================================
       VISION — R-741 (البند ٢.٢): مدخل استقبال وصف الرؤية من
       وحدة رفع الصور — لا وحدة مجهولة تكتب في المحادثة
    ======================================================== */

    receiveVisionDescription(description, fileName) {

        window.SOVEREIGN_DIALOGUE
            ?.addUserMessage(
                `🖼️ صورة: ${fileName}`
            );

        this.receiveMessage(
            `👁 ${description}`
        );
    }

    /* ========================================================
       TYPING STATE
    ======================================================== */

    setTypingState(state) {

        this.typingState = state;

        document.body.classList.toggle(
            'ai-thinking',
            state
        );

        if (
            state
        ) {

            window.SOVEREIGN_CINEMA
                ?.enterScene(
                    'thinking'
                );

        } else {

            window.SOVEREIGN_CINEMA
                ?.enterScene(
                    'response'
                );
        }
    }

    /* ========================================================
       CLEAR CONVERSATION
    ======================================================== */

    clearConversation() {

        this.activeConversation = [];

        window.SOVEREIGN_DIALOGUE
            ?.clear();
    }

    /* ========================================================
       GET CONVERSATION
    ======================================================== */

    getConversation() {

        return this.activeConversation;
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_CHAT =
    new SovereignChatRuntime();
