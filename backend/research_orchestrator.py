"""منسّق البحث — من يرتب أدوات البحث والاستدلال حسب الهدف (R-738 — بأمر
المالك «اجعل هناك من يرتب عملها»).

`run_research(goal)`: خط إنتاج البحث الموثق:
بحث ويب (web.search) ← جلب المصادر (web.fetch) ← استخراج الحقائق
(reasoning.extract) ← استدلال وتوليف (reasoning.reason) ← تقرير مستشهد
بالمصادر.

كل خطوة تُنفذ عبر سجل R-729 (registry.invoke) — أثر TOOL_INVOKED سيادي
إلزامي لكل استدعاء: لا خطوة بلا أثر. الفشل صادق: أي خطوة تفشل يُعلن
في الخطوات ولا يُختلق ما بعدها (المادة ١ — لا ادعاء بلا دليل).

(اسم الوحدة research_orchestrator تمييزًا لها عن منسّق الدورة السيادي
القائم backend/orchestrator.py — R-603).
"""

import logging

logger = logging.getLogger("sovereign.research")


def run_research(goal: str) -> dict:
    """هدف → تقرير بحثي مستشهد بالمصادر بأثر سيادي لكل خطوة."""
    goal = str(goal or "").strip()[:500]
    if not goal:
        return {"ok": False, "error": "هدف فارغ", "steps": []}

    from tool_registry import get_registry
    import config

    registry = get_registry()
    steps = []

    def _invoke(tool, inputs):
        result = registry.invoke(tool, caller="orchestrator", inputs=inputs)
        steps.append({"step": tool, "ok": bool(result.get("ok")),
                      "error": result.get("error")})
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error") or "فشل خطوة"))
        return result.get("result")

    try:
        # ١) البحث — معيار البند ٢.٥: نتائج حية مستشهدة بمصادر
        search_out = _invoke("web.search", {"query": goal})
        results = search_out.get("results", [])
        if not results:
            raise RuntimeError("لا نتائج بحث لهذا الهدف")

        # ٢) قراءة أعلى المصادر (بحد المنسّق)
        max_sources = max(1, int(getattr(config, "RESEARCH_MAX_SOURCES", 3)))
        sources, extracts = [], []
        for item in results[:max_sources]:
            url = item.get("url")
            if not url:
                continue
            try:
                page = _invoke("web.fetch", {"url": url})
            except RuntimeError:
                # R-738: صفحة تفشل لا تُسقط الدورة — الخطوة مسجلة في
                # الخطوات (steps) ويُتابع الباقي بصدق
                continue
            sources.append({"url": url, "title": page.get("title", "")})
            extracts.append({"url": url, "text": page.get("text", "")})

        if not sources:
            raise RuntimeError("تعذر قراءة أي مصدر من النتائج")

        # ٣) استخراج الحقائق من كل مصدر — أول سبب فشل يُعلن بصدق إن فشل
        # الجميع (لا حجب للسبب الحقيقي خلف رسالة عامة)
        import json
        facts = []
        first_error = None
        for ex in extracts:
            try:
                extracted = _invoke("reasoning.extract",
                                    {"text": ex["text"],
                                     "schema": "أهم الحقائق والادعاءات"})
            except RuntimeError as e:
                first_error = first_error or str(e)
                continue
            facts.append({"url": ex["url"],
                          "facts": extracted.get("extraction")})

        if not facts:
            raise RuntimeError(first_error or "تعذر استخراج الحقائق من المصادر")

        # ٤) الاستدلال والتوليف — تقرير من المصادر حصرًا
        context = "\n\n".join(
            f"[{f['url']}]\n{json.dumps(f['facts'], ensure_ascii=False)}"
            for f in facts)
        reason_out = _invoke("reasoning.reason",
                             {"question": goal, "context": context})
        report = reason_out.get("reasoning", "")

        return {
            "ok": True,
            "goal": goal,
            "plan": ["web.search", "web.fetch", "reasoning.extract",
                     "reasoning.reason"],
            "steps": steps,
            "sources": sources,
            "facts": facts,
            "report": report,
        }
    except RuntimeError as e:
        return {"ok": False, "goal": goal, "error": str(e), "steps": steps}
    except Exception as e:
        logger.warning("R-738 [research]: فشل غير متوقع (%s)",
                       type(e).__name__)
        return {"ok": False, "goal": goal,
                "error": f"فشل المنسّق ({type(e).__name__}) — لا تقرير مختلق",
                "steps": steps}
