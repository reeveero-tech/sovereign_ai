"""R-829: ترتيب الصلة بالمكتبات المسحوبة — rank_bm25 (dorianbrown) وbm25s (xhluca) وجذوع Snowball (whoosh).

- top_sentences: انتقاء أصلح جمل الصفحة الطويلة بـ BM25Okapi من rank_bm25 بدل «أول ٦٠ جملة» —
  الجواب كثيرًا ما يقع في منتصف الصفحة. الترتيب الأصلي يُحفظ (السياق يبقى مقروءًا).
- rank_passages: ترتيب مجمّع المقاطع في البحث العميق بـ bm25s (طريقة Lucene) — نفس معادلة
  gpt-researcher context/lexical.py لتصفية السياق بلا نموذج.
- stem: جذوع Snowball من whoosh لكل لغة تدعمها (روسي/إيطالي/برتغالي/هولندي/سويدي…) —
  اللغات التي لم يكن لها جذع في المحرك.
"""

from typing import Callable, List, Optional, Sequence

from . import vendored

# رمز اللغة ← اسم Snowball في whoosh.lang
# (whoosh-reloaded 3.0 لا تحوي التركية — لغة بلا جذع ⇒ الكلمة كما هي، لا استثناء يكسر البحث)
_SNOWBALL = {"ru": "russian", "it": "italian", "pt": "portuguese", "nl": "dutch",
             "sv": "swedish", "da": "danish", "fi": "finnish", "hu": "hungarian", "no": "norwegian",
             "nb": "norwegian", "ro": "romanian", "fr": "french", "es": "spanish", "de": "german",
             "en": "english"}
_STEMMERS: dict = {}


def stem(token: str, lang: str) -> str:
    """جذع Snowball للغة إن دعمتها whoosh، وإلا الكلمة كما هي."""
    name = _SNOWBALL.get(lang)
    if not name:
        return token
    fn = _STEMMERS.get(name)
    if fn is None:
        whoosh = vendored.load("whoosh")
        if whoosh is None:
            return token
        from whoosh.lang import has_stemmer, stemmer_for_language
        fn = stemmer_for_language(name) if has_stemmer(name) else (lambda x: x)
        _STEMMERS[name] = fn
    return fn(token)


def top_sentences(sentences: Sequence[str], query_terms: Sequence[str],
                  tokenize: Callable[[str], List[str]], limit: int = 60) -> List[str]:
    """أصلح `limit` جملة بـ BM25Okapi (rank_bm25)، بترتيبها الأصلي في الصفحة."""
    sents = list(sentences)
    if len(sents) <= limit or not query_terms:
        return sents[:limit]
    mod = vendored.load("rank_bm25")
    if mod is None:
        return sents[:limit]
    toks = [tokenize(s) or ["\u2205"] for s in sents]
    scores = mod.BM25Okapi(toks).get_scores(list(dict.fromkeys(query_terms)))
    keep = sorted(range(len(sents)), key=lambda i: (-scores[i], i))[:limit]
    return [sents[i] for i in sorted(keep)]


def rank_passages(passages: Sequence[str], query_tokens: Sequence[str],
                  tokenize: Callable[[str], List[str]], top: int = 12) -> List[int]:
    """فهارس أعلى المقاطع صلة بـ bm25s (Lucene) — أو ترتيبها كما هي إن تعذّر التحميل."""
    docs = [tokenize(p) or ["\u2205"] for p in passages]
    if not docs:
        return []
    bm25s = vendored.load("bm25s")
    q = [t for t in dict.fromkeys(query_tokens)]
    if bm25s is None or not q:
        return list(range(min(top, len(docs))))
    retriever = bm25s.BM25(method="lucene")
    retriever.index(docs, show_progress=False)
    scores = retriever.get_scores(q)
    order = sorted(range(len(docs)), key=lambda i: (-float(scores[i]), i))
    return [i for i in order[:top] if float(scores[i]) > 0] or order[:min(top, 3)]


def bm25_engine() -> Optional[str]:
    """أي مكتبة BM25 مسحوبة تعمل الآن (للحالة)."""
    return "rank_bm25+bm25s" if vendored.load("rank_bm25") and vendored.load("bm25s") else None
