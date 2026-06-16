"""
NexusCore — مصدّر البيانات
يصدّر البيانات إلى CSV / JSON / Markdown.
"""
import csv
import io
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.visualization.exporter")


class DataExporter:
    """يصدّر البيانات بتنسيقات متعددة"""

    def __init__(self, output_dir: str = "nexus_data/exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._exports: List[Dict] = []
        logger.info(f"📤 DataExporter initialized at {self.output_dir}")

    def to_csv_string(self, records: List[Dict]) -> str:
        if not records:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
        return output.getvalue()

    def to_json_string(self, data: Any, indent: int = 2) -> str:
        return json.dumps(data, ensure_ascii=False, indent=indent, default=str)

    def save_csv(self, records: List[Dict], filename: Optional[str] = None) -> Path:
        ts   = time.strftime("%Y%m%d_%H%M%S")
        name = filename or f"export_{ts}.csv"
        path = self.output_dir / name
        path.write_text(self.to_csv_string(records), encoding="utf-8")
        self._log_export(name, "csv", len(records))
        logger.info(f"📤 CSV exported: {path}")
        return path

    def save_json(self, data: Any, filename: Optional[str] = None) -> Path:
        ts   = time.strftime("%Y%m%d_%H%M%S")
        name = filename or f"export_{ts}.json"
        path = self.output_dir / name
        path.write_text(self.to_json_string(data), encoding="utf-8")
        self._log_export(name, "json", 1)
        logger.info(f"📤 JSON exported: {path}")
        return path

    def save_markdown_table(self, records: List[Dict],
                            title: str = "Data Export",
                            filename: Optional[str] = None) -> Path:
        ts   = time.strftime("%Y%m%d_%H%M%S")
        name = filename or f"export_{ts}.md"
        path = self.output_dir / name
        if not records:
            path.write_text("# Empty Export\n", encoding="utf-8")
            return path
        headers = list(records[0].keys())
        sep     = "| " + " | ".join(["---"] * len(headers)) + " |"
        rows    = [
            "| " + " | ".join(str(r.get(h, "")) for h in headers) + " |"
            for r in records
        ]
        md = f"# {title}\n\n"
        md += "| " + " | ".join(headers) + " |\n"
        md += sep + "\n"
        md += "\n".join(rows) + "\n"
        path.write_text(md, encoding="utf-8")
        self._log_export(name, "markdown", len(records))
        return path

    def _log_export(self, name: str, fmt: str, count: int) -> None:
        self._exports.append({"name": name, "format": fmt,
                               "count": count, "ts": time.time()})

    def list_exports(self) -> List[Dict]:
        return self._exports[-50:]
