# -*- coding: utf-8 -*-
"""R-843: سجل المجموعات المجمّدة — كل مجموعة: بيانات ثابتة ببصمة + أرضية + مشغّل.

القواعد:
- البيانات **مجمّدة ببصمة sha256 مثبتة هنا**. أي تعديل على ملف بيانات يُفشل
  التقييم (`sha_ok=False`) حتى تُحدَّث البصمة في الكود — فيظهر في الفرق ويمر
  ببوابة المراجعة والوثائق (لا ضبط صامت على الاختبار).
- الأرضية حد أدنى لا يُخفض بلا قرار موثق (DECISIONS). الحوكمة أرضيتها 1.0.
- المشغّلات حتمية (بلا عقل ولا شبكة) ⇒ تُشغَّل في CI على كل تغيير.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List

_ROOT = Path(__file__).resolve().parent
_ORCH_EVAL = _ROOT.parent / "agent_orchestrator" / "eval"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class Suite:
    suite_id: str
    layer: str
    description: str
    data_path: Path
    sha256: str
    floor: float
    runner: Callable[[Path], Dict[str, Any]]

    def public(self) -> Dict[str, Any]:
        return {"suite_id": self.suite_id, "layer": self.layer,
                "description": self.description,
                "data": _rel(self.data_path),
                "sha256": self.sha256, "floor": self.floor}


def _rel(p: Path) -> str:
    """مسار نسبي للمستودع إن أمكن، وإلا المسار كما هو (مجموعات مؤقتة في الاختبار)."""
    root = _ROOT.parent.parent
    return str(p.relative_to(root)) if p.is_relative_to(root) else str(p)


def _planner(set_name: str):
    def run(_path: Path) -> Dict[str, Any]:
        try:
            from agent_orchestrator import planning_eval
        except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
            from backend.agent_orchestrator import planning_eval
        r = planning_eval.evaluate(set_name, "semantic")
        return {"score": r["accuracy"], "passed": r["correct"], "n": r["n"],
                "failures": r["failures"],
                "extra": {"abstain_accuracy": r["abstain_accuracy"],
                          "action_precision": r["action_precision"]}}
    return run


def _governance(path: Path) -> Dict[str, Any]:
    from . import governance
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    return governance.run(cases)


SUITES: List[Suite] = [
    Suite("planner.dev", "orchestrator/planner",
          "اختيار الأدوات — مجموعة التطوير (50 هدفًا، R-842)",
          _ORCH_EVAL / "planning_goals.json",
          "da42153b6962e7623a201473f1a493cfd89d4e7caef073bc0363a7a263ec838e",
          0.90, _planner("dev")),
    Suite("planner.holdout", "orchestrator/planner",
          "اختيار الأدوات — المجموعة المعزولة المجمّدة قبل التنفيذ (20 هدفًا، R-842)",
          _ORCH_EVAL / "planning_holdout.json",
          "7eaece466afcdde6ed7af4a42a8e9287f50000cb21ff1326edaa6e9f727020ec",
          0.90, _planner("holdout")),
    Suite("orchestrator.governance", "orchestrator/governance",
          "مبادئ الميثاق كحالات تشغيل كاملة: موافقة/صلاحية/عدم تكرار/لا retry أعمى/"
          "لا نجاح كاذب/لا تسريب/حراسة العقل (20 حالة، R-843)",
          _ROOT / "data" / "governance_cases.json",
          "eefa20e63705daa5c39af09c55891115b5d8f5a547644fa12cab29b7e7c8df87",
          1.0, _governance),
]


def get(suite_id: str) -> Suite:
    for s in SUITES:
        if s.suite_id == suite_id:
            return s
    raise KeyError(f"مجموعة غير معروفة: {suite_id}")
