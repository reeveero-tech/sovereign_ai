"""
NexusCore — كاشف اللغة
يكتشف لغة النص بدون مكتبات خارجية.
"""
import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class LanguageResult:
    language: str
    confidence: float
    script: str
    mixed: bool


LANGUAGE_PATTERNS = {
    "ar":  r'[\u0600-\u06FF]',
    "en":  r'[a-zA-Z]',
    "zh":  r'[\u4E00-\u9FFF]',
    "ru":  r'[\u0400-\u04FF]',
    "fr":  r'[àâçéèêëîïôùûüæœ]',
    "de":  r'[äöüßÄÖÜ]',
}

SCRIPT_MAP = {
    "ar": "Arabic",  "en": "Latin", "zh": "Chinese",
    "ru": "Cyrillic", "fr": "Latin", "de": "Latin",
}


class LanguageDetector:
    """يكتشف لغة النص من أنماط الأحرف"""

    def detect(self, text: str) -> LanguageResult:
        if not text.strip():
            return LanguageResult("unknown", 0.0, "unknown", False)

        counts: Dict[str, int] = {}
        for lang, pattern in LANGUAGE_PATTERNS.items():
            counts[lang] = len(re.findall(pattern, text))

        total = sum(counts.values())
        if total == 0:
            return LanguageResult("unknown", 0.0, "unknown", False)

        sorted_langs = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top_lang, top_count = sorted_langs[0]
        confidence = top_count / total
        mixed = confidence < 0.85 and len([c for _, c in sorted_langs if c > 0]) > 1

        return LanguageResult(
            language=top_lang if confidence > 0.3 else "mixed",
            confidence=round(confidence, 3),
            script=SCRIPT_MAP.get(top_lang, "Unknown"),
            mixed=mixed,
        )

    def detect_batch(self, texts: List[str]) -> List[LanguageResult]:
        return [self.detect(t) for t in texts]

    def get_language_distribution(self, texts: List[str]) -> Dict[str, float]:
        results = self.detect_batch(texts)
        total   = len(results)
        counts: Dict[str, int] = {}
        for r in results:
            counts[r.language] = counts.get(r.language, 0) + 1
        return {lang: round(cnt / total, 3) for lang, cnt in counts.items()}
