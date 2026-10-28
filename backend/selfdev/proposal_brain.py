"""R-798: عقل الاقتراح — من «إشارة + دليل + شيفرة حقيقية» إلى اقتراح إصلاح قابل للتنفيذ.

المخرج (مخطط JSON إلزامي، ثم تحقق):
  root_cause      فرضية السبب الجذري مستندة إلى الدليل والشيفرة المعروضة
  route           code_fix | operational | owner_action | no_action
  target_file     ملف من المواضع القابلة للتعديل حصرًا (enum) أو "none"
  plan            خطوات (1..6)
  acceptance_test ما يجب أن يثبته اختبار RED→GREEN
  confidence      0..1

التحقق يخفّض بدل أن يختلق: code_fix بلا ملف قابل للتعديل ⇒ unresolved (يذهب لمحرك الأهداف
المتعذرة)؛ خطة فارغة ⇒ unresolved؛ ثقة خارج المدى تُقصّ. بلا عقل: تحليل حتمي معلن
(brain=false) — لا سبب جذري مختلق، والمسار من نوع الإشارة فقط.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

ROUTES = ("code_fix", "operational", "owner_action", "no_action")

SYSTEM = (
    "أنت كبير مهندسي الموثوقية في مشروع sovereign_ai. ستُعطى إشارة خلل حقيقية من النظام "
    "(مفتاحها، مصادرها، شدتها، دليلها الحرفي) ومقتطفات حقيقية من الشيفرة مع أرقام الأسطر.\n"
    "المطلوب: سبب جذري مستند إلى الدليل والشيفرة فقط (لا تخترع ما ليس فيهما)، ومسار:\n"
    "- code_fix: الخلل في الشيفرة ويمكن إصلاحه بتعديل صغير في ملف من القائمة المسموحة.\n"
    "- operational: خلل تشغيلي (شبكة/عقل/مورد) لا يحله تعديل الشيفرة الآن.\n"
    "- owner_action: يحتاج قرار المالك أو سرًا أو إعدادًا.\n"
    "- no_action: الإشارة ليست خللًا فعليًا.\n"
    "اختر target_file من القائمة المسموحة حرفيًا أو none. خطة من 1 إلى 6 خطوات، واختبار "
    "قبول يصف ما يفشل قبل الإصلاح وينجح بعده. confidence بين 0 و1. أجب JSON فقط."
)


def schema(editable: List[str]) -> Dict[str, Any]:
    return {"type": "object",
            "properties": {
                "root_cause": {"type": "string"},
                "route": {"type": "string", "enum": list(ROUTES)},
                "target_file": {"type": "string", "enum": list(editable) + ["none"]},
                "plan": {"type": "array", "items": {"type": "string"}},
                "acceptance_test": {"type": "string"},
                "confidence": {"type": "number"}},
            "required": ["root_cause", "route", "target_file", "plan", "acceptance_test",
                         "confidence"]}


def _parse(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        d = json.loads(m.group(0) if m else raw)
        return d if isinstance(d, dict) else None
    except (ValueError, AttributeError):
        return None


def deterministic(signal: Dict[str, Any], locations: List[Dict[str, Any]],
                  reason: str) -> Dict[str, Any]:
    """بلا عقل: مسار من نوع الإشارة فقط، لا سبب جذري مختلق (معلن brain=false)."""
    kind = signal.get("kind_hint")
    editable = [l["file"] for l in locations if l.get("editable")]
    if kind == "code_fix" and editable:
        route = "code_fix"
    elif kind == "owner_action":
        route = "owner_action"
    elif kind == "operational":
        route = "operational"
    else:
        route = "unresolved"
    return {"brain": False, "reason": reason, "root_cause": None, "route": route,
            "target_file": editable[0] if route == "code_fix" else None,
            "plan": [], "acceptance_test": None, "confidence": None,
            "locations": locations}


def validate(d: Dict[str, Any], editable: List[str]) -> Dict[str, Any]:
    notes = []
    route = d.get("route")
    if route not in ROUTES:
        notes.append(f"route_invalid:{route}")
        route = "unresolved"
    target = d.get("target_file")
    if target in (None, "", "none"):
        target = None
    if target is not None and target not in editable:
        notes.append(f"target_outside_editable:{target}")
        target = None
    plan = [str(p)[:300] for p in (d.get("plan") or []) if str(p).strip()][:6]
    if route == "code_fix" and (target is None or not plan):
        notes.append("code_fix_without_target_or_plan")
        route = "unresolved"
    try:
        conf = float(d.get("confidence"))
        conf = min(1.0, max(0.0, conf))
    except (TypeError, ValueError):
        conf = None
        notes.append("confidence_invalid")
    root = str(d.get("root_cause") or "").strip()[:800] or None
    if root is None:
        notes.append("root_cause_empty")
    return {"brain": True, "root_cause": root, "route": route, "target_file": target,
            "plan": plan, "acceptance_test": str(d.get("acceptance_test") or "")[:600] or None,
            "confidence": conf, "validation_notes": notes}


class ProposalBrain:
    def __init__(self, brain: Optional[Callable[[str, str, Dict[str, Any]], Optional[str]]],
                 locator) -> None:
        self._brain = brain
        self.locator = locator
        self.calls = 0
        self.failures = 0

    def analyze(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        locations = self.locator.locate(signal)
        if self._brain is None:
            return deterministic(signal, locations, "brain_unavailable")
        editable = [l["file"] for l in locations if l.get("editable")]
        snippets = []
        for loc in locations[:3]:
            snippets.append(f"### {loc['file']} (سطر {loc['line']} — {loc['why']}"
                            f"{'' if loc.get('editable') else ' — محمي، للفهم فقط'})\n"
                            f"{self.locator.snippet(loc)}")
        user = (f"الإشارة: {signal['key']}\nالعنوان: {signal.get('title')}\n"
                f"المصادر: {', '.join(signal.get('origins') or [])} — الشدة: {signal.get('severity')}\n"
                f"الدليل الحرفي: {signal.get('evidence')}\n"
                f"الملفات المسموح تعديلها: {editable or ['none']}\n\n" + "\n\n".join(snippets))
        self.calls += 1
        parsed = _parse(self._brain(SYSTEM, user, schema(editable)))
        if parsed is None:
            self.failures += 1
            return deterministic(signal, locations, "brain_invalid_or_unavailable")
        out = validate(parsed, editable)
        out["locations"] = locations
        return out
