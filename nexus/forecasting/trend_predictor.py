"""
NexusCore — متنبئ الاتجاهات
يتنبأ بالاتجاهات المستقبلية من البيانات التاريخية (linear regression بسيط).
"""
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("nexus.forecasting.trend")


@dataclass
class DataPoint:
    timestamp: float
    value: float
    label: str = ""


@dataclass
class Forecast:
    metric: str
    current_value: float
    predicted_value: float
    horizon_seconds: int
    confidence: float
    trend: str          # up / down / stable
    slope: float
    r_squared: float
    generated_at: float = field(default_factory=time.time)


class TrendPredictor:
    """يتنبأ باتجاهات المقاييس بالانحدار الخطي"""

    def __init__(self, min_points: int = 5):
        self.min_points = min_points
        self.series: Dict[str, List[DataPoint]] = {}
        self.forecasts: List[Forecast] = []
        logger.info("📈 TrendPredictor initialized")

    def add_point(self, metric: str, value: float,
                  timestamp: Optional[float] = None) -> None:
        ts = timestamp or time.time()
        self.series.setdefault(metric, []).append(DataPoint(ts, value))
        if len(self.series[metric]) > 10_000:
            self.series[metric] = self.series[metric][-10_000:]

    def predict(self, metric: str, horizon_seconds: int = 3600) -> Optional[Forecast]:
        points = self.series.get(metric, [])
        if len(points) < self.min_points:
            logger.warning(f"Not enough points for {metric}")
            return None

        xs = [p.timestamp for p in points]
        ys = [p.value for p in points]
        slope, intercept, r2 = self._linear_regression(xs, ys)

        future_ts     = points[-1].timestamp + horizon_seconds
        predicted_val = slope * future_ts + intercept
        current_val   = points[-1].value
        confidence    = min(1.0, max(0.0, r2))
        trend = "up" if slope > 1e-6 else "down" if slope < -1e-6 else "stable"

        forecast = Forecast(
            metric=metric,
            current_value=round(current_val, 4),
            predicted_value=round(predicted_val, 4),
            horizon_seconds=horizon_seconds,
            confidence=round(confidence, 3),
            trend=trend,
            slope=round(slope, 8),
            r_squared=round(r2, 3),
        )
        self.forecasts.append(forecast)
        return forecast

    @staticmethod
    def _linear_regression(xs: List[float],
                            ys: List[float]) -> Tuple[float, float, float]:
        n  = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        ss_xy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        ss_xx = sum((x - mx) ** 2 for x in xs)
        slope     = ss_xy / ss_xx if ss_xx else 0.0
        intercept = my - slope * mx
        ys_pred   = [slope * x + intercept for x in xs]
        ss_res    = sum((y - yp) ** 2 for y, yp in zip(ys, ys_pred))
        ss_tot    = sum((y - my) ** 2 for y in ys)
        r2        = 1 - ss_res / ss_tot if ss_tot else 1.0
        return slope, intercept, max(0.0, r2)

    def get_all_forecasts(self) -> List[Dict]:
        return [
            {"metric": f.metric, "current": f.current_value,
             "predicted": f.predicted_value, "trend": f.trend,
             "confidence": f.confidence, "horizon_h": f.horizon_seconds // 3600}
            for f in self.forecasts[-50:]
        ]
