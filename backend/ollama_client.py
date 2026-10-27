"""عميل العقل — السيادي (R-704، بطلب المالك 2026-10-20 — R-736: بروتوكولان).

R-704: استدعاء خادم Ollama المحلي (البروتوكول الرسمي: POST /api/chat مع
stream:false — الاستجابة {message:{content}}) لتوليد ردود /chat بدل
القوالب. لا استدعاء لأي خدمة خارجية — عقل LLM محلي بالكامل.

R-736 (البند ٢.١ — عقل المنشور على Fly، بأمر المالك «1+2+3+4»):
بروتوكول ثانٍ متوافق مع OpenAI (POST {base}/chat/completions — الاستجابة
{choices:[{message:{content}}]}) لمزود سحابي (Groq/OpenRouter/أي متوافق)،
بجانب بروتوكول Ollama القائم كما هو حرفيًا. الاختيار بـOLLAMA_PROTOCOL
("ollama" افتراضيًا / "openai") — القيمة المجهولة تُغلق fail-closed بلا
أي طلب يخرج من العملية.

مبادئ التصميم (قائمة من R-704):
- لا يرفع أبدًا: أي فشل (شبكة/مهلة/HTTP/فساد استجابة/بروتوكول مجهول)
  يعيد None والمستدعي يسقط للمحرك القالبي القائم — التطبيق لا يتعطل.
- لا يُسجل المفتاح ولا محتوى المحادثة في السجلات — فقط نوع الخطأ.
- المعطيات تُقرأ من config ديناميكيًا (على مستوى الاستدعاء) — قابلة
  للرقعة في الاختبارات دون إعادة استيراد.
- R-736: آخر نتيجة استدعاء تُتاح لـ/brain/status (last_call) — تمييز صادق
  بين «عقل مفعّل» و«استدلال ناجح»؛ لا محتوى ولا سر فيها أبدًا.
"""

import logging

logger = logging.getLogger("sovereign.ollama")

# R-736: آخر نتيجة استدعاء (عملية واحدة في الذاكرة — لا كتابة قرص).
# "none" = لم يُستدعَ العقل بعد في هذه العملية.
_LAST_OUTCOME = {"result": "none", "error": None}


def last_outcome():
    """آخر نتيجة استدعاء للعقل (بلا محتوى ولا سر) — لعرضها في /brain/status."""
    return dict(_LAST_OUTCOME)


def chat(system_prompt: str, user_message: str, timeout=None,
         json_mode: bool = False, max_tokens=None, json_schema=None,
         history=None):
    """توليد رد عبر العقل (Ollama أو متوافق OpenAI) — يعيد نص النموذج أو None.

    لا يُستدعى فعليًا إلا إذا كان العقل مفعّلًا (OLLAMA_ENABLED + نموذج)
    — تحقق المستدعي أو هذا الشرط هنا: كلاهما رخيص.

    R-765: json_mode=True يقيّد الخرج بكائن JSON (Ollama: format=json؛
    OpenAI: response_format=json_object)، وmax_tokens يسقف التوليد (Ollama:
    options.num_predict). الافتراضي بلا أي منهما — الحمولة كما كانت.
    json_schema (Ollama فقط): مخطط JSON يقيّد فك الترميز نفسه (format=<schema>)
    — مثل تعداد أسماء الأدوات الحقيقية فلا يُخترع اسم؛ متوافق OpenAI يبقى
    على json_object (الأوسع دعمًا بين المزودين).
    """
    global _LAST_OUTCOME
    import config

    if not (config.OLLAMA_ENABLED and config.OLLAMA_MODEL):
        return None

    timeout = timeout or config.OLLAMA_TIMEOUT_SECONDS
    protocol = getattr(config, "OLLAMA_PROTOCOL", "ollama")
    try:
        import httpx

        headers = {"Content-Type": "application/json"}
        if config.OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {config.OLLAMA_API_KEY}"

        payload = {
            "model": config.OLLAMA_MODEL,
            # R-786: history = أدوار سابقة [{role: user|assistant, content}] بين
            # تعليمات النظام والرسالة الحالية — أي دور آخر (system مثلًا) يُسقط.
            "messages": (
                [{"role": "system", "content": system_prompt}]
                + [
                    {"role": t["role"], "content": str(t["content"])}
                    for t in (history or [])
                    if isinstance(t, dict) and t.get("role") in ("user", "assistant") and t.get("content")
                ]
                + [{"role": "user", "content": user_message}]
            ),
            "stream": False,
        }
        if protocol == "openai":
            if json_mode or json_schema:
                payload["response_format"] = {"type": "json_object"}
            if max_tokens:
                payload["max_tokens"] = int(max_tokens)
        elif protocol == "ollama":
            if json_schema:
                payload["format"] = json_schema
            elif json_mode:
                payload["format"] = "json"
            if max_tokens:
                payload["options"] = {"num_predict": int(max_tokens)}
            # R-787: نافذة السياق — افتراض Ollama (2048/4096) يقطع نتائج الأدوات بصمت
            _num_ctx = int(getattr(config, "OLLAMA_NUM_CTX", 0) or 0)
            if _num_ctx > 0:
                payload.setdefault("options", {})["num_ctx"] = _num_ctx
        base = str(config.OLLAMA_BASE_URL).rstrip("/")
        if protocol == "openai":
            # BASE_URL بادئة الإصدار كاملة (مثل .../openai/v1) — يُلحق
            # /chat/completions مرة واحدة فقط، فلا يتكرر مسار الإصدار.
            url = f"{base}/chat/completions"
        elif protocol == "ollama":
            url = f"{base}/api/chat"
        else:
            # R-736: بروتوكول مجهول → إغلاق (fail-closed) بلا أي طلب.
            # لا صدى للقيمة الخام في السجل (قد تحمل سرًا) — تصنيف ثابت فقط.
            logger.warning(
                "R-736 [BRAIN]: بروتوكول عقل غير معروف (تصنيف: unknown_protocol) "
                "— سقوط للمحرك القالبي",
            )
            _LAST_OUTCOME = {"result": "misconfigured", "error": "unknown_protocol"}
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
            _LAST_OUTCOME = {"result": "ok", "error": None}
            return content.strip()
        logger.warning("R-704 [OLLAMA]: رد فارغ/فاسد — سقوط للمحرك القالبي")
        _LAST_OUTCOME = {"result": "error", "error": "empty_or_malformed_response"}
        return None
    except Exception as e:
        # لا مفتاح ولا محتوى محادثة في السجلات — نوع الخطأ فقط
        logger.warning(
            "R-704 [OLLAMA]: فشل خادم العقل (%s) — سقوط للمحرك القالبي",
            type(e).__name__,
        )
        _LAST_OUTCOME = {"result": "error", "error": type(e).__name__}
        return None
