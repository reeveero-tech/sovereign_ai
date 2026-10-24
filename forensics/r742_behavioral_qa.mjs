/* R-742 — سلوك حي لـ stt-input.js (دليل جنائي): تنفيذ فعلي للوحدة في Node
   ببيئة DOM/MediaRecorder/fetch وهمية. قابل لإعادة الإنتاج:
   node forensics/r742_behavioral_qa.mjs */

import { readFileSync } from 'node:fs';

const results = [];
const check = (name, ok) => {
    results.push(ok);
    console.log((ok ? 'PASS' : 'FAIL') + ' | ' + name);
};

const listeners = {};
const icon = { className: 'fas fa-microphone' };
const button = {
    attrs: {}, classList: { toggle() {} },
    addEventListener(ev, fn) { listeners[ev] = fn; },
    setAttribute(k, v) { this.attrs[k] = v; },
    querySelector: () => icon
};
const chatInput = { value: '', events: 0, dispatchEvent() { this.events++; }, focus() {} };
globalThis.document = {
    getElementById: id => id === 'btn-stt-mic' ? button : id === 'chat-input' ? chatInput : null
};
globalThis.Event = class { constructor(t) { this.type = t; } };
globalThis.window = globalThis;
const notes = [];
globalThis.SOVEREIGN_NOTIFY = { warning: m => notes.push(m), error: m => notes.push(m) };
let sendCalls = 0;
globalThis.SOVEREIGN_CHAT_RUNTIME = { sendMessage: () => sendCalls++ };

let tracksStopped = 0;
let micAllowed = true;
Object.defineProperty(globalThis, 'navigator', { value: {
    mediaDevices: {
        getUserMedia: async () => {
            if (!micAllowed) throw new Error('denied');
            return { getTracks: () => [{ stop: () => tracksStopped++ }] };
        }
    }
}, configurable: true });

let recorderMime = 'audio/webm;codecs=opus';
globalThis.MediaRecorder = class {
    static isTypeSupported(t) { return t === 'audio/webm'; }
    constructor(stream, opts) { this.mimeType = recorderMime; this.l = {}; }
    addEventListener(ev, fn) { this.l[ev] = fn; }
    start() {}
    stop() {
        this.l.dataavailable?.({ data: { size: 100, type: this.mimeType } });
        this.l.stop?.();
    }
};
globalThis.Blob = class { constructor(parts, o) { this.type = o.type; this.size = parts.length * 100; } };
globalThis.FormData = class { constructor() { this.e = []; } append(...a) { this.e.push(a); } };

let calls = [];
let response = null;
globalThis.fetch = async (url, opts) => { calls.push({ url, opts }); return response; };

eval(readFileSync(new URL('../frontend/js/modules/stt-input.js', import.meta.url), 'utf-8'));
const stt = globalThis.SOVEREIGN_STT_INPUT;
const flush = () => new Promise(r => setTimeout(r, 10));

/* ١: تسجيل ناجح بنوع codecs=opus → رفع بنوع مطبّع audio/webm */
response = { ok: true, status: 200, json: async () => ({ text: 'مرحبا يا سيادي' }) };
await listeners.click();
check('النقر الأول يبدأ التسجيل', stt.recording === true && button.attrs['aria-pressed'] === 'true');
await listeners.click(); await flush();
check('النقر الثاني يوقف التسجيل ويحرر الميكروفون', stt.recording === false && tracksStopped === 1);
check('طلب واحد إلى /stt', calls.length === 1 && calls[0].url === '/stt');
const [field, blob, fname] = calls[0].opts.body.e[0];
check('النوع مطبَّع: audio/webm (لا codecs) — لن يُرفض 415', field === 'file' && blob.type === 'audio/webm');
check('اسم الملف بامتداد صحيح', fname === 'recording.webm');
check('النص وُضع في مربع الإدخال', chatInput.value === 'مرحبا يا سيادي' && chatInput.events === 1);
check('لا إرسال آلي باسم المالك', sendCalls === 0);

/* ٢: 503 معطل → تحذير بلا نص */
calls = []; notes.length = 0; chatInput.value = '';
response = { ok: false, status: 503, json: async () => ({}) };
await listeners.click(); await listeners.click(); await flush();
check('503: لا نص في الإدخال', chatInput.value === '');
check('503: تحذير معلن بالسبب', notes.some(n => /معطل/.test(n)));

/* ٣: 502 → لا نص مختلق */
notes.length = 0;
response = { ok: false, status: 502, json: async () => ({}) };
await listeners.click(); await listeners.click(); await flush();
check('502: لا نص مختلق', chatInput.value === '' && notes.length === 1);

/* ٤: استجابة بلا نص */
notes.length = 0;
response = { ok: true, status: 200, json: async () => ({ text: '  ' }) };
await listeners.click(); await listeners.click(); await flush();
check('نص فارغ: لا إدخال وتحذير معلن', chatInput.value === '' && notes.length === 1);

/* ٥: نوع تسجيل خارج العقد → لا طلب */
calls = []; notes.length = 0; recorderMime = 'audio/x-unknown';
await listeners.click(); await listeners.click(); await flush();
check('نوع خارج العقد: لا طلب شبكة', calls.length === 0 && notes.length === 1);
recorderMime = 'audio/webm;codecs=opus';

/* ٦: رفض إذن الميكروفون */
notes.length = 0; micAllowed = false;
await listeners.click();
check('رفض الإذن: لا تسجيل وتحذير معلن', stt.recording === false && notes.some(n => /إذن/.test(n)));
micAllowed = true;

/* ٧: نص موجود في الإدخال يُلحق لا يُستبدل */
chatInput.value = 'بداية';
response = { ok: true, status: 200, json: async () => ({ text: 'تكملة' }) };
await listeners.click(); await listeners.click(); await flush();
check('النص يُلحق بما كتبه المالك لا يمحوه', chatInput.value === 'بداية تكملة');

const passed = results.filter(Boolean).length;
console.log(`SUMMARY: ${passed}/${results.length} PASS`);
if (passed !== results.length) process.exit(1);
