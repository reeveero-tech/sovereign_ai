# -*- coding: utf-8 -*-
"""
الحارس المعزول (Supervisor) — المرحلة ٢ من META_SYSTEM (R-687)

أمر المالك 2026-10-18: «الحارس المعزول: عملية مستقلة (Subprocess daemon)
تقرأ الحالة من /health و /status وتكتب سجل مراقبة مستقل (append-only).
ممنوع استيراد الحارس مباشرة داخل app.py، لكي لا يتأثر التطبيق إذا مات
الحارس. الاختبارات: اكتب اختبارات RED→GREEN تثبت أن انهيار الحارس كعملية
منفصلة لا يوقف التطبيق».

البنية هنا حرفية كما أمر المالك:
- التطبيق: عملية uvicorn حقيقية منفصلة (app:app) على منفذ حر.
- الحارس: عملية مستقلة (python -m backend.supervisor_daemon) تستطلع
  /health و/status وتلحق سطرًا لسجلها في كل دورة.
- الإثبات الأول: قتل الحارس (SIGKILL) لا يوقف التطبيق — الطلبات تستمر.
- الإثبات الثاني: موت التطبيق لا يقتل الحارس — يسجل الأخطاء ويستمر
  (استقلال في الاتجاهين، والمراقبة لا تموت مع المراقَب).
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _spawn_app(data_root: Path, port: int) -> subprocess.Popen:
    """التطبيق عملية حقيقية مستقلة — نفس عزل الإنتاج."""
    env = dict(os.environ)
    env["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"
    env["SOVEREIGN_DATA_ROOT"] = str(data_root)
    env["SOVEREIGN_DISABLE_BACKGROUND_THREADS"] = "1"
    env.pop("SOVEREIGN_ENVIRONMENT", None)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(_BACKEND_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc


def _wait_http_ok(port: int, timeout: float = 60.0) -> bool:
    """انتظار إقلاع التطبيق: /health يعيد 200 (أو ينتهي الوقت)."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=2
            ) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def _spawn_supervisor(url: str, log_path: Path,
                      interval: float = 0.25) -> subprocess.Popen:
    """الحارس عملية مستقلة — لا علاقة استيراد بالتطبيق إطلاقًا."""
    return subprocess.Popen(
        [sys.executable, "-m", "backend.supervisor_daemon",
         "--url", url, "--interval", str(interval), "--log", str(log_path)],
        cwd=str(_REPO_ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def _wait_log_entries(log_path: Path, minimum: int,
                      timeout: float = 30.0) -> list:
    """انتظار ظهور أسطر كافية في سجل الحارس (دورات مراقبة فعلية)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.exists():
            lines = [
                l for l in log_path.read_text(encoding="utf-8").splitlines()
                if l.strip()
            ]
            if len(lines) >= minimum:
                return [json.loads(l) for l in lines]
        time.sleep(0.25)
    pytest.fail(f"سجل الحارس لم يصل {minimum} سطرًا خلال {timeout}s")


def _get(port: int, path: str):
    import urllib.request
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}{path}", timeout=5
    ) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


@pytest.fixture
def live_app():
    """تطبيق حي على منفذ حر + نظافة مضمونة بعد الاختبار."""
    port = _free_port()
    data_root = Path(tempfile.mkdtemp(prefix="supervisor_app_root_"))
    app_proc = _spawn_app(data_root, port)
    try:
        assert _wait_http_ok(port), "التطبيق لم يقلع خلال المهلة"
        yield port
    finally:
        app_proc.terminate()
        try:
            app_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app_proc.kill()
            app_proc.wait(timeout=10)


def test_supervisor_monitors_and_writes_append_only_log(live_app):
    """الحارس يعمل فعلًا: يستطلع /health و/status ويلحق سطرًا سليم البنية
    لكل دورة — والسجل ينمو فقط (append-only)."""
    port = live_app
    log_path = Path(tempfile.mkdtemp(prefix="supervisor_log_")) / "monitor.jsonl"
    supervisor = _spawn_supervisor(f"http://127.0.0.1:{port}", log_path)
    try:
        entries = _wait_log_entries(log_path, minimum=3)
        for entry in entries:
            assert isinstance(entry.get("ts"), (int, float)), f"بلا وقت: {entry}"
            assert isinstance(entry.get("health"), dict), (
                f"لا قراءة /health: {entry}"
            )
            assert "status" in entry["health"], f"قراءة /health ناقصة: {entry}"
            assert isinstance(entry.get("status"), dict), (
                f"لا قراءة /status: {entry}"
            )
            assert "status" in entry["status"], f"قراءة /status ناقصة: {entry}"
        # append-only: الحجم ينمو فقط وأول سطر لا يتغير
        first_line = log_path.read_text(encoding="utf-8").splitlines()[0]
        size1 = log_path.stat().st_size
        _wait_log_entries(log_path, minimum=len(entries) + 1)
        assert log_path.stat().st_size > size1, "السجل يجب أن ينمو فقط"
        assert log_path.read_text(encoding="utf-8").splitlines()[0] == first_line
    finally:
        supervisor.terminate()
        try:
            supervisor.wait(timeout=10)
        except subprocess.TimeoutExpired:
            supervisor.kill()
            supervisor.wait(timeout=10)


def test_guardian_crash_does_not_stop_app(live_app):
    """الأمر نصًّا: انهيار الحارس كعملية منفصلة لا يوقف التطبيق —
    SIGKILL للحارس ثم سلسلة طلبات ناجحة على التطبيق الحي."""
    port = live_app
    log_path = Path(tempfile.mkdtemp(prefix="supervisor_log_")) / "monitor.jsonl"
    supervisor = _spawn_supervisor(f"http://127.0.0.1:{port}", log_path)
    try:
        _wait_log_entries(log_path, minimum=2)  # الحارس كان يعمل فعلًا قبل موته
    finally:
        pass
    # القتل القسري — أسوأ سيناريو انهيار للحارس
    supervisor.kill()
    supervisor.wait(timeout=10)
    assert supervisor.returncode != 0, "الحارس يجب أن يكون مات فعلًا بالقتل"
    # التطبيق حي تمامًا بعدها: /health و/status وسلسلة طلبات
    st, health = _get(port, "/health")
    assert st == 200 and health["status"] in ("healthy", "degraded"), (
        f"التطبيق يجب أن يبقى حيًا بعد موت الحارس: {st} {health}"
    )
    st, status = _get(port, "/status")
    assert st == 200 and status["status"] == "operational", (
        f"/status يجب أن يستمر: {st}"
    )
    for _ in range(5):
        st, _ = _get(port, "/health")
        assert st == 200, "طلبات متتالية بعد موت الحارس يجب أن تنجح كلها"


def test_supervisor_survives_app_down_and_logs_errors():
    """استقلال الاتجاه الآخر: التطبيق ميت (منفذ مغلق) — الحارس لا يموت،
    يسجل الأخطاء ويستمر بالمراقبة (المراقب لا يموت مع المراقَب)."""
    dead_port = _free_port()  # لا تطبيق عليه — اتصال مرفوض
    log_path = Path(tempfile.mkdtemp(prefix="supervisor_log_")) / "monitor.jsonl"
    supervisor = _spawn_supervisor(f"http://127.0.0.1:{dead_port}", log_path)
    try:
        entries = _wait_log_entries(log_path, minimum=2)
        for entry in entries:
            assert entry.get("health", {}).get("error") or entry.get("status", {}).get("error"), (
                f"التطبيق الميت يجب أن يظهر كخطأ في السجل: {entry}"
            )
        assert supervisor.poll() is None, (
            "الحارس يجب أن يبقى حيًا رغم موت التطبيق — المراقبة لا تموت"
        )
    finally:
        supervisor.terminate()
        try:
            supervisor.wait(timeout=10)
        except subprocess.TimeoutExpired:
            supervisor.kill()
            supervisor.wait(timeout=10)


def test_no_live_code_imports_supervisor():
    """حارس بنيوي (أمر المالك): لا كود حي يستورد الحارس — app.py تحديدًا.
    الحارس يُشغَّل كعملية مستقلة فقط (python -m backend.supervisor_daemon)."""
    live = [
        p for p in _BACKEND_DIR.rglob("*.py")
        if "tests" not in p.parts and p.name != "supervisor_daemon.py"
    ]
    live += [p for p in (_REPO_ROOT / "nexus").rglob("*.py")]
    live += [p for p in _REPO_ROOT.glob("*.py")]
    assert live
    for p in live:
        src = p.read_text(encoding="utf-8", errors="replace")
        for banned in ("supervisor_daemon", "import supervisor"):
            assert banned not in src, (
                f"ربط ممنوع (أمر المالك — المرحلة ٢): {p} يحتوي «{banned}» — "
                "الحارس عملية مستقلة لا استيراد"
            )
