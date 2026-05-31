FROM python:3.12-slim

WORKDIR /app

# نسخ متطلبات بايثون
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الكود
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# تعيين مجلد العمل
WORKDIR /app/backend

# تشغيل الخادم
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
