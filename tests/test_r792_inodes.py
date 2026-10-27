# -*- coding: utf-8 -*-
"""R-792: استنفاد عُقد القرص (inodes) حيًا — ملف لكل لحظة وعي ⇒ ENOSPC والمساحة 29%.

الحقيقة الحية 2026-10-27: inodes 322560/322560، 281117 ملفًا في consciousness/moments،
فشل كل إنشاء ملف (index.json.tmp) ورفض الخادم الاتصال. هذه الاختبارات تثبت:
1) الافتراضي ملف يومي واحد بإلحاق (عدد العقد ثابت مهما كثرت اللحظات)، بفاصل أدنى.
2) المسار القديم باقٍ خلف علم (لا حذف)، والملفات القديمة لا تُمس.
3) disk.status يكشف العقد لا المساحة فقط، والاستقلال يراها في ملاحظاته.
"""
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def field_mod(tmp_path, monkeypatch):
    import importlib
    f = importlib.import_module("consciousness.field")
    monkeypatch.setattr(f, "CONSCIOUSNESS_MOMENTS_DIR", tmp_path / "moments")
    monkeypatch.setattr(f, "CONSCIOUSNESS_MOMENTS_DAILY_DIR", tmp_path / "moments_daily")
    (tmp_path / "moments").mkdir()
    return f


def _moment(f, i, ts=1793135000.0):
    return f.ConsciousnessMoment(id=f"m{i:06d}", timestamp=ts + i, level=4, mode="m",
                                 intensity=0.5, clarity=0.5, focus={}, background={},
                                 feeling="calm", integration=0.5, narrative="سرد")


def _engine(f):
    return f.ConsciousnessFieldEngine.__new__(f.ConsciousnessFieldEngine)


def test_default_appends_one_daily_file_not_one_file_per_moment(field_mod, monkeypatch):
    monkeypatch.delenv("SOVEREIGN_MOMENTS_PER_FILE", raising=False)
    monkeypatch.setenv("SOVEREIGN_MOMENT_SAVE_INTERVAL", "0")
    eng = _engine(field_mod)
    for i in range(200):
        eng._save_moment(_moment(field_mod, i))
    daily = list(field_mod.CONSCIOUSNESS_MOMENTS_DAILY_DIR.iterdir())
    assert len(daily) == 1                       # عقدة واحدة لا 200
    assert list(field_mod.CONSCIOUSNESS_MOMENTS_DIR.iterdir()) == []
    lines = daily[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 200 and '"m000199"' in lines[-1]


def test_min_interval_throttles_writes(field_mod, monkeypatch):
    monkeypatch.delenv("SOVEREIGN_MOMENTS_PER_FILE", raising=False)
    monkeypatch.setenv("SOVEREIGN_MOMENT_SAVE_INTERVAL", "5")
    eng = _engine(field_mod)
    for i in range(20):                          # ~لحظتان/ث في الإنتاج
        eng._save_moment(_moment(field_mod, i))
    (daily,) = list(field_mod.CONSCIOUSNESS_MOMENTS_DAILY_DIR.iterdir())
    assert len(daily.read_text(encoding="utf-8").splitlines()) == 1


def test_legacy_per_file_path_kept_behind_flag_and_old_files_untouched(field_mod, monkeypatch):
    old = field_mod.CONSCIOUSNESS_MOMENTS_DIR / "old_moment.json"
    old.write_text('{"id": "old"}', encoding="utf-8")
    monkeypatch.setenv("SOVEREIGN_MOMENTS_PER_FILE", "1")
    eng = _engine(field_mod)
    eng._save_moment(_moment(field_mod, 1))
    names = sorted(p.name for p in field_mod.CONSCIOUSNESS_MOMENTS_DIR.iterdir())
    assert names == ["m000001.json", "old_moment.json"]
    assert old.read_text(encoding="utf-8") == '{"id": "old"}'
    monkeypatch.delenv("SOVEREIGN_MOMENTS_PER_FILE")
    monkeypatch.setenv("SOVEREIGN_MOMENT_SAVE_INTERVAL", "0")
    eng._save_moment(_moment(field_mod, 2))
    assert old.exists()                          # التحويل لا يمس القديم


def test_local_volume_reports_inodes_exhaustion_even_with_free_space(monkeypatch, tmp_path):
    import app as app_mod
    live = types.SimpleNamespace(f_blocks=1280000, f_bavail=909000, f_frsize=4096,
                                 f_files=322560, f_favail=0)
    monkeypatch.setattr(os, "statvfs", lambda p: live)
    v = app_mod._local_volume_status(str(tmp_path))
    assert v["inodes_used_pct"] == 100.0 and v["bytes_used_pct"] == 29.0
    assert v["state"] == "critical"


def test_local_volume_real_statvfs_and_disk_status_payload(tmp_path):
    import app as app_mod
    v = app_mod._local_volume_status(str(tmp_path))
    st = os.statvfs(str(tmp_path))
    assert v["inodes_total"] == st.f_files and v["state"] in ("ok", "warning", "critical")
    assert "local_volume" in app_mod._disk_tool_payload()
    assert "local_volume" not in app_mod._disk_status_payload()  # عقد النقطة كما هو


def test_autonomy_observations_include_local_volume(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_EXPERIENCE_DIR", str(tmp_path / "exp"))
    import goals
    from tool_registry import ToolRegistry, ToolSpec
    reg = ToolRegistry()
    reg.register(ToolSpec(name="disk.status", description="قرص", inputs={}, outputs="",
                          handler=lambda: {"cloud_disk": "disabled",
                                           "local_volume": {"inodes_used_pct": 100.0,
                                                            "state": "critical"}}))
    eng = goals.GoalEngine(reg, chat_fn=lambda *a, **k: None)
    obs = eng.observations()
    assert obs["local_volume"]["inodes_used_pct"] == 100.0
