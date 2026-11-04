# -*- coding: utf-8 -*-
"""R-845: مجموعة موثوقية الإشعارات — سيناريوهات فوق المنسق والطابور الحقيقيين.

المزيف هنا ثلاثة فقط: الشبكة (نقل HTTP يسجل النداءات ويعيد ما يُطلب)،
والساعة، وموت العملية (``Crash`` من نوع BaseException). الصندوق والموزع
والقنوات والتوقيع والمنسق والطابور كلها حقيقية. البيئة تُضبط لكل حالة
وتُستعاد بعدها.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List

from . import queue_reliability as qr

try:
    from notifications import channels as nch
    from notifications import events as nev
    from notifications import service as nsvc
    from notifications.dispatcher import Dispatcher
    from notifications.store import LEASE_S, OutboxStore
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.notifications import channels as nch
    from backend.notifications import events as nev
    from backend.notifications import service as nsvc
    from backend.notifications.dispatcher import Dispatcher
    from backend.notifications.store import LEASE_S, OutboxStore

HOOK_URL = "https://hooks.example.test/sovereign"
HOOK_SECRET = "w" * 32
TG_TOKEN = "123456789:" + "T" * 35
_ENV_KEYS = ("SOVEREIGN_NOTIFY_WEBHOOK_URL", "SOVEREIGN_NOTIFY_WEBHOOK_SECRET",
             "SOVEREIGN_TELEGRAM_BOT_TOKEN", "SOVEREIGN_TELEGRAM_CHAT_ID",
             "SOVEREIGN_NOTIFY_MIN_SEVERITY", "SOVEREIGN_NOTIFY_WEBHOOK_MIN_SEVERITY",
             "SOVEREIGN_NOTIFY_TELEGRAM_MIN_SEVERITY", "SOVEREIGN_PUBLIC_URL")


class _Net:
    """نقل HTTP مزيف: ``responses`` قائمة حالات (أو استثناءات) تُستهلك بالترتيب."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.responses: List[Any] = []
        self.default: Any = 200
        self.crash_next = False

    def __call__(self, url, body, headers, timeout):
        self.calls.append({"url": url, "body": json.loads(body.decode("utf-8")),
                           "raw": body, "headers": dict(headers)})
        if self.crash_next:
            self.crash_next = False
            raise qr.Crash("موت بعد الإرسال وقبل التسجيل")
        r = self.responses.pop(0) if self.responses else self.default
        if isinstance(r, BaseException) or (isinstance(r, type) and issubclass(r, BaseException)):
            raise r if isinstance(r, BaseException) else r("مزيف")
        return int(r), "{}"

    def to(self, host: str) -> List[Dict[str, Any]]:
        return [c for c in self.calls if host in c["url"]]


class NEnv:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.now = [2_000_000.0]
        self.net = _Net()
        self.store = self.new_store()

    def new_store(self) -> OutboxStore:
        return OutboxStore(str(self.tmp / "outbox.sqlite3"), clock=lambda: self.now[0])

    def disp(self, per_hour: int = 30) -> Dispatcher:
        return Dispatcher(self.store, max_per_hour=per_hour)

    def emit(self, ev):
        return nsvc.emit(ev, self.store)

    def advance(self, s: float) -> None:
        self.now[0] += s

    def deliv(self, nid: str, ch: str = "webhook") -> str:
        for d in self.store.deliveries_for(nid):
            if d["channel"] == ch:
                return d["status"]
        return "none"

    def events(self) -> List[str]:
        return sorted(n["event"] for n in self.store.list(limit=200))


def _ev(i: int, event: str = "job.dead") -> Dict[str, Any]:
    return nev.make(event, f"{event}:case-{i}", f"S{i}", f"ملخص {i}")


@contextmanager
def _env(**overrides):
    saved = {k: os.environ.get(k) for k in _ENV_KEYS}
    try:
        for k in _ENV_KEYS:
            os.environ.pop(k, None)
        os.environ["SOVEREIGN_NOTIFY_WEBHOOK_URL"] = HOOK_URL
        os.environ["SOVEREIGN_NOTIFY_WEBHOOK_SECRET"] = HOOK_SECRET
        for k, v in overrides.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _sig_ok(call: Dict[str, Any], secret: str) -> bool:
    h = call["headers"]
    want = hmac.new(secret.encode(), h["X-Sovereign-Timestamp"].encode() + b"." + call["raw"],
                    hashlib.sha256).hexdigest()
    return hmac.compare_digest(h.get("X-Sovereign-Signature", ""), f"sha256={want}")


def _req(session: str, title: str) -> Dict[str, Any]:
    from agent_orchestrator import schemas
    return schemas.new_request(user_id="t", session_id=session,
                               permissions=["orchestrator:write"],
                               utterance=f"افتح مشكلة بعنوان {title} في github.com/acme/webapp")


# ===================================================================== السيناريوهات
def s_approval_requested(e: NEnv) -> Dict[str, Any]:
    q = qr.Env(e.tmp / "q")
    q.o.observers.append(nsvc.loop_observer(e.store))
    secret_title = "عنوان-خاص-N01"
    out = q.o.submit(_req("n01", secret_title))
    e.disp().dispatch_once()
    ns = e.store.list()
    c = e.net.to("hooks.example.test")
    return {"notifications": len(ns), "event": ns[0]["event"] if ns else None,
            "severity": ns[0]["severity"] if ns else None, "webhook_calls": len(c),
            "delivery": e.deliv(ns[0]["id"]) if ns else None,
            "signature_valid": bool(c) and _sig_ok(c[0], HOOK_SECRET),
            "idempotency_key_is_id": bool(c) and bool(ns) and c[0]["headers"].get("Idempotency-Key") == ns[0]["id"],
            "body_sent": bool(c) and "body" in c[0]["body"],
            "utterance_leaked": any(secret_title in c_["raw"].decode() for c_ in e.net.calls),
            "loop": out["status"]}


def s_dedupe(e: NEnv) -> Dict[str, Any]:
    view = {"status": "pending_approval", "loop_id": "L-dedupe",
            "pending_approval": {"approval_id": "A-dedupe", "step_id": "s1"}, "reply": "x"}
    _, c1 = e.emit(nev.from_loop(view))
    _, c2 = e.emit(nev.from_loop(view))
    e.disp().dispatch_once()
    e.disp().dispatch_once()
    return {"created": [c1, c2], "notifications": len(e.store.list()),
            "webhook_calls": len(e.net.calls)}


def s_review_required_telegram(e: NEnv) -> Dict[str, Any]:
    q = qr.Env(e.tmp / "q")
    q.o.observers.append(nsvc.loop_observer(e.store))
    out = q.o.submit(_req("n03", "N03"))
    q.t.crash_on = {"POST"}
    try:
        q.o.decide_approval(out["loop_id"], out["pending_approval"]["approval_id"],
                            "approved", "owner", False)
    except qr.Crash:  # TOLERATED: محاكاة موت العملية — الأثر يُقاس بعد «إعادة التشغيل»
        pass
    q.restart()
    q.o.observers.append(nsvc.loop_observer(e.store))  # الإقلاع يعيد الربط (install)
    r = q.o.run(out["loop_id"])
    e.disp().dispatch_once()
    rev = [n for n in e.store.list() if n["event"] == "review.required"]
    tg = e.net.to("api.telegram.org")
    # نداءات إشعار المراجعة وحده — طلب الموافقة السابق (high) يصل Telegram أيضًا، وهذا صحيح
    tg_rev = [c for c in tg if rev and rev[0]["title"] in c["body"].get("text", "")]
    return {"loop": r["status"], "event": rev[0]["event"] if rev else None,
            "severity": rev[0]["severity"] if rev else None, "telegram_calls": len(tg_rev),
            "telegram_total": len(tg),
            "token_in_text": any(TG_TOKEN in c["raw"].decode() for c in tg),
            "delivery": e.deliv(rev[0]["id"], "telegram") if rev else None}


def s_auth_disables_channel(e: NEnv) -> Dict[str, Any]:
    e.net.default = 401
    n1, _ = e.emit(_ev(1))
    e.disp().dispatch_once()
    first, calls1 = e.deliv(n1["id"]), len(e.net.calls)
    n2, _ = e.emit(_ev(2))
    e.disp().dispatch_once()
    second, calls2 = e.deliv(n2["id"]), len(e.net.calls)
    os.environ["SOVEREIGN_NOTIFY_WEBHOOK_SECRET"] = "r" * 32   # المالك دوّر السر
    e.net.default = 200
    n3, _ = e.emit(_ev(3))
    e.disp().dispatch_once()
    return {"first": first, "calls_after_first": calls1, "second": second,
            "calls_after_second": calls2, "third": e.deliv(n3["id"]),
            "calls_after_rotate": len(e.net.calls)}


def s_transient_then_sent(e: NEnv) -> Dict[str, Any]:
    e.net.responses = [503, 200]
    n, _ = e.emit(_ev(5))
    r1 = e.disp().dispatch_once()
    e.disp().dispatch_once()
    before = len(e.net.calls)
    e.advance(5.1)
    e.disp().dispatch_once()
    return {"after_first": r1[0]["status"] if r1 else None, "calls_before_due": before,
            "final": e.deliv(n["id"]), "calls": len(e.net.calls)}


def s_transient_exhausted(e: NEnv) -> Dict[str, Any]:
    e.net.default = TimeoutError
    n, _ = e.emit(_ev(6))
    for _ in range(12):
        e.disp().dispatch_once()
        e.advance(1000)
    return {"final": e.deliv(n["id"]), "calls": len(e.net.calls)}


def s_insecure_webhook_refused(e: NEnv) -> Dict[str, Any]:
    os.environ["SOVEREIGN_NOTIFY_WEBHOOK_URL"] = "http://hooks.example.test/plain"
    n, _ = e.emit(_ev(7))
    e.disp().dispatch_once()
    return {"configured": nch.WebhookChannel().configured()[0], "delivery": e.deliv(n["id"]),
            "calls": len(e.net.calls), "inbox": len(e.store.list())}


def s_severity_filter(e: NEnv) -> Dict[str, Any]:
    v = {"status": "needs_clarification", "loop_id": "L-sev", "reply": "أي مستودع؟"}
    n1, _ = e.emit(nev.from_loop(v))
    os.environ["SOVEREIGN_NOTIFY_WEBHOOK_MIN_SEVERITY"] = "medium"
    n2, _ = e.emit(nev.from_loop(dict(v, reply="أي فرع؟")))
    e.disp().dispatch_once()
    return {"default": e.deliv(n1["id"]), "lowered": e.deliv(n2["id"]),
            "calls": len(e.net.calls)}


def s_rate_limit(e: NEnv) -> Dict[str, Any]:
    ids = [e.emit(_ev(100 + i))[0]["id"] for i in range(5)]
    e.disp(per_hour=3).dispatch_once()
    st = [e.deliv(i) for i in ids]
    return {"sent": st.count("sent"), "suppressed": st.count("suppressed"),
            "inbox": len(e.store.list()), "calls": len(e.net.calls)}


def s_crash_after_send(e: NEnv) -> Dict[str, Any]:
    n, _ = e.emit(_ev(10))
    e.net.crash_next = True
    try:
        e.disp().dispatch_once()
    except qr.Crash:  # TOLERATED: محاكاة موت العملية — الأثر يُقاس بعد «إعادة التشغيل»
        pass
    e.store = e.new_store()                       # عملية جديدة على القرص نفسه
    e.disp().dispatch_once()
    before = len(e.net.calls) - 1
    e.advance(LEASE_S + 1)
    e.disp().dispatch_once()
    keys = [c["headers"].get("Idempotency-Key") for c in e.net.calls]
    return {"before_lease": before, "calls": len(e.net.calls),
            "same_idempotency_key": len(set(keys)) == 1 and keys[0] == n["id"],
            "final": e.deliv(n["id"])}


def s_broken_observer(e: NEnv) -> Dict[str, Any]:
    q = qr.Env(e.tmp / "q")

    def boom(view):
        raise RuntimeError("مراقب معطوب")
    q.o.observers.append(boom)
    try:
        out = q.o.submit(_req("n11", "N11"))
        return {"raised": False, "loop": out["status"]}
    except Exception as exc:
        return {"raised": True, "error": type(exc).__name__}


def s_job_dead(e: NEnv) -> Dict[str, Any]:
    q = qr.Env(e.tmp / "q")
    j, _ = q.enqueue("evaluation.run", {"suites": ["planner.holdout"]}, "n12")
    q.store.claim("dead-worker")                       # عامل مات بعد الحجز
    q.advance(qr.qkinds.KINDS["evaluation.run"].timeout_s({}) + 1)
    w = q.worker()
    w.on_finish = [nsvc.job_observer(e.store)]
    w.run_once()
    return {"job": q.store.get(j["id"])["status"], "events": e.events()}


def s_no_double_on_loop_failure(e: NEnv) -> Dict[str, Any]:
    q = qr.Env(e.tmp / "q")
    q.t.status_code = 401
    q.o.observers.append(nsvc.loop_observer(e.store))
    j, _ = q.enqueue("orchestrator.loop", qr.READ, "n13")
    w = q.worker()
    w.on_finish = [nsvc.job_observer(e.store)]
    w.drain(3)
    return {"job": q.store.get(j["id"])["status"], "events": e.events()}


def s_secret_scrubbed(e: NEnv) -> Dict[str, Any]:
    secret = "ghp_" + "S" * 30
    job = {"id": "J-secret", "status": "dead", "kind": f"k-{secret}", "attempts": 3,
           "error": f"فشل بالرمز {secret}"}
    n, _ = e.emit(nev.from_job(job))
    e.disp().dispatch_once()
    full = e.store.get(n["id"])
    return {"secret_in_inbox": secret in json.dumps(full, ensure_ascii=False),
            "secret_sent": any(secret in c["raw"].decode() for c in e.net.calls),
            "webhook_calls": len(e.net.calls)}


def s_survives_restart(e: NEnv) -> Dict[str, Any]:
    n, _ = e.emit(_ev(15))
    pending = sum(1 for d in e.store.deliveries_for(n["id"]) if d["status"] == "pending")
    e.store = e.new_store()
    e.disp().dispatch_once()
    return {"pending_before": pending, "final": e.deliv(n["id"]), "calls": len(e.net.calls)}


SCENARIOS = {f.__name__[2:]: f for f in (
    s_approval_requested, s_dedupe, s_review_required_telegram, s_auth_disables_channel,
    s_transient_then_sent, s_transient_exhausted, s_insecure_webhook_refused,
    s_severity_filter, s_rate_limit, s_crash_after_send, s_broken_observer, s_job_dead,
    s_no_double_on_loop_failure, s_secret_scrubbed, s_survives_restart)}

# حالات تحتاج Telegram مضبوطًا (وWebhook غير مضبوط لعزل العد)
_TELEGRAM = {"review_required_telegram": {
    "SOVEREIGN_NOTIFY_WEBHOOK_URL": None, "SOVEREIGN_NOTIFY_WEBHOOK_SECRET": None,
    "SOVEREIGN_TELEGRAM_BOT_TOKEN": TG_TOKEN, "SOVEREIGN_TELEGRAM_CHAT_ID": "4242"}}


def run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="r845-n-"))
    saved_transport = nch.TRANSPORT
    try:
        with _env(**_TELEGRAM.get(case["scenario"], {})):
            e = NEnv(tmp)
            nch.TRANSPORT = e.net
            try:
                got = SCENARIOS[case["scenario"]](e)
            except Exception as exc:  # انهيار السيناريو فشل مُعلن لا صامت
                got = {"error": f"{type(exc).__name__}: {exc}"}
        exp = case["expect"]
        failed = [{"check": k, "want": v, "got": got.get(k)}
                  for k, v in exp.items() if got.get(k) != v]
        return {"id": case["id"], "rule": case["rule"], "pass": not failed,
                "got": got, "failed_checks": failed}
    finally:
        nch.TRANSPORT = saved_transport
        shutil.rmtree(tmp, ignore_errors=True)


def run(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = [run_case(c) for c in cases]
    passed = sum(r["pass"] for r in results)
    return {"score": round(passed / len(results), 4) if results else 0.0,
            "passed": passed, "n": len(results),
            "failures": [r for r in results if not r["pass"]]}
