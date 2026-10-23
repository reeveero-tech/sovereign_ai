"""R-729 (البند ٣.١ — بأمر المالك): سجل الأدوات الحقيقي.

استبدال runtime-capability-registry.js الزخرفي (يسجل «قدرات» وهمية لا
يستهلكها أحد) بسجل backend حقيقي: كل أداة معلنة باسم/وصف/مدخلات/مخرجات/
صلاحية، وكل استدعاء يترك أثرًا في السجل السيادي (حدث TOOL_INVOKED — بصمة
النتيجة لا النتيجة الكاملة، ولا سر في المخرجات أبدًا — المادة ٩).

مبادئ:
- لا وهم: الأدوات المسجلة قدرات موجودة فعلًا في النظام — التسجيل في app.py
  يمرر دوال حقيقية (نفس منطق النقاط الحية)، لا نصوص مزروعة.
- لا أثر = لا تنفيذ (fail-closed بنمط R-635): إن تعذر توقيع السجل السيادي
  يُرفض الاستدعاء بصوت عالٍ، لا تنفيذ صامت بلا دليل.
- العزل: الأداة تنفذ معالجها داخل محاولة — فشل الأداة يُوثق في الأثر
  (ok=False + error) ولا يكسر السجل.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class UnknownToolError(KeyError):
    """أداة غير مسجلة في السجل — لا تنفيذ صامت لما ليس معلنًا."""


@dataclass
class ToolSpec:
    """إعلان أداة — البيانات الوصفية وحدها تظهر في /tools/list (لا المعالج)."""
    name: str
    description: str
    inputs: Dict[str, str]
    outputs: str
    handler: Callable[[], Any]
    permission: str = "owner"  # استدعاؤها يتطلب مفتاح API (نمط /sovereign/command)


class ToolRegistry:
    """سجل الأدوات — singleton عبر get_registry()."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"أداة مسجلة مرتين: {spec.name}")
        self._tools[spec.name] = spec
        logger.info("R-729: أداة مسجلة في السجل — %s", spec.name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """البيانات الوصفية فقط — لا معالج ولا سر (المادة ٩)."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "inputs": s.inputs,
                "outputs": s.outputs,
                "permission": s.permission,
            }
            for s in self._tools.values()
        ]

    def invoke(self, name: str, caller: str = "owner") -> Dict[str, Any]:
        """تنفيذ أداة مسجلة مع أثر سيادي إلزامي.

        يرفع UnknownToolError إن لم تكن مسجلة، وRuntimeError (fail-closed
        بنمط R-635) إن تعذر توقيع السجل — لا أثر = لا تنفيذ.
        """
        spec = self._tools.get(name)
        if spec is None:
            raise UnknownToolError(name)
        start = time.perf_counter()
        ok, result, error = True, None, None
        try:
            result = spec.handler()
        except Exception as exc:  # فشل الأداة يوثق ولا يكسر الأثر
            ok, result, error = False, None, f"{type(exc).__name__}: {exc}"[:200]
            logger.exception("R-729: فشل أداة %s — يوثق في الأثر", name)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        fingerprint = self._fingerprint(result if ok else error)

        payload: Dict[str, Any] = {
            "tool": name,
            "caller": caller,
            "ok": ok,
            "duration_ms": duration_ms,
            "result_fingerprint": fingerprint,
        }
        if error is not None:
            payload["error"] = error

        # الأثر السيادي — fail-closed: تعذر التوقيع يرفع RuntimeError
        # (نفس حارس R-635 قبل أي حفظ دائم). لا سر في الحدث أبدًا.
        from memory.core import get_core
        get_core().append_event("tool_invoked", payload, user=caller)

        return {
            "ok": ok,
            "tool": name,
            "result": result,
            "error": error,
            "trace": {
                "ledger_event": "tool_invoked",
                "result_fingerprint": fingerprint,
                "duration_ms": duration_ms,
            },
        }

    @staticmethod
    def _fingerprint(value: Any) -> str:
        """بصمة SHA-256 (16 حرفًا) للنتيجة/الخطأ — الدليل بلا تسريب محتوى."""
        blob = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


_REGISTRY: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ToolRegistry()
    return _REGISTRY
