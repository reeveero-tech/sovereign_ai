"""R-779 (ROADMAP_V6 ٦.١.٢) — ضبط مخصص glibc في بيئة الإنتاج.

الدليل (2026-10-26، `forensics/R-779_measure_allocator.txt`): بعد R-777/R-778 صار نمو كائنات
Python شبه صفري (tracemalloc: +4.6MB في 6 دقائق منها 1.4MB لأداة القياس نفسها)، والفرق في RSS
من المخصص الأصلي. ثلاث نسخ متوازية 900ث على الكود نفسه: افتراضي 221MB، `MALLOC_ARENA_MAX=2`
167MB، ومعه عتبة mmap/trim ثابتة 131072 = 154MB، بالمعالج نفسه تقريبًا (+0.7ث نظام في 798ث).
"""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env():
    return tomllib.loads((ROOT / "fly.toml").read_text(encoding="utf-8"))["env"]


def test_arena_max_is_bounded():
    assert _env().get("MALLOC_ARENA_MAX") == "2"


def test_mmap_and_trim_thresholds_are_fixed():
    env = _env()
    assert env.get("MALLOC_MMAP_THRESHOLD_") == "131072"
    assert env.get("MALLOC_TRIM_THRESHOLD_") == "131072"
