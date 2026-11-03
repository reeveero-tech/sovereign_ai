# -*- coding: utf-8 -*-
"""R-841: العقود الإلزامية (5.1–5.5) — مخططات صارمة قابلة للتحقق الآلي.

لا ميزة في الطبقة بلا عقد مخطط. المدقق هنا صغير ومكتفي ذاتيًا (stdlib خالص)
لأن إضافة مكتبة تحقق جديدة تحتاج تبريرًا وأثرًا مقيسًا — والقاعدة المطلوبة
(نوع/إلزامي/تعداد/نمط/حدود) مغطاة كاملة.

العقود: Request (5.1)، Plan/Step (5.2)، StepResult (5.3)، DecisionLog (5.4)،
Approval (5.5) — وكلها تُصدَّر كمخططات JSON عبر /orchestrator/schemas.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------- المدقق

_TYPE_MAP = {
    "object": dict, "array": list, "string": str, "integer": int,
    "number": (int, float), "boolean": bool, "null": type(None),
}


def _matches_type(instance: Any, t: str) -> bool:
    py = _TYPE_MAP.get(t)
    if py is None:
        raise SchemaError(f"نوع غير مدعوم في المخطط: {t}")
    if isinstance(instance, bool) and t in ("integer", "number"):
        return False  # منطقي ليس رقمًا في العقد الصارم
    return isinstance(instance, py)


class SchemaError(Exception):
    """خطأ تحقق عقد — يُرفع قبل أي تنفيذ، لا بعده."""


def validate(instance: Any, schema: Dict[str, Any], path: str = "$") -> None:
    """تحقق JSON Schema جزئي صارم: type/required/properties/items/enum/نمط/حدود.

    يدعم additionalProperties=false و pattern و minItems/maxItems و
    minimum/maximum وقائمة أنواع (object|null) — كل ما تستخدمه عقود
    الطبقة. ما لا يُدعم يُرفع عند بناء المخطط نفسه (صريح لا صامت).
    """
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if isinstance(instance, bool) and "boolean" not in types:
            raise SchemaError(f"{path}: منطقي ليس من الأنواع المسموحة")
        if not any(_matches_type(instance, x) for x in types):
            raise SchemaError(
                f"{path}: متوقع {t} لكن وُجد {type(instance).__name__}")
        if isinstance(instance, bool) and len(types) == 1 and types[0] \
                in ("integer", "number"):
            raise SchemaError(f"{path}: منطقي ليس رقمًا")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaError(f"{path}: {instance!r} خارج التعداد {schema['enum']}")
    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            raise SchemaError(f"{path}: لا يطابق النمط {schema['pattern']}")
        if len(instance) < schema.get("minLength", 0):
            raise SchemaError(f"{path}: أقصر من الحد الأدنى")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaError(f"{path}: أقل من الحد الأدنى")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaError(f"{path}: أعلى من الحد الأقصى")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in instance:
                raise SchemaError(f"{path}: حقل إلزامي مفقود: {req}")
        if schema.get("additionalProperties") is False:
            extra = set(instance) - set(props)
            if extra:
                raise SchemaError(f"{path}: حقول غير مسموحة: {sorted(extra)}")
        for k, sub in props.items():
            if k in instance:
                validate(instance[k], sub, f"{path}.{k}")
    if isinstance(instance, list):
        items = schema.get("items")
        if items is not None:
            if len(instance) < schema.get("minItems", 0):
                raise SchemaError(f"{path}: عناصر أقل من الحد الأدنى")
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                raise SchemaError(f"{path}: عناصر أكثر من الحد الأقصى")
            for i, v in enumerate(instance):
                validate(v, items, f"{path}[{i}]")


# --------------------------------------------------------------------- 5.1 الطلب

REQUEST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["request_id", "user_id", "session_id", "utterance",
                "context_snapshot_id", "permissions", "constraints"],
    "additionalProperties": False,
    "properties": {
        "request_id": {"type": "string", "pattern": "^[0-9a-f-]{36}$"},
        "user_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string", "minLength": 1},
        "utterance": {"type": "string", "minLength": 1},
        "context_snapshot_id": {"type": "string"},
        "permissions": {"type": "array", "items": {"type": "string"}},
        "constraints": {
            "type": "object",
            "required": ["max_cost", "max_time_s", "max_steps"],
            "additionalProperties": False,
            "properties": {
                "max_cost": {"type": "number", "minimum": 0},
                "max_time_s": {"type": "number", "minimum": 0},
                "max_steps": {"type": "integer", "minimum": 1},
            },
        },
        "dry_run": {"type": "boolean"},
    },
}

DEFAULT_CONSTRAINTS = {"max_cost": 1.0, "max_time_s": 120.0, "max_steps": 12}


def new_request(user_id: str, session_id: str, utterance: str,
                permissions: Optional[List[str]] = None,
                constraints: Optional[Dict[str, Any]] = None,
                context_snapshot_id: str = "",
                dry_run: bool = False) -> Dict[str, Any]:
    """بناء طلب صالح المخطط — المعرّفات والحدود افتراضية قابلة للتخصيص."""
    req = {
        "request_id": str(uuid.uuid4()),
        "user_id": user_id,
        "session_id": session_id,
        "utterance": utterance,
        "context_snapshot_id": context_snapshot_id,
        "permissions": list(permissions or []),
        "constraints": dict(constraints or DEFAULT_CONSTRAINTS),
        "dry_run": dry_run,
    }
    validate(req, REQUEST_SCHEMA)
    return req


# --------------------------------------------------------------------- 5.2 الخطة

STEP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["step_id", "goal", "tool_id", "inputs", "depends_on",
                 "requires_approval", "success_criteria", "fallback"],
    "additionalProperties": False,
    "properties": {
        "step_id": {"type": "string", "minLength": 1},
        "goal": {"type": "string", "minLength": 1},
        "tool_id": {"type": "string", "minLength": 1},
        "inputs": {"type": "object"},
        "depends_on": {"type": "array", "items": {"type": "string"}},
        "requires_approval": {"type": "boolean"},
        "success_criteria": {"type": "string", "minLength": 1},
        "fallback": {"type": "string"},
    },
}

PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["plan_id", "goal", "steps", "approval_points", "max_steps",
                 "estimated_cost", "estimated_time_s", "mode", "planning_reason"],
    "additionalProperties": False,
    "properties": {
        "plan_id": {"type": "string", "pattern": "^[0-9a-f-]{36}$"},
        "goal": {"type": "string", "minLength": 1},
        "steps": {"type": "array", "items": STEP_SCHEMA, "minItems": 1},
        "approval_points": {"type": "array", "items": {"type": "string"}},
        "max_steps": {"type": "integer", "minimum": 1},
        "estimated_cost": {"type": "number", "minimum": 0},
        "estimated_time_s": {"type": "number", "minimum": 0},
        "mode": {"type": "string", "enum": ["plan_execute", "react"]},
        "planning_reason": {"type": "string", "minLength": 1},
    },
}


# ----------------------------------------------------------------- 5.3 نتيجة خطوة

STEP_RESULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["step_id", "status", "output", "error", "cost", "duration_ms",
                 "trace_ref"],
    "additionalProperties": False,
    "properties": {
        "step_id": {"type": "string", "minLength": 1},
        "status": {"type": "string",
                   "enum": ["success", "failure", "cancelled", "timeout",
                            "denied", "pending_approval", "skipped"]},
        "output": {"type": "object"},
        "error": {
            "type": ["object", "null"],
            "required": ["code", "message"],
            "additionalProperties": False,
            "properties": {
                "code": {"type": "string"},
                "message": {"type": "string"},
                "action": {"type": "string"},
            },
        },
        "cost": {"type": "number", "minimum": 0},
        "duration_ms": {"type": "integer", "minimum": 0},
        "trace_ref": {"type": "string"},
    },
}


# ----------------------------------------------------------------- 5.4 القرار

DECISION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["decision_id", "step_id", "decision_type", "chosen",
                 "rejected", "reasoning", "confidence", "trace_ref"],
    "additionalProperties": False,
    "properties": {
        "decision_id": {"type": "string", "pattern": "^[0-9a-f-]{36}$"},
        "step_id": {"type": "string"},
        "decision_type": {"type": "string",
                          "enum": ["tool_choice", "approval", "replan",
                                   "cancel", "escalate", "reflection",
                                   "clarify", "stop"]},
        "chosen": {"type": "string"},
        "rejected": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string", "minLength": 1},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "trace_ref": {"type": "string"},
    },
}


# ----------------------------------------------------------------- 5.5 الموافقة

APPROVAL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["approval_id", "step_id", "action_summary", "impact_summary",
                 "requested_by", "approved_by", "status", "timestamp"],
    "additionalProperties": False,
    "properties": {
        "approval_id": {"type": "string", "pattern": "^[0-9a-f-]{36}$"},
        "step_id": {"type": "string", "minLength": 1},
        "action_summary": {"type": "string", "minLength": 1},
        "impact_summary": {"type": "string"},
        "requested_by": {"type": "string", "minLength": 1},
        "approved_by": {"type": ["string", "null"]},
        "status": {"type": "string",
                   "enum": ["pending", "approved", "rejected", "modified"]},
        "timestamp": {"type": "string",
                      "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T"},
        "scope": {"type": "string", "enum": ["once", "session"]},
    },
}


def new_approval(step_id: str, action_summary: str, impact_summary: str,
                 requested_by: str) -> Dict[str, Any]:
    """طلب موافقة جديد بحالة pending — يُعرض على المستخدم بلغته."""
    import datetime as _dt
    ap = {
        "approval_id": str(uuid.uuid4()),
        "step_id": step_id,
        "action_summary": action_summary,
        "impact_summary": impact_summary,
        "requested_by": requested_by,
        "approved_by": None,
        "status": "pending",
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "scope": "once",
    }
    validate(ap, APPROVAL_SCHEMA)
    return ap


SCHEMAS: Dict[str, Dict[str, Any]] = {
    "request": REQUEST_SCHEMA, "plan": PLAN_SCHEMA,
    "step_result": STEP_RESULT_SCHEMA, "decision": DECISION_SCHEMA,
    "approval": APPROVAL_SCHEMA,
}
