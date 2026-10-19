# -*- coding: utf-8 -*-
"""
المرحلة ٥ (R-696 — الربط الآمن): نقطة /supervisor/status قراءة فقط.

مواصفة المالك: نقطة واحدة في التطبيق تقرأ ملف نبض الحارس (القناة
المبررة — لا HTTP داخلي)، والحارس الحي up والمعطل down مع 503، وفشل
الحارس لا يُسقط التطبيق أبدًا. اعتراضات المراجع: عقد الحالة محدود
يفشل بأمان (طوابع مستقبلية وأرقام تالفة لا تمنح up)، التنبيهات شروط
دورة قائمة (تظهر وتزول — لا عدّ أسطر سجل)، والقراءة فقط بلا كاتب
متزامن، والمفاتيح المطلوبة بالضبط بلا تسريب.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(port: int, path: str, timeout: float = 10.0):
    """طلب GET يعيد (الرمز، الجسم كديكشنري أو None)."""
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}{path}", timeout=timeout
        ) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except ValueError:
            return exc.code, None


def _spawn_app(data_root: Path, port: int) -> subprocess.Popen:
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
    data_root: Path, interval: float = 0.2,
) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "backend.supervisor_daemon",
         "--url", url, "--interval", str(interval),
         "--map-interval", "0.4", "--log", str(log_path),
         "--awareness-root", str(awareness_root)],
        cwd=str(_REPO_ROOT),
        env={**os.environ, "SOVEREIGN_DATA_ROOT": str(data_root)},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def _await_app(port: int, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=5
            ) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    pytest.fail("التطبيق لم يقلع خلال المهلة")


def _await_status_file(data_root: Path, timeout: float = 30.0) -> Path:
    status = data_root / "supervisor" / "status.json"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if status.is_file():
            try:
                if json.loads(status.read_text(encoding="utf-8")).get("epoch"):
                    return status
            except (OSError, ValueError):
                pass
        time.sleep(0.25)
    pytest.fail("ملف نبض الحارس لم يُكتب خلال المهلة")


def _make_tree(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")


def _stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def test_supervisor_status_returns_up_when_healthy(tmp_path):
    """حالة حية: تطبيق + حارس حقيقيان (القناة ملف النبض) → 200 up
    بالمفاتيح المطلوبة بالضبط: supervisor/last_heartbeat/active_alerts."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    tree = tmp_path / "tree"
    _make_tree(tree)
    log = data_root / "supervisor" / "monitor_log.jsonl"
    app_port = _free_port()
    app_proc = _spawn_app(data_root, app_port)
    try:
        _await_app(app_port)
        sup_proc = _spawn_supervisor(
            f"http://127.0.0.1:{app_port}", log, tree, data_root
        )
        try:
            _await_status_file(data_root)
            deadline = time.time() + 20
            code = body = None
            while time.time() < deadline:
                code, body = _get(app_port, "/supervisor/status")
                if code == 200:
                    break
                time.sleep(0.25)
            assert code == 200, f"النقطة لم تعد up: {code} {body}"
            assert set(body.keys()) == {
                "supervisor", "last_heartbeat", "active_alerts"
            }, f"مفاتيح غير العقد: {body}"
            assert body["supervisor"] == "up"
            assert isinstance(body["active_alerts"], int)
            assert body["active_alerts"] >= 0
            time.strptime(body["last_heartbeat"][:19], "%Y-%m-%dT%H:%M:%S")
        finally:
            _stop(sup_proc)
    finally:
        _stop(app_proc)


def test_supervisor_status_alerts_appear_and_clear(tmp_path):
    """شرط التنبيه يظهر ويزول (اعتراض المراجع): حارس على منفذ مغلق →
    active_alerts ≥ 1 (شرط فشل الجلب قائم في الدورة)؛ ثم خادم حي على
    المنفذ نفسه → الشرط يزول → active_alerts = 0. شروط دورة قائمة —
    لا عدّ أسطر سجل متأثرة بمنع التكرار."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    tree = tmp_path / "tree"
    _make_tree(tree)
    log = data_root / "supervisor" / "monitor_log.jsonl"
    app_port = _free_port()
    app_proc = _spawn_app(data_root, app_port)
    try:
        _await_app(app_port)
        dead_port = _free_port()
        sup_proc = _spawn_supervisor(
            f"http://127.0.0.1:{dead_port}", log, tree, data_root
        )
        try:
            _await_status_file(data_root)
            # التنبيه ظاهر: شرط فشل الجلب قائم
            deadline = time.time() + 20
            while time.time() < deadline:
                code, body = _get(app_port, "/supervisor/status")
                if code == 200 and body["active_alerts"] >= 1:
                    break
                time.sleep(0.25)
            assert code == 200 and body["active_alerts"] >= 1, (
                f"شرط التنبيه لم يظهر: {code} {body}"
            )
            # زوال الشرط: خادم حي على المنفذ → الجلب ينجح → 0
            server = HTTPServer(
                ("127.0.0.1", dead_port),
                _health_handler_factory(),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                deadline = time.time() + 20
                while time.time() < deadline:
                    code, body = _get(app_port, "/supervisor/status")
                    if code == 200 and body["active_alerts"] == 0:
                        break
                    time.sleep(0.25)
                assert code == 200 and body["active_alerts"] == 0, (
                    f"شرط التنبيه لم يزُل: {code} {body}"
                )
            finally:
                server.shutdown()
        finally:
            _stop(sup_proc)
    finally:
        _stop(app_proc)


def _health_handler_factory():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 — توقيع المكتبة القياسي
            body = json.dumps({"status": "ok"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    return Handler


def test_supervisor_status_returns_down_when_killed(tmp_path):
    """إسقاط فعلي: الحارس حي (up بموته مكتشف بمهلة النبض لا فور القتل)
    ثم يُقتل وتُنتظر المهلة الطبيعية (عتبة max(10s، 3×الفاصل) — بلا أي
    تعديل لملف النبض) → 503 down بالمفاتيح المطلوبة بالضبط، والتطبيق لا
    يسقط: /health يعمل و/chat يرد ردًا صالحًا وفق عقده (ChatResponse)."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    tree = tmp_path / "tree"
    _make_tree(tree)
    log = data_root / "supervisor" / "monitor_log.jsonl"
    app_port = _free_port()
    app_proc = _spawn_app(data_root, app_port)
    try:
        _await_app(app_port)
        dead_port = _free_port()
        sup_proc = _spawn_supervisor(
            f"http://127.0.0.1:{dead_port}", log, tree, data_root
        )
        try:
            _await_status_file(data_root)
            deadline = time.time() + 20
            while time.time() < deadline:
                code, body = _get(app_port, "/supervisor/status")
                if code == 200:
                    break
                time.sleep(0.25)
            assert code == 200, "الحارس لم يصل up قبل القتل"
        finally:
            sup_proc.kill()  # قتل فعلي — لا تعديل ملف النبض
            sup_proc.wait(timeout=10)
        # المهلة الطبيعية: العتبة 10 ثوانٍ (الفاصل 0.2) — انتظارها كاملة
        time.sleep(11.5)
        code, body = _get(app_port, "/supervisor/status")
        assert code == 503, f"الرمز ليس 503: {code} {body}"
        assert set(body.keys()) == {"supervisor", "reason"}, (
            f"مفاتيح غير العقد: {body}"
        )
        assert body["supervisor"] == "down"
        assert isinstance(body["reason"], str) and body["reason"]
        # التطبيق لم يسقط: الصحة والمحادثة وفق عقديهما
        code, _ = _get(app_port, "/health")
        assert code == 200, "/health توقف بعد موت الحارس"
        req = urllib.request.Request(
            f"http://127.0.0.1:{app_port}/chat",
            data=json.dumps({"text": "سلام — اختبار الربط الآمن"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            assert resp.status == 200
            chat = json.loads(resp.read().decode())
        assert isinstance(chat.get("reply"), str) and chat["reply"], (
            f"رد المحادثة ليس ردًا صالحًا وفق عقده: {chat}"
        )
    finally:
        _stop(app_proc)


def test_app_startup_succeeds_without_supervisor(tmp_path):
    """الإقلاع بلا حارس من البداية: التطبيق يعمل، والنقطة تُقرأ down
    بـ503 (الملف غائب) — لا اعتماد وجوديًا على الحارس."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    app_port = _free_port()
    app_proc = _spawn_app(data_root, app_port)
    try:
        _await_app(app_port)
        code, body = _get(app_port, "/supervisor/status")
        assert code == 503, f"بلا حارس يجب 503: {code} {body}"
        assert set(body.keys()) == {"supervisor", "reason"}
        assert body["supervisor"] == "down"
        code, _ = _get(app_port, "/health")
        assert code == 200
    finally:
        _stop(app_proc)


def test_supervisor_status_endpoint_is_readonly(tmp_path):
    """قراءة فقط (بلا كاتب متزامن — بلا حارس): ملف نبض ثابت، بصمة دليل
    الحارس ومحتوياته قبل الطلبات وبعدها متطابقة، وطرق الكتابة على المسار
    مرفوضة (405) بلا أثر، ومصدر app.py لا يفتح مسار النبض للكتابة."""
    data_root = tmp_path / "data"
    sup_dir = data_root / "supervisor"
    sup_dir.mkdir(parents=True)
    # ملف نبض صالح ثابت (عُدة الواجهة — بلا كاتب حي)
    from datetime import datetime, timezone
    status_file = sup_dir / "status.json"
    status_file.write_text(json.dumps({
        "heartbeat": datetime.now(timezone.utc).isoformat(),
        "epoch": time.time(), "interval": 2.0, "active_alerts": 0,
    }), encoding="utf-8")
    app_port = _free_port()
    app_proc = _spawn_app(data_root, app_port)
    try:
        _await_app(app_port)
        before_dir = sorted(p.name for p in sup_dir.iterdir())
        before_bytes = status_file.read_bytes()
        code, body = _get(app_port, "/supervisor/status")
        assert code == 200 and body["supervisor"] == "up"
        code, _ = _get(app_port, "/health")
        assert code == 200
        # طرق الكتابة على المسار مرفوضة بلا أثر
        for method in ("POST", "PUT", "DELETE"):
            req = urllib.request.Request(
                f"http://127.0.0.1:{app_port}/supervisor/status",
                data=b"{}", method=method,
                headers={"Content-Type": "application/json"},
            )
            try:
                urllib.request.urlopen(req, timeout=10)
                pytest.fail(f"{method} لم يُرفض على مسار القراءة")
            except urllib.error.HTTPError as exc:
                assert exc.code == 405, f"{method} → {exc.code} لا 405"
        # الدليل والملف لم يمسا
        after_dir = sorted(p.name for p in sup_dir.iterdir())
        assert after_dir == before_dir, "دليل الحارس تغير بفعل الطلبات"
        assert status_file.read_bytes() == before_bytes, (
            "ملف النبض عُدل — كتابة من التطبيق ممنوعة"
        )
        # فحص مصدري: app.py لا يفتح مسار النبض للكتابة أبدًا
        app_src = (_BACKEND_DIR / "app.py").read_text(encoding="utf-8")
        assert 'DATA_DIR / "supervisor" / "status.json"' in app_src, (
            "مسار النبض تغير — حدّث الفحص"
        )
        # الكتابة الوحيدة الممكنة على المسار داخل _load_heartbeat قراءة
        # نصية فقط — لا open بوضع كتابة على هذا المسار في الملف كله
        for line in app_src.splitlines():
            if "supervisor" in line and "status.json" in line:
                assert "read_text" in line or "open(" not in line, (
                    f"سطر يفتح مسار النبض بوضع غير القراءة: {line}"
                )
    finally:
        _stop(app_proc)


def test_supervisor_status_does_not_leak_paths_or_secrets(tmp_path):
    """لا تسريب: الحالتان (up وكل أسباب down: غائب/تالف/قديم/مستقبلي)
    بمفاتيح مطلوبة بالضبط، ولا قيمة تحمل مسارًا أو سرًّا أو جذر بيانات —
    تشمل حالة فساد الملف وفشل قراءته (اعتراض المراجع)."""
    data_root = tmp_path / "data"
    sup_dir = data_root / "supervisor"
    sup_dir.mkdir(parents=True)
    app_port = _free_port()
    app_proc = _spawn_app(data_root, app_port)
    try:
        _await_app(app_port)
        status_file = sup_dir / "status.json"

        def _assert_no_leak(body):
            for value in body.values():
                text = str(value)
                for banned in (str(data_root), "SOVEREIGN", "KEY", "/"):
                    assert banned not in text, (
                        f"تسريب في الاستجابة: {banned!r} في {text!r}"
                    )

        # ١) غائب → down/invalid
        code, body = _get(app_port, "/supervisor/status")
        assert code == 503 and set(body) == {"supervisor", "reason"}
        assert body["supervisor"] == "down"
        _assert_no_leak(body)
        # ٢) تالف JSON → down/invalid
        status_file.write_text("{تالف", encoding="utf-8")
        code, body = _get(app_port, "/supervisor/status")
        assert code == 503 and body["supervisor"] == "down"
        _assert_no_leak(body)
        # ٣) أرقام تالفة (interval سالب) → down/invalid لا up أبدية
        status_file.write_text(json.dumps({
            "heartbeat": "2026-10-19T12:00:00+00:00",
            "epoch": time.time(), "interval": -5.0, "active_alerts": 0,
        }), encoding="utf-8")
        code, body = _get(app_port, "/supervisor/status")
        assert code == 503 and body["supervisor"] == "down"
        _assert_no_leak(body)
        # ٤) طابع مستقبلي → down/invalid
        status_file.write_text(json.dumps({
            "heartbeat": "2026-10-19T12:00:00+00:00",
            "epoch": time.time() + 3600, "interval": 2.0,
            "active_alerts": 0,
        }), encoding="utf-8")
        code, body = _get(app_port, "/supervisor/status")
        assert code == 503 and body["supervisor"] == "down"
        _assert_no_leak(body)
        # ٥) قديم → down/stale
        status_file.write_text(json.dumps({
            "heartbeat": "2026-10-19T12:00:00+00:00",
            "epoch": time.time() - 3600, "interval": 2.0,
            "active_alerts": 0,
        }), encoding="utf-8")
        code, body = _get(app_port, "/supervisor/status")
        assert code == 503 and body["supervisor"] == "down"
        _assert_no_leak(body)
        # ٦) صالح → up — ولا تسريب
        from datetime import datetime, timezone
        status_file.write_text(json.dumps({
            "heartbeat": datetime.now(timezone.utc).isoformat(),
            "epoch": time.time(), "interval": 2.0, "active_alerts": 1,
        }), encoding="utf-8")
        code, body = _get(app_port, "/supervisor/status")
        assert code == 200 and set(body) == {
            "supervisor", "last_heartbeat", "active_alerts"
        }
        _assert_no_leak(body)
    finally:
        _stop(app_proc)
