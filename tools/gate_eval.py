#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-843: بوابة التقييم المستقل — تُشغَّل في CI على كل تغيير.

تفشل (رمز 1) إن هبطت أي مجموعة مجمّدة عن أرضيتها، أو تغيرت بيانات مجموعة
عن بصمتها المثبتة، أو فشل مشغّل. حتمية بالكامل: بلا عقل ولا شبكة.

الاستعمال:
    python tools/gate_eval.py              # كل المجموعات
    python tools/gate_eval.py --json out   # + التقرير كاملًا في ملف
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="مسار لحفظ التقرير الكامل")
    ap.add_argument("--suite", action="append", help="مجموعة محددة (تكرار مسموح)")
    args = ap.parse_args(argv)
    logging.disable(logging.INFO)
    from evaluation import runner
    report = runner.run_suites(args.suite)
    print(runner.format_table(report))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1,
                                              default=str), encoding="utf-8")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
