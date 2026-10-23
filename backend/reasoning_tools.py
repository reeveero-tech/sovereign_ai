"""محور الاستدلال — الاستنتاج والاستخراج والاستنباط والتنقيح والاستدلال
(R-738 — بأمر المالك «أقوى أدوات العالم»).

خمس أدوات استدلال تعمل عبر عقل المنشور (ollama_client — بروتوكولا R-736):
- extract(text, schema)  — استخراج منظّم: نص → JSON بالحقول المطلوبة.
- infer(premises)        — استنتاج: وقائع → استنتاجات صريحة.
- deduce(question, ctx)  — استنباط: سياق → فرضيات وما لم يُصرح به.
- verify(claim, evidence)— تنقيح: ادعاء × دليل → حكم مدعوم.
- reason(question, ctx) — استدلال: سؤال × سياق → استنتاج خطوة بخطوة.

fail-closed في كل شيء: العقل معطل → خطأ صادق؛ استجابة فاسدة → خطأ لا
مخرجات مختلقة (المادة ١ — لا ادعاء بلا دليل).
"""

import json
import re

import logging

logger = logging.getLogger("sovereign.reasoning")


def _brain_chat(system_prompt: str, user_text: str) -> str:
    import config
    import ollama_client

    if not (config.OLLAMA_ENABLED and config.OLLAMA_MODEL):
        raise RuntimeError("العقل معطل — لا استدلال (OLLAMA_ENABLED)")
    reply = ollama_client.chat(system_prompt, user_text)
    if not reply:
        raise RuntimeError("العقل لم يُرجع ردًا — لا استدلال مختلق")
    return reply


def _require_str_list(value, name):
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} مطلوب")
    return [str(v) for v in value][:20]


def extract(text: str, schema: str):
    """الاستخراج المنظّم: نص → JSON بالحقول الموصوفة في schema."""
    text = str(text or "").strip()[:8000]
    schema = str(schema or "").strip()[:500]
    if not text or not schema:
        raise ValueError("نص ووصف حقول مطلوبان")
    reply = _brain_chat(
        "أنت مستخرج بيانات دقيق. أعد JSON فقط (بلا سياج كود) بمفاتيح "
        "عربية مطابقة للحقول المطلوبة، من النص حصريًا — لا تخترع قيمًا؛ "
        "ما ليس في النص اجعل قيمته فارغة.",
        f"الحقول المطلوبة: {schema}\n\nالنص:\n{text}")
    # التقاط JSON حتى داخل سياج كود أو نص محيط
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    if not match:
        logger.warning("R-738 [reasoning]: رد بلا JSON — لا استخراج مختلق")
        raise RuntimeError("فشل الاستخراج — الرد ليس JSON")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise RuntimeError("فشل الاستخراج — JSON فاسد") from e
    if not isinstance(data, dict):
        raise RuntimeError("فشل الاستخراج — بنية غير متوقعة")
    fields = [f.strip() for f in re.split(r"[،,؛;]", schema) if f.strip()]
    return {"extraction": data, "fields": fields}


def infer(premises):
    """الاستنتاج: من الوقائع إلى استنتاجات صريحة (لا اختراع)."""
    facts = _require_str_list(premises, "الوقائع")
    reply = _brain_chat(
        "أنت محلل منطقي. استنتج من الوقائع حصريًا استنتاجات صريحة تتبع "
        "منها مباشرة. أعد كل استنتاج في سطر يبدأ بشرطة (-) — بلا اختراع "
        "معلومات ليست في الوقائع.",
        "\n".join(f"- {f}" for f in facts))
    conclusions = [ln.lstrip("-• ").strip()
                   for ln in reply.splitlines() if ln.strip().startswith(("-", "•"))]
    if not conclusions:
        raise RuntimeError("فشل الاستنتاج — لا استنتاجات صريحة")
    return {"conclusions": conclusions[:20]}


def deduce(question: str, context: str = ""):
    """الاستنباط: فرضيات واستنتاجات ضمنية من السياق (موسومة كفرضيات)."""
    question = str(question or "").strip()[:1000]
    if not question:
        raise ValueError("سؤال مطلوب")
    reply = _brain_chat(
        "أنت مُنَبِّه بصير. من السياق والسؤال، اقترح فرضيات واستنتاجات "
        "ضمنية (ما لم يُصرح به نصًا). أعد كل فرضية في سطر يبدأ بشرطة (-) "
        "وابتدئها بكلمة «فرضية:» — ميّزها صراحة عن الوقائع المصرح بها.",
        f"السؤال: {question}\n\nالسياق:\n{str(context or 'لا يوجد')[:4000]}")
    hypotheses = [ln.lstrip("-• ").strip()
                  for ln in reply.splitlines()
                  if ln.strip().startswith(("-", "•")) and ln.strip()]
    if not hypotheses:
        raise RuntimeError("فشل الاستنباط — لا فرضيات")
    return {"hypotheses": hypotheses[:20]}


def verify(claim: str, evidence: str):
    """التنقيح: حكم على ادعاء مقابل دليل — مدعوم/منقوض/غير كافٍ مع التعليل."""
    claim = str(claim or "").strip()[:1000]
    evidence = str(evidence or "").strip()[:8000]
    if not claim:
        raise ValueError("ادعاء مطلوب")
    reply = _brain_chat(
        "أنت مدقق صارم. قيّم الادعاء مقابل الدليل حصريًا: ابدأ سطر الحكم "
        "بـ«الحكم:» (مدعوم/منقوض/غير كافٍ) ثم علل من الدليل نفسه — لا "
        "استشهاد بمصادر خارج الدليل المعطى.",
        f"الادعاء: {claim}\n\nالدليل:\n{evidence or 'لا يوجد'}")
    if "الحكم:" not in reply:
        raise RuntimeError("فشل التنقيح — لا حكم صريح")
    verdict = reply.split("الحكم:", 1)[1].splitlines()[0].strip()
    return {"verdict": verdict, "reasoning": reply.strip()[:2000]}


def reason(question: str, context: str = ""):
    """الاستدلال: خطوات منطقية وصولًا إلى استنتاج — من السياق حصرًا."""
    question = str(question or "").strip()[:1000]
    if not question:
        raise ValueError("سؤال مطلوب")
    reply = _brain_chat(
        "أنت مُستدل دقيق. فكر خطوة بخطوة بالعربية ثم ابدأ الخلاصة بكلمة "
        "«الخلاصة:». لا تستخدم معلومات من خارج السياق المعطى.",
        f"السؤال: {question}\n\nالسياق:\n{str(context or 'لا يوجد')[:4000]}")
    return {"reasoning": reply.strip()[:4000]}
