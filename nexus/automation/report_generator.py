"""
NexusCore — مولد التقارير
يولد تقارير نصية وJSON منظمة من البيانات.
"""
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.automation.report")


@dataclass
class Report:
    title: str
    sections: List[Dict]
    metadata: Dict
    generated_at: float = field(default_factory=time.time)
    format: str = "json"


class ReportGenerator:
    """يولد تقارير منظمة من أي مصدر بيانات"""

    def __init__(self, output_dir: str = "nexus_data/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generated: List[Report] = []
        logger.info(f"📄 ReportGenerator initialized at {self.output_dir}")

    def create_report(self, title: str, sections: List[Dict],
                      metadata: Optional[Dict] = None) -> Report:
        report = Report(
            title=title,
            sections=sections,
            metadata=metadata or {"generated_by": "NexusCore"},
        )
        self.generated.append(report)
        return report

    def from_dict(self, title: str, data: Dict) -> Report:
        sections = [
            {"heading": key, "content": value}
            for key, value in data.items()
        ]
        return self.create_report(title, sections)

    def save_json(self, report: Report, filename: Optional[str] = None) -> Path:
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_title = report.title.replace(" ", "_")[:40]
        name = filename or f"{safe_title}_{ts}.json"
        path = self.output_dir / name
        payload = {
            "title": report.title,
            "generated_at": report.generated_at,
            "metadata": report.metadata,
            "sections": report.sections,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        logger.info(f"📄 Report saved: {path}")
        return path

    def save_markdown(self, report: Report, filename: Optional[str] = None) -> Path:
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_title = report.title.replace(" ", "_")[:40]
        name = filename or f"{safe_title}_{ts}.md"
        path = self.output_dir / name
        lines = [f"# {report.title}", "",
                 f"*Generated: {time.ctime(report.generated_at)}*", ""]
        for sec in report.sections:
            lines.append(f"## {sec.get('heading', 'Section')}")
            content = sec.get("content", "")
            if isinstance(content, (dict, list)):
                lines.append("```json")
                lines.append(json.dumps(content, ensure_ascii=False, indent=2))
                lines.append("```")
            else:
                lines.append(str(content))
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"📄 Markdown report saved: {path}")
        return path

    def list_reports(self) -> List[Dict]:
        return [
            {"title": r.title, "sections": len(r.sections), "ts": r.generated_at}
            for r in self.generated[-50:]
        ]
