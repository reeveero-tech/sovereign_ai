# -*- coding: utf-8 -*-
"""R-847: الأرشيف — كتابة متدفقة، وتحقق كامل، واستخراج آمن.

البنية: ``tar.gz`` (مشفر اختياريًا بـ``crypto``) أول أعضائه ``MANIFEST.json``
ثم ``data/<rel>`` لكل ملف بترتيب البيان.

التحقق لا يثق بشيء في الأرشيف:
- بصمة الملف كاملًا تطابق المسجلة في الفهرس (إن وُجدت).
- المشفر: وسم كل قطعة (العبث يُكشف قبل أي فك ضغط).
- كل عضو ملف عادي باسم آمن (لا مسار مطلق ولا ``..`` ولا رابط ولا جهاز)،
  ومذكور في البيان، ولا يتكرر، وبصمته وحجمه يطابقانه.
- كل ملف في البيان موجود في الأرشيف.

الاستخراج يجري **أثناء** التحقق إلى مجلد هدف، والعضو المرفوض يوقف كل شيء قبل
كتابته. فالمستدعي يعامل الهدف مسودة تُحذف عند الرفض.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Dict, Optional

from . import crypto
from .snapshot import sha256_file

FORMAT = "sovereign-backup/1"
MANIFEST = "MANIFEST.json"
_MAX_MANIFEST = 16 << 20


class VerifyError(Exception):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


class _Hashing:
    """غلاف كتابة يحسب sha256 والحجم لما يمر به."""

    def __init__(self, fh: BinaryIO):
        self.fh, self.h, self.n = fh, hashlib.sha256(), 0

    def write(self, data) -> int:
        self.h.update(data)
        self.n += len(data)
        return self.fh.write(data)

    def flush(self) -> None:
        self.fh.flush()


def write(work: Path, manifest: Dict[str, Any], out: Path, key: Optional[str]) -> Dict[str, Any]:
    """يكتب الأرشيف إلى ``out`` (يُستدعى على مسار ``.part``)، ويعيد البصمة والحجم."""
    with open(out, "wb") as fh:
        hashed = _Hashing(fh)
        sink = crypto.EncryptingWriter(hashed, key) if key else hashed
        mtime = int(manifest["created_at"])
        with tarfile.open(fileobj=sink, mode="w|gz", format=tarfile.PAX_FORMAT) as tf:
            raw = json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ti = tarfile.TarInfo(MANIFEST)
            ti.size, ti.mode, ti.mtime = len(raw), 0o600, mtime
            tf.addfile(ti, io.BytesIO(raw))
            for f in manifest["files"]:
                src = work / f["path"]
                ti = tarfile.TarInfo(f"data/{f['path']}")
                ti.size, ti.mode, ti.mtime = int(f["size"]), 0o600, mtime
                with open(src, "rb") as sf:
                    tf.addfile(ti, sf)
        if key:
            sink.close()
        fh.flush()
        os.fsync(fh.fileno())
    return {"sha256": hashed.h.hexdigest(), "size": hashed.n}


def safe_rel(name: str) -> Optional[str]:
    """``data/<rel>`` ⇒ ``rel`` إن كان آمنًا، وإلا None."""
    if not name.startswith("data/") or "\\" in name or "\x00" in name:
        return None
    rel = name[len("data/"):]
    p = PurePosixPath(rel)
    if not rel or p.is_absolute() or any(part in ("", ".", "..") for part in rel.split("/")):
        return None
    return p.as_posix()


def _open_stream(fh: BinaryIO, key: Optional[str]):
    head = fh.read(len(crypto.MAGIC))
    fh.seek(0)
    if crypto.is_encrypted(head):
        if not key:
            raise VerifyError("key_required")
        return crypto.DecryptingReader(fh, key), True
    if head[:2] != b"\x1f\x8b":
        raise VerifyError("unknown_format")
    return fh, False


def verify(path: Path, key: Optional[str], expect_sha: Optional[str] = None,
           extract_to: Optional[Path] = None) -> Dict[str, Any]:
    """يتحقق من الأرشيف كاملًا (واستخراجه إن طُلب). يرفع ``VerifyError``."""
    if expect_sha is not None and sha256_file(path) != expect_sha:
        raise VerifyError("sha_mismatch")
    try:
        with open(path, "rb") as fh:
            stream, encrypted = _open_stream(fh, key)
            out = _walk(stream, encrypted, extract_to)
            if encrypted:  # قراءة حتى القطعة الأخيرة: البتر بعد نهاية tar يُكشف أيضًا
                while stream.read(1 << 20):
                    pass
            return out
    except crypto.CryptoError as exc:
        raise VerifyError(exc.reason) from exc
    except (tarfile.TarError, zlib.error, EOFError) as exc:
        raise VerifyError("corrupt", type(exc).__name__) from exc
    except OSError as exc:
        if isinstance(exc, (FileNotFoundError, PermissionError)):
            raise
        raise VerifyError("corrupt", type(exc).__name__) from exc


def _walk(stream, encrypted: bool, extract_to: Optional[Path]) -> Dict[str, Any]:
    manifest: Optional[Dict[str, Any]] = None
    expected: Dict[str, Dict[str, Any]] = {}
    seen = set()
    with tarfile.open(fileobj=stream, mode="r|gz") as tf:
        for m in tf:
            if manifest is None:
                if m.name != MANIFEST or not m.isreg() or m.size > _MAX_MANIFEST:
                    raise VerifyError("manifest_missing")
                manifest = json.loads(tf.extractfile(m).read().decode("utf-8"))
                if manifest.get("format") != FORMAT:
                    raise VerifyError("bad_format")
                for f in manifest.get("files", []):
                    if safe_rel(f"data/{f.get('path', '')}") != f.get("path"):
                        raise VerifyError("unsafe_member", "manifest")
                    expected[f["path"]] = f
                continue
            rel = safe_rel(m.name)
            if rel is None:
                raise VerifyError("unsafe_member", "path")
            if not m.isreg():
                raise VerifyError("unsafe_member", "type")
            if rel not in expected or rel in seen:
                raise VerifyError("unexpected_member")
            seen.add(rel)
            want = expected[rel]
            if m.size != int(want["size"]):
                raise VerifyError("size_mismatch")
            h = hashlib.sha256()
            src = tf.extractfile(m)
            out = None
            if extract_to is not None:
                dest = extract_to.joinpath(*rel.split("/"))
                root = extract_to.resolve()
                dest.parent.mkdir(parents=True, exist_ok=True)
                if root not in dest.parent.resolve().parents and dest.parent.resolve() != root:
                    raise VerifyError("unsafe_member", "escape")
                out = open(dest, "wb")
            try:
                for block in iter(lambda: src.read(1 << 20), b""):
                    h.update(block)
                    if out is not None:
                        out.write(block)
            finally:
                if out is not None:
                    out.close()
            if h.hexdigest() != want["sha256"]:
                raise VerifyError("member_sha_mismatch")
    if manifest is None:
        raise VerifyError("manifest_missing")
    missing = set(expected) - seen
    if missing:
        raise VerifyError("missing_member", str(len(missing)))
    return {"ok": True, "encrypted": encrypted, "files": len(seen), "manifest": manifest}
