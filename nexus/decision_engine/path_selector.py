"""
NexusCore — محدد المسارات
يحلل خيارات القرار ويرتبها حسب المخاطر والعائد.
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.decision.path")


@dataclass
class Option:
    option_id: str
    name: str
    description: str
    expected_benefit: float   # 0-100
    estimated_cost: float     # 0-100
    risk_level: float         # 0-1
    metadata: Dict = field(default_factory=dict)


@dataclass
class Decision:
    decision_id: str
    context: str
    options: List[Option]
    selected: Optional[Option]
    score: float
    reasoning: str
    created_at: float = field(default_factory=time.time)
    requires_approval: bool = False


class PathSelector:
    """يرتب الخيارات ويختار الأفضل بناءً على معايير متعددة"""

    def __init__(self, risk_tolerance: float = 0.5):
        self.risk_tolerance = risk_tolerance
        self.history: List[Decision] = []
        logger.info(f"🧭 PathSelector initialized (risk_tolerance={risk_tolerance})")

    def evaluate(self, context: str, options: List[Dict],
                 benefit_weight: float = 0.4, cost_weight: float = 0.3,
                 risk_weight: float = 0.3) -> Decision:
        option_objs = [
            Option(
                option_id=str(uuid.uuid4())[:8],
                name=o.get("name", f"option_{i}"),
                description=o.get("description", ""),
                expected_benefit=float(o.get("benefit", 50)),
                estimated_cost=float(o.get("cost", 50)),
                risk_level=float(o.get("risk", 0.5)),
                metadata=o.get("metadata", {})
            )
            for i, o in enumerate(options)
        ]
        scored = []
        for opt in option_objs:
            # معادلة التقييم: مزيج من العائد والتكلفة والمخاطرة
            score = (
                opt.expected_benefit * benefit_weight
                - opt.estimated_cost * cost_weight
                - opt.risk_level * 100 * risk_weight
            )
            scored.append((opt, round(score, 2)))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_opt, best_score = scored[0] if scored else (None, 0.0)

        # قرارات عالية الخطورة تستلزم موافقة
        needs_approval = best_opt is not None and best_opt.risk_level > 0.8

        decision = Decision(
            decision_id=str(uuid.uuid4())[:8],
            context=context,
            options=option_objs,
            selected=best_opt,
            score=best_score,
            reasoning=(
                f"اختيار '{best_opt.name}' بدرجة {best_score:.1f} "
                f"(عائد={best_opt.expected_benefit}, تكلفة={best_opt.estimated_cost}, "
                f"خطر={best_opt.risk_level:.2f})"
            ) if best_opt else "لا توجد خيارات كافية",
            requires_approval=needs_approval,
        )
        self.history.append(decision)
        if needs_approval:
            logger.warning(f"⚠️ Decision {decision.decision_id} requires approval")
        return decision

    def get_history(self, limit: int = 20) -> List[Dict]:
        return [
            {"id": d.decision_id, "context": d.context,
             "selected": d.selected.name if d.selected else None,
             "score": d.score, "approved_required": d.requires_approval,
             "ts": d.created_at}
            for d in self.history[-limit:]
        ]
