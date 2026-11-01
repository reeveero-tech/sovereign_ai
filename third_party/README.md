# المشاريع مفتوحة المصدر المسحوبة (R-829)

مولَّد آليًا من `MANIFEST.json` بواسطة `scripts/vendor_sync.py` — لا تعدّله يدويًا.

كل مشروع منسوخ بكامل كوده عند commit محدد مع رخصته الأصلية. الربط بمحرك البحث وأوضاعه
(runtime يعمل / ported منقول / source محفوظ) في `backend/search_agents/__init__.py`.

## وكلاء البحث والاستنتاج والتنقيح

| المشروع | الرخصة | commit | الملفات | الدور |
|---|---|---|---|---|
| [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) | Apache-2.0 | `3582a6841f` | 822 | تفكيك السؤال إلى أسئلة فرعية + بحث متوازٍ + تقرير مستشهد (planner/execution/publisher) |
| [stanford-oval/storm](https://github.com/stanford-oval/storm) | MIT | `fb951af774` | 70 | اكتشاف المنظورات من مقالات ويكيبيديا المرتبطة ثم أسئلة لكل منظور ومخطط تقرير |
| [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) | MIT | `1b7d2e80db` | 42 | تخطيط أقسام ← بحث لكل قسم ← تأمّل (reflection) لاكتشاف الفجوات ← استعلامات متابعة |
| [dzhng/deep-research](https://github.com/dzhng/deep-research) | MIT | `1f8f3e285b` | 21 | بحث تكراري بعرض/عمق: استعلامات SERP ← تعلّمات ← اتجاهات متابعة ← تعمّق |
| [jina-ai/node-DeepResearch](https://github.com/jina-ai/node-DeepResearch) | Apache-2.0 | `fd323b521a` | 82 | حلقة بحث/قراءة/تأمّل/إجابة حتى ميزانية رموز مع تقييم الإجابة قبل قبولها |
| [InternLM/MindSearch](https://github.com/InternLM/MindSearch) | Apache-2.0 | `7952c5f8a9` | 116 | مخطِّط يبني رسمًا بيانيًا للأسئلة الفرعية (WebPlanner) وباحث لكل عقدة (WebSearcher) |
| [huggingface/smolagents](https://github.com/huggingface/smolagents) | Apache-2.0 | `96f33faaf0` | 184 | وكلاء الكود/الأدوات ومثال open_deep_research (أدوات بحث وقراءة نصية) |
| [togethercomputer/open_deep_research](https://github.com/togethercomputer/open_deep_research) | MIT | `832c05b3be` | 44 | تخطيط استعلامات ← بحث ← تقييم كفاية ← تكرار ← تقرير |
| [mshumer/OpenDeepResearcher](https://github.com/mshumer/OpenDeepResearcher) | MIT | `6bbb94516b` | 4 | حلقة بحث غير متزامنة: استعلامات ← صفحات ← تقييم الصلة ← استخلاص ← قرار المتابعة |
| [zamalali/DeepGit](https://github.com/zamalali/DeepGit) | MIT | `206f634acd` | 41 | بحث عميق في مستودعات GitHub وترتيبها دلاليًا |
| [MiroMindAI/MiroThinker](https://github.com/MiroMindAI/MiroThinker) | Apache-2.0 | `1c4253f677` | 178 | وكيل بحث استنتاجي بأدوات (بحث/قراءة/تنفيذ) |
| [SkyworkAI/DeepResearchAgent](https://github.com/SkyworkAI/DeepResearchAgent) | MIT | `5e3c95d142` | 835 | وكيل تخطيط هرمي يوزع المهام على وكلاء بحث فرعيين |
| [NVIDIA-AI-Blueprints/deep-researcher-agent](https://github.com/NVIDIA-AI-Blueprints/deep-researcher-agent) | Apache-2.0 | `951a1a1114` | 1088 | مخطط بحث عميق: تخطيط ← بحث ← تقييم ← تقرير مع طبقة معرفة |
| [jordan-gibbs/hyperresearch](https://github.com/jordan-gibbs/hyperresearch) | MIT | `aece65f930` | 275 | بحث متعدد المراحل مع تحقق متقاطع |
| [kidzik/web-research-agent](https://github.com/kidzik/web-research-agent) | Apache-2.0 | `e898da019d` | 7 | وكيل بحث ويب بسيط: بحث ← قراءة ← تلخيص |
| [Alibaba-NLP/DeepResearch](https://github.com/Alibaba-NLP/DeepResearch) | Apache-2.0 | `f72f75d8c3` | 276 | Tongyi DeepResearch: WebSailor/WebWalker/WebDancer |

## محركات بحث بالذكاء الاصطناعي

| المشروع | الرخصة | commit | الملفات | الدور |
|---|---|---|---|---|
| [rashadphz/farfalle](https://github.com/rashadphz/farfalle) | Apache-2.0 | `a9dd4939d2` | 151 | محرك إجابات: بحث ← إعادة ترتيب ← إجابة مستشهدة |
| [ItzCrazyKns/Vane](https://github.com/ItzCrazyKns/Vane) | MIT | `348feca3e3` | 233 | Perplexica (Vane): أوضاع تركيز البحث وإعادة الترتيب بالتشابه |
| [mckaywrigley/clarity-ai](https://github.com/mckaywrigley/clarity-ai) | MIT | `5a33db140d` | 23 | محرك إجابات مختصر مستشهد |

## محركات البحث والفهرسة والترتيب

| المشروع | الرخصة | commit | الملفات | الدور |
|---|---|---|---|---|
| [dorianbrown/rank_bm25](https://github.com/dorianbrown/rank_bm25) | Apache-2.0 | `47aa3ddf8d` | 11 | ترتيب Okapi BM25 / BM25L / BM25+ للجمل المرشحة |
| [xhluca/bm25s](https://github.com/xhluca/bm25s) | MIT | `f3d5dbc8b9` | 98 | BM25 سريع بمصفوفات متفرقة |
| [Sygil-Dev/whoosh-reloaded](https://github.com/Sygil-Dev/whoosh-reloaded) | BSD-2-Clause | `4cab4ccc04` | 270 | محرك فهرسة بحث نصي كامل بلغة Python |
| [deedy5/ddgs](https://github.com/deedy5/ddgs) | MIT | `8e74959141` | 53 | بحث فوقي متعدد المحركات (Bing/Brave/DuckDuckGo/Google/Mojeek/Yahoo/Yandex/Wikipedia) |
| [benbusby/whoogle-search](https://github.com/benbusby/whoogle-search) | MIT | `0543f86528` | 150 | وسيط بحث Google بلا تتبع وتحليل نتائجه |
| [mat-1/metasearch2](https://github.com/mat-1/metasearch2) | CC0-1.0 | `910d52a2bc` | 68 | محرك بحث فوقي يدمج النتائج من عدة محركات |
| [quickwit-oss/tantivy](https://github.com/quickwit-oss/tantivy) | MIT | `360a5ebbbb` | 621 | محرك بحث نصي كامل (Rust) — مرجع Lucene-مثله |
| [toshi-search/Toshi](https://github.com/toshi-search/Toshi) | MIT | `a13a51820b` | 79 | خادم بحث نصي كامل فوق tantivy |
| [tinysearch/tinysearch](https://github.com/tinysearch/tinysearch) | Apache-2.0 | `d6c92d5a62` | 63 | فهرس بحث ثابت مضغوط بمرشحات Bloom |
| [SeekStorm/SeekStorm](https://github.com/SeekStorm/SeekStorm) | Apache-2.0 | `2b0847bfda` | 105 | محرك بحث نصي كامل عالي الأداء |
| [lucaong/minisearch](https://github.com/lucaong/minisearch) | MIT | `3d239d1c3a` | 75 | بحث نصي كامل داخل المتصفح (JavaScript) |

## أدوات القراءة والاستخراج

| المشروع | الرخصة | commit | الملفات | الدور |
|---|---|---|---|---|
| [adbar/trafilatura](https://github.com/adbar/trafilatura) | Apache-2.0 | `43ca3d4d65` | 136 | استخراج النص الرئيسي والتاريخ والمؤلف من صفحات الويب |
| [codelucas/newspaper](https://github.com/codelucas/newspaper) | MIT | `745dfe3abe` | 100 | استخراج المقالات الإخبارية (العنوان/النص/التاريخ) |
