"""R-852 (٦.١.٤ / D-067): احتفاظ السجل السيادي — أرشفة البادئة القديمة دون كسر السلسلة.

المشكلة (RED — forensics/R-852_ledger_retention_RED.txt): السجل ``ledger.jsonl`` ينمو
بلا حد (الإنتاج ~3.5 حدث/ث) وكل مسار ساخن (الإقلاع، المطابقة، التحقق) خطي في حجمه؛
وأصل السلسلة مثبت على ``GENESIS`` فأي اقتطاع للبادئة = CORRUPTED، والمراسي (R-641)
بفهارس مطلقة تنكسر.

الحل: البادئة المتحقق منها تُنقل إلى مقاطع مضغوطة ``archive/seg-NNNNNN.jsonl.gz``
بأسطرها كما هي بايتًا ببايت، ويُلحق لكل مقطع سجل في ``archive/MANIFEST.jsonl``
موقّع بمفتاح KeyRing النشط (نفس توقيع نقاط التفتيش R-783a) ومتسلسل
(``prev_manifest`` = sha256 للسجل السابق). آخر سجل صالح هو «أصل» السلسلة الحية:
``SovereignCore`` يبدأ التحقق منه بدل ``GENESIS``. أي عبث بالبيان (حذفه، تعديله،
توقيع مزور، مقطع ناقص) ⇒ أصل غير صالح ⇒ CORRUPTED (فشل مغلق، لا ثقة عمياء).

ما لا يفعله (صدقًا): لا يحذف الـblobs (الحمولة تبقى قابلة للقراءة محليًا)، ولا
يؤرشف إلا ما سبق التحقق منه (بادئة R-768 المبصومة)، ولا يعمل تلقائيًا — بطلب
المالك عبر ``POST /ledger/retention/archive``. النسخة الدائمة (Supabase) مرآة
لإثبات السلسلة (تجزئات + توقيعات) لا للحمولة.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import hmac as _hmac
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

ARCHIVE_DIRNAME = "archive"
MANIFEST_NAME = "MANIFEST.jsonl"
SEGMENT_MAX_EVENTS = 5000          # ~2MB خام / ~0.4MB مضغوط — يتسع لصف المخزن الدائم
DURABLE_NAMESPACE = "ledger_archive"
MANIFEST_VERSION = 1
KEEP_LAST_MIN = 1
KEEP_LAST_MAX = 10_000_000
RECORD_FIELDS = ("v", "seq", "epoch", "segment", "count", "global_start",
                 "first_hash", "first_prev_hash", "last_hash", "sha256_raw",
                 "sha256_gz", "prev_manifest", "created_at")


class RetentionError(RuntimeError):
    """رفض أرشفة صريح (سبب مقروء) — لا تغيير على القرص."""


def archive_dir_for(log_file: Path) -> Path:
    return Path(log_file).parent / ARCHIVE_DIRNAME


def _canon(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _core_module(core):
    return sys.modules[type(core).__module__]


# ------------------------------------------------------------------ قراءة البيان
def read_manifest(adir: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    """السجلات كما هي + أخطاء البنية (سطر غير JSON يُبلّغ ولا يُتخطى بصمت)."""
    path = Path(adir) / MANIFEST_NAME
    if not path.exists():
        return [], []
    records, errors = [], []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            errors.append(f"manifest_line_{n}_malformed")
            continue
        if not isinstance(rec, dict):
            errors.append(f"manifest_line_{n}_not_object")
            continue
        records.append(rec)
    return records, errors


def _record_payload(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {k: rec.get(k) for k in RECORD_FIELDS}


def _verify_event_line(core, event: Dict[str, Any]) -> bool:
    """توقيع حدث واحد بنفس قواعد ``_verify_walk`` (ed25519 / KeyRing HMAC / تاريخي)."""
    data = (f"{event['hash']}|{event['prev_hash']}|{event['blob']}|"
            f"{event['time']}|{event['type']}")
    if "key_id" in event:
        if event.get("sig_type") == "ed25519":
            try:
                from backend.sovereign.keys import ed25519_verifier as _ed
            except ImportError:  # TOLERATED (R-852): نمط الاستيراد المزدوج القائم
                from sovereign.keys import ed25519_verifier as _ed
            rec = core._keyring.get_key(event["key_id"]) if core._keyring else None
            if rec is None or getattr(rec, "key_type", "hmac") != "ed25519":
                return False
            return bool(_ed.verify_hex(rec.public_key,
                                       f"{data}|{event.get('key_id', '')}".encode("utf-8"),
                                       event["signature"]))
        try:
            expected = core._compute_event_signature(
                event["hash"], event["prev_hash"], event["blob"], event["time"],
                event["type"], key_id=event.get("key_id"))
        except Exception:  # TOLERATED (R-852): مفتاح غائب = توقيع غير متحقق (فشل مغلق)
            return False
        return _hmac.compare_digest(event["signature"], expected)
    if core.signing_key is None:
        return False
    expected = _hmac.new(core.signing_key, data.encode("utf-8"), hashlib.sha256).hexdigest()
    return _hmac.compare_digest(event["signature"], expected)


def _segment_lines(raw: bytes) -> List[bytes]:
    return [ln for ln in raw.split(b"\n") if ln.strip()]


def verify_archive(core, adir: Optional[Path] = None, deep: bool = False) -> Dict[str, Any]:
    """تحقق البيان والمقاطع. ``deep`` يعيد حساب تجزئة وتوقيع كل حدث مؤرشف.

    يعيد ``origin`` = آخر تجزئة مؤرشفة (أو GENESIS بلا أرشيف)، و ``ok=False``
    مع ``errors`` عند أي خلل — المستدعي (النواة) يعامل ذلك كفساد.
    """
    adir = Path(adir) if adir is not None else archive_dir_for(core.log_file)
    records, errors = read_manifest(adir)
    out: Dict[str, Any] = {"ok": True, "segments": len(records), "archived_events": 0,
                           "origin": "GENESIS", "epoch": None, "deep": bool(deep),
                           "events_checked": 0, "errors": errors[:]}
    prev_manifest, prev_last, total = "GENESIS", "GENESIS", 0
    for i, rec in enumerate(records):
        tag = f"seg{i}"
        payload = _record_payload(rec)
        if any(payload[k] is None for k in RECORD_FIELDS):
            out["errors"].append(f"{tag}_missing_fields")
            break
        if not core._verify_checkpoint_signature(rec.get("key_id"), payload, rec.get("sig")):
            out["errors"].append(f"{tag}_bad_signature")
            break
        if payload["seq"] != i:
            out["errors"].append(f"{tag}_seq_gap")
            break
        if payload["prev_manifest"] != prev_manifest:
            out["errors"].append(f"{tag}_manifest_chain_broken")
            break
        if payload["first_prev_hash"] != prev_last:
            out["errors"].append(f"{tag}_event_chain_broken")
            break
        if payload["global_start"] != total:
            out["errors"].append(f"{tag}_global_start_mismatch")
            break
        seg_path = adir / str(payload["segment"])
        if not seg_path.exists() or "/" in str(payload["segment"]):
            out["errors"].append(f"{tag}_segment_missing")
            break
        gz = seg_path.read_bytes()
        if _sha(gz) != payload["sha256_gz"]:
            out["errors"].append(f"{tag}_segment_tampered")
            break
        if deep:
            err = _deep_check_segment(core, gz, payload)
            if err:
                out["errors"].append(f"{tag}_{err}")
                break
            out["events_checked"] += payload["count"]
        out["epoch"] = out["epoch"] or payload["epoch"]
        prev_manifest = _sha(_canon(rec))
        prev_last = payload["last_hash"]
        total += payload["count"]
    out["archived_events"] = total
    out["origin"] = prev_last
    out["ok"] = not out["errors"]
    if not out["ok"]:
        out["origin"] = None
    return out


def _deep_check_segment(core, gz: bytes, payload: Dict[str, Any]) -> Optional[str]:
    try:
        raw = gzip.decompress(gz)
    except (OSError, EOFError):
        return "segment_not_gzip"
    if _sha(raw) != payload["sha256_raw"]:
        return "raw_hash_mismatch"
    prev, count, first = payload["first_prev_hash"], 0, None
    for ln in _segment_lines(raw):
        try:
            ev = json.loads(ln)
        except ValueError:
            return "event_malformed"
        if ev.get("prev_hash") != prev:
            return "event_link_broken"
        if ev.get("hash") != core._compute_event_hash(ev["prev_hash"], ev["blob"],
                                                      ev["time"], ev["type"]):
            return "event_hash_mismatch"
        if not _verify_event_line(core, ev):
            return "event_signature_invalid"
        first = first or ev["hash"]
        prev = ev["hash"]
        count += 1
    if count != payload["count"] or first != payload["first_hash"] or prev != payload["last_hash"]:
        return "segment_bounds_mismatch"
    return None


# ------------------------------------------------------------------ أصل السلسلة
_ORIGIN_CACHE: Dict[str, Tuple[Any, Optional[str]]] = {}


def chain_origin(core) -> Optional[str]:
    """أصل السلسلة الحية: GENESIS بلا أرشيف، آخر تجزئة مؤرشفة مع بيان صالح، و None
    لبيان/مقاطع عبث بها (فشل مغلق). يُخزّن مؤقتًا ببصمة البيان والمفاتيح."""
    adir = archive_dir_for(core.log_file)
    mpath = adir / MANIFEST_NAME
    if not mpath.exists():
        if adir.exists() and any(adir.glob("seg-*.jsonl.gz")):
            return None  # مقاطع بلا بيان = حذف البيان ⇒ لا أصل موثوق
        return "GENESIS"
    try:
        st = mpath.stat()
        fp = (st.st_size, st.st_mtime_ns, core._keyring_fingerprint())
    except OSError:
        return None
    cached = _ORIGIN_CACHE.get(str(mpath))
    if cached and cached[0] == fp:
        return cached[1]
    origin = verify_archive(core, adir, deep=False)["origin"]
    _ORIGIN_CACHE[str(mpath)] = (fp, origin)
    return origin


def iter_archived_lines(ledger_path: Path) -> Iterator[str]:
    """أسطر الأرشيف بالترتيب (للمراسي R-641 بفهارسها المطلقة). بلا تحقق هنا —
    جذر Merkle يكشف أي عبث في الأسطر نفسها."""
    adir = archive_dir_for(ledger_path)
    records, _ = read_manifest(adir)
    for rec in sorted(records, key=lambda r: r.get("seq", 0)):
        seg = adir / str(rec.get("segment", ""))
        if not seg.is_file():
            continue
        try:
            raw = gzip.decompress(seg.read_bytes())
        except (OSError, EOFError):  # TOLERATED (R-852): مقطع تالف — verify_archive يبلّغه
            continue
        for ln in _segment_lines(raw):
            yield ln.decode("utf-8")


# ------------------------------------------------------------------ استكمال المعلّق
def recover_pending(core) -> Dict[str, Any]:
    """انقطاع بعد إلحاق البيان وقبل إعادة كتابة السجل الحي: الأسطر المؤرشفة ما زالت
    في رأس السجل. تُقتطع فقط إن طابقت بايتات المقاطع حرفيًا (لا تخمين)."""
    adir = archive_dir_for(core.log_file)
    if not (adir / MANIFEST_NAME).exists() or not core.log_file.exists():
        return {"recovered": False}
    v = verify_archive(core, adir)
    if not v["ok"] or v["segments"] == 0:
        return {"recovered": False}
    with open(core.log_file, "rb") as fh:
        head = fh.readline()
    try:
        first = json.loads(head)
    except ValueError:
        return {"recovered": False}
    if first.get("prev_hash") == v["origin"]:
        return {"recovered": False}  # الحالة الطبيعية
    records, _ = read_manifest(adir)
    start = next((r for r in records if r.get("first_hash") == first.get("hash")), None)
    if start is None:
        return {"recovered": False}
    expected = b""
    for rec in records[start["seq"]:]:
        expected += gzip.decompress((adir / rec["segment"]).read_bytes())
    mod = _core_module(core)
    with mod.FileLock(mod.LOCK_FILE):
        data = core.log_file.read_bytes()
        if not data.startswith(expected):
            return {"recovered": False, "reason": "live_head_differs"}
        _fsync_write(core.log_file, data[len(expected):])
    _after_rewrite(core)
    logger.warning("R-852: استُكملت أرشفة معلّقة (%d بايت)", len(expected))
    return {"recovered": True, "bytes": len(expected)}


def _after_rewrite(core) -> None:
    core._integrity_cache = None
    core._integrity_prefix = None
    try:
        core.integrity_checkpoint_file.unlink()
    except FileNotFoundError:  # TOLERATED (R-852): لا نقطة سابقة — لا شيء يُبطل
        pass
    _ORIGIN_CACHE.clear()
    core._ledger_nonevent_lines = 0
    core.index = core._rebuild_index()
    core._save_meta()


# ------------------------------------------------------------------ الأرشفة
def plan(core, keep_last: int) -> Dict[str, Any]:
    if not isinstance(keep_last, int) or not KEEP_LAST_MIN <= keep_last <= KEEP_LAST_MAX:
        raise RetentionError(f"keep_last خارج المدى {KEEP_LAST_MIN}..{KEEP_LAST_MAX}")
    live = core._ledger_line_count() - getattr(core, "_ledger_nonevent_lines", 0)
    return {"live_events": live, "keep_last": keep_last,
            "would_archive": max(0, live - keep_last)}


def archive(core, keep_last: int, dry_run: bool = False, store: Any = None,
            audit: bool = True) -> Dict[str, Any]:
    """أرشفة كل ما يزيد عن آخر ``keep_last`` حدثًا (من البادئة المتحقق منها فقط)."""
    p = plan(core, keep_last)
    if dry_run:
        return {"ok": True, "dry_run": True, **p}
    recover_pending(core)
    adir = archive_dir_for(core.log_file)
    before = verify_archive(core, adir)
    if not before["ok"]:
        raise RetentionError(f"الأرشيف الحالي غير صالح: {before['errors'][:3]}")
    status = core.verify_integrity(verbose=True)
    if status.value != "verified":
        raise RetentionError(f"السجل الحي ليس VERIFIED ({status.value}) — لا أرشفة لسجل مشكوك فيه")
    prefix = core._integrity_prefix
    if not prefix or prefix.get("status") is not None:
        raise RetentionError("لا بادئة متحقق منها مبصومة")
    if core._sign_checkpoint_payload({"probe": 1}) is None:
        raise RetentionError("لا مفتاح KeyRing نشط لتوقيع البيان (فشل مغلق)")

    mod = _core_module(core)
    written: List[Dict[str, Any]] = []
    with mod.FileLock(mod.LOCK_FILE):
        data = core.log_file.read_bytes()
        verified = data[:prefix["offset"]]
        if _sha(verified) != prefix["sha256"]:
            raise RetentionError("البادئة تغيّرت بعد التحقق — أعد المحاولة")
        # مواضع نهاية كل سطر حدثي داخل البادئة المتحقق منها
        ends, pos = [], 0
        for raw in verified.split(b"\n")[:-1]:  # البادئة تنتهي دائمًا بنهاية سطر
            pos += len(raw) + 1
            if raw.strip():
                ends.append(pos)
        tail_events = len(_segment_lines(data[prefix["offset"]:]))
        total = len(ends) + tail_events
        n = min(len(ends), max(0, total - keep_last))
        if n == 0:
            return {"ok": True, "archived": 0, "segments_written": 0, **p}
        records, _ = read_manifest(adir)
        adir.mkdir(parents=True, exist_ok=True)
        prev_manifest = _sha(_canon(records[-1])) if records else "GENESIS"
        prev_last = before["origin"]
        epoch = before["epoch"]
        global_start = before["archived_events"]
        start_byte, idx = 0, 0
        while idx < n:
            j = min(n, idx + SEGMENT_MAX_EVENTS)
            raw = data[start_byte:ends[j - 1]]
            lines = _segment_lines(raw)
            first, last = json.loads(lines[0]), json.loads(lines[-1])
            if first.get("prev_hash") != prev_last:
                raise RetentionError("أول حدث لا يتصل بأصل السلسلة — رفض")
            seq = len(records) + len(written)
            gz = gzip.compress(raw, mtime=0)
            seg_name = f"seg-{seq:06d}.jsonl.gz"
            _fsync_write(adir / seg_name, gz)
            payload = {"v": MANIFEST_VERSION, "seq": seq,
                       "epoch": epoch or first["hash"], "segment": seg_name,
                       "count": len(lines), "global_start": global_start,
                       "first_hash": first["hash"], "first_prev_hash": prev_last,
                       "last_hash": last["hash"], "sha256_raw": _sha(raw),
                       "sha256_gz": _sha(gz), "prev_manifest": prev_manifest,
                       "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            key_id, sig = core._sign_checkpoint_payload(payload)
            rec = {**payload, "key_id": key_id, "sig": sig}
            with open(adir / MANIFEST_NAME, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            written.append({"rec": rec, "gz": gz})
            epoch = payload["epoch"]
            prev_manifest, prev_last = _sha(_canon(rec)), last["hash"]
            global_start += len(lines)
            start_byte, idx = ends[j - 1], j
        _fsync_write(core.log_file, data[ends[n - 1]:])
        _after_rewrite(core)
    after = verify_integrity_full(core)
    result = {"ok": after["ok"], "archived": n, "segments_written": len(written),
              "kept_live": total - n, "origin": prev_last, "epoch": epoch,
              "archive": {k: after["archive"][k] for k in ("segments", "archived_events", "ok")},
              "live_status": after["live_status"],
              "durable": mirror_to_store(store, written) if store is not None else None}
    if audit:
        try:
            core.append_event("ledger.archived", {
                "archived": n, "segments": [w["rec"]["segment"] for w in written],
                "origin": prev_last, "epoch": epoch, "kept_live": total - n,
                "durable": result["durable"]})
        except Exception as exc:  # TOLERATED (R-852): الأرشفة تمت وتحققت؛ فشل التدقيق يُعلن
            result["audit_error"] = type(exc).__name__
    return result


def verify_integrity_full(core, deep: bool = False) -> Dict[str, Any]:
    """تحقق كامل بعد الأرشفة: الأرشيف (بيان + مقاطع [+ كل حدث]) ثم السجل الحي من أصله."""
    arch = verify_archive(core, deep=deep)
    _ORIGIN_CACHE.clear()
    core._integrity_cache = None
    live = core.verify_integrity(verbose=True).value
    return {"ok": arch["ok"] and live == "verified", "archive": arch, "live_status": live}


# ------------------------------------------------------------------ المرآة الدائمة
def mirror_to_store(store: Any, written: List[Dict[str, Any]]) -> Dict[str, Any]:
    """دفع المقاطع وسجلاتها للمخزن الدائم — فشل الدفع يُعلن ولا يلغي الأرشفة المحلية."""
    pushed, failed = 0, 0
    for w in written:
        rec = w["rec"]
        key = f"{rec['epoch'][:16]}/{rec['segment']}"
        try:
            ok = bool(store.save_blob(DURABLE_NAMESPACE, key, {
                "record": rec, "gz_b64": base64.b64encode(w["gz"]).decode("ascii")}))
        except Exception:  # TOLERATED (R-852): المخزن بعيد — يُعدّ فشلًا معلنًا
            ok = False
        pushed += ok
        failed += not ok
    return {"pushed": pushed, "failed": failed, "namespace": DURABLE_NAMESPACE}


def verify_durable(core, store: Any) -> Dict[str, Any]:
    """تحقق المرآة الدائمة لكل حقبة: توقيع كل سجل، تسلسل البيان والسلسلة، بصمة المقطع."""
    if store is None:
        return {"available": False}
    try:
        rows = store.list_blobs(DURABLE_NAMESPACE) or []
    except Exception as exc:  # TOLERATED (R-852): بعيد — يُعلن
        return {"available": True, "ok": False, "error": type(exc).__name__}
    epochs: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        pl = (row or {}).get("payload") or {}
        rec = pl.get("record")
        if isinstance(rec, dict):
            epochs.setdefault(str(rec.get("epoch")), []).append(pl)
    report = {}
    for ep, items in epochs.items():
        items.sort(key=lambda x: x["record"].get("seq", 0))
        prev_m, prev_last, total, err = "GENESIS", "GENESIS", 0, None
        for i, it in enumerate(items):
            rec = it["record"]
            if rec.get("seq") != i:
                err = f"seq{i}_gap"
            elif not core._verify_checkpoint_signature(rec.get("key_id"), _record_payload(rec),
                                                       rec.get("sig")):
                err = f"seq{i}_bad_signature"
            elif rec.get("prev_manifest") != prev_m or rec.get("first_prev_hash") != prev_last:
                err = f"seq{i}_chain_broken"
            else:
                try:
                    gz = base64.b64decode(it.get("gz_b64") or "", validate=True)
                except ValueError:
                    gz = b""
                if _sha(gz) != rec.get("sha256_gz"):
                    err = f"seq{i}_segment_tampered"
            if err:
                break
            prev_m, prev_last = _sha(_canon(rec)), rec["last_hash"]
            total += rec["count"]
        report[ep[:16]] = {"ok": err is None, "segments": len(items),
                           "archived_events": total, "error": err}
    return {"available": True, "ok": all(r["ok"] for r in report.values()),
            "epochs": report}


def status(core, store: Any = None) -> Dict[str, Any]:
    arch = verify_archive(core)
    return {"live_events": plan(core, KEEP_LAST_MIN)["live_events"],
            "archive": {k: arch[k] for k in ("ok", "segments", "archived_events",
                                             "origin", "epoch", "errors")},
            "segment_max_events": SEGMENT_MAX_EVENTS,
            "auto": False,
            "durable": ({"backend": getattr(store, "backend_label", None)
                         or type(store).__name__} if store is not None else None)}
