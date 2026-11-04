# -*- coding: utf-8 -*-
"""R-847: لقطة متسقة لمجلد البيانات — قواعد الاستثناء ونسخ كل نوع بطريقته.

لماذا لا يكفي ``cp``؟ أثبت RED أن قاعدة SQLite في وضع WAL باتصال مفتوح
تُنسخ بلا جداول، لأن الصفوف الملتزمة كلها في ``-wal``. لذا:
- **SQLite** (يُعرف بالرأس ``SQLite format 3\\0``، لا بالامتداد): يُنسخ بواجهة
  ``sqlite3.Connection.backup``، وهي نسخة متسقة على الإنترنت تشمل ما في WAL،
  ثم يُفحص ``PRAGMA integrity_check``.
- **jsonl/ndjson/log**: ملفات إلحاق، فتُنسخ حتى آخر ``\\n`` فقط. السطر الأخير
  الذي يُكتب لحظة النسخ يُسقط ولا يُؤرشف ممزقًا.
- **غيرها**: نسخ بايتات. كتابات المشروع ذرية (``atomic_write_json``)، فالملف
  إما قديم كامل أو جديد كامل.

الاستثناءات المشتركة مع الاستعادة: مجلد النسخ نفسه و``.restore``، وملفات
``-wal/-shm/-journal`` (محتواها داخل نسخة القاعدة)، والملفات المؤقتة. أما
الروابط الرمزية والملفات الخاصة فتُتخطى وتُسجل في البيان، ولا تُتبع.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import stat
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import quote

SQLITE_MAGIC = b"SQLite format 3\x00"
SIDE_SUFFIXES = ("-wal", "-shm", "-journal")
TMP_SUFFIXES = (".tmp", ".part")
APPEND_SUFFIXES = (".jsonl", ".ndjson", ".log")
RESTORE_DIR = ".restore"


class BackupError(Exception):
    """فشل إنشاء نسخة — ``reason`` من مفردات ثابتة (لا مسارات ولا أسرار)."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def is_sqlite(path: Path) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(16) == SQLITE_MAGIC
    except OSError:  # TOLERATED: ملف لا يُقرأ ليس قاعدة — يُعامل نسخ بايتات ويُكشف خطؤه هناك
        return False


def excluded_name(name: str) -> bool:
    return name.endswith(SIDE_SUFFIXES) or name.endswith(TMP_SUFFIXES)


def walk(data_dir: Path, excluded_tops: Sequence[str]
         ) -> Iterator[Tuple[str, Path, Optional[str]]]:
    """يعيد (المسار النسبي، المسار، سبب التخطي أو None) لكل ملف غير مستثنى.

    المسار النسبي بفواصل ``/`` دائمًا. المستثنى بالقاعدة لا يظهر أصلًا، أما
    المتخطى (الرابط الرمزي والخاص) فيظهر بسببه ليُسجل.
    """
    tops = set(excluded_tops) | {RESTORE_DIR}
    for root, dirs, files in os.walk(data_dir, followlinks=False):
        rel_root = Path(root).relative_to(data_dir)
        if rel_root == Path("."):
            dirs[:] = [d for d in dirs if d not in tops]
        keep = []
        for d in sorted(dirs):
            p = Path(root) / d
            if p.is_symlink():
                yield ((rel_root / d).as_posix(), p, "symlink")
            else:
                keep.append(d)
        dirs[:] = keep
        for f in sorted(files):
            if excluded_name(f):
                continue
            p = Path(root) / f
            rel = (rel_root / f).as_posix()
            st = os.lstat(p)
            if stat.S_ISLNK(st.st_mode):
                yield (rel, p, "symlink")
            elif not stat.S_ISREG(st.st_mode):
                yield (rel, p, "special")
            else:
                yield (rel, p, None)


def _copy_sqlite(src: Path, dst: Path) -> None:
    s = sqlite3.connect(f"file:{quote(str(src))}?mode=ro", uri=True, timeout=30)
    try:
        d = sqlite3.connect(str(dst))
        try:
            s.backup(d)
            row = d.execute("PRAGMA integrity_check").fetchone()
            if not row or row[0] != "ok":
                raise BackupError("sqlite_corrupt", src.name)
        finally:
            d.close()
    finally:
        s.close()


def _copy_append(src: Path, dst: Path) -> bool:
    """ينسخ حتى آخر سطر كامل. يعيد True إن أُسقط ذيل ممزق."""
    data = src.read_bytes()
    cut = data.rfind(b"\n") + 1
    dst.write_bytes(data[:cut])
    return cut != len(data)


def collect(data_dir: Path, work: Path, excluded_tops: Sequence[str],
            max_bytes: int) -> Dict[str, object]:
    """ينسخ كل ملف غير مستثنى إلى ``work/<rel>`` ويعيد قائمة البيان."""
    files: List[Dict[str, object]] = []
    skipped: List[Dict[str, str]] = []
    total, torn = 0, 0
    for rel, path, why in walk(data_dir, excluded_tops):
        if why:
            skipped.append({"path": rel, "reason": why})
            continue
        try:
            mode = stat.S_IMODE(os.stat(path).st_mode)
            size_now = os.path.getsize(path)
        except FileNotFoundError:  # TOLERATED: ملف حُذف أثناء المسح — ليس في اللقطة ويُسجل
            skipped.append({"path": rel, "reason": "vanished"})
            continue
        if total + size_now > max_bytes:
            raise BackupError("size_cap", f"> {max_bytes} bytes")
        dst = work / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if is_sqlite(path):
                kind = "sqlite"
                _copy_sqlite(path, dst)
            elif path.name.endswith(APPEND_SUFFIXES):
                kind = "append"
                torn += 1 if _copy_append(path, dst) else 0
            else:
                kind = "file"
                shutil.copyfile(path, dst)
        except FileNotFoundError:  # TOLERATED: حُذف بين المسح والنسخ — يُسجل متخطى
            skipped.append({"path": rel, "reason": "vanished"})
            continue
        size = dst.stat().st_size
        total += size
        if total > max_bytes:
            raise BackupError("size_cap", f"> {max_bytes} bytes")
        files.append({"path": rel, "kind": kind, "size": size, "mode": mode,
                      "sha256": sha256_file(dst)})
    return {"files": files, "skipped": skipped, "bytes": total, "torn_tails": torn}
