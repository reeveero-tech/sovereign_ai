# -*- coding: utf-8 -*-
"""R-758 (V5 ٥.٣): تقرير قياس الأسطول — تشغيل فعلي لـ10 و100 و1000 عامل.

يكتب forensics/R-758_SCALE_REPORT.json. كل رقم مقيس من التنفيذ (عداد تزامن حي،
عينات RSS من /proc، ساعة perf_counter) — لا رقم محسوب أو مفترض. السجل في القياس
سجل ذاكرة محلي (لا مفتاح توقيع في هذه البيئة)؛ أثر fleet_event الموقّع يتطلب ١.٣.
الاستخدام: python tools/fleet_scale_report.py [مسار_الإخراج]
"""
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


class _LocalLedger:
    """سجل قياس محلي يعد الأحداث — بديل معلن عن السجل الموقّع."""

    def __init__(self):
        self.lock = threading.Lock()
        self.counts = {}

    def append_event(self, t, p, user=None):
        key = f"{t}:{p.get('op', '')}" if isinstance(p, dict) else str(t)
        with self.lock:
            self.counts[key] = self.counts.get(key, 0) + 1


def main(argv):
    import memory.core as core_mod
    import fleet
    out = Path(argv[1]) if len(argv) > 1 else ROOT / "forensics" / "R-758_SCALE_REPORT.json"
    ledger = _LocalLedger()
    core_mod.get_core = lambda: ledger
    runs = []
    plan = ((10, 10, 50), (100, 50, 50), (1000, 100, 50), (1000, 250, 50),
            (1000, 1000, 50), (1000, 1000, 1000))
    for n, cap, ms in plan:
        rep = fleet.measure_scale(n, max_concurrency=cap, work_ms=ms)
        runs.append(rep)
        print(f"n={n} cap={cap} ms={ms} peak={rep['measured_peak_concurrency']} "
              f"done={rep['completed']} wall={rep['wall_s']}s rss_peak={rep['rss_mb_peak']}MB")
    doc = {"record": "R-758", "roadmap": "V5 ٥.٣",
           "measured_at": datetime.now(timezone.utc).isoformat(),
           "method": "كل عامل حلقة R-753 تستدعي أداة work (انتظار I/O بمدة work_ms_per_worker) ثم تتحقق من "
                     "المخرج وتنهي؛ الذروة من عداد حي داخل التنفيذ؛ الذاكرة عينات VmRSS كل 20ms",
           "ledger": "سجل قياس محلي يعد الأحداث (لا مفتاح توقيع هنا — ١.٣)",
           "ledger_event_counts": ledger.counts,
           "limits": ["العمال خيوط في عملية واحدة — مناسبة لعبء I/O لا الحساب الثقيل (GIL)",
                      "البيئة sandbox وليست آلة Fly 512MB — قياس الإنتاج يتطلب النشر ١.٧",
                      "العبء أداة انتظار مُعلنة لا استدعاءات عقل حية (١.٦)"],
           "runs": runs}
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"written {out}")
    return 0 if all(r["completed"] == r["registered"] for r in runs) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
