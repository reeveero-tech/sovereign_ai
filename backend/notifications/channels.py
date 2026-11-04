# -*- coding: utf-8 -*-
"""R-845: القنوات الخارجية — لكل قناة وصف وخطر وشرط إعداد صريح.

لا قناة تُرسل بلا إعداد كامل. الإعداد من البيئة فقط، ولا يُعاد أي سر
أو رابط في الواجهة أو السجلات أو رسائل الخطأ.

تصنيف ردود HTTP (لا إعادة عمياء):
- 2xx ⇒ أُرسل.
- 401/403 ⇒ ``auth``: نهائي، والقناة تُعطَّل حتى يتغير إعدادها.
- 400/404/413/422 وغيرها من 4xx ⇒ ``permanent``: نهائي لهذا الإشعار.
- 408/425/429/5xx وأعطال الشبكة والمهلة ⇒ ``transient``: إعادة بتأخير أسي.
"""
from __future__ import annotations

import abc
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

from .events import rank, scrub

HTTP_TIMEOUT_S = 10.0
MIN_SECRET_LEN = 16


class SendError(Exception):
    def __init__(self, kind: str, message: str, status: int = 0):
        super().__init__(message)
        if kind not in ("transient", "permanent", "auth"):
            raise ValueError(kind)
        self.kind, self.status = kind, status


def _urllib_post(url: str, body: bytes, headers: Dict[str, str],
                 timeout: float) -> Tuple[int, str]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec — https مفروض
            return r.status, r.read(2000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read(2000) or b"").decode("utf-8", "replace")


# النقل قابل للحقن (التقييم والاختبارات) — الافتراضي urllib حقيقي
TRANSPORT: Callable[[str, bytes, Dict[str, str], float], Tuple[int, str]] = _urllib_post


def _post(url: str, body: bytes, headers: Dict[str, str], channel: str) -> None:
    try:
        status, text = TRANSPORT(url, body, headers, HTTP_TIMEOUT_S)
    except (TimeoutError, ConnectionError, OSError) as exc:
        # رسالة الخطأ قد تحوي الرابط (وفيه رمز Telegram) ⇒ نوع الخطأ فقط
        raise SendError("transient", f"{channel}: عطل شبكة ({type(exc).__name__})") from None
    if 200 <= status < 300:
        return
    detail = f"{channel}: HTTP {status} {scrub(text, 120)}"
    if status in (401, 403):
        raise SendError("auth", detail, status)
    if status in (408, 425, 429) or status >= 500:
        raise SendError("transient", detail, status)
    raise SendError("permanent", detail, status)


class Channel(abc.ABC):
    """قناة مجردة — لا تُنشأ قناة ناقصة (abc يرفض الإنشاء قبل التنفيذ)."""

    name = ""
    description = ""
    risk = "medium"
    risk_reason = ""

    def min_severity(self) -> str:
        v = os.environ.get(f"SOVEREIGN_NOTIFY_{self.name.upper()}_MIN_SEVERITY", "").strip()
        return v if rank(v) < 4 else os.environ.get("SOVEREIGN_NOTIFY_MIN_SEVERITY",
                                                    "high").strip() or "high"

    @abc.abstractmethod
    def configured(self) -> Tuple[bool, str]:
        """(مضبوطة؟، السبب)."""

    @abc.abstractmethod
    def fingerprint(self) -> str:
        """بصمة الإعداد (لا تكشفه) — تغيّرها يرفع تعطيل المصادقة."""

    @abc.abstractmethod
    def send(self, n: Dict[str, Any]) -> None:
        """يرسل أو يرفع SendError."""

    def public(self) -> Dict[str, Any]:
        ok, reason = self.configured()
        return {"channel": self.name, "description": self.description, "risk": self.risk,
                "risk_reason": self.risk_reason, "configured": ok, "reason": reason,
                "min_severity": self.min_severity()}


def _fp(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:16]


def _external_payload(n: Dict[str, Any]) -> Dict[str, Any]:
    """أقل بيانات: لا body ولا نص طلب — معرّفات وعنوان وملخص ورابط."""
    return {"id": n["notification_id"] if "notification_id" in n else n["id"],
            "event": n["event"], "severity": n["severity"], "title": n["title"],
            "summary": n["summary"], "link": n["link"], "created_at": n["created_at"]}


class WebhookChannel(Channel):
    name = "webhook"
    description = ("POST بصيغة JSON إلى رابط HTTPS يملكه المالك، موقّع HMAC-SHA256"
                   " (X-Sovereign-Signature)، ومع Idempotency-Key = معرّف الإشعار"
                   " ليستطيع المستقبِل إسقاط التكرار.")
    risk = "medium"
    risk_reason = "يرسل معرّفات وملخصًا إلى خادم خارجي — بلا نص الطلب أو الأسرار"

    def _cfg(self) -> Tuple[str, str]:
        return (os.environ.get("SOVEREIGN_NOTIFY_WEBHOOK_URL", "").strip(),
                os.environ.get("SOVEREIGN_NOTIFY_WEBHOOK_SECRET", ""))

    def configured(self) -> Tuple[bool, str]:
        url, secret = self._cfg()
        if not url:
            return False, "SOVEREIGN_NOTIFY_WEBHOOK_URL غير مضبوط"
        if not url.startswith("https://"):
            return False, "الرابط ليس https:// — لا إرسال بلا تشفير"
        if len(secret) < MIN_SECRET_LEN:
            return False, f"SOVEREIGN_NOTIFY_WEBHOOK_SECRET مفقود أو أقصر من {MIN_SECRET_LEN} — لا إرسال بلا توقيع"
        return True, "مضبوط"

    def fingerprint(self) -> str:
        return _fp(*self._cfg())

    def send(self, n: Dict[str, Any]) -> None:
        url, secret = self._cfg()
        payload = _external_payload(n)
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ts = str(int(time.time()))
        sig = hmac.new(secret.encode("utf-8"), ts.encode() + b"." + body,
                       hashlib.sha256).hexdigest()
        _post(url, body, {"Content-Type": "application/json; charset=utf-8",
                          "Idempotency-Key": payload["id"],
                          "X-Sovereign-Event": payload["event"],
                          "X-Sovereign-Timestamp": ts,
                          "X-Sovereign-Signature": f"sha256={sig}"}, self.name)


class TelegramChannel(Channel):
    name = "telegram"
    description = ("رسالة نصية عبر بوت Telegram إلى محادثة المالك (sendMessage، نص"
                   " خام بلا parse_mode فلا حقن تنسيق).")
    risk = "medium"
    risk_reason = ("يرسل معرّفات وملخصًا إلى Telegram؛ لا يدعم Telegram مفتاح عدم تكرار،"
                   " فإعادة بعد مهلة غامضة قد تكرر الرسالة (أقل مرة واحدة)")

    def _cfg(self) -> Tuple[str, str]:
        return (os.environ.get("SOVEREIGN_TELEGRAM_BOT_TOKEN", "").strip(),
                os.environ.get("SOVEREIGN_TELEGRAM_CHAT_ID", "").strip())

    def configured(self) -> Tuple[bool, str]:
        tok, chat = self._cfg()
        if not tok or ":" not in tok:
            return False, "SOVEREIGN_TELEGRAM_BOT_TOKEN غير مضبوط أو غير صالح"
        if not chat:
            return False, "SOVEREIGN_TELEGRAM_CHAT_ID غير مضبوط"
        return True, "مضبوط"

    def fingerprint(self) -> str:
        return _fp(*self._cfg())

    def send(self, n: Dict[str, Any]) -> None:
        tok, chat = self._cfg()
        p = _external_payload(n)
        text = f"[{p['severity']}] {p['title']}\n{p['summary']}"
        if p["link"]:
            text += f"\n{p['link']}"
        body = json.dumps({"chat_id": chat, "text": text[:4000],
                           "disable_web_page_preview": True},
                          ensure_ascii=False).encode("utf-8")
        _post(f"https://api.telegram.org/bot{tok}/sendMessage", body,
              {"Content-Type": "application/json; charset=utf-8"}, self.name)


def all_channels() -> List[Channel]:
    return [WebhookChannel(), TelegramChannel()]


def by_name() -> Dict[str, Channel]:
    return {c.name: c for c in all_channels()}


def eligible(ch: Channel, severity: str) -> Tuple[str, str]:
    """(الحالة الأولية، السبب) لتسليم إشعار بهذه الشدة على هذه القناة."""
    ok, reason = ch.configured()
    if not ok:
        return "skipped", f"غير مضبوطة: {reason}"
    if rank(severity) < rank(ch.min_severity()):
        return "skipped", f"تحت الحد الأدنى للشدة ({ch.min_severity()})"
    return "pending", ""


def get(name: str) -> Optional[Channel]:
    return by_name().get(name)
