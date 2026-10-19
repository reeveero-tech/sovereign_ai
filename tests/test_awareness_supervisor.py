# -*- coding: utf-8 -*-
"""
طبقة الوعي (R-694 — المرحلة ٣): الحارس يقرأ الخريطة دوريًا — اختبارات
التكامل الفعلية بعمليات حقيقية.

مواصفة المالك: (ج) الحارس يسجّل العبث في سجل مراقبة، (د) التطبيق لا
يتأثر. واعتراضات المراجع في التخطيط: اختبار الحارس الفعلي (لا استدعاء
دالة مساعدة مرتين) على شجرة مؤقتة مع تعديل ملف بين دورتين، وإثبات
استمرار استجابة التطبيق أثناء رصد التغيير وبعد توقف عملية الحارس —
والفحص البنيوي (app.py بلا أي إشارة لـ awareness) مكمل لا بديل.

البنية حرفية كما في R-687: التطبيق عملية uvicorn حقيقية، والحارس عملية
مستقلة (python -m backend.supervisor_daemon) — التواصل عبر HTTP فقط.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_tree(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")
    (root / "README.md").write_text("# t\n", encoding="utf-8")


def _spawn_app(data_root: Path, port: int) -> subprocess.Popen:
    """التطبيق عملية حقيقية مستقلة — نفس عزل الإنتاج."""
    env = dict(os.environ)
    env["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"
    env["SOVEREIGN_DATA_ROOT"] = str(data_root)
    env["SOVEREIGN_DISABLE_BACKGROUND_THREADS"] = "1"
    env.pop("SOVEREIGN_ENVIRONMENT", None)
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(_BACKEND_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def _spawn_supervisor(
    url: str, log_path: Path, awareness_root: Path,
    interval: float = 0.2, map_interval: float = 0.4,
) -> subprocess.Popen:
    """الحارس عملية مستقلة — يقرأ الخريطة من شجرة الوعي دوريًا.

    مخزن الخريطة صريح داخل جذر بيانات مؤقت (شقيق سجل المراقبة) — لا
    كتابة في data/ الحقيقي للمستودع أبدًا (عزل الاختبارات القائم)."""
    map_store = log_path.parent.parent / "awareness" / "project_map.json"
    return subprocess.Popen(
        [sys.executable, "-m", "backend.supervisor_daemon",
         "--url", url, "--interval", str(interval),
         "--map-interval", str(map_interval), "--log", str(log_path),
         "--awareness-root", str(awareness_root),
         "--map-store", str(map_store)],
        cwd=str(_REPO_ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def _read_log(log_path: Path) -> list:
    if not log_path.exists():
        return []
    return [
        json.loads(l)
        for l in log_path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]


def _await_awareness_event(
    log_path: Path, event: str, timeout: float = 30.0
) -> dict:
    """انتظار حدث وعي محدد في سجل المراقبة (دورية فعلية مثبتة بالسجل)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for entry in _read_log(log_path):
            aw = entry.get("awareness")
            if isinstance(aw, dict) and aw.get("event") == event:
                return aw
        time.sleep(0.25)
    pytest.fail(f"حدث الوعي «{event}» لم يظهر في سجل المراقبة خلال {timeout}s")


def _get_health(port: int) -> int:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/health", timeout=5
    ) as resp:
        return resp.status


def test_supervisor_logs_tampering_periodically(tmp_path):
    """(ج) الحارس الفعلي يسجّل العبث في سجل مراقبته: أول فحص يؤسس المرجعية،
    وتعديل ملف بين فحصين يظهر كتغيير مرصود — بالبصمتين وتفاصيل الملفات."""
    tree = Path(tempfile.mkdtemp(prefix="awareness_tree_"))
    _make_tree(tree)
    data_root = Path(tempfile.mkdtemp(prefix="awareness_data_"))
    log = data_root / "supervisor" / "monitor_log.jsonl"
    # لا تطبيق هنا: منفذ مغلق — الحارس يسجل أخطاء الجلب ويستمر (عقد R-687)
    dead_port = _free_port()
    proc = _spawn_supervisor(f"http://127.0.0.1:{dead_port}", log, tree)
    try:
        baseline = _await_awareness_event(log, "baseline_created")
        assert baseline.get("files") >= 2, "المرجعية أسست على شجرة فارغة؟"
        # العبث: تعديل ملف بين فحصين
        (tree / "src" / "app.py").write_text("print('tampered')\n", encoding="utf-8")
        change = _await_awareness_event(log, "changes_detected")
        assert change.get("changes", {}).get("modified") == ["src/app.py"], (
            f"التعديل غير مسجل بدقة: {change}"
        )
        assert change.get("previous_fingerprint"), "بصمة الخريطة السابقة غائبة"
        assert change.get("current_fingerprint"), "بصمة الخريطة الحالية غائبة"
        assert change["previous_fingerprint"] != change["current_fingerprint"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def test_app_unaffected_during_and_after_awareness(tmp_path):
    """(د) التطبيق لا يتأثر: يستجيب أثناء رصد التغيير وبعد توقف الحارس —
    والفحص البنيوي مكمل: app.py بلا أي إشارة لطبقة الوعي."""
    port = _free_port()
    data_root = Path(tempfile.mkdtemp(prefix="awareness_app_root_"))
    app_proc = _spawn_app(data_root, port)
    tree = Path(tempfile.mkdtemp(prefix="awareness_tree2_"))
    _make_tree(tree)
    sup_log = data_root / "supervisor" / "monitor_log.jsonl"
    deadline = time.time() + 60
    up = False
    while time.time() < deadline and not up:
        try:
            up = _get_health(port) == 200
        except Exception:
            time.sleep(0.5)
    assert up, "التطبيق لم يقلع خلال المهلة"
    sup_proc = _spawn_supervisor(f"http://127.0.0.1:{port}", sup_log, tree)
    try:
        _await_awareness_event(sup_log, "baseline_created")
        # أثناء عمل الحارس: التطبيق يستجيب
        assert _get_health(port) == 200, "التطبيق توقف أثناء عمل الحارس"
        (tree / "src" / "app.py").write_text("print('t2')\n", encoding="utf-8")
        change = _await_awareness_event(sup_log, "changes_detected")
        assert "src/app.py" in change.get("changes", {}).get("modified", [])
        # أثناء رصد التغيير نفسه: التطبيق ما زال يستجيب
        assert _get_health(port) == 200, "التطبيق توقف أثناء رصد التغيير"
    finally:
        sup_proc.terminate()
        try:
            sup_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            sup_proc.kill()
            sup_proc.wait(timeout=10)
    # بعد توقف عملية الحارس: التطبيق يستمر
    assert _get_health(port) == 200, "التطبيق توقف بعد توقف الحارس"
    app_proc.terminate()
    try:
        app_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        app_proc.kill()
        app_proc.wait(timeout=10)
    # الفحص البنيوي المكمل: لا ربط مباشر بالتطبيق — لا استيراد لوحدة الوعي
    # (إشارة consciousness.awareness القائمة مسبقًا وحدة وعي أخرى غير محورنا)
    app_src = (_BACKEND_DIR / "app.py").read_text(encoding="utf-8")
    assert "backend.awareness" not in app_src, "app.py يستورد طبقة الوعي — ربط ممنوع"
    assert "import awareness" not in app_src, "app.py يستورد طبقة الوعي — ربط ممنوع"
