"""R-734 (البند ٢.٧ — بأمر المالك): قياس موارد النظام من نظام التشغيل مباشرة.

مبادئ (لا وهم):
- كل قيمة مقاسة فعليًا مع مصدرها، أو null مع سبب صريح — لا تقدير ولا افتراض.
- الذاكرة المقيمة من /proc/self/status (Linux — بيئة الإنتاج)، وإلا الحد الأقصى
  من resource.getrusage معلنًا أنه «ذروة» لا قيمة لحظية.
- المعالج: نسبة استهلاك العملية بين عينتين متتاليتين (time.process_time /
  الزمن الحقيقي). أول قراءة بلا عينة سابقة = null صريح.
- القرص: shutil.disk_usage لمجلد البيانات، بتسمية نسبية — لا مسار مطلق (المادة ٩).
- مكتبة قياسية فقط — لا اعتماد جديد (psutil غير مثبت).
"""

import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

_lock = threading.Lock()
_last: Optional[Dict[str, float]] = None


def reset_cpu_baseline() -> None:
    global _last
    with _lock:
        _last = None


def _rss() -> Dict[str, Any]:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return {"rss_mb": round(int(line.split()[1]) / 1024.0, 1),
                        "rss_source": "/proc/self/status"}
    except OSError:  # R-734: لا /proc (منصة غير Linux) — ننتقل للمصدر البديل أدناه معلنًا
        pass
    try:
        import resource
        peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {"rss_mb": round(peak_kb / 1024.0, 1),
                "rss_source": "getrusage.ru_maxrss (ذروة لا قيمة لحظية)"}
    except Exception as exc:  # R-734: منصة بلا /proc ولا resource — null معلن لا رقم
        return {"rss_mb": None, "rss_source": f"غير متاح: {type(exc).__name__}"}


def _cpu() -> Dict[str, Any]:
    global _last
    now_wall, now_proc = time.monotonic(), time.process_time()
    with _lock:
        prev, _last = _last, {"wall": now_wall, "proc": now_proc}
    if prev is None or now_wall - prev["wall"] <= 0:
        return {"cpu_percent": None,
                "cpu_note": "يحتاج عينتين متتاليتين — هذه أول قراءة"}
    pct = (now_proc - prev["proc"]) / (now_wall - prev["wall"]) * 100.0
    return {"cpu_percent": round(max(pct, 0.0), 2),
            "cpu_note": f"استهلاك العملية خلال آخر {round(now_wall - prev['wall'], 1)} ثانية"}


def _disk(path: Path, label: str) -> Dict[str, Any]:
    try:
        u = shutil.disk_usage(str(path))
        return {"label": label, "total_gb": round(u.total / 1e9, 2),
                "free_gb": round(u.free / 1e9, 2),
                "used_percent": round((u.used / u.total) * 100.0, 1) if u.total else None}
    except OSError as exc:  # R-734: المجلد غير متاح — null معلن
        return {"label": label, "total_gb": None, "free_gb": None, "used_percent": None,
                "error": type(exc).__name__}


def snapshot(disk_path: Optional[Path] = None, disk_label: str = "data") -> Dict[str, Any]:
    try:
        load_1m: Optional[float] = round(os.getloadavg()[0], 2)
    except (OSError, AttributeError):  # R-734: منصة بلا getloadavg — null معلن
        load_1m = None
    process = {**_rss(), **_cpu(), "threads": threading.active_count()}
    return {
        "process": process,
        "host": {"cpu_count": os.cpu_count() or 1, "load_avg_1m": load_1m},
        "disk": _disk(disk_path or Path("."), disk_label),
        "timestamp": time.time(),
    }
