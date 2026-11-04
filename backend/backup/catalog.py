# -*- coding: utf-8 -*-
"""R-847: فهرس النسخ — ``<id>.svbk`` وبجانبه ``<id>.json``، والقفل، والحالة.

الملف الجانبي يحمل البيانات الوصفية (البصمة والحجم والنوع وبصمة المفتاح وحالة
الرفع)، ولا يحمل المفتاح أبدًا. والقفل ``flock`` غير حاجز على ``.lock``، فنسختان
متزامنتان من خيطين أو عمليتين تنتهيان بواحدة تعمل والأخرى ``busy``.

الاحتفاظ:
- النسخ ``scheduled/manual/fetched`` تُبقي أحدث ``keep``.
- نسخ ``pre_restore`` (شبكة الأمان للتراجع) لها حد مستقل ``PRE_KEEP``، ولا تُحسب
  ضمن ``keep``.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

try:
    from runtime.atomic_json import atomic_write_json
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.runtime.atomic_json import atomic_write_json

from .snapshot import BackupError

ID_RE = re.compile(r"^bk-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}$")
PRE_KEEP = 3
KINDS = ("scheduled", "manual", "pre_restore", "fetched")


def new_id(now: float) -> str:
    return time.strftime("bk-%Y%m%dT%H%M%SZ-", time.gmtime(now)) + secrets.token_hex(3)


def valid_id(bid: str) -> bool:
    return bool(ID_RE.match(bid or ""))


class Catalog:
    def __init__(self, root: Path):
        self.root = Path(root)

    # ------------------------------------------------------------ مسارات
    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / ".work").mkdir(exist_ok=True)

    def archive(self, bid: str) -> Path:
        return self.root / f"{bid}.svbk"

    def sidecar(self, bid: str) -> Path:
        return self.root / f"{bid}.json"

    @property
    def work(self) -> Path:
        return self.root / ".work"

    # ------------------------------------------------------------ القفل
    @contextmanager
    def lock(self) -> Iterator[None]:
        self.ensure()
        fd = os.open(str(self.root / ".lock"), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise BackupError("busy", "نسخة أخرى قيد الإنشاء") from exc
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    # ------------------------------------------------------------ الفهرس
    def put(self, meta: Dict[str, Any]) -> None:
        atomic_write_json(self.sidecar(meta["backup_id"]), meta, ensure_ascii=False,
                          file_mode=0o600)

    def get(self, bid: str) -> Optional[Dict[str, Any]]:
        if not valid_id(bid):
            return None
        p = self.sidecar(bid)
        if not p.exists() or not self.archive(bid).exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def list(self) -> List[Dict[str, Any]]:
        out = []
        if not self.root.is_dir():
            return out
        for p in self.root.glob("bk-*.json"):
            bid = p.stem
            meta = self.get(bid)
            if meta is not None:
                out.append(meta)
        out.sort(key=lambda m: (m.get("created_at", 0), m["backup_id"]), reverse=True)
        return out

    def delete(self, bid: str) -> None:
        for p in (self.archive(bid), self.sidecar(bid)):
            try:
                p.unlink()
            except FileNotFoundError:  # TOLERATED: الحذف متساوي القوة — غائب أصلًا
                pass

    def prune(self, keep: int) -> List[str]:
        removed: List[str] = []
        items = self.list()
        regular = [m for m in items if m.get("kind") != "pre_restore"]
        pre = [m for m in items if m.get("kind") == "pre_restore"]
        for m in regular[max(1, keep):] + pre[PRE_KEEP:]:
            self.delete(m["backup_id"])
            removed.append(m["backup_id"])
        return removed

    # ------------------------------------------------------------ الحالة
    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    def state(self) -> Dict[str, Any]:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):  # TOLERATED: لا حالة بعد (أو تالفة) ⇒ فارغة؛ تُعاد كتابتها عند أول نسخة
            return {}

    def update_state(self, **kv: Any) -> Dict[str, Any]:
        self.ensure()
        st = self.state()
        st.update(kv)
        atomic_write_json(self.state_path, st, ensure_ascii=False, file_mode=0o600)
        return st
