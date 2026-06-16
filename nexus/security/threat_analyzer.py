"""
NexusCore — محلل التهديدات (دفاعي فقط)
يحلل الأحداث ويصنف التهديدات دون اتخاذ إجراءات مستقلة.
"""
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.security.threat")


@dataclass
class ThreatEvent:
    event_id: str
    source_ip: Optional[str]
    event_type: str
    severity: str        # low / medium / high / critical
    description: str
    raw_data: Dict
    timestamp: float = field(default_factory=time.time)
    mitigated: bool = False


class ThreatAnalyzer:
    """محلل تهديدات دفاعي — يكتشف ويُبلّغ، لا يتصرف"""

    SIGNATURES = [
        {"name": "sql_injection",   "pattern": r"(union|select|insert|drop)\s+",
         "severity": "high"},
        {"name": "path_traversal",  "pattern": r"\.\./",
         "severity": "medium"},
        {"name": "xss_attempt",     "pattern": r"<script[^>]*>",
         "severity": "high"},
        {"name": "brute_force",     "pattern": r"failed.{0,30}(login|auth|password)",
         "severity": "medium"},
        {"name": "cmd_injection",   "pattern": r"[;&|`]\s*(ls|cat|rm|wget|curl)\b",
         "severity": "critical"},
    ]

    def __init__(self, alert_threshold: int = 5):
        self.events: List[ThreatEvent] = []
        self.alert_threshold = alert_threshold
        self._ip_counts: Dict[str, int] = defaultdict(int)
        logger.info("🛡️ ThreatAnalyzer initialized (defensive only)")

    def analyze_text(self, text: str, source_ip: Optional[str] = None,
                     context: Optional[Dict] = None) -> List[ThreatEvent]:
        import uuid
        detected: List[ThreatEvent] = []
        for sig in self.SIGNATURES:
            if re.search(sig["pattern"], text, re.IGNORECASE):
                event = ThreatEvent(
                    event_id=uuid.uuid4().hex[:8],
                    source_ip=source_ip,
                    event_type=sig["name"],
                    severity=sig["severity"],
                    description=f"Signature match: {sig['name']}",
                    raw_data={"text_snippet": text[:200], "context": context or {}},
                )
                detected.append(event)
                logger.warning(f"🚨 Threat detected: {sig['name']} from {source_ip}")
        self.events.extend(detected)
        if source_ip:
            self._ip_counts[source_ip] += len(detected)
        return detected

    def analyze_http_request(self, method: str, path: str,
                             headers: Dict, body: str = "",
                             source_ip: Optional[str] = None) -> List[ThreatEvent]:
        combined = f"{method} {path} {json.dumps(headers)} {body}"
        return self.analyze_text(combined, source_ip,
                                 {"method": method, "path": path})

    def get_high_risk_ips(self, min_events: int = 3) -> List[Dict]:
        return [
            {"ip": ip, "event_count": cnt}
            for ip, cnt in self._ip_counts.items()
            if cnt >= min_events
        ]

    def get_recent_threats(self, limit: int = 50,
                           min_severity: str = "low") -> List[Dict]:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_lvl = order.get(min_severity, 0)
        filtered = [
            e for e in self.events
            if order.get(e.severity, 0) >= min_lvl
        ]
        return [
            {"id": e.event_id, "type": e.event_type,
             "severity": e.severity, "ip": e.source_ip,
             "description": e.description, "ts": e.timestamp,
             "mitigated": e.mitigated}
            for e in filtered[-limit:]
        ]

    def get_stats(self) -> Dict:
        by_sev: Dict[str, int] = {}
        for e in self.events:
            by_sev[e.severity] = by_sev.get(e.severity, 0) + 1
        return {"total_events": len(self.events), "by_severity": by_sev,
                "unique_ips": len(self._ip_counts)}


import json  # noqa
