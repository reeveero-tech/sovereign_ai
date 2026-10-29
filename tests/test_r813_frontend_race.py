# -*- coding: utf-8 -*-
"""R-813 (تصحيح المراجعة الثالثة) — اختبار سلوكي حقيقي لمنطق المحادثات في
الواجهة: يُشغَّل كود الواجهة الفعلي (المستخرج من index.html) في Node مع
كوابيل، وتُتحكم أزمنة الاستجابات يدويًا لاختبار السباق بترتيب معكوس.

يغطي مطالب المراجعة الثالثة:
١) سقف الضيف: ١٠٥ محادثات برسائل مميزة (٥ لكل محادثة) ⇒ التخزين يحفظها
   كلها كاملة، وأقدمها (g0 — الإضافة في المقدمة تجعل الأولى أقدمها) تُستعاد
   كاملة بعد إعادة تحميل التخزين.
٢) سباق persistConv (مسار المالك) بترتيب معكوس: A يبدأ، ننتقل إلى B،
   استجابة B تكتمل أولًا ثم رد A المتأخر — الحارس يمنع فساد هوية B.
٣) فتح A وB بعد السباق من بيانات حُفظت فعلًا بطلبات الاختبار (مخزن POST/GET
   مصغّر بالمعرف) — والمعرفات والرسائل والنماذج بلا اختلاط.
٤) فشل حفظ التخزين (امتلاء المساحة) ظاهر لا صامت: الحفظ يفشل والتبديل
   يتوقف والمحادثة الجارية لا تُفرَّغ باعتبارها محفوظة.
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UI = REPO_ROOT / "frontend" / "chat" / "index.html"

HARNESS = r"""
'use strict';
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');

// استخراج دالة كاملة من المصدر بمطابقة الأقواس
function extractFn(name) {
  const start = html.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('function not found: ' + name);
  let realStart = start;
  if (html.slice(Math.max(0, start - 6), start) === 'async ') realStart = start - 6;  // لا تُفقد async
  let i = html.indexOf('{', realStart), depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i; break; } }
  }
  return html.slice(realStart, end + 1);  // async محفوظة إن وُجدت
}

// ---- كوابيل البيئة ----
const store = new Map();
let quotaExceeded = false;
global.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => {
    if (quotaExceeded) { const e = new Error('QuotaExceededError'); throw e; }
    store.set(k, String(v));
  },
  removeItem: (k) => store.delete(k),
};
global.CONV_LOCAL = 'sovereign.localConvs';
const state = { sessionId: null, convId: null, messages: [], model: null };
let ownerKeyValue = 'test-owner-key';
function ownerKey() { return ownerKeyValue; }
function save() {}
function renderChat() {}
function paintConvs() {}
function paintModelSel() {}
function go() {}
function toast() {}
function loadConvs() {}
let navSeq = 0;   // R-813 (خامسة): معرّف عملية التنقل — مشترك مع الدوال المستخرجة
function el(tag, cls, txt) { return { className: cls, textContent: txt }; }
function $(id) { return { appendChild() {}, textContent: '', hidden: false }; }

// ---- مخزن محادثات مصغّر حقيقي: POST يحفظ فعلًا وGET يُعيد بالمعرف ----
const convStore = new Map();
const apiCalls = [];
const apiBodies = [];
const pendingApi = [];
let idSeq = 0;
let failNextSave = false;
function api(url, opts) {
  apiCalls.push({ url, method: opts && opts.method });
  return new Promise((resolve, reject) => {
    const rec = { resolve, reject };
    if (url === '/ws/conversations' && (!opts.method || opts.method === 'POST')) {
      const body = JSON.parse(JSON.stringify(opts.json));
      if (!body.id) { body.id = 'srv-' + (++idSeq); }  // الخادم يعين المعرف عند الاستلام لا عند التشغيل
      apiBodies.push(body);
      if (failNextSave) {   // الخادم يرفض الحفظ القادم (اختبار مسار المالك) — لمرة واحدة عند الإنشاء
        failNextSave = false;
        rec.run = () => rec.reject(new Error('500'));
      } else {
        rec.run = () => { convStore.set(body.id, body); resolve({ id: body.id }); };
      }
    } else if (/^\/ws\/conversations\/(.+)$/.test(url)) {
      const id = url.split('/').pop();
      rec.run = () => {
        if (opts && opts.method === 'PUT') {   // تحديث حقيقي للسجل المحفوظ
          const c = convStore.get(id);
          if (!c) { rec.reject(new Error('غير موجودة')); return; }
          Object.assign(c, JSON.parse(JSON.stringify(opts.json)));
          resolve({ id });
          return;
        }
        const c = convStore.get(id);
        if (!c) { rec.reject(new Error('غير موجودة')); return; }
        resolve({ id: c.id, messages: c.messages, model: c.model, title: c.title });
      };
    } else {
      rec.run = () => resolve({});
    }
    pendingApi.push(rec);
  });
}
const tick = () => new Promise((r) => setImmediate(r));

// ---- الوظائف الحية من الواجهة — تُقيَّم معًا في نطاق واحد ----
const FN_NAMES = ['loadLocalConvs', 'saveLocalConvs', 'convTitle', 'upsertLocalConv',
                  'keepCurrentConversationBeforeNew', 'persistConv', 'openLocalConv',
                  'openConv'];
const fns = {};
eval(FN_NAMES.map((n) => extractFn(n)).join('\n') +
     '\n; FN_NAMES.forEach((n) => { fns[n] = eval(n); });');
let localConvs = fns.loadLocalConvs();

const results = [];
function check(name, cond) { results.push((cond ? 'PASS' : 'FAIL') + ' :: ' + name); }

(async () => {
// ================= ١) سقف التخزين: ١٠٥ محادثات برسائل مميزة =================
for (let i = 0; i < 105; i++) {
  const msgs = [];
  for (let m = 0; m < 5; m++)
    msgs.push({ role: m % 2 ? 'assistant' : 'user', content: `رسالة ${i}-${m}` });
  fns.upsertLocalConv({ id: 'g' + i, title: 'محادثة ' + i, messages: msgs,
    updated_at: 1000 + i, model: 'm' + (i % 3) });
}
const stored = JSON.parse(localStorage.getItem('sovereign.localConvs'));
check('التخزين يحفظ ١٠٥ محادثات بلا اقتطاط', stored.length === 105);
check('كل المحادثات كاملة الرسائل الخمس', stored.every(c => c.messages.length === 5));
const g0 = stored.find(c => c.id === 'g0');
check('أقدم محادثة (g0 — الإضافة في المقدمة) محفوظة كاملة',
      g0 && g0.messages.length === 5 && g0.messages[4].content === 'رسالة 0-4');

// استعادة أقدمها كاملة بعد إعادة تحميل التخزين (لا من الذاكرة العابرة)
localConvs = fns.loadLocalConvs();
state.sessionId = 'current'; state.messages = [];  // لا جارية ⇒ لا حفظ وهمي يلوث القسم التالي
await fns.openLocalConv('g0');
check('فتح أقدم محادثة بعد إعادة التحميل يستعيد رسائلها الخمس كاملة',
      state.messages.length === 5 && state.messages[0].content === 'رسالة 0-0' &&
      state.messages[4].content === 'رسالة 0-4');
check('فتحها يستعيد نموذجها', state.model === 'm0');

// ================= ٢) سباق persistConv بترتيب معكوس (مسار المالك) =================
// محادثة A نشطة: حفظها يبدأ ولا تكتمل استجابته بعد
state.sessionId = 'A'; state.convId = null; state.model = 'mA';
state.messages = [{ role: 'user', content: 'سؤال A' },
                  { role: 'assistant', content: 'رد A-1' },
                  { role: 'user', content: 'تتمة A' },
                  { role: 'assistant', content: 'رد A-2' }];
fns.persistConv();                     // نداء A — استجابته معلقة
const bodyA = apiBodies[apiBodies.length - 1];
check('نداء A حُمل بمحتوى A كاملًا ونموذجها',
      bodyA.messages.length === 4 && bodyA.messages[0].content === 'سؤال A' &&
      bodyA.model === 'mA');

// ننتقل إلى B ونحفظها — تكتمل استجابة B أولًا
state.sessionId = 'B'; state.convId = null; state.model = 'mB';
state.messages = [{ role: 'user', content: 'سؤال B' },
                  { role: 'assistant', content: 'رد B-1' }];
fns.persistConv();                     // نداء B
const bodyB = apiBodies[apiBodies.length - 1];
check('نداءان معلقان (A ثم B)', pendingApi.length === 2);
check('نداء B حُمل بمحتوى B ونموذجها',
      bodyB.messages.length === 2 && bodyB.messages[0].content === 'سؤال B' &&
      bodyB.model === 'mB');
pendingApi[1].run();                   // B تكتمل أولًا
await tick();
check('استجابة B تثبت هوية B', state.convId === 'srv-2');
check('B محفوظة فعلًا في المخزن بالمعرف',
      convStore.has('srv-2') && convStore.get('srv-2').messages.length === 2 &&
      convStore.get('srv-2').model === 'mB');

// استجابة A المتأخرة تكتمل الآن (بعد التبديل) — الحارس يجب أن يمنع فساد B
pendingApi[0].run();                   // A تكتمل أخيرًا (بعد التبديل)
await tick();
check('حارس العرق يمنع فساد هوية B برد A المتأخر', state.convId === 'srv-2');
check('جلسة العرض بقيت B', state.sessionId === 'B');
check('A محفوظة فعلًا في المخزن بالمعرف',
      convStore.has('srv-1') && convStore.get('srv-1').messages.length === 4 &&
      convStore.get('srv-1').model === 'mA');

// ================= ٣) فتح A وB من البيانات المحفوظة فعلًا — بلا اختلاط =====
async function openConvAndWait(id) {           // قيادة النداءين المعلقين: GET ثم PUT الحفظ
  fns.openConv(id);
  const gi = pendingApi.length - 1;            // GET الاسترجاع معلق
  pendingApi[gi].run(); await tick();           // يكتمل → .then يحفظ الجارية (PUT) ثم يفتح
  if (pendingApi.length > gi + 1) { pendingApi[pendingApi.length - 1].run(); await tick(); }
}
await openConvAndWait('srv-1');
check('فتح A من المخزن يثبت معرفها', state.sessionId === 'srv-1' && state.convId === 'srv-1');
check('فتح A يستعيد رسائلها الأربع كاملة لا B',
      state.messages.length === 4 && state.messages[0].content === 'سؤال A' &&
      state.messages[3].content === 'رد A-2');
check('نموذج A مستعاد من المخزن', state.model === 'mA');
await openConvAndWait('srv-2');
check('فتح B من المخزن يثبت معرفها', state.sessionId === 'srv-2' && state.convId === 'srv-2');
check('فتح B يستعيد رسائلها لا A',
      state.messages.length === 2 && state.messages[0].content === 'سؤال B' &&
      state.messages[1].content === 'رد B-1');
check('نموذج B مستعاد من المخزن', state.model === 'mB');

// ================= ٤) الحفظ قبل التبديل: يرسل الجارية ويرجع النتيجة ==========
state.sessionId = 'B'; state.convId = 'srv-2'; state.model = 'mB';
state.messages = [{ role: 'user', content: 'سؤال B' },
                  { role: 'assistant', content: 'رد B جديد' }];
apiCalls.length = 0; pendingApi.length = 0;
const okSwitchP = fns.keepCurrentConversationBeforeNew();  // وعد — النتيجة الفعلية تُنتظر
check('الحفظ قبل التبديل يبدأ نداء الجارية (B)', apiCalls.length === 1);
pendingApi[0].run(); await tick();
const okSwitch = await okSwitchP;
check('الحفظ قبل التبديل يرسل محتوى الجارية (B) بنموذجها',
      convStore.get('srv-2').messages[1].content === 'رد B جديد' &&
      convStore.get('srv-2').model === 'mB');
check('نجاح الحفظ يعيد true (يسمح بالتبديل)', okSwitch === true);

// ================= ٥) فشل حفظ التخزين (امتلاء المساحة) ظاهر لا صامت ============
quotaExceeded = true;   // كل setItem يفشل من الآن — QuotaExceededError
ownerKeyValue = null;   // مسار الضيف — المفتاح الوحيد هو التخزين المحلي
state.sessionId = 'C'; state.convId = null; state.model = 'mC';
state.messages = [{ role: 'user', content: 'رسالة C الحرجة' }];
const before = state.messages.slice();
const failedSwitchP = fns.keepCurrentConversationBeforeNew();   // وعد — مسار الضيف
const failedSwitch = await failedSwitchP;
check('فشل الحفظ يُعاد للمنادي (لا نجاح صامت كاذب)', failedSwitch === false);
check('المحادثة الجارية لم تُفرَّغ باعتبارها محفوظة',
      state.messages.length === 1 && state.messages[0].content === 'رسالة C الحرجة');
// والزر يوقف التفريغ: `if (!(await keepCurrentConversationBeforeNew())) return;`

// ================= ٦) فشل حفظ الخادم في مسار المالك يوقف التبديل ================
// (تصحيح المراجعة الرابعة: نتيجة الحفظ الفعلية تُنتظر — لا نجاح صامت كاذب للمالك)
quotaExceeded = false; ownerKeyValue = 'test-owner-key';   // مسار المالك من جديد
state.sessionId = 'D'; state.convId = null; state.model = 'mD';
state.messages = [{ role: 'user', content: 'رسالة D الحرجة' }];
apiCalls.length = 0; pendingApi.length = 0;
failNextSave = true;                    // الخادم سيرفض نداء الحفظ القادم
const dSwitchP = fns.keepCurrentConversationBeforeNew();   // وعد ينتظر نتيجة الحفظ الفعلية
check('حفظ المالك بدأ نداءً حقيقيًا', apiCalls.length === 1);
pendingApi[pendingApi.length - 1].run();                    // الخادم يرفض → الرفض يصعد للمنادي
await tick();
const dSwitch = await dSwitchP;
check('رفض الخادم يعاد للمنادي في مسار المالك (لا نجاح صامت كاذب)', dSwitch === false);
check('المحادثة الجارية للمالك سليمة — لم تُفرَّغ',
      state.messages.length === 1 && state.messages[0].content === 'رسالة D الحرجة');

// ===== ٧) تنقل متداخل: فتح B ينتظر حفظ A، فتح C يكتمل أولًا، والقديم لا يفتح B =====
// (تصحيح المراجعة الخامسة: معرّف تنقل متزايد + النتيجة القديمة إلغاء لا نجاح)
state.sessionId = 'A'; state.convId = null; state.model = 'mA';
state.messages = [{ role: 'user', content: 'رسالة A' }];
apiCalls.length = 0; pendingApi.length = 0; navSeq = 0;
convStore.set('B', { id: 'B', title: 'B', model: 'mB',
                    messages: [{ role: 'user', content: 'سؤال B' }, { role: 'assistant', content: 'رد B' }] });
convStore.set('C', { id: 'C', title: 'C', model: 'mC',
                    messages: [{ role: 'user', content: 'سؤال C' }, { role: 'assistant', content: 'رد C' }] });
fns.openConv('B');                    // التنقل الأقدم: GET(B) معلق (myNav=1)
failNextSave = true;                  // الخادم سيرفض حفظ A المرتبط بفتح B
const getB = pendingApi.length - 1;
pendingApi[getB].run(); await tick(); // GET(B) يكتمل → المعالج ينتظر حفظ A (وسيرفض)
fns.openConv('C');                    // تنقل أحدث (myNav=2) — يلغي الأقدم عند الفحص
const getC = pendingApi.length - 1;
pendingApi[getC].run(); await tick(); // GET(C) يكتمل → المعالج ينتظر حفظ الجارية (A)
const saveC = pendingApi.length - 1;
pendingApi[saveC].run(); await tick(); // حفظ C يكتمل أولًا ⇒ تُفتح C فعلًا
check('فتح C الأحدث اكتمل فعلًا', state.sessionId === 'C' && state.messages.length === 2);
state.messages.push({ role: 'user', content: 'رسالة C الجديدة' });   // المستخدم يكتب في C
const saveB = getB + 1;               // رد الحفظ القديم (المرتبط بفتح B) يصل الآن مرفوضًا
pendingApi[saveB].run(); await tick(); // القديم: الجلسة تبدلت ⇒ إلغاء (لا نجاح يفتح B)
check('العملية القديمة لم تفتح B — C باقية برسالتها الجديدة',
      state.sessionId === 'C' && state.messages.length === 3 &&
      state.messages[2].content === 'رسالة C الجديدة');
// والنجاح القديم أيضًا إلغاء: نتيجة قديمة = false لا true
state.sessionId = 'A2'; state.convId = null; state.model = 'mA';
state.messages = [{ role: 'user', content: 'رسالة A2' }];
apiCalls.length = 0; pendingApi.length = 0;
const staleP = fns.keepCurrentConversationBeforeNew();  // حفظ A2 يبدأ
const staleSave = pendingApi.length - 1;
state.sessionId = 'أحدث';          // تنقل أحدث بدأ أثناء انتظار الحفظ
pendingApi[staleSave].run(); await tick();
check('النتيجة القديمة إلغاء (false) لا نجاح (true)', (await staleP) === false);

// ===== ٨) حراسة navSeq مستقلة عن نتيجة الحفظ: بدء الأحدث وحده يلغي الأقدم =====
// (تصحيح المراجعة السادسة: الحفظ ينجح والجلسة لم تتغير — ومع ذلك لا يفتح الأقدم)
state.sessionId = 'A'; state.convId = null; state.model = 'mA';
state.messages = [{ role: 'user', content: 'رسالة A' }];
apiCalls.length = 0; pendingApi.length = 0; navSeq = 0;
fns.openConv('B');                      // تنقل قديم (myNav=1): GET(B) معلق
const gB = pendingApi.length - 1;
pendingApi[gB].run(); await tick();     // GET(B) يكتمل → المعالج ينتظر حفظ A (سينجح)
const sB = pendingApi.length - 1;
fns.openConv('C');                      // تنقل أحدث (myNav=2) — GET الخاص بها يبقى معلقًا
const gC = pendingApi.length - 1;
check('تنقل C الأحدث بدأ ولم يكتمل (GET معلق)', gC === sB + 1);
pendingApi[sB].run(); await tick();     // حفظ A ينجح والجلسة ما زالت A ⇒ النتيجة true
check('نجاح حفظ الأقدم لا يفتحه — بدء الأحدث وحده ألغاه',
      state.sessionId === 'A' && state.messages.length === 1 &&
      state.messages[0].content === 'رسالة A');
pendingApi[gC].run(); await tick();     // ثم يكتمل GET الأحدث فتُفتح C (الأحدث فقط يفتح)
if (pendingApi.length > gC + 1) { pendingApi[pendingApi.length - 1].run(); await tick(); }  // وحفظ A قبلها (PUT)
check('التنقل الأحدث هو الذي يفتح', state.sessionId === 'C' &&
      state.messages[0].content === 'سؤال C' &&           // رسائل C (تضمنت رسالة المستخدم من قسم ٧)
      state.messages[state.messages.length - 1].content === 'رسالة C الجديدة');

// ===== ٩) إعادة اختيار المحادثة المحلية الحالية تُلغي التنقل الأقدم المعلق =====
state.sessionId = 'A'; state.convId = null; state.model = 'mA';
state.messages = [{ role: 'user', content: 'رسالة A الحالية' }];
localConvs = [{ id: 'A', title: 'A', model: 'mA', messages: state.messages.slice() }];
apiCalls.length = 0; pendingApi.length = 0; navSeq = 0;
fns.openConv('B');                      // تنقل قديم (myNav=1) معلق على GET(B)
const gB2 = pendingApi.length - 1;
await fns.openLocalConv('A');           // إعادة اختيار الحالية (myNav=2) — تُلغي الأقدم وتخرج
check('إعادة اختيار الحالية لم تعِد تحميل رسائلها', state.messages.length === 1 &&
      state.messages[0].content === 'رسالة A الحالية');
pendingApi[gB2].run(); await tick();    // رد GET القديم يصل الآن — ملغى بمعرّف التنقل
check('التنقل القديم لم يفتح B — الحالية باقية',
      state.sessionId === 'A' && state.messages[0].content === 'رسالة A الحالية');
})().then(() => {
  console.log(results.join('\n'));
  if (results.some(r => r.startsWith('FAIL'))) process.exit(1);
});
"""


def test_frontend_race_and_full_storage(tmp_path):
    """سباق المحادثات بترتيب معكوس + تخزين كامل + فشل حفظ ظاهر — على الكود الحي."""
    harness = tmp_path / "race_harness.js"
    harness.write_text(HARNESS, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(harness), str(UI)],
        capture_output=True, text=True, timeout=60,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, f"فشل الاختبار السلوكي:\n{out}"
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    assert lines, "لا مخرجات من الاختبار السلوكي"
    bad = [l for l in lines if not l.startswith("PASS")]
    assert not bad, f"فحوصات فاشلة: {bad}"
    joined = "\n".join(lines)
    # تحقق صريح من نقاط المراجعة الثالثة
    assert "١٠٥ محادثات بلا اقتطاط" in joined
    assert "أقدم محادثة (g0" in joined
    assert "يمنع فساد هوية B" in joined
    assert "يستعيد رسائلها الأربع كاملة لا B" in joined
    assert "يستعيد رسائلها لا A" in joined
    assert "لا نجاح صامت كاذب" in joined
    assert "لم تُفرَّغ باعتبارها محفوظة" in joined


def test_storage_cap_display_index_separate():
    """فهرس العرض منفصل عن المخزن الكامل، وفشل الحفظ يوقف التبديل في كل
    مسارات التبديل (زر جديد، فتح ضيف، فتح مالك) — مطابق للمصدر."""
    src = UI.read_text(encoding="utf-8")
    assert "CONV_DISPLAY_CAP = 100" in src
    assert "localConvs.slice(0, showAllLocalConvs ? localConvs.length : CONV_DISPLAY_CAP)" in src
    assert "إظهار الكل" in src
    upsert = re.search(r"function upsertLocalConv.*?\n  }", src, re.DOTALL).group(0)
    assert ".slice(0, 2)" not in upsert
    assert "return saveLocalConvs();" in upsert
    # فشل الحفظ يوقف التفريغ في كل مسارات التبديل
    assert src.count("if (!(await keepCurrentConversationBeforeNew())) return;") >= 2  # المسارات الثلاثة تنتظر النتيجة
    assert "var myNav = ++navSeq;" in src  # كل مسارات التنقل محمية بمعرّف العملية
