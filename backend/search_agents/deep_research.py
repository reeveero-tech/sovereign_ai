"""R-829: البحث العميق — خوارزميات وكلاء البحث مفتوحة المصدر المسحوبة في third_party/ منقولة إلى
محرك حتمي يعمل بلا نموذج لغوي (العقل السحابي محدود بطلب كل ٤٥ ث فلا يُعتمد عليه هنا).

خط الإنتاج وأصل كل خطوة (الملف المسحوب الذي نُقلت منه الفكرة):
١) التخطيط
   - تفكيك الأسئلة متعددة الكيانات إلى عقد فرعية — MindSearch (InternLM__MindSearch/mindsearch/agent/graph.py:
     WebSearchGraph يضيف عقدة لكل سؤال فرعي ثم يجمعها).
   - زوايا الموضوع من فهرس مقال ويكيبيديا — STORM (stanford-oval__storm/.../persona_generator.py:
     get_wiki_page_title_and_toc يستخرج عناوين الأقسام ويستبعد See also/References/…).
   - أسئلة فرعية متوازية بعدد breadth — gpt-researcher (assafelovic__gpt-researcher: plan_research ⇒ sub_queries).
٢) التنفيذ: حلقة العرض/العمق — dzhng deep-research (dzhng__deep-research/src/deep-research.ts:
   كل مستوى يبحث breadth سؤالًا متوازيًا ثم يتعمق بـ ceil(breadth/2) سؤال متابعة حتى depth=0).
   كل سؤال فرعي يُجاب بمحرك world_search الكامل (كل اللغات والمزودات والتقييم والترجمة).
٣) التنقيح: مُقيِّم الإجابة — node-DeepResearch (jina-ai__node-DeepResearch/src/tools/evaluator.ts:
   أنواع التقييم definitive/freshness/plurality/completeness) + التأمل وسد الفجوات —
   open_deep_research (langchain-ai__open_deep_research: think/reflection ⇒ أسئلة متابعة)،
   وكشف تعارض الأرقام بين المصادر.
٤) النشر: تقرير بأقسام مستشهدة ومصادر موحّدة الترقيم — gpt-researcher/STORM (article generation).
"""

import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

_STORM_EXCLUDED = {"contents", "see also", "notes", "references", "external links", "further reading",
                   "bibliography", "sources", "gallery", "footnotes", "citations", "works cited",
                   "notes and references", "explanatory notes", "general and cited references"}
_DIRECT_KINDS = {"currency", "metal", "crypto", "weather", "time"}
_AGENTS = ["InternLM/MindSearch", "stanford-oval/storm", "assafelovic/gpt-researcher", "dzhng/deep-research",
           "jina-ai/node-DeepResearch", "langchain-ai/open_deep_research", "mat-1/metasearch2",
           "deedy5/ddgs", "adbar/trafilatura", "dorianbrown/rank_bm25", "xhluca/bm25s",
           "Sygil-Dev/whoosh-reloaded"]


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# ---------- ١) التخطيط ----------

def decompose(en_q: str) -> List[str]:
    """MindSearch: سؤال عن كيانات متعددة (مقارنة/«و») ⇒ عقدة فرعية لكل كيان بالجانب نفسه."""
    q = re.sub(r"\s+", " ", str(en_q or "")).strip().rstrip("?").strip()
    if not q:
        return []
    m = re.search(r"(?:difference|differences|compare|comparison|versus)\s+(?:between|of)?\s*(.+)", q, re.I)
    body = m.group(1) if m else q
    parts = re.split(r"\s+(?:vs\.?|versus|and|or)\s+|\s*,\s*", body, flags=re.I)
    parts = [re.sub(r"^(?:the|a|an)\s+", "", p.strip(), flags=re.I) for p in parts if p.strip()]
    if len(parts) < 2 or not (m or re.search(r"\b(?:vs\.?|versus)\b", q, re.I)):
        return []
    return [f"What is {p}" for p in parts[:4] if len(p) >= 2]


def perspectives(topic: str, limit: int = 4, lang: str = "en") -> Dict[str, Any]:
    """STORM: عناوين أقسام مقال ويكيبيديا الأقرب للموضوع = زوايا البحث (بلغة الموضوع)."""
    import world_search as w
    topic = str(topic or "").strip()
    if not topic:
        return {"article": None, "sections": []}
    import httpx
    # سياسة ويكيميديا: هوية روبوت بعنوان تواصل (UA_BOT) — المتصفح المقلَّد يُرفض بـ 403
    with httpx.Client(timeout=6.0, headers={"User-Agent": w.UA_BOT}) as c:
        api = f"https://{lang}.wikipedia.org/w/api.php"
        r = c.get(api, params={"action": "query", "list": "search", "srsearch": topic, "srlimit": 3, "format": "json"})
        r.raise_for_status()
        hits = r.json().get("query", {}).get("search", [])
        # المقال يجب أن يكون عن الموضوع نفسه: كلمات عنوانه من كلمات الموضوع (لا مقال جانبي طابق كلمة)
        topic_terms = set(w._terms(topic, lang))
        hits = [h for h in hits if set(w._terms(h["title"], lang)) & topic_terms]
        if not hits:
            return {"article": None, "sections": []}
        title = hits[0]["title"]
        r2 = c.get(api, params={
            "action": "parse", "page": title, "prop": "sections", "format": "json", "redirects": 1})
        r2.raise_for_status()
        secs = r2.json().get("parse", {}).get("sections", [])
    out = []
    for s in secs:
        name = re.sub(r"<[^>]+>", "", s.get("line") or "").strip()
        if str(s.get("toclevel")) != "1" or not name or name.lower() in _STORM_EXCLUDED:
            continue
        out.append(name)
    return {"article": title, "sections": out[:limit]}


def plan(question: str, breadth: int = 3) -> Dict[str, Any]:
    """أسئلة فرعية بعدد breadth: تفكيك الكيانات (MindSearch) ثم زوايا الموضوع (STORM)."""
    import search_platforms as sp
    import world_search as w
    user_lang = w.detect_lang(question)
    core = w.core_question(question)
    if user_lang == "en":
        en_q = core
    else:
        tr, name = w.translate(core, "en", user_lang)
        en_q = tr if name else ""  # الترجمة فشلت ⇒ لا سؤال إنجليزي مختلق؛ التخطيط بلغة السائل
    intent = sp.analyze(question, en_q, user_lang, w.is_fresh(question), w.is_tech(question))
    subs: List[Dict[str, str]] = []
    if bool(_DIRECT_KINDS & set(intent["kinds"])):
        return {"user_lang": user_lang, "en_q": en_q, "intent": intent, "sub_questions": [],
                "article": None, "note": "سؤال لحظي (صرف/ذهب/طقس/وقت) — الإجابة المباشرة الحية هي الجواب"}
    for q in decompose(en_q):
        subs.append({"q": q, "origin": "MindSearch", "aspect": q[8:], "lang": "en"})
    for q in w.split_subquestions(en_q) if en_q else []:
        if len(w.split_subquestions(en_q)) > 1 and not any(q == s["q"] for s in subs):
            subs.append({"q": q, "origin": "MindSearch", "aspect": q, "lang": "en"})
    article, errors, spare = None, [], []
    if len(subs) < breadth:
        plang = "en" if en_q else user_lang
        topic = w.keyword_query(en_q or core, plang)
        try:
            pv = perspectives(topic, limit=breadth + 2, lang=plang)
            article = pv["article"]
            for sec in pv["sections"]:
                if len(subs) >= breadth:
                    spare.append(f"{article} {sec}")  # زاوية لم تُبحث ⇒ سؤال ذو صلة (farfalle)
                    continue
                subs.append({"q": f"{article} {sec}", "origin": "STORM", "aspect": sec, "lang": plang})
        except Exception as exc:  # TOLERATED: ويكيبيديا غير متاحة ⇒ التخطيط يكمل بالتفكيك وحده ويُعلن السبب
            errors.append(f"STORM: {type(exc).__name__}: {str(exc)[:120]}")
    return {"user_lang": user_lang, "en_q": en_q, "intent": intent, "sub_questions": subs[:breadth],
            "article": article, "errors": errors, "spare": spare}


# ---------- ٣) التنقيح: مُقيِّم node-DeepResearch ----------

def evaluation_types(question: str, en_q: str, intent: Dict[str, Any]) -> List[str]:
    """أنواع التقييم المطلوبة: definitive دائمًا، freshness للآني، plurality للتعداد، completeness للكيانات المسماة."""
    import world_search as w
    types = ["definitive"]
    if w.is_fresh(question) or w.is_fresh(en_q or ""):
        types.append("freshness")
    if decompose(en_q) or len(w.split_subquestions(en_q or "")) > 1:
        types.append("completeness")  # يسبق plurality كما في evaluator.ts
    elif intent.get("answer_type") == "list" or re.search(r"\b(?:types|examples|ways|benefits|symptoms|causes|"
                                                           r"top \d+|list)\b", en_q or "", re.I):
        types.append("plurality")
    return types


def evaluate(question: str, en_q: str, intent: Dict[str, Any], types: List[str],
             results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """حكم حتمي لكل نوع + فجوات تتحول إلى أسئلة متابعة (تأمل open_deep_research)."""
    import world_search as w
    pts = [p for r in results for p in (r.get("points") or [])]
    checks: Dict[str, Dict[str, Any]] = {}
    gaps: List[str] = []
    strong = [p for p in pts if p.get("structured") or p.get("score", 0) >= 0.6]
    checks["definitive"] = {"pass": bool(strong), "reason": f"{len(strong)} نقطة قوية (منظّمة أو درجة ≥ 0.6)"}
    if not strong and en_q:
        gaps.append(w.scholarly_query(en_q) if "scholarly" in intent.get("kinds", []) else w.keyword_query(en_q, "en"))
    if "freshness" in types:
        recent = [p for p in pts if (w.age_days(p.get("published")) or 999) <= 30 or p.get("instant")]
        news = sum(len(r.get("news") or []) for r in results)
        checks["freshness"] = {"pass": bool(recent or news), "reason": f"{len(recent)} نقطة حديثة و{news} عنوانًا"}
        if not (recent or news) and en_q:
            gaps.append(f"{w.keyword_query(en_q, 'en')} latest {time.gmtime().tm_year}")
    if "completeness" in types:
        ents = [q[8:] for q in decompose(en_q)] or w.split_subquestions(en_q)
        blob = " ".join(f"{p.get('original', '')} {p.get('text', '')}" for p in pts).lower()
        missing = [e for e in ents if not set(w._terms(e, "en")) <= set(w._terms(blob, "en"))]
        checks["completeness"] = {"pass": not missing, "reason": ("كل الكيانات مغطاة" if not missing
                                                                  else "غير مغطى: " + "، ".join(missing))}
        gaps += [f"{e} {w.keyword_query(en_q, 'en')}" for e in missing]
    if "plurality" in types:
        n = len({p.get("text") for p in pts if not p.get("instant")})
        checks["plurality"] = {"pass": n >= 3, "reason": f"{n} عنصرًا مستقلًا (المطلوب ≥ 3)"}
        if n < 3 and en_q:
            gaps.append(f"{w.keyword_query(en_q, 'en')} list")
    nums = w.numeric_check([p for p in pts if not p.get("structured")])
    if nums and nums.get("kind") != "consensus":
        checks["numbers"] = {"pass": False, "reason": "تتباين الأرقام بين المصادر"}
        if en_q:
            gaps.append(f"{w.keyword_query(en_q, 'en')} official figure")
    return {"checks": checks, "gaps": list(dict.fromkeys(g for g in gaps if g)),
            "passed": all(c["pass"] for c in checks.values())}


# ---------- ٢) التنفيذ + ٤) النشر ----------

def run(question: str, breadth: int = 3, depth: int = 2, target_lang: Optional[str] = None) -> Dict[str, Any]:
    """سؤال ⇒ تقرير بحثي عميق: تخطيط ← بحث متوازٍ بعرض/عمق ← تقييم وسد فجوات ← تقرير مستشهد."""
    import world_search as w
    t0 = time.monotonic()
    question = str(question or "").strip()[:600]
    if not question:
        return {"ok": False, "error": "سؤال فارغ"}
    breadth = max(1, min(int(breadth or 3), 5))
    depth = max(1, min(int(depth or 2), 3))
    budget = _env_float("DEEP_RESEARCH_BUDGET_SECONDS", 110.0)
    deadline = t0 + budget
    pl = plan(question, breadth)
    user_lang = target_lang or pl["user_lang"]
    en_q, intent = pl["en_q"], pl["intent"]
    types = evaluation_types(question, en_q, intent)
    sections: List[Dict[str, Any]] = []
    rounds: List[Dict[str, Any]] = []

    def _ask(q: str, per: float) -> Dict[str, Any]:
        return w.answer(q, user_lang, budget=per)

    # الجولة ٠: السؤال نفسه مع أول دفعة أسئلة فرعية — متوازية
    asked: List[str] = [question]
    level_qs = [s["q"] for s in pl["sub_questions"]]
    with ThreadPoolExecutor(max_workers=1 + breadth) as pool:
        per = max(15.0, min(40.0, deadline - time.monotonic() - 10))
        fut_main = pool.submit(_ask, question, per)
        futs = [(s, pool.submit(_ask, s["q"], per)) for s in pl["sub_questions"]]
        main = fut_main.result()
        for s, f in futs:
            sections.append({"question": s["q"], "origin": s["origin"], "aspect": s["aspect"], "lang": s["lang"],
                             "result": f.result()})
    asked += level_qs
    rounds.append({"level": 0, "breadth": len(level_qs) + 1, "questions": [question] + level_qs,
                   "seconds": round(time.monotonic() - t0, 1)})
    ev = evaluate(question, en_q, intent, types, [main] + [s["result"] for s in sections])
    level, cur_breadth = 1, breadth
    while level < depth and ev["gaps"] and time.monotonic() < deadline - 20:
        cur_breadth = math.ceil(cur_breadth / 2)  # dzhng: العرض ينتصف مع كل تعمق
        follow = [g for g in ev["gaps"] if g not in asked][:cur_breadth]
        if not follow:
            break
        t1 = time.monotonic()
        per = max(12.0, min(35.0, deadline - time.monotonic() - 8))
        with ThreadPoolExecutor(max_workers=len(follow)) as pool:
            for q, res in zip(follow, pool.map(lambda q_: _ask(q_, per), follow)):
                sections.append({"question": q, "origin": "node-DeepResearch/open_deep_research (سد فجوة)",
                                 "aspect": q, "lang": "en", "result": res})
        asked += follow
        rounds.append({"level": level, "breadth": len(follow), "questions": follow,
                       "seconds": round(time.monotonic() - t1, 1)})
        ev = evaluate(question, en_q, intent, types, [main] + [s["result"] for s in sections])
        level += 1

    # عناوين الأقسام بلغة السائل (دفعة ترجمة واحدة)
    foreign = [s for s in sections if s["lang"] != user_lang]
    if foreign and time.monotonic() < deadline:
        joined, name = w.translate("\n".join(s["aspect"] for s in foreign), user_lang, "en")
        lines = joined.split("\n") if name else []
        if len(lines) == len(foreign):
            for s, t in zip(foreign, lines):
                s["title"] = t.strip()
    for s in sections:
        s.setdefault("title", s["aspect"])

    # توحيد المصادر وترقيمها + تنقيح التكرار بين الأقسام (gpt-researcher/STORM)
    merged_sources: List[Dict[str, Any]] = []
    by_url: Dict[str, int] = {}

    def _remap(res: Dict[str, Any]) -> Dict[int, int]:
        mp = {}
        for src in res.get("sources") or []:
            u = src.get("url")
            if u not in by_url:
                by_url[u] = len(merged_sources) + 1
                merged_sources.append({**src, "n": by_url[u]})
            mp[src.get("n")] = by_url[u]
        return mp
    kept_sets: List[set] = []

    def _points(res: Dict[str, Any]) -> List[Dict[str, Any]]:
        mp = _remap(res)
        out = []
        for p in res.get("points") or []:
            ts = set(w._terms(p.get("text") or "", user_lang))
            if ts and any(w._jaccard(ts, k) > 0.6 for k in kept_sets):
                continue
            kept_sets.append(ts)
            out.append({**p, "source": mp.get(p.get("source"), p.get("source"))})
        return out
    summary = _points(main)
    main_news = [{**n, "source": _remap(main).get(n.get("source"), n.get("source"))} for n in main.get("news") or []]
    out_sections = []
    for s in sections:
        pts = _points(s["result"])
        if pts:
            out_sections.append({"title": s["title"], "question": s["question"], "origin": s["origin"],
                                 "points": pts, "elapsed_seconds": s["result"].get("elapsed_seconds")})
    all_pts = summary + [p for s in out_sections for p in s["points"]]
    # farfalle related_queries: أسئلة ذات صلة = زوايا STORM لم تُبحث + فجوات المُقيِّم المتبقية، بلغة السائل
    related = [q for q in list(dict.fromkeys((pl.get("spare") or []) + ev["gaps"])) if q not in asked][:5]
    if related and pl.get("en_q") and user_lang != "en" and time.monotonic() < deadline + 5:
        joined, name = w.translate("\n".join(related), user_lang, "en")
        lines = joined.split("\n") if name else []
        related = [x.strip() for x in lines] if len(lines) == len(related) else related
    return {
        "ok": bool(all_pts or main_news), "question": question, "user_lang": user_lang,
        "intent": main.get("intent"), "summary": summary, "news": main_news, "platforms": main.get("platforms") or [],
        "sections": out_sections, "sources": merged_sources, "related": related,
        "numeric_check": w.numeric_check([p for p in all_pts if not p.get("structured")])
        if (main.get("intent") or {}).get("answer_type") == "numeric" else None,
        "plan": {"sub_questions": pl["sub_questions"], "wikipedia_article": pl.get("article"),
                 "note": pl.get("note"), "errors": pl.get("errors") or []},
        "evaluation": {"types": types, **ev}, "rounds": rounds, "depth_reached": level,
        "agents": _AGENTS, "elapsed_seconds": round(time.monotonic() - t0, 2),
        "error": None if all_pts else (main.get("error") or "لا نقاط موثقة كافية"),
        "method": ("تخطيط (تفكيك الكيانات MindSearch + زوايا ويكيبيديا STORM) ← أسئلة فرعية متوازية "
                   "(gpt-researcher) ← حلقة عرض/عمق (dzhng deep-research) كل سؤال بمحرك البحث العالمي الكامل "
                   "← مُقيِّم node-DeepResearch (حسم/حداثة/تعدد/اكتمال/أرقام) وسد الفجوات بأسئلة متابعة "
                   "(open_deep_research) ← تقرير بأقسام ومصادر موحّدة — بلا نموذج لغوي"),
    }


def format_report(res: Dict[str, Any]) -> str:
    """التقرير نصًا (للمحادثة): خلاصة ← أقسام ← تقييم الاكتمال ← مصادر."""
    if not res.get("ok"):
        return f"تعذّر البحث العميق: {res.get('error') or 'خطأ'}"
    lines = [f"بحث عميق: {res['question']}", "", "الخلاصة:"]
    lines += [f"• {p['text']} [{p['source']}]" for p in res.get("summary") or []]
    for n in (res.get("news") or [])[:4]:
        lines.append(f"• {n.get('title')} [{n.get('source')}]")
    for s in res.get("sections") or []:
        lines += ["", f"{s['title']}:"] + [f"• {p['text']} [{p['source']}]" for p in s["points"][:4]]
    ev = res.get("evaluation") or {}
    if ev.get("checks"):
        names = {"definitive": "الحسم", "freshness": "الحداثة", "plurality": "التعدد", "completeness": "الاكتمال",
                 "numbers": "اتساق الأرقام"}
        lines += ["", "تقييم الاكتمال:"] + [f"• {names.get(k, k)}: {'نعم' if v['pass'] else 'لا'} — {v['reason']}"
                                           for k, v in ev["checks"].items()]
    if res.get("related"):
        lines += ["", "أسئلة ذات صلة:"] + [f"• {q}" for q in res["related"]]
    lines += ["", "المصادر:"] + [f"[{s['n']}] {s.get('title') or s['url']} — {s['url']}" for s in res.get("sources") or []]
    lines += ["", f"({len(res.get('sections') or [])} قسمًا، عمق {res.get('depth_reached')}، "
                  f"{res.get('elapsed_seconds')} ث)"]
    return "\n".join(lines)
