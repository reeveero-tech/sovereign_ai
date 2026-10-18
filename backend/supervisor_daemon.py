#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/supervisor_daemon.py — الحارس المعزول (R-687 — المرحلة ٢ من META_SYSTEM)

أمر المالك 2026-10-18: «الحارس المعزول: عملية مستقلة (Subprocess daemon)
تقرأ الحالة من /health و /status وتكتب سجل مراقبة مستقل (append-only).
ممنوع استيراد الحارس مباشرة داخل app.py، لكي لا يتأثر التطبيق إذا مات
الحارس».

العقد التصميمي:
- عملية مستقلة كليًا: تُشغَّل بـ`python -m backend.supervisor_daemon` —
  لا يستوردها أي كود حي (حارس بنيوي يمنع ذلك)، ولا تستورد هي التطبيق:
  كل التواصل عبر HTTP فقط. موت أي طرف لا يمس الآخر.
- stdlib خالص: urllib للقراءة، json، signal للتوقف النظيف.
- صفر مسارات موت: لا exit/_exit إطلاقًا (حارس AST الدائم يمنعها) —
  التوقف بالإشارة (SIGTERM/SIGINT) يضبط علمًا فينتهي الحلقة ويعود main.
- سجل مراقبة append-only: سطر JSON لكل دورة {ts, health, status} —
  نجاح التطبيق يُقرأ، وفشله يُسجل كخطأ ويستمر الحارس (المراقب لا يموت
  مع المراقَب — الاتجاهان مقيسان بالاختبارات).
- فشل القراءة لا يوقف الحارس ولا يرفع استثناءً — يسجل الخطأ ويكمل.
"""

import argparse
import json
import os
import signal
import time
import urllib.error
import urllib.request
from pathlib import Path

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_MODULE_DIR)

_STOP = False  # يُضبط من معالج الإشارة — لا استدعاء إنهاء إطلاقًا


def _handle_stop(signum, frame):  # noqa: ARG001 — توقيع الإشارة القياسي
    """SIGTERM/SIGINT: طلب توقف نظيف — الحلقة تنتهي ويعود main طبيعيًا."""
    global _STOP
    _STOP = True


def _fetch_json(url: str, timeout: float):
    """قراءة JSON عبر HTTP — يعيد (البيانات أو None، خطأ نصي أو None)."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except Exception as exc:  # المراقبة لا تموت مع المراقَب — الخطأ يُسجل
        return None, f"{type(exc).__name__}: {exc}"


def _summarize_status(status: dict) -> dict:
    """/status كبير — يُختصر للسجل: الحالة + عدد المكونات + الطابع الزمني."""
    components = status.get("components")
    return {
        "status": status.get("status"),
        "version": status.get("version"),
        "components_count": len(components) if isinstance(components, dict) else None,
        "timestamp": status.get("timestamp"),
    }


def _append_log_line(log_path: Path, entry: dict) -> None:
    """إلحاق سطر واحد — فشل الكتابة لا يقتل الحارس (يُحاول في الدورة التالية)."""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:  # R-687: السجل لا يوقف المراقبة أبدًا — أثر الفشل غياب السطر فقط
        pass


def _default_log_path() -> Path:
    """سجل المراقبة في جذر البيانات (يُحترم SOVEREIGN_DATA_ROOT للعزل)."""
    data_root = os.getenv("SOVEREIGN_DATA_ROOT") or os.path.join(_REPO_ROOT, "data")
    return Path(data_root) / "supervisor" / "monitor_log.jsonl"


def run(url: str, interval: float, log_path: Path) -> int:
    """حلقة المراقبة — تعيد 0 عند التوقف النظيف بالإشارة."""
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    while not _STOP:
        started = time.time()
        health, health_err = _fetch_json(f"{url.rstrip('/')}/health", timeout=5)
        status, status_err = _fetch_json(f"{url.rstrip('/')}/status", timeout=5)
        entry = {
            "ts": time.time(),
            "target": url,
            "health": health if health is not None else {"error": health_err},
            "status": (
                _summarize_status(status) if status is not None
                else {"error": status_err}
            ),
        }
        _append_log_line(log_path, entry)
        # نوم متقطع يستجيب للإشارة بسرعة — لا نوم كتلي طويل
        elapsed = time.time() - started
        while not _STOP and time.time() - started < interval:
            time.sleep(min(0.1, max(0.01, interval)))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="الحارس المعزول — مراقبة مستقلة للتطبيق عبر /health و/status",
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000",
        help="عنوان التطبيق الأساسي (افتراضي: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--interval", type=float, default=2.0,
        help="ثوانٍ بين دورات المراقبة (افتراضي: 2.0)",
    )
    parser.add_argument(
        "--log", default=None,
        help="مسار سجل المراقبة append-only (افتراضي: <جذر البيانات>/supervisor/monitor_log.jsonl)",
    )
    args = parser.parse_args(argv)
    log_path = Path(args.log) if args.log else _default_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:  # R-687: الإنشاء يُحاول مجددًا عند الكتابة — الفشل لا يوقف المراقبة
        pass  # السجل لا يوقف المراقبة أبدًا
    return run(args.url, args.interval, log_path)


if __name__ == "__main__":
    main()
