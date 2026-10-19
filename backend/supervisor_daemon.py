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

from backend import awareness

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


def _append_log_line(log_path: Path, entry: dict) -> bool:
    """إلحاق سطر واحد — يعيد True عند النجاح وFalse عند الفشل (فشل الكتابة
    لا يقتل الحارس — يُحاول في الدورة التالية). R-694: مرجعية الوعي لا
    تُحدَّث إلا بعد True — التغيير لا يختفي دون سجل يوثقه."""
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except OSError:  # R-687: السجل لا يوقف المراقبة أبدًا — أثر الفشل غياب السطر فقط
        return False


def _default_map_store() -> Path:
    """مخزن خريطة الوعي في جذر البيانات (يُحترم SOVEREIGN_DATA_ROOT)."""
    data_root = os.getenv("SOVEREIGN_DATA_ROOT") or os.path.join(_REPO_ROOT, "data")
    return awareness.awareness_map_path(data_root)


def _awareness_check(
    repo_root: Path, map_store: Path, log_path: Path
) -> "tuple[dict, dict | None]":
    """فحص وعي واحد — الحارس يقرأ الخريطة (لا التطبيق — أمر المالك).

    يعيد (حادثة الوعي التي تُرفق بسطر الدورة، الخريطة الجديدة للمرجعية إن
    وجب تحديثها وإلا None). عقد سطر الدورة (R-687) محفوظ: كل سطر يحمل
    ts/target/health/status — والوعي مفتاح إضافي عند الحدث فقط. الترتيب
    الإلزامي (اعتراض المراجع — تخطيط R-694): الحارس يُلحق السطر أولًا ثم
    يحفظ المرجعية (في run) — فشل التسجيل يُبقي المرجعية السابقة وإعادة
    المحاولة في الفحص التالي: التغيير لا يختفي دون سجل يوثقه. المرجعية
    التالفة/غير المقروءة ليست «أول تشغيل» صامتًا: خطأ يُسجل ولا تُستبدل."""
    try:
        # R-694 (اعتراض المراجع ج2): مخرجات الحارس مستثناة بمسارَي الملفين
        # نفسيهما (المخزن والسجل) — لا أبويهما: استثناء الأب واسع يسقط
        # جيرة، والحارس يكتب سجله كل دورة فيُرصد عبثًا ذاتيًا إن لم يُستثنَ
        current = awareness.build_project_map(
            repo_root, exclude_paths=[map_store, log_path]
        )
    except OSError as exc:
        return {"event": "map_build_failed", "error": str(exc)}, None
    fingerprint = awareness.overall_fingerprint(current)
    if not map_store.exists():
        # أول تشغيل: تأسيس المرجعية — يُسجل أولًا (السطر) ثم يُحفظ
        return (
            {
                "event": "baseline_created",
                "fingerprint": fingerprint, "files": len(current),
            },
            current,
        )
    try:
        previous = awareness.load_map(map_store)
    except (OSError, ValueError) as exc:
        # تالفة/غير مقروءة — لا استبدال صامت: الخطأ يُسجل والمرجعية تبقى
        return {"event": "baseline_unreadable", "error": str(exc)}, None
    changes = awareness.diff_maps(previous, current)
    if not any(changes.values()):
        return {}, None  # لا تغيير — لا حادثة (الحوادث فقط تُسجل)
    return (
        {
            "event": "changes_detected",
            "previous_fingerprint": awareness.overall_fingerprint(previous),
            "current_fingerprint": fingerprint,
            "changes": changes,
            "files": len(current),
        },
        current,
    )


def run(
    url: str, interval: float, log_path: Path,
    map_interval: float = 60.0,
    repo_root: Path | None = None,
    map_store: Path | None = None,
) -> int:
    """حلقة المراقبة — تعيد 0 عند التوقف النظيف بالإشارة.

    R-694 (المرحلة ٣): فحص خريطة الوعي أول الإقلاع ثم عندما يحين موعده
    بساعة رتيبة (map_interval ثوانٍ — قرار تصميمي لا ادعاء أداء). الحارس
    يقرأ الخريطة — لا التطبيق (أمر المالك: لا ربط مباشر بـ app.py)."""
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    root = Path(repo_root) if repo_root is not None else Path(_REPO_ROOT)
    store = Path(map_store) if map_store is not None else _default_map_store()
    next_map_check = 0.0  # أول فحص فور الإقلاع
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
        if time.monotonic() >= next_map_check:
            try:
                # R-694: حادثة الوعي تُرفق بسطر الدورة نفسه (عقد R-687 قائم)
                awareness_event, new_baseline = _awareness_check(
                    root, store, log_path
                )
                if awareness_event:
                    entry["awareness"] = awareness_event
            except Exception as exc:  # الوعي لا يقتل الحارس أبدًا — يُسجل ويتابع
                entry["awareness"] = {"event": "check_failed", "error": str(exc)}
                new_baseline = None
            next_map_check = time.monotonic() + max(map_interval, 0.1)
        else:
            new_baseline = None
        # R-694: الترتيب الإلزامي — إلحاق ناجح أولًا ثم حفظ المرجعية:
        # فشل السجل يُبقي المرجعية السابقة (إعادة المحاولة — لا يضيع الأثر)
        if _append_log_line(log_path, entry) and new_baseline is not None:
            try:
                awareness.save_map(new_baseline, store)
            except OSError:  # R-694: المحاولة تُعاد لاحقًا — لا يقتل الحارس
                pass
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
    parser.add_argument(
        "--map-interval", type=float, default=60.0,
        help="ثوانٍ بين فحوص خريطة الوعي (افتراضي: 60.0 — فحص أول فور الإقلاع)",
    )
    parser.add_argument(
        "--awareness-root", default=None,
        help="جذر الشجرة الحية للخريطة (افتراضي: جذر المستودع)",
    )
    parser.add_argument(
        "--map-store", default=None,
        help="مخزن الخريطة المرجعية (افتراضي: <جذر البيانات>/awareness/project_map.json)",
    )
    args = parser.parse_args(argv)
    log_path = Path(args.log) if args.log else _default_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:  # R-687: الإنشاء يُحاول مجددًا عند الكتابة — الفشل لا يوقف المراقبة
        pass  # السجل لا يوقف المراقبة أبدًا
    return run(
        args.url, args.interval, log_path,
        map_interval=args.map_interval,
        repo_root=Path(args.awareness_root) if args.awareness_root else None,
        map_store=Path(args.map_store) if args.map_store else None,
    )


if __name__ == "__main__":
    main()
