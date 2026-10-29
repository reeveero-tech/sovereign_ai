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
        print("usage: live_check_settings.py FILE", file=sys.stderr)
        return 2
    try:
        data = _load(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"::error::تعذر فحص الاستجابة: {exc}")
        return 2
    if not isinstance(data, dict) or not data.get("enabled"):
        print("::error::إعدادات العقل تُقرأ لكن العقل معطل")
        return 1
    if "OLLAMA_API_KEY" in data or "api_key" in data:
        print("::error::سر مفتاح المزود تسرب في إعدادات تُقرأ — انتهاك لا-سر")
        return 1
    print("OK brain settings (enabled, no secret leak)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
