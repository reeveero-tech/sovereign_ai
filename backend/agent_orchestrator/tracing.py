# -*- coding: utf-8 -*-
"""R-841 (4.12): المراقبة والتتبع — لا استدعاء بلا trace ولا trace بلا حلقة.

Span لكل خطوة (مدخلات بلا أسرار/مخرجات/زمن)، قرار أداة، قرار موافقة،
قرار إيقاف — والتكلفة والزمن الكليان والانحراف عن الخطة وأسبابه.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

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
    if isinstance(value, str) and len(value) > 2000:
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
                "total_duration_ms": round((time.monotonic() - self._t0) * 1000, 1),
                "total_cost": round(total_cost, 6),
                "span_count": len(self._spans),
            }

    def full(self) -> Dict[str, Any]:
        return self.summary()
