#!/bin/bash
# نقطة التشغيل الموحدة (M1)
# المنفذ من متغير البيئة PORT، الافتراضي 8000
cd backend
PORT="${PORT:-8000}"
exec python -m uvicorn app:app --host 0.0.0.0 --port "$PORT" --log-level info
