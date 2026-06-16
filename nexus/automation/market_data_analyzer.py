"""
NexusCore — محلل بيانات السوق
بديل آمن لـ market_operator.py — يحلل ويقرر، لا يتداول آلياً.
"""
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.automation.market_data")


@dataclass
class MarketSnapshot:
    symbol: str
    price: float
    volume: float
    timestamp: float = field(default_factory=time.time)
    source: str = "manual"


@dataclass
class MarketSummary:
    symbol: str
    avg_price: float
    min_price: float
    max_price: float
    price_change_pct: float
    avg_volume: float
    volatility: float
    data_points: int
    period_seconds: float


class MarketDataAnalyzer:
    """محلل بيانات السوق — للقراءة والتحليل فقط"""

    def __init__(self, max_history: int = 10_000):
        self.snapshots: Dict[str, List[MarketSnapshot]] = {}
        self.max_history = max_history
        logger.info("📈 MarketDataAnalyzer initialized (read-only)")

    def add_snapshot(self, symbol: str, price: float,
                     volume: float = 0.0, source: str = "manual") -> None:
        snap = MarketSnapshot(symbol=symbol, price=price,
                              volume=volume, source=source)
        self.snapshots.setdefault(symbol, []).append(snap)
        if len(self.snapshots[symbol]) > self.max_history:
            self.snapshots[symbol] = self.snapshots[symbol][-self.max_history:]

    def summarize(self, symbol: str,
                  window_seconds: int = 3600) -> Optional[MarketSummary]:
        snaps = self.snapshots.get(symbol, [])
        if not snaps:
            return None
        cutoff = time.time() - window_seconds
        recent = [s for s in snaps if s.timestamp >= cutoff]
        if not recent:
            recent = snaps[-50:]

        prices  = [s.price for s in recent]
        volumes = [s.volume for s in recent]
        first_p = recent[0].price
        last_p  = recent[-1].price
        change  = (last_p - first_p) / first_p * 100 if first_p else 0.0
        vol     = statistics.stdev(prices) if len(prices) > 1 else 0.0
        period  = recent[-1].timestamp - recent[0].timestamp

        return MarketSummary(
            symbol=symbol,
            avg_price=round(sum(prices) / len(prices), 4),
            min_price=round(min(prices), 4),
            max_price=round(max(prices), 4),
            price_change_pct=round(change, 3),
            avg_volume=round(sum(volumes) / len(volumes), 2),
            volatility=round(vol, 4),
            data_points=len(recent),
            period_seconds=round(period, 1),
        )

    def detect_anomalies(self, symbol: str,
                         threshold_sigma: float = 2.5) -> List[Dict]:
        snaps = self.snapshots.get(symbol, [])
        if len(snaps) < 10:
            return []
        prices = [s.price for s in snaps]
        mean   = statistics.mean(prices)
        std    = statistics.stdev(prices)
        return [
            {"timestamp": s.timestamp, "price": s.price,
             "deviation_sigma": round(abs(s.price - mean) / std, 2)}
            for s in snaps
            if std > 0 and abs(s.price - mean) / std > threshold_sigma
        ]

    def compare_symbols(self, symbols: List[str]) -> List[Dict]:
        results = []
        for sym in symbols:
            summ = self.summarize(sym)
            if summ:
                results.append({
                    "symbol": sym,
                    "avg_price": summ.avg_price,
                    "change_pct": summ.price_change_pct,
                    "volatility": summ.volatility,
                    "data_points": summ.data_points,
                })
        return sorted(results, key=lambda x: x["change_pct"], reverse=True)
