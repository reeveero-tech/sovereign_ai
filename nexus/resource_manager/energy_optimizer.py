"""
NexusCore — محسّن استهلاك الطاقة
بديل آمن لـ power_grid.py و water_manager.py —
يحلل استهلاك الطاقة ويقترح التحسينات.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.resource.energy")


@dataclass
class EnergyReading:
    source: str
    consumption_kwh: float
    timestamp: float = field(default_factory=time.time)
    unit: str = "kWh"
    tags: Dict = field(default_factory=dict)


@dataclass
class OptimizationSuggestion:
    source: str
    current_kwh: float
    target_kwh: float
    saving_pct: float
    action: str
    estimated_saving_usd: float
    priority: str


class EnergyOptimizer:
    """يحلل استهلاك الطاقة ويقترح التحسينات (لا يتحكم مباشرة)"""

    KWH_COST_USD = 0.12

    def __init__(self):
        self.readings: Dict[str, List[EnergyReading]] = {}
        self.suggestions: List[OptimizationSuggestion] = []
        logger.info("⚡ EnergyOptimizer initialized")

    def record(self, source: str, kwh: float,
               tags: Optional[Dict] = None) -> EnergyReading:
        reading = EnergyReading(source=source, consumption_kwh=kwh,
                                tags=tags or {})
        self.readings.setdefault(source, []).append(reading)
        if len(self.readings[source]) > 10_000:
            self.readings[source] = self.readings[source][-10_000:]
        return reading

    def analyze(self, source: str,
                window: int = 24) -> Optional[Dict]:
        """يحلل استهلاك مصدر معين خلال النافذة الزمنية (ساعات)"""
        readings = self.readings.get(source, [])
        if not readings:
            return None
        cutoff = time.time() - window * 3600
        recent = [r for r in readings if r.timestamp >= cutoff]
        if not recent:
            recent = readings[-50:]
        values = [r.consumption_kwh for r in recent]
        avg = sum(values) / len(values)
        peak = max(values)
        base = min(values)
        trend = "stable"
        if len(values) >= 6:
            mid = len(values) // 2
            first_half = sum(values[:mid]) / mid
            second_half = sum(values[mid:]) / (len(values) - mid)
            if second_half > first_half * 1.1:
                trend = "increasing"
            elif second_half < first_half * 0.9:
                trend = "decreasing"
        return {
            "source": source,
            "avg_kwh": round(avg, 3),
            "peak_kwh": round(peak, 3),
            "baseline_kwh": round(base, 3),
            "trend": trend,
            "data_points": len(recent),
            "cost_usd": round(avg * self.KWH_COST_USD, 4),
        }

    def generate_suggestions(self, threshold_pct: float = 20.0) -> List[OptimizationSuggestion]:
        suggestions: List[OptimizationSuggestion] = []
        for source in self.readings:
            analysis = self.analyze(source)
            if not analysis:
                continue
            avg = analysis["avg_kwh"]
            peak = analysis["peak_kwh"]
            if avg == 0:
                continue
            # اقترح تخفيضاً إذا كان الاستهلاك مرتفعاً
            if peak > avg * (1 + threshold_pct / 100):
                target = avg * 0.9
                saving_pct = (avg - target) / avg * 100
                sug = OptimizationSuggestion(
                    source=source,
                    current_kwh=round(avg, 3),
                    target_kwh=round(target, 3),
                    saving_pct=round(saving_pct, 1),
                    action=f"تحسين جدولة استخدام {source} لتجنب الذرى",
                    estimated_saving_usd=round(
                        (avg - target) * self.KWH_COST_USD * 720, 2
                    ),
                    priority="high" if saving_pct > 15 else "medium",
                )
                suggestions.append(sug)
        self.suggestions.extend(suggestions)
        return suggestions

    def get_total_consumption(self) -> Dict:
        totals = {
            source: sum(r.consumption_kwh for r in readings)
            for source, readings in self.readings.items()
        }
        grand_total = sum(totals.values())
        return {
            "by_source": {k: round(v, 3) for k, v in totals.items()},
            "total_kwh": round(grand_total, 3),
            "estimated_cost_usd": round(grand_total * self.KWH_COST_USD, 2),
        }
