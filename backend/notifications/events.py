# -*- coding: utf-8 -*-
"""R-845: الأحداث — ما يستحق إشعار المالك، وبأي شدة، وبأي مفتاح عدم تكرار.

مبدأ أقل بيانات: القنوات الخارجية تتلقى ``title`` و``summary`` و``link`` فقط
(معرّفات ونوع الحدث)، ونص الرد الكامل (``body``، بعد التنقية) يبقى في
الصندوق الداخلي. نص الطلب الأصلي لا يغادر الخادم أبدًا.
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, Optional

SEVERITIES = ("info", "medium", "high", "critical")

# الحدث ⇒ (الشدة، العنوان)
EVENTS: Dict[str, tuple] = {
    "approval.requested": ("high", "موافقة مطلوبة"),
    "review.required": ("critical", "مراجعة المالك مطلوبة — نتيجة كتابة غير مؤكدة"),
    "clarification.needed": ("medium", "توضيح مطلوب"),
    "loop.failed": ("medium", "فشلت حلقة"),
    "job.dead": ("high", "مهمة ميتة في الطابور — استُنفدت المحاولات"),
    "job.failed": ("medium", "فشلت مهمة في الطابور"),
    "eval.failed": ("high", "فشل التقييم المستقل تحت الأرضية"),
    "notify.test": ("high", "إشعار تجريبي"),
    # R-846: الجاهزية — مرة لكل (حالة، فحص، ساعة)
    "health.failing": ("critical", "الجاهزية: فحص فاشل"),
    "health.degraded": ("high", "الجاهزية: تدهور"),
    # R-847: النسخ والاستعادة
    "backup.failed": ("high", "فشل النسخ الاحتياطي"),
    "backup.offsite_failed": ("high", "تعذر رفع النسخة خارج الخادم"),
    "restore.staged": ("high", "استعادة مجهزة — تُطبق عند إعادة التشغيل"),
    "restore.applied": ("high", "طُبقت الاستعادة"),
    "restore.failed": ("critical", "فشلت الاستعادة — تراجع إلى ما قبلها"),
}

_SECRETISH = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|sbp_[A-Za-z0-9]{8,}"
    r"|rnd_[A-Za-z0-9]{8,}|sk-[A-Za-z0-9_-]{8,}|xox[abprs]-[A-Za-z0-9-]{8,}"
    r"|Bearer\s+[A-Za-z0-9._-]{8,}|\b\d{6,12}:[A-Za-z0-9_-]{30,})")


def scrub(text: Any, limit: int = 500) -> str:
    """لا سر في نص يُحفظ أو يُرسل (يشمل نمط رمز بوت Telegram)."""
    return _SECRETISH.sub("***", str(text or ""))[:limit]


def rank(sev: str) -> int:
    return SEVERITIES.index(sev) if sev in SEVERITIES else len(SEVERITIES)


def _link(path: str) -> str:
    base = os.environ.get("SOVEREIGN_PUBLIC_URL", "").strip().rstrip("/")
    return f"{base}{path}" if base.startswith("https://") else path


def make(event: str, dedupe_key: str, subject: str, summary: str,
         body: str = "", link: str = "") -> Dict[str, Any]:
    if event not in EVENTS:
        raise ValueError(f"حدث غير معروف: {event}")
    sev, title = EVENTS[event]
    return {"event": event, "severity": sev, "title": title,
            "dedupe_key": dedupe_key[:200], "subject": subject[:100],
            "summary": scrub(summary, 200), "body": scrub(body or summary, 500),
            "link": _link(link) if link else ""}


def from_loop(view: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """حالة حلقة منسق ⇒ حدث أو None. يُستدعى عند كل ``_finalize``."""
    status = view.get("status")
    lid = str(view.get("loop_id") or "")
    if not lid:
        return None
    short, link = lid[:8], f"/orchestrator/loops/{lid}"
    reply = view.get("reply") or ""
    if status == "pending_approval":
        ap = view.get("pending_approval") or {}
        aid = str(ap.get("approval_id") or "")
        if not aid:
            return None
        return make("approval.requested", f"approval.requested:{aid}", lid,
                    f"الحلقة {short} تنتظر موافقتك على الخطوة {ap.get('step_id', '?')}"
                    f" (الموافقة {aid[:8]})", reply, link)
    if status == "needs_owner_review":
        return make("review.required", f"review.required:{lid}", lid,
                    f"الحلقة {short}: انقطاع أثناء كتابة — لم تُعَد تلقائيًا، تحقق يدويًا",
                    reply, link)
    if status == "needs_clarification":
        h = hashlib.sha256(reply.encode("utf-8")).hexdigest()[:10]
        return make("clarification.needed", f"clarification.needed:{lid}:{h}", lid,
                    f"الحلقة {short} تحتاج توضيحًا منك", reply, link)
    if status == "failed":
        return make("loop.failed", f"loop.failed:{lid}", lid,
                    f"الحلقة {short} فشلت", reply, link)
    return None


def from_job(job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """مهمة طابور انتهت ⇒ حدث أو None.

    فشل مهمة مرتبطة بحلقة يغطيه حدث الحلقة نفسه (لا إشعاران لسبب واحد).
    """
    if not job:
        return None
    jid, status, kind = str(job.get("id")), job.get("status"), job.get("kind", "?")
    link = f"/queue/jobs/{jid}"
    err = job.get("error") or ""
    if status == "dead":
        return make("job.dead", f"job.dead:{jid}", jid,
                    f"المهمة {jid[:8]} ({kind}) ماتت بعد {job.get('attempts', '?')} محاولة",
                    err, link)
    res = job.get("result") or {}
    if kind == "evaluation.run" and res.get("pass") is False:
        return make("eval.failed", f"eval.failed:{jid}", jid,
                    f"تقرير التقييم {str(res.get('report_id', ''))[:8]} تحت الأرضية",
                    err, link)
    if kind == "backup.create":
        return None  # R-847: الخدمة تُصدر backup.failed بسببه — لا إشعاران لسبب واحد
    if status == "failed" and not job.get("loop_id"):
        return make("job.failed", f"job.failed:{jid}", jid,
                    f"المهمة {jid[:8]} ({kind}) فشلت", err, link)
    return None
