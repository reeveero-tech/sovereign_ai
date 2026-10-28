"""R-800: تخزين بايتات الملفات + فهرس بياناتها الوصفية.

- SupabaseStorage: Supabase Storage (حاوية خاصة «sovereign-files») — دائم عبر إعادة النشر.
- LocalStorage: مجلد محلي (اختبارات/تشغيل محلي) — يُعلن durable=false في الإنتاج بلا Supabase.
- الفهرس: جدول disk (KV) بالفضاء «ws_files» عبر SupabaseDisk، أو ذاكرة+ملف JSON محليًا.
لا حذف نهائي: الأرشفة علامة فقط (archived=true) — البايتات تبقى.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

BUCKET = "sovereign-files"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def new_id(prefix: str = "F") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class LocalStorage:
    durable = False
    backend = "local"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return True

    def get(self, key: str) -> Optional[bytes]:
        p = self.root / key
        return p.read_bytes() if p.is_file() else None


class SupabaseStorage:
    durable = True
    backend = "supabase"

    def __init__(self, base_url: str, service_key: str, bucket: str = BUCKET,
                 transport: Optional[httpx.BaseTransport] = None, timeout: float = 60.0) -> None:
        self.bucket = bucket
        self._client = httpx.Client(base_url=base_url.rstrip("/") + "/storage/v1", timeout=timeout,
                                    transport=transport,
                                    headers={"apikey": service_key,
                                             "Authorization": f"Bearer {service_key}"})
        self._ready = False
        self.last_error: Optional[str] = None

    def ensure_bucket(self) -> bool:
        if self._ready:
            return True
        r = self._client.get(f"/bucket/{self.bucket}")
        if r.status_code == 200:
            self._ready = True
            return True
        r = self._client.post("/bucket", json={"id": self.bucket, "name": self.bucket,
                                                "public": False})
        self._ready = r.status_code in (200, 201) or "already exists" in r.text.lower()
        if not self._ready:
            self.last_error = f"bucket HTTP {r.status_code}: {r.text[:160]}"
        return self._ready

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        if not self.ensure_bucket():
            return False
        r = self._client.post(f"/object/{self.bucket}/{key}", content=data,
                              headers={"Content-Type": content_type or "application/octet-stream",
                                       "x-upsert": "true"})
        if r.status_code not in (200, 201):
            self.last_error = f"put HTTP {r.status_code}: {r.text[:160]}"
            return False
        return True

    def get(self, key: str) -> Optional[bytes]:
        r = self._client.get(f"/object/{self.bucket}/{key}")
        if r.status_code != 200:
            self.last_error = f"get HTTP {r.status_code}"
            return None
        return r.content


class Index:
    """فهرس سجلات (ملفات/محادثات/مشاريع) بفضاء أسماء في KV — ذاكرة + دوام."""

    def __init__(self, namespace: str, disk: Any = None, local_path: Optional[Path] = None) -> None:
        self.namespace = namespace
        self._disk = disk
        self._local = Path(local_path) if local_path else None
        self._rows: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._hydrated = False
        self.persist_errors = 0

    @property
    def durable(self) -> bool:
        return bool(self._disk)

    def _hydrate(self) -> None:
        if self._hydrated:
            return
        self._hydrated = True
        if self._disk:
            offset = 0
            while True:
                rows = self._disk.list_blobs(self.namespace, limit=1000, offset=offset)
                if not rows:
                    break
                for r in rows:
                    if isinstance(r.get("payload"), dict):
                        self._rows[r["key"]] = r["payload"]
                if len(rows) < 1000:
                    break
                offset += 1000
        elif self._local and self._local.is_file():
            self._rows = json.loads(self._local.read_text(encoding="utf-8"))

    def put(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        rec = json.loads(json.dumps(rec, ensure_ascii=False, default=str))
        rec["updated_at"] = time.time()
        with self._lock:
            self._hydrate()
            self._rows[rec["id"]] = rec
            if self._disk:
                if not self._disk.save_blob(self.namespace, rec["id"], rec):
                    self.persist_errors += 1
            elif self._local:
                self._local.parent.mkdir(parents=True, exist_ok=True)
                self._local.write_text(json.dumps(self._rows, ensure_ascii=False), encoding="utf-8")
        return rec

    def get(self, rid: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._hydrate()
            r = self._rows.get(rid)
            return json.loads(json.dumps(r)) if r else None

    def all(self) -> List[Dict[str, Any]]:
        with self._lock:
            self._hydrate()
            rows = [json.loads(json.dumps(r)) for r in self._rows.values()]
        rows.sort(key=lambda r: r.get("updated_at") or 0, reverse=True)
        return rows


def default_backends(data_root: Path):
    """(storage, disk) الحقيقيان: Supabase إن ضُبط، وإلا محلي معلن."""
    try:
        from sovereign.cloud_disk import get_cloud_disk, _supabase_env
        disk = get_cloud_disk()
        url, key = _supabase_env("SUPABASE_URL"), _supabase_env("SUPABASE_SECRET_KEY")
    except Exception:  # TOLERATED: بلا وحدة القرص — تخزين محلي معلن durable=false
        disk, url, key = None, None, None
    if disk is not None and url and key:
        return SupabaseStorage(url, key), disk
    return LocalStorage(Path(data_root) / "workspace_files"), None
