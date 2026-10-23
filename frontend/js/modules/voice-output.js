/* ============================================================
   Sovereign AI — voice-output.js
   R-740 (البند ٢.٤ — بأمر المالك «ابدأ»): صوت — نطق الردود (TTS)
   زر تبديل (btn-tts-toggle) + نطق ردود الذكاء عبر POST /tts.
   ============================================================ */

class SovereignVoiceOutput {

    constructor() {

        /* حالة التبديل تبقى بين الجلسات (localStorage) */
        this.storageKey = 'sov-tts-on';
        this.enabled =
            localStorage.getItem(this.storageKey) === '1';

        this.speaking = false;

        console.log(
            '🔊 Voice Output Initialized',
            { enabled: this.enabled }
        );

        this.init();
    }

    /* ========================================================
       INIT
    ======================================================== */

    init() {

        this.bindToggle();
        this.renderToggleState();
    }

    /* ========================================================
       TOGGLE — زر التشغيل/الإيقاف (مفتاح البند في الواجهة)
    ======================================================== */

    bindToggle() {

        const button =
            document.getElementById(
                'btn-tts-toggle'
            );

        if (!button) return;

        button.addEventListener(
            'click',
            () => this.toggle()
        );
    }

    toggle() {

        this.enabled = !this.enabled;

        localStorage.setItem(
            this.storageKey,
            this.enabled ? '1' : '0'
        );

        this.renderToggleState();

        window.SOVEREIGN_NOTIFY
            ?.info(
                this.enabled
                    ? 'نطق الردود مفعّل'
                    : 'نطق الردود متوقف'
            );
    }

    renderToggleState() {

        const button =
            document.getElementById(
                'btn-tts-toggle'
            );

        if (!button) return;

        const icon =
            button.querySelector('i');

        button.setAttribute(
            'aria-pressed',
            this.enabled ? 'true' : 'false'
        );

        if (icon) {

            icon.className =
                this.enabled
                    ? 'fas fa-volume-high'
                    : 'fas fa-volume-xmark';
        }
    }

    /* ========================================================
       SPEAK — نص → مقطع صوتي عبر POST /tts
       فشل صادق: تعطل النقطة يُعلن ولا يُخفى (503/502 → إشعار)
    ======================================================== */

    async speak(text) {

        if (
            !this.enabled ||
            !text ||
            this.speaking
        ) return;

        this.speaking = true;

        try {

            const response =
                await fetch('/tts', {
                    method: 'POST',
                    headers: {
                        'Content-Type':
                            'application/json'
                    },
                    body: JSON.stringify({
                        text: String(text).slice(0, 2000)
                    })
                });

            if (response.status === 503) {

                /* تعطل النطق يُعلن بصدق — لا صمت كاذب */
                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'النطق معطل على الخادم (TTS_ENABLED) — فعّله من الأسرار'
                    );

                return;
            }

            if (!response.ok) {

                window.SOVEREIGN_NOTIFY
                    ?.warning(
                        'تعذر نطق الرد (خدمة النطق لم تُرجع صوتًا)'
                    );

                return;
            }

            const blob =
                await response.blob();

            const audio =
                new Audio(
                    URL.createObjectURL(blob)
                );

            audio.play();

        } catch (error) {

            console.error(
                'Voice Output Failed',
                error
            );

        } finally {

            this.speaking = false;
        }
    }
}

/* ============================================================
   إنشاء النظام العالمي
============================================================ */

window.SOVEREIGN_VOICE =
    new SovereignVoiceOutput();
