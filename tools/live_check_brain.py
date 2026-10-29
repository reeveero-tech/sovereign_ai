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
        print("usage: live_check_brain.py FILE", file=sys.stderr)
        return 2
    try:
        data = _load(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"::error::تعذر فحص الاستجابة: {exc}")
        return 2
    if not isinstance(data, dict) or not data.get("enabled"):
        print("::error::العقل غير مفعل على المنشور")
        return 1
    if not str(data.get("model") or "").strip():
        print("::error::لا نموذج معلن للعقل")
        return 1
    print("OK brain (enabled with model)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
