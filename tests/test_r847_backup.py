# -*- coding: utf-8 -*-
"""اختبارات R-847 — النسخ الاحتياطي والاستعادة (D-062).

قبل R-847 (forensics/R-847_backup_RED.txt): لا نسخة للبيانات أصلًا. نسخ ملف
قاعدة WAL باتصال مفتوح يعطي قاعدة بلا جداول. واستعادة ملف القاعدة وحده مع
``-wal`` قديم تعيد تطبيقه بصمت (50 صفًا بدل صف النسخة). ولا فحص جاهزية
للنسخ، ولا موقع ثانٍ، و``/backups`` غير موجودة.

بعض الاختبارات هنا تسد ثغرات كشفتها الطفرات ولم تغطها الحالات المجمّدة:
M10 (تخطي بصمة العضو) وM30 (تخطي تطابق المعرّف عند الجلب). وأخرى تغطي بتر
التشفير وإعادة ترتيب قطعه.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import struct
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from backup import __main__ as bcli  # noqa: E402
from backup import api_routes as bapi, archive, crypto, offsite, restore  # noqa: E402
from backup import service as bsvc  # noqa: E402
from backup.restore import RestoreError  # noqa: E402
from backup.snapshot import BackupError  # noqa: E402
from evaluation import backup_reliability as brl, suites  # noqa: E402
from job_queue import kinds as jkinds  # noqa: E402
from job_queue.store import JobStore  # noqa: E402
from notifications import events as nev  # noqa: E402

OWNER_KEY = "test_master_key_1234567890abcdef"
H = {"X-API-Key": OWNER_KEY}
KEY = "pytest-backup-key-" + "k9" * 12


@pytest.fixture
def env(tmp_path):
    s = brl._env(tmp_path, key=KEY)
    brl._seed(s.data_dir)
    return s


# ===================================================================== التشفير
def _enc(data: bytes, chunk: int = 64) -> bytes:
    out = io.BytesIO()
    w = crypto.EncryptingWriter(out, KEY, chunk=chunk)
    w.write(data)
    w.close()
    return out.getvalue()


def _chunks(blob: bytes):
    head, rest, parts = blob[:crypto.HEADER_LEN], blob[crypto.HEADER_LEN:], []
    while rest:
        (n,) = struct.unpack(">I", rest[:4])
        parts.append(rest[:4 + n])
        rest = rest[4 + n:]
    return head, parts


def _dec(blob: bytes, key: str = KEY) -> bytes:
    return crypto.DecryptingReader(io.BytesIO(blob), key).read()


def test_crypto_roundtrip_multichunk():
    data = os.urandom(1000)
    blob = _enc(data)
    assert len(_chunks(blob)[1]) == 16 and _dec(blob) == data
    assert _dec(_enc(b"")) == b""


@pytest.mark.parametrize("mut,reason", [
    (lambda h, p: h + b"".join(p[:-1]), "truncated"),           # بتر القطعة الأخيرة
    (lambda h, p: h + b"".join([p[1], p[0]] + p[2:]), "auth_failed"),  # إعادة ترتيب
    (lambda h, p: h + b"".join(p) + b"x", "trailing_data"),
    (lambda h, p: h[:-1] + bytes([h[-1] ^ 1]) + b"".join(p), "bad_header"),
])
def test_crypto_rejects_tampering(mut, reason):
    head, parts = _chunks(_enc(os.urandom(300)))
    with pytest.raises(crypto.CryptoError) as e:
        _dec(mut(head, parts))
    assert e.value.reason in (reason, "auth_failed")
    if reason != "bad_header":
        assert e.value.reason == reason


def test_crypto_wrong_key_and_weak_key():
    with pytest.raises(crypto.CryptoError) as e:
        _dec(_enc(b"abc"), "z" * 40)
    assert e.value.reason == "auth_failed"
    with pytest.raises(crypto.CryptoError):
        crypto.check_key("short")
    fp = crypto.fingerprint(KEY)
    assert len(fp) == 16 and KEY not in fp and fp == crypto.fingerprint(KEY)


# ===================================================================== ثغرات الطفرات
def test_m10_member_sha_mismatch_detected(tmp_path):
    """بصمة الملف الخارجية سليمة لكن عضوًا لا يطابق البيان ⇒ رفض (طفرة M10)."""
    work = tmp_path / "w"
    work.mkdir()
    (work / "a.txt").write_bytes(b"real")
    man = {"format": archive.FORMAT, "backup_id": "bk-x", "created_at": 1,
           "files": [{"path": "a.txt", "size": 4, "sha256": "0" * 64}]}
    out = tmp_path / "a.svbk"
    res = archive.write(work, man, out, None)
    with pytest.raises(archive.VerifyError) as e:
        archive.verify(out, None, res["sha256"])
    assert e.value.reason == "member_sha_mismatch"


def test_m30_fetch_rejects_renamed_object(tmp_path, env):
    """كائن نسخة A مرفوع باسم B ⇒ الجلب يرفض (طفرة M30)."""
    dest = offsite.DirDestination(tmp_path / "remote")
    env.dest = dest
    a = bsvc.create("manual", "t", env)["backup_id"]
    other = "bk-20000101T000000Z-abcdef"
    (tmp_path / "remote" / f"{a}.svbk").rename(tmp_path / "remote" / f"{other}.svbk")
    s2 = brl._env(tmp_path, key=KEY, dest=dest, name="fresh")
    with pytest.raises(BackupError) as e:
        bsvc.fetch(other, s2)
    assert e.value.reason == "id_mismatch" and s2.catalog().list() == []


# ===================================================================== الإنشاء والإعداد
def test_weak_key_fails_loud_no_plaintext_fallback(tmp_path):
    s = brl._env(tmp_path, key="too-short")
    brl._plain_seed(s.data_dir)
    with pytest.raises(BackupError) as e:
        bsvc.create("manual", "t", s)
    assert e.value.reason == "weak_key" and s.catalog().list() == []
    assert [x["event"] for x in s.events] == ["backup.failed"]
    assert s.catalog().state()["last_failure"]["reason"] == "weak_key"


def test_from_env_offsite_config(monkeypatch):
    for k in ("SOVEREIGN_BACKUP_SUPABASE_URL", "SOVEREIGN_BACKUP_SUPABASE_KEY",
              "SOVEREIGN_BACKUP_SUPABASE_BUCKET", "SOVEREIGN_BACKUP_MIRROR_DIR"):
        monkeypatch.delenv(k, raising=False)
    assert bsvc.from_env().dest is None
    monkeypatch.setenv("SOVEREIGN_BACKUP_SUPABASE_URL", "https://p.supabase.co")
    s = bsvc.from_env()
    assert s.dest is None and "ناقصة" in s.offsite_error
    assert next(c for c in bsvc.checks(s) if c["check"] == "backup.offsite")["status"] == "degraded"
    monkeypatch.setenv("SOVEREIGN_BACKUP_SUPABASE_URL", "http://p.supabase.co")
    monkeypatch.setenv("SOVEREIGN_BACKUP_SUPABASE_KEY", "k")
    monkeypatch.setenv("SOVEREIGN_BACKUP_SUPABASE_BUCKET", "b")
    assert bsvc.from_env().dest is None and bsvc.from_env().offsite_error
    monkeypatch.setenv("SOVEREIGN_BACKUP_SUPABASE_URL", "https://p.supabase.co")
    assert isinstance(bsvc.from_env().dest, offsite.SupabaseStorage)
    monkeypatch.setenv("SOVEREIGN_BACKUP_INTERVAL_S", "abc")
    assert bsvc.from_env().interval_s == 21600


def test_supabase_key_not_in_errors():
    fake = brl._FakeSupabase(script=[403])
    d = offsite.SupabaseStorage("https://p.supabase.co", "sekrit-service-key", "b", transport=fake)
    with pytest.raises(offsite.OffsiteError) as e:
        d.put("bk-x.svbk", Path(__file__))
    assert e.value.kind == "auth" and "sekrit" not in str(e.value)


def test_schedule_tick_idempotent_per_period(tmp_path):
    clock = brl._Clock(t=36000.0)
    s = brl._env(tmp_path, interval=3600, clock=clock)
    store = JobStore(str(tmp_path / "q.sqlite3"))
    a, b = bsvc.schedule_tick(store, s), bsvc.schedule_tick(store, s)
    assert a["created"] and not b["created"] and a["job_id"] == b["job_id"]
    clock.t += 3600
    assert bsvc.schedule_tick(store, s)["created"]
    s.interval_s = 0
    assert bsvc.schedule_tick(store, s) is None


def test_job_kind_and_single_notification(tmp_path):
    k = jkinds.get("backup.create")
    assert k.public()["risk"] == "medium" and k.max_attempts == 1 and k.retryable == ()
    with pytest.raises(Exception):
        k.validate({"kind": "pre_restore"})  # نوع داخلي لا يُطلب من الطابور
    assert nev.from_job({"id": "j", "status": "failed", "kind": "backup.create"}) is None
    for e in ("backup.failed", "backup.offsite_failed", "restore.staged", "restore.applied"):
        assert nev.EVENTS[e][0] == "high"
    assert nev.EVENTS["restore.failed"][0] == "critical"


# ===================================================================== الاستعادة
def test_stage_idempotent_and_single_pending(env):
    bid = bsvc.create("manual", "t", env)["backup_id"]
    a = brl._stage(env, bid, "same")
    b = brl._stage(env, bid, "same")
    assert b["replayed"] and b["pre_restore_id"] == a["pre_restore_id"]
    assert sum(1 for m in env.catalog().list() if m["kind"] == "pre_restore") == 1
    with pytest.raises(RestoreError) as e:
        brl._stage(env, bid, "other")
    assert e.value.reason == "restore_pending_exists"
    assert restore.cancel(env.data_dir)["cancelled"] and restore.pending(env.data_dir) is None


def test_apply_bounded_attempts_rolls_back(env):
    bid = bsvc.create("manual", "t", env)["backup_id"]
    brl._stage(env, bid)
    p = restore.pending(env.data_dir)
    p["state"], p["attempts"] = "applying", restore.MAX_APPLY_ATTEMPTS
    (env.data_dir / ".restore" / "PENDING.json").write_text(json.dumps(p), encoding="utf-8")
    res = bsvc.apply_pending(env)
    assert res["state"] == "rolled_back" and res["reason"] == "too_many_attempts"
    assert bsvc.apply_pending(env) == {"state": "none"}


def test_rollback_failed_stays_visible(tmp_path):
    s = brl._env(tmp_path)
    brl._plain_seed(s.data_dir)
    bid = bsvc.create("manual", "t", s)["backup_id"]
    st = brl._stage(s, bid)
    (s.data_dir / ".restore" / "staged" / "a.json").write_text("x", encoding="utf-8")
    s.catalog().delete(st["pre_restore_id"])  # شبكة الأمان مفقودة ⇒ التراجع يفشل
    res = bsvc.apply_pending(s)
    assert res["state"] == "rollback_failed"
    assert restore.pending(s.data_dir)["state"] == "rollback_failed"
    chk = next(c for c in bsvc.checks(s) if c["check"] == "backup.restore")
    assert chk["status"] == "failing"
    assert bsvc.apply_pending(s)["state"] == "rollback_failed"  # لا حلقة تطبيق عمياء


def test_cli_apply_pending_none(tmp_path, capsys):
    s = brl._env(tmp_path)
    with bsvc.use_settings(s):
        assert bcli.main(["apply-pending"]) == 0
        assert bcli.main([]) == 64 and bcli.main(["nope"]) == 64
    assert '"state": "none"' in capsys.readouterr().out


def test_entrypoint_applies_before_app():
    sh = (REPO_ROOT / "scripts" / "container_entrypoint.sh").read_text(encoding="utf-8")
    assert "python3 -m backup apply-pending" in sh
    root_path = sh[sh.index('if [ "$(id -u)" = "0" ]; then\n  mkdir -p'):]
    assert root_path.index("apply_restore") < root_path.index("start_supervisor") \
        < root_path.index("exec setpriv")
    assert "apply-pending" in (REPO_ROOT / "start.sh").read_text(encoding="utf-8")


# ===================================================================== الواجهة
@pytest.fixture
def api(tmp_path, env):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    store = JobStore(str(tmp_path / "q.sqlite3"))
    app = FastAPI()
    app.include_router(bapi.make_router(owner_ok=lambda k: k == OWNER_KEY, job_store=lambda: store))
    with bsvc.use_settings(env):
        yield TestClient(app), env


def test_api_restore_flow(api):
    c, s = api
    bid = bsvc.create("manual", "t", s)["backup_id"]
    assert c.get("/backups").status_code == 401
    lst = c.get("/backups", headers=H)
    assert lst.status_code == 200 and KEY not in lst.text
    assert lst.json()["backups"][0]["backup_id"] == bid
    assert c.post(f"/backups/{bid}/verify", headers=H).json()["ok"] is True
    assert c.post("/backups/bk-bad/verify", headers=H).status_code == 404
    plan = c.post(f"/backups/{bid}/restore/plan", headers=H).json()
    body = {"plan_hash": plan["plan_hash"], "confirm": plan["confirm"]}
    assert c.post(f"/backups/{bid}/restore", headers=H, json=body).status_code == 428
    bad = c.post(f"/backups/{bid}/restore", headers={**H, "Idempotency-Key": "r"},
                 json={**body, "confirm": "yes"})
    assert bad.status_code == 422 and bad.json()["detail"]["reason"] == "confirm_mismatch"
    ok = c.post(f"/backups/{bid}/restore", headers={**H, "Idempotency-Key": "r"}, json=body)
    assert ok.status_code == 202 and ok.json()["state"] == "staged"
    again = c.post(f"/backups/{bid}/restore", headers={**H, "Idempotency-Key": "r"}, json=body)
    assert again.status_code == 200 and again.json()["replayed"]
    assert c.get("/backups/restore", headers=H).json()["pending"]["backup_id"] == bid
    assert c.delete("/backups/restore/pending", headers=H).status_code == 428
    assert c.delete("/backups/restore/pending",
                    headers={**H, "Idempotency-Key": "c"}).json()["cancelled"] is True
    assert c.get("/backups/offsite", headers=H).json()["destination"] is None


def test_suite_registered_and_green():
    s = suites.get("backup.reliability")
    assert s.floor == 1.0 and s.data_path.name == "backup_cases.json"
    r = s.runner(s.data_path)
    assert r["score"] == 1.0 and r["n"] == 23, r["failures"]


def test_app_wiring():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        assert c.get("/backups").status_code == 401
        r = c.get("/backups", headers=H)
        assert r.status_code == 200 and "settings" in r.json()
        h = c.get("/observability/health").json()
        assert {x["check"] for x in h["checks"]} >= {"backup.freshness", "backup.offsite",
                                                      "backup.restore"}
        m = c.get("/metrics", headers=H)
        assert "backup_last_success_timestamp" in m.text and "backup_offsite_configured" in m.text
