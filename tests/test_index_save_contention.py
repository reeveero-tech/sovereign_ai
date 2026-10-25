"""R-772 — حفظ الفهرس لا يحتجز قفل السجل دقائق، ولا يترك فهرسًا صفريًا بعد القتل.

دليل الإنتاج (2026-10-26، بعد نشر R-771): `agent.run` و`fleet.spawn` فشلا بـ
`TimeoutError: لا يمكن الحصول على القفل`. 30 عينة py-spy من العملية الحية: الماسك للقفل
في 27 منها داخل `SovereignIndex.save → json.dump`، و25 خيطًا تنتظر. `index.json.tmp`
بلغ 2MB من ~15MB بعد أكثر من 6 دقائق كتابة. السبب: `json.dump(obj, f)` يستخدم المرمّز
بلغة Python (`_iterencode_dict`) الذي يتخلى عن قفل المفسّر بين القطع — ومع ~100 خيط على
معالج مشترك واحد يمتد دقائق، والقفل محتجز طوال ذلك. القياس المحلي مع 60 خيطًا مشغولًا:
`json.dump` إلى ملف 8.9ث مقابل `json.dumps` (مرمّز C دفعة واحدة) 0.12ث — 73 ضعفًا.

وكان `index.json` نفسه على الإنتاج تالفًا: بايتات صفرية من الحرف 525,772 — الحفظ يكتب
ملفًا مؤقتًا ثم `os.replace` بلا `fsync`، فقتل العملية عند النشر يترك محتوى لم يُدفع للقرص.
"""
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

import backend.memory.core as core_mod
from backend.memory.core import SovereignIndex


@pytest.fixture
def index():
    tmp = Path(tempfile.mkdtemp())
    idx = SovereignIndex(tmp / "index.json")
    for i in range(50):
        idx.data["by_hash"][f"h{i}"] = {"type": "t", "time": "x", "prev_hash": "p", "user": None}
    idx.data["events_count"] = 50
    yield idx
    shutil.rmtree(tmp, ignore_errors=True)


def test_save_uses_one_shot_encoder_not_streaming_dump(index, monkeypatch):
    def streaming_dump(*a, **k):
        raise AssertionError("json.dump (مرمّز Python المتدفق) يحتجز القفل دقائق تحت التزاحم")
    monkeypatch.setattr(core_mod.json, "dump", streaming_dump)
    index.save()
    data = json.loads(index.index_file.read_text(encoding="utf-8"))
    assert data["events_count"] == 50 and len(data["by_hash"]) == 50


def test_save_fsyncs_tmp_before_replace(index, monkeypatch):
    calls = []
    real_fsync, real_replace = os.fsync, os.replace
    monkeypatch.setattr(core_mod.os, "fsync", lambda fd: (calls.append("fsync"), real_fsync(fd))[1])
    monkeypatch.setattr(core_mod.os, "replace",
                        lambda a, b: (calls.append("replace"), real_replace(a, b))[1])
    index.save()
    assert "replace" in calls
    assert "fsync" in calls[:calls.index("replace")], calls


def test_saved_index_roundtrips(index):
    index.save()
    again = SovereignIndex(index.index_file)
    assert again.data["by_hash"] == index.data["by_hash"]
