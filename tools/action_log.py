#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""سجل أفعال البناء الفعلي (تصويب المراجع — الاعتراض 7).

كل فعل يُسجَّل لحظة تنفيذه بـ: طابع زمني حقيقي (UTC) + SHA256 لمحتوى كل
ملف متأثر «قبل» (من آخر حالة ملتزمة في Git) و«بعد» (الشجرة العاملة).
السجل append-only (forensics/build_actions.jsonl) — الإضافة فقط.

الاستخدام:
  python tools/action_log.py record --action "وصف الفعل" --files a.py b.py
  python tools/action_log.py show
"""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG = REPO_ROOT / "forensics" / "build_actions.jsonl"


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_head_bytes(repo_root: Path, path: str):
    """محتوى الملف من آخر حالة ملتزمة (HEAD) — أساس الـ«قبل» المرجعي."""
    r = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        capture_output=True, cwd=str(repo_root),
    )
    return r.stdout if r.returncode == 0 else None


def snapshot_files(files: list, repo_root=None) -> dict:
    """لقطة «قبل» فعلًا — تُؤخذ قبل تنفيذ الفعل مباشرة (لا من HEAD):
    {path: sha256 لمحتوى الشجرة العاملة لحظة الالتقاط}."""
    root = Path(repo_root) if repo_root else REPO_ROOT
    snap = {}
    for p in files:
        wt = root / p
        snap[p] = _sha_bytes(wt.read_bytes()) if wt.exists() else None
    return snap


def record(action: str, files: list, log_path=None, repo_root=None,
           before_snapshot: dict = None) -> dict:
    """تسجيل فعل — لكل ملف «قبل» و«بعد»:

    - قبل_snapshot (الموصى به): لقطة snapshot_files المأخوذة قبل تنفيذ
      الفعل مباشرة — الإثبات الزمني الحقيقي (قبل الفعل/بعد الفعل).
    - بدونه: «قبل» من آخر حالة ملتزمة (HEAD) — مرجع لا إثبات زمني للفعل.
    """
    root = Path(repo_root) if repo_root else REPO_ROOT
    entries = []
    for p in files:
        if before_snapshot is not None and p in before_snapshot:
            before_sha = before_snapshot[p]
        else:
            head_bytes = _git_head_bytes(root, p)
            before_sha = _sha_bytes(head_bytes) if head_bytes is not None else None
        wt = root / p
        after_bytes = wt.read_bytes() if wt.exists() else None
        entries.append({
            "path": p,
            "before_sha": before_sha,
            "after_sha": _sha_bytes(after_bytes) if after_bytes is not None else None,
        })
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "action": action,
        "files": entries,
        "timing_proof": "pre-action snapshot" if before_snapshot is not None else "HEAD reference only",
    }
    target = Path(log_path) if log_path else LOG
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def run_logged(action: str, files: list, fn, log_path=None, repo_root=None):
    """الغلاف الفعلي (تصويب المراجع — الاعتراض 7): يلتقط المحتوى «قبل»
    تنفيذ الفعل، ينفذه، ثم يسجل سطرًا كاملًا واحدًا — وقت البداية والنهاية،
    البصمتان، حالة التنفيذ، النتيجة أو الخطأ. يُسجل حتى عند فشل الفعل
    (status=failed + الخطأ) ثم يُعاد رفع الاستثناء.

    إرجاع: (نتيجة fn، سجل الفعل كما كُتب على القرص)
    """
    import datetime as _dt

    root = Path(repo_root) if repo_root else REPO_ROOT
    target_log = Path(log_path) if log_path else LOG

    before = snapshot_files(files, repo_root=root)
    started = _dt.datetime.now(_dt.timezone.utc).isoformat()

    status, result, error = "ok", None, None
    try:
        result = fn()
    except Exception as exc:  # يُسجل الفشل أيضًا — لا فعل بلا سطر
        status, error = "failed", repr(exc)

    ended = _dt.datetime.now(_dt.timezone.utc).isoformat()

    entries = []
    for p in files:
        wt = root / p
        after_bytes = wt.read_bytes() if wt.exists() else None
        entries.append({
            "path": p,
            "before_sha": before.get(p),
            "after_sha": _sha_bytes(after_bytes) if after_bytes is not None else None,
        })

    def _jsonable(v):
        try:
            import json as _json
            _json.dumps(v)
            return v
        except (TypeError, ValueError):
            return repr(v)

    rec = {
        "ts": ended,
        "started_at": started,
        "ended_at": ended,
        "action": action,
        "files": entries,
        "timing_proof": "pre-action snapshot",
        "status": status,
        "result": _jsonable(result) if status == "ok" else None,
        "error": error,
    }
    with target_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if status == "failed":
        raise RuntimeError(f"logged action failed: {error}")
    return result, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("record", help="سجل فعلًا")
    r.add_argument("--action", required=True)
    r.add_argument("--files", nargs="+", required=True)

    sub.add_parser("show", help="اعرض السجل")

    args = ap.parse_args(argv)
    if args.cmd == "record":
        rec = record(args.action, args.files)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0
    print(LOG.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
