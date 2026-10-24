"""R-744 (البند ٤.٢ — سجل التطور): كل دورة تطور ذاتي تترك مدخلًا إلحاقيًا
قابلًا للتدقيق في جدول disk_log الإلحاقي (R-719 — namespace=evolution).

المدخل يجيب: ماذا اكتشف (discovered) / ماذا زال (resolved) / أين كانت
وأين صارت (open_before → open_after) / بأي دليل (report_fingerprint — بصمة
ToolRegistry نفسها، فتطابق result_fingerprint في حدث tool_invoked الموقّع).
وماذا غيّر: النظام لا يعدّل نفسه اليوم — changed=[] صادقًا لا وعدًا.

مبادئ:
- مدخل لكل دورة، حتى بلا تغيير (لا دورة صامتة).
- سلسلة تجزئة في العملية (prev_hash → entry_hash): verify() تكشف العبث.
  أول مدخل بعد كل إقلاع segment_start=True (السلسلة لا تُستأنف عبر إعادة
  التشغيل — حدّ معلن؛ الترتيب الدائم هو id الإلحاقي في disk_log).
- Supabase مفعّل → POST إلحاقي فقط (لا PATCH/DELETE)؛ معطل أو بعيد →
  durable=False معلن (لا ادعاء دوام) والدورة لا تنهار (best-effort نمط R-719).
- لا سر في المدخل: معرّفات عيوب وأعداد وبصمات فقط.
"""

import hashlib
import json
import threading
from collections import deque
from typing import Any, Callable, Dict, List, Optional

NAMESPACE = "evolution"
BUFFER_SIZE = 200


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def _open_ids(report: Dict[str, Any]) -> set:
    return {d["id"] for d in report.get("defects", []) if d.get("status") == "open"}


def _default_disk():
    try:
        from sovereign.cloud_disk import get_cloud_disk
    except ImportError:  # TOLERATED: مسار الاستيراد من جذر المستودع (نمط /disk/status)
        from backend.sovereign.cloud_disk import get_cloud_disk
    return get_cloud_disk()


def _fingerprint(value: Any) -> str:
    from tool_registry import ToolRegistry
    return ToolRegistry._fingerprint(value)


class EvolutionLedger:
    def __init__(self, disk_factory: Optional[Callable[[], Any]] = None) -> None:
        self._disk_factory = disk_factory or _default_disk
        self._lock = threading.Lock()
        self._entries: deque = deque(maxlen=BUFFER_SIZE)
        self._prev_hash: Optional[str] = None
        self._prev_open: Optional[set] = None
        self._seq = 0

    @staticmethod
    def _hash_entry(entry: Dict[str, Any]) -> str:
        body = {k: v for k, v in entry.items()
                if k not in ("entry_hash", "durable", "cloud_error")}
        return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()

    def record_cycle(self, cycle: str, report: Dict[str, Any], now: float) -> Dict[str, Any]:
        with self._lock:
            current = _open_ids(report)
            before = self._prev_open
            self._seq += 1
            entry = {
                "seq": self._seq,
                "at": now,
                "cycle": cycle,
                "segment_start": before is None,
                "discovered": sorted(current - (before or set())) if before is not None
                else sorted(current),
                "resolved": sorted((before or set()) - current),
                "open_before": len(before) if before is not None else None,
                "open_after": len(current),
                "changed": [],
                "report_fingerprint": _fingerprint(report),
                "prev_hash": self._prev_hash,
            }
            entry["entry_hash"] = self._hash_entry(entry)

            durable, cloud_error = False, None
            disk = None
            try:
                disk = self._disk_factory()
            except Exception as exc:  # TOLERATED: تعذر بناء العميل = غير دائم معلن
                cloud_error = f"{type(exc).__name__}: {exc}"[:200]
            if disk is not None:
                try:
                    durable = bool(disk.append_log(NAMESPACE, dict(entry)))
                    if not durable:
                        cloud_error = "disk_log رفض الإلحاق (انظر السجلات)"
                except Exception as exc:  # TOLERATED: القرص بعيد — best-effort (R-719)
                    cloud_error = f"{type(exc).__name__}: {exc}"[:200]
            entry["durable"] = durable
            entry["cloud_error"] = cloud_error

            self._entries.append(entry)
            self._prev_hash = entry["entry_hash"]
            self._prev_open = current
            return dict(entry)

    def entries(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(e) for e in self._entries]

    def verify(self) -> Dict[str, Any]:
        """تحقق السلسلة في الذاكرة: كل entry_hash يطابق محتواه، وكل prev_hash
        يطابق سابقه (ما لم يكن أول مدخل في المخزن المؤقت)."""
        with self._lock:
            items = list(self._entries)
        prev = None
        for i, e in enumerate(items):
            if self._hash_entry(e) != e.get("entry_hash"):
                return {"ok": False, "broken_at": i, "reason": "entry_hash لا يطابق المحتوى"}
            if i > 0 and e.get("prev_hash") != prev:
                return {"ok": False, "broken_at": i, "reason": "prev_hash لا يطابق السابق"}
            prev = e.get("entry_hash")
        return {"ok": True, "checked": len(items)}

    def status(self) -> Dict[str, Any]:
        try:
            enabled = self._disk_factory() is not None
        except Exception:  # TOLERATED: تعذر بناء العميل = غير مفعّل معلن
            enabled = False
        out = {"namespace": NAMESPACE, "durable": enabled, "buffered": len(self._entries)}
        if not enabled:
            out["reason"] = ("Supabase غير مفعّل (SUPABASE_URL + SUPABASE_SECRET_KEY — "
                             "البند ٤.١ بيد المالك): المداخل في الذاكرة فقط وتضيع عند "
                             "إعادة التشغيل؛ الأثر الدائم هو حدث tool_invoked الموقّع")
        return out


_LEDGER: Optional[EvolutionLedger] = None


def get_ledger() -> EvolutionLedger:
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = EvolutionLedger()
    return _LEDGER
