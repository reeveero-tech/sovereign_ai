# -*- coding: utf-8 -*-
"""R-852: مجموعة مجمّدة ledger.retention — احتفاظ السجل السيادي (٦.١.٤).

كل سيناريو يبني نواة معزولة (KeyRing Ed25519 مؤقت، مجلد مؤقت) ويؤرشف بمقاطع
صغيرة (8 أحداث) ليختبر عدة مقاطع. التوقعات في data/ledger_retention_cases.json
مكتوبة من القاعدة قبل أول تشغيل ومجمّدة ببصمة sha256 (suites.py).
"""
from __future__ import annotations

import base64
import gzip
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# النواة تستورد مفاتيحها من backend.sovereign.keys — نفس المسار هنا وإلا اختلفت
# هوية الأصناف (KeyStatus) فرفضت النواة المفتاح النشط (R-635)
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(1, str(REPO_ROOT / "backend"))

from backend.memory import retention as R  # noqa: E402
from backend.memory.core import SovereignCore  # noqa: E402
from backend.sovereign.keys import KeyRing  # noqa: E402

SEG = 8


class Store:
    def __init__(self):
        self.blobs: Dict[str, Dict[str, Any]] = {}

    def save_blob(self, ns, key, payload):
        self.blobs[f"{ns}/{key}"] = json.loads(json.dumps(payload))
        return True

    def list_blobs(self, ns, limit=1000, offset=0):
        return [{"key": k.split("/", 1)[1], "payload": v}
                for k, v in sorted(self.blobs.items()) if k.startswith(ns + "/")]


class Env:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.kr = KeyRing(keys_dir=tmp / "keys")
        self.kr.load_from_disk()
        self.kr.generate_new_ed25519_key(reason="R-852 eval")
        self.kr.save_to_disk()
        self.sc = tmp / "sovereign_core"
        (self.sc / "blobs").mkdir(parents=True, exist_ok=True)
        self.log = self.sc / "ledger.jsonl"
        self.adir = self.sc / "archive"
        self.manifest = self.adir / "MANIFEST.jsonl"

    def core(self, keyring=None) -> SovereignCore:
        R._ORIGIN_CACHE.clear()
        return SovereignCore(log_file=self.log, blobs_dir=self.sc / "blobs",
                             index_file=self.sc / "index.json", meta_file=self.sc / "meta.json",
                             integrity_file=self.sc / "integrity.json",
                             keyring=keyring or self.kr)

    def filled(self, n: int = 30) -> SovereignCore:
        c = self.core()
        for i in range(n):
            c.append_event("test::r852", {"n": i})
        return c

    def live_lines(self) -> List[str]:
        return [ln for ln in self.log.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def fresh_status(self) -> str:
        return self.core().verify_integrity(verbose=True).value


def s_archive_keeps_tail(env):
    r = R.archive(env.filled(), keep_last=5)
    return {"ok": r["ok"], "archived": r["archived"], "segments": r["segments_written"],
            "kept_live": r["kept_live"], "live_status": r["live_status"]}


def s_reboot_verifies(env):
    R.archive(env.filled(), keep_last=5)
    return {"status": env.fresh_status(), "live_events": len(env.live_lines())}


def s_deep_verify(env):
    c = env.filled()
    R.archive(c, keep_last=5)
    full = R.verify_integrity_full(c, deep=True)
    return {"ok": full["ok"], "events_checked": full["archive"]["events_checked"]}


def s_second_archive_continues(env):
    c = env.filled()
    R.archive(c, keep_last=5)
    for i in range(10):
        c.append_event("test::r852", {"m": i})
    r = R.archive(c, keep_last=4)
    recs, _ = R.read_manifest(env.adir)
    links = all(recs[i]["first_prev_hash"] == recs[i - 1]["last_hash"] for i in range(1, len(recs)))
    starts = [x["global_start"] for x in recs] == [sum(y["count"] for y in recs[:i])
                                                   for i in range(len(recs))]
    return {"ok": r["ok"], "links": links, "global_starts": starts,
            "archived_total": r["archive"]["archived_events"], "status": env.fresh_status()}


def s_manifest_deleted(env):
    R.archive(env.filled(), keep_last=5)
    env.manifest.unlink()
    return {"status": env.fresh_status()}


def s_manifest_edited(env):
    R.archive(env.filled(), keep_last=5)
    lines = env.manifest.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["count"] += 1
    lines[0] = json.dumps(rec, sort_keys=True)
    env.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    c = env.core()
    return {"status": c.verify_integrity(verbose=True).value,
            "error": R.verify_archive(c)["errors"][:1]}


def s_manifest_foreign_key(env):
    c = env.filled()
    R.archive(c, keep_last=5)
    other = KeyRing(keys_dir=env.tmp / "other")
    other.load_from_disk()
    other.generate_new_ed25519_key(reason="attacker")
    forger = env.core(keyring=other)
    lines = env.manifest.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[-1])
    payload = {k: rec[k] for k in R.RECORD_FIELDS}
    rec["key_id"], rec["sig"] = forger._sign_checkpoint_payload(payload)
    lines[-1] = json.dumps(rec, sort_keys=True)
    env.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    c = env.core()
    return {"status": c.verify_integrity(verbose=True).value,
            "error": R.verify_archive(c)["errors"][:1]}


def s_segment_tampered(env):
    R.archive(env.filled(), keep_last=5)
    seg = env.adir / "seg-000001.jsonl.gz"
    raw = gzip.decompress(seg.read_bytes()).replace(b"test::r852", b"test::r853", 1)
    seg.write_bytes(gzip.compress(raw, mtime=0))
    c = env.core()
    return {"status": c.verify_integrity(verbose=True).value,
            "error": R.verify_archive(c)["errors"][:1]}


def s_segment_deleted(env):
    R.archive(env.filled(), keep_last=5)
    (env.adir / "seg-000002.jsonl.gz").unlink()
    c = env.core()
    return {"status": c.verify_integrity(verbose=True).value,
            "error": R.verify_archive(c)["errors"][:1]}


def s_live_head_tampered(env):
    R.archive(env.filled(), keep_last=5)
    lines = env.live_lines()
    lines.pop(0)  # حذف أول حدث حي بعد الأصل = كسر الوصلة
    env.log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": env.fresh_status()}


def s_refuse_unverified(env):
    c = env.filled()
    with open(env.log, "ab") as fh:
        fh.write(b"{not json}\n")
    c = env.core()
    try:
        R.archive(c, keep_last=5)
        refused = False
    except R.RetentionError:
        refused = True
    return {"refused": refused, "archive_created": env.adir.exists()}


def s_refuse_no_signing_key(env):
    c = env.filled()
    c._sign_checkpoint_payload = lambda payload: None
    try:
        R.archive(c, keep_last=5)
        refused = False
    except R.RetentionError:
        refused = True
    return {"refused": refused, "archive_created": env.adir.exists(),
            "live_events": len(env.live_lines())}


def s_keep_last_bounds(env):
    c = env.filled()
    rejected = []
    for bad in (0, -1, 10_000_001, "5"):
        try:
            R.archive(c, keep_last=bad)
            rejected.append(False)
        except R.RetentionError:
            rejected.append(True)
    plan = R.archive(c, keep_last=10, dry_run=True)
    return {"rejected": rejected, "would_archive": plan["would_archive"],
            "dry_run_changed": env.adir.exists() or len(env.live_lines()) != 30}


def s_nothing_to_archive(env):
    r = R.archive(env.filled(10), keep_last=50)
    return {"archived": r["archived"], "manifest": env.manifest.exists(),
            "live_events": len(env.live_lines())}


def s_pending_recovery(env):
    c = env.filled()
    real = R._fsync_write

    def crash_on_ledger(path, data):
        if Path(path) == env.log:
            raise OSError("simulated crash before live rewrite")
        return real(path, data)
    R._fsync_write = crash_on_ledger
    try:
        try:
            R.archive(c, keep_last=5)
        except OSError:  # TOLERATED (R-852): الانقطاع المحاكى هو المقصود
            pass
    finally:
        R._fsync_write = real
    mid = len(env.live_lines())
    c2 = env.core()  # الإقلاع يستكمل
    return {"lines_after_crash": mid, "live_after_boot": len(env.live_lines()),
            "status": c2.verify_integrity(verbose=True).value}


def s_anchor_indices_preserved(env):
    from backend.sovereign.ledger import LedgerAnchor
    c = env.filled()
    a = LedgerAnchor(ledger_path=env.log, anchors_path=env.sc / "anchors.jsonl")
    before = a.read_ledger_lines()
    R.archive(c, keep_last=5)
    after = a.read_ledger_lines()
    return {"prefix_identical": after[:len(before)] == before,
            "count_after": len(after), "live_only": len(env.live_lines())}


def s_durable_mirror(env):
    store = Store()
    c = env.filled()
    r = R.archive(c, keep_last=5, store=store)
    ok = R.verify_durable(c, store)
    key = sorted(store.blobs)[1]
    gz = base64.b64decode(store.blobs[key]["gz_b64"])
    store.blobs[key]["gz_b64"] = base64.b64encode(gz[:-1] + bytes([gz[-1] ^ 1])).decode()
    bad = R.verify_durable(c, store)
    return {"pushed": r["durable"]["pushed"], "failed": r["durable"]["failed"],
            "verified": ok["ok"], "tamper_detected": not bad["ok"],
            "error": next(iter(bad["epochs"].values()))["error"]}


def s_blobs_retained(env):
    c = env.filled()
    R.archive(c, keep_last=5)
    first = json.loads(next(R.iter_archived_lines(env.log)))
    return {"payload": c.get_payload(first)}


def s_audit_event(env):
    c = env.filled()
    r = R.archive(c, keep_last=5)
    last = json.loads(env.live_lines()[-1])
    pl = c.get_payload(last)
    return {"type": last["type"], "archived": pl.get("archived"),
            "segments": len(pl.get("segments", [])), "origin_match": pl.get("origin") == r["origin"]}


def s_status_shape(env):
    c = env.filled()
    s0 = R.status(c)
    R.archive(c, keep_last=5)
    s1 = R.status(c)
    return {"before": [s0["archive"]["segments"], s0["archive"]["origin"]],
            "after_segments": s1["archive"]["segments"], "after_ok": s1["archive"]["ok"],
            "archived_events": s1["archive"]["archived_events"], "auto": s1["auto"],
            "live_events": s1["live_events"]}


SCENARIOS = {f.__name__[2:]: f for f in (
    s_archive_keeps_tail, s_reboot_verifies, s_deep_verify, s_second_archive_continues,
    s_manifest_deleted, s_manifest_edited, s_manifest_foreign_key, s_segment_tampered,
    s_segment_deleted, s_live_head_tampered, s_refuse_unverified, s_refuse_no_signing_key,
    s_keep_last_bounds, s_nothing_to_archive, s_pending_recovery, s_anchor_indices_preserved,
    s_durable_mirror, s_blobs_retained, s_audit_event, s_status_shape)}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r852-e-"))
    old_seg = R.SEGMENT_MAX_EVENTS
    R.SEGMENT_MAX_EVENTS = SEG
    level = logging.getLogger().level
    logging.disable(logging.CRITICAL)
    try:
        try:
            got = SCENARIOS[case["scenario"]](Env(tmp))
        except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
            got = {"error": f"{type(exc).__name__}: {exc}"}
        failed = [{"check": k, "want": v, "got": got.get(k)}
                  for k, v in case["expect"].items() if got.get(k) != v]
        return {"id": case["id"], "rule": case["rule"], "pass": not failed,
                "got": got, "failed_checks": failed}
    finally:
        logging.disable(logging.NOTSET)
        logging.getLogger().setLevel(level)
        R.SEGMENT_MAX_EVENTS = old_seg
        R._ORIGIN_CACHE.clear()
        shutil.rmtree(tmp, ignore_errors=True)


def run(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [run_case(c) for c in cases]
    passed = sum(r["pass"] for r in results)
    return {"score": round(passed / len(results), 4) if results else 0.0,
            "passed": passed, "n": len(results),
            "failures": [r for r in results if not r["pass"]]}
