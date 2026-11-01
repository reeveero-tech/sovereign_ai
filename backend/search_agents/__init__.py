"""R-829: طبقة وكلاء ومحركات البحث مفتوحة المصدر — كل مشروع مسحوب في third_party/ مربوط هنا بدوره.

أوضاع الربط (صادقة — لا ادعاء تشغيل لما لا يعمل):
- runtime: الكود المسحوب نفسه يعمل داخل محرك البحث الآن (يُحمَّل من third_party/).
- ported: الخوارزمية منقولة إلى بايثون حتمية داخل هذه الحزمة؛ الأصل محفوظ كاملًا مرجعًا للنقل.
- source: الكود محفوظ كاملًا (Rust/TypeScript أو وكيل يتطلب نموذجًا لغويًا مستمرًا)؛ دوره مُعلن
  ومرجعه محدد، ولا يُدّعى أنه يعمل في الخادم الحالي.
"""

import json
from typing import Any, Dict

from . import vendored

_R = "runtime"
_P = "ported"
_S = "source"

_CAPS: Dict[str, Dict[str, Any]] = {
    # ---- يعمل فعليًا ----
    "deedy5/ddgs": {"mode": _R, "module": "search_agents.metasearch",
                    "capability": "مزودات بحث جديدة: Google/Brave/Yandex/Mojeek/Yahoo/Startpage عبر ddgs المسحوبة"},
    "adbar/trafilatura": {"mode": _R, "module": "search_agents.reader",
                          "capability": "استخراج متن الصفحة وتاريخ نشرها وعنوانها عند القراءة (web_tools.fetch)"},
    "dorianbrown/rank_bm25": {"mode": _R, "module": "search_agents.ranking",
                              "capability": "BM25Okapi لانتقاء أصلح جمل الصفحة الطويلة قبل التقييم"},
    "xhluca/bm25s": {"mode": _R, "module": "search_agents.ranking",
                     "capability": "BM25 (Lucene) لترتيب مقاطع البحث العميق"},
    "Sygil-Dev/whoosh-reloaded": {"mode": _R, "module": "search_agents.ranking",
                                  "capability": "جذوع Snowball لـ ١١ لغة بلا جذع سابق (روسي/إيطالي/برتغالي/هولندي/سويدي…) في مطابقة الكلمات"},
    # ---- خوارزميات منقولة ----
    "mat-1/metasearch2": {"mode": _P, "module": "search_agents.metasearch",
                          "reference": "src/engines/ranking.rs",
                          "capability": "دمج نتائج المحركات: Σ وزن/(مرتبة+1) — اتفاق المحركات يرفع أولوية القراءة"},
    "InternLM/MindSearch": {"mode": _P, "module": "search_agents.deep_research",
                            "reference": "mindsearch/agent/graph.py",
                            "capability": "تفكيك السؤال متعدد الكيانات إلى عقد فرعية (البحث العميق)"},
    "stanford-oval/storm": {"mode": _P, "module": "search_agents.deep_research",
                            "reference": "knowledge_storm/storm_wiki/modules/persona_generator.py",
                            "capability": "زوايا البحث من فهرس أقسام ويكيبيديا (البحث العميق)"},
    "assafelovic/gpt-researcher": {"mode": _P, "module": "search_agents.deep_research",
                                   "reference": "gpt_researcher/context/lexical.py",
                                   "capability": "أسئلة فرعية متوازية + تصفية السياق بـ BM25 + تقرير بأقسام"},
    "dzhng/deep-research": {"mode": _P, "module": "search_agents.deep_research",
                            "reference": "src/deep-research.ts",
                            "capability": "حلقة العرض/العمق: كل تعمق بـ ceil(breadth/2) سؤال متابعة"},
    "jina-ai/node-DeepResearch": {"mode": _P, "module": "search_agents.deep_research",
                                  "reference": "src/tools/evaluator.ts",
                                  "capability": "مُقيِّم الإجابة: حسم/حداثة/تعدد/اكتمال قبل اعتماد التقرير"},
    "langchain-ai/open_deep_research": {"mode": _P, "module": "search_agents.deep_research",
                                        "reference": "src/open_deep_research/deep_researcher.py",
                                        "capability": "التأمل وسد الفجوات: ما لم يُغطَّ يتحول إلى سؤال متابعة"},
    "rashadphz/farfalle": {"mode": _P, "module": "search_agents.deep_research",
                           "reference": "src/backend/related_queries.py",
                           "capability": "أسئلة ذات صلة يقترحها التقرير (زوايا وفجوات لم تُبحث بعد)"},

    "mshumer/OpenDeepResearcher": {"mode": _P, "module": "search_agents.deep_research",
                                   "reference": "open_deep_researcher.ipynb",
                                   "capability": "حلقة «هل نحتاج بحثًا إضافيًا؟» — هنا بحكم المُقيِّم الحتمي"},
    # ---- محفوظ كاملًا (دور معلن، لا تشغيل مدّعى) ----
    "huggingface/smolagents": {"mode": _S, "reference": "src/smolagents/agents.py",
                               "capability": "إطار وكلاء الأدوات — يتطلب نموذجًا لغويًا مستمرًا (العقل المحلي)"},
    "togethercomputer/open_deep_research": {"mode": _S, "reference": "README.md",
                                            "capability": "وكيل بحث عميق بنماذج Together — مرجع لتخطيط التقرير"},
    "zamalali/DeepGit": {"mode": _S, "reference": "README.md",
                         "capability": "بحث عميق في مستودعات GitHub — مكمل لمزود GitHub في المنصات"},
    "MiroMindAI/MiroThinker": {"mode": _S, "reference": "README.md",
                               "capability": "وكيل بحث بنموذج مدرَّب على الأدوات — يتطلب خادم نموذج"},
    "SkyworkAI/DeepResearchAgent": {"mode": _S, "reference": "README.md",
                                    "capability": "وكيل بحث هرمي متعدد الوكلاء — يتطلب نموذجًا لغويًا"},
    "NVIDIA-AI-Blueprints/deep-researcher-agent": {"mode": _S, "reference": "README.md",
                                                   "capability": "مخطط NVIDIA للبحث العميق — يتطلب NIM"},
    "jordan-gibbs/hyperresearch": {"mode": _S, "reference": "README.md",
                                   "capability": "وكيل بحث متوازٍ — مرجع لتوزيع الأسئلة الفرعية"},
    "kidzik/web-research-agent": {"mode": _S, "reference": "README.md",
                                  "capability": "وكيل بحث ويب بخطوات — مرجع لخط الاستخراج"},
    "Alibaba-NLP/DeepResearch": {"mode": _S, "reference": "README.md",
                                 "capability": "Tongyi DeepResearch — يتطلب نموذج 30B"},
    "ItzCrazyKns/Vane": {"mode": _S, "reference": "README.md",
                         "capability": "Perplexica: أوضاع التركيز (ويب/أكاديمي/فيديو/نقاشات) — مرجع توجيه المنصات"},
    "mckaywrigley/clarity-ai": {"mode": _S, "reference": "README.md",
                                "capability": "واجهة بحث بإجابة مستشهدة — مرجع لعرض المصادر المرقمة"},
    "benbusby/whoogle-search": {"mode": _S, "reference": "app/filter.py",
                                "capability": "تحليل صفحات نتائج Google — مغطى تشغيليًا بمحرك google في ddgs"},
    "quickwit-oss/tantivy": {"mode": _S, "reference": "README.md",
                             "capability": "محرك فهرسة نصية بلغة Rust — مرشح لفهرس ذاتي محلي كبير"},
    "toshi-search/Toshi": {"mode": _S, "reference": "README.md",
                           "capability": "خادم بحث موزع فوق tantivy (Rust)"},
    "tinysearch/tinysearch": {"mode": _S, "reference": "README.md",
                              "capability": "بحث WebAssembly للمواقع الثابتة (Rust)"},
    "SeekStorm/SeekStorm": {"mode": _S, "reference": "README.md",
                            "capability": "محرك بحث وفهرسة عالي الأداء (Rust)"},
    "lucaong/minisearch": {"mode": _S, "reference": "README.md",
                           "capability": "بحث نصي داخل المتصفح (TypeScript) — مرشح للبحث في المحادثات محليًا"},
    "codelucas/newspaper": {"mode": _S, "reference": "newspaper/article.py",
                            "capability": "استخراج المقالات — مغطى تشغيليًا بـ trafilatura"},
}


def _manifest() -> Dict[str, Dict[str, Any]]:
    path = vendored.ROOT / "MANIFEST.json"
    if not path.exists():
        return {}
    return {p["repo"]: p for p in json.loads(path.read_text(encoding="utf-8")).get("projects", [])}


def registry() -> Dict[str, Dict[str, Any]]:
    """كل مشروع مسحوب ⇒ قدرته ووضعه ووحدته ورخصته وcommit النسخة."""
    man = _manifest()
    out = {}
    for repo, cap in _CAPS.items():
        m = man.get(repo, {})
        out[repo] = {**cap, "module": cap.get("module", ""), "license": m.get("license"),
                     "commit": m.get("commit"), "category": m.get("category"),
                     "dir": repo.replace("/", "__")}
    return out


def status() -> Dict[str, Any]:
    reg = registry()
    counts: Dict[str, int] = {}
    for c in reg.values():
        counts[c["mode"]] = counts.get(c["mode"], 0) + 1
    return {"projects": len(reg), "modes": counts, "runtime_libraries": vendored.status()}
