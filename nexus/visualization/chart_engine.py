"""
NexusCore — محرك الرسوم البيانية
يولد بيانات الرسوم البيانية بتنسيق JSON جاهز للعرض (Chart.js / Plotly).
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.visualization.chart")


@dataclass
class ChartData:
    chart_id: str
    chart_type: str   # line / bar / pie / scatter / area
    title: str
    labels: List[str]
    datasets: List[Dict]
    options: Dict = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)


class ChartEngine:
    """يولد بيانات رسوم بيانية بتنسيق JSON"""

    COLORS = [
        "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
        "#8B5CF6", "#EC4899", "#14B8A6", "#F97316",
    ]

    def __init__(self):
        self.charts: Dict[str, ChartData] = {}
        logger.info("📊 ChartEngine initialized")

    def line_chart(self, title: str, labels: List[str],
                   series: Dict[str, List[float]],
                   chart_id: Optional[str] = None) -> ChartData:
        import uuid
        cid = chart_id or uuid.uuid4().hex[:8]
        datasets = [
            {"label": name, "data": values,
             "borderColor": self.COLORS[i % len(self.COLORS)],
             "fill": False, "tension": 0.4}
            for i, (name, values) in enumerate(series.items())
        ]
        chart = ChartData(chart_id=cid, chart_type="line", title=title,
                          labels=labels, datasets=datasets,
                          options={"responsive": True, "maintainAspectRatio": False})
        self.charts[cid] = chart
        return chart

    def bar_chart(self, title: str, labels: List[str],
                  series: Dict[str, List[float]],
                  chart_id: Optional[str] = None) -> ChartData:
        import uuid
        cid = chart_id or uuid.uuid4().hex[:8]
        datasets = [
            {"label": name, "data": values,
             "backgroundColor": self.COLORS[i % len(self.COLORS)]}
            for i, (name, values) in enumerate(series.items())
        ]
        chart = ChartData(chart_id=cid, chart_type="bar", title=title,
                          labels=labels, datasets=datasets)
        self.charts[cid] = chart
        return chart

    def pie_chart(self, title: str, labels: List[str],
                  values: List[float], chart_id: Optional[str] = None) -> ChartData:
        import uuid
        cid = chart_id or uuid.uuid4().hex[:8]
        total = sum(values) or 1
        pcts  = [round(v / total * 100, 1) for v in values]
        dataset = {
            "data": pcts,
            "backgroundColor": self.COLORS[:len(labels)],
        }
        chart = ChartData(chart_id=cid, chart_type="pie", title=title,
                          labels=labels, datasets=[dataset])
        self.charts[cid] = chart
        return chart

    def scatter_chart(self, title: str,
                      points: List[Dict[str, float]],
                      chart_id: Optional[str] = None) -> ChartData:
        import uuid
        cid = chart_id or uuid.uuid4().hex[:8]
        dataset = {"data": points, "backgroundColor": self.COLORS[0]}
        chart = ChartData(chart_id=cid, chart_type="scatter", title=title,
                          labels=[], datasets=[dataset])
        self.charts[cid] = chart
        return chart

    def to_json(self, chart: ChartData) -> Dict:
        return {
            "id": chart.chart_id, "type": chart.chart_type,
            "title": chart.title, "labels": chart.labels,
            "datasets": chart.datasets, "options": chart.options,
            "generated_at": chart.generated_at,
        }
