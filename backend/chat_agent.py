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


class ChatPlanner:
    """مخطط محادثة فوق العقل الحي — الفهرس في تعليمات النظام (بادئة ثابتة يعيد Ollama
    استخدام ذاكرتها بين الطلبات)، والرسالة وسياقها ونتائج الخطوات في رسالة المستخدم."""

    kind = "brain-chat"
    accepts_feedback = True

    def __init__(self, history: Optional[List[Dict[str, str]]] = None,
                 deadline: Optional[float] = None, chat_fn=None):
        self.history = list(history or [])[-6:]
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

    def next_step(self, goal: str, tools: List[Dict[str, Any]],
                  history: List[Dict[str, Any]],
                  feedback: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        from agent_loop import PlannerError, _extract_json, step_schema, PLANNER_MAX_TOKENS
        catalog = [{"name": t["name"], "description": t.get("description", "")[:140],
                    "inputs": t.get("inputs", {})} for t in tools]
        system = _CHAT_SYSTEM + "الأدوات المتاحة الآن:\n" + json.dumps(
            catalog, ensure_ascii=False)
        payload: Dict[str, Any] = {}
        if self.history:
            payload["conversation"] = [{"role": h.get("role"), "content": _clip(h.get("content", ""), 400)}
                                       for h in self.history]
        payload["message"] = goal
        if history:
            payload["tool_results"] = [
                {"tool": h.get("tool"), "inputs": h.get("inputs"), "ok": h.get("ok"),
                 "result": _clip(h.get("result")), "error": h.get("error")}
                for h in history]
        if feedback:
            payload["rejected"] = feedback
        reply = self._call(system, json.dumps(payload, ensure_ascii=False, default=str),
                           json_mode=True,
                           max_tokens=max(PLANNER_MAX_TOKENS, ANSWER_MAX_TOKENS),
                           json_schema=step_schema([t["name"] for t in tools]))
        if reply is None:
            raise PlannerError(_brain_failure_reason())
        return _extract_json(reply)

    def final_answer(self, goal: str, steps: List[Dict[str, Any]]) -> Optional[str]:
        """نفدت الميزانية بعد نتائج حقيقية ⇒ العقل يجيب منها نصًا (لا قالب)."""
        system = (_CHAT_SYSTEM.split("أجب بكائن JSON")[0]
                  + "أجب الآن نصًا عاديًا (لا JSON) من نتائج الأدوات أدناه وحدها.")
        user = json.dumps({"message": goal, "tool_results": [
            {"tool": s.get("tool"), "ok": s.get("ok"), "result": _clip(s.get("result")),
             "error": s.get("error")} for s in steps]}, ensure_ascii=False, default=str)
        return self._call(system, user, max_tokens=ANSWER_MAX_TOKENS)


def _brain_failure_reason() -> str:
    try:
        import ollama_client
        out = getattr(ollama_client, "_LAST_OUTCOME", None)
        if out:
            return f"العقل اللغوي لم يرد: {_clip(out, 200)}"
    except Exception:  # TOLERATED: السبب العام يكفي
        pass
    return "العقل اللغوي لم يرد (غير متاح أو انتهت المهلة)"


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
    planner = ChatPlanner(history, deadline=deadline, chat_fn=chat_fn)
    names = allowed_tools(registry, owner)
    loop = AgentLoop(registry, planner, max_steps=MAX_STEPS, max_seconds=budget,
                     allowed_tools=names, caller="chat")
    res = loop.run(text)
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
