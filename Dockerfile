FROM python:3.12

# مجلد العمل الرئيسي
WORKDIR /app

# نسخ ملف المتطلبات من الجذر
COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ جميع ملفات المشروع
COPY . .

# تشغيل التطبيق
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
