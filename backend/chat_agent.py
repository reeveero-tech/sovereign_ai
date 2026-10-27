"""R-789 — المحادثة تفهم وتنفذ فعليًا عبر حلقة الوكيل (لا أجوبة مزروعة).

أمر المالك (2026-10-27): «يمنع منعًا باتًا أن تزرع أجوبة في الكود — يجب أن يستجيب النظام
فعليًا، يعرف ما يوجه له ويترجمه ثم يعيد الإجابة بناءً على الحقيقة».

التدفق لكل رسالة:
  1. العقل (BrainPlanner بمخطط JSON مقيّد بأسماء الأدوات المسجلة فعلًا) يقرأ الرسالة وسياق
     المحادثة ويقرر: يجيب مباشرة (finish) أو يستدعي أداة حقيقية (call).
  2. الأداة تُنفذ عبر ToolRegistry.invoke(caller="chat") — أثر موقّع لكل نداء.
  3. النتيجة الحقيقية تعود للعقل؛ يكرر أو ينهي بجواب مبني عليها.
  4. نفدت الميزانية بعد نتائج حقيقية ⇒ نداء أخير للعقل ليجيب منها (نص النموذج، لا قالب).
  5. فشل العقل ⇒ إعلان صادق بالسبب الفعلي — لا نص بديل مكتوب مسبقًا يدّعي أنه جواب.

الصلاحيات: بلا مفتاح المالك ⇒ أدوات القراءة فقط (بياناتها خلف نقاط عامة أصلًا). بمفتاح المالك
الصحيح ⇒ كل الأدوات المسجلة عدا agent.run (FORBIDDEN_TOOLS — لا وكيل داخل وكيل).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

# أدوات القراءة — كل منها يعيد ما تعرضه نقطة عامة قائمة أو يقرأ الويب العام بحارس SSRF
CHAT_READ_TOOLS = frozenset({
    "system.capabilities", "health.snapshot", "memory.stats", "disk.status",
    "vault.status", "brain.status", "connectors.status", "skills.status",
    "defects.scan", "sovereignty.score", "web.fetch", "github.repo",
})
# R-790: قراءة الخبرة والمعرفة المكتسبة — بيانات وقائع النظام نفسه، بلا أسرار
CHAT_READ_TOOLS = CHAT_READ_TOOLS | frozenset({"experience.stats", "experience.recall",
                                               "knowledge.recall",
                                               # R-791: قراءة الأهداف وحالة الاستقلال
                                               "goals.list", "autonomy.status"})
# web.search يُضاف فقط إن وُجد مزود فعلي — لا أداة تعرض على العقل وهي لا تعمل
SEARCH_TOOL = "web.search"

RESULT_CHARS = int(os.getenv("CHAT_AGENT_RESULT_CHARS", "1800") or 1800)
MAX_STEPS = int(os.getenv("CHAT_AGENT_MAX_STEPS", "4") or 4)
MAX_SECONDS = float(os.getenv("CHAT_AGENT_MAX_SECONDS", "150") or 150)
ANSWER_MAX_TOKENS = int(os.getenv("CHAT_AGENT_ANSWER_TOKENS", "420") or 420)

_CHAT_SYSTEM = (
    "أنت عقل نظام sovereign_ai — نظام سيادي ذاتي الاستضافة لمالكه، له سجل موقّع وذاكرة دائمة "
    "وأدوات مسجلة حقيقية. اقرأ رسالة المالك وافهم ما يريده فعلًا، ثم قرر:\n"
    "- إن كان الجواب يحتاج بيانات حقيقية من النظام أو من الويب ⇒ استدعِ الأداة المناسبة.\n"
    "- إن كان سؤالًا عامًا أو محادثة أو طلب كتابة ⇒ أنهِ مباشرة بجوابك.\n"
    "- بعد نتائج الأدوات ⇒ أنهِ بجواب مبني على النتائج حرفيًا؛ لا تختلق رقمًا أو قدرة.\n"
    "أجب بكائن JSON واحد فقط:\n"
    '{"action":"call","tool":"<اسم من القائمة>","inputs":{...}}\n'
    '{"action":"finish","answer":"<الجواب للمالك>"}\n'
    "الجواب بالعربية الفصحى (أو بلغة المالك إن كتب بغيرها)، واضح وموجز، بلا حروف صينية. "
    "لا تقل إنك لا تستطيع الوصول إلى الإنترنت: أداة web.fetch تقرأ أي رابط، وgithub.repo "
    "تقرأ مستودعات GitHub العامة. إن فشلت أداة فقل ذلك بصدق.\n"
)


def _clip(obj: Any, n: int = RESULT_CHARS) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + f"… [مقتطع — {len(s)} حرفًا]"


def _compact(obj: Any, n: int = RESULT_CHARS) -> str:
    """R-789c: تحويل عام (لا يعرف أي أداة) من JSON إلى أسطر «مفتاح: قيمة» بلا قيم فارغة —
    قياس حي: نتيجة الجرد (~5000 حرف JSON) أخذت 136ث تقييمًا للمدخل وقرأها العقل خطأً."""
    if isinstance(obj, str):
        return _clip(obj, n)
    out: List[str] = []

    def scalar(v):
        return isinstance(v, (str, int, float, bool))

    def walk(v, path):
        if v is None or v == "" or v == [] or v == {}:
            return
        if scalar(v):
            out.append(f"{path}: {v}")
        elif isinstance(v, dict):
            flat = {k: x for k, x in v.items() if scalar(x) and x != ""}
            nested = {k: x for k, x in v.items() if not scalar(x)}
            if path and flat and len(flat) == len([k for k, x in v.items() if x not in (None, "")]):
                out.append(f"{path}: " + "، ".join(f"{k}={x}" for k, x in flat.items()))
                return
            for k, x in flat.items():
                out.append(f"{path + '.' if path else ''}{k}: {x}")
            for k, x in nested.items():
                walk(x, f"{path + '.' if path else ''}{k}")
        elif isinstance(v, (list, tuple)):
            if all(scalar(x) for x in v):
                out.append(f"{path}: " + "، ".join(str(x) for x in v))
            else:
                for i, x in enumerate(v):
                    walk(x, f"{path}[{i}]")
        else:
            out.append(f"{path}: {v}")

    try:
        walk(obj, "")
    except Exception:  # TOLERATED: يعود إلى JSON المقتطع
        return _clip(obj, n)
    return _clip("\n".join(out), n)


def search_available() -> bool:
    try:
        import chat_tools
        return bool(chat_tools.search_configured())
    except Exception:  # TOLERATED: بلا مزود مؤكد لا تُعرض الأداة
        return False


def allowed_tools(registry, owner: bool) -> List[str]:
    from agent_loop import FORBIDDEN_TOOLS
    names = [t["name"] for t in registry.list_tools()]
    if owner:
        allowed = [n for n in names if n not in FORBIDDEN_TOOLS]
        if not search_available():
            allowed = [n for n in allowed if n != SEARCH_TOOL]
        return allowed
    read = set(CHAT_READ_TOOLS)
    if search_available():
        read.add(SEARCH_TOOL)
    return [n for n in names if n in read]


_ROUTER_SYSTEM = (
    "أنت موجّه نظام sovereign_ai. مهمتك الوحيدة: اختيار الأداة التي تجلب الحقيقة اللازمة "
    "للإجابة عن رسالة المالك. أي سؤال عن النظام نفسه (ذاكرته، أحداثه، صحته، قدراته، قرصه، "
    "أرقامه، مفاتيحه، موصلاته) يحتاج أداة دائمًا. أي رابط أو مستودع في الرسالة يحتاج أداة القراءة. "
    "اختر none فقط إن كانت الرسالة لا تحتاج بيانات من النظام أو الويب (تحية، كتابة، معرفة عامة)، "
    "أو إن كانت النتائج المجموعة تكفي للإجابة.\nالأدوات:\n"
)

_ANSWER_SYSTEM = (
    "أنت عقل نظام sovereign_ai — نظام ذكاء سيادي ذاتي الاستضافة لمالكه: سجل أحداث موقّع "
    "(Ed25519)، ذاكرة دائمة، وأدوات مسجلة حقيقية؛ وأنت النموذج اللغوي الذي يفهم ويجيب. "
    "أجب المالك بالعربية الفصحى (أو بلغته إن كتب بغيرها) — لا كلمات إنجليزية داخل الجملة "
    "العربية ولا حروف صينية — بإيجاز ودقة. إن وُجدت نتائج أدوات فابنِ الجواب عليها حرفيًا "
    "واذكر الأرقام كما هي؛ لا تختلق رقمًا أو قدرة. إن فشلت أداة فقل ذلك بصدق. "
    "إن لم تكن متأكدًا من معلومة عامة فقل ذلك. "
    "معاني مستويات القدرات في النتائج: enabled = مفعّلة تعمل الآن، implemented_disabled = "
    "مبنية لكنها معطلة، missing = غير مبنية، blocked = محجوبة، deferred = مؤجلة بقرار المالك."
)


class ChatPlanner:
    """R-789b: مرحلتان بقرار العقل في كلتيهما (قياس حي: 8/8 توجيهًا صحيحًا مقابل 1/4
    حين طُلب القرار والجواب معًا من qwen2.5:3b — forensics/R-789b_live_routing.txt):
      1. توجيه: JSON مقيّد {tool: <أداة مسموحة أو none>, inputs} — لا جواب في هذه المرحلة.
      2. جواب: نص حر من العقل مبني على الرسالة والسياق ونتائج الأدوات الحقيقية.
    يعمل داخل AgentLoop (صلاحيات + أثر موقّع + ميزانية) كأي مخطط."""

    kind = "brain-chat"
    accepts_feedback = True

    def __init__(self, history: Optional[List[Dict[str, str]]] = None,
                 deadline: Optional[float] = None, chat_fn=None, lessons: str = ""):
        self.history = list(history or [])[-6:]
        # R-790: وقائع تجارب سابقة مشابهة (experience.lessons_text) — العقل يتعلم مما وقع
        self.lessons = lessons or ""
        self.deadline = deadline
        self._chat = chat_fn

    def _call(self, system: str, user: str, **kw) -> Optional[str]:
        chat = self._chat
        if chat is None:
            import ollama_client
            chat = ollama_client.chat
        timeout = None
        if self.deadline is not None:
            timeout = max(5.0, self.deadline - time.monotonic())
        return chat(system, user, timeout=timeout, **kw)

    def _results(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{"tool": h.get("tool"), "inputs": h.get("inputs"), "ok": h.get("ok"),
                 "result": _compact(h.get("result")), "error": h.get("error")}
                for h in (history or [])]

    def _conversation(self) -> List[Dict[str, Any]]:
        return [{"role": h.get("role"), "content": _clip(h.get("content", ""), 400)}
                for h in self.history]

    def route(self, goal: str, tools: List[Dict[str, Any]],
              history: List[Dict[str, Any]], feedback=None) -> Dict[str, Any]:
        from agent_loop import PlannerError, _extract_json
        lines = []
        for t in tools:
            inp = ", ".join(f"{k}" for k in (t.get("inputs") or {})) or "بلا مدخلات"
            lines.append(f"- {t['name']} (المدخلات: {inp}): {t.get('description', '')[:140]}")
        system = _ROUTER_SYSTEM + "\n".join(lines) + '\nأجب JSON فقط: {"tool":"<اسم أو none>","inputs":{}}'
        if self.lessons:
            system += ("\nتجارب سابقة مشابهة (وقائع مسجلة — كرر ما نجح وتجنب ما فشل):\n"
                       + self.lessons)
        payload: Dict[str, Any] = {}
        if self.history:
            payload["conversation"] = self._conversation()
        payload["message"] = goal
        if history:
            payload["gathered_results"] = self._results(history)
        if feedback:
            payload["rejected"] = feedback
        schema = {"type": "object",
                  "properties": {"tool": {"type": "string",
                                          "enum": [t["name"] for t in tools] + ["none"]},
                                 "inputs": {"type": "object"}},
                  "required": ["tool", "inputs"]}
        reply = self._call(system, json.dumps(payload, ensure_ascii=False, default=str),
                           json_mode=True, max_tokens=120, json_schema=schema)
        if reply is None:
            raise PlannerError(_brain_failure_reason())
        return _extract_json(reply)

    def answer(self, goal: str, history: List[Dict[str, Any]]) -> Optional[str]:
        payload: Dict[str, Any] = {}
        if self.history:
            payload["conversation"] = self._conversation()
        payload["message"] = goal
        if history:
            payload["tool_results"] = self._results(history)
        user = json.dumps(payload, ensure_ascii=False, default=str) if (self.history or history) else goal
        return self._call(_ANSWER_SYSTEM, user, max_tokens=ANSWER_MAX_TOKENS)

    def next_step(self, goal: str, tools: List[Dict[str, Any]],
                  history: List[Dict[str, Any]],
                  feedback: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        from agent_loop import PlannerError
        decision = self.route(goal, tools, history, feedback)
        tool = str(decision.get("tool") or "none")
        inputs = decision.get("inputs") if isinstance(decision.get("inputs"), dict) else {}
        already = any(h.get("tool") == tool and (h.get("inputs") or {}) == inputs for h in history or [])
        if tool != "none" and not already:
            return {"action": "call", "tool": tool, "inputs": inputs}
        text = self.answer(goal, history)
        if not text or not text.strip():
            raise PlannerError(_brain_failure_reason())
        return {"action": "finish", "answer": text.strip()}

    def final_answer(self, goal: str, steps: List[Dict[str, Any]]) -> Optional[str]:
        """نفدت الخطوات بعد نتائج حقيقية ⇒ العقل يجيب منها نصًا (لا قالب)."""
        return self.answer(goal, steps)


def _brain_failure_reason() -> str:
    try:
        import ollama_client
        out = getattr(ollama_client, "_LAST_OUTCOME", None)
        if out:
            return f"العقل اللغوي لم يرد: {_clip(out, 200)}"
    except Exception:  # TOLERATED: السبب العام يكفي
        pass
    return "العقل اللغوي لم يرد (غير متاح أو انتهت المهلة)"


def _learn(text: str, res: Dict[str, Any]) -> None:
    """R-790: كل محادثة تُسجل خبرةً كما وقعت (الأدوات، الحالة، الخطأ) — لا تفسير مختلق."""
    try:
        import experience
        experience.record_run("chat", text, res)
    except Exception:  # TOLERATED: الخبرة إضافة؛ لا تكسر الرد
        pass


def brain_enabled() -> bool:
    try:
        import config
        return bool(config.OLLAMA_ENABLED and config.OLLAMA_MODEL)
    except Exception:  # TOLERATED: بلا إعدادات ⇒ معطل
        return False


def respond(text: str, history: Optional[List[Dict[str, str]]] = None, *,
            owner: bool = False, registry=None, chat_fn=None,
            max_seconds: Optional[float] = None) -> Dict[str, Any]:
    """يعيد {reply, status, tools_used, steps, run_id} — reply نص العقل أو سبب صادق."""
    from agent_loop import AgentLoop
    if registry is None:
        from tool_registry import get_registry
        registry = get_registry()
    if chat_fn is None and not brain_enabled():
        return {"reply": "العقل اللغوي غير مفعّل على هذا الخادم (OLLAMA_ENABLED/OLLAMA_MODEL) — "
                         "لا أستطيع فهم الرسالة والإجابة عنها دونه.",
                "status": "brain_disabled", "tools_used": [], "steps": []}
    budget = float(max_seconds if max_seconds is not None else MAX_SECONDS)
    deadline = time.monotonic() + budget
    lessons = ""
    try:
        import experience
        lessons = experience.lessons_text(text, k=3)
    except Exception:  # TOLERATED: بلا خبرة يعمل الموجّه كما كان
        lessons = ""
    planner = ChatPlanner(history, deadline=deadline, chat_fn=chat_fn, lessons=lessons)
    names = allowed_tools(registry, owner)
    loop = AgentLoop(registry, planner, max_steps=MAX_STEPS, max_seconds=budget,
                     allowed_tools=names, caller="chat")
    res = loop.run(text)
    _learn(text, res)
    steps = res.get("steps") or []
    used = [s.get("tool") for s in steps if s.get("tool")]
    out = {"status": res.get("status"), "tools_used": used, "run_id": res.get("run_id"),
           "steps": [{"tool": s.get("tool"), "ok": s.get("ok"),
                      "error": s.get("error")} for s in steps]}
    answer = (res.get("answer") or "").strip() if res.get("status") == "completed" else ""
    if answer:
        out["reply"] = answer
        return out
    if steps and time.monotonic() < deadline - 5:
        try:
            final = planner.final_answer(text, steps)
        except Exception:  # TOLERATED: يُعلن أدناه بصدق
            final = None
        if final and final.strip():
            out["reply"], out["status"] = final.strip(), "answered_from_results"
            return out
    reason = res.get("error") or res.get("status") or "سبب غير معروف"
    ran = ("، ونُفذت الأدوات: " + "، ".join(used)) if used else ""
    out["reply"] = f"لم أُكمل الجواب بصدق: {_clip(reason, 300)}{ran}."
    return out
