# -*- coding: utf-8 -*-
"""R-847: سطر أوامر النسخ — ``python3 -m backup <أمر>`` (من ``backend/``).

- ``apply-pending``: يطبق استعادة مجهزة. تستدعيه نقطة دخول الحاوية و``start.sh``
  **قبل** التطبيق. رمز الخروج 0 يعني لا شيء أو طُبقت، و1 يعني تراجع أو فشل
  (مسجل في ``.restore/LAST.json`` ومُشعر). والإقلاع يكمل في الحالتين.
- ``create`` / ``list`` / ``verify <id>``: للمشغل من صدفة الآلة.
"""
from __future__ import annotations

import json
import sys

from . import service
from .snapshot import BackupError


def main(argv) -> int:
    if not argv:
        print("الاستعمال: python3 -m backup {apply-pending|create|list|verify <id>}",
              file=sys.stderr)
        return 64
    cmd = argv[0]
    if cmd == "apply-pending":
        out = service.apply_pending()
        print(json.dumps({k: v for k, v in out.items() if k != "files"}, ensure_ascii=False))
        return 0 if out.get("state") in ("none", "applied") else 1
    if cmd == "create":
        try:
            meta = service.create("manual", "cli")
        except BackupError as exc:
            print(json.dumps({"ok": False, "reason": exc.reason}, ensure_ascii=False))
            return 1
        print(json.dumps({"ok": True, "backup_id": meta["backup_id"], "size": meta["size"],
                          "offsite": meta["offsite"]}, ensure_ascii=False))
        return 0
    if cmd == "list":
        for m in service.settings().catalog().list():
            print(json.dumps({k: m.get(k) for k in ("backup_id", "kind", "size", "encrypted",
                                                    "offsite")}, ensure_ascii=False))
        return 0
    if cmd == "verify" and len(argv) == 2:
        out = service.verify(argv[1])
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    print(f"أمر مجهول: {cmd}", file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
