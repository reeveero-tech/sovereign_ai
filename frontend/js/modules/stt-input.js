/* ============================================================
   Sovereign AI — stt-input.js
   R-742 (البند ٢.٣ — الجولة الموثقة «اللاحقة»): زر الميكروفون —
   تسجيل عبر MediaRecorder → POST /stt → النص في مربع الإدخال
   للمراجعة (لا إرسال آلي باسم المالك).
   ============================================================ */

class SovereignSttInput {

    constructor() {

        /* أنواع الرفع المفضلة — كلها ضمن STT_ALLOWED_CONTENT_TYPES
           في الخادم حرفيًا (حارس test_mic_ui) */
        this.uploadTypes = [
            'audio/webm',
            'audio/ogg',
            'audio/mp4'
        ];

        /* حد الحجم — نفس حد الخادم (25MiB افتراضيًا) */
        this.maxBytes = 25 * 1024 * 1024;

        this.recorder = null;
        this.stream = null;
        this.chunks = [];
        this.recording = false;
        this.uploading = false;

        this.init();
    }

    init() {

        const button =
            document.getElementById('btn-stt-mic');

        if (!button) return;

        this.button = button;

        button.addEventListener(
            'click',
            () => this.toggle()
        );
    }

    async toggle() {

        if (this.uploading) return;

        if (this.recording) {
            this.stop();
            return;
        }

        await this.start();
    }

    /* نوع أساسي بلا معاملات: المتصفح يعطي «audio/webm;codecs=opus»
       والخادم يطابق النوع حرفيًا — بلا تطبيع يُرفض كل تسجيل 415 */
    baseType(mime) {
        return (mime || '').split(';')[0].trim().toLowerCase();
    }

    pickRecorderType() {
        if (typeof MediaRecorder?.isTypeSupported !== 'function') return '';
        return this.uploadTypes.find(
            t => MediaRecorder.isTypeSupported(t)
        ) || '';
    }

    async start() {

        if (!navigator.mediaDevices?.getUserMedia
            || typeof MediaRecorder === 'undefined') {
            window.SOVEREIGN_NOTIFY
                ?.warning('المتصفح لا يدعم تسجيل الصوت');
            return;
        }

        try {
            this.stream =
                await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (error) {
            window.SOVEREIGN_NOTIFY
                ?.warning('رُفض إذن الميكروفون — لا تسجيل');
            return;
        }

        const preferred = this.pickRecorderType();
        this.recorder = preferred
            ? new MediaRecorder(this.stream, { mimeType: preferred })
            : new MediaRecorder(this.stream);

        this.chunks = [];

        this.recorder.addEventListener(
            'dataavailable',
            (e) => { if (e.data && e.data.size) this.chunks.push(e.data); }
        );

        this.recorder.addEventListener(
            'stop',
            () => this.upload()
        );

        this.recorder.start();
        this.setRecording(true);
    }

    stop() {
        try { this.recorder?.stop(); } catch (e) { /* أُوقف مسبقًا */ }
        this.stream?.getTracks().forEach(t => t.stop());
        this.stream = null;
        this.setRecording(false);
    }

    setRecording(state) {
        this.recording = state;
        if (!this.button) return;
        this.button.setAttribute('aria-pressed', state ? 'true' : 'false');
        this.button.classList.toggle('recording', state);
        const icon = this.button.querySelector('i');
        if (icon) icon.className = state ? 'fas fa-stop' : 'fas fa-microphone';
    }

    async upload() {

        const type = this.baseType(
            this.recorder?.mimeType || this.chunks[0]?.type
        );

        if (!this.chunks.length) {
            window.SOVEREIGN_NOTIFY?.warning('لم يُلتقط صوت');
            return;
        }

        if (!this.uploadTypes.includes(type)) {
            window.SOVEREIGN_NOTIFY
                ?.warning(`نوع التسجيل غير مدعوم في الخادم (${type || 'غير معروف'})`);
            return;
        }

        const blob = new Blob(this.chunks, { type });
        this.chunks = [];

        if (blob.size > this.maxBytes) {
            window.SOVEREIGN_NOTIFY
                ?.warning('التسجيل أكبر من الحد (25MiB) — سجّل مقطعًا أقصر');
            return;
        }

        this.uploading = true;

        try {

            const ext = type.split('/')[1];
            const body = new FormData();
            body.append('file', blob, `recording.${ext}`);

            const response =
                await fetch('/stt', { method: 'POST', body });

            const messages = {
                503: 'السمع معطل على الخادم (STT_ENABLED) — فعّله من الأسرار',
                502: 'خدمة السمع لم تُرجع نصًا — لا نص مختلق',
                413: 'التسجيل أكبر من حد الخادم (25MiB)',
                415: 'الخادم رفض نوع التسجيل (415)',
                429: 'تجاوزت حد طلبات السمع — أعد المحاولة لاحقًا'
            };

            if (messages[response.status]) {
                window.SOVEREIGN_NOTIFY?.warning(messages[response.status]);
                return;
            }

            if (!response.ok) {
                window.SOVEREIGN_NOTIFY
                    ?.warning(`تعذر تحويل الكلام (${response.status})`);
                return;
            }

            const data = await response.json();
            const text = (data?.text || '').trim();

            if (!text) {
                window.SOVEREIGN_NOTIFY
                    ?.warning('استجابة السمع بلا نص — لا نص مختلق');
                return;
            }

            /* النص في مربع الإدخال للمراجعة — المالك يرسله بنفسه */
            const input = document.getElementById('chat-input');
            if (input) {
                input.value = input.value
                    ? `${input.value} ${text}`
                    : text;
                input.dispatchEvent(new Event('input'));
                input.focus?.();
            }

        } catch (error) {

            console.error('STT Input Failed', error);
            window.SOVEREIGN_NOTIFY?.error('فشل إرسال التسجيل (شبكة/خادم)');

        } finally {

            this.uploading = false;
        }
    }
}

window.SOVEREIGN_STT_INPUT =
    new SovereignSttInput();
