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

# R-787a: مقيس حيًا — العقل (qwen2.5:3b على performance-2x) يقيّم المطالبة بنحو 20
# رمزًا/ث ويولّد بنحو 7 رموز/ث؛ 4.5 ألف حرف سياق ⇒ ~150ث فانتهت المهلة. السقف الآن
# يبقي المطالبة كلها ضمن ~1400 رمز (forensics/R-787a_brain_speed.txt).
MAX_CONTEXT_CHARS = 2200
TOOL_REPLY_MAX_TOKENS = 380
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
    # R-787a: مشاهد حيًا — العقل ادّعى «تنفيذ الكود» (مؤجل) و«البحث» (بلا مزود)
    if not search_configured():
        lines.append("- تنبيه صدق: البحث العام (web.search) لا مزود بحث له في هذا النشر — غير متاح فعليًا؛ "
                     "المتاح من الويب هو قراءة رابط محدد فقط.")
    lines.append("- لا تدّعِ أبدًا قدرة مؤجلة أو معطلة أو غير مبنية (مثل تنفيذ الكود) كأنها متاحة.")
    return "\n".join(lines)


def search_configured() -> bool:
    """مزود بحث مضبوط فعلًا: tavily بمفتاح، أو searxng على عنوان غير الافتراضي المحلي."""
    import config
    provider = str(getattr(config, "SEARCH_PROVIDER", "") or "").lower()
    base = str(getattr(config, "SEARCH_BASE_URL", "") or "")
    if provider == "world":
        return True  # R-823: مزودات عامة بلا مفتاح (world_search) — الإتاحة الفعلية تُعلن لكل بحث
    if provider == "tavily":
        return bool(getattr(config, "SEARCH_API_KEY", None))
    if provider == "searxng":
        return bool(base) and "127.0.0.1" not in base and "localhost" not in base
    return False


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
        parts.append("- الملفات والمجلدات الجذرية: " + "، ".join(names[:30]))
    except Exception as e:  # TOLERATED
        parts.append(f"- الملفات الجذرية: تعذر الجلب ({str(e)[:80]})")
    try:
        commits = _fetch_json(base + "/commits?per_page=6") or []
        parts.append("- آخر الالتزامات:")
        for c in commits[:4]:
            msg = ((c.get("commit") or {}).get("message") or "").splitlines()[0][:80]
            date = str(((c.get("commit") or {}).get("author") or {}).get("date", ""))[:10]
            parts.append(f"  • {str(c.get('sha', ''))[:7]} {date} {msg}")
    except Exception as e:  # TOLERATED
        parts.append(f"- الالتزامات: تعذر الجلب ({str(e)[:80]})")
    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    for label, path, limit in (("README", "README.md", 700), ("وثيقة حالة المشروع", "docs/PROJECT_STATE.md", 450)):
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


# R-787b: مشاهد حيًا بعد R-787a — حتى مع المنع الصريح ادّعى النموذج (3B) «تنفيذ البحث».
# سؤال القدرات/الهوية المباشر يُجاب من الجرد الحي حرفيًا بلا نموذج: فوري وصادق دائمًا.
_DIRECT_CAP_RE = re.compile(
    r"(قدرات|قدراتك|ماذا تستطيع|ما الذي تستطيع|ماذا تقدر|وش تقدر|ايش تقدر|إيش تقدر|أدواتك|ادواتك|"
    r"من أنت|من انت|عرف بنفسك|عرّف بنفسك|capabilit|what can you)",
    re.IGNORECASE,
)


def wants_direct_capabilities(text: str) -> bool:
    t = (text or "").strip()
    return bool(t) and len(t) <= 120 and not extract_urls(t) and bool(_DIRECT_CAP_RE.search(t))


def capabilities_reply(caps: Dict[str, Any], tool_names: List[str]) -> str:
    """رد حتمي من الجرد الحي — لا نموذج، لا ادعاء."""
    import config
    searchable = search_configured()
    groups: Dict[str, List[str]] = {}
    for c in caps.get("capabilities", []):
        name = c.get("name", c.get("id", ""))
        level = c.get("level", "missing")
        if not searchable and c.get("id") == "web_tools" and level == "enabled":
            name += " (القراءة من رابط فقط — البحث العام بلا مزود)"
        if not searchable and c.get("id") == "research" and level == "enabled":
            level = "implemented_disabled"
            name += " (يحتاج مزود بحث غير موجود في هذا النشر)"
        groups.setdefault(level, []).append(name)
    model = getattr(config, "OLLAMA_MODEL", None) or "غير مضبوط"
    out = [
        "أنا واجهة مشروع sovereign_ai. هذا جردي الحي الآن، مقروء من النظام مباشرة لا من النموذج اللغوي:",
        "",
    ]
    for lv in ("enabled", "implemented_disabled", "blocked", "deferred", "missing"):
        if groups.get(lv):
            out.append(f"{LEVEL_AR[lv]}:")
            out.extend(f"  - {n}" for n in groups[lv])
    out += [
        "",
        "ما أفعله داخل هذه المحادثة فعليًا:",
        f"  - أجيب بمعرفة عامة عبر عقلي اللغوي «{model}» (نموذج صغير على معالج بلا GPU — الرد يستغرق 20 إلى 120 ثانية).",
        "  - أقرأ أي رابط تضعه في رسالتك، وأحلل مستودعات GitHub العامة (عبر الأداة web.fetch، وكل قراءة تُسجل بأثر موقّع).",
        "  - أعرض هذا الجرد عند سؤالك عن قدراتي.",
        "",
        "ما لا أستطيعه الآن:",
    ]
    if not searchable:
        out.append("  - البحث العام في الإنترنت (لا مزود بحث مضبوط).")
    out += [
        "  - تشغيل الأدوات الأخرى من المحادثة تلقائيًا (الوكيل والمهام والأسطول تعمل عبر واجهة API لا من هنا بعد).",
        "  - قراءة المستودعات الخاصة (لا رمز GitHub).",
        "  - أي قدرة مؤجلة أو معطلة في القائمة أعلاه.",
    ]
    if tool_names:
        out += ["", f"الأدوات المسجلة فعلًا ({len(tool_names)}): " + "، ".join(tool_names)]
    return "\n".join(out)


def gather(text: str, capabilities_fn: Optional[Callable[[], Dict[str, Any]]] = None) -> Dict[str, Any]:
    """يعيد {"context": نص للعقل أو "", "tools_used": [وصف عربي لكل أداة استُخدمت]}."""
    blocks: List[str] = []
    used: List[str] = []
    if capabilities_fn is not None and wants_direct_capabilities(text):
        try:
            from tool_registry import get_registry
            names = [t["name"] for t in get_registry().list_tools()]
            return {"context": "", "tools_used": ["جرد القدرات الحي"],
                    "direct_reply": capabilities_reply(capabilities_fn(), names)}
        except Exception:  # TOLERATED: يسقط إلى المسار العادي (سياق للعقل) — يُعلن هناك
            pass
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
