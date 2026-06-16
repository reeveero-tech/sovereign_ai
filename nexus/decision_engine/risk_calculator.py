"""
NexusCore — حاسبة المخاطر
تحسب درجات المخاطرة لأي قرار أو حدث.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.decision.risk")


@dataclass
class RiskAssessment:
    subject: str
    overall_score: float       # 0.0 – 1.0
    level: str                 # low / medium / high / critical
    factors: Dict[str, float]  # عامل → درجة
    recommendations: List[str]
    timestamp: float = field(default_factory=time.time)


RISK_THRESHOLDS = {
    "low": 0.3, "medium": 0.6, "high": 0.85, "critical": 1.0
}


class RiskCalculator:
    """حاسبة مخاطر متعددة الأبعاد"""

    def __init__(self):
        self.assessments: List[RiskAssessment] = []
        self._weights: Dict[str, float] = {
            "probability":  0.3,
            "impact":       0.4,
            "reversibility": 0.2,
            "exposure":     0.1,
        }
        logger.info("⚖️ RiskCalculator initialized")

    def assess(self, subject: str, factors: Dict[str, float]) -> RiskAssessment:
        # احسب الدرجة الإجمالية (مزيج موزون)
        score = 0.0
        for factor, value in factors.items():
            w = self._weights.get(factor, 0.1)
            score += min(1.0, max(0.0, float(value))) * w

        # إذا لم تُعطَ أوزان مخصصة، حساب بسيط
        if not any(f in self._weights for f in factors):
            score = sum(min(1.0, max(0.0, float(v))) for v in factors.values()) / max(len(factors), 1)

        score = min(1.0, score)
        level = next(
            (k for k, threshold in RISK_THRESHOLDS.items() if score <= threshold),
            "critical"
        )
        recommendations = self._generate_recommendations(level, factors)
        assessment = RiskAssessment(
            subject=subject, overall_score=round(score, 3),
            level=level, factors={k: round(v, 3) for k, v in factors.items()},
            recommendations=recommendations
        )
        self.assessments.append(assessment)
        return assessment

    def _generate_recommendations(self, level: str, factors: Dict[str, float]) -> List[str]:
        recs: List[str] = []
        if level in ("high", "critical"):
            recs.append("يوصى بمراجعة بشرية قبل المتابعة")
            recs.append("إنشاء نسخة احتياطية قبل أي إجراء")
        if factors.get("probability", 0) > 0.7:
            recs.append("احتمالية المخاطرة عالية — قلل نطاق العمل")
        if factors.get("impact", 0) > 0.8:
            recs.append("تأثير محتمل كبير — خطط لبروتوكول تعافٍ")
        if not recs:
            recs.append("مستوى مخاطرة مقبول — يمكن المتابعة")
        return recs

    def get_summary(self) -> Dict:
        if not self.assessments:
            return {}
        levels = {}
        for a in self.assessments:
            levels[a.level] = levels.get(a.level, 0) + 1
        avg = sum(a.overall_score for a in self.assessments) / len(self.assessments)
        return {"total": len(self.assessments), "avg_score": round(avg, 3),
                "by_level": levels}
