"""R-776 (ROADMAP_V6 ٦.١.٣) — فهرس السجل محدود الحجم.

الدليل الحي (2026-10-26 بعد نشر R-775): معالج التطبيق ~8% من نواة لكن الحمل 4.9–6.9 ⇒ خيوط
محجوبة بالإدخال/الإخراج. `index.json` = 16.7MB منها `by_hash` 13.5MB (55,434 مدخلًا، بلا حد)
و`by_type` 3.8MB، ويُعاد كتابته كاملًا + fsync كل 5ث (R-762) ⇒ ~3.3MB/ث كتابة مستمرة.
ولا قارئ لـ`by_hash` خارج `SovereignIndex.get_event` (لا يناديها أحد)، ولا لـ`get_events_by_type`.
الفهرس ذاكرة مؤقتة قابلة لإعادة البناء؛ السجل وحده مصدر الحقيقة ولم يُمس.
"""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from backend.memory.core import SovereignIndex


@pytest.fixture
def tmp():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _add(idx, i, t="t"):
    idx.add_event(event_hash=f"h{i:06d}", event_type=t, event_time=f"T{i}", prev_hash=f"h{i-1:06d}")


def test_by_hash_keeps_only_the_newest_entries(tmp, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_INDEX_BY_HASH_MAX", "10")
    idx = SovereignIndex(tmp / "index.json")
    for i in range(50):
        _add(idx, i)
    assert len(idx.data["by_hash"]) == 10
    assert list(idx.data["by_hash"]) == [f"h{i:06d}" for i in range(40, 50)]
    assert idx.get_event("h000049")["time"] == "T49"
    assert idx.get_event("h000000") is None
    assert idx.data["events_count"] == 50  # العدّاد الكامل لا يتأثر (مطابقة الإقلاع R-762)


def test_default_cap_bounds_production_scale(tmp, monkeypatch):
    monkeypatch.delenv("SOVEREIGN_INDEX_BY_HASH_MAX", raising=False)
    monkeypatch.setenv("SOVEREIGN_INDEX_SAVE_INTERVAL", "3600")
    idx = SovereignIndex(tmp / "index.json")
    for i in range(12000):
        _add(idx, i, t=f"type{i % 52}")
    idx.save()
    assert len(idx.data["by_hash"]) == 10000
    assert all(len(v) <= 500 for v in idx.data["by_type"].values())
    size = (tmp / "index.json").stat().st_size
    assert size < 5_000_000, f"index.json {size/1e6:.1f}MB"


def test_by_type_capped_per_type(tmp, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_INDEX_BY_TYPE_MAX", "5")
    idx = SovereignIndex(tmp / "index.json")
    for i in range(20):
        _add(idx, i, t="a")
    _add(idx, 99, t="b")
    assert idx.data["by_type"]["a"] == [f"h{i:06d}" for i in range(15, 20)]
    assert idx.data["by_type"]["b"] == ["h000099"]


def test_oversized_index_from_disk_is_trimmed_on_next_event(tmp, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_INDEX_BY_HASH_MAX", "10")
    big = SovereignIndex(tmp / "index.json")._empty_index()
    big["by_hash"] = {f"h{i:06d}": {"type": "t", "time": "", "prev_hash": "", "user": None} for i in range(100)}
    big["events_count"] = 100
    (tmp / "index.json").write_text(json.dumps(big), encoding="utf-8")
    idx = SovereignIndex(tmp / "index.json")
    _add(idx, 100)
    assert len(idx.data["by_hash"]) == 10 and "h000100" in idx.data["by_hash"]
    assert idx.data["events_count"] == 101
