# -*- coding: utf-8 -*-
"""
الفصل بين العمليات — R-689 (اعتراض المراجع ج2 على R-688)

الاختبار الفاصل الذي طلبه المراجع: «شغّل التطبيق والكاتب في عمليتين
منفصلتين، وافشل كتابة عزل مكوّن في الكاتب، ثم اطلب ذلك المكوّن ومكوّنًا
آخر من التطبيق. تحقق من النتيجة الفعلية».

النتيجة المعمارية: احتياط الذاكرة لا يعبر العمليات (ذاكرة خاصة بالعملية) —
لذلك أُضيفت قناتا إنفاذ تعبران العمليات فعلًا:
١) فحص صحة قناة الكتابة في المدخل (TTL): الكاتب فشل بسبب مجلد للقراءة فقط
   ← التطبيق يكتشف القناة غير قابلة للكتابة ← إغلاق على مسارات المكونات
   بخطأ محدد (quarantine_log_unwritable) — لا سماح صامت.
٢) فشل صريح لعملية العزل نفسها (Mr.quarantine يعيد False + انتهاك مسجل
   quarantine_persistence_failed) — الكاتب لا يعلن نجاحًا كاذبًا.
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

# فحص الصحة بلا نافذة TTL — القرار فوري في الاختبار
_PROBE_TTL_ENV = {"SOVEREIGN_BREAKER_PROBE_TTL": "0"}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _spawn_app(data_root: Path, port: int) -> subprocess.Popen:
    env = dict(os.environ)
    env["SOVEREIGN_KEY"] = "test_master_key_1234567890abcdef"
    env["SOVEREIGN_DATA_ROOT"] = str(data_root)
    env["SOVEREIGN_DISABLE_BACKGROUND_THREADS"] = "1"
    env.update(_PROBE_TTL_ENV)
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(_BACKEND_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def _writer_quarantine_fails(data_root: Path, component: str) -> bool:
    """الكاتب في عملية منفصلة: عزل مكوّن — يعيد فشل التوثيق (False)."""
    script = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(_REPO_ROOT)!r})\n"
        "from backend.loyalty_log import append_entry\n"
        f"ok = append_entry('quarantine', 'عزل عبر كاتب منفصل', component={component!r})\n"
        "print('WRITER_RESULT:' + json.dumps({'ok': ok}))\n"
    )
    env = dict(os.environ)
    env["SOVEREIGN_DATA_ROOT"] = str(data_root)
    result = subprocess.run(
        [sys.executable, "-u", "-c", script],
        capture_output=True, text=True, cwd=str(_REPO_ROOT), timeout=60, env=env,
    )
    payload = None
    for line in result.stdout.splitlines():
        if line.startswith("WRITER_RESULT:"):
            payload = json.loads(line[len("WRITER_RESULT:"):])
    assert payload is not None, f"الكاتب لم يُخرج نتيجة: {result.stderr[-300:]}"
    return payload["ok"]


def _get(port: int, path: str):
    import urllib.request
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}{path}", timeout=5
        ) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body[:200]}


@pytest.fixture
def live_app_with_broken_channel():
    """تطبيق حي على جذر معزول + قناة السجل معطلة (المجلد للقراءة فقط) —
    الكاتب المنفصل سيفشل في التوثيق، والتطبيق يجب أن يكتشف ذلك."""
    port = _free_port()
    data_root = Path(tempfile.mkdtemp(prefix="crossproc_root_"))
    loyalty_dir = data_root / "loyalty"
    loyalty_dir.mkdir(parents=True)
    # القناة مكسورة من البداية: مجلد loyalty للقراءة فقط
    os.chmod(loyalty_dir, 0o500)
    app_proc = _spawn_app(data_root, port)
    try:
        yield port, data_root, loyalty_dir
    finally:
        os.chmod(loyalty_dir, 0o700)
        app_proc.terminate()
        try:
            app_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app_proc.kill()
            app_proc.wait(timeout=10)


def _wait_http_ok(port: int, timeout: float = 60.0) -> bool:
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


def test_cross_process_write_failure_enforced(live_app_with_broken_channel):
    """الاختبار الفاصل: كاتب منفصل يفشل توثيق عزل مكوّن (القناة معطلة) —
    التطبيق لا يسمح صامتًا: مسارات المكونات تُغلق بخطأ محدد، والتطبيق حي
    (المسارات غير المكوّنية تعمل)."""
    port, data_root, loyalty_dir = live_app_with_broken_channel
    assert _wait_http_ok(port), "التطبيق لم يقلع خلال المهلة"
    # الكاتب (عملية منفصلة) يحاول عزل predictive — التوثيف يفشل صراحة
    persisted = _writer_quarantine_fails(data_root, "predictive")
    assert persisted is False, (
        "الكاتب نجح في التوثيق رغم القناة المعطلة — الاختبار لا يختبر شيئًا"
    )
    # الطلب للمكوّن المعزول: لا سماح صامت — إغلاق بخطأ محدد
    st, body = _get(port, "/components/predictive")
    assert st == 503, (
        f"النتيجة الفعلية المطلوبة: رفض لا سماح صامت — أعيد {st}: {body}"
    )
    assert body.get("error") == "quarantine_log_unwritable", body
    # المكوّن الآخر: القناة معطولة = الحالة غير قابلة للإثبات — إغلاق موثق
    # (لا سماح)، والقرار معلن في التقرير الجنائي: قناة مكسورة = إغلاق
    st2, body2 = _get(port, "/components/memory")
    assert st2 == 503 and body2.get("error") == "quarantine_log_unwritable", (
        f"قناة معطولة = حالة غير قابلة للإثبات لكل المكونات — {st2}: {body2}"
    )
    # التطبيق حي: المسارات غير المكوّنية تعمل
    st3, health = _get(port, "/health")
    assert st3 == 200 and health.get("status") in ("healthy", "degraded"), (
        f"التطبيق يجب أن يبقى حيًا — {st3}: {health}"
    )


def test_cross_process_quarantine_enforced(live_app_with_broken_channel):
    """التحقق الإيجابي للقناة عبر العمليات: عند نجاح التوثيف (قناة سليمة)،
    الكاتب المنفصل يثبت العزل والتطبيق (عملية أخرى) يرى العزل فعلًا."""
    port, data_root, loyalty_dir = live_app_with_broken_channel
    assert _wait_http_ok(port), "التطبيق لم يقلع خلال المهلة"
    # إصلاح القناة (الكاتب سينجح) — ثم إعادتها معطلة بعد التوثيق لا تُسقط
    # العزل المثبت (الحالة تُقرأ من الملف؛ المجلد r-x يسمح بالقراءة)
    os.chmod(loyalty_dir, 0o700)
    try:
        persisted = _writer_quarantine_fails(data_root, "simulation")
        assert persisted is True, "التوثيق يجب أن ينجح هنا (القناة سليمة)"
    finally:
        os.chmod(loyalty_dir, 0o500)  # المجلد للقراءة فقط — القراءة ممكنة
    # التطبيق (عملية أخرى) يرى العزل من الملف — الإنفاذ عبر العمليات فعلًا
    st, body = _get(port, "/components/simulation")
    assert st == 503 and body.get("error") == "component_quarantined", (
        f"العزل الموثق عبر كاتب منفصل غير مفروض على التطبيق: {st} {body}"
    )
