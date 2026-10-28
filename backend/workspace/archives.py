"""R-800: الأرشيفات — سرد وتفكيك آمن وإنشاء.

الأمان (كل حد يُعلن سببه حرفيًا عند الرفض):
- لا مسارات مطلقة ولا «..» ولا روابط رمزية/صلبة ولا أجهزة (zip-slip/tar-slip).
- حدود: MAX_MEMBERS عضو، MAX_MEMBER_BYTES للعضو، MAX_TOTAL_BYTES للمجموع، ونسبة ضغط
  ≤ MAX_RATIO للأعضاء الكبيرة (قنابل الضغط).
الصيغ: zip, tar, tar.gz/tgz, tar.bz2, tar.xz, gz, bz2, xz, 7z. (rar غير مدعوم — يُعلن.)
"""

from __future__ import annotations

import bz2
import gzip
import io
import lzma
import tarfile
import zipfile
from pathlib import PurePosixPath
from typing import Any, Dict, List, Tuple

from .readers import ext_of

MAX_MEMBERS = 2000
MAX_MEMBER_BYTES = 50 * 1024 * 1024
MAX_TOTAL_BYTES = 200 * 1024 * 1024
MAX_RATIO = 200


class ArchiveError(ValueError):
    pass


def safe_name(name: str) -> str:
    n = str(name).replace("\\", "/")
    parts = [p for p in PurePosixPath(n).parts if p not in ("", ".", "/")]
    if not parts or any(p == ".." for p in parts) or n.startswith("/") or ":" in parts[0]:
        raise ArchiveError(f"مسار غير آمن داخل الأرشيف: {name!r}")
    return "/".join(parts)


def _fmt(name: str, data: bytes) -> str:
    e = ext_of(name)
    if e == ".zip" or data[:4] == b"PK\x03\x04":
        return "zip"
    if e == ".7z" or data[:6] == b"7z\xbc\xaf\x27\x1c":
        return "7z"
    if e in (".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz", ".tbz2", ".txz"):
        return "tar"
    if e == ".gz":
        return "tar" if _is_tar(gzip.decompress, data) else "gz"
    if e == ".bz2":
        return "tar" if _is_tar(bz2.decompress, data) else "bz2"
    if e == ".xz":
        return "tar" if _is_tar(lzma.decompress, data) else "xz"
    if e == ".rar":
        return "rar"
    raise ArchiveError(f"صيغة أرشيف غير معروفة: {name}")


def _is_tar(fn, data: bytes) -> bool:
    try:
        head = fn(data)[:512]
    except Exception:  # TOLERATED: ليس ضغطًا صالحًا — يُعامل كملف مضغوط مفرد ويفشل بسببه لاحقًا
        return False
    return len(head) >= 262 and head[257:262] == b"ustar"


def list_members(name: str, data: bytes) -> Dict[str, Any]:
    fmt = _fmt(name, data)
    members: List[Dict[str, Any]] = []
    if fmt == "zip":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for i in z.infolist():
                members.append({"name": i.filename, "size": i.file_size,
                                "compressed": i.compress_size, "dir": i.is_dir(),
                                "encrypted": bool(i.flag_bits & 0x1)})
    elif fmt == "tar":
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
            for m in t.getmembers():
                members.append({"name": m.name, "size": m.size, "dir": m.isdir(),
                                "link": m.issym() or m.islnk(), "special": not (m.isfile() or m.isdir())})
    elif fmt == "7z":
        import py7zr
        with py7zr.SevenZipFile(io.BytesIO(data)) as z:
            for i in z.list():
                members.append({"name": i.filename, "size": i.uncompressed or 0, "dir": i.is_directory})
    elif fmt in ("gz", "bz2", "xz"):
        inner = PurePosixPath(name).stem or "file"
        members.append({"name": inner, "size": None, "dir": False})
    else:
        raise ArchiveError("RAR غير مدعوم (لا أداة unrar حرة في الصورة) — حوّله إلى zip/7z")
    files = [m for m in members if not m.get("dir")]
    return {"format": fmt, "members": members[:MAX_MEMBERS], "count": len(members),
            "files": len(files), "total_size": sum(m["size"] or 0 for m in files)}


def _guard(entries: List[Tuple[str, bytes]], name: str, size: int, budget: Dict[str, int]) -> None:
    if len(entries) >= MAX_MEMBERS:
        raise ArchiveError(f"تجاوز حد الأعضاء {MAX_MEMBERS}")
    if size > MAX_MEMBER_BYTES:
        raise ArchiveError(f"العضو {name} أكبر من {MAX_MEMBER_BYTES // (1024 * 1024)}MB")
    budget["total"] += size
    if budget["total"] > MAX_TOTAL_BYTES:
        raise ArchiveError(f"مجموع المفكوك تجاوز {MAX_TOTAL_BYTES // (1024 * 1024)}MB")


def unpack(name: str, data: bytes) -> Dict[str, Any]:
    """⇒ {"format", "entries": [(path, bytes)], "skipped": [{"name","reason"}]}"""
    fmt = _fmt(name, data)
    entries: List[Tuple[str, bytes]] = []
    skipped: List[Dict[str, str]] = []
    budget = {"total": 0}
    if fmt == "zip":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for i in z.infolist():
                if i.is_dir():
                    continue
                if i.flag_bits & 0x1:
                    skipped.append({"name": i.filename, "reason": "مشفر بكلمة مرور"})
                    continue
                try:
                    path = safe_name(i.filename)
                except ArchiveError as exc:
                    skipped.append({"name": i.filename, "reason": str(exc)})
                    continue
                if (i.file_size > 10 * 1024 * 1024 and i.compress_size
                        and i.file_size / i.compress_size > MAX_RATIO):
                    raise ArchiveError(f"نسبة ضغط مريبة في {i.filename} (قنبلة ضغط محتملة)")
                _guard(entries, i.filename, i.file_size, budget)
                with z.open(i) as f:
                    blob = f.read(MAX_MEMBER_BYTES + 1)
                if len(blob) > MAX_MEMBER_BYTES:
                    raise ArchiveError(f"العضو {i.filename} تجاوز الحد عند الفك")
                entries.append((path, blob))
    elif fmt == "tar":
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as t:
            for m in t.getmembers():
                if m.isdir():
                    continue
                if not m.isfile():
                    skipped.append({"name": m.name, "reason": "رابط أو ملف خاص — لا يُفك"})
                    continue
                try:
                    path = safe_name(m.name)
                except ArchiveError as exc:
                    skipped.append({"name": m.name, "reason": str(exc)})
                    continue
                _guard(entries, m.name, m.size, budget)
                f = t.extractfile(m)
                entries.append((path, f.read() if f else b""))
    elif fmt == "7z":
        import py7zr
        with py7zr.SevenZipFile(io.BytesIO(data)) as z:
            infos = [i for i in z.list() if not i.is_directory]
            for i in infos:
                _guard(entries, i.filename, i.uncompressed or 0, budget)
            for fname, bio in (z.readall() or {}).items():
                try:
                    entries.append((safe_name(fname), bio.read()))
                except ArchiveError as exc:
                    skipped.append({"name": fname, "reason": str(exc)})
    elif fmt in ("gz", "bz2", "xz"):
        fn = {"gz": gzip.GzipFile, "bz2": bz2.BZ2File, "xz": lzma.LZMAFile}[fmt]
        with fn(io.BytesIO(data)) as f:
            blob = f.read(MAX_MEMBER_BYTES + 1)
        if len(blob) > MAX_MEMBER_BYTES:
            raise ArchiveError("المحتوى المفكوك تجاوز الحد")
        entries.append((safe_name(PurePosixPath(name).stem or "file"), blob))
    else:
        raise ArchiveError("RAR غير مدعوم (لا أداة unrar حرة في الصورة) — حوّله إلى zip/7z")
    return {"format": fmt, "entries": entries, "skipped": skipped}


def make_zip(entries: List[Tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    seen = set()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path, blob in entries:
            p = safe_name(path)
            base, n = p, 1
            while p in seen:
                stem = PurePosixPath(base)
                p = str(stem.with_name(f"{stem.stem} ({n}){stem.suffix}"))
                n += 1
            seen.add(p)
            z.writestr(p, blob)
    return buf.getvalue()
