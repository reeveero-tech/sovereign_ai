"""
NexusCore — جامع البيانات
يجمع البيانات من APIs / ملفات / مصادر يدوية.
"""
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.data_pipeline.collector")


class SourceType(Enum):
    REST_API = "rest_api"
    FILE     = "file"
    MANUAL   = "manual"
    STREAM   = "stream"


@dataclass
class DataSource:
    name: str
    source_type: SourceType
    config: Dict[str, Any]
    enabled: bool = True
    last_collected: Optional[float] = None
    records_collected: int = 0


@dataclass
class CollectedRecord:
    source: str
    timestamp: float
    data: Any
    metadata: Dict = field(default_factory=dict)


class DataCollector:
    """جامع البيانات من مصادر متعددة"""

    def __init__(self):
        self.sources: Dict[str, DataSource] = {}
        self.buffer: List[CollectedRecord] = []
        self.max_buffer = 10_000
        logger.info("📥 DataCollector initialized")

    def add_source(self, name: str, source_type: SourceType, config: Dict) -> None:
        self.sources[name] = DataSource(name=name, source_type=source_type, config=config)

    def remove_source(self, name: str) -> bool:
        return bool(self.sources.pop(name, None))

    async def collect_from_source(self, source_name: str) -> List[CollectedRecord]:
        source = self.sources.get(source_name)
        if not source or not source.enabled:
            return []
        handlers = {
            SourceType.FILE:     self._collect_file,
            SourceType.REST_API: self._collect_api,
            SourceType.MANUAL:   self._collect_manual,
        }
        records = await handlers.get(source.source_type, self._collect_manual)(source)
        source.last_collected = time.time()
        source.records_collected += len(records)
        self._add_to_buffer(records)
        return records

    async def _collect_file(self, source: DataSource) -> List[CollectedRecord]:
        import pathlib
        path = source.config.get("path", "")
        try:
            content = pathlib.Path(path).read_text(encoding="utf-8")
            data = json.loads(content) if path.endswith(".json") else content
            return [CollectedRecord(source=source.name, timestamp=time.time(),
                                    data=data, metadata={"path": path})]
        except Exception as exc:
            logger.warning(f"File collect error [{source.name}]: {exc}")
            return []

    async def _collect_api(self, source: DataSource) -> List[CollectedRecord]:
        try:
            import httpx
            url = source.config.get("url", "")
            headers = source.config.get("headers", {})
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return [CollectedRecord(source=source.name, timestamp=time.time(),
                                        data=resp.json(),
                                        metadata={"url": url, "status": resp.status_code})]
        except Exception as exc:
            logger.warning(f"API collect error [{source.name}]: {exc}")
            return []

    async def _collect_manual(self, source: DataSource) -> List[CollectedRecord]:
        data = source.config.get("data", {})
        return [CollectedRecord(source=source.name, timestamp=time.time(), data=data)]

    def ingest(self, source: str, data: Any, metadata: Optional[Dict] = None) -> CollectedRecord:
        record = CollectedRecord(source=source, timestamp=time.time(),
                                  data=data, metadata=metadata or {})
        self._add_to_buffer([record])
        return record

    def _add_to_buffer(self, records: List[CollectedRecord]) -> None:
        self.buffer.extend(records)
        if len(self.buffer) > self.max_buffer:
            self.buffer = self.buffer[-self.max_buffer:]

    def flush(self) -> List[CollectedRecord]:
        records, self.buffer = self.buffer[:], []
        return records

    def get_stats(self) -> Dict:
        return {
            "sources": len(self.sources),
            "buffer_size": len(self.buffer),
            "sources_detail": {
                n: {"records": s.records_collected, "enabled": s.enabled}
                for n, s in self.sources.items()
            },
        }
