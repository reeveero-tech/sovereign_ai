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
    if len(sys.argv) != 2:
        print("usage: live_check_conversation.py FILE", file=sys.stderr)
        return 2
    try:
        data = _load(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"::error::تعذر فحص الاستجابة: {exc}")
        return 2
    msgs = data.get("messages") if isinstance(data, dict) else None
    if not isinstance(msgs, list) or len(msgs) < 2:
        print("::error::المحادثة لم تُستعاد برسائلها")
        return 1
    bot = next((m for m in msgs if m.get("role") == "assistant"), None)
    if not bot or "فحص" not in str(bot.get("content") or ""):
        print("::error::رسالة المساعد لم تُستعاد بمحتواها")
        return 1
    # R-814b: العلامات الصادقة تعبر جولة الخادم — لا تضيع بالحفظ
    if not bot.get("err"):
        print("::error::علامة الفشل (err) ضاعت عبر جولة الخادم")
        return 1
    if not bot.get("rev"):
        print("::error::تحفظ المراجع (rev) ضاع عبر جولة الخادم")
        return 1
    print("OK conversation roundtrip (content + err + rev preserved)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
