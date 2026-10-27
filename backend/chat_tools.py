"""R-787: جسر المحادثة ↔ أدوات المشروع.

المشكلة (المالك 2026-10-27، بدليل محادثته): «أخبرني عن قدراتك» ⇒ النموذج سرد
قدرات عامة لا علاقة لها بالمشروع؛ «حلل هذا المستودع» ⇒ «لا أملك الوصول إلى
الإنترنت». السبب الحقيقي: مسار `/chat` كان يرسل النص إلى النموذج مباشرة —
لا جرد القدرات ولا أي أداة من الأدوات الـ27 المسجلة يمر بالمحادثة.

هذا الجسر حتمي (لا يعتمد على قدرة نموذج 3B على التخطيط): قبل استدعاء العقل
يفحص الرسالة، ويستدعي الأدوات المسجلة نفسها عبر `ToolRegistry.invoke` — فكل
استدعاء يترك أثر `tool_invoked` موقّعًا في السجل (لا أثر = لا تنفيذ) — ثم يمرر
نتائجها للعقل سياقًا صريحًا. الفشل يُمرر نصًا صادقًا (لا محتوى مختلق).

المسارات:
- سؤال عن القدرات/الهوية/المشروع ⇒ جرد القدرات الحي (`/capabilities`) + أسماء الأدوات.
- رابط مستودع GitHub عام ⇒ `web.fetch` على واجهة GitHub العامة (البيانات، اللغات،
  الملفات الجذرية، آخر الالتزامات، README، ووثيقة الحالة إن وُجدت).
- أي رابط http(s) آخر ⇒ `web.fetch` للصفحة.
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional

MAX_CONTEXT_CHARS = 5000
MAX_URLS = 2

_URL_RE = re.compile(r"https?://[^\s<>\"'()\[\]{}]+", re.IGNORECASE)
_GH_RE = re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.IGNORECASE)
_CAP_RE = re.compile(
    r"(قدرات|قدراتك|تستطيع|تقدر|أدوات|ادوات|أدواتك|ادواتك|من أنت|من انت|عرف بنفسك|عرّف بنفسك|"
    r"ما هو المشروع|ما المشروع|مشروعك|هذا المشروع|ماذا تفعل|وش تقدر|ايش تقدر|إيش تقدر|"
    r"capabilit|what can you)",
    re.IGNORECASE,
)

LEVEL_AR = {
    "enabled": "مفعّلة",
    "implemented_disabled": "مبنية لكنها معطلة",
    "blocked": "محجوبة",
    "deferred": "مؤجلة بقرار المالك",
    "missing": "غير مبنية",
}


def extract_urls(text: str) -> List[str]:
    urls = []
    for m in _URL_RE.findall(text or ""):
        u = m.rstrip(".,،؛;:!?؟")
        if u not in urls:
            urls.append(u)
    return urls[:MAX_URLS]


def wants_capabilities(text: str) -> bool:
    return bool(_CAP_RE.search(text or ""))


def _invoke(name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    from tool_registry import get_registry
    return get_registry().invoke(name, caller="chat", inputs=inputs)


def _fetch(url: str) -> Dict[str, Any]:
    """web.fetch عبر السجل — يعيد result أو يرفع RuntimeError بنص الخطأ الصادق."""
    out = _invoke("web.fetch", {"url": url})
    if not out.get("ok"):
        raise RuntimeError(out.get("error") or "فشل الجلب")
    return out["result"] or {}


def _fetch_json(url: str) -> Any:
    return json.loads(_fetch(url).get("text") or "null")


def capabilities_context(caps: Dict[str, Any], tool_names: List[str]) -> str:
    groups: Dict[str, List[str]] = {}
    for c in caps.get("capabilities", []):
        groups.setdefault(c.get("level", "missing"), []).append(c.get("name", c.get("id", "")))
    lines = ["جرد القدرات الحي لمشروع sovereign_ai (من الحالة الفعلية الآن، لا ادعاء):"]
    for lv in ("enabled", "implemented_disabled", "blocked", "deferred", "missing"):
        if groups.get(lv):
            lines.append(f"- {LEVEL_AR[lv]}: " + "، ".join(groups[lv]))
    if tool_names:
        lines.append(f"- الأدوات المسجلة فعلًا ({len(tool_names)}): " + "، ".join(tool_names))
    lines.append(
        "- داخل هذه المحادثة يستخدم النظام تلقائيًا: جرد القدرات عند السؤال عنها، "
        "وقراءة أي رابط أو مستودع GitHub عام يضعه المالك في رسالته (عبر الأداة web.fetch بأثر موقّع)."
    )
    return "\n".join(lines)


def github_context(owner: str, repo: str) -> str:
    base = f"https://api.github.com/repos/{owner}/{repo}"
    parts: List[str] = [f"بيانات مستودع GitHub {owner}/{repo} (جُلبت الآن من واجهة GitHub العامة):"]
    meta = _fetch_json(base)
    if not isinstance(meta, dict) or not meta.get("full_name"):
        raise RuntimeError("المستودع غير موجود أو خاص أو تجاوز حد GitHub")
    branch = meta.get("default_branch") or "main"
    parts.append(
        f"- الوصف: {meta.get('description') or 'لا وصف'} | اللغة الرئيسية: {meta.get('language')} | "
        f"النجوم: {meta.get('stargazers_count')} | الحجم: {meta.get('size')}KB | "
        f"أُنشئ: {str(meta.get('created_at'))[:10]} | آخر دفع: {str(meta.get('pushed_at'))[:10]}"
    )
    try:
        langs = _fetch_json(base + "/languages") or {}
        total = sum(langs.values()) or 1
        parts.append("- اللغات: " + "، ".join(f"{k} {round(v * 100 / total)}%" for k, v in list(langs.items())[:6]))
    except Exception as e:  # TOLERATED: جزء اختياري — يُعلن ولا يُختلق
        parts.append(f"- اللغات: تعذر الجلب ({str(e)[:80]})")
    names: List[str] = []
    try:
        items = _fetch_json(base + "/contents") or []
        names = [(i.get("name", "") + ("/" if i.get("type") == "dir" else "")) for i in items if isinstance(i, dict)]
        parts.append("- الملفات والمجلدات الجذرية: " + "، ".join(names[:40]))
    except Exception as e:  # TOLERATED
        parts.append(f"- الملفات الجذرية: تعذر الجلب ({str(e)[:80]})")
    try:
        commits = _fetch_json(base + "/commits?per_page=6") or []
        parts.append("- آخر الالتزامات:")
        for c in commits[:6]:
            msg = ((c.get("commit") or {}).get("message") or "").splitlines()[0][:110]
            date = str(((c.get("commit") or {}).get("author") or {}).get("date", ""))[:10]
            parts.append(f"  • {str(c.get('sha', ''))[:7]} {date} {msg}")
    except Exception as e:  # TOLERATED
        parts.append(f"- الالتزامات: تعذر الجلب ({str(e)[:80]})")
    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    for label, path, limit in (("README", "README.md", 1600), ("وثيقة حالة المشروع", "docs/PROJECT_STATE.md", 1400)):
        if path == "docs/PROJECT_STATE.md" and "docs/" not in names:
            continue
        try:
            txt = (_fetch(f"{raw}/{path}").get("text") or "").strip()
            if txt:
                parts.append(f"- مقتطف {label}: {txt[:limit]}")
        except Exception:  # TOLERATED: ملف غير موجود — لا يُذكر
            pass
    return "\n".join(parts)


def page_context(url: str) -> str:
    r = _fetch(url)
    return f"محتوى الصفحة {r.get('url', url)} (العنوان: {r.get('title') or '—'}), جُلب الآن:\n{(r.get('text') or '')[:2500]}"


def gather(text: str, capabilities_fn: Optional[Callable[[], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """يعيد {"context": نص للعقل أو "", "tools_used": [وصف عربي لكل أداة استُخدمت]}."""
    blocks: List[str] = []
    used: List[str] = []
    if capabilities_fn is not None and wants_capabilities(text):
        try:
            from tool_registry import get_registry
            names = [t["name"] for t in get_registry().list_tools()]
            blocks.append(capabilities_context(capabilities_fn(), names))
            used.append("جرد القدرات الحي")
        except Exception as e:  # TOLERATED: يُعلن للعقل بصدق
            blocks.append(f"تعذر قراءة جرد القدرات: {str(e)[:120]}")
    for url in extract_urls(text):
        gh = _GH_RE.match(url)
        try:
            if gh:
                owner, repo = gh.group(1), re.sub(r"\.git$", "", gh.group(2))
                blocks.append(github_context(owner, repo))
                used.append(f"قراءة GitHub: {owner}/{repo}")
            else:
                blocks.append(page_context(url))
                used.append(f"قراءة صفحة: {url[:60]}")
        except Exception as e:
            blocks.append(f"محاولة قراءة {url} فشلت فعليًا: {str(e)[:160]} — أخبر المالك بالفشل كما هو ولا تختلق محتوى.")
            used.append(f"فشل قراءة: {url[:60]}")
    ctx = "\n\n".join(blocks)
    if len(ctx) > MAX_CONTEXT_CHARS:
        ctx = ctx[:MAX_CONTEXT_CHARS] + " …(اقتُطع)"
    return {"context": ctx, "tools_used": used}
