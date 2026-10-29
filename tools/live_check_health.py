#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-814b — فحص صحة /health بنيويًا (لا بحث نص عن healthy متداخل).

الحقل العلوي status هو الحَكَم — استجابة سليمة البنية بمكون معطوب تُرفض،
واستجابة بلا الحقل تُرفض (خلل فحص ≠ نجاح). سكربت مستقل يختبره pytest.
خروج: 0 سليم، 1 عيب، 2 خلل فحص (ملك غير قابل للفحص).
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: live_check_health.py FILE", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"::error::تعذر فحص الاستجابة (خلل فحص لا نجاح): {exc}")
        return 2
    if not isinstance(data, dict) or data.get("status") != "healthy":
        print(f"::error::/health ليس سليمًا — الحالة العلوية: {data.get('status') if isinstance(data, dict) else 'ليس كائنًا'}")
        return 1
    # R-814c: غياب المكونات/حالاتها ليس نجاحًا — العقد الحي: components قاموس
    # لكل مكون status صريح (العينة الحية: 23 مكونًا كلها بحالة)
    comps = data.get("components")
    if not isinstance(comps, dict) or not comps:
        print("::error::/health بلا مكونات — ليس نجاحًا ذا معنى")
        return 1
    bad = []
    for k, v in comps.items():
        st = v.get("status") if isinstance(v, dict) else None
        if st is None:
            bad.append(f"{k}(بلا حالة)")
        elif st != "healthy":
            bad.append(f"{k}({st})")
    if bad:
        print(f"::error::مكونات غير سليمة أو بلا حالة: {bad[:5]}")
        return 1
    print(f"OK /health (top-level healthy, {len(comps)} components all explicit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
