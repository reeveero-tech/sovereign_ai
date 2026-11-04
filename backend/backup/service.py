# -*- coding: utf-8 -*-
"""R-847: خدمة النسخ — الإعدادات، والإنشاء، والجدولة، والجاهزية، والمقاييس.

البيئة:
- ``SOVEREIGN_BACKUP_INTERVAL_S``: فترة النسخ المجدول (افتراضي 21600 = 6 ساعات،
  و0 يعطلها). تُدرج المجدولة مهمة ``backup.create`` في الطابور بمفتاح
  ``backup:scheduled:<الفترة>``، فلا تتكرر النسخة في الفترة الواحدة ولو أُعيد
  الإقلاع.
- ``SOVEREIGN_BACKUP_KEEP``: عدد النسخ المحفوظة محليًا (افتراضي 7).
- ``SOVEREIGN_BACKUP_MAX_MB``: سقف حجم البيانات المنسوخة (افتراضي 512).
- ``SOVEREIGN_BACKUP_KEY``: مفتاح التشفير (32 حرفًا على الأقل). عند ضبطه تُشفر
  كل النسخ، وهو شرط أي رفع خارجي. والمفتاح الأقصر خطأ صريح ``weak_key``، لا
  نسخة صريحة صامتة.
- ``SOVEREIGN_BACKUP_DIR``: مجلد الفهرس (افتراضي ``DATA_DIR/backups``).
- وجهة خارجية (اختيارية؛ الأولى المضبوطة):
  ``SOVEREIGN_BACKUP_SUPABASE_URL`` و``_KEY`` و``_BUCKET``، أو
  ``SOVEREIGN_BACKUP_MIRROR_DIR``.

قاعدة الربط: النسخ لا يكسر ما ينسخه. وكل فشل يُسجل في ``state.json``، ويُشعر
المالك بحدث ``backup.failed``، ويظهر في فحص ``backup.freshness``.
"""
from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

from . import archive, crypto, offsite, restore, snapshot
from .catalog import KINDS, Catalog, new_id, valid_id
from .snapshot import BackupError

_log = logging.getLogger("backup")
_STARTED = {"at": time.time()}
_SCHED: Dict[str, Any] = {}
_LOCK = threading.Lock()
SCHED_TICK_S = 300


# ===================================================================== الإعدادات
def _int_env(name: str, default: int, lo: int, hi: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(lo, min(int(raw), hi))
    except ValueError:
        _log.warning("R-847: %s=%r غير صالح — الافتراضي %s", name, raw, default)
        return default


def _default_notify(ev: Dict[str, Any]) -> Any:
    try:
        from notifications import service as nt
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.notifications import service as nt
    return nt.safe_emit(ev)


@dataclass
class Settings:
    data_dir: Path
    root: Path
    key: Optional[str] = None
    interval_s: int = 21600
    keep: int = 7
    max_bytes: int = 512 << 20
    dest: Optional[offsite.Destination] = None
    offsite_error: str = ""
    notify: Optional[Callable[[Dict[str, Any]], Any]] = None
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.time
    started_at: float = field(default_factory=lambda: _STARTED["at"])

    @property
    def excluded_tops(self) -> List[str]:
        try:
            rel = Path(self.root).resolve().relative_to(Path(self.data_dir).resolve())
        except ValueError:  # TOLERATED: الفهرس خارج مجلد البيانات ⇒ لا استثناء له
            return []
        return [rel.parts[0]] if rel.parts else []

    def catalog(self) -> Catalog:
        return Catalog(self.root)

    def emit(self, ev: Dict[str, Any]) -> None:
        if self.notify is not None:
            self.notify(ev)


def _data_dir() -> Path:
    try:
        from config import DATA_DIR
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.config import DATA_DIR
    return Path(DATA_DIR)


def from_env() -> Settings:
    data_dir = _data_dir()
    root = Path(os.environ.get("SOVEREIGN_BACKUP_DIR", "").strip() or data_dir / "backups")
    key = os.environ.get("SOVEREIGN_BACKUP_KEY", "").strip() or None
    dest, err = None, ""
    url = os.environ.get("SOVEREIGN_BACKUP_SUPABASE_URL", "").strip()
    skey = os.environ.get("SOVEREIGN_BACKUP_SUPABASE_KEY", "").strip()
    bucket = os.environ.get("SOVEREIGN_BACKUP_SUPABASE_BUCKET", "").strip()
    mirror = os.environ.get("SOVEREIGN_BACKUP_MIRROR_DIR", "").strip()
    if url or skey or bucket:
        if url and skey and bucket:
            try:
                dest = offsite.SupabaseStorage(url, skey, bucket)
            except offsite.OffsiteError as exc:
                err = exc.detail or exc.kind
        else:
            err = "إعدادات Supabase ناقصة (URL/KEY/BUCKET)"
    elif mirror:
        dest = offsite.DirDestination(Path(mirror))
    return Settings(data_dir=data_dir, root=root, key=key,
                    interval_s=_int_env("SOVEREIGN_BACKUP_INTERVAL_S", 21600, 0, 7 * 86400),
                    keep=_int_env("SOVEREIGN_BACKUP_KEEP", 7, 1, 100),
                    max_bytes=_int_env("SOVEREIGN_BACKUP_MAX_MB", 512, 1, 10240) << 20,
                    dest=dest, offsite_error=err, notify=_default_notify)


_OVERRIDE: List[Settings] = []


@contextmanager
def use_settings(s: Settings) -> Iterator[Settings]:
    """للاختبار والتقييم: إعدادات معزولة بدل البيئة (مكدس، يُعاد عند الخروج)."""
    _OVERRIDE.append(s)
    try:
        yield s
    finally:
        _OVERRIDE.remove(s)


def settings() -> Settings:
    return _OVERRIDE[-1] if _OVERRIDE else from_env()


# ===================================================================== الإنشاء
def _event(s: Settings, name: str, dedupe: str, subject: str, summary: str) -> None:
    try:
        from notifications import events
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.notifications import events
    s.emit(events.make(name, dedupe, subject, summary, link="/backups"))


def _fail(s: Settings, cat: Catalog, reason: str, bid: str) -> None:
    now = s.clock()
    cat.update_state(last_failure={"at": now, "reason": reason, "backup_id": bid})
    _event(s, "backup.failed", f"backup.failed:{reason}:{int(now // 3600)}", bid,
           f"فشل النسخ الاحتياطي ({reason})")


def _reason(exc: BaseException) -> str:
    if isinstance(exc, (BackupError, archive.VerifyError, crypto.CryptoError)):
        return exc.reason
    if isinstance(exc, sqlite3.Error):
        return "sqlite_error"
    if isinstance(exc, OSError):
        return "io_error"
    return type(exc).__name__


def create(kind: str = "manual", actor: str = "owner", s: Optional[Settings] = None
           ) -> Dict[str, Any]:
    """ينشئ نسخة متحققًا منها (قراءة راجعة كاملة). يرفع ``BackupError``."""
    s = s or settings()
    if kind not in KINDS or kind == "fetched":
        raise ValueError(f"نوع نسخة غير صالح: {kind}")
    cat = s.catalog()
    try:
        crypto.check_key(s.key)
    except crypto.CryptoError:
        cat.ensure()
        _fail(s, cat, "weak_key", "-")
        raise BackupError("weak_key", f"SOVEREIGN_BACKUP_KEY أقصر من {crypto.MIN_KEY_LEN}")
    with cat.lock():
        now = s.clock()
        bid = new_id(now)
        work, part = cat.work / bid, cat.root / f".{bid}.svbk.part"
        try:
            work.mkdir(parents=True)
            snap = snapshot.collect(s.data_dir, work, s.excluded_tops, s.max_bytes)
            manifest = {"format": archive.FORMAT, "backup_id": bid, "kind": kind,
                        "created_at": now, "files": snap["files"], "skipped": snap["skipped"],
                        "bytes": snap["bytes"], "torn_tails": snap["torn_tails"],
                        "encrypted": bool(s.key)}
            res = archive.write(work, manifest, part, s.key)
            os.replace(part, cat.archive(bid))
            archive.verify(cat.archive(bid), s.key, res["sha256"])  # قراءة راجعة
            meta = {"backup_id": bid, "kind": kind, "actor": actor[:120], "created_at": now,
                    "size": res["size"], "sha256": res["sha256"], "encrypted": bool(s.key),
                    "key_fingerprint": crypto.fingerprint(s.key) if s.key else None,
                    "files": len(snap["files"]), "data_bytes": snap["bytes"],
                    "skipped": len(snap["skipped"]), "torn_tails": snap["torn_tails"],
                    "manifest_digest": restore.manifest_digest(snap["files"]),
                    "verified_at": s.clock(), "offsite": {"status": "none"}}
            cat.put(meta)
        except Exception as exc:
            for p in (part, cat.archive(bid), cat.sidecar(bid)):
                restore._unlink(p)
            reason = _reason(exc)
            _fail(s, cat, reason, bid)
            raise BackupError(reason, getattr(exc, "detail", "")) from exc
        finally:
            shutil.rmtree(work, ignore_errors=True)
        meta["pruned"] = cat.prune(s.keep)
        _push(s, cat, meta)
        cat.update_state(last_success={"backup_id": bid, "at": now, "size": meta["size"],
                                       "kind": kind})
        return meta


def _push(s: Settings, cat: Catalog, meta: Dict[str, Any]) -> None:
    if meta["kind"] == "pre_restore":
        return  # شبكة أمان محلية للتراجع — لا تُرفع
    if s.dest is None:
        if s.offsite_error:
            meta["offsite"] = {"status": "config", "detail": s.offsite_error}
            cat.put(meta)
        return
    r = offsite.push(s.dest, meta["backup_id"], cat.archive(meta["backup_id"]),
                     bool(meta["encrypted"]), s.sleep)
    meta["offsite"] = {**r, "at": s.clock()}
    cat.put(meta)
    cat.update_state(last_offsite={"status": r["status"], "at": s.clock(),
                                   "backup_id": meta["backup_id"]})
    if r["status"] not in ("uploaded", "exists"):
        _event(s, "backup.offsite_failed", f"backup.offsite_failed:{meta['backup_id']}",
               meta["backup_id"],
               f"تعذر رفع {meta['backup_id']} خارج الخادم ({r['status']}"
               f", {r['attempts']} محاولة)")


# ===================================================================== التحقق والجلب
def verify(bid: str, s: Optional[Settings] = None) -> Dict[str, Any]:
    s = s or settings()
    cat = s.catalog()
    meta = cat.get(bid) if valid_id(bid) else None
    if meta is None:
        return {"ok": False, "reason": "not_found"}
    try:
        v = archive.verify(cat.archive(bid), s.key, meta["sha256"])
    except archive.VerifyError as exc:
        return {"ok": False, "reason": exc.reason, "backup_id": bid}
    ok = restore.manifest_digest(v["manifest"]["files"]) == meta.get("manifest_digest")
    return {"ok": ok, "reason": "" if ok else "manifest_digest", "backup_id": bid,
            "files": v["files"], "encrypted": v["encrypted"]}


def fetch(bid: str, s: Optional[Settings] = None) -> Dict[str, Any]:
    """تعافٍ من كارثة: ينزّل نسخة من الوجهة الخارجية ويتحقق منها ويدخلها الفهرس."""
    s = s or settings()
    if not valid_id(bid):
        raise BackupError("not_found")
    if s.dest is None:
        raise BackupError("offsite_not_configured")
    cat = s.catalog()
    existing = cat.get(bid)
    if existing is not None:
        return {**existing, "replayed": True}
    cat.ensure()
    tmp = cat.work / f"{bid}.fetch"
    try:
        s.dest.get(offsite.object_name(bid), tmp)
        sha = snapshot.sha256_file(tmp)
        v = archive.verify(tmp, s.key, sha)
        man = v["manifest"]
        if man.get("backup_id") != bid:
            raise BackupError("id_mismatch")
        os.replace(tmp, cat.archive(bid))
    except offsite.OffsiteError as exc:
        restore._unlink(tmp)
        raise BackupError(f"offsite_{exc.kind}", exc.detail) from exc
    except archive.VerifyError as exc:
        restore._unlink(tmp)
        raise BackupError("verify_failed", exc.reason) from exc
    meta = {"backup_id": bid, "kind": "fetched", "actor": "owner",
            "created_at": man["created_at"], "size": cat.archive(bid).stat().st_size,
            "sha256": sha, "encrypted": v["encrypted"],
            "key_fingerprint": crypto.fingerprint(s.key) if s.key and v["encrypted"] else None,
            "files": len(man["files"]), "data_bytes": man.get("bytes"),
            "skipped": len(man.get("skipped", [])), "torn_tails": man.get("torn_tails", 0),
            "manifest_digest": restore.manifest_digest(man["files"]),
            "verified_at": s.clock(), "offsite": {"status": "exists"}, "fetched_at": s.clock()}
    cat.put(meta)
    return meta


# ===================================================================== الاستعادة
def plan(bid: str, s: Optional[Settings] = None) -> Dict[str, Any]:
    s = s or settings()
    return restore.plan(s.catalog(), bid, s.data_dir, s.key, s.excluded_tops)


def stage(bid: str, plan_hash: str, confirm: str, actor: str, idem_key: str,
          s: Optional[Settings] = None) -> Dict[str, Any]:
    s = s or settings()
    out = restore.stage(s.catalog(), bid, plan_hash, confirm, actor, idem_key, s.data_dir,
                        s.key, lambda: create("pre_restore", actor, s), s.clock)
    if not out.get("replayed"):
        _event(s, "restore.staged", f"restore.staged:{bid}:{out['pre_restore_id']}", bid,
               f"جُهزت استعادة {bid} — تُطبق عند إعادة التشغيل التالية"
               f" (نسخة ما قبلها {out['pre_restore_id']})")
    return out


def apply_pending(s: Optional[Settings] = None, progress=None) -> Dict[str, Any]:
    s = s or settings()
    return restore.apply_pending(s.data_dir, s.catalog(), s.key, s.excluded_tops,
                                 notify=s.notify, progress=progress, clock=s.clock)


def restore_status(s: Optional[Settings] = None) -> Dict[str, Any]:
    s = s or settings()
    p = restore.pending(s.data_dir)
    return {"pending": restore._public(p) if p else None, "last": restore.last(s.data_dir)}


# ===================================================================== المهمة والجدولة
def run_job(payload: Dict[str, Any], actor: str) -> Dict[str, Any]:
    """معالج ``backup.create`` في الطابور."""
    meta = create(payload.get("kind", "manual"), actor)
    return {k: meta.get(k) for k in ("backup_id", "kind", "size", "files", "encrypted",
                                     "offsite", "pruned")}


def schedule_tick(store, s: Optional[Settings] = None) -> Optional[Dict[str, Any]]:
    """إدراج نسخة الفترة الحالية (متساوي القوة بمفتاح الفترة)."""
    s = s or settings()
    if s.interval_s <= 0:
        return None
    period = int(s.clock() // s.interval_s)
    job, created = store.enqueue("backup.create", {"kind": "scheduled"},
                                 f"backup:scheduled:{period}", "scheduler",
                                 max_attempts=1, timeout_s=1800.0)
    return {"job_id": job["id"], "created": created, "period": period}


def start_scheduler() -> str:
    try:
        from job_queue import service as jq
        from runtime.threads import start_managed
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.job_queue import service as jq
        from backend.runtime.threads import start_managed
    s = from_env()
    if s.interval_s == 0:
        return "النسخ: المجدول معطل (SOVEREIGN_BACKUP_INTERVAL_S=0)"
    with _LOCK:
        t = _SCHED.get("thread")
        if t is not None and t.is_alive():
            return "النسخ: المجدول يعمل مسبقًا"
        stop = threading.Event()

        def _loop() -> None:
            while not stop.is_set():
                try:
                    schedule_tick(jq.get_store(), from_env())
                except Exception as exc:  # TOLERATED: دورة إدراج فاشلة تُسجل والمجدول يكمل (الفحص يكشف التقادم)
                    _log.error("R-847: تعذر إدراج النسخة المجدولة: %s", type(exc).__name__)
                stop.wait(min(SCHED_TICK_S, s.interval_s))

        t = start_managed(_loop, name="backup-scheduler", stop_event=stop)
        if t is None:
            return "النسخ: خيوط الخلفية معطلة — POST /backups عند الطلب فقط"
        _SCHED.update(thread=t, stop=stop)
    enc = "مشفرة" if s.key else "غير مشفرة (لا SOVEREIGN_BACKUP_KEY)"
    where = s.dest.name if s.dest else "محلية فقط"
    return f"النسخ: كل {s.interval_s}ث، {enc}، الوجهة: {where}"


# ===================================================================== الجاهزية والمقاييس
def checks(s: Optional[Settings] = None, now: Optional[float] = None) -> List[Dict[str, str]]:
    try:
        from observability.health import DEGRADED, FAILING, OK, _r
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.observability.health import DEGRADED, FAILING, OK, _r
    s = s or settings()
    now = s.clock() if now is None else now
    st = s.catalog().state()
    ok, fail = st.get("last_success"), st.get("last_failure")
    out: List[Dict[str, str]] = []
    window = 2 * s.interval_s
    if s.interval_s == 0:
        out.append(_r("backup.freshness", OK, "النسخ المجدول معطل بأمر البيئة (INTERVAL_S=0)"))
    elif ok is None:
        late = now - s.started_at > window
        out.append(_r("backup.freshness", DEGRADED if late else OK,
                      "لا نسخة ناجحة بعد" + ("" if late else " — الأولى خلال الفترة")))
    elif now - float(ok["at"]) > window:
        out.append(_r("backup.freshness", DEGRADED,
                      f"آخر نسخة ناجحة قبل {(now - float(ok['at'])) / 3600:.1f}س"
                      f" (الحد {window / 3600:.1f}س)"))
    elif fail and float(fail["at"]) > float(ok["at"]):
        out.append(_r("backup.freshness", DEGRADED, f"آخر محاولة فشلت ({fail.get('reason')})"))
    else:
        out.append(_r("backup.freshness", OK,
                      f"آخر نسخة قبل {(now - float(ok['at'])) / 3600:.1f}س"))
    if s.dest is None:
        out.append(_r("backup.offsite", DEGRADED if s.offsite_error else OK,
                      "إعدادات الوجهة الخارجية غير صالحة" if s.offsite_error
                      else "لا وجهة خارجية مضبوطة — النسخ على الحجم نفسه فقط"))
    else:
        lo = st.get("last_offsite") or {}
        bad = lo.get("status") not in (None, "uploaded", "exists")
        out.append(_r("backup.offsite", DEGRADED if bad else OK,
                      f"آخر رفع إلى {s.dest.name}: {lo.get('status', 'لم يجر بعد')}"))
    p, last = restore.pending(s.data_dir), restore.last(s.data_dir)
    if p is not None and p.get("state") == "rollback_failed":
        out.append(_r("backup.restore", FAILING, "فشلت الاستعادة وفشل التراجع — تدخل المالك"))
    elif last and last.get("state") in ("rolled_back", "rollback_failed") \
            and now - float(last.get("at", 0)) < 86400:
        out.append(_r("backup.restore", FAILING,
                      f"آخر استعادة فشلت ({last.get('reason')}) وتراجعت"))
    elif p is not None:
        out.append(_r("backup.restore", DEGRADED, "استعادة مجهزة تنتظر إعادة التشغيل"))
    else:
        out.append(_r("backup.restore", OK, "لا استعادة معلقة"))
    return out


def collector() -> Iterator[tuple]:
    s = settings()
    items = s.catalog().list()
    st = s.catalog().state()
    ok = st.get("last_success") or {}
    yield ("backup_last_success_timestamp", "gauge", "وقت آخر نسخة ناجحة (يونكس)", {},
           float(ok.get("at") or 0))
    for kind in KINDS:
        yield ("backup_archives", "gauge", "النسخ المحفوظة محليًا حسب النوع", {"kind": kind},
               sum(1 for m in items if m.get("kind") == kind))
    yield ("backup_bytes", "gauge", "حجم النسخ المحفوظة محليًا", {},
           sum(int(m.get("size") or 0) for m in items))
    yield ("backup_offsite_configured", "gauge", "وجهة خارجية مضبوطة (1/0)", {},
           1 if s.dest is not None else 0)
    yield ("backup_restore_pending", "gauge", "استعادة مجهزة تنتظر الإقلاع (1/0)", {},
           1 if restore.pending(s.data_dir) else 0)


def install(registry=None) -> str:
    try:
        from observability import metrics as om
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.observability import metrics as om
    (registry or om.registry()).register_collector("backup", collector)
    return "النسخ: جامع المقاييس مربوط"


def summary(s: Optional[Settings] = None) -> Dict[str, Any]:
    s = s or settings()
    return {"encrypted": bool(s.key), "interval_s": s.interval_s, "keep": s.keep,
            "max_mb": s.max_bytes >> 20,
            "offsite": s.dest.name if s.dest else None, "offsite_error": s.offsite_error,
            "state": s.catalog().state(), "restore": restore_status(s)}
