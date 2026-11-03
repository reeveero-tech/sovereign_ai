# -*- coding: utf-8 -*-
"""R-841 (4.2): سجل الأدوات — عقد واحد لكل أداة قابلة للاستدعاء.

القاعدة: لا أداة بلا وصف دلالي ولا مستوى خطورة ولا مخطط مدخلات صارم.
الأداة غلاف رفيع فوق عملية محددة في موصل R-840 — الصلاحيات والـretry
وقاطع الدائرة والـIdempotency كلها موروثة من المنفذ، لا معاد بناؤها.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import schemas

RISK_LEVELS = ("low", "medium", "high")
ACCESS_LEVELS = ("read", "write", "admin")


class ToolRegistryError(Exception):
    """رفض تسجيل/استدعاء أداة — بسبب موثق، لا صمت."""


@dataclass(frozen=True)
class ToolDefinition:
    """عقد الأداة: كل ما يحتاجه المخطط لاختيارها وحكمتها قبل تنفيذها."""
    tool_id: str                      # github.repo_read
    name: str
    description: str                  # دلالي — يُستخدم في الاختيار
    connector_id: str                 # من R-840
    operation: str                    # العملية المحددة داخل الموصل
    access: str                       # read|write|admin
    risk: str                         # low|medium|high — يحدد الحاجة لموافقة
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    scopes: List[str]                # نطاقات R-840 المطلوبة
    idempotent: bool
    estimated_cost: float             # وحدة تكلفة تقديرية لكل استدعاء
    estimated_time_s: float
    examples: List[Dict[str, Any]] = field(default_factory=list)
    lifecycle: str = "active"        # active|preview|deprecated
    inverse_tool_id: Optional[str] = None  # للتراجع (4.15)
    compensation_hint: str = ""       # تعويض إذا لا عكس متاح

    def public(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id, "name": self.name,
            "description": self.description,
            "connector_id": self.connector_id, "operation": self.operation,
            "access": self.access, "risk": self.risk,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "scopes": list(self.scopes), "idempotent": self.idempotent,
            "estimated_cost": self.estimated_cost,
            "estimated_time_s": self.estimated_time_s,
            "examples": list(self.examples), "lifecycle": self.lifecycle,
            "inverse_tool_id": self.inverse_tool_id,
            "compensation_hint": self.compensation_hint,
        }


class ToolRegistry:
    """مركز واحد — التسجيل يتحقق من العقد كاملًا قبل القبول."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._lock = threading.RLock()

    def register(self, d: ToolDefinition) -> ToolDefinition:
        # القاعدة: لا أداة بلا مخطط/وصف/خطورة — يُرفض التسجيل صراحة
        if not d.tool_id or "." not in d.tool_id:
            raise ToolRegistryError(f"معرّف أداة غير صالح: {d.tool_id!r}")
        if not d.description or len(d.description.strip()) < 10:
            raise ToolRegistryError(
                f"{d.tool_id}: لا تسجيل بلا وصف دلالي (10 أحرف على الأقل)")
        if d.risk not in RISK_LEVELS:
            raise ToolRegistryError(f"{d.tool_id}: مستوى خطورة غير معروف: {d.risk}")
        if d.access not in ACCESS_LEVELS:
            raise ToolRegistryError(f"{d.tool_id}: مستوى وصول غير معروف: {d.access}")
        if not d.input_schema or not d.output_schema:
            raise ToolRegistryError(f"{d.tool_id}: لا تسجيل أداة بلا مخططات")
        if d.lifecycle not in ("active", "preview", "deprecated"):
            raise ToolRegistryError(f"{d.tool_id}: حالة دورة حياة غير معروفة")
        with self._lock:
            self._tools[d.tool_id] = d
        return d

    def get(self, tool_id: str) -> ToolDefinition:
        with self._lock:
            d = self._tools.get(tool_id)
        if d is None:
            raise ToolRegistryError(f"أداة غير مسجلة: {tool_id}")
        if d.lifecycle == "deprecated":
            raise ToolRegistryError(f"أداة مهجورة: {tool_id}")
        return d

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [d.public() for d in self._tools.values()]

    def by_capability(self, access: str) -> List[ToolDefinition]:
        with self._lock:
            return [d for d in self._tools.values() if d.access == access]


# ---------------------------------------------------------------- الأدوات المبدئية
# خمس أدوات عبر موصلات R-840 الموجودة — عقد كل واحدة كامل فوق عقد الموصل.

def seed_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolDefinition(
        tool_id="github.repo_read", name="قراءة مستودع GitHub",
        description="قراءة بيانات مستودع GitHub (مالك/اسم المستودع): الافتراضية،"
                    " الخصوصية، الفرع الافتراضي — للتحليل والاستكشاف",
        connector_id="github", operation="repo_read", access="read", risk="low",
        input_schema={"type": "object", "required": ["owner", "repo"],
                      "additionalProperties": False,
                      "properties": {"owner": {"type": "string", "minLength": 1},
                                     "repo": {"type": "string", "minLength": 1}}},
        output_schema={"type": "object", "required": ["ok"],
                       "properties": {"ok": {"type": "boolean"},
                                      "repo": {"type": "string"}}},
        scopes=["repo:read"], idempotent=True,
        estimated_cost=0.001, estimated_time_s=1.5,
        examples=[{"utterance": "حلل مستودع reeveero-tech/sovereign_ai",
                   "inputs": {"owner": "reeveero-tech",
                              "repo": "sovereign_ai"}}],
    ))
    reg.register(ToolDefinition(
        tool_id="github.issue_create", name="فتح مشكلة GitHub",
        description="فتح issue جديد في مستودع GitHub — كتابة حساسة تتطلب موافقة"
                    " صريحة قبل التنفيذ، مع عكس جزئي (إغلاق المشكلة) للتراجع",
        connector_id="github", operation="issue_create", access="write",
        risk="high",
        input_schema={"type": "object", "required": ["owner", "repo", "title"],
                      "additionalProperties": False,
                      "properties": {"owner": {"type": "string", "minLength": 1},
                                     "repo": {"type": "string", "minLength": 1},
                                     "title": {"type": "string", "minLength": 1},
                                     "body": {"type": "string"}}},
        output_schema={"type": "object", "required": ["ok"],
                       "properties": {"ok": {"type": "boolean"},
                                      "issue_number": {"type": "integer"}}},
        scopes=["repo:write"], idempotent=True,
        estimated_cost=0.01, estimated_time_s=2.0,
        examples=[{"utterance": "افتح مشكلة في مستودع X بعنوان Y",
                   "inputs": {"owner": "x", "repo": "r", "title": "Y"}}],
        compensation_hint="أغلق المشكلة المفتوحة يدويًا عبر GitHub (لا عكس آلي"
                          " متاح في الموصل الحالي) وسجّل رقمها",
    ))
    reg.register(ToolDefinition(
        tool_id="supabase.table_select", name="قراءة جدول Supabase",
        description="قراءة أول ٥ صفوف من جدول في قاعدة بيانات Supabase عبر"
                    " REST — للإجابة عن أسئلة البيانات",
        connector_id="supabase", operation="table_select", access="read",
        risk="low",
        input_schema={"type": "object", "required": ["table"],
                      "additionalProperties": False,
                      "properties": {"table": {"type": "string", "minLength": 1},
                                     "base_url": {"type": "string"}}},
        output_schema={"type": "object", "required": ["ok", "rows"],
                      "properties": {"ok": {"type": "boolean"},
                                     "rows": {"type": "array"}}},
        scopes=["db:read"], idempotent=True,
        estimated_cost=0.001, estimated_time_s=1.0,
        examples=[{"utterance": "اعرض لي صفوف جدول users",
                   "inputs": {"table": "users"}}],
    ))
    reg.register(ToolDefinition(
        tool_id="render.services_list", name="قائمة خدمات Render",
        description="سرد خدمات Render المنشورة وحالتها — لفحص البنية"
                    " التشغيلية قبل النشر أو أثناءه",
        connector_id="render", operation="services_list", access="read",
        risk="low",
        input_schema={"type": "object", "required": [], "additionalProperties": False,
                      "properties": {}},
        output_schema={"type": "object", "required": ["ok", "services"],
                       "properties": {"ok": {"type": "boolean"},
                                      "services": {"type": "array"}}},
        scopes=["connector:read"], idempotent=True,
        estimated_cost=0.001, estimated_time_s=1.0,
        examples=[{"utterance": "ما الخدمات المنشورة عندنا على Render؟",
                   "inputs": {}}],
    ))
    reg.register(ToolDefinition(
        tool_id="openapi.register_spec", name="تسجيل مواصفة OpenAPI",
        description="تسجيل مواصفة OpenAPI لموصل عام جديد — يستنتج عمليات"
                    " الموصل ويطبق المصادقة الموحدة (معاينة، كتابة إدارية)",
        connector_id="generic_openapi", operation="register_spec",
        access="admin", risk="medium",
        input_schema={"type": "object", "required": ["connector_id"],
                      "additionalProperties": False,
                      "properties": {"connector_id": {"type": "string",
                                                     "minLength": 1},
                                     "spec": {"type": "object"}}},
        output_schema={"type": "object", "required": ["ok"],
                       "properties": {"ok": {"type": "boolean"}}},
        scopes=["connector:write"], idempotent=False,
        estimated_cost=0.0, estimated_time_s=0.5,
        examples=[{"utterance": "سجّل API المزامنة من مواصفته",
                   "inputs": {"connector_id": "sync_api", "spec": {}}}],
    ))
    return reg


_REGISTRY: Optional[ToolRegistry] = None


def default_registry() -> ToolRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = seed_registry()
    return _REGISTRY


def new_decision(step_id: str, decision_type: str, chosen: str,
                 rejected: List[str], reasoning: str, confidence: float,
                 trace_ref: str) -> Dict[str, Any]:
    """قرار مسجل (5.4) — كل اختيار أداة أو انحراف يمر من هنا."""
    d = {
        "decision_id": str(uuid.uuid4()),
        "step_id": step_id,
        "decision_type": decision_type,
        "chosen": chosen,
        "rejected": list(rejected),
        "reasoning": reasoning,
        "confidence": confidence,
        "trace_ref": trace_ref,
    }
    schemas.validate(d, schemas.DECISION_SCHEMA)
    return d
