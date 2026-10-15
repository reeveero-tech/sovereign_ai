"""
NexusCore — معالج البيانات
تنظيف + تحويل + تطبيع + تقييم الجودة.
"""
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nexus.data_pipeline.processor")


@dataclass
class ProcessedRecord:
    record_id: str
    source: str
    timestamp: float
    raw: Any
    processed: Any
    schema: str
    quality_score: float  # 0.0 – 1.0


class DataProcessor:
    """معالج البيانات — تنظيف، تحويل، تطبيع"""

    def __init__(self):
        self._transformers: Dict[str, List[Callable]] = {}
        self.stats = {"processed": 0, "failed": 0, "total_ms": 0.0}
        logger.info("⚙️ DataProcessor initialized")

    def register_transformer(self, schema: str, fn: Callable) -> None:
        self._transformers.setdefault(schema, []).append(fn)

    def process(self, raw: Any, source: str = "unknown",
                schema: str = "generic") -> Optional[ProcessedRecord]:
        start = time.time()
        try:
            data = self._clean(raw)
            for fn in self._transformers.get(schema, []):
                data = fn(data)
            quality = self._score_quality(data)
            rid = hashlib.md5(
                json.dumps(data, default=str, sort_keys=True).encode()
            ).hexdigest()[:12]
            record = ProcessedRecord(
                record_id=rid, source=source, timestamp=time.time(),
                raw=raw, processed=data, schema=schema, quality_score=quality
            )
            self.stats["processed"] += 1
            self.stats["total_ms"] += (time.time() - start) * 1000
            return record
        except Exception as exc:
            logger.exception(f"R-682: Process error [{source}] — silently swallowing. exc={exc}")
            self.stats["failed"] += 1
            return None

    def process_batch(self, items: List[Any], source: str = "unknown",
                      schema: str = "generic") -> List[ProcessedRecord]:
        return [r for raw in items if (r := self.process(raw, source, schema))]

    def _clean(self, raw: Any) -> Any:
        if isinstance(raw, str):
            return raw.strip()
        if isinstance(raw, dict):
            return {k: self._clean(v) for k, v in raw.items()
                    if v is not None and v != ""}
        if isinstance(raw, list):
            return [self._clean(i) for i in raw if i is not None]
        return raw

    def _score_quality(self, data: Any) -> float:
        if data is None:
            return 0.0
        if isinstance(data, dict):
            filled = sum(1 for v in data.values() if v is not None and v != "")
            return min(1.0, filled / max(len(data), 1))
        if isinstance(data, list):
            return min(1.0, len(data) / 10) if data else 0.0
        if isinstance(data, str):
            return min(1.0, len(data) / 100)
        return 1.0

    def get_stats(self) -> Dict:
        p = self.stats["processed"]
        return {
            "total_processed": p,
            "failed": self.stats["failed"],
            "avg_ms": round(self.stats["total_ms"] / p if p else 0, 2),
        }
