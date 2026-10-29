"""R-804: بوابة الدليل في محرك الأهداف المتعذرة — لا مهمة بلا ملف وسطر حقيقيين.

الدليل الحي (RED): الهدف U-bfea1a63 «هدف عالق: فحص أخطاء النظام واستبدال الحزم المفقودة»
ورث تفصيلًا واحدًا «المهمة SD-25c6ad42 استنفدت 3 محاولات» ثم وُلّدت منه مهام توسيع وتفكيك
بلا files_hint ولا دليل (SD-3388ecf9 ⇒ search_occurs_0_times، SD-40976cdf، SD-e18264ad).

المثبت هنا:
- بلا دليل في الشيفرة ⇒ لا مهمة (outcome=no_evidence) ويتقدم السُلّم بصدق إلى المالك.
- التوسيع يحمل ملفات الدليل وسطرها حرفيًا؛ مصدر الإنذار والمجرَّب سابقًا خارج الدليل.
- التفكيك: الملف من قائمة الدليل (enum) والاقتباس موجود فعلًا في الملف، وإلا رفض مسجَّل.
- الهدف المولود من مهمة مستنفدة يرث نص المهمة الأصلي وملفاتها.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import self_develop as sd  # noqa: E402
from selfdev.unmet import UnmetGoals  # noqa: E402


def _repo(tmp_path):
    b = tmp_path / "backend"
    b.mkdir()
    (b / "pkg_fixer.py").write_text(
        "def replace_missing_package(name):\n    return install_package(name)\n", encoding="utf-8")
    (b / "pkg_tried.py").write_text(
        "def replace_missing_package_old(name):\n    return None\n", encoding="utf-8")
    (b / "watcher.py").write_text(
        "def scan(g):\n    return 'selfmon:goal_stuck:' + g  # replace_missing_package\n", encoding="utf-8")
    return tmp_path


def _engine(repo):
    return sd.SelfDevEngine(repo_root=repo, brain=None, disk=False)


def _set(eng, tid, status, file=None):
    t = eng._tasks[tid]
    t["status"] = status
    if file:
        t["draft"] = {"file": file}


def test_no_evidence_spawns_nothing_and_escalates_honestly(tmp_path):
    eng = _engine(_repo(tmp_path))
    um = UnmetGoals(eng, brain=None, disk=False)
    um.raise_goal("repair_exhausted", "SD-25c6ad42", "هدف عالق: فحص أخطاء النظام واستبدال الحزم المفقودة",
                  detail="المهمة SD-25c6ad42 استنفدت 3 محاولات", now=0.0)
    for i in range(1, 4):
        um.cycle(now=float(i))
    g = um.status()["goals"][0]
    assert [s["outcome"] for s in g["strategies"]] == ["no_evidence", "no_evidence", "escalated"]
    assert g["status"] == "needs_owner" and "لم يُعثر على دليل" in g["owner_report"]
    assert not [t for t in eng.status()["tasks"] if t["source"] == "unmet"]


def test_widen_carries_real_files_and_literal_lines(tmp_path):
    repo = _repo(tmp_path)
    eng = _engine(repo)
    um = UnmetGoals(eng, brain=None, disk=False)
    um.raise_goal("goal_blocked", "G-1", "replace_missing_package يفشل", detail="",
                  files_tried=["backend/pkg_tried.py"], signal_key="selfmon:goal_stuck:G-1", now=0.0)
    um.cycle(now=1.0)
    g = um.status()["goals"][0]
    st = g["strategies"][0]
    assert st["strategy"] == "widen" and st["outcome"] == "spawned"
    files = [e["file"] for e in g["evidence"]]
    assert files == ["backend/pkg_fixer.py"]  # الكاشف (watcher) والمجرَّب (pkg_tried) خارج الدليل
    t = eng._tasks[st["tasks"][0]]
    assert t["files_hint"] == ["backend/pkg_fixer.py"]
    quote = g["evidence"][0]["quote"]
    assert quote in (repo / "backend" / "pkg_fixer.py").read_text(encoding="utf-8")
    assert f"backend/pkg_fixer.py:{g['evidence'][0]['line']}: {quote}" in t["detail"]


def test_decompose_rejects_foreign_file_and_fabricated_quote(tmp_path):
    repo = _repo(tmp_path)
    eng = _engine(repo)
    seen = {}

    def brain(system, user, schema):
        seen["schema"], seen["user"] = schema, user
        return json.dumps({"subtasks": [
            {"title": "صحيح", "detail": "d", "file": "backend/pkg_fixer.py",
             "evidence": "return install_package(name)"},
            {"title": "ملف أجنبي", "detail": "d", "file": "backend/watcher.py", "evidence": "def scan(g):"},
            {"title": "اقتباس مختلق", "detail": "d", "file": "backend/pkg_fixer.py",
             "evidence": "return pip_install_everything()"}]})

    um = UnmetGoals(eng, brain=brain, disk=False)
    um.raise_goal("goal_blocked", "G-2", "replace_missing_package يفشل",
                  signal_key="selfmon:goal_stuck:G-2", now=0.0)
    um.cycle(now=1.0)
    widen = um.status()["goals"][0]["strategies"][0]["tasks"][0]
    _set(eng, widen, "exhausted")
    um.cycle(now=2.0)
    um.cycle(now=3.0)
    g = um.status()["goals"][0]
    st = g["strategies"][-1]
    assert st["strategy"] == "decompose" and len(st["tasks"]) == 1
    assert sorted(r["reason"] for r in st["rejected"]) == [
        "file_not_in_evidence:backend/watcher.py", "quote_not_found_in_file"]
    item = seen["schema"]["properties"]["subtasks"]["items"]
    assert item["properties"]["file"]["enum"] == [e["file"] for e in g["evidence"]]
    assert "backend/watcher.py" not in item["properties"]["file"]["enum"]
    assert {"file", "evidence"} <= set(item["required"])
    assert "install_package" in seen["user"]  # المقتطف الحقيقي معروض للعقل
    sub = eng._tasks[st["tasks"][0]]
    assert sub["files_hint"] == ["backend/pkg_fixer.py"] and "return install_package(name)" in sub["detail"]


def test_goal_from_exhausted_task_inherits_original_detail_and_files(tmp_path):
    repo = _repo(tmp_path)
    eng = _engine(repo)
    t = eng.request("أصلح الحزم", "الدليل: replace_missing_package يعيد None", source="owner", ref="o",
                    now=0.0, files_hint=["backend/pkg_fixer.py"])
    _set(eng, t["id"], "exhausted")
    um = UnmetGoals(eng, brain=None, disk=False)
    um.cycle(now=1.0)
    g = um.status()["goals"][0]
    assert "replace_missing_package يعيد None" in g["detail"]
    assert g["source_files"] == ["backend/pkg_fixer.py"]
    assert g["strategies"][0]["outcome"] == "spawned"
    assert eng.brief(t["id"])["files_hint"] == ["backend/pkg_fixer.py"]


def test_live_stuck_goal_on_real_repo_no_longer_spawns_vague_task():
    eng = sd.SelfDevEngine(repo_root=REPO_ROOT, brain=None, disk=False)
    um = UnmetGoals(eng, brain=None, disk=False)
    um.raise_goal("repair_exhausted", "SD-25c6ad42", "هدف عالق: فحص أخطاء النظام واستبدال الحزم المفقودة",
                  detail="المهمة SD-25c6ad42 استنفدت 3 محاولات", now=0.0)
    out = um.cycle(now=1.0)
    g = um.status()["goals"][0]
    assert out["advanced"][0]["tasks"] == [] and g["strategies"][0]["outcome"] == "no_evidence"


def test_wiring_gives_unmet_the_tool_aware_locator(monkeypatch, tmp_path):
    from selfdev import wiring
    monkeypatch.setattr(sd, "_ENGINE", _engine(_repo(tmp_path)), raising=False)
    wiring.reset()
    try:
        um = wiring.get_unmet()
        assert um._locator is not None and um._locator._registry_fn is wiring._registry
    finally:
        wiring.reset()
