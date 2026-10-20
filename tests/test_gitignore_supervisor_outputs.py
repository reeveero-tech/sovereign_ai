"""GS-2 (قرار المالك د.٤ — 2026-10-20): مخرجات الحارس المحلي لا تُلتزم.

تشغيل `python -m backend.supervisor_daemon` محليًا (دليل التجربة §٦) يُنشئ
`data/supervisor/` (status.json + monitor_log.jsonl) و`data/awareness/`
(خريطة الوعي). كانت تظهر في `git status` غير متتبعة — بيانات تشغيل حية،
لا مصدر. هذا الاختبار يثبت أن git يتجاهلها، وأن لا ملف متتبعًا تحتها.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

RUNTIME_PATHS = [
    "data/supervisor/status.json",
    "data/supervisor/monitor_log.jsonl",
    "data/awareness/project_map.json",
]


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True)


def test_supervisor_runtime_outputs_are_ignored():
    not_ignored = [p for p in RUNTIME_PATHS if _git("check-ignore", "-q", "--no-index", p).returncode != 0]
    assert not not_ignored, f"مخرجات الحارس غير مستثناة في .gitignore: {not_ignored}"


def test_no_tracked_files_under_supervisor_outputs():
    tracked = _git("ls-files", "data/supervisor", "data/awareness").stdout.split()
    assert not tracked, f"ملفات متتبعة تحت مسارات مستثناة: {tracked}"
