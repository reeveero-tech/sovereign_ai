#!/bin/bash
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 5000 --log-level info
