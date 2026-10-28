# -*- coding: utf-8 -*-
"""R-794 (البند ٤.٦ — المراقبة الذاتية الموسّعة): النظام يقيس نفسه ويتابع اتجاهه.

يبني فوق ما هو قائم ولا يستبدله: نفس شكل تقرير العيوب (defect_scan) فيُغذّي
ProposalBook وسجل التطور (evolution_ledger) كما هما — أي اقتراح فقط، والقرار
للمالك وحده (الميثاق: لا تعديل ذاتي بلا موافقة).

ما يرصده (كله من مصادر تشغيلية حقيقية، لا تخمين):
- القرص المحلي (بايتات/عُقد) وحالته، واتجاه ارتفاع العُقد عبر الدورات.
- أدوات تفشل باستمرار (success_rate من سجل الخبرة).
- سلامة سلسلة سجل التطور (verify).
- حلقة الاستقلال: انهيار آخر دورة.
- أهداف عالقة: آخر ٣ تشغيلات لم تكتمل.
- تراكم اقتراحات التحسين بلا قرار.
- «تراجع»: اقتراح عُلّم implemented والعيب نفسه ما زال مفتوحًا (هل التطوير
  أفاد فعلًا؟ — تقييم ذاتي للتطوير لا ادعاء له).
- مصدر رصد تعذّر: يُعلن عيبًا صغيرًا لا يُبتلع (لا عمى صامت).

حدود صريحة: حالة في الذاكرة فقط؛ لا كتابة ملفات، لا أوامر، لا git، لا تعديل
شيفرة (حارس ثابت في tests/test_r794_self_monitor.py).
"""

import threading
from collections import deque
from typing import Any, Callable, Dict, List, Optional

HISTORY_SIZE = 20
TOOL_MIN_CALLS = 3
TOOL_FAIL_BELOW = 0.5
STUCK_RUNS = 3
BACKLOG_AT = 5
TREND_POINTS = 3
TREND_MIN_RISE = 5.0
EVIDENCE_MAX = 200
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _clip(value: Any) -> str:
    return str(value)[:EVIDENCE_MAX]


def _d(did: str, severity: str, area: str, title: str, evidence: Any) -> Dict[str, Any]:
    return {"id": did, "severity": severity, "area": area, "title": title,
            "evidence": _clip(evidence), "status": "open"}


def collect(sources: Dict[str, Callable[[], Any]]) -> Dict[str, Any]:
    """يقرأ كل مصدر معزولًا: تعذر مصدر لا يُسقط الدورة ويُسجَّل في errors."""
    vitals: Dict[str, Any] = {"errors": {}}
    for name, fn in sources.items():
        try:
            vitals[name] = fn()
        except Exception as exc:  # TOLERATED: مصدر ناقص يُعلن عيبًا لا انهيارًا
            vitals[name] = None
            vitals["errors"][name] = f"{type(exc).__name__}: {str(exc)[:120]}"
    return vitals


def detect(vitals: Dict[str, Any], history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []

    for name, err in sorted((vitals.get("errors") or {}).items()):
        found.append(_d(f"selfmon:source_unavailable:{name}", "low", "self_monitor",
                        f"مصدر الرصد «{name}» تعذّر", err))

    disk = vitals.get("disk")
    if isinstance(disk, dict) and not disk.get("error"):
        state = disk.get("state")
        if state in ("warning", "critical"):
            found.append(_d(f"selfmon:disk_{state}", "high" if state == "critical" else "medium",
                            "disk", f"القرص المحلي في حالة {state}",
                            f"bytes={disk.get('bytes_used_pct')}% inodes={disk.get('inodes_used_pct')}%"))
        pts = [h.get("inodes_used_pct") for h in history if h.get("inodes_used_pct") is not None]
        if disk.get("inodes_used_pct") is not None:
            pts.append(disk["inodes_used_pct"])
        tail = pts[-TREND_POINTS:]
        if (len(tail) == TREND_POINTS and all(b > a for a, b in zip(tail, tail[1:]))
                and tail[-1] - tail[0] >= TREND_MIN_RISE):
            found.append(_d("selfmon:disk_trend", "medium", "disk",
                            "عُقد القرص ترتفع باطراد عبر الدورات", f"inodes_used_pct={tail}"))
    elif isinstance(disk, dict) and disk.get("error"):
        found.append(_d("selfmon:source_unavailable:disk", "low", "self_monitor",
                        "قراءة القرص المحلي فشلت", disk.get("error")))

    stats = vitals.get("tool_stats")
    if isinstance(stats, dict):
        for tool, s in sorted(stats.items()):
            rate = (s or {}).get("success_rate")
            if (s or {}).get("calls", 0) >= TOOL_MIN_CALLS and rate is not None and rate < TOOL_FAIL_BELOW:
                found.append(_d(f"selfmon:tool_failing:{tool}", "medium", "tools",
                                f"الأداة {tool} تفشل غالبًا",
                                f"success_rate={rate} calls={s.get('calls')} last_error={s.get('last_error')}"))

    chain = vitals.get("ledger_verify")
    if isinstance(chain, dict) and chain.get("ok") is False:
        found.append(_d("selfmon:ledger_chain_broken", "high", "evolution_ledger",
                        "سلسلة سجل التطور مكسورة", chain.get("reason") or chain))

    loop = vitals.get("autonomy")
    if isinstance(loop, dict) and loop.get("enabled") and isinstance(loop.get("last"), dict) \
            and loop["last"].get("tick") == "crashed":
        found.append(_d("selfmon:autonomy_crashed", "high", "autonomy",
                        "آخر دورة استقلال انهارت", loop["last"].get("error")))

    goals = vitals.get("goals")
    if isinstance(goals, dict):
        for gid, g in sorted(goals.items()):
            runs = (g or {}).get("runs") or []
            if (g or {}).get("status") == "active" and len(runs) >= STUCK_RUNS and all(
                    r.get("status") != "completed" for r in runs[-STUCK_RUNS:]):
                found.append(_d(f"selfmon:goal_stuck:{gid}", "medium", "goals",
                                f"هدف عالق: {str(g.get('title'))[:60]}",
                                f"آخر {STUCK_RUNS} تشغيلات لم تكتمل"))

    props = vitals.get("proposals")
    if isinstance(props, list):
        waiting = [p for p in props if p.get("status") == "proposed"]
        if len(waiting) >= BACKLOG_AT:
            found.append(_d("selfmon:proposal_backlog", "low", "proposals",
                            "اقتراحات تحسين تنتظر قرار المالك",
                            f"proposed={len(waiting)} ids={[p.get('id') for p in waiting][:6]}"))
        for p in props:
            if p.get("status") == "implemented" and p.get("defect_open"):
                found.append(_d(f"selfmon:regression:{p.get('id')}", "high", "proposals",
                                "اقتراح منفّذ والعيب ما زال مفتوحًا — التطوير لم يُجدِ",
                                f"{p.get('id')} defect={p.get('defect_id')} commit={p.get('commit')}"))
    return found


class SelfMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._history: deque = deque(maxlen=HISTORY_SIZE)
        self._scans = 0
        self._last: Optional[Dict[str, Any]] = None

    def run(self, sources: Dict[str, Callable[[], Any]], now: float) -> Dict[str, Any]:
        vitals = collect(sources)
        with self._lock:
            self._scans += 1
            defects = detect(vitals, list(self._history))
            disk = vitals.get("disk") if isinstance(vitals.get("disk"), dict) else {}
            self._history.append({"at": now, "inodes_used_pct": disk.get("inodes_used_pct"),
                                  "bytes_used_pct": disk.get("bytes_used_pct")})
            defects.sort(key=lambda i: (SEVERITY_ORDER.get(i["severity"], 9), i["id"]))
            report = {
                "generated_at": now,
                "scans": self._scans,
                "open_count": len(defects),
                "resolved_count": 0,
                "defects": defects,
                "vitals": {"disk": disk or None, "errors": vitals["errors"],
                           "tools_tracked": len(vitals.get("tool_stats") or {}),
                           "goals_tracked": len(vitals.get("goals") or {}),
                           "proposals_tracked": len(vitals.get("proposals") or [])},
                "history": list(self._history),
                "limits": "يقترح فقط: لا يكتب ولا ينفّذ ولا يعدّل شيفرة؛ القرار للمالك",
            }
            self._last = report
            return report

    def last_report(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._last


_MONITOR: Optional[SelfMonitor] = None


def get_monitor() -> SelfMonitor:
    global _MONITOR
    if _MONITOR is None:
        _MONITOR = SelfMonitor()
    return _MONITOR
