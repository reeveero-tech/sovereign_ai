"""
NexusCore — كاشف الأنماط
يكتشف أنماطاً متكررة في البيانات الرقمية والنصية.
"""
import logging
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nexus.analytics.pattern")


@dataclass
class Pattern:
    pattern_id: str
    description: str
    frequency: int
    confidence: float
    examples: List[Any] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class PatternMapper:
    """يكتشف ويصنّف الأنماط في مجموعات البيانات"""

    def __init__(self, min_frequency: int = 2, min_confidence: float = 0.6):
        self.min_frequency  = min_frequency
        self.min_confidence = min_confidence
        self.discovered: List[Pattern] = []
        logger.info("🔎 PatternMapper initialized")

    # ── بيانات رقمية ────────────────────────────
    def find_numeric_patterns(self, values: List[float]) -> List[Pattern]:
        if len(values) < 4:
            return []
        patterns: List[Pattern] = []
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 0

        # نمط: اتجاه متصاعد
        ascending = all(values[i] <= values[i + 1] for i in range(len(values) - 1))
        if ascending:
            patterns.append(Pattern("ascending_trend", "اتجاه متصاعد",
                                     frequency=1, confidence=1.0,
                                     examples=values[:5], tags=["trend"]))
        # نمط: تذبذب حول المتوسط
        if std > 0:
            within_1std = sum(1 for v in values if abs(v - mean) <= std) / len(values)
            if within_1std > 0.68:
                patterns.append(Pattern("normal_distribution", "توزيع طبيعي",
                                         frequency=len(values), confidence=within_1std,
                                         examples=[round(mean, 2), round(std, 2)],
                                         tags=["distribution"]))
        # نمط: قيم متكررة
        rounded = [round(v, 1) for v in values]
        counter = Counter(rounded)
        for val, cnt in counter.most_common(3):
            if cnt >= self.min_frequency:
                patterns.append(Pattern(f"repeated_{val}", f"قيمة متكررة: {val}",
                                         frequency=cnt,
                                         confidence=min(1.0, cnt / len(values) * 5),
                                         examples=[val], tags=["repetition"]))
        self.discovered.extend(patterns)
        return patterns

    # ── بيانات نصية ─────────────────────────────
    def find_text_patterns(self, texts: List[str]) -> List[Pattern]:
        import re
        patterns: List[Pattern] = []
        all_words: List[str] = []
        for t in texts:
            all_words.extend(re.findall(r'\w+', t.lower()))
        counter = Counter(all_words)
        for word, cnt in counter.most_common(10):
            if len(word) > 3 and cnt >= self.min_frequency:
                conf = min(1.0, cnt / len(texts))
                patterns.append(Pattern(f"word_{word}", f"كلمة متكررة: {word}",
                                         frequency=cnt, confidence=conf,
                                         examples=[word], tags=["text", "frequency"]))
        self.discovered.extend(patterns)
        return patterns

    # ── بيانات هيكلية ────────────────────────────
    def find_structural_patterns(self, records: List[Dict]) -> List[Pattern]:
        if not records:
            return []
        patterns: List[Pattern] = []
        key_counter: Counter = Counter()
        for r in records:
            key_counter.update(r.keys())
        for key, cnt in key_counter.items():
            presence = cnt / len(records)
            if presence >= self.min_confidence:
                patterns.append(Pattern(f"field_{key}", f"حقل شائع: {key}",
                                         frequency=cnt, confidence=presence,
                                         tags=["structure"]))
        self.discovered.extend(patterns)
        return patterns

    def get_summary(self) -> Dict:
        return {
            "total_discovered": len(self.discovered),
            "by_tag": Counter(tag for p in self.discovered for tag in p.tags),
            "top_patterns": [
                {"id": p.pattern_id, "desc": p.description,
                 "freq": p.frequency, "conf": p.confidence}
                for p in sorted(self.discovered, key=lambda x: x.confidence, reverse=True)[:5]
            ],
        }
