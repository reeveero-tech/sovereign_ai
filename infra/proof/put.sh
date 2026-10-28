#!/usr/bin/env bash
# R-801: نسخ ملف إلى آلة التطبيق عبر ssh (base64) — بديل غير تفاعلي لـ sftp.
# الاستعمال: infra/proof/put.sh <local> <remote>   (يتطلب FLY_APP و APPM)
set -euo pipefail
B64=$(base64 -w0 "$1")
flyctl ssh console -a "$FLY_APP" --machine "$APPM" -C "python3 -c \"import base64;open('$2','wb').write(base64.b64decode('$B64'));print('PUT $2')\""
