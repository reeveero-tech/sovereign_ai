"""
NexusCore — محلل بيانات الأسواق
يحلل بيانات الأسعار والحجم ويولد مؤشرات تقنية بسيطة.
بديل آمن لـ market_operator.py (يحلل فقط — لا يتداول).
"""
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.forecasting.market")


@dataclass
class OHLCV:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class MarketIndicators:
    symbol: str
    sma_20: Optional[float]
    sma_50: Optional[float]
    rsi_14: Optional[float]
    volatility: float
    trend: str
    signal: str          # buy_signal / sell_signal / hold — للتحليل فقط
    confidence: float
    generated_at: float = field(default_factory=time.time)


class MarketAnalyzer:
    """محلل بيانات الأسواق — تحليل تقني، لا تداول آلي"""

    def __init__(self):
        self.data: Dict[str, List[OHLCV]] = {}
        logger.info("📊 MarketAnalyzer initialized (read-only analysis)")

    def add_candle(self, symbol: str, ohlcv: OHLCV) -> None:
        self.data.setdefault(symbol, []).append(ohlcv)
        if len(self.data[symbol]) > 1000:
            self.data[symbol] = self.data[symbol][-1000:]

    def add_candles_from_list(self, symbol: str, records: List[Dict]) -> None:
        for r in records:
            self.add_candle(symbol, OHLCV(**r))

    def analyze(self, symbol: str) -> Optional[MarketIndicators]:
        candles = self.data.get(symbol, [])
        if len(candles) < 20:
            return None
        closes  = [c.close for c in candles]
        sma20   = self._sma(closes, 20)
        sma50   = self._sma(closes, 50) if len(closes) >= 50 else None
        rsi14   = self._rsi(closes, 14)
        vol     = self._volatility(closes[-20:])
        trend   = "bullish" if (sma50 and sma20 > sma50) else "bearish" if sma50 else "neutral"
        # إشارة تحليلية فقط
        if rsi14 and rsi14 < 30 and trend == "bullish":
            signal, conf = "buy_signal", 0.75
        elif rsi14 and rsi14 > 70:
            signal, conf = "sell_signal", 0.70
        else:
            signal, conf = "hold", 0.50
        return MarketIndicators(
            symbol=symbol, sma_20=round(sma20, 4),
            sma_50=round(sma50, 4) if sma50 else None,
            rsi_14=round(rsi14, 2) if rsi14 else None,
            volatility=round(vol, 4), trend=trend,
            signal=signal, confidence=conf,
        )

    @staticmethod
    def _sma(closes: List[float], period: int) -> float:
        return sum(closes[-period:]) / period

    @staticmethod
    def _rsi(closes: List[float], period: int) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains  = [max(d, 0) for d in deltas[-period:]]
        losses = [abs(min(d, 0)) for d in deltas[-period:]]
        avg_g  = sum(gains)  / period
        avg_l  = sum(losses) / period
        if avg_l == 0:
            return 100.0
        rs = avg_g / avg_l
        return 100 - 100 / (1 + rs)

    @staticmethod
    def _volatility(closes: List[float]) -> float:
        if len(closes) < 2:
            return 0.0
        mean = sum(closes) / len(closes)
        var  = sum((c - mean) ** 2 for c in closes) / len(closes)
        return math.sqrt(var)
