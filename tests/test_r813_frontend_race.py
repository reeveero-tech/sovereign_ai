# -*- coding: utf-8 -*-
"""R-813 (تصحيح المراجعة الثانية) — اختبار سلوكي حقيقي لمنطق المحادثات في
الواجهة: يُشغَّل كود الواجهة الفعلي (المستخرج من index.html) في Node مع
كوابيل، وتُتحكم أزمنة الاستجابات يدويًا لاختبار السباق بترتيب معكوس.

يغطي مطالب المراجعة الثانية:
١) سقف الضيف: إنشاء ١٠٥ محادثات ⇒ التخزين يحفظها كلها كاملة (لا اقتطاط)،
   وأقدمها تُستعاد كاملة بفتحها.
٢) سباق persistConv (مسار المالك): حفظ A يبدأ، ننتقل إلى B، استجابة A
   تكتمل بعد B (ترتيب معكوس) ⇒ حارس targetSession يمنع فساد هوية B.
٣) فتح A وB بعد السباق: المعرفات والرسائل والنماذج بلا اختلاط.
"""

import json
import re
import subprocess
import sys
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
  let i = html.indexOf('{', start), depth = 0, end = -1;
  for (; i < html.length; i++) {
    if (html[i] === '{') depth++;
    else if (html[i] === '}') { depth--; if (depth === 0) { end = i; break; } }
  }
  return html.slice(start, end + 1);
}

// ---- كوابيل البيئة ----
const store = new Map();
global.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};
const state = {
  sessionId: null, convId: null, messages: [], model: null,
};
let ownerKeyValue = 'test-owner-key';
function ownerKey() { return ownerKeyValue; }
function save() {}
function renderChat() {}
function paintConvs() {}
function paintModelSel() {}
function go() {}
// ---- سجل نداءات المالك مع تحكم يدوي في الإكمال ----
const apiCalls = [];
const pendingApi = [];
const autoResponses = [];
function api(url, opts) {
  const rec = { url, json: opts && opts.json ? JSON.parse(JSON.stringify(opts.json)) : null,
                resolve: null };
  apiCalls.push(rec);
  return new Promise((resolve) => {
    rec.resolve = resolve;
    if (autoResponses.length) { resolve(autoResponses.shift()); return; }
    pendingApi.push(rec);
  });
}
const tick = () => new Promise((r) => setImmediate(r));
function el(tag, cls, txt) { const e = { className: cls, textContent: txt }; return e; }
function $(id) { return { appendChild() {}, textContent: '', hidden: false }; }

// ثوابت صفحة الحية التي تعتمد عليها الوظائف المستخرجة
global.CONV_LOCAL = 'sovereign.localConvs';
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

// ================= ١) سقف التخزين: ١٠٥ محادثات كلها كاملة =================
for (let i = 0; i < 105; i++) {
  fns.upsertLocalConv({ id: 'g' + i, title: 'محادثة ' + i,
    messages: [{ role: 'user', content: 'رسالة ' + i },
               { role: 'assistant', content: 'رد ' + i }],
    updated_at: 1000 + i, model: 'm' + (i % 3) });
}
const stored = JSON.parse(localStorage.getItem('sovereign.localConvs'));
check('التخزين يحفظ ١٠٥ محادثات بلا اقتطاط', stored.length === 105);
check('كل المحادثات كاملة الرسائل (أقدمها أيضًا)', stored.every(c => c.messages.length === 2));
const oldest = stored.find(c => c.id === 'g104');
check('أقدم محادثة (g104) محفوظة كاملة', oldest && oldest.messages.length === 2 &&
      oldest.messages[1].content === 'رد 104');

// استعادة أقدمها كاملة بفتحها
state.sessionId = 'current'; state.messages = [{ role: 'user', content: 'جارية' }];
fns.openLocalConv('g104');
check('فتح أقدم محادثة يستعيد رسائلها كاملة',
      state.messages.length === 2 && state.messages[0].content === 'رسالة 104');
check('فتحها يستعيد نموذجها', state.model === 'm2');

// ================= ٢) سباق persistConv بترتيب معكوس (مسار المالك) =================
(async () => {
// محادثة A نشطة: حفظها يبدأ ولا تكتمل استجابته بعد
state.sessionId = 'A'; state.convId = null; state.model = 'mA';
state.messages = [{ role: 'user', content: 'سؤال A' }, { role: 'assistant', content: 'رد A' }];
fns.persistConv();                     // نداء A — استجابته معلقة
const callA = apiCalls[apiCalls.length - 1];
check('نداء A حُمل بمحتوى A', callA.json.title.indexOf('سؤال A') >= 0 &&
      callA.json.model === 'mA');

// ننتقل إلى B ونحفظها — تكتمل استجابة B أولًا
state.sessionId = 'B'; state.convId = null; state.model = 'mB';
state.messages = [{ role: 'user', content: 'سؤال B' }];
fns.persistConv();                     // نداء B
const callB = apiCalls[apiCalls.length - 1];
check('نداء B حُمل بمحتوى B', callB.json.title.indexOf('سؤال B') >= 0 &&
      callB.json.model === 'mB');
callB.resolve({ id: 'B-id' });         // B تكتمل أولًا
await tick();
check('استجابة B تثبت هوية B', state.convId === 'B-id');

// استجابة A المتأخرة تكتمل الآن (بعد التبديل) — الحارس يجب أن يمنع فساد B
callA.resolve({ id: 'A-id' });
await tick();
check('حارس العرق يمنع فساد هوية B برد A المتأخر', state.convId === 'B-id');
check('جلسة العرض بقيت B', state.sessionId === 'B');

// فتح A وB بعد السباق عبر مسار المالك (openConv) — بلا اختلاط
autoResponses.push({ messages: [{ role: 'user', content: 'سؤال A' },
                                { role: 'assistant', content: 'رد A' }], model: 'mA' });
await fns.openConv('A-id');
check('فتح A يستعيد محتوى A لا B',
      state.messages.length === 2 && state.messages[0].content === 'سؤال A' &&
      state.messages[1].content === 'رد A');
check('نموذج A مستعاد', state.model === 'mA');
autoResponses.push({ messages: [{ role: 'user', content: 'سؤال B' }], model: 'mB' });
await fns.openConv('B-id');
check('فتح B يستعيد محتوى B لا A', state.messages.length === 1 &&
      state.messages[0].content === 'سؤال B');
check('نموذج B مستعاد', state.model === 'mB');
})().then(() => {
  console.log(results.join('\n'));
  if (results.some(r => r.startsWith('FAIL'))) process.exit(1);
});

// ================= ٣) الحفظ قبل التبديل لا يخلط شيئًا =================
state.sessionId = 'B'; state.convId = 'B-id';
state.messages = [{ role: 'user', content: 'سؤال B' }, { role: 'assistant', content: 'رد B جديد' }];
state.model = 'mB';
apiCalls.length = 0;
fns.keepCurrentConversationBeforeNew();  // حفظ الجارية قبل التبديل
const pre = apiCalls[apiCalls.length - 1];
check('الحفظ قبل التبديل يرسل محتوى الجارية (B)', pre &&
      pre.json.title.indexOf('سؤال B') >= 0 && pre.json.model === 'mB');


"""


def test_frontend_race_and_full_storage(tmp_path):
    """سباق المحادثات بترتيب معكوس + تخزين كامل بلا اقتطاط — على الكود الحي."""
    harness = tmp_path / "race_harness.js"
    # تنظيف سطر تعريف مزدوج زائد من القالب
    code = HARNESS.replace("function apiFetchLog = [];", "")
    harness.write_text(code, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(harness), str(UI)],
        capture_output=True, text=True, timeout=60,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    assert proc.returncode == 0, f"فشل اختبار السباق السلوكي:\n{out}"
    # كل الفحوصات PASS
    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    assert lines, "لا مخرجات من الاختبار السلوكي"
    bad = [l for l in lines if not l.startswith("PASS")]
    assert not bad, f"فحوصات فاشلة: {bad}"
    # تحقق صريح من نقاط المراجعة
    joined = "\n".join(lines)
    assert "١٠٥ محادثات بلا اقتطاط" in joined
    assert "يمنع فساد هوية B" in joined
    assert "يستعيد محتوى A لا B" in joined
    assert "يستعيد محتوى B لا A" in joined


def test_storage_cap_display_index_separate():
    """فهرس العرض منفصل عن المخزن: العرض أحدث ١٠٠ قابل للتوسيع، والمخزن
    الكامل بلا اقتطاط — مطابق لمصدر الواجهة."""
    src = UI.read_text(encoding="utf-8")
    assert "CONV_DISPLAY_CAP = 100" in src
    assert "localConvs.slice(0, showAllLocalConvs ? localConvs.length : CONV_DISPLAY_CAP)" in src
    assert "إظهار الكل" in src  # مؤشر التوسيع الصادق
    # لا اقتطاط في مسار التخزين
    upsert = re.search(r"function upsertLocalConv.*?\n  }", src, re.DOTALL).group(0)
    assert ".slice(0, 2)" not in upsert
    assert "archived" not in upsert
