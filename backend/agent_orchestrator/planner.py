# -*- coding: utf-8 -*-
"""R-841 (4.3): محرك التخطيط — خطة صريحة مسجلة قبل أي تنفيذ.

نمط مزدوج: plan_execute للمهام المركبة (تفكيك + اعتماديات + بديل)،
وreact للمهام الاستكشافية (خطوة فحص أولى ثم تكييف).
الاختيار حتمي من التمثيل الدلالي (طبقة الفهم) — لا تخطيط بلا مبرر مسجل.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from . import schemas
from .semantic_planner import BrainPlanner, SemanticRanker
from .tool_registry import ToolDefinition, ToolRegistry, new_decision


class Planner:
    """يبني خطة صالحة المخطط من التمثيل الدلالي للطلب.

    R-842: الاختيار عبر BrainPlanner (مرتِّب دلالي حتمي + عقل عند الغموض)؛
    اختيار R-841 بالكلمات المفتاحية محفوظ في _keyword_candidates خط أساسٍ للتقييم.
    """

    def __init__(self, tools: ToolRegistry, brain_fn=None,
                 planner_mode: Optional[str] = None):
        self.tools = tools
        self.ranker = SemanticRanker(tools)
        self.selector = BrainPlanner(self.ranker, brain_fn=brain_fn,
                                     mode=planner_mode)

    def _candidates(self, semantic: Dict[str, Any],
                   trace_ref: str) -> Dict[str, Any]:
        """R-842: اختيار دلالي — نفس شكل الناتج القديم + كائن الاختيار للأثر."""
        sel = self.selector.select(semantic)
        return {"candidates": list(sel.tools), "rejected": list(sel.rejected),
                "intent": (semantic.get("intent") or {}).get("label", "request"),
                "selection": sel}

    # ------------------------------------------------------------ تحليل النية (R-841)
    def _keyword_candidates(self, semantic: Dict[str, Any],
                            trace_ref: str) -> Dict[str, Any]:
        """اختيار R-841 بالكلمات المفتاحية — خط أساس للتقييم فقط (R-842)."""
        utterance = (semantic.get("utterance") or "").lower()
        entities = semantic.get("entities") or []
        intent = (semantic.get("intent") or {}).get("label", "request")
        candidates: List[ToolDefinition] = []
        rejected: List[str] = []

        has_github = any("github.com" in str(e.get("surface", "")).lower()
                         for e in entities) or "github" in utterance \
            or "مستودع" in utterance or "ريبو" in utterance
        wants_issue = any(w in utterance for w in
                           ("مشكلة", "issue", "انشيء", "افتح", "فتح")) \
            and has_github
        wants_write = wants_issue or "أنشئ" in utterance or "انشئ" in utterance
        wants_supabase = any(w in utterance for w in
                              ("supabase", "جدول", "قاعدة البيانات", "صفوف"))
        wants_render = any(w in utterance for w in
                           ("render", "خدمات النشر", "الخدمات المنشورة"))
        wants_openapi = any(w in utterance for w in
                            ("openapi", "مواصفة", "swagger"))

        if wants_issue:
            candidates.append(self.tools.get("github.issue_create"))
        if has_github and not wants_write:
            candidates.append(self.tools.get("github.repo_read"))
        if wants_supabase:
            candidates.append(self.tools.get("supabase.table_select"))
        if wants_render:
            candidates.append(self.tools.get("render.services_list"))
        if wants_openapi:
            candidates.append(self.tools.get("openapi.register_spec"))
        if not candidates and has_github:
            candidates.append(self.tools.get("github.repo_read"))

        # البرهان: أداة غير مطابقة للنية تُرفض وتُسجل الأسباب
        for tid in ("github.issue_create", "openapi.register_spec"):
            if tid not in [c.tool_id for c in candidates] and (
                    tid == "github.issue_create" and has_github and not wants_write
                    or tid == "openapi.register_spec" and wants_supabase):
                rejected.append(tid)
        if not candidates:
            rejected.append("no_tool_matched")
        return {"candidates": candidates, "rejected": rejected,
                "intent": intent}

    def _extract_inputs(self, tool: ToolDefinition,
                         semantic: Dict[str, Any]) -> Dict[str, Any]:
        """استخراج المدخلات من الكيانات المحلولة — لا افتراضات صامتة."""
        text = semantic.get("utterance") or ""
        entities = semantic.get("entities") or []
        inputs: Dict[str, Any] = {}
        props = tool.input_schema.get("properties", {})
        for name in props:
            if name == "owner":
                for e in entities:
                    s = str(e.get("surface", ""))
                    if "github.com" in s.lower():
                        parts = s.rstrip("/").split("/")
                        if len(parts) >= 4:
                            inputs["owner"] = parts[-2]
                            break
                if "owner" not in inputs and "/" in text and "github.com" in text:
                    seg = text.split("github.com/")[-1].split()[0]
                    if "/" in seg:
                        inputs["owner"] = seg.split("/")[0]
                if "owner" not in inputs:
                    # سلاگ owner/repo (بلا نطاق) — كيان أو نص
                    import re as _re
                    slug = None
                    for e in entities:
                        s = str(e.get("surface", "")).strip("/")
                        if _re.fullmatch(r"[\w.-]+/[\w.-]+", s):
                            slug = s
                            break
                    if slug is None:
                        m = _re.search(
                            r"(?:^|\s)([\w.-]{2,}/[\w.-]{2,})(?:\s|$)", text)
                        if m:
                            slug = m.group(1)
                    if slug:
                        inputs["owner"] = slug.split("/")[0]
            elif name == "repo":
                for e in entities:
                    s = str(e.get("surface", ""))
                    if "github.com" in s.lower():
                        parts = s.rstrip("/").split("/")
                        if len(parts) >= 4:
                            inputs["repo"] = parts[-1]
                            break
                if "repo" not in inputs and "/" in text and "github.com" in text:
                    seg = text.split("github.com/")[-1].split()[0]
                    if "/" in seg and seg.split("/")[1]:
                        inputs["repo"] = seg.split("/")[1]
                if "repo" not in inputs:
                    import re as _re
                    for e in entities:
                        s = str(e.get("surface", "")).strip("/")
                        if _re.fullmatch(r"[\w.-]+/[\w.-]+", s):
                            inputs["repo"] = s.split("/")[1]
                            break
                    if "repo" not in inputs:
                        m = _re.search(
                            r"(?:^|\s)([\w.-]{2,}/[\w.-]{2,})(?:\s|$)", text)
                        if m and "owner" in inputs:
                            inputs["repo"] = m.group(1).split("/")[1]
            elif name == "title":
                # عنوان المشكلة: النص بعد كلمة العنوان إن وجدت، وإلا الطلب كله
                for marker in ("عنوان", "بعنوان", "باسم"):
                    if marker in text:
                        inputs["title"] = text.split(marker)[-1].strip()[:140]
                        break
                if "title" not in inputs:
                    inputs["title"] = text[:140]
            elif name == "table":
                for e in entities:
                    if e.get("type") in ("table", "entity") and str(
                            e.get("surface", "")).isidentifier():
                        inputs["table"] = e["surface"]
                        break
                if "table" not in inputs:  # R-842: «table X» / «X table» بالإنجليزية
                    import re as _re
                    m = _re.search(r"\btable\s+([A-Za-z_]\w*)", text) or \
                        _re.search(r"\b([A-Za-z_]\w*)\s+table\b", text)
                    if m and m.group(1).lower() not in ("the", "a", "this", "that", "our"):
                        inputs["table"] = m.group(1)
                if "table" not in inputs and "جدول" in text:
                    # الكلمة التالية لـ«جدول» — استخراج نصي صريح لا افتراض
                    parts = text.split("جدول")
                    if len(parts) > 1 and parts[1].split():
                        cand = parts[1].split()[0].strip("،,.؛;:")
                        if cand.isidentifier():
                            inputs["table"] = cand
            elif name == "service_id":
                for e in entities:
                    if e.get("surface", "").startswith("srv-"):
                        inputs["service_id"] = e["surface"]
            elif name == "spec":
                inputs["spec"] = {}
        # الحد الإلزامي: كل مفتاح مطلوب لا قيمة له يُرفض عند التحقق لاحقًا
        return {k: v for k, v in inputs.items() if v is not None}

    # ------------------------------------------------------------ بناء الخطة
    def build(self, request: Dict[str, Any], semantic: Dict[str, Any],
              trace_ref: str) -> Dict[str, Any]:
        sel = self._candidates(semantic, trace_ref)
        if not sel["candidates"]:
            raise ValueError(
                "لا أداة مطابقة للطلب — أعد صياغة الهدف أو أضف أداة للسجل")
        # النمط: مركب (3+ أدوات أو نية إنشاء) → plan_execute، وإلا react
        exploratory = len(sel["candidates"]) == 1 and \
            sel["candidates"][0].access == "read"
        mode = "react" if exploratory else "plan_execute"
        # R-842: الأداة معروفة لكن مدخلاتها الإلزامية ناقصة ⇒ سؤال توضيحي لا افتراض
        extracted = {t.tool_id: self._extract_inputs(t, semantic)
                     for t in sel["candidates"]}
        missing = {t.tool_id: [k for k in t.input_schema.get("required", [])
                               if k not in extracted[t.tool_id]]
                   for t in sel["candidates"]}
        missing = {k: v for k, v in missing.items() if v}
        if missing:
            detail = "؛ ".join(f"{tid}: {', '.join(v)}" for tid, v in missing.items())
            raise ValueError(f"مدخلات إلزامية ناقصة ({detail}) — حدّدها في طلبك")
        steps: List[Dict[str, Any]] = []
        for i, tool in enumerate(sel["candidates"], 1):
            requires_approval = tool.access in ("write", "admin") \
                or tool.risk == "high"
            steps.append({
                "step_id": f"s{i}",
                "goal": tool.description.split("—")[0].strip(),
                "tool_id": tool.tool_id,
                "inputs": extracted[tool.tool_id],
                "depends_on": [f"s{i-1}"] if mode == "plan_execute" and i > 1 else [],
                "requires_approval": requires_approval,
                "success_criteria": f"استجابة ناجحة من {tool.connector_id}"
                                    f".{tool.operation}",
                "fallback": "" if i == len(sel["candidates"]) else f"s{i}",
            })
        selection = sel.get("selection")
        plan = {
            "plan_id": str(uuid.uuid4()),
            "goal": request["utterance"][:200],
            "steps": steps,
            "approval_points": [s["step_id"] for s in steps
                               if s["requires_approval"]],
            "max_steps": int(request["constraints"]["max_steps"]),
            "estimated_cost": round(sum(
                self.tools.get(s["tool_id"]).estimated_cost
                for s in steps), 6),
            "estimated_time_s": round(sum(
                self.tools.get(s["tool_id"]).estimated_time_s
                for s in steps), 3),
            "mode": mode,
            "planning_reason": (
                f"نية={sel['intent']}؛ أدوات مرشحة="
                f"{[c.tool_id for c in sel['candidates']]}؛ مرفوضة="
                f"{sel['rejected']}؛ نمط {mode}"
                + (" (أداة قراءة واحدة — استكشافي)"
                   if exploratory else " (تفكيك مركب)")
                + (f"؛ {selection.reason}" if selection is not None else "")),
        }
        if selection is not None:  # R-842: تفسير الاختيار مرفق بالخطة للأثر
            plan["selection"] = selection.public()
        schemas.validate(plan, schemas.PLAN_SCHEMA)
        return plan

    def replan(self, plan: Dict[str, Any], failed_step_id: str,
              reason: str, trace_ref: str) -> Dict[str, Any]:
        """خطة بديلة عند فشل خطوة حرجة — تسقط الخطوة الفاشلة وتسجل السبب."""
        new_steps = []
        for s in plan["steps"]:
            if s["step_id"] == failed_step_id:
                if s["fallback"]:
                    continue  # البديل المعلن: تخطَّ الخطوة
                new_steps.append({**s, "goal": s["goal"] + " (إعادة محاولة"
                                              " بعد فشل معالج)"})
            else:
                new_steps.append(s)
        if not new_steps:
            raise ValueError("فشل إعادة التخطيط: لا خطوات متبقية")
        replanned = {**plan, "steps": new_steps,
                     "planning_reason": f"إعادة تخطيط بعد فشل {failed_step_id}:"
                                        f" {reason}"}
        schemas.validate(replanned, schemas.PLAN_SCHEMA)
        return replanned
