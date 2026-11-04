# -*- coding: utf-8 -*-
"""R-845: الموزع — يحجز التسليمات المستحقة ويرسلها بحدود صريحة.

حدود (ممنوع «حلقة بلا حد»):
- ``dispatch_once(limit)``: سقف صلب ``MAX_BATCH``.
- ``MAX_ATTEMPTS`` محاولات للعابر فقط، بتأخير أسي 5، 10، 20... بسقف 600ث.
- ``max_per_hour`` لكل قناة: الزائد يصبح ``suppressed`` (ويبقى في الصندوق الداخلي)
  بدل إغراق المالك.
- 401/403 ⇒ لا إعادة، والقناة تُعطَّل ببصمة إعدادها (لا إعادة عمياء على 401/403).

لماذا الموزع مستقل عن الطابور (R-844): إشعار «مهمة ميتة» أو «الطابور ممتلئ»
لا يصح أن يعتمد على الطابور نفسه.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

from . import channels as ch_mod
from .events import scrub
from .store import OutboxStore

_log = logging.getLogger("notifications.dispatcher")

MAX_BATCH = 50
MAX_ATTEMPTS = 5
BACKOFF_BASE_S = 5.0
BACKOFF_CAP_S = 600.0


def backoff_s(attempt: int) -> float:
    return min(BACKOFF_BASE_S * (2 ** max(0, attempt - 1)), BACKOFF_CAP_S)


class Dispatcher:
    def __init__(self, store: OutboxStore,
                 channels: Optional[Callable[[], Dict[str, ch_mod.Channel]]] = None,
                 max_per_hour: int = 30):
        self.store = store
        self.channels = channels or ch_mod.by_name
        self.max_per_hour = max(1, int(max_per_hour))

    def dispatch_once(self, limit: int = 20) -> List[Dict[str, Any]]:
        out = []
        chans = self.channels()
        for d in self.store.claim_due(max(0, min(int(limit), MAX_BATCH))):
            out.append(self._deliver(d, chans))
        return out

    def _deliver(self, d: Dict[str, Any], chans: Dict[str, ch_mod.Channel]
                 ) -> Dict[str, Any]:
        nid, name = d["notification_id"], d["channel"]
        res = {"notification_id": nid, "channel": name, "attempt": d["attempts"]}
        if d["attempts"] > MAX_ATTEMPTS:  # انقطاعات متكررة بعد الحجز — لا دوران بلا حد
            self.store.mark_final(nid, name, "failed", "استُنفدت المحاولات (انقطاعات)")
            return {**res, "status": "failed"}
        ch = chans.get(name)
        if ch is None:
            self.store.mark_final(nid, name, "failed", "قناة غير مسجلة")
            return {**res, "status": "failed"}
        ok, why = ch.configured()
        if not ok:
            self.store.mark_final(nid, name, "failed", f"لم تعد مضبوطة: {why}")
            return {**res, "status": "failed"}
        fp = ch.fingerprint()
        disabled = self.store.channel_disabled(name, fp)
        if disabled:
            self.store.mark_final(nid, name, "failed", f"القناة معطلة: {disabled}")
            return {**res, "status": "failed"}
        if self.store.sent_since(name, self.store.clock() - 3600) >= self.max_per_hour:
            self.store.mark_final(nid, name, "suppressed",
                                  f"حد الإرسال {self.max_per_hour}/ساعة — باقٍ في الصندوق الداخلي")
            return {**res, "status": "suppressed"}
        try:
            ch.send(d)
        except ch_mod.SendError as exc:
            err = scrub(str(exc), 300)
            if exc.kind == "auth":
                self.store.disable_channel(name, err, fp)
                self.store.mark_final(nid, name, "failed", "رفض المصادقة — لا إعادة", err)
                _log.warning("R-845: القناة %s عُطّلت: %s", name, err)
                return {**res, "status": "failed", "error": err, "channel_disabled": True}
            if exc.kind == "transient" and d["attempts"] < MAX_ATTEMPTS:
                self.store.mark_retry(nid, name, backoff_s(d["attempts"]), err)
                return {**res, "status": "retry", "error": err}
            reason = "استُنفدت المحاولات" if exc.kind == "transient" else "رفض نهائي"
            self.store.mark_final(nid, name, "failed", reason, err)
            return {**res, "status": "failed", "error": err}
        except Exception as exc:  # خطأ برمجي غير متوقع — نهائي، لا إعادة عمياء
            err = scrub(f"{type(exc).__name__}: {exc}", 300)
            self.store.mark_final(nid, name, "failed", "خطأ غير متوقع", err)
            return {**res, "status": "failed", "error": err}
        self.store.mark_sent(nid, name)
        return {**res, "status": "sent"}

    def loop(self, stop: threading.Event, poll_s: float = 2.0) -> None:
        while not stop.is_set():
            try:
                did = self.dispatch_once()
            except Exception as exc:  # TOLERATED: عطل المخزن يُسجَّل والموزع يبقى حيًا
                _log.error("R-845: عطل في الموزع: %s", scrub(str(exc)))
                did = []
            if not did:
                stop.wait(poll_s)
