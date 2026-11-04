# -*- coding: utf-8 -*-
"""R-847: مجموعة موثوقية النسخ والاستعادة — سيناريوهات فوق المكونات الحقيقية.

المزيف هنا: الوجهة الخارجية (نقل Supabase مزيف يحفظ الكائنات في ذاكرة،
أو مجلد مرآة)، والساعة، وانهيار العملية (``BaseException`` من خطاف التقدم).
أما اللقطة والتشفير والأرشيف والتحقق والفهرس والاحتفاظ والقفل والتجهيز
والتطبيق والتراجع والفحوص وواجهة ``/backups`` والطابور فكلها حقيقية. وكل
حالة تعمل في مجلد مؤقت خاص بإعدادات معزولة (``use_settings``)، ولا تلمس
البيئة.

الحلقات بأعداد ثابتة لا مشتقة من الثوابت المختبرة (درس R-846 O05). وكل
سيناريو يصل فعلًا إلى المسار الذي يقيسه (درس O13). والقيم تُقارن بدقة، لا بحث
عن سلسلة في نص كبير (درس O03).
"""
from __future__ import annotations

import gzip
import io
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List

try:
    from backup import api_routes as bapi, archive, offsite, restore
    from backup import service as bsvc
    from backup.restore import RestoreError
    from backup.snapshot import BackupError, sha256_file
    from job_queue import kinds as jkinds
    from job_queue.store import JobStore
    from job_queue.worker import Worker
    from notifications import events as nev
    from notifications.store import OutboxStore
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.backup import api_routes as bapi, archive, offsite, restore
    from backend.backup import service as bsvc
    from backend.backup.restore import RestoreError
    from backend.backup.snapshot import BackupError, sha256_file
    from backend.job_queue import kinds as jkinds
    from backend.job_queue.store import JobStore
    from backend.job_queue.worker import Worker
    from backend.notifications import events as nev
    from backend.notifications.store import OutboxStore

KEY = "backup-suite-key-" + "q7" * 12
OWNER = "owner-key-for-backup-suite"
MARKER = "SECRET-MARKER-R847-" + "zx" * 8


# ===================================================================== أدوات
class _Clock:
    def __init__(self, t: float = 1_793_800_000.0, step: float = 0.0):
        self.t, self.step = t, step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def _env(tmp: Path, key=None, dest=None, keep=7, max_bytes=64 << 20, interval=21600,
         clock=None, name="data") -> bsvc.Settings:
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    events: List[Dict[str, Any]] = []
    s = bsvc.Settings(data_dir=d, root=d / "backups", key=key, interval_s=interval, keep=keep,
                      max_bytes=max_bytes, dest=dest, notify=events.append,
                      sleep=lambda _x: None, clock=clock or _Clock(step=1.0))
    s.events = events  # type: ignore[attr-defined]
    return s


def _seed(d: Path) -> None:
    (d / "keys").mkdir(exist_ok=True)
    (d / "keys" / "k.json").write_text('{"k": "v"}', encoding="utf-8")
    (d / "conf.json").write_text('{"a": 1}', encoding="utf-8")
    (d / "events.jsonl").write_text('{"e": 1}\n{"e": 2}\n', encoding="utf-8")
    c = sqlite3.connect(d / "state.sqlite3")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE t (v TEXT)")
    c.execute("INSERT INTO t VALUES ('قديم')")
    c.commit()
    c.close()


def _manifest(s: bsvc.Settings, bid: str, extract_to=None) -> Dict[str, Any]:
    cat = s.catalog()
    return archive.verify(cat.archive(bid), s.key, cat.get(bid)["sha256"], extract_to)["manifest"]


def _mapping(man: Dict[str, Any]) -> Dict[str, str]:
    return {f["path"]: f["sha256"] for f in man["files"]}


def _tree(s: bsvc.Settings) -> Dict[str, str]:
    return restore.tree_map(s.data_dir, s.excluded_tops)


def _stage(s: bsvc.Settings, bid: str, idem: str = "idem-1") -> Dict[str, Any]:
    p = bsvc.plan(bid, s)
    return bsvc.stage(bid, p["plan_hash"], f"RESTORE {bid}", "suite", idem, s)


class _FakeSupabase:
    """نقل مزيف بمخزن كائنات في الذاكرة وسلسلة ردود مبرمجة للرفع."""

    def __init__(self, script=None):
        self.objects: Dict[str, bytes] = {}
        self.script = list(script or [])
        self.calls: List[str] = []

    def __call__(self, method, url, headers, body):
        self.calls.append(method)
        if method == "POST" and "/object/list/" in url:
            return 200, json.dumps([{"name": n, "metadata": {"size": len(b)}}
                                    for n, b in self.objects.items()]).encode()
        name = url.rsplit("/", 1)[-1]
        if method == "POST":
            if self.script:
                st = self.script.pop(0)
                if st != 200:
                    return st, b'{"error":"scripted"}'
            if name in self.objects:
                return 400, b'{"statusCode":"409","error":"Duplicate","message":"The resource already exists"}'
            self.objects[name] = body.read() if hasattr(body, "read") else bytes(body)
            return 200, b'{"Key":"ok"}'
        if method == "GET":
            if name not in self.objects:
                return 404, b'{"error":"not_found"}'
            return 200, self.objects[name]
        return 405, b""


def _supabase(fake: _FakeSupabase) -> offsite.SupabaseStorage:
    return offsite.SupabaseStorage("https://proj.supabase.co", "service-key-xyz", "bk",
                                   transport=fake)


# ===================================================================== اللقطة
def s_sqlite_wal_consistent(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp)
    (s.data_dir / "notifications").mkdir()
    ob = OutboxStore(str(s.data_dir / "notifications" / "outbox.sqlite3"))
    for i in range(5):
        ob.emit(nev.make("job.dead", f"k{i}", "s", "x"), [("webhook", "pending", "")])
    wal = s.data_dir / "notifications" / "outbox.sqlite3-wal"
    assert wal.exists() and wal.stat().st_size > 0, "الاتصال المفتوح يجب أن يبقي الصفوف في WAL"
    meta = bsvc.create("manual", "suite", s)
    x = tmp / "x"
    man = _manifest(s, meta["backup_id"], x)
    c = sqlite3.connect(x / "notifications" / "outbox.sqlite3")
    try:
        rows = c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        integ = c.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        c.close()
    return {"rows": rows, "integrity": integ,
            "wal_in_archive": sum(1 for f in man["files"]
                                  if f["path"].endswith(("-wal", "-shm")))}


def s_jsonl_torn_tail(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp)
    (s.data_dir / "log.jsonl").write_bytes(b'{"n": 1}\n{"n": 2}\n{"n": 3}\n{"n": 4, "par')
    meta = bsvc.create("manual", "suite", s)
    x = tmp / "x"
    _manifest(s, meta["backup_id"], x)
    lines = (x / "log.jsonl").read_text(encoding="utf-8").splitlines()
    ok = True
    for ln in lines:
        try:
            json.loads(ln)
        except ValueError:
            ok = False
    return {"lines": len(lines), "all_parse": ok, "tail_dropped": meta["torn_tails"] == 1}


def s_manifest_hashes(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp)
    _seed(s.data_dir)
    meta = bsvc.create("manual", "suite", s)
    x = tmp / "x"
    man = _manifest(s, meta["backup_id"], x)
    match = all(sha256_file(x.joinpath(*f["path"].split("/"))) == f["sha256"]
                and (x.joinpath(*f["path"].split("/"))).stat().st_size == f["size"]
                for f in man["files"])
    with tarfile.open(s.catalog().archive(meta["backup_id"]), "r:gz") as tf:
        first = tf.next().name
    return {"all_match": match, "manifest_first": first == archive.MANIFEST,
            "files_ok": sorted(_mapping(man)) == ["conf.json", "events.jsonl", "keys/k.json",
                                                  "state.sqlite3"]}


def s_excludes(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp)
    _seed(s.data_dir)
    bsvc.create("manual", "suite", s)  # يملأ backups/ نفسه
    (s.data_dir / ".restore").mkdir()
    (s.data_dir / ".restore" / "x.json").write_text("{}")
    (s.data_dir / "orphan.sqlite3-wal").write_bytes(b"w" * 64)
    os.symlink(s.data_dir / "conf.json", s.data_dir / "link.json")
    meta = bsvc.create("manual", "suite", s)
    man = _manifest(s, meta["backup_id"])
    paths = [f["path"] for f in man["files"]]
    return {"self_included": any(p.startswith("backups/") for p in paths),
            "restore_dir_included": any(p.startswith(".restore/") for p in paths)
            or any(p.endswith("-wal") for p in paths),
            "symlink_skipped": {"path": "link.json", "reason": "symlink"} in man["skipped"]}


def _flip(src: Path, dst: Path) -> None:
    raw = bytearray(src.read_bytes())
    raw[len(raw) // 2] ^= 0x01
    dst.write_bytes(bytes(raw))


def _verifies(path: Path, key, sha=None) -> bool:
    try:
        archive.verify(path, key, sha)
        return True
    except archive.VerifyError:
        return False


def s_tamper_detected(tmp: Path) -> Dict[str, Any]:
    plain, enc = _env(tmp, name="p"), _env(tmp, key=KEY, name="e")
    for s in (plain, enc):
        _seed(s.data_dir)
        (s.data_dir / "big.bin").write_bytes(os.urandom(200_000))
    mp = bsvc.create("manual", "suite", plain)
    me = bsvc.create("manual", "suite", enc)
    pa, ea = plain.catalog().archive(mp["backup_id"]), enc.catalog().archive(me["backup_id"])
    _flip(pa, tmp / "p.bad")
    _flip(ea, tmp / "e.bad")
    return {"plain_ok": _verifies(tmp / "p.bad", None, mp["sha256"]),
            # المشفر بلا بصمة الفهرس: وسم GCM وحده يكشف العبث
            "encrypted_ok": _verifies(tmp / "e.bad", KEY, None),
            "untampered_ok": _verifies(pa, None, mp["sha256"]) and _verifies(ea, KEY, None)}


def _evil(path: Path, member: tarfile.TarInfo, payload: bytes) -> None:
    man = {"format": archive.FORMAT, "backup_id": "bk-evil", "created_at": 0,
           "files": [{"path": "ok.txt", "sha256": "0" * 64, "size": len(payload)}]}
    raw = json.dumps(man).encode()
    with tarfile.open(path, "w:gz", format=tarfile.PAX_FORMAT) as tf:
        ti = tarfile.TarInfo(archive.MANIFEST)
        ti.size = len(raw)
        tf.addfile(ti, io.BytesIO(raw))
        if member.isreg():
            member.size = len(payload)
            tf.addfile(member, io.BytesIO(payload))
        else:
            tf.addfile(member)


def s_path_traversal_rejected(tmp: Path) -> Dict[str, Any]:
    outside = tmp / "outside"
    stage = tmp / "stage" / "x"
    stage.mkdir(parents=True)
    out: Dict[str, Any] = {}
    dot = tarfile.TarInfo("data/../../evil.txt")
    absm = tarfile.TarInfo(str(outside / "evil_abs.txt"))
    link = tarfile.TarInfo("data/ok.txt")
    link.type, link.linkname = tarfile.SYMTYPE, "/etc/passwd"
    for label, m in (("dotdot", dot), ("absolute", absm), ("symlink", link)):
        p = tmp / f"{label}.tgz"
        _evil(p, m, b"pwned")
        try:
            archive.verify(p, None, None, extract_to=stage)
            out[f"{label}_rejected"] = False
        except archive.VerifyError as exc:
            out[f"{label}_rejected"] = exc.reason == "unsafe_member"
    written = [p for p in stage.rglob("*")] + [p for p in (tmp / "evil.txt",
                                                            tmp / "stage" / "evil.txt",
                                                            outside / "evil_abs.txt")
                                               if p.exists()]
    out["outside_written"] = bool(written)
    return out


def _maybe_gunzip(raw: bytes) -> bytes:
    try:
        return gzip.decompress(raw)
    except (OSError, EOFError):  # TOLERATED: ليس gzip (مشفر) ⇒ نبحث في البايتات الخام
        return raw


def s_encryption_at_rest(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp, key=KEY)
    (s.data_dir / "vault.json").write_text(json.dumps({"secret": MARKER}), encoding="utf-8")
    meta = bsvc.create("manual", "suite", s)
    path = s.catalog().archive(meta["backup_id"])
    found = MARKER.encode() in _maybe_gunzip(path.read_bytes())
    side = s.catalog().sidecar(meta["backup_id"]).read_text(encoding="utf-8")
    state = s.catalog().state_path.read_text(encoding="utf-8")
    return {"plaintext_found": found, "wrong_key_ok": _verifies(path, "w" * 40, None),
            "right_key_ok": _verifies(path, KEY, meta["sha256"]),
            "key_in_sidecar": KEY in side or KEY in state}


# ===================================================================== الخارج
def s_offsite_requires_encryption(tmp: Path) -> Dict[str, Any]:
    dest = offsite.DirDestination(tmp / "remote")
    s = _env(tmp, key=None, dest=dest)
    _seed(s.data_dir)
    meta = bsvc.create("manual", "suite", s)
    st = meta["offsite"]["status"]
    return {"uploaded": st == "uploaded", "refused": st == "refused",
            "remote_objects": len(dest.list())}


def s_offsite_auth_no_blind_retry(tmp: Path) -> Dict[str, Any]:
    fake = _FakeSupabase(script=[401, 401, 401, 401])
    s = _env(tmp, key=KEY, dest=_supabase(fake))
    _seed(s.data_dir)
    meta = bsvc.create("manual", "suite", s)
    return {"attempts": fake.calls.count("POST"), "status": meta["offsite"]["status"],
            "notified": [e["event"] for e in s.events] == ["backup.offsite_failed"]}


def s_offsite_transient_retry(tmp: Path) -> Dict[str, Any]:
    fake = _FakeSupabase(script=[503, 503, 200])
    s = _env(tmp, key=KEY, dest=_supabase(fake))
    _seed(s.data_dir)
    meta = bsvc.create("manual", "suite", s)
    return {"attempts": fake.calls.count("POST"),
            "uploaded": meta["offsite"]["status"] == "uploaded" and len(fake.objects) == 1}


def s_offsite_idempotent(tmp: Path) -> Dict[str, Any]:
    fake = _FakeSupabase()
    dest = _supabase(fake)
    s = _env(tmp, key=KEY, dest=dest)
    _seed(s.data_dir)
    meta = bsvc.create("manual", "suite", s)
    again = offsite.push(dest, meta["backup_id"], s.catalog().archive(meta["backup_id"]),
                         True, s.sleep)
    return {"remote_objects": len(dest.list()), "second_status": again["status"]}


def s_retention(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp, keep=3, clock=_Clock(step=10.0))
    _seed(s.data_dir)
    pre = bsvc.create("pre_restore", "suite", s)
    ids = [bsvc.create("manual", "suite", s)["backup_id"] for _ in range(6)]
    items = s.catalog().list()
    regular = [m["backup_id"] for m in items if m["kind"] != "pre_restore"]
    return {"kept": len(regular), "newest_kept": ids[-1] in regular and regular == ids[:-4:-1],
            "pre_restore_kept": s.catalog().get(pre["backup_id"]) is not None}


# ===================================================================== الاستعادة
def s_restore_requires_plan_and_confirm(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp)
    _seed(s.data_dir)
    bid = bsvc.create("manual", "suite", s)["backup_id"]
    good = bsvc.plan(bid, s)["plan_hash"]
    out: Dict[str, Any] = {}
    for label, ph, conf in (("wrong_plan", "0" * 64, f"RESTORE {bid}"),
                            ("wrong_confirm", good, "RESTORE")):
        try:
            bsvc.stage(bid, ph, conf, "suite", f"k-{label}", s)
            out[label] = "accepted"
        except RestoreError as exc:
            out[label] = exc.reason
    out["staged"] = (restore.pending(s.data_dir) is not None
                     or (s.data_dir / ".restore").exists()
                     or any(m["kind"] == "pre_restore" for m in s.catalog().list()))
    return out


def s_restore_roundtrip(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp, key=KEY)
    _seed(s.data_dir)
    bid = bsvc.create("manual", "suite", s)["backup_id"]
    want = _mapping(_manifest(s, bid))
    (s.data_dir / "conf.json").write_text('{"a": 2}', encoding="utf-8")
    (s.data_dir / "events.jsonl").unlink()
    (s.data_dir / "extra.txt").write_text("زائد", encoding="utf-8")
    c = sqlite3.connect(s.data_dir / "state.sqlite3")
    c.execute("INSERT INTO t VALUES ('جديد')")
    c.commit()
    c.close()
    _stage(s, bid)
    res = bsvc.apply_pending(s)
    return {"equal": _tree(s) == want,
            "extra_displaced": (s.data_dir / ".restore" / "displaced" / bid / "extra.txt").exists(),
            "extra_in_place": (s.data_dir / "extra.txt").exists(), "state": res["state"]}


def s_restore_stale_wal(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp)
    _seed(s.data_dir)
    bid = bsvc.create("manual", "suite", s)["backup_id"]
    db = s.data_dir / "state.sqlite3"
    c = sqlite3.connect(db)
    c.execute("PRAGMA wal_autocheckpoint=0")
    c.execute("DELETE FROM t")
    c.executemany("INSERT INTO t VALUES (?)", [("جديد",)] * 49)
    c.commit()
    held = tmp / "held.wal"
    shutil.copyfile(str(db) + "-wal", held)
    c.close()
    _stage(s, bid)
    shutil.copyfile(held, str(db) + "-wal")  # WAL قديم باقٍ كما بعد انهيار
    bsvc.apply_pending(s)
    c = sqlite3.connect(db)
    try:
        rows = c.execute("SELECT v FROM t").fetchall()
    finally:
        c.close()
    return {"rows": len(rows), "value": rows[0][0] if rows else None}


class _Crash(BaseException):
    """محاكاة موت العملية — لا يلتقطها ``except Exception``."""


def s_restore_crash_resume(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp)
    _seed(s.data_dir)
    bid = bsvc.create("manual", "suite", s)["backup_id"]
    want = _mapping(_manifest(s, bid))
    for p in ("conf.json", "keys/k.json"):
        (s.data_dir / p).write_text('{"changed": true}', encoding="utf-8")
    _stage(s, bid)

    def boom(n: int) -> None:
        if n == 1:
            raise _Crash()
    try:
        bsvc.apply_pending(s, progress=boom)
    except _Crash:  # TOLERATED: الانهيار المحاكى مقصود — الحالة تُفحص بعده
        pass
    first = (restore.pending(s.data_dir) or {}).get("state")
    res = bsvc.apply_pending(s)
    return {"first_state": first, "final_state": res["state"], "equal": _tree(s) == want}


def _plain_seed(d: Path) -> None:
    (d / "a.json").write_text('{"v": 1}', encoding="utf-8")
    (d / "b.txt").write_text("ب", encoding="utf-8")
    (d / "log.jsonl").write_text('{"l": 1}\n', encoding="utf-8")


def s_restore_verify_fail_rollback(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp)
    _plain_seed(s.data_dir)
    bid = bsvc.create("manual", "suite", s)["backup_id"]
    (s.data_dir / "a.json").write_text('{"v": "قبل الاستعادة"}', encoding="utf-8")
    (s.data_dir / "c.txt").write_text("جديد", encoding="utf-8")
    pre_map = _tree(s)
    _stage(s, bid)
    (s.data_dir / ".restore" / "staged" / "a.json").write_text("تالف", encoding="utf-8")
    res = bsvc.apply_pending(s)
    names = [e["event"] for e in s.events if e["event"].startswith("restore.")]
    return {"state": res["state"], "equal_pre": _tree(s) == pre_map,
            "notified": names[-1] if names else None}


def s_pre_restore_snapshot_taken(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp, key=KEY)
    _seed(s.data_dir)
    bid = bsvc.create("manual", "suite", s)["backup_id"]
    st = _stage(s, bid)
    meta = s.catalog().get(st["pre_restore_id"]) or {}
    return {"pre_restore_exists": bool(meta), "kind": meta.get("kind"),
            "verifies": bsvc.verify(st["pre_restore_id"], s)["ok"]}


def _status(checks: List[Dict[str, str]], name: str) -> str:
    return next(c["status"] for c in checks if c["check"] == name)


def s_health_backup(tmp: Path) -> Dict[str, Any]:
    clock = _Clock(step=0.0)
    s = _env(tmp, interval=3600, clock=clock)
    _plain_seed(s.data_dir)
    bid = bsvc.create("manual", "suite", s)["backup_id"]
    t0 = clock.t
    fresh = _status(bsvc.checks(s, now=t0 + 100), "backup.freshness")
    stale = _status(bsvc.checks(s, now=t0 + 3 * 3600), "backup.freshness")
    _stage(s, bid)
    (s.data_dir / ".restore" / "staged" / "a.json").write_text("تالف", encoding="utf-8")
    bsvc.apply_pending(s)  # يتراجع فعلًا ⇒ LAST.json rolled_back
    failed = _status(bsvc.checks(s, now=t0 + 200), "backup.restore")
    return {"fresh": fresh, "stale": stale, "restore_failed": failed}


def s_api_job_kind(tmp: Path) -> Dict[str, Any]:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    k = jkinds.KINDS.get("backup.create")
    registered = bool(k and k.description and k.risk in ("low", "medium", "high")
                      and k.risk_reason and k.payload_schema.get("type") == "object")
    s = _env(tmp)
    _plain_seed(s.data_dir)
    store = JobStore(str(tmp / "queue.sqlite3"))
    app = FastAPI()
    app.include_router(bapi.make_router(owner_ok=lambda key: key == OWNER,
                                        job_store=lambda: store))
    c = TestClient(app)
    with bsvc.use_settings(s):
        no_key = c.post("/backups", headers={"X-API-Key": OWNER}).status_code
        no_owner = c.post("/backups", headers={"X-API-Key": "x", "Idempotency-Key": "a"}).status_code
        r = c.post("/backups", headers={"X-API-Key": OWNER, "Idempotency-Key": "a"})
        out = Worker(store, registry=jkinds.KINDS).run_once() or {}
    return {"kind_registered": registered, "no_key": no_key, "with_key": r.status_code,
            "no_owner": no_owner,
            "backup_created": out.get("status") == "succeeded" and len(s.catalog().list()) == 1}


def s_disaster_recovery(tmp: Path) -> Dict[str, Any]:
    dest = offsite.DirDestination(tmp / "remote")
    s = _env(tmp, key=KEY, dest=dest)
    _seed(s.data_dir)
    meta = bsvc.create("manual", "suite", s)
    want = _mapping(_manifest(s, meta["backup_id"]))
    s2 = _env(tmp, key=KEY, dest=dest, name="fresh")  # حجم جديد فارغ
    fetched = bsvc.fetch(meta["backup_id"], s2)
    _stage(s2, meta["backup_id"])
    bsvc.apply_pending(s2)
    return {"fetched": fetched["kind"] == "fetched" and fetched["sha256"] == meta["sha256"],
            "equal": _tree(s2) == want}


def s_size_cap(tmp: Path) -> Dict[str, Any]:
    s = _env(tmp, max_bytes=4096)
    (s.data_dir / "a.bin").write_bytes(b"a" * 3000)
    (s.data_dir / "b.bin").write_bytes(b"b" * 3000)
    try:
        bsvc.create("manual", "suite", s)
        refused, reason = False, ""
    except BackupError as exc:
        refused, reason = True, exc.reason
    root = s.root
    left = [p for p in root.iterdir() if p.name.endswith((".svbk", ".part"))
            or p.name.startswith("bk-")] + list((root / ".work").iterdir())
    return {"refused": refused, "reason": reason, "leftovers": len(left)}


class _BlockingDir(offsite.DirDestination):
    def __init__(self, root: Path):
        super().__init__(root)
        self.entered, self.release = threading.Event(), threading.Event()

    def put(self, obj: str, path: Path) -> str:
        self.entered.set()
        self.release.wait(20)
        return super().put(obj, path)


def s_concurrent_lock(tmp: Path) -> Dict[str, Any]:
    dest = _BlockingDir(tmp / "remote")
    s = _env(tmp, key=KEY, dest=dest)
    _plain_seed(s.data_dir)
    errs: List[str] = []
    t = threading.Thread(target=lambda: bsvc.create("manual", "a", s), daemon=True)
    t.start()
    dest.entered.wait(20)
    busy = 0
    try:
        bsvc.create("manual", "b", s)
    except BackupError as exc:
        busy = 1 if exc.reason == "busy" else 0
        errs.append(exc.reason)
    dest.release.set()
    t.join(30)
    return {"created": len(s.catalog().list()), "busy": busy}


SCENARIOS = {f.__name__[2:]: f for f in (
    s_sqlite_wal_consistent, s_jsonl_torn_tail, s_manifest_hashes, s_excludes,
    s_tamper_detected, s_path_traversal_rejected, s_encryption_at_rest,
    s_offsite_requires_encryption, s_offsite_auth_no_blind_retry, s_offsite_transient_retry,
    s_offsite_idempotent, s_retention, s_restore_requires_plan_and_confirm,
    s_restore_roundtrip, s_restore_stale_wal, s_restore_crash_resume,
    s_restore_verify_fail_rollback, s_pre_restore_snapshot_taken, s_health_backup,
    s_api_job_kind, s_disaster_recovery, s_size_cap, s_concurrent_lock)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r847-b-"))
    try:
        try:
            got = SCENARIOS[case["scenario"]](tmp)
        except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
            got = {"error": f"{type(exc).__name__}: {exc}"}
        exp = case["expect"]
        failed = [{"check": k, "want": v, "got": got.get(k)}
                  for k, v in exp.items() if got.get(k) != v]
        return {"id": case["id"], "rule": case["rule"], "pass": not failed,
                "got": got, "failed_checks": failed}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [run_case(c) for c in cases]
    passed = sum(r["pass"] for r in results)
    return {"score": round(passed / len(results), 4) if results else 0.0,
            "passed": passed, "n": len(results),
            "failures": [r for r in results if not r["pass"]]}
