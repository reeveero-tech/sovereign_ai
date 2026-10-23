"""R-734 (البند ٢.٧ — بأمر المالك «تابع»): لمس — إحساس النظام بموارده وأخطائه.

المتبقي في ٢.٧ بعد R-733: الأخطاء لكل مكون (موجودة في /health) والموارد
(لا نقطة لها). يثبت هذا الحارس:
- /system/resources تعيد قياسات حقيقية من نظام التشغيل (لا تقديرات): الذاكرة
  المقيمة تطابق /proc/self/status، والقرص يطابق shutil.disk_usage، والمعالج
  نسبة فعلية بين عينتين (null صريح في أول قراءة لا رقم مختلق).
- لا مسار مطلق ولا سر في الاستجابة (المادة ٩).
- الواجهة تعرض الموارد وأخطاء المكونات حيًا من النقطتين الفعليتين.
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
sys.path.insert(0, str(REPO_ROOT / "backend"))


def _client():
    from fastapi.testclient import TestClient
    from app import app
    return TestClient(app)


def _proc_rss_mb():
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    except OSError:
        return None
    return None


def test_resources_endpoint_returns_real_measurements():
    with _client() as c:
        r = c.get("/system/resources")
        assert r.status_code == 200, "نقطة الموارد غير موجودة"
        d = r.json()
    p = d["process"]
    expected = _proc_rss_mb()
    if expected is not None:
        assert p["rss_source"] == "/proc/self/status"
        assert abs(p["rss_mb"] - expected) / expected < 0.25, (
            f"الذاكرة المعلنة {p['rss_mb']} لا تطابق القياس الفعلي {expected}"
        )
    else:
        assert p["rss_mb"] is None or p["rss_source"] != "/proc/self/status"
    assert isinstance(d["host"]["cpu_count"], int) and d["host"]["cpu_count"] >= 1
    assert p["threads"] >= 1


def test_disk_matches_os_and_hides_absolute_path():
    with _client() as c:
        d = c.get("/system/resources").json()
    disk = d["disk"]
    assert not str(disk["label"]).startswith("/"), "مسار مطلق مكشوف في الاستجابة"
    from app import _resources_disk_path
    usage = shutil.disk_usage(_resources_disk_path())
    assert abs(disk["free_gb"] - usage.free / 1e9) < 0.5
    assert abs(disk["total_gb"] - usage.total / 1e9) < 0.5


def test_cpu_percent_is_measured_between_samples_not_invented():
    import system_resources
    system_resources.reset_cpu_baseline()
    first = system_resources.snapshot()
    assert first["process"]["cpu_percent"] is None, "أول قراءة بلا عينة سابقة يجب أن تكون null"
    assert "عينتين" in first["process"]["cpu_note"]
    end = time.time() + 0.3
    x = 0
    while time.time() < end:
        x += 1
    second = system_resources.snapshot()
    cpu = second["process"]["cpu_percent"]
    assert isinstance(cpu, float) and cpu > 0, f"حمل فعلي ولم يُقس: {cpu}"


def test_no_secrets_in_resources():
    with _client() as c:
        r = c.get("/system/resources")
        assert r.status_code == 200, "النقطة غير موجودة — غياب السر في 404 ليس نجاحًا"
        body = r.text
    key = os.environ.get("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")
    assert key not in body


def test_frontend_renders_resources_and_component_errors():
    js = (FRONTEND / "js/modules/live-health-chart.js").read_text(encoding="utf-8")
    assert "/system/resources" in js, "الواجهة لا تستهلك نقطة الموارد"
    assert "error_count" in js and "last_error" in js, "أخطاء المكونات لا تُعرض"
    assert "Math.random" not in js
    m = json.loads((FRONTEND / "LIVE_BINDINGS.json").read_text(encoding="utf-8"))
    eps = {(b["element"], b["endpoint"]) for b in m["bound"]}
    assert ("live-resources", "GET /system/resources") in eps
    assert ("live-component-errors", "GET /health") in eps
