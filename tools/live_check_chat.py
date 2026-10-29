#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-814b — فحص بنيوي مستقل يختبره pytest (خلل فحص ≠ نجاح)."""
from __future__ import annotations

import json
import sys


def _load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[2] not in ("expect-ok", "expect-error"):
        print("usage: live_check_chat.py FILE expect-ok|expect-error", file=sys.stderr)
        return 2
    try:
        data = _load(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"::error::تعذر فحص الاستجابة: {exc}")
        return 2
    want_ok = sys.argv[2] == "expect-ok"
    status = data.get("status")
    agent = data.get("agent_status")
    if want_ok:
        if status != "ok":
            print(f"::error::محادثة حقيقية بحالة فاشلة: {status} / {agent}")
            return 1
        if agent not in ("completed", "answered_from_results"):
            print(f"::error::حالة الوكيل ليست مكتملة: {agent}")
            return 1
        # R-814c: نجاح بلا جواب غير ذي معنى — الرد نفسه جزء من العقد
        if not str(data.get("reply") or "").strip():
            print("::error::نجاح بلا جواب (reply فارغ) — ليس نجاحًا ذا معنى")
            return 1
        print("OK live chat (ok + completed + nonempty reply)")
    else:
        # عقد الحالة الصادق (R-814): فشل فعلي ⇒ error لا ok
        if status != "error":
            print(f"::error::فشل فعلي بحالة {status} — عقد الحالة الصادق انكسر")
            return 1
        if agent != "planner_failed":
            print(f"::error::حالة الوكيل للنموذج الوهمي: {agent} (المتوقع planner_failed)")
            return 1
        print("OK honest failure contract (error + planner_failed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
