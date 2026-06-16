"""
NexusCore — نظام التدقيق الأمني
بديل شامل لـ guardian/ و prevention/ — دفاعي بحت.
"""
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.security.audit")


@dataclass
class SecurityFinding:
    finding_id: str
    severity: str       # info / low / medium / high / critical
    category: str
    description: str
    affected: str
    remediation: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False


class SecurityAudit:
    """تدقيق أمني شامل — يكتشف، يسجل، يوصي. لا يتصرف بشكل مستقل."""

    def __init__(self, audit_dir: str = "nexus_data/security"):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.findings: List[SecurityFinding] = []
        self._checks: List[Dict] = []
        self._register_default_checks()
        logger.info("🔐 SecurityAudit initialized")

    def _register_default_checks(self) -> None:
        self._checks = [
            {
                "id": "weak_secret",
                "name": "مفتاح سري ضعيف",
                "fn": self._check_weak_secret,
                "severity": "high",
            },
            {
                "id": "world_writable",
                "name": "ملف قابل للكتابة من الجميع",
                "fn": self._check_world_writable,
                "severity": "medium",
            },
            {
                "id": "large_log",
                "name": "ملف سجل ضخم",
                "fn": self._check_large_logs,
                "severity": "low",
            },
        ]

    def run_full_audit(self, target_dirs: Optional[List[str]] = None) -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []
        dirs = target_dirs or ["."]
        for check in self._checks:
            try:
                result = check["fn"](dirs)
                if result:
                    for r in result:
                        f = SecurityFinding(
                            finding_id=hashlib.md5(
                                f"{check['id']}{r}".encode()
                            ).hexdigest()[:8],
                            severity=check["severity"],
                            category=check["id"],
                            description=f"{check['name']}: {r}",
                            affected=r,
                            remediation=self._get_remediation(check["id"]),
                        )
                        findings.append(f)
            except Exception as exc:
                logger.warning(f"Check {check['id']} failed: {exc}")
        self.findings.extend(findings)
        self._save_report(findings)
        logger.info(f"🔐 Audit complete: {len(findings)} findings")
        return findings

    def _check_weak_secret(self, dirs: List[str]) -> List[str]:
        weak = []
        for d in dirs:
            for p in Path(d).rglob("*.env"):
                try:
                    content = p.read_text(errors="ignore")
                    for line in content.splitlines():
                        if "SECRET" in line.upper() and ("123" in line or "password" in line.lower()):
                            weak.append(str(p))
                except Exception:
                    pass
        return weak

    def _check_world_writable(self, dirs: List[str]) -> List[str]:
        writable = []
        for d in dirs:
            for p in Path(d).rglob("*"):
                try:
                    if p.is_file() and (p.stat().st_mode & 0o002):
                        writable.append(str(p))
                except Exception:
                    pass
        return writable[:10]

    def _check_large_logs(self, dirs: List[str]) -> List[str]:
        large = []
        for d in dirs:
            for p in Path(d).rglob("*.log"):
                try:
                    if p.stat().st_size > 100 * 1024 * 1024:  # 100MB
                        large.append(str(p))
                except Exception:
                    pass
        return large

    def _get_remediation(self, check_id: str) -> str:
        remed = {
            "weak_secret": "استخدم مولد مفاتيح قوي (32+ حرف عشوائي)",
            "world_writable": "غير صلاحيات الملف: chmod 640 <file>",
            "large_log": "فعّل log rotation لإدارة أحجام السجلات",
        }
        return remed.get(check_id, "راجع التوثيق الأمني")

    def _save_report(self, findings: List[SecurityFinding]) -> None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        report_file = self.audit_dir / f"audit_{ts}.json"
        report_file.write_text(json.dumps(
            [{"id": f.finding_id, "severity": f.severity, "description": f.description,
              "affected": f.affected, "remediation": f.remediation}
             for f in findings],
            ensure_ascii=False, indent=2
        ), encoding="utf-8")

    def get_summary(self) -> Dict:
        by_severity: Dict[str, int] = {}
        for f in self.findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        return {"total": len(self.findings), "by_severity": by_severity,
                "open": sum(1 for f in self.findings if not f.resolved)}
