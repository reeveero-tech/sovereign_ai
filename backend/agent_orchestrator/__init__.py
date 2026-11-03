# -*- coding: utf-8 -*-
"""R-841: طبقة تنسيق الوكلاء — الجهاز العصبي فوق طبقتي الفهم والموصلات.

تحوّل الفهم إلى قرار، والقرار إلى إجراء، والإجراء إلى أثر قابل للتدقيق
والتراجع. المبدأ الحاكم: التخطيط يسبق التنفيذ، وأقل صلاحية وأقل أداة،
وبوابات صلاحية وموافقة وتكلفة قبل المنفذ — لا استدعاء بلا خطة أو أثر.

المكونات: runtime (4.1)، tool_registry (4.2)، planner (4.3)،
execution_engine (4.4)، policy_gate (4.5)، approval_gate (4.6)،
reflection (4.7)، memory (4.8)، context_manager (4.9)، failure (4.10)،
governor (4.11)، tracing (4.12)، hitl (4.13)، state (4.14)،
rollback (4.15)، والمعاينة الجافة داخل runtime (4.16).
"""
from __future__ import annotations

from . import (approval_gate, context_manager, execution_engine, failure,
               governor, hitl, memory, planner, policy_gate, reflection,
               rollback, runtime, schemas, state, tool_registry, tracing)
from .runtime import OrchestratorSystem

__all__ = [
    "OrchestratorSystem", "approval_gate", "context_manager",
    "execution_engine", "failure", "governor", "hitl", "memory", "planner",
    "policy_gate", "reflection", "rollback", "runtime", "schemas", "state",
    "tool_registry", "tracing",
]
