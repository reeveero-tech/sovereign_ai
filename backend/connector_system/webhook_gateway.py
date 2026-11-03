# -*- coding: utf-8 -*-
"""R-840: بوابة Webhooks — استقبال الأحداث بتحقق إلزامي.

- تحقق التوقيع (HMAC-SHA256 بمقارنة ثابتة الزمن) — رفض بلا توقيع صحيح.
- نافذة زمنية ضد إعادة التشغيل (افتراضي ٥ دقائق).
- منع التكرار بمعرّف الحدث (dedup).
- طابور رسائل ميتة (DLQ) للمرفوضات مع السبب.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


class WebhookError(Exception):
    pass


def hmac_sha256_hex(secret: str, data: bytes) -> str:
    return hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()


def verify_hmac(secret: str, body: bytes, signature: str) -> Tuple[bool, str]:
    """تحقق HMAC-SHA256 بمقارنة ثابتة الزمن — يرفض التوقيع الخاطئ."""
    if not signature:
        return False, "لا توقيع"
    expected = hmac_sha256_hex(secret, body)
    if not hmac.compare_digest(expected, signature):
        return False, "توقيع خاطئ — مرفوض"
    return True, ""


class WebhookGateway:
    """بوابة موحدة لكل الموصلات — التحقق قبل أي معالجة."""

    def __init__(self, state_dir, replay_window_s: float = 300.0,
                 max_dlq: int = 200, clock=time.time):
        self.state_dir = str(state_dir)
        self.replay_window_s = replay_window_s
        self.max_dlq = max_dlq
        self.clock = clock
        self._seen: Dict[str, float] = {}
        self._dlq: List[Dict[str, Any]] = []
        self._lock = threading.RLock()  # رفض داخل القفل — إعادة دخول آمنة
        os.makedirs(self.state_dir, exist_ok=True)

    # ------------------------------------------------------------ الاستقبال
    def ingest(self, connector_id: str, secret: str, body: bytes,
               headers: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
        """بوابة الدخول: توقيع → نافذة زمنية → تكرار → قبول."""
        sig_header = (headers.get("X-Hub-Signature-256")
                      or headers.get("X-Signature") or "").replace("sha256=", "")
        ok, reason = verify_hmac(secret, body, sig_header)
        if not ok:
            return self._reject(connector_id, reason, body)

        ts_raw = headers.get("X-Timestamp") or headers.get("X-Ts") or ""
        try:
            ts = float(ts_raw) if ts_raw else self.clock()
        except ValueError:
            return self._reject(connector_id, "طابع زمني غير صالح", body)
        if abs(self.clock() - ts) > self.replay_window_s:
            return self._reject(connector_id,
                                "خارج النافذة الزمنية (اشتباه إعادة تشغيل)", body)

        try:
            event = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._reject(connector_id, "جسم غير JSON", body)

        event_id = str(event.get("id") or event.get("delivery_id")
                      or hashlib.sha256(body).hexdigest()[:16])
        with self._lock:
            if event_id in self._seen:
                return self._reject(connector_id, "duplicate", body,
                                    event_id=event_id)
            self._seen[event_id] = self.clock()
            # تنظيف المقبول فقط — لا DLQ يخفي القبول
            cutoff = self.clock() - 2 * self.replay_window_s
            self._seen = {k: v for k, v in self._seen.items() if v >= cutoff}

        return True, {"connector": connector_id, "event_id": event_id,
                      "accepted": True, "type": event.get("type", "")}

    def _reject(self, connector_id: str, reason: str, body: bytes,
                event_id: str = "") -> Tuple[bool, Dict[str, Any]]:
        with self._lock:
            self._dlq.append({"ts": self.clock(), "connector": connector_id,
                              "reason": reason,
                              "body_fingerprint": hashlib.sha256(body).hexdigest()[:12],
                              "event_id": event_id})
            self._dlq = self._dlq[-self.max_dlq:]
        return False, {"connector": connector_id, "accepted": False,
                      "reason": reason}

    def dead_letter(self) -> List[Dict[str, Any]]:
        return list(self._dlq)
