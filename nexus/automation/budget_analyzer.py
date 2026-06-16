"""
NexusCore — محلل الميزانية
بديل آمن لـ fund_blocker.py — يحلل فقط، لا يتحكم في التمويل.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("nexus.automation.budget")


@dataclass
class BudgetItem:
    category: str
    allocated: float
    spent: float
    currency: str = "USD"
    period: str = "monthly"

    @property
    def remaining(self) -> float:
        return self.allocated - self.spent

    @property
    def utilization(self) -> float:
        return self.spent / self.allocated if self.allocated > 0 else 0.0


@dataclass
class BudgetReport:
    total_allocated: float
    total_spent: float
    utilization_rate: float
    over_budget_items: List[str]
    recommendations: List[str]
    generated_at: float = field(default_factory=time.time)


class BudgetAnalyzer:
    """محلل الميزانية — تحليل، تنبيه، توصيات (قراءة فقط)"""

    def __init__(self):
        self.items: Dict[str, BudgetItem] = {}
        self.history: List[BudgetReport] = []
        logger.info("💰 BudgetAnalyzer initialized")

    def add_item(self, category: str, allocated: float,
                 spent: float, currency: str = "USD") -> None:
        self.items[category] = BudgetItem(
            category=category, allocated=allocated,
            spent=spent, currency=currency
        )

    def update_spent(self, category: str, amount: float) -> bool:
        if category in self.items:
            self.items[category].spent = amount
            return True
        return False

    def generate_report(self) -> BudgetReport:
        total_alloc = sum(i.allocated for i in self.items.values())
        total_spent = sum(i.spent for i in self.items.values())
        util_rate   = total_spent / total_alloc if total_alloc > 0 else 0.0

        over_budget = [
            cat for cat, item in self.items.items()
            if item.utilization > 1.0
        ]
        near_limit  = [
            cat for cat, item in self.items.items()
            if 0.9 < item.utilization <= 1.0
        ]

        recommendations: List[str] = []
        if over_budget:
            recommendations.append(
                f"تجاوز الميزانية في: {', '.join(over_budget)} — مراجعة مطلوبة"
            )
        if near_limit:
            recommendations.append(
                f"قريب من الحد في: {', '.join(near_limit)} — توقع إضافي مقترح"
            )
        if util_rate < 0.5:
            recommendations.append("استخدام أقل من 50% — قد تحتاج إعادة توزيع")
        if not recommendations:
            recommendations.append("الميزانية في نطاق سليم")

        report = BudgetReport(
            total_allocated=round(total_alloc, 2),
            total_spent=round(total_spent, 2),
            utilization_rate=round(util_rate, 3),
            over_budget_items=over_budget,
            recommendations=recommendations,
        )
        self.history.append(report)
        return report

    def get_breakdown(self) -> List[Dict]:
        return [
            {"category": item.category, "allocated": item.allocated,
             "spent": item.spent, "remaining": round(item.remaining, 2),
             "utilization_pct": round(item.utilization * 100, 1)}
            for item in self.items.values()
        ]

    def forecast_overspend(self, days_elapsed: int,
                           total_days: int) -> List[Dict]:
        forecasts = []
        for cat, item in self.items.items():
            if days_elapsed > 0 and total_days > 0:
                daily_rate  = item.spent / days_elapsed
                projected   = daily_rate * total_days
                will_exceed = projected > item.allocated
                forecasts.append({
                    "category": cat,
                    "current_rate": round(daily_rate, 2),
                    "projected_total": round(projected, 2),
                    "will_exceed": will_exceed,
                    "surplus_deficit": round(item.allocated - projected, 2),
                })
        return forecasts
