"""R-829: تحميل المكتبات المسحوبة كاملة في third_party/ — من النسخة المحفوظة في المستودع نفسه.

الإنتاج يثبّت الحزم من مساراتها المحلية (requirements.txt: ./third_party/<owner>__<repo>)، فيكون
الكود العامل هو الكود المسحوب حرفيًا. وحيث لا يكون التثبيت متاحًا (rank_bm25 يستخرج إصداره من git
فلا يُبنى خارج مستودعه) يُضاف مجلد النسخة إلى sys.path. أي فشل استيراد يُسجَّل بسببه ويُعلن في
الحالة — لا نجاح صامت ولا بديل مختلق.
"""

import importlib
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("sovereign.search_agents")

ROOT = Path(__file__).resolve().parent.parent.parent / "third_party"

# الوحدة ← مجلد النسخة المسحوبة (الجذر الذي يحوي الحزمة/الملف)
_PATHS = {
    "rank_bm25": "dorianbrown__rank_bm25",
    "bm25s": "xhluca__bm25s",
    "ddgs": "deedy5__ddgs",
    "trafilatura": "adbar__trafilatura",
    "whoosh": "Sygil-Dev__whoosh-reloaded/src",
}

_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}
_ERRORS: Dict[str, str] = {}


def vendor_dir(module: str) -> Path:
    return ROOT / _PATHS[module]


def load(module: str) -> Optional[Any]:
    """الوحدة المسحوبة أو None مع سبب مسجّل في errors()."""
    with _LOCK:
        if module in _CACHE:
            return _CACHE[module]
        mod = None
        try:
            mod = importlib.import_module(module)
        except ImportError as exc:  # غير مثبتة ⇒ من النسخة المسحوبة مباشرة
            path = str(vendor_dir(module))
            if path not in sys.path:
                sys.path.append(path)
            try:
                mod = importlib.import_module(module)
            except Exception as exc2:  # TOLERATED: سبب الفشل يُسجَّل ويُعلن في الحالة
                _ERRORS[module] = f"{type(exc2).__name__}: {str(exc2)[:200]} (قبلها: {str(exc)[:120]})"
                logger.warning("R-829: تعذّر تحميل %s المسحوبة: %s", module, _ERRORS[module])
        except Exception as exc:  # TOLERATED: خطأ أثناء استيراد حزمة مثبتة — يُسجَّل ويُعلن
            _ERRORS[module] = f"{type(exc).__name__}: {str(exc)[:200]}"
            logger.warning("R-829: تعذّر تحميل %s: %s", module, _ERRORS[module])
        _CACHE[module] = mod
        return mod


def origin(module: str) -> Optional[str]:
    """مسار الملف الذي حُمّلت منه الوحدة — دليل على أنها النسخة المسحوبة."""
    mod = load(module)
    return getattr(mod, "__file__", None) if mod else None


def errors() -> Dict[str, str]:
    return dict(_ERRORS)


def status() -> Dict[str, Any]:
    out = {}
    for m in _PATHS:
        mod = load(m)
        out[m] = {"loaded": mod is not None, "file": origin(m), "error": _ERRORS.get(m),
                  "version": getattr(mod, "__version__", None) if mod else None}
    return out
