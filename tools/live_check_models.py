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
        print("usage: live_check_models.py FILE", file=sys.stderr)
        return 2
    try:
        data = _load(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"::error::تعذر فحص الاستجابة: {exc}")
        return 2
    if not isinstance(data, dict) or not data.get("ok"):
        print(f"::error::اكتشاف النماذج فشل: {data.get('error') if isinstance(data, dict) else 'ليس كائنًا'}")
        return 1
    models = data.get("models")
    if not isinstance(models, list) or not models:
        print("::error::لا نماذج مكتشفة من المزود الحي")
        return 1
    print(f"OK models discovery ({len(models)} live)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
