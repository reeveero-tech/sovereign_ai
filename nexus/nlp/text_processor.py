"""
NexusCore — معالج النصوص
تنظيف، تجزئة، واستخراج بيانات من النصوص.
"""
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

logger = logging.getLogger("nexus.nlp.text")

_STOP_AR = {"في","من","إلى","على","هذا","هذه","التي","الذي","عن","مع","هو","هي"}
_STOP_EN = {"the","a","an","is","in","on","at","to","of","and","or","not","for"}


@dataclass
class ProcessedText:
    original: str
    cleaned: str
    tokens: List[str]
    sentences: List[str]
    keywords: List[str]
    word_count: int
    char_count: int
    language: str


class TextProcessor:
    """يعالج النصوص: تنظيف، تجزئة، استخراج كلمات مفتاحية"""

    def __init__(self, extra_stopwords: Optional[Set[str]] = None):
        self.stopwords = _STOP_AR | _STOP_EN | (extra_stopwords or set())
        logger.info("📝 TextProcessor initialized")

    def process(self, text: str) -> ProcessedText:
        cleaned   = self._clean(text)
        tokens    = self._tokenize(cleaned)
        sentences = self._split_sentences(text)
        keywords  = self._extract_keywords(tokens)
        lang      = self._detect_language(text)
        return ProcessedText(
            original=text, cleaned=cleaned, tokens=tokens,
            sentences=sentences, keywords=keywords,
            word_count=len(tokens), char_count=len(text), language=lang,
        )

    def _clean(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'[^\w\s\u0600-\u06FF.,!?؟،]', '', text)
        return text

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in re.findall(r'\w+', text.lower()) if len(t) > 1]

    def _split_sentences(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r'[.!?؟]\s+', text) if s.strip()]

    def _extract_keywords(self, tokens: List[str],
                          top_n: int = 10) -> List[str]:
        from collections import Counter
        counts = Counter(t for t in tokens if t not in self.stopwords and len(t) > 3)
        return [w for w, _ in counts.most_common(top_n)]

    def _detect_language(self, text: str) -> str:
        ar = len(re.findall(r'[\u0600-\u06FF]', text))
        en = len(re.findall(r'[a-zA-Z]', text))
        return "ar" if ar > en else "en" if en > ar else "mixed"

    def batch_process(self, texts: List[str]) -> List[ProcessedText]:
        return [self.process(t) for t in texts]

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        entities: Dict[str, List[str]] = {"emails": [], "urls": [], "numbers": []}
        entities["emails"]  = re.findall(r'\b[\w.]+@[\w.]+\.\w+\b', text)
        entities["urls"]    = re.findall(r'https?://\S+', text)
        entities["numbers"] = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        return entities
