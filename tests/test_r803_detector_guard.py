"""R-803 (مواصلة التطوير 2026-10-28): مصدر الإنذار ليس هدف إصلاح.

الدليل الحي (/selfdev/nucleus على الإنتاج): الإشارة `selfmon:goal_stuck:G-6eeb1d19` وُجّهت
code_fix إلى `backend/self_monitor.py` — الملف الذي يُصدر الإنذار — وخطة العقل «استبدل all() بـ any()»
في شرط الكشف نفسه: إسكات الإنذار بدل إصلاح سببه. ثم ورثت كل المهام اللاحقة الخطأ.
المثبت: الكاشف لا يكون قابلًا للتعديل لإشارته، فلا يقبله التحقق هدفًا؛ إلا إن كان العطل فيه (Traceback).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import self_develop as sd  # noqa: E402
from selfdev.locator import Locator  # noqa: E402
from selfdev.proposal_brain import ProposalBrain  # noqa: E402

DETECTOR = (
    "def scan(goals):\n"
    "    out = []\n"
    "    for gid, g in goals.items():\n"
    "        if all(r != 'completed' for r in g['runs']):\n"
    "            out.append(f\"selfmon:goal_stuck:{gid}\")\n"
    "    return out\n"
)
CAUSE = "def run_goal(g):\n    return g.get('goal_stuck_reason') or 'failed'\n"


def _repo(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "watcher.py").write_text(DETECTOR, encoding="utf-8")
    (tmp_path / "backend" / "runner.py").write_text(CAUSE, encoding="utf-8")
    return tmp_path


SIG = {"key": "selfmon:goal_stuck:G-1", "title": "هدف عالق goal_stuck", "evidence": "آخر 3 تشغيلات لم تكتمل",
       "origins": ["self_monitor"], "severity": "medium", "kind_hint": "code_fix"}


def test_alarm_literal():
    assert Locator.alarm_literal("selfmon:goal_stuck:G-1") == "selfmon:goal_stuck:"
    assert Locator.alarm_literal("benchmark_gap:mind_latency") == "benchmark_gap:"
    assert Locator.alarm_literal("supervisor_heartbeat_missing") == "supervisor_heartbeat_missing"


def test_detector_not_editable_cause_still_editable(tmp_path):
    locs = {l["file"]: l for l in Locator(_repo(tmp_path)).locate(SIG)}
    assert locs["backend/watcher.py"]["editable"] is False and locs["backend/watcher.py"]["detector"]
    assert locs["backend/runner.py"]["editable"] is True


def test_detector_editable_when_it_is_the_crash(tmp_path):
    sig = dict(SIG, evidence='Traceback (most recent call last):\n  File "backend/watcher.py", line 4\nKeyError: runs')
    locs = {l["file"]: l for l in Locator(_repo(tmp_path)).locate(sig)}
    assert locs["backend/watcher.py"]["editable"] is True


def test_brain_cannot_target_detector(tmp_path):
    def brain(system, user, schema):
        return json.dumps({"route": "code_fix", "target_file": "backend/watcher.py", "root_cause": "شرط الكشف",
                           "plan": ["استبدل all بـ any"], "acceptance_test": "x", "confidence": 0.9})
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path), brain=None, disk=False)
    out = ProposalBrain(brain, Locator(tmp_path, engine=eng)).analyze(SIG)
    assert out["route"] != "code_fix" and out["target_file"] is None
    assert any("watcher.py" in n for n in out["validation_notes"])


def test_deterministic_path_skips_detector(tmp_path):
    eng = sd.SelfDevEngine(repo_root=_repo(tmp_path), brain=None, disk=False)
    out = ProposalBrain(None, Locator(tmp_path, engine=eng)).analyze(SIG)
    assert out["target_file"] != "backend/watcher.py"


def test_real_repo_live_signals_do_not_target_their_detectors():
    loc = Locator(sd.REPO_ROOT)
    for key, det in (("selfmon:goal_stuck:G-6eeb1d19", "backend/self_monitor.py"),
                     ("benchmark_gap:mind_latency", "backend/external_benchmark.py"),
                     ("supervisor_heartbeat_missing", "backend/defect_scan.py")):
        locs = {l["file"]: l for l in loc.locate({"key": key, "title": key, "evidence": ""})}
        assert det in locs and locs[det]["editable"] is False, key
