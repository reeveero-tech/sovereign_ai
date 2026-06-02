/* ============================================================
   Sovereign AI — live-ai-engine.js
   الإصدار: 4.0.0
   محرك الذكاء الحي السيادي
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
                'تعذر الاتصال بالذكاء السيادي'
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

        let index = 0;

        const stream = () => {

            if (index < text.length) {

                content.textContent +=
                    text[index];

                index++;

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
