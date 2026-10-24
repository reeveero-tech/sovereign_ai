/* R-741 — سلوك حي للوحدة (دليل جنائي — ليس اختبار CI):
   تنفيذ فعلي لـ vision-input.js في Node ببيئة DOM/fetch وهمية —
   إثبات أن الاختيار يرفع إلى /vision والفشل يعلن بصدق والنجاح
   يسلم للمحادثة. (المادة ٢: شاهد الفعل، لا السطور.) */

import { readFileSync } from 'node:fs';

const results = [];
const check = (name, ok, detail = '') => {
    results.push({ name, ok, detail });
    console.log((ok ? 'PASS' : 'FAIL') + ' | ' + name + (detail ? ' | ' + detail : ''));
};

/* ---------- وهم DOM ---------- */
const makeEl = () => ({
    listeners: {},
    addEventListener(ev, fn) { this.listeners[ev] = fn; },
    click() { this.listeners['click']?.(); },
    value: '',
    files: null
});
const button = makeEl();
const input = makeEl();

globalThis.document = {
    getElementById: (id) =>
        id === 'btn-vision-upload' ? button :
        id === 'vision-file-input' ? input : null
};

/* ---------- وهم الشبكة والدول ---------- */
let fetchCalls = [];
let fetchResponse = null;
globalThis.fetch = async (url, opts) => {
    fetchCalls.push({ url, opts });
    return fetchResponse;
};
globalThis.FormData = class FormData {
    constructor() { this.entries = []; }
    append(k, v) { this.entries.push([k, v]); }
};

const notifyCalls = [];
globalThis.window = globalThis;
globalThis.SOVEREIGN_NOTIFY = {
    warning: (m) => notifyCalls.push(['warning', m]),
    error: (m) => notifyCalls.push(['error', m])
};
let chatDelivery = null;
globalThis.SOVEREIGN_CHAT_RUNTIME = {
    receiveVisionDescription: (desc, name) => { chatDelivery = [desc, name]; }
};

/* ---------- تحميل الوحدة الفعلية ---------- */
const src = readFileSync(
    new URL('../frontend/js/modules/vision-input.js', import.meta.url),
    'utf-8');
eval(src);

const vision = globalThis.SOVEREIGN_VISION_INPUT;
check('الوحدة حُملت وأنشأت SOVEREIGN_VISION_INPUT', !!vision);

/* الزر مربوط: نقر الزر يفتح منتقي الملفات */
let inputClicked = false;
input.click = () => { inputClicked = true; };
button.click();
check('نقر الزر يفتح منتقي الملفات', inputClicked);

const fakeFile = (type, size) => ({
    type, size, name: 'test.' + (type.split('/')[1] || 'bin')
});

/* ---------- ١: نوع غير مسموح → لا طلب ---------- */
fetchCalls = []; notifyCalls.length = 0; chatDelivery = null;
input.files = [fakeFile('text/plain', 100)];
await vision.handleFile(input);
check('نوع غير مسموح: لا طلب شبكة', fetchCalls.length === 0);
check('نوع غير مسموح: تحذير معلن', notifyCalls.some(c => c[0] === 'warning'));

/* ---------- ٢: حجم زائد → لا طلب ---------- */
fetchCalls = []; notifyCalls.length = 0;
input.files = [fakeFile('image/png', 11 * 1024 * 1024)];
await vision.handleFile(input);
check('حجم زائد (11MiB): لا طلب شبكة', fetchCalls.length === 0);
check('حجم زائد: تحذير معلن', notifyCalls.some(c => c[0] === 'warning'));

/* ---------- ٣: صورة صالحة → رفع فعلي إلى /vision ---------- */
fetchCalls = []; notifyCalls.length = 0;
input.files = [fakeFile('image/png', 1024)];
fetchResponse = { ok: true, status: 200, json: async () => ({ description: 'قطة سوداء' }) };
await vision.handleFile(input);
check('صورة صالحة: طلب واحد إلى /vision',
    fetchCalls.length === 1 && fetchCalls[0].url === '/vision');
check('الرفع multipart يحمل الملف',
    fetchCalls[0]?.opts?.body?.entries?.some(([k, v]) => k === 'file' && v?.name?.startsWith('test.')));
check('الوصف سُلّم للمحادثة', chatDelivery?.[0] === 'قطة سوداء' && chatDelivery?.[1]?.startsWith('test.'));

/* ---------- ٤: 503 (معطلة) → تحذير + لا تسليم ---------- */
fetchCalls = []; notifyCalls.length = 0; chatDelivery = null;
input.files = [fakeFile('image/png', 1024)];
fetchResponse = { ok: false, status: 503, json: async () => ({}) };
await vision.handleFile(input);
check('503: لا تسليم للمحادثة', chatDelivery === null);
check('503: تحذير معلن بالسبب', notifyCalls.some(c => c[0] === 'warning' && /معطلة/.test(c[1])));

/* ---------- ٥: 502 (فشل الخدمة) → لا وصف مختلق ---------- */
chatDelivery = null; notifyCalls.length = 0;
input.files = [fakeFile('image/png', 1024)];
fetchResponse = { ok: false, status: 502, json: async () => ({}) };
await vision.handleFile(input);
check('502: لا تسليم ولا وصف مختلق', chatDelivery === null);
check('502: تحذير معلن', notifyCalls.some(c => c[0] === 'warning'));

/* ---------- ٦: استجابة بلا وصف → فشل معلن لا نجاح كاذب ---------- */
chatDelivery = null; notifyCalls.length = 0;
input.files = [fakeFile('image/png', 1024)];
fetchResponse = { ok: true, status: 200, json: async () => ({}) };
await vision.handleFile(input);
check('بلا description: لا تسليم', chatDelivery === null);
check('بلا description: تحذير معلن', notifyCalls.some(c => c[0] === 'warning'));

/* ---------- ٧: تجاوز أثناء رفع قائم (uploading flag) ---------- */
fetchCalls = [];
input.files = [fakeFile('image/png', 1024)];
fetchResponse = { ok: true, status: 200, json: async () => ({ description: 'x' }) };
const p1 = vision.handleFile(input);
input.files = [fakeFile('image/png', 2048)];
await vision.handleFile(input);   /* يجب أن تُرفض لأن الرفع الأول جارٍ */
await p1;
check('لا رفعان متزامنان (uploading flag)', fetchCalls.length === 1);

/* ---------- النتيجة ---------- */
const failed = results.filter(r => !r.ok);
console.log('SUMMARY: ' + (results.length - failed.length) + '/' + results.length + ' PASS');
if (failed.length) { console.log('FAILED CHECKS: ' + failed.map(f => f.name).join(' ; ')); process.exit(1); }
