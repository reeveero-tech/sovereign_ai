"""R-824: عقل سحابي احتياطي (متوافق OpenAI) — نداء واحد مقيّد بالمصادر حين يتعذر العقل الأساسي.

بأمر المالك (2026-10-31): «يجب أن يكون أقوى مما هو عليه ألف مرة» + «هناك هلوسة».

الوضع الحي: العقل الأساسي (Ollama على شبكة المالك الخاصة) لا تصل إليه السحابة، فكانت
الردود استخلاصًا حتميًا بلا صياغة. هذه الوحدة طبقة صياغة فوق النتائج الحقيقية، لا بديل عنها:
- grounded(): يصوغ جوابًا متماسكًا بلغة السائل من نقاط البحث العالمي **المرقّمة فقط**
  مع سياق المحادثة؛ يُرفض الناتج (ويبقى الرد الحتمي) إن لم يستشهد بأرقام موجودة أو استشهد
  برقم غير موجود — هذا حارس الهلوسة.
- general(): مهام لا تحتاج حقائق خارجية (كتابة، صياغة، كود، أفكار) مع سياق المحادثة، ويُعلن
  في الرد أنه من النموذج الاحتياطي.

المزود الافتراضي: Pollinations (نقطة OpenAI متوافقة بلا مفتاح، حدها المجاني رد كل 45ث لكل IP).
أي مزود متوافق (Groq/OpenRouter/Gemini/مفتاح Pollinations) يُضبط بالمتغيرات بلا تغيير كود:
CLOUD_BRAIN_ENABLED, CLOUD_BRAIN_URL (نقطة chat/completions كاملة), CLOUD_BRAIN_MODEL,
CLOUD_BRAIN_API_KEY, CLOUD_BRAIN_MIN_INTERVAL_SECONDS, CLOUD_BRAIN_TIMEOUT_SECONDS,
CLOUD_BRAIN_MAX_WAIT_SECONDS.

مبادئ: لا يرفع أبدًا (فشل ⇒ None والمستدعي يبقي الحتمي)، لا محتوى ولا مفتاح في السجلات،
مزلاج حد المعدل يحترم «Retry after Ns» من المزود فلا طوفان طلبات مرفوضة.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sovereign.cloud_brain")

DEFAULT_URL = "https://text.pollinations.ai/openai"
_LOCK = threading.Lock()
_NEXT_ALLOWED = 0.0
_LAST = {"result": "none", "error": None, "model": None, "at": None}
_CITE = re.compile(r"\[(\d{1,2})\]")
_RETRY = re.compile(r"[Rr]etry after (\d+)\s*s")


def _env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or default).strip()


def enabled() -> bool:
    return _env("CLOUD_BRAIN_ENABLED", "false").lower() == "true"


def model() -> str:
    return _env("CLOUD_BRAIN_MODEL", "openai")


def status() -> Dict[str, Any]:
    wait = max(0.0, _NEXT_ALLOWED - time.time())
    host = re.sub(r"^https?://([^/]+).*$", r"\1", _env("CLOUD_BRAIN_URL", DEFAULT_URL))
    return {"enabled": enabled(), "provider_host": host, "model": model(),
            "has_key": bool(_env("CLOUD_BRAIN_API_KEY")), "next_available_in_seconds": round(wait, 1),
            "last": dict(_LAST)}


def _min_interval() -> float:
    default = "0" if _env("CLOUD_BRAIN_API_KEY") else "45"
    try:
        return max(0.0, float(_env("CLOUD_BRAIN_MIN_INTERVAL_SECONDS", default)))
    except ValueError:
        return 45.0


def plain(text: str) -> str:
    """R-824e: الواجهة تعرض نصًا خامًا (بلا innerHTML) ⇒ رموز Markdown تظهر حرفيًا («**عنوان**») —
    تحويل للنص المقروء: عريض/مائل/عناوين/اقتباس ⇒ نص، والنقاط ⇒ «•»، والاستشهادات [n] كما هي."""
    t = str(text or "").replace("\r\n", "\n")
    t = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), t)
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", t)
    t = re.sub(r"(?m)^\s{0,3}>\s?", "", t)
    t = re.sub(r"(?m)^(\s*)[-*+]\s+", lambda m: m.group(1) + "• ", t)
    t = re.sub(r"(?m)^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", "", t)
    t = re.sub(r"(?m)[ \t]+$", "", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def chat(system: str, user: str, history=None, max_tokens: int = 1400) -> Optional[str]:
    """نداء واحد — نص المساعد أو None (معطّل/محدود المعدل/فشل)."""
    global _NEXT_ALLOWED, _LAST
    if not enabled():
        return None
    try:
        max_wait = float(_env("CLOUD_BRAIN_MAX_WAIT_SECONDS", "20"))
    except ValueError:
        max_wait = 20.0
    with _LOCK:  # الطلبات تتسلسل — الحد لكل IP لا لكل خيط
        wait = _NEXT_ALLOWED - time.time()
        if wait > max_wait:
            _LAST = {"result": "rate_limited", "error": f"wait {int(wait)}s", "model": model(), "at": time.time()}
            return None
        if wait > 0:
            time.sleep(wait)
        msgs = [{"role": "system", "content": system}]
        for t in list(history or [])[-10:]:
            if isinstance(t, dict) and t.get("role") in ("user", "assistant") and str(t.get("content") or "").strip():
                msgs.append({"role": t["role"], "content": str(t["content"])[:3000]})
        msgs.append({"role": "user", "content": user})
        headers = {"Content-Type": "application/json"}
        if _env("CLOUD_BRAIN_API_KEY"):
            headers["Authorization"] = "Bearer " + _env("CLOUD_BRAIN_API_KEY")
        try:
            import httpx
            timeout = float(_env("CLOUD_BRAIN_TIMEOUT_SECONDS", "60"))
            with httpx.Client(timeout=httpx.Timeout(timeout, connect=8.0)) as c:
                r = c.post(_env("CLOUD_BRAIN_URL", DEFAULT_URL), headers=headers,
                           json={"model": model(), "messages": msgs, "max_tokens": int(max_tokens)})
            if r.status_code in (402, 429):
                m = _RETRY.search(r.text or "")
                _NEXT_ALLOWED = time.time() + (int(m.group(1)) + 1 if m else _min_interval())
                _LAST = {"result": "rate_limited", "error": f"HTTP {r.status_code}", "model": model(),
                         "at": time.time()}
                return None
            r.raise_for_status()
            data = r.json()
            content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
            _NEXT_ALLOWED = time.time() + _min_interval()
            if isinstance(content, str) and content.strip():
                _LAST = {"result": "ok", "error": None, "model": data.get("model") or model(), "at": time.time()}
                return plain(content)
            _LAST = {"result": "error", "error": "empty", "model": model(), "at": time.time()}
            return None
        except Exception as e:  # TOLERATED: طبقة صياغة اختيارية — الحتمي يبقى
            code = getattr(getattr(e, "response", None), "status_code", None)
            _LAST = {"result": "error", "error": type(e).__name__ + (f":{code}" if code else ""),
                     "model": model(), "at": time.time()}
            _NEXT_ALLOWED = time.time() + 10
            logger.warning("R-824: فشل العقل السحابي (%s)", _LAST["error"])
            return None


_LANG_NAME = {"ar": "العربية", "en": "English", "fr": "Français", "es": "Español", "de": "Deutsch"}


def grounded(question: str, world: Dict[str, Any], history=None) -> Optional[Dict[str, Any]]:
    """صياغة من النقاط المرقمة فقط — {"text", "model"} أو None إن فشل/خالف الحارس."""
    pts = world.get("points") or []
    srcs = {s["n"]: s for s in (world.get("sources") or [])}
    if not pts or not srcs:
        return None
    lang = world.get("user_lang") or "ar"
    lines = []
    for p in pts:
        src = srcs.get(p.get("source")) or {}
        orig = p.get("original")
        lines.append(f"[{p.get('source')}] ({src.get('title', '')[:90]}) {p.get('text')}"
                     + (f"\n    original: {orig[:400]}" if orig and orig != p.get("text") else ""))
    system = (
        "You are the Sovereign AI assistant. Answer ONLY from the numbered evidence below; every factual "
        "sentence must end with its citation like [1] or [2][3]. Never invent facts, numbers, studies or "
        "sources that are not in the evidence. If the evidence does not fully answer, say clearly what is "
        "missing. Use the conversation history only to understand what the user means. "
        f"Write in {_LANG_NAME.get(lang, lang)}, clear and well organized (short paragraphs or bullet "
        "points), no preamble, no source list (it will be appended).")
    user = f"Question: {question}\n\nEvidence:\n" + "\n".join(lines)
    out = chat(system, user, history=history)
    if not out:
        return None
    cited = {int(n) for n in _CITE.findall(out)}
    if not cited or not cited.issubset(set(srcs)):
        _LAST["result"] = "rejected_by_guard"
        logger.warning("R-824: رُفضت صياغة سحابية (استشهادات %s خارج المصادر %s)", sorted(cited), sorted(srcs))
        return None
    return {"text": out, "model": _LAST.get("model") or model()}


def general(question: str, history=None, lang: str = "ar") -> Optional[Dict[str, Any]]:
    """مهمة لا تحتاج حقائق خارجية (كتابة/كود/أفكار) — مع سياق المحادثة."""
    system = (
        "You are the Sovereign AI assistant. Help with the user's request directly and completely, using the "
        "conversation history for context. Do not state current facts, statistics or news as certain; if the "
        "request needs up-to-date facts, say they should be verified. "
        f"Reply in {_LANG_NAME.get(lang, lang)}.")
    out = chat(system, question, history=history)
    return {"text": out, "model": _LAST.get("model") or model()} if out else None
