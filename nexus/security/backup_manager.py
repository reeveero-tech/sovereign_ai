"""
NexusCore — مدير النسخ الاحتياطية
ينشئ ويدير نسخاً احتياطية آمنة من البيانات والكود.
"""
import hashlib
import json
import logging
import shutil
import tarfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.security.backup")


@dataclass
class BackupRecord:
    backup_id: str
    source_path: str
    backup_path: str
    size_bytes: int
    checksum: str
    timestamp: float = field(default_factory=time.time)
    verified: bool = False
    label: str = ""


class BackupManager:
    """إدارة نسخ احتياطية مع التحقق من السلامة"""

    def __init__(self, backup_dir: str = "nexus_data/backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.records: List[BackupRecord] = []
        logger.info(f"💾 BackupManager initialized at {self.backup_dir}")

    def backup_file(self, source: str, label: str = "") -> Optional[BackupRecord]:
        src = Path(source)
        if not src.exists():
            logger.error(f"Source not found: {source}")
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{src.stem}_{ts}{src.suffix}"
        dest = self.backup_dir / backup_name
        shutil.copy2(src, dest)
        checksum = self._checksum(dest)
        size = dest.stat().st_size
        import uuid
        record = BackupRecord(
            backup_id=uuid.uuid4().hex[:8],
            source_path=str(src),
            backup_path=str(dest),
            size_bytes=size,
            checksum=checksum,
            label=label or src.name,
        )
        self.records.append(record)
        logger.info(f"✅ Backed up: {src} → {dest} ({size} bytes)")
        return record

    def backup_directory(self, source: str, label: str = "") -> Optional[BackupRecord]:
        src = Path(source)
        if not src.is_dir():
            logger.error(f"Directory not found: {source}")
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        archive_name = f"{src.name}_{ts}.tar.gz"
        dest = self.backup_dir / archive_name
        with tarfile.open(dest, "w:gz") as tar:
            tar.add(src, arcname=src.name)
        checksum = self._checksum(dest)
        size = dest.stat().st_size
        import uuid
        record = BackupRecord(
            backup_id=uuid.uuid4().hex[:8],
            source_path=str(src),
            backup_path=str(dest),
            size_bytes=size,
            checksum=checksum,
            label=label or src.name,
        )
        self.records.append(record)
        logger.info(f"✅ Directory archived: {dest} ({size} bytes)")
        return record

    def verify(self, record: BackupRecord) -> bool:
        path = Path(record.backup_path)
        if not path.exists():
            record.verified = False
            return False
        current = self._checksum(path)
        record.verified = current == record.checksum
        if not record.verified:
            logger.error(f"❌ Checksum mismatch for {record.backup_path}")
        return record.verified

    def restore(self, record: BackupRecord, dest: str) -> bool:
        if not self.verify(record):
            logger.error("Cannot restore: backup verification failed")
            return False
        dest_path = Path(dest)
        src_path  = Path(record.backup_path)
        if src_path.suffix == ".gz":
            dest_path.mkdir(parents=True, exist_ok=True)
            with tarfile.open(src_path, "r:gz") as tar:
                tar.extractall(dest_path)
        else:
            shutil.copy2(src_path, dest_path)
        logger.info(f"✅ Restored {src_path} → {dest_path}")
        return True

    def cleanup_old(self, keep_last: int = 10) -> int:
        if len(self.records) <= keep_last:
            return 0
        to_delete = self.records[:-keep_last]
        count = 0
        for rec in to_delete:
            p = Path(rec.backup_path)
            if p.exists():
                p.unlink()
                count += 1
        self.records = self.records[-keep_last:]
        return count

    @staticmethod
    def _checksum(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def list_backups(self) -> List[Dict]:
        return [
            {"id": r.backup_id, "label": r.label,
             "source": r.source_path, "size_mb": round(r.size_bytes / 1024 / 1024, 2),
             "ts": r.timestamp, "verified": r.verified}
            for r in self.records
        ]
