"""
NexusCore — موصل مصادر البيانات
يتعامل مع مصادر بيانات متنوعة: CSV, JSON, RSS, Webhook.
"""
import csv
import io
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger("nexus.connectors.data")


@dataclass
class DataBatch:
    source: str
    format: str
    records: List[Dict]
    count: int
    fetched_at: float


class DataConnector:
    """موصل بيانات مرن يدعم تنسيقات متعددة"""

    def __init__(self):
        self.stats = {"batches_loaded": 0, "total_records": 0}
        logger.info("🔌 DataConnector initialized")

    def from_json_string(self, source: str, json_str: str) -> DataBatch:
        data = json.loads(json_str)
        records = data if isinstance(data, list) else [data]
        return self._make_batch(source, "json", records)

    def from_csv_string(self, source: str, csv_str: str,
                        delimiter: str = ",") -> DataBatch:
        reader = csv.DictReader(io.StringIO(csv_str), delimiter=delimiter)
        records = [dict(row) for row in reader]
        return self._make_batch(source, "csv", records)

    def from_file(self, source: str, file_path: str) -> DataBatch:
        from pathlib import Path
        p = Path(file_path)
        if not p.exists():
            return self._make_batch(source, "unknown", [])
        content = p.read_text(encoding="utf-8")
        if p.suffix == ".json":
            return self.from_json_string(source, content)
        if p.suffix in (".csv", ".tsv"):
            delim = "\t" if p.suffix == ".tsv" else ","
            return self.from_csv_string(source, content, delim)
        # نص عادي — كل سطر سجل
        records = [{"line": i + 1, "text": line.strip()}
                   for i, line in enumerate(content.splitlines()) if line.strip()]
        return self._make_batch(source, "text", records)

    def from_dict_list(self, source: str, records: List[Dict]) -> DataBatch:
        return self._make_batch(source, "dict", records)

    def _make_batch(self, source: str, fmt: str, records: List[Dict]) -> DataBatch:
        batch = DataBatch(source=source, format=fmt,
                          records=records, count=len(records),
                          fetched_at=time.time())
        self.stats["batches_loaded"] += 1
        self.stats["total_records"] += len(records)
        logger.info(f"📦 Loaded {len(records)} records from {source} ({fmt})")
        return batch

    def stream_records(self, batch: DataBatch,
                       chunk_size: int = 100) -> Generator[List[Dict], None, None]:
        for i in range(0, len(batch.records), chunk_size):
            yield batch.records[i: i + chunk_size]

    def get_stats(self) -> Dict:
        return self.stats
