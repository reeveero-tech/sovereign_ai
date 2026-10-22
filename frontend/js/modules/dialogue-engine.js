/* ============================================================
   Sovereign AI — dialogue-engine.js
   الإصدار: 5.0.0
   محرك الحوار السيادي
   ============================================================ */

class SovereignDialogueEngine {

    constructor() {

        this.messages = [];

        this.container = null;

        this.initialized = false;

        console.log(
            '💬 Dialogue Engine Initialized'
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.container =
            document.getElementById(
                'dialogue-groups'
            );

        if (!this.container) {

            console.warn(
                'Dialogue Container Missing'
            );

            return;
        }

        this.initialized = true;
    }

    /* ========================================================
       ADD USER MESSAGE
    ======================================================== */

    addUserMessage(text) {

        this.createMessage({
            type: 'user',
            text
        });

        if (
            window.SOVEREIGN_CINEMA
        ) {

            window.SOVEREIGN_CINEMA
                .pulse(1.1);
        }
    }

    /* ========================================================
       ADD AI MESSAGE
    ======================================================== */

    addAIMessage(text) {

        this.createMessage({
            type: 'ai',
            text
        });

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
       CREATE MESSAGE
    ======================================================== */

    createMessage(data) {

        if (!this.container) return;

        const message =
            document.createElement('div');

        message.className =
            `
            message
            sovereign-live-message
            ${data.type}
            `;

        const meta =
            document.createElement('div');

        meta.className =
            'message-meta';

        meta.innerHTML = `
            <span class="message-type">
                ${
                    data.type === 'user'
                    ? 'السيد'
                    : 'الذكاء السيادي'
                }
            </span>

            <span class="message-time">
                ${
                    new Date()
                    .toLocaleTimeString('ar-SA')
                }
            </span>
        `;

        const content =
            document.createElement('div');

        content.className =
            'message-content';

        message.appendChild(meta);

        message.appendChild(content);

        this.container.appendChild(
            message
        );

        this.messages.push(data);

        if (
            data.type === 'ai'
        ) {

            this.streamText(
                content,
                data.text
            );

        } else {

            content.textContent =
                data.text;
        }

        this.scrollToBottom();

        this.saveMemory(data);
    }

    /* ========================================================
       STREAM TEXT
    ======================================================== */

    streamText(
        element,
        text
    ) {

        /* R-715: كان يكتب حرفًا واحدًا لكل إطار ⇒ عند 9 FPS يستغرق رد من
           300 حرف أكثر من 30 ثانية، ويتوقف نهائيًا إن كان التبويب في
           الخلفية. الآن: التقدّم بالزمن (يكتمل خلال ~1.2 ثانية مهما كان
           معدّل الإطارات)، والنص كاملًا فورًا إن كانت الصفحة مخفية. */

        let index = 0;

        const total = text.length;

        const startedAt = performance.now();

        const durationMs = Math.min(1200, Math.max(200, total * 15));

        const stream = () => {

            if (document.hidden) {
                index = total;
            } else {
                const elapsed = performance.now() - startedAt;
                index = Math.min(
                    total,
                    Math.max(index + 1, Math.ceil(total * elapsed / durationMs))
                );
            }

            element.textContent = text.slice(0, index);

            if (
                index < total
            ) {

                requestAnimationFrame(
                    stream
                );

            } else {

                element.parentElement
                    ?.classList
                    .add(
                        'response-complete'
                    );
            }
        };

        stream();
    }

    /* ========================================================
       SCROLL
    ======================================================== */

    scrollToBottom() {

        requestAnimationFrame(() => {

            this.container.scrollTop =
                this.container.scrollHeight;
        });
    }

    /* ========================================================
       MEMORY
    ======================================================== */

    saveMemory(data) {

        if (
            !window.SOVEREIGN_MEMORY
        ) return;

        if (
            data.type === 'ai'
        ) {

            const lastUser =
                this.messages
                    .filter(
                        m => m.type === 'user'
                    )
                    .slice(-1)[0];

            if (lastUser) {

                window.SOVEREIGN_MEMORY
                    .saveInteraction(
                        lastUser.text,
                        data.text
                    );
            }
        }
    }

    /* ========================================================
       CLEAR
    ======================================================== */

    clear() {

        this.messages = [];

        if (this.container) {

            this.container.innerHTML = '';
        }
    }

    /* ========================================================
       GET MESSAGES
    ======================================================== */

    getMessages() {

        return this.messages;
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_DIALOGUE =
    new SovereignDialogueEngine();
