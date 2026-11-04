# -*- coding: utf-8 -*-
"""R-841 (4.15): الإلغاء والتراجع — ما تم وما لم يتم موثقان دائمًا.

Rollback للعمليات القابلة للتراجع (أداة عكسية متوفرة)، وتعويض موثق
للعمليات التي لا تُرجَع. الإلغاء فوري ويجمد الحالة لا يمسحها.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import schemas
from .tool_registry import new_decision


class RollbackEngine:
    """تراجع خطوة منفذة — عكس إن وُجدت الأداة، وإلا خطة تعويض موثقة."""

    def __init__(self, tools, execution_engine):
        self.tools = tools
        self.engine = execution_engine

    def rollback(self, state: Dict[str, Any], step_id: str,
                 actor: str, budget, trace_ref: str, tracer=None
                 ) -> Dict[str, Any]:
        """تراجع عن خطوة — يُنفذ العكس أو يوثق التعويض، ولا يدّعي ما لا يفعله."""
        results: List[Dict[str, Any]] = state.get("results", [])
        target = next((r for r in results if r["step_id"] == step_id), None)
        if target is None or target["status"] != "success":
            return {"ok": False,
                    "reason": f"لا خطوة منجحة باسم {step_id} للتراجع عنها",
                    "action": "none"}
        plan = state["plan"]
        step = next((s for s in plan["steps"] if s["step_id"] == step_id), None)
        if step is None:
            return {"ok": False, "reason": "خطوة غير موجودة في الخطة",
                    "action": "none"}
        tool = self.tools.get(step["tool_id"])
        if tool.inverse_tool_id:
            inverse = self.tools.get(tool.inverse_tool_id)
            rb_step = {"step_id": f"rb-{step_id}", "goal":
                       f"عكس {step['goal']}",
                       "tool_id": inverse.tool_id,
                       "inputs": dict(step["inputs"]),
                       "depends_on": [], "requires_approval":
                       inverse.access in ("write", "admin"),
                       "success_criteria": "نجاح العكس",
                       "fallback": ""}
            r = self.engine.execute(rb_step, state["request"]["permissions"],
                                    budget, state["request"]["session_id"],
                                    actor, trace_ref, tracer,
                                    loop_id=state.get("loop_id", ""))
            return {"ok": r["status"] == "success",
                    "action": "rollback",
                    "result": r,
                    "decision": new_decision(
                        step_id, "cancel", f"عكس عبر {inverse.tool_id}", [],
                        "تراجع قابل للعكس — نُفذت الأداة المعاكسة", 1.0,
                        trace_ref)}
        # لا عكس متاح: تعويض موثق — خطة واضحة لا ادعاء تراجع
        comp = tool.compensation_hint or \
            f"لا أداة عكسية لـ{tool.tool_id} — التعويض يدوي موثق"
        record = {"ok": True, "action": "compensation",
                  "compensation_plan": comp, "rolled_back_step": step_id,
                  "executed_by": actor,
                  "decision": new_decision(
                      step_id, "cancel", "تعويض موثق", [],
                      "العملية غير قابلة للعكس آليًا — خطة تعويض موثقة"
                      " بدل ادعاء تراجع", 1.0, trace_ref)}
        state.setdefault("compensations", []).append(record)
        return record

    def cancel_document(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """توثيق ما تم وما لم يتم عند الإلغاء — لا صمت ولا فقدان."""
        results = state.get("results", [])
        plan = state.get("plan") or {"steps": []}
        done = {r["step_id"] for r in results
                if r["status"] == "success"}
        not_done = [s["step_id"] for s in plan.get("steps", [])
                    if s["step_id"] not in done]
        return {"executed": sorted(done), "not_executed": not_done,
                "results_count": len(results)}
