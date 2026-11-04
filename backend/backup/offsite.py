# -*- coding: utf-8 -*-
"""R-847: وجهات خارج الخادم — نسخة على الحجم نفسه لا تنجو من فقدانه.

القواعد:
- **مشفر فقط**: لا يغادر الخادم أرشيف صريح أبدًا. ``push`` يرفض النسخة غير
  المشفرة قبل أي اتصال.
- **تساوي القوة**: اسم الكائن ``<prefix>/<id>.svbk``. الرفع بلا ``upsert``،
  والكائن الموجود يعني ``exists`` لا خطأ.
- **401/403 بلا إعادة عمياء**: محاولة واحدة ثم ``auth`` وإشعار. الأعطال العابرة
  (5xx/429/الشبكة) تُعاد حتى ``MAX_ATTEMPTS`` بتراجع ثابت. وأي خطأ آخر نهائي.

الوجهات:
- ``DirDestination``: مجلد مرآة (حجم ثانٍ مركّب أو قرص شبكي).
- ``SupabaseStorage``: ``/storage/v1/object/<bucket>/<name>``. النقل محقون كما في
  قنوات الإشعارات، والمفتاح لا يُسجل ولا يظهر في الأخطاء.
"""
from __future__ import annotations

import abc
import http.client
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote, urlsplit

MAX_ATTEMPTS = 3
_BACKOFF = (2.0, 8.0)


class OffsiteError(Exception):
    """``kind`` ∈ auth | transient | permanent | config."""

    def __init__(self, kind: str, detail: str = ""):
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind, self.detail = kind, detail


class Destination(abc.ABC):
    name = "abstract"

    @abc.abstractmethod
    def put(self, obj: str, path: Path) -> str:
        """يرفع الملف. يعيد ``uploaded`` أو ``exists``، أو يرفع ``OffsiteError``."""

    @abc.abstractmethod
    def list(self) -> List[Dict[str, Any]]:
        """``[{name, size}]`` للكائنات تحت البادئة."""

    @abc.abstractmethod
    def get(self, obj: str, dest: Path) -> None:
        """ينزّل الكائن إلى ``dest``."""


def object_name(bid: str) -> str:
    return f"{bid}.svbk"


# ===================================================================== مجلد
class DirDestination(Destination):
    name = "dir"

    def __init__(self, root: Path):
        self.root = Path(root)

    def put(self, obj: str, path: Path) -> str:
        dest = self.root / obj
        if dest.exists():
            return "exists"
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.root / f".{obj}.part"
        shutil.copyfile(path, tmp)
        with open(tmp, "rb") as fh:
            os.fsync(fh.fileno())
        os.replace(tmp, dest)
        return "uploaded"

    def list(self) -> List[Dict[str, Any]]:
        if not self.root.is_dir():
            return []
        return [{"name": p.name, "size": p.stat().st_size}
                for p in sorted(self.root.glob("bk-*.svbk"))]

    def get(self, obj: str, dest: Path) -> None:
        src = self.root / obj
        if not src.exists():
            raise OffsiteError("permanent", "not_found")
        shutil.copyfile(src, dest)


# ===================================================================== Supabase
Transport = Callable[[str, str, Dict[str, str], Any], Tuple[int, bytes]]


def _http_transport(method: str, url: str, headers: Dict[str, str], body: Any
                    ) -> Tuple[int, bytes]:
    u = urlsplit(url)
    conn = http.client.HTTPSConnection(u.netloc, timeout=120)
    try:
        path = u.path + (f"?{u.query}" if u.query else "")
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def classify(status: int, body: bytes) -> Optional[str]:
    """None ⇒ نجاح. وإلا نوع الخطأ (وexists للكائن الموجود)."""
    if 200 <= status < 300:
        return None
    text = body[:400].decode("utf-8", "replace").lower()
    if status == 409 or (status == 400 and ("duplicate" in text or "already exists" in text)):
        return "exists"
    if status in (401, 403):
        return "auth"
    if status == 429 or status >= 500:
        return "transient"
    return "permanent"


class SupabaseStorage(Destination):
    name = "supabase"

    def __init__(self, url: str, key: str, bucket: str, prefix: str = "sovereign",
                 transport: Optional[Transport] = None):
        if not url.startswith("https://"):
            raise OffsiteError("config", "url must be https")
        self.url, self._key, self.bucket = url.rstrip("/"), key, bucket
        self.prefix = prefix.strip("/")
        self.transport = transport or _http_transport

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Authorization": f"Bearer {self._key}", "apikey": self._key}
        h.update(extra or {})
        return h

    def _obj_url(self, obj: str) -> str:
        return (f"{self.url}/storage/v1/object/{quote(self.bucket)}/"
                f"{quote(self.prefix)}/{quote(obj)}")

    def _call(self, method: str, url: str, headers: Dict[str, str], body: Any
              ) -> Tuple[int, bytes]:
        try:
            return self.transport(method, url, headers, body)
        except (OSError, http.client.HTTPException) as exc:
            raise OffsiteError("transient", type(exc).__name__) from exc

    def put(self, obj: str, path: Path) -> str:
        size = path.stat().st_size
        with open(path, "rb") as fh:
            status, body = self._call("POST", self._obj_url(obj), self._headers({
                "Content-Type": "application/octet-stream", "x-upsert": "false",
                "Content-Length": str(size)}), fh)
        kind = classify(status, body)
        if kind is None:
            return "uploaded"
        if kind == "exists":
            return "exists"
        raise OffsiteError(kind, f"HTTP {status}")

    def list(self) -> List[Dict[str, Any]]:
        status, body = self._call(
            "POST", f"{self.url}/storage/v1/object/list/{quote(self.bucket)}",
            self._headers({"Content-Type": "application/json"}),
            json.dumps({"prefix": self.prefix, "limit": 1000}).encode("utf-8"))
        kind = classify(status, body)
        if kind is not None:
            raise OffsiteError("permanent" if kind == "exists" else kind, f"HTTP {status}")
        items = json.loads(body.decode("utf-8") or "[]")
        return [{"name": it.get("name"),
                 "size": int((it.get("metadata") or {}).get("size") or 0)}
                for it in items if str(it.get("name", "")).endswith(".svbk")]

    def get(self, obj: str, dest: Path) -> None:
        status, body = self._call("GET", self._obj_url(obj), self._headers(), None)
        kind = classify(status, body)
        if kind is not None:
            raise OffsiteError("permanent" if kind == "exists" else kind, f"HTTP {status}")
        dest.write_bytes(body)


# ===================================================================== الرفع
def push(dest: Destination, bid: str, path: Path, encrypted: bool,
         sleep: Callable[[float], None] = time.sleep) -> Dict[str, Any]:
    """يرفع نسخة واحدة ويعيد ``{status, attempts, detail}`` (لا يرفع استثناء)."""
    if not encrypted:
        return {"status": "refused", "attempts": 0,
                "detail": "offsite_requires_encryption", "destination": dest.name}
    attempts = 0
    last = ""
    for i in range(MAX_ATTEMPTS):
        attempts = i + 1
        try:
            st = dest.put(object_name(bid), path)
            return {"status": st, "attempts": attempts, "detail": "",
                    "destination": dest.name}
        except OffsiteError as exc:
            last = exc.detail or exc.kind
            if exc.kind != "transient":
                return {"status": exc.kind, "attempts": attempts, "detail": last,
                        "destination": dest.name}
            if attempts < MAX_ATTEMPTS:
                sleep(_BACKOFF[min(i, len(_BACKOFF) - 1)])
    return {"status": "transient", "attempts": attempts, "detail": last,
            "destination": dest.name}
