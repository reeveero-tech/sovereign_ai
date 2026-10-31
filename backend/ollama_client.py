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
import os
import time

logger = logging.getLogger("sovereign.ollama")

# R-736: آخر نتيجة استدعاء (عملية واحدة في الذاكرة — لا كتابة قرص).
# "none" = لم يُستدعَ العقل بعد في هذه العملية.
_LAST_OUTCOME = {"result": "none", "error": None}

# ============================================================
# R-821: مزلاج وصول العقل (نصف-مفتوح) — إحياء سرعة السقوط الرشيد
# ============================================================
# المشكلة الحية (لوحظت على النشر): العقل مفعّل (OLLAMA_ENABLED=true) لكن
# المزود بعيد (خادم Ollama على شبكة المالك الخاصة لا تصل إليها السحابة) —
# كل استدعاء عقل ينتظر مهلة كاملة (3-60ث) قبل السقوط للقالبي، ودورة
# المحادثة تستدعي العقل مرات عدة فتصبح المحادثة بطيئة جدًا (دقائق).
# المزلاج: أول فشل اتصال يُغلق الدائرة لمدة تهدئة (60ث افتراضيًا) —
# خلالها كل استدعاء يعيد None فورًا (بلا انتظار) والمستدعي يسقط للقالبي
# بسرعة كاملة. أول نجاح (أو انقضاء الهدوء) يعيد المحاولة — نمط نصف-مفتوح:
# لا يمنع الاسترداد أبدًا، فقط يوقف الطوفان البطيء. قابل للضبط:
# OLLAMA_UNREACHABLE_COOLDOWN_SECONDS=0 يعطّل المزلاج تمامًا.
_UNREACHABLE_UNTIL = 0.0
_LATCH_FAILURES = 0
_LATCH_KEY = None


def _brain_latch_key():
    """هوية العقل الحالية — تغيّرها (بروتوكول/عنوان/نموذج) يعيد ضبط المزلاج.

    يلتقط تبديل المالك الحي للمزود من الواجهة (طبقة التشغيل فوق البيئة)
    وتبديل الاختبارات للعقل الوهمي (منفذ جديد لكل اختبار) — الدائرة لا
    تعاقب مزودًا جديدًا بذنب المزود السابق.
    """
    try:
        import config
        return (
            str(config.brain_get("OLLAMA_PROTOCOL", "ollama") or "ollama"),
            str(config.brain_get("OLLAMA_BASE_URL", "") or ""),
            str(config.brain_get("OLLAMA_MODEL", "") or ""),
        )
    except Exception:
        return ()


def _latch_sync_key():
    """ضبط المزلاج على هوية العقل الحالية — إعادة ضبط عند أي تبديل."""
    global _LATCH_KEY, _UNREACHABLE_UNTIL, _LATCH_FAILURES
    k = _brain_latch_key()
    if k != _LATCH_KEY:
        _LATCH_KEY = k
        _UNREACHABLE_UNTIL = 0.0
        _LATCH_FAILURES = 0


def _latch_cooldown_seconds() -> float:
    try:
        return max(0.0, float(os.getenv(
            "OLLAMA_UNREACHABLE_COOLDOWN_SECONDS", "60",
        )))
    except ValueError:
        return 60.0


def _connect_timeout(total: float) -> float:
    """R-821: مهلة الاتصال وحدها — قصيرة دائمًا.

    ميزانية الوكيل (deadline) تُمرر كمهلة كلية للنداء الواحد — لكنها
    مهلة قراءة/توليد، ليست مهلة انتظار اتصال. الخادم البعيد (شبكة خاصة
    لا تصلها السحابة مثلًا) كان ينتظر الميزانية كاملة قبل فشل الاتصال،
    فكانت أول محادثة تستغرق دقائق. الاتصال الناجح (خادم المالك الحي)
    يستمر بمهلة التوليد الكاملة كما هو — لا خسارة أبدًا.
    """
    try:
        cap = float(os.getenv("OLLAMA_CONNECT_TIMEOUT_SECONDS", "3"))
    except ValueError:
        cap = 3.0
    if cap <= 0:
        return total
    return min(total, max(0.5, cap))


def _brain_latch_open() -> bool:
    """هل الدائرة مفتوحة الآن (تخطي الاتصال والسقوط الفوري)؟"""
    _latch_sync_key()
    return time.monotonic() < _UNREACHABLE_UNTIL


def _brain_latch_trip() -> None:
    """افتتاح الدائرة بعد فشل — لمدة الهدوء فقط."""
    global _UNREACHABLE_UNTIL, _LATCH_FAILURES
    _latch_sync_key()
    _LATCH_FAILURES += 1
    cooldown = _latch_cooldown_seconds()
    _UNREACHABLE_UNTIL = time.monotonic() + cooldown
    if cooldown > 0:
        logger.warning(
            "R-821 [BRAIN]: مزلاج الوصول مفتوح لمدة %.0fث (فشل متوالٍ #%d) — "
            "سقوط فوري للمحرك القالبي خلال الهدوء",
            cooldown, _LATCH_FAILURES,
        )


def _brain_latch_reset() -> None:
    """إغلاق الدائرة عند أول نجاح — لا عقوبة على العقل الحي."""
    global _UNREACHABLE_UNTIL, _LATCH_FAILURES
    _latch_sync_key()
    if _LATCH_FAILURES or _UNREACHABLE_UNTIL:
        _LATCH_FAILURES = 0
        _UNREACHABLE_UNTIL = 0.0


def last_outcome():
    """آخر نتيجة استدعاء للعقل (بلا محتوى ولا سر) — لعرضها في /brain/status."""
    return dict(_LAST_OUTCOME)


def list_models(timeout=None):
    """R-810 (المالك — البند ٢): اكتشاف النماذج المتاحة من العقل المُعد فعليًا.

    لا وهم ولا قائمة ثابتة: تُستعلم نهاية المزود الحيّة (ollama: ‹/api/tags›،
    openai المتوافق: ‹/models›) ويعاد ما أعلنه المزود نفسه، أو خطأ صادق منضبط.
    الإعدادات من config.brain_get — نفس مصدر حقيقة العميل الحي، فالتبديل
    الحي يسري على الاكتشاف والاستدعاء معًا.
    """
    import config

    if not config.brain_get("OLLAMA_ENABLED"):
        return {"ok": False, "error": "disabled", "models": []}
    # R-821: دائرة الوصول مفتوحة — اكتشاف فوري بلا انتظار مهلة
    if _brain_latch_open():
        return {"ok": False, "error": "unreachable_latched", "models": []}
    protocol = str(config.brain_get("OLLAMA_PROTOCOL", "ollama") or "ollama").strip().lower() or "ollama"
    base = str(config.brain_get("OLLAMA_BASE_URL")).rstrip("/")
    if protocol == "ollama":
        url = f"{base}/api/tags"
    elif protocol == "openai":
        url = f"{base}/models"
    else:
        # R-736: بروتوكول مجهول يُغلق fail-closed — لا قائمة مختلَقة
        return {"ok": False, "error": "unknown_protocol", "models": []}
    try:
        import httpx

        headers = {}
        _api_key = config.brain_get("OLLAMA_API_KEY")
        if _api_key:
            headers["Authorization"] = f"Bearer {_api_key}"
        to = float(timeout or config.brain_get("OLLAMA_TIMEOUT_SECONDS", 60))
        # R-821: مهلة اتصال قصيرة — الاكتشاف لا ينتظر ميزانية كاملة على خادم بعيد
        resp = httpx.get(url, headers=headers, timeout=httpx.Timeout(to, connect=_connect_timeout(to)))
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}", "models": []}
        payload = resp.json()
    except Exception as e:  # فشل الاتصال صادق ومنضبط — لا استثناء يكسر الواجهة
        _brain_latch_trip()  # R-821: فشل اكتشاف يفتح الدائرة أيضًا
        return {"ok": False, "error": type(e).__name__, "models": []}
    _brain_latch_reset()  # R-821: اتصال حي ناجح
    models = []
    try:
        if protocol == "ollama":
            for m in payload.get("models", []):
                name = (m or {}).get("name") or (m or {}).get("model")
                if name:
                    models.append(name)
        else:
            for m in payload.get("data", []):
                name = (m or {}).get("id")
                if name:
                    models.append(name)
    except (AttributeError, TypeError):
        return {"ok": False, "error": "bad_payload", "models": []}
    models = sorted(set(models))
    return {"ok": True, "error": None, "models": models}


def chat(system_prompt: str, user_message: str, timeout=None,
         json_mode: bool = False, max_tokens=None, json_schema=None,
         history=None, model=None):
    """توليد رد عبر العقل (Ollama أو متوافق OpenAI) — يعيد نص النموذج أو None.

    لا يُستدعى فعليًا إلا إذا كان العقل مفعّلًا (OLLAMA_ENABLED + نموذج)
    — تحقق المستدعي أو هذا الشرط هنا: كلاهما رخيص.

    R-765: json_mode=True يقيّد الخرج بكائن JSON (Ollama: format=json؛
    OpenAI: response_format=json_object)، وmax_tokens يسقف التوليد (Ollama:
    options.num_predict). الافتراضي بلا أي منهما — الحمولة كما كانت.
    json_schema (Ollama فقط): مخطط JSON يقيّد فك الترميز نفسه (format=<schema>)
    — مثل تعداد أسماء الأدوات الحقيقية فلا يُخترع اسم؛ متوافق OpenAI يبقى
    على json_object (الأوسع دعمًا بين المزودين).

    R-810 (المالك — البندان ٢ و٣): كل الإعدادات تُقرأ عبر config.brain_get —
    طبقة التشغيل (تعديلات المالك الحية من الواجهة) فوق البيئة، بلا إعادة تشغيل.
    model: تجاوز النموذج لهذا الطلب فقط (تبديل النماذج)؛ بلا قيمة يُستخدم
    النموذج الفعّال.
    """
    global _LAST_OUTCOME
    import config

    _enabled = config.brain_get("OLLAMA_ENABLED")
    _effective_model = model or config.brain_get("OLLAMA_MODEL")
    if not (_enabled and _effective_model):
        return None

    # R-821: دائرة الوصول مفتوحة (فشل اتصال حديث) — سقوط فوري بلا انتظار مهلة
    if _brain_latch_open():
        _LAST_OUTCOME = {"result": "unreachable_latched", "error": None}
        return None

    timeout = timeout or config.brain_get("OLLAMA_TIMEOUT_SECONDS", 60)
    protocol = str(config.brain_get("OLLAMA_PROTOCOL", "ollama") or "ollama").strip().lower() or "ollama"
    try:
        import httpx

        headers = {"Content-Type": "application/json"}
        _api_key = config.brain_get("OLLAMA_API_KEY")
        if _api_key:
            headers["Authorization"] = f"Bearer {_api_key}"

        payload = {
            "model": _effective_model,
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
            _num_ctx = int(config.brain_get("OLLAMA_NUM_CTX", 0) or 0)
            if _num_ctx > 0:
                payload.setdefault("options", {})["num_ctx"] = _num_ctx
        base = str(config.brain_get("OLLAMA_BASE_URL")).rstrip("/")
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
        # R-821: مهلة الاتصال قصيرة (بعيد؟ فشل سريع) ومهلة القراءة/التوليد كاملة
        _to = httpx.Timeout(timeout, connect=_connect_timeout(timeout))
        with httpx.Client(timeout=_to) as client:
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
            _brain_latch_reset()  # R-821: نجاح حي يغلق الدائرة فورًا
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
        # R-799: رمز HTTP الحرفي (500/400/404...) — دليل حي: «HTTPStatusError» وحده لا يشخّص
        code = getattr(getattr(e, "response", None), "status_code", None)
        kind = type(e).__name__ + (f":{code}" if code else "")
        _LAST_OUTCOME = {"result": "error", "error": kind}
        _brain_latch_trip()  # R-821: فشل اتصال يفتح الدائرة لمدة الهدوء
        return None
