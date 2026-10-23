"""عميل النطق — تحويل النص لصوت (R-740 — البند ٢.٤، بأمر المالك «ابدأ»).

نص → مقطع صوتي عبر خدمة نطق متوافقة مع OpenAI:
POST {base}/audio/speech بجسد {"model", "input", "voice"?} — والاستجابة
بايتات صوت ثنائية (audio/mpeg ونحوها). البروتوكول القياسي الواحد يغطي:
- خدمة سحابية (مثال Groq: playai-tts).
- خادمًا محليًا متوافقًا (piper/kokoro بغلاف متوافق OpenAI).

مبادئ قائمة (R-704/R-736/R-737/R-739):
- معطل افتراضيًا (TTS_ENABLED) — لا اتصال ضمني أبدًا.
- لا يرفع أبدًا: أي فشل يعيد None والنقطة تعلن السبب بصدق — لا صوت
  مختلق ولا نجاح كاذب.
- لا مفتاح ولا نص في السجلات — نوع الخطأ فقط.
- يرفض الاستجابة غير الصوتية (JSON خطأ مثلًا) — لا إرجاع جسد فاسد كصوت.
"""

import logging

logger = logging.getLogger("sovereign.tts")


def speak(text: str, timeout=None):
    """نص → (بايتات الصوت، نوع المحتوى) أو None (fail-closed).

    يتطلب TTS_ENABLED + TTS_MODEL.
    """
    import config

    if not config.TTS_ENABLED or not config.TTS_MODEL:
        return None

    timeout = timeout or config.TTS_TIMEOUT_SECONDS
    try:
        import httpx

        headers = {}
        if config.TTS_API_KEY:
            headers["Authorization"] = f"Bearer {config.TTS_API_KEY}"
        payload = {"model": config.TTS_MODEL, "input": text}
        if config.TTS_VOICE:
            payload["voice"] = config.TTS_VOICE
        base = str(config.TTS_BASE_URL).rstrip("/")
        url = f"{base}/audio/speech"
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if not ctype.startswith("audio/") or not resp.content:
            logger.warning("R-740 [TTS]: استجابة غير صوتية (%s) — لا صوت",
                           ctype or "بلا نوع")
            return None
        return resp.content, ctype
    except Exception as e:
        # لا مفتاح ولا نص في السجلات — نوع الخطأ فقط
        logger.warning("R-740 [TTS]: فشل خدمة النطق (%s) — لا صوت",
                       type(e).__name__)
        return None
