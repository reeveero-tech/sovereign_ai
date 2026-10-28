"""R-798: ربط حزمة التطوير الذاتي بالنظام كوحدة واحدة.

المصادر هنا هي الكائنات التشغيلية الحية نفسها (لا نسخ ولا قيم ثابتة). المجدول يُربط من
app.py عند الإقلاع عبر bind_scheduler (منعًا للاستيراد الدائري).

full_cycle() = دورة واحدة كاملة تحل محل دورة R-796:
  النواة (جمع ⇒ أولوية ⇒ صياغة ⇒ توجيه) ⇒ محرك التطوير (CI + اقتراحات + مسودة واحدة)
  ⇒ محرك الأهداف المتعذرة (مزامنة المستنفد ⇒ مراجعة ⇒ تصعيد واحد)
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional

import self_develop

from .locator import Locator
from .nucleus import Nucleus
from .proposal_brain import ProposalBrain
from .unmet import UnmetGoals

_SCHEDULER_FN: Optional[Callable[[], Any]] = None
_LOCK = threading.Lock()
_NUCLEUS: Optional[Nucleus] = None
_UNMET: Optional[UnmetGoals] = None


def bind_scheduler(fn: Optional[Callable[[], Any]]) -> None:
    global _SCHEDULER_FN
    _SCHEDULER_FN = fn


def _scheduler_status() -> Any:
    if _SCHEDULER_FN is None:
        return {}
    return _SCHEDULER_FN()


def default_sources() -> Dict[str, Callable[[], Any]]:
    def proposals():
        import improvement_proposals
        return improvement_proposals.get_book().list()

    def defects():
        import defect_scan
        return defect_scan.get_worklist().last_report()

    def monitor():
        import self_monitor
        return self_monitor.get_monitor().last_report()

    def tool_stats():
        import experience
        return experience.get_store().tool_stats()

    def brain():
        import ollama_client
        return ollama_client.last_outcome()

    def goals_state():
        import goals
        return goals.GoalStore().state()

    return {"proposals": proposals, "defects": defects, "self_monitor": monitor,
            "scheduler": _scheduler_status, "tool_stats": tool_stats, "brain": brain,
            "goals": goals_state, "selfdev": lambda: self_develop.get_engine().status()}


def _registry():
    from tool_registry import get_registry
    return get_registry()


def get_unmet() -> UnmetGoals:
    global _UNMET
    with _LOCK:
        if _UNMET is None:
            eng = self_develop.get_engine()
            _UNMET = UnmetGoals(eng, brain=eng._brain)
        return _UNMET


def get_nucleus() -> Nucleus:
    global _NUCLEUS
    unmet = get_unmet()
    with _LOCK:
        if _NUCLEUS is None:
            eng = self_develop.get_engine()
            locator = Locator(registry_fn=_registry, engine=eng)
            _NUCLEUS = Nucleus(default_sources(), ProposalBrain(eng._brain, locator), eng, unmet)
        return _NUCLEUS


def reset(nucleus: Optional[Nucleus] = None, unmet: Optional[UnmetGoals] = None) -> None:
    global _NUCLEUS, _UNMET
    with _LOCK:
        _NUCLEUS, _UNMET = nucleus, unmet


def full_cycle(now: Optional[float] = None, proposals: Optional[list] = None) -> Dict[str, Any]:
    now = time.time() if now is None else now
    nucleus, unmet, engine = get_nucleus(), get_unmet(), self_develop.get_engine()
    out: Dict[str, Any] = {"at": now}
    active = None
    try:
        n = nucleus.cycle(now=now)
        out["nucleus"] = n["cycle"]
        active = set(n["active_keys"])
    except Exception as exc:  # TOLERATED: فشل النواة يُعلن ولا يوقف المحرك
        out["nucleus"] = {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    if proposals is None:
        try:
            import improvement_proposals
            proposals = improvement_proposals.get_book().list()
        except Exception as exc:  # TOLERATED: بلا دفتر اقتراحات — يُعلن
            proposals = []
            out["proposals_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    out["engine"] = engine.tick(proposals=proposals, now=now)
    try:
        out["unmet"] = unmet.cycle(active_keys=active, now=now)
    except Exception as exc:  # TOLERATED: فشل محرك الأهداف يُعلن
        out["unmet"] = {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    # توافق R-796: الحقول العليا لدورة المحرك تبقى كما هي لمن يقرأها
    for k in ("tick", "status", "task", "ci_applied", "ingested"):
        if k in out["engine"]:
            out[k] = out["engine"][k]
    return out
