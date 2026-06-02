FROM python:3.11-slim

WORKDIR /app

# نسخ ملف المتطلبات
COPY requirements.txt .

# تثبيت الاعتماديات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كل الكود
COPY . .

# تعيين مجلد backend كمسار العمل
WORKDIR /app/backend

# تعيين متغير البيئة
ENV PYTHONPATH=/app

# تشغيل الخادم
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
