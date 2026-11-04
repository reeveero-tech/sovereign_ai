# -*- coding: utf-8 -*-
"""R-843: مشغّل التقييم — كل المجموعات المجمّدة، تقرير قابل للتتبع، حكم صريح.

النجاح يتطلب لكل مجموعة: بصمة البيانات = المثبتة **و** الدرجة ≥ الأرضية.
فشل المشغّل نفسه (استثناء) = فشل المجموعة بسببه — لا تخطٍ صامت.
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import suites as _suites

_FAIL_CAP = 10


def run_suites(ids: Optional[List[str]] = None) -> Dict[str, Any]:
    selected = [_suites.get(i) for i in ids] if ids else list(_suites.SUITES)
    t0 = time.monotonic()
    rows = []
    for s in selected:
        row: Dict[str, Any] = {**s.public()}
        t = time.monotonic()
        try:
            actual = _suites.file_sha256(s.data_path)
        except OSError as exc:
            actual = f"missing:{type(exc).__name__}"
        row["sha_ok"] = actual == s.sha256
        row["sha_actual"] = actual
        try:
            r = s.runner(s.data_path)
            row.update(score=r["score"], passed=r["passed"], n=r["n"],
                       failures=r.get("failures", [])[:_FAIL_CAP],
                       extra=r.get("extra"), error=None)
        except Exception as exc:  # TOLERATED: فشل المشغّل يُسجل فشلًا للمجموعة لا يُبتلع
            row.update(score=0.0, passed=0, n=0, failures=[],
                       extra=None, error=f"{type(exc).__name__}: {exc}"[:300])
        row["duration_s"] = round(time.monotonic() - t, 3)
        row["pass"] = bool(row["sha_ok"] and row["error"] is None
                           and row["score"] >= s.floor)
        rows.append(row)
    return {"report_id": str(uuid.uuid4()),
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_sha": os.environ.get("GITHUB_SHA") or os.environ.get("SOVEREIGN_GIT_SHA"),
            "suites": rows, "pass": all(r["pass"] for r in rows),
            "duration_s": round(time.monotonic() - t0, 3)}


def save_report(report: Dict[str, Any], data_dir: Optional[str] = None) -> str:
    """حفظ ذري للتقرير الأخير + سطر في سجل إلحاقي (تتبع كل تشغيل)."""
    import json
    try:
        from runtime.atomic_json import atomic_write_json
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.runtime.atomic_json import atomic_write_json
    root = Path(data_dir or os.environ.get("SOVEREIGN_EVAL_DIR") or
                Path(__file__).resolve().parents[2] / "data" / "evaluation")
    root.mkdir(parents=True, exist_ok=True)
    atomic_write_json(root / "latest.json", report)
    summary = {"report_id": report["report_id"], "at": report["at"],
               "git_sha": report["git_sha"], "pass": report["pass"],
               "scores": {r["suite_id"]: r["score"] for r in report["suites"]}}
    with open(root / "history.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return str(root / "latest.json")


def format_table(report: Dict[str, Any]) -> str:
    lines = [f"تقرير التقييم {report['report_id']} — {'✅ ناجح' if report['pass'] else '❌ فاشل'}"]
    for r in report["suites"]:
        mark = "✅" if r["pass"] else "❌"
        lines.append(f"{mark} {r['suite_id']}: {r['score']} (أرضية {r['floor']}) "
                     f"{r['passed']}/{r['n']} بصمة={'سليمة' if r['sha_ok'] else 'مختلفة'}"
                     + (f" خطأ={r['error']}" if r["error"] else ""))
        for f in r["failures"]:
            lines.append(f"     ✗ {f.get('id')}: {f.get('rule') or f.get('utterance', '')}"[:200])
    return "\n".join(lines)
