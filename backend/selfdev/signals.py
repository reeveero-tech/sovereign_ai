"""R-798: المجسّات — إشارات موحّدة من كل جزء في النظام.

كل مجمّع دالة نقية: يأخذ ناتج مصدر حقيقي (تقرير/حالة) ويعيد قائمة إشارات بالشكل نفسه:

  {key, origins[], component, severity, title, evidence, kind_hint, tools[], files_hint[]}

- key: معرّف ثابت للظاهرة (نفس معرّف العيب حين يوجد) — يدمج المصادر المتعددة للظاهرة.
- kind_hint: code_fix | investigation | owner_action | operational | unmet.
- لا تخمين: إشارة بلا دليل حرفي لا تُنشأ؛ مصدر تعذّر = إشارة source_unavailable معلنة.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple

SEVERITY_WEIGHT = {"high": 3.0, "medium": 2.0, "low": 1.0}
EVIDENCE_MAX = 600


def _sig(key: str, origin: str, severity: str, title: str, evidence: Any,
         kind_hint: str = "investigation", component: str = "", tools: Optional[List[str]] = None,
         files_hint: Optional[List[str]] = None, ref: Optional[str] = None) -> Dict[str, Any]:
    return {"key": key, "origins": [origin], "component": component or key.split(":")[0],
            "severity": severity if severity in SEVERITY_WEIGHT else "medium",
            "title": str(title)[:200], "evidence": str(evidence)[:EVIDENCE_MAX],
            "kind_hint": kind_hint, "tools": list(tools or []),
            "files_hint": list(files_hint or []), "ref": ref}


def evidence_hash(sig: Dict[str, Any]) -> str:
    return hashlib.sha256((sig.get("key", "") + "|" + sig.get("evidence", "")).encode("utf-8")
                          ).hexdigest()[:16]


def _tool_from_key(key: str) -> List[str]:
    for marker in ("tool_failing:",):
        if marker in key:
            return [key.split(marker, 1)[1]]
    return []


def from_proposals(items: Any) -> List[Dict[str, Any]]:
    out = []
    for p in items or []:
        if not isinstance(p, dict):
            continue
        if p.get("status") in ("suppressed", "rejected", "implemented"):
            continue
        if p.get("defect_open") is False:
            continue
        key = p.get("defect_id") or p.get("id")
        if not key:
            continue
        out.append(_sig(key, "proposals", p.get("severity") or "medium",
                        p.get("title") or key,
                        f"{p.get('evidence', '')} | توصية: {p.get('recommendation', '')}",
                        kind_hint=p.get("kind") or "investigation", tools=_tool_from_key(key),
                        ref=p.get("id")))
    return out


def from_defect_report(report: Any, origin: str = "defect_scan") -> List[Dict[str, Any]]:
    out = []
    if not isinstance(report, dict):
        return out
    for d in report.get("defects") or []:
        if not isinstance(d, dict) or d.get("status") != "open" or not d.get("id"):
            continue
        did = d["id"]
        kind = "code_fix" if (did.startswith(("component_unhealthy:", "scheduled_task_failed:"))
                              or "tool_failing:" in did) else "investigation"
        if did.startswith("selfmon:disk_"):
            kind = "owner_action"
        out.append(_sig(did, origin, d.get("severity") or "medium", d.get("title") or did,
                        d.get("evidence") or "", kind_hint=kind, component=d.get("area") or "",
                        tools=_tool_from_key(did)))
    return out


def from_scheduler(status: Any) -> List[Dict[str, Any]]:
    out = []
    if not isinstance(status, dict):
        return out
    for t in status.get("tasks") or []:
        if t.get("last_ok") is False and t.get("runs", 0) > 0:
            out.append(_sig(f"scheduled_task_failed:{t.get('name')}", "scheduler", "medium",
                            f"المهمة المجدولة {t.get('name')} فشلت",
                            f"tool={t.get('tool')} last_error={t.get('last_error')}",
                            kind_hint="code_fix", component="scheduler",
                            tools=[t.get("tool")] if t.get("tool") else []))
    return out


def from_tool_stats(stats: Any, min_calls: int = 3, fail_below: float = 0.5) -> List[Dict[str, Any]]:
    out = []
    if not isinstance(stats, dict):
        return out
    for tool, s in sorted(stats.items()):
        s = s or {}
        rate = s.get("success_rate")
        if s.get("calls", 0) >= min_calls and rate is not None and rate < fail_below:
            out.append(_sig(f"selfmon:tool_failing:{tool}", "tool_stats", "medium",
                            f"الأداة {tool} تفشل غالبًا",
                            f"success_rate={rate} calls={s.get('calls')} last_error={s.get('last_error')}",
                            kind_hint="code_fix", component="tools", tools=[tool]))
    return out


def from_brain(outcome: Any) -> List[Dict[str, Any]]:
    if not isinstance(outcome, dict) or outcome.get("result") in (None, "none", "ok", "success"):
        return []
    return [_sig("brain_call_failed", "brain", "high", "آخر نداء للعقل فشل",
                 f"result={outcome.get('result')} error={outcome.get('error')}",
                 kind_hint="operational", component="brain", files_hint=["backend/ollama_client.py"])]


def from_goals(state: Any) -> List[Dict[str, Any]]:
    out = []
    if not isinstance(state, dict):
        return out
    for gid, g in sorted(state.items()):
        g = g or {}
        if g.get("status") == "blocked":
            out.append(_sig(f"goal_blocked:{gid}", "goals", "medium",
                            f"هدف متعذر: {str(g.get('title'))[:80]}",
                            f"why={g.get('why')} runs={len(g.get('runs') or [])}",
                            kind_hint="unmet", component="goals", ref=gid))
    return out


def from_selfdev(status: Any) -> List[Dict[str, Any]]:
    out = []
    if not isinstance(status, dict):
        return out
    for t in status.get("tasks") or []:
        if t.get("status") == "exhausted" and t.get("source") != "unmet":
            out.append(_sig(f"selfdev_exhausted:{t.get('id')}", "selfdev", "medium",
                            f"إصلاح عجز عنه المحرك: {str(t.get('title'))[:80]}",
                            f"attempts={t.get('attempts')} errors={t.get('errors')} ci={t.get('ci')}",
                            kind_hint="unmet", component="selfdev",
                            files_hint=[t["file"]] if t.get("file") else [], ref=t.get("id")))
    return out


COLLECTORS: Dict[str, Callable[[Any], List[Dict[str, Any]]]] = {
    "proposals": from_proposals,
    "defects": from_defect_report,
    "self_monitor": lambda r: from_defect_report(r, origin="self_monitor"),
    "scheduler": from_scheduler,
    "tool_stats": from_tool_stats,
    "brain": from_brain,
    "goals": from_goals,
    "selfdev": from_selfdev,
}


def merge(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """دمج الظاهرة نفسها من مصادر متعددة: الأصول تتجمع، الأشد يغلب، الأدلة تتسلسل."""
    by: Dict[str, Dict[str, Any]] = {}
    for s in signals:
        cur = by.get(s["key"])
        if cur is None:
            by[s["key"]] = dict(s, origins=list(s["origins"]), tools=list(s["tools"]),
                                files_hint=list(s["files_hint"]))
            continue
        for o in s["origins"]:
            if o not in cur["origins"]:
                cur["origins"].append(o)
        if SEVERITY_WEIGHT[s["severity"]] > SEVERITY_WEIGHT[cur["severity"]]:
            cur["severity"] = s["severity"]
        if s["kind_hint"] == "code_fix":
            cur["kind_hint"] = "code_fix"
        for k in ("tools", "files_hint"):
            for v in s[k]:
                if v and v not in cur[k]:
                    cur[k].append(v)
        if s["evidence"] and s["evidence"] not in cur["evidence"]:
            cur["evidence"] = (cur["evidence"] + " ‖ " + s["evidence"])[:EVIDENCE_MAX]
        cur["ref"] = cur.get("ref") or s.get("ref")
    return list(by.values())


def gather(sources: Dict[str, Callable[[], Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """يقرأ كل مصدر معزولًا؛ تعذّر مصدر لا يُسقط الجمع ويُعلن إشارة منخفضة."""
    raw: List[Dict[str, Any]] = []
    errors: Dict[str, str] = {}
    for name, fn in sources.items():
        coll = COLLECTORS.get(name)
        if coll is None:
            continue
        try:
            raw.extend(coll(fn()))
        except Exception as exc:  # TOLERATED: مصدر ناقص يُعلن إشارة لا انهيارًا
            errors[name] = f"{type(exc).__name__}: {str(exc)[:160]}"
            raw.append(_sig(f"selfdev:source_unavailable:{name}", "nucleus", "low",
                            f"مجسّ «{name}» تعذّر", errors[name], kind_hint="investigation",
                            component="selfdev"))
    return merge(raw), errors
