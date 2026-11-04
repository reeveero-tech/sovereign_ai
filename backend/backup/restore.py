# -*- coding: utf-8 -*-
"""R-847: الاستعادة — عملية حساسة: خطة جافة، ثم تجهيز بتأكيد صريح، ثم تطبيق عند الإقلاع.

لماذا عند الإقلاع لا أثناء التشغيل؟ قواعد SQLite مفتوحة باتصالات حية (أثبت
RED أن اتصالًا مفتوحًا يحمل كل الصفوف في ``-wal``)، واستبدال ملف تحت اتصال
مفتوح يفسده. لذا التجهيز يكتب الملفات المتحقق منها إلى ``.restore/staged``، ولا
يلمس الحالة الحية. ويطبقها ``python3 -m backup apply-pending`` في نقطة دخول
الحاوية **قبل** تشغيل التطبيق.

الضمانات:
1. ``plan``: تحقق كامل من النسخة، وفرق مع الحالة الحالية (يُضاف، يتغير، يُزاح)،
   و``plan_hash`` يربط القرار بمحتوى النسخة نفسه.
2. ``stage``: يتطلب ``plan_hash`` مطابقًا وتأكيد ``RESTORE <id>`` حرفيًا، ويأخذ نسخة
   ``pre_restore`` من الحالة الحالية **قبل** أي تجهيز. والمفتاح نفسه بالنسخة
   نفسها يعيد التجهيز القائم (تساوي القوة).
3. ``apply_pending``: لكل ملف نسخ إلى مؤقت ثم ``os.replace``، وقبل استبدال القاعدة
   تُحذف ``-wal/-shm/-journal`` (وإلا أعاد SQLite تطبيق WAL قديم كما في RED).
   الملفات غير الموجودة في النسخة **تُزاح** إلى ``.restore/displaced/<id>`` ولا
   تُحذف. وبعدها تُطابق كل البصمات.
4. الانهيار وسط التطبيق يترك الحالة ``applying``، والإقلاع التالي يعيد التطبيق
   كله (المصدر المجهز لا يُستهلك). وبعد ``MAX_APPLY_ATTEMPTS`` محاولات يُتراجع.
5. أي فشل أو عدم تطابق يتراجع إلى نسخة ``pre_restore`` بالطريقة نفسها ويُشعر
   حرجًا. وإن فشل التراجع نفسه تبقى الحالة ``rollback_failed`` ظاهرة: فحص
   ``backup.restore`` يصير failing، والإقلاع لا يُمنع حتى يبقى المالك قادرًا
   على الوصول والتصحيح.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

try:
    from runtime.atomic_json import atomic_write_json
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.runtime.atomic_json import atomic_write_json

from . import archive
from .catalog import Catalog, valid_id
from .snapshot import RESTORE_DIR, SIDE_SUFFIXES, sha256_file, walk

PENDING = "PENDING.json"
LAST = "LAST.json"
MAX_APPLY_ATTEMPTS = 3
_SAMPLE = 20


class RestoreError(Exception):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


def manifest_digest(files: Sequence[Dict[str, Any]]) -> str:
    rows = sorted((f["path"], f["sha256"]) for f in files)
    return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


def plan_hash(bid: str, meta: Dict[str, Any]) -> str:
    return hashlib.sha256(
        f"{bid}|{meta['sha256']}|{meta['manifest_digest']}".encode("utf-8")).hexdigest()


def _rdir(data_dir: Path) -> Path:
    return Path(data_dir) / RESTORE_DIR


def _load(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:  # TOLERATED: لا ملف ⇒ لا حالة
        return None


def pending(data_dir: Path) -> Optional[Dict[str, Any]]:
    return _load(_rdir(data_dir) / PENDING)


def last(data_dir: Path) -> Optional[Dict[str, Any]]:
    return _load(_rdir(data_dir) / LAST)


def tree_map(data_dir: Path, excluded_tops: Sequence[str]) -> Dict[str, str]:
    return {rel: sha256_file(p) for rel, p, why in walk(Path(data_dir), excluded_tops)
            if why is None}


# ===================================================================== الخطة
def _verified(cat: Catalog, bid: str, key: Optional[str],
              extract_to: Optional[Path] = None) -> Dict[str, Any]:
    meta = cat.get(bid) if valid_id(bid) else None
    if meta is None:
        raise RestoreError("not_found")
    try:
        v = archive.verify(cat.archive(bid), key, meta["sha256"], extract_to)
    except archive.VerifyError as exc:
        raise RestoreError("verify_failed", exc.reason) from exc
    if manifest_digest(v["manifest"]["files"]) != meta.get("manifest_digest"):
        raise RestoreError("verify_failed", "manifest_digest")
    return {"meta": meta, "manifest": v["manifest"]}


def plan(cat: Catalog, bid: str, data_dir: Path, key: Optional[str],
         excluded_tops: Sequence[str]) -> Dict[str, Any]:
    """خطة جافة — لا تكتب شيئًا."""
    v = _verified(cat, bid, key)
    files = {f["path"]: f for f in v["manifest"]["files"]}
    cur = tree_map(data_dir, excluded_tops)
    added = sorted(p for p in files if p not in cur)
    changed = sorted(p for p in files if p in cur and cur[p] != files[p]["sha256"])
    displaced = sorted(p for p in cur if p not in files)
    return {"backup_id": bid, "kind": v["meta"].get("kind"),
            "created_at": v["meta"].get("created_at"),
            "files": len(files), "added": len(added), "changed": len(changed),
            "displaced": len(displaced), "unchanged": len(files) - len(added) - len(changed),
            "sample": {"added": added[:_SAMPLE], "changed": changed[:_SAMPLE],
                       "displaced": displaced[:_SAMPLE]},
            "plan_hash": plan_hash(bid, v["meta"]),
            "confirm": f"RESTORE {bid}",
            "note": "التطبيق عند إعادة التشغيل التالية؛ الملفات الزائدة تُزاح ولا تُحذف"}


# ===================================================================== التجهيز
def stage(cat: Catalog, bid: str, given_plan_hash: str, confirm: str, actor: str,
          idem_key: str, data_dir: Path, key: Optional[str],
          pre_snapshot: Callable[[], Dict[str, Any]],
          clock: Callable[[], float] = time.time) -> Dict[str, Any]:
    if not valid_id(bid) or cat.get(bid) is None:
        raise RestoreError("not_found")
    if confirm != f"RESTORE {bid}":
        raise RestoreError("confirm_mismatch")
    meta = cat.get(bid)
    if not given_plan_hash or given_plan_hash != plan_hash(bid, meta):
        raise RestoreError("plan_mismatch")
    rd = _rdir(data_dir)
    cur = pending(data_dir)
    if cur is not None:
        if cur.get("idem_key") == idem_key and cur.get("backup_id") == bid:
            return {**_public(cur), "replayed": True}
        raise RestoreError("restore_pending_exists", str(cur.get("backup_id")))
    try:
        pre = pre_snapshot()
    except Exception as exc:
        raise RestoreError("pre_restore_failed", getattr(exc, "reason", type(exc).__name__)) from exc
    rd.mkdir(parents=True, exist_ok=True)
    tmp = rd / "staged.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    try:
        v = _verified(cat, bid, key, extract_to=tmp)
    except RestoreError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    shutil.rmtree(rd / "staged", ignore_errors=True)
    os.replace(tmp, rd / "staged")
    p = {"backup_id": bid, "pre_restore_id": pre["backup_id"], "plan_hash": given_plan_hash,
         "actor": actor[:120], "idem_key": idem_key[:200], "staged_at": clock(),
         "state": "staged", "attempts": 0,
         "files": [{k: f[k] for k in ("path", "sha256", "size", "mode", "kind")}
                   for f in v["manifest"]["files"]]}
    atomic_write_json(rd / PENDING, p, ensure_ascii=False, file_mode=0o600)
    return _public(p)


def _public(p: Dict[str, Any]) -> Dict[str, Any]:
    return {**{k: v for k, v in p.items() if k not in ("files", "idem_key")},
            "files": len(p.get("files", []))}


def cancel(data_dir: Path) -> Dict[str, Any]:
    rd = _rdir(data_dir)
    cur = pending(data_dir)
    if cur is None:
        return {"cancelled": False, "reason": "لا استعادة مجهزة"}
    if cur.get("state") == "applying":
        return {"cancelled": False, "reason": "التطبيق بدأ — لا إلغاء"}
    (rd / PENDING).unlink()
    shutil.rmtree(rd / "staged", ignore_errors=True)
    return {"cancelled": True, "backup_id": cur.get("backup_id")}


# ===================================================================== التطبيق
def _unlink(p: Path) -> None:
    try:
        p.unlink()
    except FileNotFoundError:  # TOLERATED: الحذف متساوي القوة — غائب أصلًا
        pass


def _apply_tree(data_dir: Path, src_root: Path, files: List[Dict[str, Any]],
                displaced_root: Path, excluded_tops: Sequence[str],
                progress: Optional[Callable[[int], None]] = None) -> int:
    want = {f["path"] for f in files}
    for i, f in enumerate(files):
        src = src_root.joinpath(*f["path"].split("/"))
        dst = Path(data_dir).joinpath(*f["path"].split("/"))
        dst.parent.mkdir(parents=True, exist_ok=True)
        if f.get("kind") == "sqlite":
            for suf in SIDE_SUFFIXES:
                _unlink(Path(str(dst) + suf))
        tmp = dst.parent / f".{dst.name}.restore.tmp"
        shutil.copyfile(src, tmp)
        with open(tmp, "rb") as fh:
            os.fsync(fh.fileno())
        os.chmod(tmp, int(f.get("mode", 0o600)))
        os.replace(tmp, dst)
        if progress is not None:
            progress(i + 1)
    moved = 0
    for rel, path, why in list(walk(Path(data_dir), excluded_tops)):
        if why is not None or rel in want:
            continue
        target = displaced_root.joinpath(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(path, target)
        for suf in SIDE_SUFFIXES:
            side = Path(str(path) + suf)
            if side.exists():
                os.replace(side, Path(str(target) + suf))
        moved += 1
    return moved


def _mismatches(data_dir: Path, files: List[Dict[str, Any]]) -> List[str]:
    bad = []
    for f in files:
        dst = Path(data_dir).joinpath(*f["path"].split("/"))
        if not dst.is_file() or sha256_file(dst) != f["sha256"]:
            bad.append(f["path"])
        elif f.get("kind") == "sqlite" and any(Path(str(dst) + s).exists()
                                               for s in SIDE_SUFFIXES):
            bad.append(f["path"])
    return bad


def _event(notify, name: str, bid: str, summary: str) -> None:
    if notify is None:
        return
    try:
        from notifications import events
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.notifications import events
    notify(events.make(name, f"{name}:{bid}", bid, summary, link="/backups/restore"))


def apply_pending(data_dir: Path, cat: Catalog, key: Optional[str],
                  excluded_tops: Sequence[str], notify: Optional[Callable] = None,
                  progress: Optional[Callable[[int], None]] = None,
                  clock: Callable[[], float] = time.time) -> Dict[str, Any]:
    """يُستدعى عند الإقلاع قبل التطبيق. لا يرفع إلا انهيارًا حقيقيًا (BaseException)."""
    rd = _rdir(data_dir)
    p = pending(data_dir)
    if p is None:
        return {"state": "none"}
    if p.get("state") not in ("staged", "applying"):
        return {"state": p.get("state"), "backup_id": p.get("backup_id")}
    bid = p["backup_id"]
    p["state"], p["attempts"] = "applying", int(p.get("attempts", 0)) + 1
    atomic_write_json(rd / PENDING, p, ensure_ascii=False, file_mode=0o600)
    reason = ""
    moved = 0
    try:
        if p["attempts"] > MAX_APPLY_ATTEMPTS:
            raise RestoreError("too_many_attempts", str(p["attempts"] - 1))
        moved = _apply_tree(data_dir, rd / "staged", p["files"], rd / "displaced" / bid,
                            excluded_tops, progress)
        bad = _mismatches(data_dir, p["files"])
        if bad:
            raise RestoreError("verify_mismatch", str(len(bad)))
    except Exception as exc:  # فشل مُعلن ⇒ تراجع (لا ابتلاع: يُسجل في LAST ويُشعر)
        reason = getattr(exc, "reason", type(exc).__name__)
    if not reason:
        res = {"state": "applied", "backup_id": bid, "pre_restore_id": p.get("pre_restore_id"),
               "at": clock(), "files": len(p["files"]), "displaced": moved,
               "attempts": p["attempts"], "actor": p.get("actor")}
        atomic_write_json(rd / LAST, res, ensure_ascii=False, file_mode=0o600)
        (rd / PENDING).unlink()
        shutil.rmtree(rd / "staged", ignore_errors=True)
        _event(notify, "restore.applied", bid,
               f"طُبقت النسخة {bid}: {len(p['files'])} ملف، أُزيح {moved}")
        return res
    return _rollback(data_dir, cat, key, excluded_tops, p, reason, notify, clock)


def _rollback(data_dir: Path, cat: Catalog, key: Optional[str], excluded_tops: Sequence[str],
              p: Dict[str, Any], reason: str, notify, clock) -> Dict[str, Any]:
    rd, bid, pre_id = _rdir(data_dir), p["backup_id"], p.get("pre_restore_id")
    rb = rd / "rollback"
    shutil.rmtree(rb, ignore_errors=True)
    rb.mkdir(parents=True)
    state, rb_reason = "rolled_back", ""
    try:
        v = _verified(cat, pre_id, key, extract_to=rb)
        files = v["manifest"]["files"]
        _apply_tree(data_dir, rb, files, rd / "displaced" / f"{bid}-rollback", excluded_tops)
        if _mismatches(data_dir, files):
            raise RestoreError("rollback_mismatch")
    except Exception as exc:  # فشل التراجع نفسه ⇒ حالة ظاهرة failing لا انهيار إقلاع
        state, rb_reason = "rollback_failed", getattr(exc, "reason", type(exc).__name__)
    res = {"state": state, "backup_id": bid, "pre_restore_id": pre_id, "at": clock(),
           "reason": reason, "rollback_reason": rb_reason, "attempts": p.get("attempts"),
           "actor": p.get("actor")}
    atomic_write_json(rd / LAST, res, ensure_ascii=False, file_mode=0o600)
    if state == "rolled_back":
        (rd / PENDING).unlink()
        shutil.rmtree(rd / "staged", ignore_errors=True)
    else:
        p["state"] = "rollback_failed"
        atomic_write_json(rd / PENDING, p, ensure_ascii=False, file_mode=0o600)
    shutil.rmtree(rb, ignore_errors=True)
    _event(notify, "restore.failed", bid,
           f"فشلت استعادة {bid} ({reason}) — "
           + ("تراجع إلى ما قبلها" if state == "rolled_back" else f"والتراجع فشل ({rb_reason})"))
    return res
