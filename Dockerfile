FROM python:3.11-slim

WORKDIR /app

# نسخ الاعتماديات الموحدة
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# نقطة التشغيل: من داخل backend (لأن app.py يستورد orchestrator نسبياً)
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

# ⚠️ SECURITY (جولة المجلس <1> — أمين 2.2): الإنتاج صريح — الرفض المغلق
# يعمل (لا يُقبل البدء بلا SOVEREIGN_KEY من fly secrets).
ENV AI_ENVIRONMENT=production

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
