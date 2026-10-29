/* ============================================================
   Sovereign AI — live-ai-engine.js
   الإصدار: 4.0.0
   محرك الذكاء الحي
   ============================================================ */

class SovereignLiveAI {

    constructor() {

        this.isThinking = false;

        this.currentStream = '';

        this.abortController = null;

        this.memory = [];

        console.log(
            '🧠 Live AI Engine Initialized'
        );
    }

    /* ========================================================
       SEND MESSAGE
    ======================================================== */

    async sendMessage(message) {

        if (!message) return;

        this.isThinking = true;

        this.createThinkingState();

        try {

            const response =
                await fetch('/chat', {

                    method: 'POST',

                    headers: {
                        'Content-Type':
                            'application/json'
                    },

                    body: JSON.stringify({
                        text: message,
                        user_id: 'sovereign',
                        live: true
                    })
                });

            const data =
                await response.json();

            this.removeThinkingState();

            this.streamResponse(
                data.reply || '...'
            );

            this.saveMemory(
                message,
                data.reply
            );

        } catch (error) {

            this.removeThinkingState();

            console.error(
                'AI Error:',
                error
            );

            this.emitSystemMessage(
                'تعذر الاتصال بالنظام'
            );
        }

        this.isThinking = false;
    }

    /* ========================================================
       STREAM RESPONSE
    ======================================================== */

    streamResponse(text) {

        const container =
            document.getElementById(
                'dialogue-groups'
            );

        if (!container) return;

        const message =
            document.createElement('div');

        message.className =
            'message sovereign-live-message';

        const content =
            document.createElement('div');

        content.className =
            'message-content';

        message.appendChild(content);

        container.appendChild(message);

        /* R-715: تقدّم بالزمن لا بالإطار (انظر dialogue-engine.streamText) */

        let index = 0;

        const total = text.length;

        const startedAt = performance.now();

        const durationMs = Math.min(1200, Math.max(200, total * 15));

        const stream = () => {

            index = document.hidden
                ? total
                : Math.min(
                    total,
                    Math.max(
                        index + 1,
                        Math.ceil(total * (performance.now() - startedAt) / durationMs)
                    )
                );

            content.textContent = text.slice(0, index);

            if (index < total) {

                requestAnimationFrame(stream);

            } else {

                this.finishResponse(
                    message
                );
            }
        };

        stream();

        if (
            window.SOVEREIGN_CINEMA
        ) {

            window.SOVEREIGN_CINEMA
                .enterScene(
                    'response'
                );
        }
    }

    /* ========================================================
       THINKING STATE
    ======================================================== */

    createThinkingState() {

        document.body.classList.add(
            'ai-thinking'
        );

        if (
            window.SOVEREIGN_CINEMA
        ) {

            window.SOVEREIGN_CINEMA
                .enterScene(
                    'thinking'
                );
        }
    }

    /* ========================================================
       REMOVE THINKING
    ======================================================== */

    removeThinkingState() {

        document.body.classList.remove(
            'ai-thinking'
        );
    }

    /* ========================================================
       FINISH RESPONSE
    ======================================================== */

    finishResponse(message) {

        message.classList.add(
            'response-complete'
        );

        if (
            window.SOVEREIGN_FX
        ) {

            window.SOVEREIGN_FX
                .cinematicFlash(0.6);
        }
    }

    /* ========================================================
       MEMORY
    ======================================================== */

    saveMemory(user, ai) {

        this.memory.push({
            user,
            ai,
            timestamp: Date.now()
        });

        if (
            this.memory.length > 50
        ) {

            this.memory.shift();
        }
    }

    /* ========================================================
       SYSTEM MESSAGE
    ======================================================== */

    emitSystemMessage(text) {

        console.warn(
            '[SOVEREIGN SYSTEM]',
            text
        );
    }

    /* ========================================================
       GET MEMORY
    ======================================================== */

    getMemory() {

        return this.memory;
    }
}

/* ============================================================
   إنشاء المحرك العالمي
============================================================ */

window.SOVEREIGN_AI =
    new SovereignLiveAI();
