"""
NexusCore — مدير الملفات
رفع، تنزيل، إدارة، وتحقق من الملفات.
"""
import hashlib
import logging
import mimetypes
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.file_manager")


@dataclass
class FileRecord:
    file_id: str
    filename: str
    path: str
    size_bytes: int
    mime_type: str
    checksum: str
    uploaded_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


class FileHandler:
    """يدير الملفات بأمان مع التحقق من السلامة"""

    ALLOWED_TYPES = {
        "text/plain", "application/json", "text/csv",
        "image/png", "image/jpeg", "image/gif",
        "application/pdf", "text/markdown",
    }
    MAX_SIZE_MB = 50

    def __init__(self, storage_dir: str = "nexus_data/files"):
        self.storage = Path(storage_dir)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.records: Dict[str, FileRecord] = {}
        logger.info(f"📁 FileHandler initialized at {self.storage}")

    def save_file(self, filename: str, content: bytes,
                  metadata: Optional[Dict] = None,
                  skip_type_check: bool = False) -> Optional[FileRecord]:
        import uuid
        # فحص الحجم
        size_mb = len(content) / 1024 / 1024
        if size_mb > self.MAX_SIZE_MB:
            logger.error(f"File too large: {size_mb:.1f}MB > {self.MAX_SIZE_MB}MB")
            return None
        # فحص نوع الملف
        mime, _ = mimetypes.guess_type(filename)
        mime = mime or "application/octet-stream"
        if not skip_type_check and mime not in self.ALLOWED_TYPES:
            logger.warning(f"File type not allowed: {mime}")
        # حفظ الملف
        file_id = uuid.uuid4().hex[:12]
        safe_name = f"{file_id}_{Path(filename).name}"
        path = self.storage / safe_name
        path.write_bytes(content)
        checksum = hashlib.sha256(content).hexdigest()
        record = FileRecord(
            file_id=file_id, filename=filename,
            path=str(path), size_bytes=len(content),
            mime_type=mime, checksum=checksum,
            metadata=metadata or {}
        )
        self.records[file_id] = record
        logger.info(f"✅ File saved: {filename} ({len(content)} bytes)")
        return record

    def get_file(self, file_id: str) -> Optional[bytes]:
        record = self.records.get(file_id)
        if not record:
            return None
        path = Path(record.path)
        if not path.exists():
            return None
        content = path.read_bytes()
        # تحقق من السلامة
        if hashlib.sha256(content).hexdigest() != record.checksum:
            logger.error(f"Checksum mismatch for {file_id}")
            return None
        return content

    def delete_file(self, file_id: str) -> bool:
        record = self.records.pop(file_id, None)
        if record:
            path = Path(record.path)
            if path.exists():
                path.unlink()
            return True
        return False

    def list_files(self) -> List[Dict]:
        return [
            {"id": r.file_id, "name": r.filename,
             "size_mb": round(r.size_bytes / 1024 / 1024, 3),
             "mime": r.mime_type, "uploaded_at": r.uploaded_at}
            for r in self.records.values()
        ]

    def get_storage_info(self) -> Dict:
        total_bytes = sum(r.size_bytes for r in self.records.values())
        return {
            "total_files": len(self.records),
            "total_size_mb": round(total_bytes / 1024 / 1024, 2),
            "max_size_mb": self.MAX_SIZE_MB,
            "storage_path": str(self.storage),
        }
