"""R-745 (البند ٤.٥ — التحسين بموافقة): اقتراح → موافقة مالك → التزام ذري.

«لا تطوير ذاتي غير مقيّد بموافقة المالك» (حدود GOVERNANCE قائمة):
- هذه الوحدة تقترح فقط: لا تكتب ملفات، لا تشغّل أوامر، لا تلمس git ولا
  الشيفرة (حارس ثابت في tests/test_improvement_proposals.py).
- الاقتراح يُولَّد من العيوب المفتوحة (البند ٤.٣) بدليلها الحرفي، بمعرّف
  ثابت P-<sha256(defect_id)[:8]>، ولا يتكرر.
- ما يصطدم بقرار مالك موثق يُحجب بسببه (suppressed) لا يُقترح (المادة ٦).
- القرار للمالك وحده: عبر الأداة proposals.decide في السجل — أي عبر
  /tools/invoke بمفتاح المالك وبأثر tool_invoked موقّع (fail-closed R-635).
- التنفيذ ليس هنا: الموافَق عليه يُصدَّر ملف توصية (markdown) يُنفَّذ بالدورة
  الذرية المعتادة (المادة ٤)، ثم يُعلَّم implemented برقم الالتزام.
- آلة حالات: proposed → approved | rejected ؛ approved → implemented.
  المرفوض لا يُعاد اقتراحه. التاريخ إلحاقي (history) لا يُمحى.
- حالة في الذاكرة فقط — لا كتابة تحت data/ (المادة ٧)؛ الأثر الدائم هو
  حدث tool_invoked الموقّع لكل قرار.
"""

import hashlib
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

COMMIT_RE = re.compile(r"[0-9a-f]{7,40}")
DECISIONS = {"approved", "rejected", "implemented"}
TRANSITIONS = {
    "proposed": {"approved", "rejected"},
    "approved": {"implemented", "rejected"},
}

# قرارات مالك موثقة تحجب اقتراحات بعينها (المادة ٦: ما حُجب عمدًا يبقى محجوبًا)
OWNER_SUPPRESSIONS: Dict[str, str] = {
    "supervisor_heartbeat_missing":
        "قرار المالك ٤.٧ (الحارس كخدمة): مغلق — خارج النطاق "
        "(docs/OWNER_DECISIONS_PENDING.md) — لا يُقترح تشغيل الحارس",
}


def _proposal_id(defect_id: str) -> str:
    return "P-" + hashlib.sha256(defect_id.encode("utf-8")).hexdigest()[:8]


def _recommend(defect: Dict[str, Any]) -> Tuple[str, str]:
    """(kind, recommendation) — حتمية من معرّف العيب ودليله، بلا تخمين."""
    did = defect.get("id", "")
    ev = str(defect.get("evidence", ""))
    if "R-635" in ev:
        return ("owner_action",
                "إجراء مالك لا إصلاح كود: توليد/تدوير مفتاح توقيع نشط على البيئة "
                "(R-635). بدونه يرفض السجل السيادي كل كتابة (لا أثر = لا تنفيذ).")
    if did.startswith("component_unhealthy:"):
        comp = did.split(":", 1)[1]
        return ("code_fix",
                f"تشخيص المكوّن «{comp}» من دليل /health، وكتابة اختبار أحمر يعيد "
                "إنتاج العطل قبل أي إصلاح، ثم الإصلاح في دورة ذرية.")
    if did == "health_degraded_persistent":
        return ("investigation",
                "التدهور مستمر عبر دورات: مراجعة المكونات غير السليمة في التقرير "
                "نفسه أولًا؛ الإصلاح يتبع اقتراحات المكونات لا هذا البند وحده.")
    if did.startswith("scheduled_task_failed:"):
        task = did.split(":", 1)[1]
        return ("code_fix",
                f"إعادة إنتاج فشل المهمة «{task}» باختبار أحمر من last_error، ثم "
                "الإصلاح في دورة ذرية.")
    if did.startswith("benchmark_gap:"):
        return ("investigation",
                f"فجوة مقابل مرجع عام ({did.split(':', 1)[1]}): قياس أدق (تكرار + "
                "تحليل أداء) قبل أي تغيير؛ المرجع والرقم في الدليل وفي /benchmark/report.")
    if did == "supervisor_alerts":
        return ("investigation",
                "مراجعة التنبيهات النشطة في /supervisor/status وتصنيفها قبل أي تغيير.")
    return ("investigation", "عيب غير مصنف: تحقيق يدوي من الدليل قبل أي تغيير.")


ATOMIC_CHECKLIST = """## الدورة الذرية المطلوبة للتنفيذ (المادة ٤)
- [ ] اختبار يفشل أولًا (RED) ويُحفظ دليله في forensics/
- [ ] الإصلاح حتى يخضرّ الاختبار (GREEN) — لا إضعاف لاختبار قائم
- [ ] تحديث docs/PROJECT_STATE.md + docs/CHANGELOG.md + بند الخارطة في نفس الالتزام
- [ ] أي سطر محذوف: # DELETION-JUSTIFIED + مدخل forensics/DELETED_LINES_AUDIT.md في نفس الالتزام
- [ ] verify.sh --full بتطابق ثلاثي (محلي = CI = استنساخ نظيف) قبل إعلان الإنجاز
- [ ] بعد الدفع: proposals.decide بـ decision=implemented و commit=<SHA> (بمفتاح المالك)
"""


class ProposalBook:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: Dict[str, Dict[str, Any]] = {}

    def ingest(self, report: Dict[str, Any], now: float) -> List[Dict[str, Any]]:
        """يحوّل العيوب المفتوحة إلى اقتراحات؛ يعيد الاقتراحات الجديدة فقط."""
        created: List[Dict[str, Any]] = []
        open_ids = set()
        with self._lock:
            for d in (report or {}).get("defects", []):
                if d.get("status") != "open":
                    continue
                did = d.get("id", "")
                open_ids.add(did)
                pid = _proposal_id(did)
                item = self._items.get(pid)
                if item is not None:
                    item["last_seen"] = now
                    item["evidence"] = str(d.get("evidence", ""))
                    item["defect_open"] = True
                    continue
                kind, rec = _recommend(d)
                suppressed = OWNER_SUPPRESSIONS.get(did)
                status = "suppressed" if suppressed else "proposed"
                item = {
                    "id": pid, "defect_id": did, "kind": kind,
                    "severity": d.get("severity"), "title": d.get("title"),
                    "evidence": str(d.get("evidence", "")),
                    "recommendation": rec, "status": status,
                    "suppressed_reason": suppressed,
                    "created_at": now, "last_seen": now, "defect_open": True,
                    "decided_at": None, "note": None, "commit": None,
                    "history": [{"to": status, "at": now, "by": "system"}],
                }
                self._items[pid] = item
                created.append(dict(item))
            for item in self._items.values():
                if item["defect_id"] not in open_ids:
                    item["defect_open"] = False
        return created

    def decide(self, proposal_id: str, decision: str, note: Optional[str] = None,
               commit: Optional[str] = None, now: float = 0.0) -> Dict[str, Any]:
        """تحضير + تطبيق مباشر (للاستخدام الداخلي والاختبارات)."""
        return self.apply_prepared(self.prepare(proposal_id, decision, note, commit, now))

    def prepare(self, proposal_id: str, decision: str, note: Optional[str] = None,
                commit: Optional[str] = None, now: float = 0.0) -> Dict[str, Any]:
        """يتحقق ويعيد الاقتراح كما سيصير — بلا أي تغيير في الحالة (R-745:
        المرحلة الأولى؛ التطبيق بعد نجاح الأثر الموقّع فقط)."""
        if decision not in DECISIONS:
            raise ValueError(f"قرار غير معروف: {decision} — المسموح {sorted(DECISIONS)}")
        with self._lock:
            item = self._items.get(proposal_id)
            if item is None:
                raise KeyError(proposal_id)
            allowed = TRANSITIONS.get(item["status"], set())
            if decision not in allowed:
                raise ValueError(
                    f"انتقال مرفوض: {item['status']} → {decision} "
                    f"(المسموح من {item['status']}: {sorted(allowed) or 'لا شيء'})")
            if decision == "implemented":
                if not commit or not COMMIT_RE.fullmatch(commit):
                    raise ValueError("implemented يتطلب commit=<SHA> صالحًا (7-40 hex)")
            preview = self._copy(item)
            preview["from_status"] = item["status"]
            if decision == "implemented":
                preview["commit"] = commit
            preview["status"] = decision
            preview["decided_at"] = now
            preview["note"] = (note or None) and str(note)[:500]
            preview["history"].append({"to": decision, "at": now, "by": "owner"})
            return preview

    def apply_prepared(self, preview: Dict[str, Any]) -> Dict[str, Any]:
        """المرحلة الثانية: يطبّق المحضّر إن لم تتغير الحالة منذ التحضير."""
        with self._lock:
            item = self._items.get(preview["id"])
            if item is None:
                raise KeyError(preview["id"])
            if item["status"] != preview["from_status"]:
                raise ValueError(
                    f"تغيّرت الحالة منذ التحضير ({preview['from_status']} → {item['status']})")
            for k in ("status", "decided_at", "note", "commit"):
                item[k] = preview[k]
            item["history"] = [dict(h) for h in preview["history"]]
            return self._copy(item)

    @staticmethod
    def _copy(item: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(item)
        out["history"] = [dict(h) for h in item["history"]]
        return out

    def get(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._items.get(proposal_id)
            return self._copy(item) if item else None

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._copy(i) for i in sorted(
                self._items.values(), key=lambda i: (i["created_at"], i["id"]))]

    def render_markdown(self, proposal_id: str) -> str:
        p = self.get(proposal_id)
        if p is None:
            raise KeyError(proposal_id)
        lines = [
            f"# {p['id']} — اقتراح تحسين ({p['kind']})",
            "",
            f"- **الحالة:** {p['status']}",
            f"- **العيب المصدر:** `{p['defect_id']}` (الشدة: {p['severity']}؛ "
            f"ما زال مفتوحًا: {'نعم' if p['defect_open'] else 'لا'})",
            f"- **الدليل:** `{p['evidence']}`",
            f"- **التوصية:** {p['recommendation']}",
        ]
        if p["suppressed_reason"]:
            lines.append(f"- **محجوب:** {p['suppressed_reason']}")
        if p["note"]:
            lines.append(f"- **ملاحظة المالك:** {p['note']}")
        if p["commit"]:
            lines.append(f"- **التزام التنفيذ:** `{p['commit']}`")
        lines += ["", "## التاريخ"]
        lines += [f"- {h['to']} — {h['by']} — {h['at']}" for h in p["history"]]
        lines += ["", "هذا ملف توصية فقط: النظام لا ينفّذه بنفسه (البند ٤.٥).", "",
                  ATOMIC_CHECKLIST]
        return "\n".join(lines)


_BOOK: Optional[ProposalBook] = None


def get_book() -> ProposalBook:
    global _BOOK
    if _BOOK is None:
        _BOOK = ProposalBook()
    return _BOOK
