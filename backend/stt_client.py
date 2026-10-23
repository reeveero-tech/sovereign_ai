"""عميل السمع — تحويل الكلام لنص (R-737 — البند ٢.٣، بأمر المالك «ابدأ»).

استدعاء خدمة تحويل كلام متوافقة مع OpenAI (البروتوكول القياسي:
POST {base}/audio/transcriptions بطلب multipart — الاستجابة {text}).
بروتوكول واحد يغطي المصدرين المذكورين في الخارطة («Whisper محلي أو خدمة»):

- خادم whisper.cpp محلي (نقطته متوافقة مع OpenAI؛ الخادم يقرر النموذج
  بنفسه فلا حاجة إلى STT_MODEL).
- خدمة سحابية (مثال Groq: whisper-large-v3 على الأساس نفسه).

مبادئ التصميم (قائمة من R-704/R-736 — نمط العقل):
- معطل افتراضيًا (STT_ENABLED) — لا اتصال ضمني أبدًا.
- لا يرفع أبدًا: أي فشل (شبكة/مهلة/HTTP/فساد استجابة) يعيد None
  والمستدعي يعلن السبب بصدق — لا نص مختلق ولا نجاح كاذب.
- لا مفتاح ولا محتوى صوتي ولا نص مستخرج في السجلات — نوع الخطأ فقط.
- المعطيات تُقرأ من config ديناميكيًا (على مستوى الاستدعاء) — قابلة
  للرقعة في الاختبارات دون إعادة استيراد.
"""

import logging

logger = logging.getLogger("sovereign.stt")


def transcribe(audio_bytes: bytes, filename: str, content_type: str,
               timeout=None):
    """تحويل مقطع صوتي إلى نص — يعيد النص أو None (fail-closed).

    لا يُستدعى فعليًا إلا إذا كان السمع مفعّلًا (STT_ENABLED) — التحقق هنا
    أيضًا: كلاهما رخيص، والمستدعي (نقطة /stt) يفحص أولًا ليعلن السبب
    بصدق قبل قراءة الملف.
    """
    import config

    if not config.STT_ENABLED:
        return None

    timeout = timeout or config.STT_TIMEOUT_SECONDS
    try:
        import httpx

        headers = {}
        if config.STT_API_KEY:
            headers["Authorization"] = f"Bearer {config.STT_API_KEY}"
        data = {}
        if config.STT_MODEL:
            data["model"] = config.STT_MODEL
        base = str(config.STT_BASE_URL).rstrip("/")
        url = f"{base}/audio/transcriptions"
        files = {"file": (filename or "audio", audio_bytes,
                          content_type or "application/octet-stream")}
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, data=data, files=files, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        logger.warning("R-737 [STT]: استجابة بلا نص — لا نص مختلق")
        return None
    except Exception as e:
        # لا مفتاح ولا محتوى في السجلات — نوع الخطأ فقط
        logger.warning("R-737 [STT]: فشل خدمة السمع (%s) — لا نص",
                       type(e).__name__)
        return None
