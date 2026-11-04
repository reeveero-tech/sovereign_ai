# -*- coding: utf-8 -*-
"""R-841 (4.12): المراقبة والتتبع — لا استدعاء بلا trace ولا trace بلا حلقة.

Span لكل خطوة (مدخلات بلا أسرار/مخرجات/زمن)، قرار أداة، قرار موافقة،
قرار إيقاف — والتكلفة والزمن الكليان والانحراف عن الخطة وأسبابه.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

try:
    from observability.redact import redact as _redact_text
    from runtime.atomic_json import atomic_write_json
except ImportError:  # TOLERATED: نمط الاستيراد المزدوج القائم
    from backend.observability.redact import redact as _redact_text
    from backend.runtime.atomic_json import atomic_write_json

# أنماط أسرار لا تدخل الأثر أبدًا (كناري: القيم الحرفية تُنقّى عند الإدخال)
_SECRET_KEY_RE = [
    "password", "secret", "token", "api_key", "apikey", "authorization",
    "credential", "private_key", "access_key", "refresh_token",
]


def scrub(value: Any) -> Any:
    """تنقية متكررة: أي مفتاح سرّي تُستبدل قيمته بـ*** — الأثر نظيف بالبنية."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            kl = str(k).lower()
            if any(s in kl for s in _SECRET_KEY_RE):
                out[str(k)] = "***"
            else:
                out[str(k)] = scrub(v)
        return out
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, str):
        # R-846: قيمة نصية تحمل رمزًا (ghp_/sbp_/Bearer…) تُنقّى ولو تحت مفتاح عادي
        value = _redact_text(value)
        if len(value) > 2000:
            return value[:2000] + "…"
    return value


class Tracer:
    """أثر حلقة واحدة — يُنشأ معها ويعيش معها ويفحصها التدقيق بعدها."""

    def __init__(self, loop_id: str):
        self.loop_id = loop_id
        self.trace_ref = f"trace:{loop_id[:8]}"
        self._spans: List[Dict[str, Any]] = []
        self._decisions: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._t0 = time.monotonic()
        self._offset_ms = 0.0  # R-846: زمن سابق لأثر مستعاد من القرص

    @classmethod
    def restore(cls, summary: Dict[str, Any]) -> "Tracer":
        """R-846: أثر مستعاد يكمل من حيث توقف — الامتدادات والقرارات والزمن محفوظة."""
        t = cls(str(summary["loop_id"]))
        t._spans = list(summary.get("spans") or [])
        t._decisions = list(summary.get("decisions") or [])
        t._offset_ms = float(summary.get("total_duration_ms") or 0.0)
        return t

    def span(self, step_id: str, inputs: Dict[str, Any],
             outputs: Dict[str, Any], duration_ms: float,
             status: str = "ok") -> Dict[str, Any]:
        span = {"span_id": str(uuid.uuid4()), "loop_id": self.loop_id,
                "step_id": step_id, "status": status,
                "inputs": scrub(inputs), "outputs": scrub(outputs),
                "duration_ms": round(duration_ms, 1),
                "ts": time.time()}
        with self._lock:
            self._spans.append(span)
        return span

    def decision(self, d: Dict[str, Any]) -> None:
        with self._lock:
            self._decisions.append(scrub(d))

    def stop_reason(self, reason: str) -> Dict[str, Any]:
        return self.decision({"decision_type": "stop", "chosen": reason,
                              "reasoning": reason, "step_id": "",
                              "rejected": [], "confidence": 1.0,
                              "trace_ref": self.trace_ref})

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            total_cost = sum(s.get("cost", 0) for s in self._spans
                             if isinstance(s.get("cost"), (int, float)))
            return {
                "loop_id": self.loop_id,
                "trace_ref": self.trace_ref,
                "spans": list(self._spans),
                "decisions": list(self._decisions),
                "total_duration_ms": round(self._offset_ms
                                           + (time.monotonic() - self._t0) * 1000, 1),
                "total_cost": round(total_cost, 6),
                "span_count": len(self._spans),
            }

    def full(self) -> Dict[str, Any]:
        return self.summary()


_LOOP_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class TraceStore:
    """R-846: آثار دائمة — ملف JSON ذري لكل حلقة تحت ``data_dir/traces``.

    الأثر كان يعيش في الذاكرة فقط فيضيع عند إعادة التشغيل ويتضخم بلا حد.
    الآن يُكتب عند كل نقطة نهاية/تعليق، ويُستعاد عند الحاجة، ويُقلَّم إلى
    ``max_files`` (الأقدم أولًا). المعرّف يُتحقق منه قبل بناء أي مسار.
    """

    def __init__(self, root: str, max_files: int = 1000):
        self.root = root
        self.max_files = max(10, int(max_files))
        os.makedirs(root, exist_ok=True)
        self._writes = 0

    def _path(self, loop_id: str) -> Optional[str]:
        if not _LOOP_ID_RE.match(str(loop_id)):
            return None
        return os.path.join(self.root, f"{loop_id}.json")

    def save(self, summary: Dict[str, Any]) -> bool:
        path = self._path(summary.get("loop_id", ""))
        if path is None:
            return False
        atomic_write_json(path, scrub(summary), ensure_ascii=False)
        self._writes += 1
        if self._writes % 50 == 1:
            self.prune()
        return True

    def load(self, loop_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(loop_id)
        if path is None or not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) and data.get("loop_id") == loop_id else None

    def count(self) -> int:
        return sum(1 for n in os.listdir(self.root) if n.endswith(".json"))

    def prune(self) -> int:
        files = [os.path.join(self.root, n) for n in os.listdir(self.root)
                 if n.endswith(".json")]
        excess = len(files) - self.max_files
        if excess <= 0:
            return 0
        files.sort(key=lambda p: os.path.getmtime(p))
        removed = 0
        for p in files[:excess]:
            try:
                os.remove(p)
                removed += 1
            except OSError:  # TOLERATED: سباق حذف — الملف أزيل سلفًا
                continue
        return removed
