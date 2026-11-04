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


def _queue(path: Path) -> Dict[str, Any]:
    from . import queue_reliability
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    return queue_reliability.run(cases)


def _notify(path: Path) -> Dict[str, Any]:
    from . import notify_reliability
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    return notify_reliability.run(cases)


def _observability(path: Path) -> Dict[str, Any]:
    from . import observability_reliability
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    return observability_reliability.run(cases)


def _backup(path: Path) -> Dict[str, Any]:
    from . import backup_reliability
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    return backup_reliability.run(cases)


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
    Suite("queue.reliability", "job_queue",
          "موثوقية الطابور: انقطاع أثناء كتابة/قراءة، عدم تكرار، سياج، ضغط خلفي،"
          " لا retry أعمى، عزل الموافقات، دوامها بعد إعادة التشغيل (14 حالة، R-844)",
          _ROOT / "data" / "queue_cases.json",
          "8d8671b5d81dc2533359a947931d97ae0f80181efd0f76cb401362a6e2437574",
          1.0, _queue),
    Suite("notify.reliability", "notifications",
          "موثوقية الإشعارات: عدم تكرار، توقيع، أقل بيانات، لا retry على 401، حد الساعة،"
          " نجاة من الانقطاع، تنقية الأسرار، لا إشعارين لسبب واحد (15 حالة، R-845)",
          _ROOT / "data" / "notify_cases.json",
          "07a7258f035ce73761ce0b1c84316defa5496fa5f02831a29d08721a34feaa87",
          1.0, _notify),
    Suite("observability.reliability", "observability",
          "موثوقية الرصد: معرّف الطلب، وسوم القوالب وسقف السلاسل، صيغة Prometheus، مصادقة"
          " المقاييس، تنقية السجلات، آثار دائمة محدودة، جاهزية صادقة وإشعار واحد (19 حالة، R-846)",
          _ROOT / "data" / "observability_cases.json",
          "75f26c103de7bb81a399d0fe75df5a40d86ab774c0ac7b917377bbae04b4f991",
          1.0, _observability),
    Suite("backup.reliability", "backup",
          "موثوقية النسخ والاستعادة: لقطة WAL متسقة، ذيل jsonl، بيان وبصمات، استثناءات،"
          " كشف العبث وtar-slip، تشفير عند السكون، رفع خارجي مشفر بلا إعادة عمياء،"
          " احتفاظ، استعادة بخطة وتأكيد ونسخة سابقة وتراجع واستئناف، جاهزية، طابور،"
          " تعافٍ من كارثة، سقف وقفل (23 حالة، R-847)",
          _ROOT / "data" / "backup_cases.json",
          "68a8908385b3bd48625e066bb5b133ee8cce0d078599db291053967bc7cd851a",
          1.0, _backup),
]


def get(suite_id: str) -> Suite:
    for s in SUITES:
        if s.suite_id == suite_id:
            return s
    raise KeyError(f"مجموعة غير معروفة: {suite_id}")
