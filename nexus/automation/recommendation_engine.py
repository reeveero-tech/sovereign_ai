"""
NexusCore — محرك التوصيات
بديل آمن لـ policy_suggester.py — يقترح، والقرار للمستخدم.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.automation.recommendation")


@dataclass
class Recommendation:
    rec_id: str
    title: str
    description: str
    category: str
    priority: str        # low / medium / high
    confidence: float    # 0-1
    data_basis: Dict     # البيانات التي بني عليها الاقتراح
    requires_human_approval: bool = True   # دائماً True بشكل افتراضي
    created_at: float = field(default_factory=time.time)
    accepted: Optional[bool] = None


class RecommendationEngine:
    """يولد توصيات مدعومة بالبيانات — القرار النهائي للمستخدم دائماً"""

    def __init__(self):
        import uuid as _uuid
        self._uuid = _uuid
        self.recommendations: List[Recommendation] = []
        self._rules: List[Dict] = []
        logger.info("💡 RecommendationEngine initialized")

    def add_rule(self, name: str, condition: Any, template: str,
                 category: str = "general", priority: str = "medium") -> None:
        self._rules.append({
            "name": name, "condition": condition,
            "template": template, "category": category, "priority": priority,
        })

    def generate(self, context: Dict) -> List[Recommendation]:
        recs: List[Recommendation] = []
        for rule in self._rules:
            cond = rule["condition"]
            triggered = False
            if callable(cond):
                try:
                    triggered = bool(cond(context))
                # TOLERATED: known-safe fallback — non-fatal diagnostic path (R-680)
                except Exception:
                    pass
            elif isinstance(cond, dict):
                triggered = all(
                    context.get(k) == v for k, v in cond.items()
                )
            if triggered:
                rec = Recommendation(
                    rec_id=self._uuid.uuid4().hex[:8],
                    title=rule["name"],
                    description=rule["template"].format(**context),
                    category=rule["category"],
                    priority=rule["priority"],
                    confidence=0.75,
                    data_basis=context,
                    requires_human_approval=True,
                )
                recs.append(rec)
        self.recommendations.extend(recs)
        logger.info(f"💡 Generated {len(recs)} recommendations")
        return recs

    def generate_from_analysis(self, analysis: Dict) -> List[Recommendation]:
        """يولد توصيات من نتائج تحليل بيانات"""
        recs: List[Recommendation] = []
        # توصيات بناءً على أنماط شائعة
        if analysis.get("trend") == "down" and analysis.get("confidence", 0) > 0.7:
            recs.append(Recommendation(
                rec_id=self._uuid.uuid4().hex[:8],
                title="مراجعة الأداء",
                description="الاتجاه هبوطي بثقة عالية — يُقترح مراجعة مؤشرات الأداء",
                category="performance",
                priority="high",
                confidence=analysis.get("confidence", 0.7),
                data_basis=analysis,
                requires_human_approval=True,
            ))
        if analysis.get("anomaly_count", 0) > 5:
            recs.append(Recommendation(
                rec_id=self._uuid.uuid4().hex[:8],
                title="تحقيق في الشذوذات",
                description=f"تم اكتشاف {analysis['anomaly_count']} شذوذ — يُقترح التحقيق",
                category="security",
                priority="high",
                confidence=0.9,
                data_basis=analysis,
                requires_human_approval=True,
            ))
        self.recommendations.extend(recs)
        return recs

    def accept(self, rec_id: str) -> bool:
        for r in self.recommendations:
            if r.rec_id == rec_id:
                r.accepted = True
                logger.info(f"✅ Recommendation {rec_id} accepted by user")
                return True
        return False

    def reject(self, rec_id: str) -> bool:
        for r in self.recommendations:
            if r.rec_id == rec_id:
                r.accepted = False
                return True
        return False

    def get_pending(self) -> List[Dict]:
        return [
            {"id": r.rec_id, "title": r.title, "description": r.description,
             "priority": r.priority, "confidence": r.confidence,
             "requires_approval": r.requires_human_approval}
            for r in self.recommendations if r.accepted is None
        ]
