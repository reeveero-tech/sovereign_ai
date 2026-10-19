# -*- coding: utf-8 -*-
"""
المرحلة ٤ (R-695): الربط بالحارس — اختبارات التكامل بعمليات حقيقية.

مواصفة المالك: المصنف والمقترح مربوطان بالحارس (لا بـapp.py) — الحارس
يقرأ، المصنف يصنف، المقترح يقترح، والمالك يُقرر. واعتراض المراجع (تخطيط
R-695): الربط الفعلي من حوادث الحارس نفسها (حلقة المراقبة تصنف أخطاءها
الفعلية — لا بيانات مصطنعة)، و--process-incident لإعادة المعالجة،
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


def _read_log(log_path: Path) -> list:
    if not log_path.exists():
        return []
    return [
        json.loads(l)
        for l in log_path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]


def _spawn_app(data_root: Path, port: int) -> subprocess.Popen:
    """التطبيق عملية حقيقية مستقلة — نفس عزل الإنتاج (نمط R-687/694)."""
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
    """الحارس عملية مستقلة — يصنف حوادثه الفعلية ويقترح (لا التطبيق)."""
    return subprocess.Popen(
        [sys.executable, "-m", "backend.supervisor_daemon",
         "--url", url, "--interval", str(interval),
         "--map-interval", "0.4", "--log", str(log_path),
         "--awareness-root", str(awareness_root)],
        cwd=str(_REPO_ROOT), env={**os.environ, "SOVEREIGN_DATA_ROOT": str(data_root)},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def _get_health(port: int) -> int:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/health", timeout=5
    ) as resp:
        return resp.status


def _await_incident_in_log(log_path: Path, timeout: float = 30.0) -> dict:
    """انتظار سطر دورة يحمل حادثة مصنفة من الحارس الفعلي."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for entry in _read_log(log_path):
            if isinstance(entry.get("incident"), dict) and entry["incident"].get("class"):
                return entry["incident"]
        time.sleep(0.25)
    pytest.fail("الحارس لم يصنف حادثة فعلية في سجل المراقبة خلال المهلة")


def _make_tree(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("print('x')\n", encoding="utf-8")


def test_supervisor_loop_classifies_real_incidents(tmp_path):
    """الربط الفعلي: حلقة الحارس تصنف حوادثها الفعلية — خطأ جلب حقيقي
    (منفذ مغلق — عقد R-687 القائم، لا بيانات مصطنعة) يظهر في سطر الدورة
    بحادثة مصنفة network_error مع الإجراء، والسطر يحمل عقد الدورة كاملًا."""
    tree = Path(tempfile.mkdtemp(prefix="repair_tree_"))
    _make_tree(tree)
    data_root = Path(tempfile.mkdtemp(prefix="repair_data_"))
    log = data_root / "supervisor" / "monitor_log.jsonl"
    dead_port = _free_port()
    proc = _spawn_supervisor(f"http://127.0.0.1:{dead_port}", log, tree, data_root)
    try:
        incident = _await_incident_in_log(log)
        assert incident["class"] == "network_error", (
            f"خطأ جلب حقيقي صُنف خطأً: {incident}"
        )
        assert incident["action"], "الإجراء المقترح غائب"
        # عقد سطر الدورة (R-687) قائم مع مفتاح الحادثة الإضافي
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


def test_supervisor_proposes_without_applying(tmp_path):
    """(ج) عبر الحارس الفعلي (--process-incident): مصدر معزول معلوم → وصف
    + ملف رقعة + سجل؛ والمصدر المعزول والحي لم يتغيرا حرفيًا قبل العملية
    وبعدها؛ والرقعة تُفحص على نسخة اختبارية فقط (تغيير سلوك حقيقي)."""
    tree = Path(tempfile.mkdtemp(prefix="repair_prop_tree_"))
    (tree / "backend" / "predictive").mkdir(parents=True)
    component_src = tree / "backend" / "predictive" / "__init__.py"
    source_text = "import predictive\nimport json\n"
    component_src.write_text(source_text, encoding="utf-8")
    data_root = Path(tempfile.mkdtemp(prefix="repair_prop_data_"))
    loyalty = data_root / "loyalty"
    loyalty.mkdir(parents=True)
    (loyalty / "quarantine_log.jsonl").write_text(
        '{"time": 1.0, "kind": "quarantine", "detail": "خلل", '
        '"component": "predictive"}\n', encoding="utf-8")
    # حادثة استيراد حقيقية الشكل — من صيغة أخطاء الحارس القائمة
    incident_file = data_root / "incident.json"
    incident_file.write_text(json.dumps({
        "id": "1792380000.0:http://127.0.0.1:1",
        "source": "supervisor", "kind": "fetch_error",
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
    # المصدر المعزول لم يتغير حرفيًا — لا تطبيق تلقائي
    assert component_src.read_text(encoding="utf-8") == source_text, (
        "المصدر المعزول تغير — تطبيق تلقائي ممنوع"
    )
    # ملف الرقعة الفعلي + السجل يشير إليه
    proposals = data_root / "proposals"
    diffs = list(proposals.rglob("*.diff")) if proposals.exists() else []
    assert diffs, "ملف الرقعة غير موجود"
    diff_text = diffs[0].read_text(encoding="utf-8")
    assert diff_text.startswith("--- ") and "+++ " in diff_text, (
        "الرقعة ليست unified diff فعلية"
    )
    log_text = (proposals / "proposals_log.jsonl").read_text(encoding="utf-8")
    assert diffs[0].name in log_text, "سجل الاقتراحات لا يشير للرقعة"
    assert '"applied": false' in log_text, "السجل لا يوثق عدم التطبيق"
    # فحص الرقعة على نسخة اختبارية فقط: تطبيق يدوي في الاختبار ينتج الحرس
    patched = tree_parent_check = None
    work = Path(tempfile.mkdtemp(prefix="repair_patch_check_"))
    target = work / "patched.py"
    target.write_text(source_text, encoding="utf-8")
    _apply_diff_manually(target, diff_text)
    patched_text = target.read_text(encoding="utf-8")
    assert "except ImportError" in patched_text and "import predictive" in patched_text


def _apply_diff_manually(target: Path, diff_text: str) -> None:
    """تطبيق يدوي داخل الاختبار فقط (الإنتاج بلا أي آلية تطبيق) — hunk
    موحد بسيط."""
    import re as _re
    lines = diff_text.splitlines()
    hunk = next(i for i, l in enumerate(lines) if l.startswith("@@"))
    added = []
    for l in lines[hunk + 1:]:
        if l.startswith("+"):
            added.append(l[1:])
        elif l.startswith(" "):
            added.append(l[1:])
        elif l.startswith("-"):
            continue
    # أول سطر "-" يحدد موضع البدء من الرأس
    start = int(_re.search(r"@@ -(\d+)", lines[hunk]).group(1))
    original = target.read_text(encoding="utf-8").splitlines()
    new = original[: start - 1] + added + original[start - 1 + len(
        [l for l in lines[hunk + 1:] if l.startswith("-")]
    ):]
    target.write_text("\n".join(new) + "\n", encoding="utf-8")


def test_app_unaffected_during_and_after_repair(tmp_path):
    """(د) التطبيق لا يتأثر: يستجيب أثناء معالجة الحارس لحادثة وبعدها،
    وapp.py وbackend/compat وbackend/Mr.py لم تتغير (بصمات قبل/بعد) ولا
    استيراد للمرحلة ٤ في app.py."""
    port = _free_port()
    data_root = Path(tempfile.mkdtemp(prefix="repair_app_data_"))
    app_proc = _spawn_app(data_root, port)
    tree = Path(tempfile.mkdtemp(prefix="repair_app_tree_"))
    _make_tree(tree)
    # بصمات الملفات المحظورة قبل المعالجة
    forbidden = ["app.py"]
    compat_files = sorted(
        p.name for p in (_BACKEND_DIR / "compat").iterdir() if p.is_file()
    ) if (_BACKEND_DIR / "compat").is_dir() else []
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
    # حادثة تُعالج أثناء عمل التطبيق (حارس حقيقي يصنف خطأ جلب فعليًا)
    log = data_root / "supervisor" / "monitor_log.jsonl"
    dead_port = _free_port()
    sup_proc = _spawn_supervisor(f"http://127.0.0.1:{dead_port}", log, tree, data_root)
    try:
        _await_incident_in_log(log)
        assert _get_health(port) == 200, "التطبيق توقف أثناء معالجة الحارس"
    finally:
        sup_proc.terminate()
        try:
            sup_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            sup_proc.kill()
            sup_proc.wait(timeout=10)
    # بعد توقف الحارس: التطبيق يستمر + الملفات المحظورة لم تتغير
    assert _get_health(port) == 200, "التطبيق توقف بعد توقف الحارس"
    app_proc.terminate()
    try:
        app_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        app_proc.kill()
        app_proc.wait(timeout=10)
    assert (_BACKEND_DIR / "app.py").read_bytes() == before["app.py"], (
        "app.py تغير"
    )
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
