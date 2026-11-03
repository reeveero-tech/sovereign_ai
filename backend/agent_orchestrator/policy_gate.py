# -*- coding: utf-8 -*-
"""R-841 (4.5): بوابة الصلاحيات — كل استدعاء يُفحص قبل التنفيذ لا بعده.

الرفض يعيد سببًا واضحًا برمز 403 (نمط الحوكمة، لا 500) — لا تمرير صامت.
القرار يُسجَّل دائمًا (من فحص، من رفض، من اشتراط موافقة).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .tool_registry import ToolDefinition, ToolRegistry


@dataclass
class PolicyDecision:
    allowed: bool
    requires_approval: bool = False
    reason: str = ""
    code: str = "ok"          # ok|forbidden|disabled|org_policy

    @property
    def http_status(self) -> int:
        # 403 للرفض الحوكمي — لا 500 أبدًا (نمط R-840c)
        return 200 if self.allowed else 403


class PolicyGate:
    """تحقق ثلاثي: صلاحية الفاعل ← حالة الأداة ← سياسة المؤسسة (R-840)."""

    def __init__(self, tools: ToolRegistry,
                 org_policy=None, connector_registry=None):
        self.tools = tools
        self.org_policy = org_policy            # policy.OrgPolicy من R-840 (اختياري)
        self.connector_registry = connector_registry  # سجل موصلات R-840

    def check(self, tool: ToolDefinition, actor_permissions: List[str],
              actor: str = "user") -> PolicyDecision:
        # ١) صلاحية الفاعل: أداة الكتابة تتطلب صلاحية الكتابة صراحة
        if tool.access in ("write", "admin"):
            needed = f"orchestrator:{tool.access}"
            if needed not in actor_permissions:
                return PolicyDecision(
                    False, reason=f"صلاحية غير كافية: {needed} مطلوبة لهذه"
                                 f" العملية ({tool.tool_id}) — اطلب التوسيع"
                                 f" أو أداة بديلة قرائية",
                    code="forbidden")
        # ٢) حالة الأداة في السجل
        if tool.lifecycle != "active":
            return PolicyDecision(
                False, reason=f"الأداة {tool.tool_id} ليست نشطة"
                             f" ({tool.lifecycle})",
                code="disabled")
        # ٣) سياسة المؤسسة من R-840 — لا التفاف عليها
        if self.org_policy is not None and self.connector_registry is not None:
            try:
                self.org_policy.check_execution(
                    tool.connector_id, tool.operation, actor)
            except Exception as exc:  # سياسة تمنع = 403 موثق، لا 500
                return PolicyDecision(
                    False, reason=f"سياسة المؤسسة تمنع العملية: {exc}",
                    code="org_policy")
        # ٤) مستوى الخطورة يحدد الحاجة لموافقة بشرية
        requires_approval = tool.access in ("write", "admin") \
            or tool.risk == "high"
        return PolicyDecision(
            True, requires_approval=requires_approval,
            reason="مسموح" + (" — يتطلب موافقة" if requires_approval else ""))

    def decision_record(self, tool: ToolDefinition, pd: PolicyDecision,
                        trace_ref: str) -> Dict[str, Any]:
        from .tool_registry import new_decision
        return new_decision(
            step_id="", decision_type="tool_choice",
            chosen=tool.tool_id if pd.allowed else f"رفض:{tool.tool_id}",
            rejected=[], reasoning=pd.reason, confidence=1.0,
            trace_ref=trace_ref)
