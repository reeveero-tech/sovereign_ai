# -*- coding: utf-8 -*-
"""
المرحلة ٤ (R-695): الربط بالحارس — اختبارات التكامل بعمليات حقيقية.

مواصفة المالك: المصنف والمقترح مربوطان بالحارس (لا بـapp.py). واعتراضات
المراجع (ج2–ج4): المسار المتصل من حدث حارس قائم إلى التصنيف ثم اقتراح
منطبق (لا ملف حادثة منشأ وCLI فقط)، وحوادث الوعي تصل المصنف حتى مع
استجابة HTTP سليمة، والرقعة تُفحص بالتنفيذ على نسخة اختبارية فقط،
و(د) app.py لا يتأثر: التطبيق يستجيب أثناء معالجة الحارس وبعدها
وapp.py وbackend/compat وbackend/Mr.py لا تتغير.
"""

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
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


def _read_log(log_path: Path) -> list:
    if not log_path.exists():
        return []
    return [
        json.loads(l)
        for l in log_path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]


def _await_incident_in_log(log_path: Path, incident_class: str | None = None,
                           timeout: float = 40.0) -> dict:
    """انتظار سطر دورة يحمل حادثة مصنفة من الحارس الفعلي."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for entry in _read_log(log_path):
            inc = entry.get("incident")
            if isinstance(inc, dict) and inc.get("class"):
                if incident_class is None or inc["class"] == incident_class:
                    return inc
        time.sleep(0.25)
    pytest.fail(
        f"الحارس لم يسجل حادثة {incident_class or 'مصنفة'} في سجل المراقبة خلال المهلة"
    )


def _make_tree(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")


def _make_repair_fixture(tmp: Path):
    """عُدة المسار المتصل: شجرة فيها المكوّن المعزول المعطوب الاستيراد +
    الوحدة المستهدفة النظيفة + سجل عزل حقيقي + جذر بيانات."""
    tree = tmp / "tree"
    (tree / "backend" / "memory").mkdir(parents=True)
    (tree / "backend" / "predictive").mkdir(parents=True)
    source_text = "import json\nimport predictive\n"
    component_src = tree / "backend" / "memory" / "__init__.py"
    component_src.write_text(source_text, encoding="utf-8")
    (tree / "backend" / "predictive" / "__init__.py").write_text(
        "marker = 'predictive-ok'\n", encoding="utf-8")
    data_root = tmp / "data"
    (data_root / "loyalty").mkdir(parents=True)
    (data_root / "loyalty" / "quarantine_log.jsonl").write_text(
        json.dumps({"time": 1.0, "kind": "quarantine", "detail": "خلل",
                    "component": "memory"}) + "\n",
        encoding="utf-8",
    )
    return tree, data_root, component_src, source_text


def _spawn_supervisor(
    url: str, log_path: Path, awareness_root: Path,
    data_root: Path, interval: float = 0.2,
) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "backend.supervisor_daemon",
         "--url", url, "--interval", str(interval),
         "--map-interval", "0.4", "--log", str(log_path),
         "--awareness-root", str(awareness_root)],
        cwd=str(_REPO_ROOT), env={**os.environ, "SOVEREIGN_DATA_ROOT": str(data_root)},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


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


def _get_health(port: int) -> int:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/health", timeout=5
    ) as resp:
        return resp.status


def test_supervisor_loop_classifies_real_incidents(tmp_path):
    """الربط الفعلي (ج): حلقة الحارس تصنف حوادثها الفعلية — خطأ جلب حقيقي
    (منفذ مغلق — عقد R-687، لا بيانات مصطنعة) يظهر بسطر الدورة بحادثة
    network_error مع الإجراء، والعقد قائم (health/status في كل سطر)."""
    tree = Path(tempfile.mkdtemp(prefix="repair_tree_"))
    _make_tree(tree)
    data_root = Path(tempfile.mkdtemp(prefix="repair_data_"))
    log = data_root / "supervisor" / "monitor_log.jsonl"
    dead_port = _free_port()
    proc = _spawn_supervisor(f"http://127.0.0.1:{dead_port}", log, tree, data_root)
    try:
        incident = _await_incident_in_log(log, "network_error")
        assert incident["action"], "الإجراء المقترح غائب"
        for entry in _read_log(log):
            if isinstance(entry.get("incident"), dict):
                assert "health" in entry and "status" in entry, (
                    "سطر حادثة كسر عقد الدورة"
                )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def test_supervisor_loop_classifies_awareness_incidents(tmp_path):
    """حوادث الوعي تصل المصنف حتى مع استجابة HTTP سليمة (اعتراض المراجع
    ج4): تغيّر شجرة حقيقي → changes_detected → حادثة سلامة مصنفة بسطر
    الدورة."""
    tree = Path(tempfile.mkdtemp(prefix="repair_aw_tree_"))
    _make_tree(tree)
    data_root = Path(tempfile.mkdtemp(prefix="repair_aw_data_"))
    log = data_root / "supervisor" / "monitor_log.jsonl"
    dead_port = _free_port()
    proc = _spawn_supervisor(f"http://127.0.0.1:{dead_port}", log, tree, data_root)
    try:
        _await_incident_in_log(log, "network_error")
        # تغيير حقيقي في الشجرة → حدث وعي → حادثة سلامة مصنفة
        (tree / "src" / "app.py").write_text("print('tampered')\n", encoding="utf-8")
        incident = _await_incident_in_log(log, "integrity_change")
        assert incident["action"], "إجراء حادثة السلامة غائب"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def _status_app_factory(component_error: str):
    """تطبيق مرجعي أصغر بعقد /status الفعلي: صحة المكونات بصيغة
    get_component_health (last_error) — مسار البيانات الحقيقي الذي يحافظ
    عليه ملخص الحارس. ليس بديل التطبيق الحي — عُدة إثبات المسار المتصل."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 — توقيع المكتبة القياسي
            if self.path == "/health":
                body = json.dumps({"status": "ok"}).encode()
            elif self.path == "/status":
                body = json.dumps({
                    "status": "operational", "version": "test",
                    "components": {
                        "memory": {
                            "status": "error", "error_count": 3,
                            "last_error": component_error,
                            "last_success": None,
                        }
                    },
                    "timestamp": time.time(),
                }).encode()
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # صمت — ليس محور الاختبار
            pass

    return Handler


def test_continuous_path_from_supervisor_event_to_proposal(tmp_path):
    """المسار المتصل (اعتراض المراجع ج4): حدث حارس قائم — خطأ مكوّن يبلغ
    عنه التطبيق في /status (last_error) — يمر كاملًا عبر الحارس الفعلي:
    جلب ← ملخص يحفظ الخطأ ← سطر دورة ← حادثة ← تصنيف ← اقتراح منطبق على
    المكوّن المعزول (رقعة فعلية)، لا ملف حادثة منشأ ولا CLI."""
    tree, data_root, component_src, source_text = _make_repair_fixture(tmp_path)
    log = data_root / "supervisor" / "monitor_log.jsonl"
    # تطبيق مرجعي يبلغ عن خطأ مكوّن استيراد — بعقد /status الفعلي نفسه
    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), _status_app_factory(
        "ModuleNotFoundError: No module named 'predictive'"
    ))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        proc = _spawn_supervisor(
            f"http://127.0.0.1:{port}", log, tree, data_root
        )
        try:
            # الحلقة تصنف خطأ المكوّن المُبلَّغ وتقترح — المسار المتصل كله
            incident = _await_incident_in_log(log, "import_error")
            assert "proposal" in incident, (
                f"الاقتراح لم يصل سطر الدورة: {incident}"
            )
            # الرقعة فعلية في المخزن والسجل يشير إليها وapplied:false
            diff_file = data_root / "proposals" / incident["proposal"]
            assert diff_file.is_file(), "ملف الرقعة غير موجود"
            diff_text = diff_file.read_text(encoding="utf-8")
            assert diff_text.startswith("--- ") and "from backend import predictive" in diff_text
            log_text = (data_root / "proposals" / "proposals_log.jsonl").read_text(
                encoding="utf-8")
            assert incident["proposal"] in log_text
            assert '"applied": false' in log_text
            # لا تطبيق تلقائيًا: المصدر المعزول لم يتغير حرفيًا
            assert component_src.read_text(encoding="utf-8") == source_text
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
    finally:
        server.shutdown()


def test_supervisor_proposes_without_applying(tmp_path):
    """(ج) عبر الحارس الفعلي (--process-incident — وضع إعادة المعالجة):
    مصدر معزول معلوم → وصف + ملف رقعة + سجل؛ والمصدر لم يتغير حرفيًا؛
    والرقعة تُفحص بالتنفيذ على نسخة اختبارية فقط (الأصل يفشل والمرقّع
    يستورد)."""
    import re as _re
    tree, data_root, component_src, source_text = _make_repair_fixture(tmp_path)
    incident_file = data_root / "incident.json"
    incident_file.write_text(json.dumps({
        "id": "1792380000.0:http://127.0.0.1:1",
        "source": "supervisor", "kind": "component_error",
        "error_text": "ModuleNotFoundError: No module named 'predictive'",
    }), encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "backend.supervisor_daemon",
         "--process-incident", str(incident_file),
         "--awareness-root", str(tree)],
        cwd=str(_REPO_ROOT),
        env={**os.environ, "SOVEREIGN_DATA_ROOT": str(data_root)},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        out, err = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        pytest.fail(f"--process-incident لم يكتمل: {err.decode()[:300]}")
    assert proc.returncode == 0, f"فشل المعالجة: {err.decode()[:300]}"
    result = json.loads(out.decode().strip().splitlines()[-1])
    assert result["status"] == "proposed", f"لم يقترح: {result}"
    assert component_src.read_text(encoding="utf-8") == source_text, (
        "المصدر المعزول تغير — تطبيق تلقائي ممنوع"
    )
    diff_file = data_root / "proposals" / result["diff_file"]
    diff_text = diff_file.read_text(encoding="utf-8")
    # فحص الرقعة بالتنفيذ على نسخة اختبارية: الأصل يفشل والمرقّع يستورد
    patched = tmp_path / "patched_copy.py"
    new_text = _restore_from_unified_diff(source_text, diff_text)
    compile(new_text, "<patched>", "exec")
    patched.write_text(new_text, encoding="utf-8")
    original_run = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(tree)!r}); "
         f"exec(open({str(component_src)!r}).read())"],
        capture_output=True, text=True,
    )
    assert original_run.returncode != 0, "الأصل المفروض أنه يفشل بالاستيراد"
    patched_run = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(tree)!r}); "
         f"exec(open({str(patched)!r}).read())"],
        capture_output=True, text=True,
    )
    assert patched_run.returncode == 0, (
        f"المرقّع فشل — الرقعة لا تصلح: {patched_run.stderr[-300:]}"
    )


def _restore_from_unified_diff(original_text: str, diff_text: str) -> str:
    """استرجاع النص الجديد من رقعة unified diff — في الاختبار فقط
    (الإنتاج بلا أي آلية تطبيق). أسطر السياق في الجانبين معًا."""
    lines = diff_text.splitlines()
    hunks = []
    current = None
    for l in lines:
        if l.startswith("@@"):
            current = {"start": int(_re_search(r"@@ -(\d+)", l)),
                       "added": [], "removed": 0}
            hunks.append(current)
        elif current is not None:
            if l.startswith(("--- ", "+++ ")):
                continue
            if l.startswith("+"):
                current["added"].append(l[1:])
            elif l.startswith("-"):
                current["removed"] += 1
            elif l.startswith(" "):
                current["added"].append(l[1:])
                current["removed"] += 1
    original = original_text.splitlines()
    for h in reversed(hunks):
        s = h["start"]
        original[s - 1: s - 1 + h["removed"]] = h["added"]
    return "\n".join(original) + "\n"


def _re_search(pattern: str, text: str) -> int:
    import re
    return int(re.search(pattern, text).group(1))


def test_app_unaffected_during_and_after_repair(tmp_path):
    """(د) التطبيق لا يتأثر: يستجيب أثناء معالجة الحارس لحادثة وبعدها،
    وapp.py وbackend/compat وbackend/Mr.py لم تتغير (بصمات قبل/بعد) ولا
    استيراد للمرحلة ٤ في app.py."""
    port = _free_port()
    data_root = Path(tempfile.mkdtemp(prefix="repair_app_data_"))
    app_proc = _spawn_app(data_root, port)
    tree = Path(tempfile.mkdtemp(prefix="repair_app_tree_"))
    _make_tree(tree)
    mr = _BACKEND_DIR / "Mr.py"
    _compat_files = (
        sorted(p for p in (_BACKEND_DIR / "compat").iterdir() if p.is_file())
        if (_BACKEND_DIR / "compat").is_dir() else []
    )
    before = {
        "app.py": (_BACKEND_DIR / "app.py").read_bytes(),
        "Mr.py": mr.read_bytes() if mr.exists() else b"",
        "compat": [p.read_bytes() for p in _compat_files],
    }
    deadline = time.time() + 60
    up = False
    while time.time() < deadline and not up:
        try:
            up = _get_health(port) == 200
        except Exception:
            time.sleep(0.5)
    assert up, "التطبيق لم يقلع خلال المهلة"
    log = data_root / "supervisor" / "monitor_log.jsonl"
    dead_port = _free_port()
    sup_proc = _spawn_supervisor(f"http://127.0.0.1:{dead_port}", log, tree, data_root)
    try:
        _await_incident_in_log(log, "network_error")
        assert _get_health(port) == 200, "التطبيق توقف أثناء معالجة الحارس"
    finally:
        sup_proc.terminate()
        try:
            sup_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            sup_proc.kill()
            sup_proc.wait(timeout=10)
    assert _get_health(port) == 200, "التطبيق توقف بعد توقف الحارس"
    app_proc.terminate()
    try:
        app_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        app_proc.kill()
        app_proc.wait(timeout=10)
    assert (_BACKEND_DIR / "app.py").read_bytes() == before["app.py"], "app.py تغير"
    assert mr.read_bytes() == before["Mr.py"], "Mr.py تغير"
    if (_BACKEND_DIR / "compat").is_dir():
        after_compat = sorted(
            p for p in (_BACKEND_DIR / "compat").iterdir() if p.is_file()
        )
        assert [p.read_bytes() for p in after_compat] == before["compat"], (
            "backend/compat تغير"
        )
    app_src = (_BACKEND_DIR / "app.py").read_text(encoding="utf-8")
    assert "backend.repair" not in app_src and "import repair" not in app_src, (
        "app.py يستورد المرحلة ٤ — ربط ممنوع"
    )
