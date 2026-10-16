# -*- coding: utf-8 -*-
"""اختبارات مسجل أفعال البناء الفعلي (tools/action_log.py).

الجولة الإنشائية — تصويب المراجع (الاعتراض 7): كل فعل يُوثَّق بإثبات
زمني حقيقي — لقطة «قبل» تؤخذ قبل تنفيذ الفعل مباشرة، و«بعد» بعده، مع
طابع زمني لكل منهما. الاختبارات مستقلة تمامًا عن حالة الشجرة الحالية
(مستودع Git مؤقت داخل tmp_path) — لا تعتمد على تعديلات غير ملتزمة.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from tools.action_log import _sha_bytes, record, run_logged, snapshot_files  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _make_temp_repo(tmp_path: Path) -> Path:
    """مستودع Git مؤقت بملتزامين — أساس مستقل للقيل والقال."""
    repo = tmp_path / "repo"
    repo.mkdir()
    def _git(*args):
        r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(repo))
        assert r.returncode == 0, f"git {args} failed: {r.stderr}"
    _git("init", "-q")
    (repo / "module.py").write_text("# v1\n", encoding="utf-8")
    _git("add", "-A")
    _git("-c", "user.name=test", "-c", "user.email=t@t", "commit", "-q", "-m", "c1")
    return repo


def test_record_captures_real_ts_and_before_after_hashes(tmp_path):
    """تسجيل فعل داخل مستودع مؤقت: تعديل غير ملتزم — الهاشان مختلفان،
    «قبل» يطابق HEAD، «بعد» يطابق الشجرة، والطابع الزمني حقيقي."""
    repo = _make_temp_repo(tmp_path)
    target = "module.py"
    log_file = tmp_path / "build_actions.jsonl"

    # تعديل غير ملتزم
    (repo / target).write_text("# v2 modified\n", encoding="utf-8")

    rec = record("تعديل module.py", [target], log_path=log_file, repo_root=repo)

    # طابع زمني حقيقي
    ts = datetime.fromisoformat(rec["ts"])
    now = datetime.now(ts.tzinfo)
    assert abs((now - ts).total_seconds()) < 60, "ts must be real and current"

    entry = rec["files"][0]
    assert entry["path"] == target
    assert entry["before_sha"] and entry["after_sha"]
    assert entry["before_sha"] != entry["after_sha"], "uncommitted change — hashes must differ"

    # «قبل» قابل للتحقق من Git
    git_content = subprocess.run(
        ["git", "show", f"HEAD:{target}"],
        capture_output=True, cwd=str(repo),
    ).stdout
    assert entry["before_sha"] == _sha_bytes(git_content)

    # «بعد» يطابق الشجرة
    assert entry["after_sha"] == _sha_bytes((repo / target).read_bytes())

    # السجل append-only JSONL
    lines = [l for l in log_file.read_text(encoding="utf-8").split("\n") if l.strip()]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["action"] == rec["action"]


def test_run_logged_proves_timing_around_action(tmp_path):
    """الغلاف الفعلي: لقطة «قبل» تُؤخذ قبل تنفيذ الفعل، و«بعد» بعده —
    وتعديلان متتابعان: «قبل الثاني» = «بعد الأول» (إثبات زمني متسق)."""
    repo = _make_temp_repo(tmp_path)
    target = "module.py"
    log_file = tmp_path / "build_actions.jsonl"

    def _modify_v2():
        (repo / target).write_text("# v2\n", encoding="utf-8")
        return "done-v2"

    result1, rec1 = run_logged("التعديل الأول", [target], _modify_v2,
                               log_path=log_file, repo_root=repo)
    assert result1 == "done-v2"
    after1 = rec1["files"][0]["after_sha"]
    # «قبل» الفعل الأول = الحالة الملتزمة (v1)
    before1 = rec1["files"][0]["before_sha"]
    assert before1 == _sha_bytes(b"# v1\n")

    def _modify_v3():
        (repo / target).write_text("# v3\n", encoding="utf-8")
        return "done-v3"

    result2, rec2 = run_logged("التعديل الثاني", [target], _modify_v3,
                               log_path=log_file, repo_root=repo)
    assert result2 == "done-v3"
    before2 = rec2["files"][0]["before_sha"]

    # الإثبات الزمني: «قبل الثاني» = «بعد الأول» — تسلسل حقيقي لا لقطة HEAD
    assert before2 == after1, (
        "pre-action snapshot of the second action must equal the post-state "
        "of the first — real per-action timing proof"
    )
    assert rec2["timing_proof"] == "pre-action snapshot"

    # السجل: إدخالان append-only
    lines = [l for l in log_file.read_text(encoding="utf-8").split("\n") if l.strip()]
    assert len(lines) == 2


def test_snapshot_files_reads_current_state(tmp_path):
    """snapshot_files تقرأ الشجرة العاملة لحظة الالتقاط — لا HEAD."""
    repo = _make_temp_repo(tmp_path)
    (repo / "module.py").write_text("# uncommitted state\n", encoding="utf-8")
    snap = snapshot_files(["module.py"], repo_root=repo)
    assert snap["module.py"] == _sha_bytes(b"# uncommitted state\n")
    assert snap["module.py"] != _sha_bytes(b"# v1\n")


def test_run_logged_writes_complete_record_to_disk(tmp_path):
    """السجل المحفوظ على القرص كامل: وقت البداية والنهاية، البصمتان،
    الحالة، والنتيجة — يُقرأ من JSONL لا من الكائن المعاد (تصويب المراجع)."""
    import json

    repo = _make_temp_repo(tmp_path)
    log_file = tmp_path / "build_actions.jsonl"

    def _modify():
        (repo / "module.py").write_text("# v2-logged\n", encoding="utf-8")
        return {"changed": 1}

    result, rec = run_logged("فعل موثق", ["module.py"], _modify,
                              log_path=log_file, repo_root=repo)
    assert result == {"changed": 1}

    # القراءة من القرص — لا الاعتماد على الكائن المعاد
    lines = [l for l in log_file.read_text(encoding="utf-8").split("\n") if l.strip()]
    assert len(lines) == 1
    on_disk = json.loads(lines[0])

    for field in ("ts", "started_at", "ended_at", "action", "files",
                  "timing_proof", "status", "result"):
        assert field in on_disk, f"missing field on disk: {field}"
    assert on_disk["status"] == "ok"
    assert on_disk["result"] == {"changed": 1}
    assert on_disk["started_at"] <= on_disk["ended_at"]
    entry = on_disk["files"][0]
    assert entry["before_sha"] == _sha_bytes(b"# v1\n")
    assert entry["after_sha"] == _sha_bytes(b"# v2-logged\n")


def test_run_logged_records_failure_and_reraises(tmp_path):
    """فشل الفعل لا يُسكت: سطر بـstatus=failed والخطأ، ثم يُعاد رفع
    الاستثناء — لا فعل بلا سجل (تصويب المراجع)."""
    import json

    repo = _make_temp_repo(tmp_path)
    log_file = tmp_path / "build_actions.jsonl"

    def _boom():
        raise ValueError("intentional failure")

    with pytest.raises(RuntimeError, match="intentional failure"):
        run_logged("فعل فاشل", ["module.py"], _boom,
                    log_path=log_file, repo_root=repo)

    lines = [l for l in log_file.read_text(encoding="utf-8").split("\n") if l.strip()]
    assert len(lines) == 1, "failure must still be logged"
    on_disk = json.loads(lines[0])
    assert on_disk["status"] == "failed"
    assert "intentional failure" in on_disk["error"]
    # الملف لم يتغير — البصمتان متطابقتان
    entry = on_disk["files"][0]
    assert entry["before_sha"] == entry["after_sha"]


def test_gate_runner_command_shape():
    """غلاف البوابة (tools/run_gate.py) مستورد فعليًا (لا يتيمًا) — وأمر
    البوابة هو الأمر الفعلي نفسه: junit-prefix + استبعاد التشغيلية."""
    from tools.run_gate import GATE_CMD

    assert any("--junit-prefix=" in part for part in GATE_CMD), (
        "gate command must use --junit-prefix (verify.sh actual command)"
    )
    assert "-m" in GATE_CMD and "not operational" in GATE_CMD, (
        "gate command must deselect operational tests (verify.sh mechanism)"
    )
    assert any("junitxml" in part for part in GATE_CMD)
    # لا يشغل البوابة هنا — الاستيراد فقط (التشغيل تحت __main__)
