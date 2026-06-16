"""
NexusCore — مكتشف العلاقات
يجد العلاقات والارتباطات بين حقول البيانات المختلفة.
"""
import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nexus.analytics.relationship")


@dataclass
class Relationship:
    field_a: str
    field_b: str
    correlation: float    # -1.0 … +1.0
    strength: str         # weak / moderate / strong
    direction: str        # positive / negative / none
    sample_size: int


class RelationshipFinder:
    """يحسب الارتباطات ويكتشف العلاقات بين الحقول"""

    def __init__(self, min_sample: int = 5):
        self.min_sample = min_sample
        self.relationships: List[Relationship] = []
        logger.info("🔗 RelationshipFinder initialized")

    def find_correlations(self, records: List[Dict],
                          numeric_fields: Optional[List[str]] = None) -> List[Relationship]:
        if not records or len(records) < self.min_sample:
            return []
        # اكتشاف الحقول الرقمية تلقائياً
        if numeric_fields is None:
            numeric_fields = [
                k for k in records[0].keys()
                if isinstance(records[0].get(k), (int, float))
            ]
        results: List[Relationship] = []
        for i, fa in enumerate(numeric_fields):
            for fb in numeric_fields[i + 1:]:
                pairs = [
                    (r[fa], r[fb]) for r in records
                    if isinstance(r.get(fa), (int, float))
                    and isinstance(r.get(fb), (int, float))
                ]
                if len(pairs) < self.min_sample:
                    continue
                corr = self._pearson(pairs)
                strength = (
                    "strong"   if abs(corr) > 0.7 else
                    "moderate" if abs(corr) > 0.4 else "weak"
                )
                direction = "positive" if corr > 0.1 else "negative" if corr < -0.1 else "none"
                rel = Relationship(field_a=fa, field_b=fb,
                                   correlation=round(corr, 3),
                                   strength=strength, direction=direction,
                                   sample_size=len(pairs))
                results.append(rel)
        self.relationships.extend(results)
        return results

    def find_category_links(self, records: List[Dict],
                            cat_field: str, value_field: str) -> Dict:
        groups: Dict[Any, List[float]] = {}
        for r in records:
            cat = r.get(cat_field)
            val = r.get(value_field)
            if cat is not None and isinstance(val, (int, float)):
                groups.setdefault(cat, []).append(val)
        return {
            str(cat): {
                "count": len(vals),
                "mean": round(sum(vals) / len(vals), 3),
                "min": min(vals),
                "max": max(vals),
            }
            for cat, vals in groups.items()
        }

    @staticmethod
    def _pearson(pairs: List[Tuple[float, float]]) -> float:
        n = len(pairs)
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in pairs)
        dx  = math.sqrt(sum((x - mx) ** 2 for x in xs))
        dy  = math.sqrt(sum((y - my) ** 2 for y in ys))
        return num / (dx * dy) if dx * dy else 0.0

    def get_strong_relationships(self, threshold: float = 0.7) -> List[Relationship]:
        return [r for r in self.relationships if abs(r.correlation) >= threshold]
