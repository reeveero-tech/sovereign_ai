# Dockerfile — جاهز لـfly.io (R-698 — تحديث تجهيز النشر، لا نشر فعلي)
#
# قواعد ثابتة محفوظة:
# - الرفض المغلق: AI_ENVIRONMENT=production — التطبيق يرفض الإقلاع بلا
#   SOVEREIGN_KEY من الأسرار الخارجية (جولة المجلس <1> — أمين 2.2).
# - الأسرار لا تدخل الصورة إطلاقًا (.dockerignore: key.secret/keyring/
#   credentials/*.pem) — تُمرر عبر fly secrets.
# - التشغيل من داخل backend (app.py يستورد نسبيًا).

FROM python:3.11-slim

WORKDIR /app

# R-800: ffmpeg (ffprobe للصوت/الفيديو) + libfribidi0 (تشكيل العربية في Pillow/raqm) + poppler-utils (pdftotext)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libfribidi0 poppler-utils \
    && rm -rf /var/lib/apt/lists/*

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

# R-698 (جاهزية fly.io): مستخدم غير جذري بأقل امتياز — التطبيق لا يحتاج
# root أبدًا؛ الملفات الجارية تُكتب في /app/data (ملكية sovereign).
# R-760 (بأمر المالك D-044): /app/data حجم Fly دائم يُنشأ مملوكًا للجذر — لذا
# لا `USER` هنا؛ نقطة الدخول تبدأ جذرًا لتملّك الحجم ثم تُسقط الامتياز إلى 1001
# بـsetpriv قبل التطبيق (scripts/container_entrypoint.sh — محروسة باختبار).
RUN useradd --system --uid 1001 --create-home sovereign \
    && mkdir -p /app/data \
    && chown -R sovereign:sovereign /app \
    && chmod 0755 /app/scripts/container_entrypoint.sh

EXPOSE 8080

# فحص حيوية داخل الحاوية — /health عبر urllib (لا curl في slim)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4)"]

ENTRYPOINT ["/app/scripts/container_entrypoint.sh"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
