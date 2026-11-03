# -*- coding: utf-8 -*-
"""R-841 (4.9): مدير السياق — ميزانية رموز صريحة لكل خطوة.

الترتيب: تعليمات > حقائق > خطة > حالة > استرجاع. التضخم يُمنع بالتلخيص،
وكل ما أُدرج وما أُهمل يُسجَّل مع سببه — لا سياق مخفي.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _estimate_tokens(obj: Any) -> int:
    """تقدير خشن: الكلمات + نصف الرموز غير الكلامية — كافٍ للميزانية."""
    if isinstance(obj, str):
        return max(1, len(obj.split()) + (len(obj) - len(obj.replace(" ", "")))
                   // 2)
    if isinstance(obj, dict):
        return sum(_estimate_tokens(k) + _estimate_tokens(v)
                   for k, v in obj.items())
    if isinstance(obj, list):
        return sum(_estimate_tokens(x) for x in obj)
    return 4


class ContextManager:
    """يجمّع سياق الخطوة ضمن ميزانية، ويسجل ما أُهمل ولماذا."""

    def __init__(self, token_budget: int = 4000):
        self.token_budget = token_budget

    def assemble(self, instructions: str, facts: List[str],
                 plan: Dict[str, Any], state: Dict[str, Any],
                 retrieval: List[str]) -> Dict[str, Any]:
        """سياق مرتب بالأولوية — القطع من الأسفل (الاسترجاع أولًا يُسقط)."""
        layers = [
            ("instructions", instructions),
            ("facts", facts),
            ("plan", plan),
            ("state", state),
            ("retrieval", retrieval),
        ]
        included: Dict[str, Any] = {}
        omitted: List[Dict[str, str]] = []
        total = 0
        for name, payload in layers:
            cost = _estimate_tokens(payload)
            if total + cost <= self.token_budget:
                included[name] = payload
                total += cost
            else:
                # تلخيص: أول ٥ عناصر فقط من الحمولة القابلة للتقطيع
                if isinstance(payload, list) and payload:
                    kept = payload[:5]
                    cost = _estimate_tokens(kept)
                    if total + cost <= self.token_budget:
                        included[name] = kept
                        total += cost
                        omitted.append({"layer": name,
                                        "why": "قُطّع لأول ٥ عناصر"
                                               " (ميزانية الرموز)"})
                        continue
                omitted.append({"layer": name,
                                "why": f"استُبعد — تجاوز ميزانية"
                                       f" {self.token_budget} رمز"})
        return {"context": included, "omitted": omitted,
                "estimated_tokens": total}
