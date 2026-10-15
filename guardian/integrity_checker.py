"""
Guardian — فاحص سلامة كود السيد
يراقب الملفات المحمية ويكتشف أي تعديل غير مصرح.
يعمل بشكل دوري ويرفع تنبيهاً فورياً عند أي تغيير.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

# R-611: تثبيت المسارات على جذر المستودع — تعمل من أي دليل عمل
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
def _repo_path(rel: str):
    return str(_os.path.join(_REPO_ROOT, rel))


logger = logging.getLogger("guardian.integrity")

INTEGRITY_DB   = Path(_repo_path("guardian/data/integrity_baseline.json"))
INTEGRITY_LOG  = Path(_repo_path("guardian/data/integrity_events.jsonl"))

# الملفات والمجلدات المحمية (لا يجوز تعديلها دون إذن السيد)
PROTECTED_PATHS = [
    "backend/app.py",
    "backend/api.py",
    "backend/orchestrator.py",
    "backend/safety.py",
    "backend/config.py",
    "frontend/",
    "main.py",
    "start.sh",
]


@dataclass
class FileSnapshot:
    path: str
    checksum: str
    size_bytes: int
    last_modified: float
    snapshot_time: float = field(default_factory=time.time)


@dataclass
class IntegrityViolation:
    violation_id: str
    path: str
    violation_type: str   # modified / deleted / new_file
    old_checksum: Optional[str]
    new_checksum: Optional[str]
    detected_at: float = field(default_factory=time.time)
    severity: str = "critical"


class IntegrityChecker:
    """
    فاحص سلامة كود السيد
    ═════════════════════
    • يأخذ baseline snapshot من الملفات المحمية
    • يفحص بشكل دوري عند الاستدعاء
    • يرفع تنبيهاً فورياً عند أي تغيير
    • لا يُصلح التغييرات — يُبلّغ فقط
    """

    def __init__(self, extra_paths: Optional[List[str]] = None,
                 alert_callback: Optional[Callable] = None):
        self.protected_paths: List[str] = PROTECTED_PATHS + (extra_paths or [])
        self._baseline: Dict[str, FileSnapshot] = {}
        self.violations: List[IntegrityViolation] = []
        self._alert_callback = alert_callback
        self._check_count = 0

        INTEGRITY_DB.parent.mkdir(parents=True, exist_ok=True)
        self._load_baseline()
        logger.info(
            f"🔍 IntegrityChecker initialized "
            f"({len(self.protected_paths)} protected paths)"
        )

    # ══════════════════════════════════════════════════════════════════
    # Baseline
    # ══════════════════════════════════════════════════════════════════
    def build_baseline(self) -> Dict[str, FileSnapshot]:
        """يبني baseline جديداً من الملفات الحالية"""
        snapshots: Dict[str, FileSnapshot] = {}
        for path_str in self.protected_paths:
            path = Path(path_str)
            if path.is_file():
                snap = self._snapshot_file(path)
                if snap:
                    snapshots[path_str] = snap
            elif path.is_dir():
                for f in path.rglob("*"):
                    if f.is_file():
                        snap = self._snapshot_file(f)
                        if snap:
                            snapshots[str(f)] = snap
        self._baseline = snapshots
        self._save_baseline()
        logger.info(f"📸 Baseline built: {len(snapshots)} files")
        return snapshots

    def _snapshot_file(self, path: Path) -> Optional[FileSnapshot]:
        try:
            content = path.read_bytes()
            stat    = path.stat()
            return FileSnapshot(
                path=str(path),
                checksum=hashlib.sha256(content).hexdigest(),
                size_bytes=stat.st_size,
                last_modified=stat.st_mtime,
            )
        except Exception as exc:
            logger.exception(
                f"R-682 [SECURITY]: Snapshot error [{path}] — file skipped from "
                f"integrity baseline. This may hide a real integrity problem. "
                f"exc={exc}"
            )
            return None

    # ══════════════════════════════════════════════════════════════════
    # الفحص الدوري
    # ══════════════════════════════════════════════════════════════════
    def check(self) -> List[IntegrityViolation]:
        """يفحص سلامة الملفات المحمية ويُعيد قائمة الانتهاكات"""
        self._check_count += 1
        violations: List[IntegrityViolation] = []
        import uuid

        if not self._baseline:
            logger.warning("No baseline found — building now")
            self.build_baseline()
            return []

        # فحص الملفات الموجودة في الـ baseline
        for path_str, old_snap in self._baseline.items():
            path = Path(path_str)
            if not path.exists():
                v = IntegrityViolation(
                    violation_id=uuid.uuid4().hex[:8],
                    path=path_str,
                    violation_type="deleted",
                    old_checksum=old_snap.checksum,
                    new_checksum=None,
                )
                violations.append(v)
                continue

            new_snap = self._snapshot_file(path)
            if new_snap and new_snap.checksum != old_snap.checksum:
                v = IntegrityViolation(
                    violation_id=uuid.uuid4().hex[:8],
                    path=path_str,
                    violation_type="modified",
                    old_checksum=old_snap.checksum,
                    new_checksum=new_snap.checksum,
                )
                violations.append(v)

        # فحص ملفات جديدة في المجلدات المحمية
        for path_str in self.protected_paths:
            p = Path(path_str)
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file() and str(f) not in self._baseline:
                        v = IntegrityViolation(
                            violation_id=uuid.uuid4().hex[:8],
                            path=str(f),
                            violation_type="new_file",
                            old_checksum=None,
                            new_checksum=self._snapshot_file(f).checksum
                            if self._snapshot_file(f) else None,
                        )
                        violations.append(v)

        if violations:
            self.violations.extend(violations)
            self._log_violations(violations)
            self._alert(violations)

        logger.info(
            f"✅ Integrity check #{self._check_count}: "
            f"{len(violations)} violation(s) found"
        )
        return violations

    def _alert(self, violations: List[IntegrityViolation]) -> None:
        for v in violations:
            logger.critical(
                f"🚨 INTEGRITY VIOLATION [{v.violation_type.upper()}]: "
                f"{v.path} — checksum changed"
            )
        if self._alert_callback:
            try:
                self._alert_callback(violations)
            except Exception as exc:
                logger.error(f"Alert callback error: {exc}")

    # ══════════════════════════════════════════════════════════════════
    # تثبيت التغييرات المعتمدة
    # ══════════════════════════════════════════════════════════════════
    def approve_changes(self, paths: List[str],
                        master_token: str,
                        master_hash: str) -> Dict:
        """
        يثبّت التغييرات المعتمدة من السيد في الـ baseline الجديد.
        يتطلب رمز السيد.
        """
        if hashlib.sha256(master_token.encode()).hexdigest() != master_hash:
            return {"success": False, "reason": "رمز السيد غير صحيح"}

        updated: List[str] = []
        for path_str in paths:
            path = Path(path_str)
            if path.exists():
                snap = self._snapshot_file(path)
                if snap:
                    self._baseline[path_str] = snap
                    updated.append(path_str)

        self._save_baseline()
        logger.info(f"✅ Baseline updated for {len(updated)} approved paths")
        return {"success": True, "updated_paths": updated}

    # ══════════════════════════════════════════════════════════════════
    # استمرارية الـ Baseline
    # ══════════════════════════════════════════════════════════════════
    def _save_baseline(self) -> None:
        data = {
            path: {
                "checksum": snap.checksum,
                "size_bytes": snap.size_bytes,
                "last_modified": snap.last_modified,
                "snapshot_time": snap.snapshot_time,
            }
            for path, snap in self._baseline.items()
        }
        INTEGRITY_DB.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _load_baseline(self) -> None:
        if not INTEGRITY_DB.exists():
            return
        try:
            data = json.loads(INTEGRITY_DB.read_text(encoding="utf-8"))
            for path, info in data.items():
                self._baseline[path] = FileSnapshot(
                    path=path,
                    checksum=info["checksum"],
                    size_bytes=info["size_bytes"],
                    last_modified=info["last_modified"],
                    snapshot_time=info.get("snapshot_time", 0),
                )
            logger.info(f"📂 Baseline loaded: {len(self._baseline)} files")
        except Exception as exc:
            logger.error(f"Baseline load error: {exc}")

    def _log_violations(self, violations: List[IntegrityViolation]) -> None:
        for v in violations:
            line = json.dumps({
                "violation_id": v.violation_id,
                "path": v.path,
                "type": v.violation_type,
                "old_checksum": v.old_checksum,
                "new_checksum": v.new_checksum,
                "detected_at": v.detected_at,
                "severity": v.severity,
            }, ensure_ascii=False)
            with open(INTEGRITY_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    # ══════════════════════════════════════════════════════════════════
    # التقارير
    # ══════════════════════════════════════════════════════════════════
    def get_summary(self) -> Dict:
        by_type: Dict[str, int] = {}
        for v in self.violations:
            by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
        return {
            "baseline_files": len(self._baseline),
            "total_violations": len(self.violations),
            "by_type": by_type,
            "total_checks": self._check_count,
            "protected_paths": self.protected_paths,
        }

    def get_recent_violations(self, limit: int = 20) -> List[Dict]:
        return [
            {"id": v.violation_id, "path": v.path, "type": v.violation_type,
             "severity": v.severity, "detected_at": v.detected_at}
            for v in self.violations[-limit:]
        ]
