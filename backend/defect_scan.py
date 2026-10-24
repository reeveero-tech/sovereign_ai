"""R-743 (البند ٤.٣ — اكتشاف العيوب ذاتيًا): دورة بجدول تنتج تقرير عيوب.

مبادئ:
- لا تخمين: كل عيب مشتق من مصدر تشغيلي حقيقي (لقطة /health، حالة المجدول،
  نبض الحارس) ومعه دليله الحرفي المختصر. حالة سليمة = صفر عيوب.
- قائمة عمل لا تنسى: العيب المتكرر لا يتضاعف (first_seen/last_seen/
  occurrences)، والعيب الزائل يُعلَّم resolved مع وقته — لا يُحذف (المادة ٣).
- رصد التاريخ: نافذة محدودة من لقطات الصحة؛ التدهور في PERSISTENT_AFTER
  دورات متتالية يُرفع إلى عيب مستمر.
- ما حُجب عمدًا ليس عيبًا (المادة ٦): الحواس المعطلة افتراضيًا والمجدول
  المعطل قرارات مالك — لا تُدرج.
- لا سر: الأدلة مقتطعة (200 حرف) ومن مصادر معروضة أصلًا في نقاط عامة.
- في الذاكرة فقط: لا كتابة تحت data/ (المادة ٧)؛ الأثر الدائم هو حدث
  tool_invoked الموقّع عند كل تشغيل عبر السجل.
"""

import threading
from collections import deque
from typing import Any, Dict, List, Optional

PERSISTENT_AFTER = 3
HISTORY_SIZE = 20
EVIDENCE_MAX = 200
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _clip(value: Any) -> str:
    return str(value)[:EVIDENCE_MAX]


def detect(health: Optional[Dict[str, Any]],
           scheduler: Optional[Dict[str, Any]],
           heartbeat: Optional[Dict[str, Any]],
           history: List[str]) -> List[Dict[str, str]]:
    """المصادر الحقيقية → قائمة اكتشافات (id/severity/area/title/evidence)."""
    found: List[Dict[str, str]] = []

    if not health:
        found.append({"id": "health_unavailable", "severity": "high",
                      "area": "health", "title": "لقطة الصحة غير متاحة",
                      "evidence": "health=None"})
    else:
        for name, comp in sorted((health.get("components") or {}).items()):
            status = (comp or {}).get("status")
            if status != "healthy":
                found.append({
                    "id": f"component_unhealthy:{name}", "severity": "high",
                    "area": "health", "title": f"مكوّن غير سليم: {name}",
                    "evidence": _clip(f"status={status} error={(comp or {}).get('error')}")})
        if history and len(history) >= PERSISTENT_AFTER and all(
                s != "healthy" for s in history[-PERSISTENT_AFTER:]):
            found.append({
                "id": "health_degraded_persistent", "severity": "high",
                "area": "health",
                "title": f"تدهور مستمر في {PERSISTENT_AFTER} دورات متتالية",
                "evidence": _clip(f"history={history[-PERSISTENT_AFTER:]}")})

    for task in (scheduler or {}).get("tasks") or []:
        if task.get("last_ok") is False:
            found.append({
                "id": f"scheduled_task_failed:{task.get('name')}",
                "severity": "medium", "area": "scheduler",
                "title": f"فشل آخر تشغيل للمهمة {task.get('name')}",
                "evidence": _clip(task.get("last_error") or "last_ok=False")})

    if heartbeat is None:
        found.append({
            "id": "supervisor_heartbeat_missing", "severity": "low",
            "area": "supervisor", "title": "نبض الحارس غير متاح أو قديم",
            "evidence": "data/supervisor/status.json غائب أو تالف أو منتهي المهلة"})
    elif int(heartbeat.get("active_alerts") or 0) > 0:
        found.append({
            "id": "supervisor_alerts", "severity": "medium",
            "area": "supervisor", "title": "تنبيهات نشطة لدى الحارس",
            "evidence": f"active_alerts={heartbeat.get('active_alerts')}"})

    return found


class DefectWorklist:
    """قائمة عمل العيوب — حالة في الذاكرة محمية بقفل."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: Dict[str, Dict[str, Any]] = {}
        self._history: deque = deque(maxlen=HISTORY_SIZE)
        self._scans = 0
        self._last: Optional[Dict[str, Any]] = None

    def scan(self, health, scheduler, heartbeat, now: float) -> Dict[str, Any]:
        with self._lock:
            self._scans += 1
            if health:
                self._history.append(health.get("status") or "unknown")
            history = list(self._history)
            current = {d["id"]: d for d in detect(health, scheduler, heartbeat, history)}

            for did, d in current.items():
                item = self._items.get(did)
                if item is None or item["status"] == "resolved":
                    reopened = item is not None
                    item = {**d, "status": "open", "first_seen": now,
                            "last_seen": now, "occurrences": 0,
                            "resolved_at": None, "reopened": reopened}
                    self._items[did] = item
                item.update(evidence=d["evidence"], last_seen=now)
                item["occurrences"] += 1

            for did, item in self._items.items():
                if item["status"] == "open" and did not in current:
                    item["status"] = "resolved"
                    item["resolved_at"] = now

            defects = sorted(
                (dict(i) for i in self._items.values()),
                key=lambda i: (i["status"] != "open",
                               SEVERITY_ORDER.get(i["severity"], 9), i["id"]))
            report = {
                "generated_at": now,
                "scans": self._scans,
                "open_count": sum(1 for i in defects if i["status"] == "open"),
                "resolved_count": sum(1 for i in defects if i["status"] == "resolved"),
                "defects": defects,
                "health_history": history,
                "limits": "يرصد الحالة التشغيلية فقط؛ حزمة الاختبارات والحراس تعمل "
                          "في CI لكل التزام لا داخل عملية الإنتاج",
            }
            self._last = report
            return report

    def last_report(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._last


_WORKLIST: Optional[DefectWorklist] = None


def get_worklist() -> DefectWorklist:
    global _WORKLIST
    if _WORKLIST is None:
        _WORKLIST = DefectWorklist()
    return _WORKLIST
