"""عميل الرؤية — تحليل الصور (R-739 — البند ٢.٢، بأمر المالك «ابدأ»).

صورة → وصف نصي عبر نموذج متعدد الوسائط على عقل المنشور (بروتوكولا
R-736 — بنفس أساس OLLAMA_*):

- بروتوكول ollama: POST {base}/api/chat — الصورة base64 في
  `messages[].images[]` (عقد Ollama للوسائط المتعددة).
- بروتوكول openai: POST {base}/chat/completions — الصورة data-URL
  داخل `content[].image_url` (عقد OpenAI للوسائط).

مبادئ قائمة (R-704/R-736/R-737):
- معطل افتراضيًا (VISION_ENABLED) — لا اتصال ضمني أبدًا.
- لا يرفع أبدًا: أي فشل يعيد None والنقطة تعلن السبب بصدق — لا وصف
  مختلق ولا نجاح كاذب.
- لا مفتاح ولا محتوى صورة في السجلات — نوع الخطأ فقط.
"""

import base64
import logging

logger = logging.getLogger("sovereign.vision")


def describe(image_bytes: bytes, content_type: str, prompt: str = None,
             timeout=None):
    """صورة → وصف نصي — يعيد الوصف أو None (fail-closed).

    يتطلب: VISION_ENABLED + VISION_MODEL (نموذج رؤية) + عقلًا مفعّلًا.
    """
    import config

    if not config.VISION_ENABLED or not config.VISION_MODEL:
        return None

    timeout = timeout or config.OLLAMA_TIMEOUT_SECONDS
    prompt = prompt or ("صِف هذه الصورة بدقة بالعربية: ما فيها وما غرضها "
                        "وأي نص ظاهر فيها — بلا تخمين لما لا يُرى.")
    try:
        import httpx

        b64 = base64.b64encode(image_bytes).decode()
        headers = {"Content-Type": "application/json"}
        if config.OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {config.OLLAMA_API_KEY}"
        base = str(config.OLLAMA_BASE_URL).rstrip("/")
        protocol = getattr(config, "OLLAMA_PROTOCOL", "ollama")

        if protocol == "openai":
            url = f"{base}/chat/completions"
            payload = {
                "model": config.VISION_MODEL,
                "stream": False,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:{content_type or 'image/png'};base64,{b64}"}},
                    ],
                }],
            }
        elif protocol == "ollama":
            url = f"{base}/api/chat"
            payload = {
                "model": config.VISION_MODEL,
                "stream": False,
                "messages": [{
                    "role": "user",
                    "content": prompt,
                    "images": [b64],
                }],
            }
        else:
            # بروتوكول مجهول → إغلاق بلا طلب (نمط R-736 — لا صدى للقيمة)
            logger.warning("R-739 [VISION]: بروتوكول غير معروف — إغلاق")
            return None

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if protocol == "openai":
            choices = data.get("choices") or []
            first = choices[0] if choices else {}
            content = (first.get("message") or {}).get("content")
        else:
            content = (data.get("message") or {}).get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        logger.warning("R-739 [VISION]: استجابة بلا وصف — لا وصف مختلق")
        return None
    except Exception as e:
        # لا مفتاح ولا محتوى في السجلات — نوع الخطأ فقط
        logger.warning("R-739 [VISION]: فشل خدمة الرؤية (%s) — لا وصف",
                       type(e).__name__)
        return None
