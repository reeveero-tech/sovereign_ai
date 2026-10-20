"""عميل Ollama — عقل السيادي المحلي (R-704، بطلب المالك 2026-10-20).

استدعاء خادم Ollama المحلي (البروتوكول الرسمي: POST /api/chat مع
stream:false — الاستجابة {message:{content}}) لتوليد ردود /chat بدل
القوالب. لا استدعاء لأي خدمة خارجية — عقل LLM محلي بالكامل.

مبادئ التصميم:
- لا يرفع أبدًا: أي فشل (شبكة/مهلة/HTTP/فساد استجابة) يعيد None
  والمستدعي يسقط للمحرك القالبي القائم — التطبيق لا يتعطل بغياب العقل.
- لا يُسجل المفتاح ولا محتوى المحادثة في السجلات — فقط نوع الخطأ.
- المعطيات تُقرأ من config ديناميكيًا (على مستوى الاستدعاء) — قابلة
  للرقعة في الاختبارات دون إعادة استيراد.
"""

import logging

logger = logging.getLogger("sovereign.ollama")


def chat(system_prompt: str, user_message: str, timeout=None):
    """توليد رد عبر خادم Ollama — يعيد نص النموذج أو None عند أي فشل.

    لا يُستدعى فعليًا إلا إذا كان العقل مفعّلًا (OLLAMA_ENABLED + نموذج)
    — تحقق المستدعي أو هذا الشرط هنا: كلاهما رخيص.
    """
    import config

    if not (config.OLLAMA_ENABLED and config.OLLAMA_MODEL):
        return None

    timeout = timeout or config.OLLAMA_TIMEOUT_SECONDS
    try:
        import httpx

        headers = {"Content-Type": "application/json"}
        if config.OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {config.OLLAMA_API_KEY}"

        payload = {
            "model": config.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        url = f"{str(config.OLLAMA_BASE_URL).rstrip('/')}/api/chat"
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = (data.get("message") or {}).get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        logger.warning("R-704 [OLLAMA]: رد فارغ/فاسد — سقوط للمحرك القالبي")
        return None
    except Exception as e:
        # لا مفتاح ولا محتوى محادثة في السجلات — نوع الخطأ فقط
        logger.warning(
            "R-704 [OLLAMA]: فشل خادم العقل (%s) — سقوط للمحرك القالبي",
            type(e).__name__,
        )
        return None
