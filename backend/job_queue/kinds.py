# -*- coding: utf-8 -*-
"""R-844 (D-059): أنواع المهام — لكل نوع وصف دلالي وخطورة ومخطط وحدود.

ممنوع صريح: «لا أداة بلا وصف دلالي/مخاطرة/مخطط». المهمة أداة غير متزامنة،
فلا تُقبل إلا بنوع مسجل هنا وحمولة تطابق مخططه. والأنواع لا تتجاوز البوابات:
``orchestrator.loop`` يمر بكل بوابات المنسق (الصلاحية، والموافقة على
الكتابة، والميزانية، والأثر). الطابور يغير **متى** يعمل الشيء، ولا يغير
**هل يُسمح** به.

سياسة المحاولات: تُعاد المهمة فقط عند الأعطال العابرة المعلنة
(``retryable``)، أي المهلة وانقطاع الاتصال. أي استثناء آخر يعطي ``failed``
بلا إعادة عمياء. وحلقة المنسق التي تنتهي بفشل حوكمي (401 أو 403 أو رفض أو
ميزانية) لا تُعاد أبدًا، لأن المنسق نفسه حسمها.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

try:
    from agent_orchestrator import schemas as orch_schemas
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.agent_orchestrator import schemas as orch_schemas


class StaleJob(Exception):
    """العامل لم يعد مالك المهمة (سياج تغير) — يتوقف بلا أثر."""


@dataclass
class Outcome:
    status: str                      # succeeded | needs_human | failed | cancelled
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class JobContext:
    job: Dict[str, Any]
    bind_loop: Callable[[str], bool]
    cancel_requested: Callable[[], bool]
    orchestrator: Optional[Callable[[], Any]] = None  # None ⇒ منسق الخادم المشترك

    def orch(self):
        return (self.orchestrator or _orchestrator)()


@dataclass(frozen=True)
class JobKind:
    name: str
    description: str
    risk: str                        # low | medium | high
    risk_reason: str
    payload_schema: Dict[str, Any]
    timeout_s: Callable[[Dict[str, Any]], float]
    max_attempts: int
    retryable: Tuple[type, ...]
    handler: Callable[[JobContext], Outcome]

    def validate(self, payload: Dict[str, Any]) -> None:
        orch_schemas.validate(payload, self.payload_schema)

    def public(self) -> Dict[str, Any]:
        return {"kind": self.name, "description": self.description,
                "risk": self.risk, "risk_reason": self.risk_reason,
                "payload_schema": self.payload_schema,
                "max_attempts": self.max_attempts,
                "retryable": [t.__name__ for t in self.retryable]}


# ===================================================================== المنسق
def _orchestrator():
    try:
        from agent_orchestrator.api_routes import get_orchestrator
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.agent_orchestrator.api_routes import get_orchestrator
    return get_orchestrator()


#: حالة الحلقة ⇒ حالة المهمة. ما ينتظر إنسانًا ليس نجاحًا ولا فشلًا.
LOOP_TO_JOB = {"completed": "succeeded", "pending_approval": "needs_human",
               "needs_clarification": "needs_human", "paused": "needs_human",
               "needs_owner_review": "needs_human", "failed": "failed",
               "cancelled": "cancelled"}


def _loop_outcome(out: Dict[str, Any]) -> Outcome:
    if not out.get("ok", False):
        return Outcome("failed", error=str(out.get("error") or "فشل المنسق")[:300])
    st = out.get("status")
    job_status = LOOP_TO_JOB.get(st)
    if job_status is None:  # running لا يُتوقع بعد عودة run — لا نجاح مُدّعى
        return Outcome("failed", {"loop_id": out.get("loop_id"), "loop_status": st},
                       f"حالة حلقة غير منتهية بعد التشغيل: {st}")
    res = {"loop_id": out.get("loop_id"), "loop_status": st,
           "reply": (out.get("reply") or "")[:1000],
           "pending_approval": out.get("pending_approval")}
    return Outcome(job_status, res,
                   None if job_status != "failed" else (out.get("reply") or "")[:300])


_LOOP_SCHEMA = {
    "type": "object", "required": ["utterance"], "additionalProperties": False,
    "properties": {
        "user_id": {"type": "string", "minLength": 1, "maxLength": 120},
        "session_id": {"type": "string", "minLength": 1, "maxLength": 120},
        "utterance": {"type": "string", "minLength": 1, "maxLength": 4000},
        "permissions": {"type": "array", "items": {"type": "string"}},
        "constraints": {
            "type": "object", "required": ["max_cost", "max_time_s", "max_steps"],
            "additionalProperties": False,
            "properties": {"max_cost": {"type": "number", "minimum": 0, "maximum": 100},
                           "max_time_s": {"type": "number", "minimum": 1, "maximum": 600},
                           "max_steps": {"type": "integer", "minimum": 1, "maximum": 50}}},
        "dry_run": {"type": "boolean"},
    },
}


def _run_loop(ctx: JobContext) -> Outcome:
    o = ctx.orch()
    p = ctx.job["payload"]
    if ctx.cancel_requested():
        return Outcome("cancelled", error="أُلغيت قبل البدء")
    loop_id = ctx.job.get("loop_id")
    if loop_id and o.state.load(loop_id) is not None:
        # استعادة بعد انقطاع: الحلقة نفسها من نقطة تفتيشها، والكتابة المعلقة
        # تُحسم بـneeds_owner_review في المنسق، فلا تُعاد عمياء.
        return _loop_outcome(o.run(loop_id))
    if not loop_id:
        loop_id = str(uuid.uuid4())
        if not ctx.bind_loop(loop_id):
            raise StaleJob("فقد العامل ملكية المهمة قبل البدء")
    request = orch_schemas.new_request(
        user_id=p.get("user_id", "user"), session_id=p.get("session_id", "s-queue"),
        utterance=p["utterance"], permissions=p.get("permissions", []),
        constraints=p.get("constraints"), dry_run=bool(p.get("dry_run", False)))
    return _loop_outcome(o.submit(request, loop_id=loop_id))


def _loop_timeout(p: Dict[str, Any]) -> float:
    c = p.get("constraints") or orch_schemas.DEFAULT_CONSTRAINTS
    return float(c["max_time_s"]) + 60.0


_APPROVAL_SCHEMA = {
    "type": "object", "required": ["loop_id", "approval_id", "decision"],
    "additionalProperties": False,
    "properties": {
        "loop_id": {"type": "string", "pattern": "^[0-9a-f-]{36}$"},
        "approval_id": {"type": "string", "pattern": "^[0-9a-f-]{36}$"},
        "decision": {"type": "string", "enum": ["approved", "rejected", "modified"]},
        "approved_by": {"type": "string", "minLength": 1, "maxLength": 120},
        "session_scope": {"type": "boolean"},
    },
}


def _decide(ctx: JobContext) -> Outcome:
    p = ctx.job["payload"]
    if ctx.cancel_requested():
        return Outcome("cancelled", error="أُلغيت قبل البدء")
    if not ctx.job.get("loop_id") and not ctx.bind_loop(p["loop_id"]):
        raise StaleJob("فقد العامل ملكية المهمة قبل البدء")
    o = ctx.orch()
    out = o.decide_approval(p["loop_id"], p["approval_id"], p["decision"],
                            p.get("approved_by", "owner"), bool(p.get("session_scope")))
    if out.get("ok") and out.get("status") == "running":
        # استعادة: الموافقة حُسمت قبل الانقطاع والحلقة توقفت جارية — استئنافها
        # (الكتابة المعلقة تُحسم needs_owner_review في المنسق، لا تُعاد عمياء)
        out = o.run(p["loop_id"])
    return _loop_outcome(out)


# ===================================================================== التقييم
_EVAL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"suites": {"type": "array", "items": {"type": "string"},
                              "maxItems": 20}},
}


def _run_eval(ctx: JobContext) -> Outcome:
    try:
        from evaluation import runner, suites
    except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
        from backend.evaluation import runner, suites
    ids = ctx.job["payload"].get("suites") or None
    for sid in ids or []:
        suites.get(sid)  # معرّف مجهول ⇒ KeyError صريح ⇒ failed
    rep = runner.run_suites(ids)
    runner.save_report(rep)
    res = {"report_id": rep["report_id"], "pass": rep["pass"],
           "suites": [{"suite_id": r["suite_id"], "score": r["score"], "pass": r["pass"]}
                      for r in rep["suites"]]}
    return Outcome("succeeded" if rep["pass"] else "failed", res,
                   None if rep["pass"] else "مجموعة تحت أرضيتها أو بصمتها تغيرت")


# ===================================================================== السجل
_TRANSIENT = (TimeoutError, ConnectionError)

KINDS: Dict[str, JobKind] = {k.name: k for k in (
    JobKind(
        name="orchestrator.loop",
        description="تشغيل طلب لغوي عبر حلقة المنسق في الخلفية (تخطيط ثم بوابات ثم"
                    " تنفيذ ثم انعكاس) بدل حجز الطلب HTTP حتى النهاية",
        risk="medium",
        risk_reason="قد تقود لكتابة خارجية — لكن كل كتابة تمر ببوابة الصلاحية"
                    " والموافقة الصريحة في المنسق؛ الطابور لا يتجاوزها",
        payload_schema=_LOOP_SCHEMA, timeout_s=_loop_timeout, max_attempts=3,
        retryable=_TRANSIENT, handler=_run_loop),
    JobKind(
        name="orchestrator.approval",
        description="حسم موافقة معلقة ثم استئناف الحلقة في الخلفية",
        risk="high",
        risk_reason="الموافقة نفسها تُطلق كتابة خارجية — تتطلب مفتاح المالك"
                    " والمفتاح الحتمي للخطوة يمنع تكرارها عند الاستئناف",
        payload_schema=_APPROVAL_SCHEMA, timeout_s=lambda p: 300.0, max_attempts=2,
        retryable=_TRANSIENT, handler=_decide),
    JobKind(
        name="evaluation.run",
        description="تشغيل مجموعات التقييم المجمّدة (R-843) وحفظ التقرير",
        risk="low", risk_reason="قراءة فقط في بيئة معزولة بشبكة مزيفة",
        payload_schema=_EVAL_SCHEMA, timeout_s=lambda p: 900.0, max_attempts=1,
        retryable=(), handler=_run_eval),
)}


def get(name: str) -> JobKind:
    k = KINDS.get(name)
    if k is None:
        raise KeyError(f"نوع مهمة غير مسجل: {name} — المسجل: {sorted(KINDS)}")
    return k
