#!/bin/bash
# نقطة التشغيل الموحدة (M1)
# المنفذ من متغير البيئة PORT، الافتراضي 8000
cd backend
PORT="${PORT:-8000}"
# R-847: استعادة مجهزة تُطبق قبل التطبيق (فشلها يتراجع داخليًا ولا يمنع الإقلاع)
if [ -f "data/.restore/PENDING.json" ] || [ -f "../data/.restore/PENDING.json" ]; then
  python -m backup apply-pending || echo "R-847: تطبيق الاستعادة لم ينجح — انظر .restore/LAST.json" >&2
fi
exec python -m uvicorn app:app --host 0.0.0.0 --port "$PORT" --log-level info
