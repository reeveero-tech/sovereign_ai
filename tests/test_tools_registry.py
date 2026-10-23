"""R-729 (البند ٣.١ — بأمر المالك): سجل الأدوات الحقيقي — استبدال
runtime-capability-registry.js الزخرفي بسجل backend حقيقي: كل أداة معلنة
باسم/مدخلات/مخرجات/صلاحية، وكل استدعاء يترك أثرًا في السجل السيادي
(حدث TOOL_INVOKED ببصمة النتيجة — لا سر في المخرجات أبدًا).
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))


def _client():
    from fastapi.testclient import TestClient
    from app import app
    return TestClient(app)


def _api_key() -> str:
    return os.environ.get("SOVEREIGN_KEY", "test_master_key_1234567890abcdef")


# -------------------------
# /tools/list — الأدوات الفعلية لا الوهم
# -------------------------

def test_tools_list_returns_real_registered_tools():
    """البند ٣.١: /tools/list يعيد الأدوات الفعلية المسجلة في backend —
    القدرات الحقيقية الموجودة فعلًا (صحة/ذاكرة/قرص/عقل/سيادة)، لا قدرات
    وهمية مزروعة كما كان يفعل runtime-capability-registry.js."""
    with _client() as client:
        r = client.get("/tools/list")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data.get("tools"), list) and data["tools"], (
            "لا أدوات مسجلة — سجل بلا محتوى"
        )
        names = {t["name"] for t in data["tools"]}
        expected = {"health.snapshot", "memory.stats", "disk.status",
                    "brain.status", "sovereignty.score"}
        missing = expected - names
        assert not missing, f"أدوات حقيقية غير مسجلة: {missing}"
        for t in data["tools"]:
            for field in ("name", "description", "inputs", "outputs", "permission"):
                assert field in t, f"أداة {t.get('name')} بلا حقل {field}"
            assert "handler" not in t, "لا يُسرَّب كود المعالج في القائمة"
            assert "api_key" not in str(t).lower(), "لا سر في مخرجات السجل"


def test_tools_invoke_requires_api_key():
    """الاستدعاء أمر مالك — بلا مفتاح صحيح يُرفض (نمط /sovereign/command)."""
    with _client() as client:
        r = client.post("/tools/invoke", json={"tool": "health.snapshot"})
        assert r.status_code == 401, "استدعاء بلا مفتاح API يجب أن يُرفض"
        r = client.post("/tools/invoke", json={
            "tool": "health.snapshot", "api_key": "wrong-key"})
        assert r.status_code == 401, "مفتاح خاطئ يجب أن يُرفض"


def test_tools_invoke_unknown_tool_rejected():
    """أداة غير مسجلة → 404 — لا تنفيذ صامت لما ليس في السجل."""
    with _client() as client:
        r = client.post("/tools/invoke", json={
            "tool": "nonexistent.tool", "api_key": _api_key()})
        assert r.status_code == 404


def test_tools_invoke_health_snapshot_returns_real_data():
    """استدعاء أداة حقيقية يعيد بيانات فعلية من النظام (نفس منطق /health)
    + بصمة النتيجة في الأثر — لا نص مزروع."""
    with _client() as client:
        r = client.post("/tools/invoke", json={
            "tool": "health.snapshot", "api_key": _api_key()})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["tool"] == "health.snapshot"
        result = data["result"]
        assert result.get("status") in ("healthy", "degraded")
        assert "components" in result
        trace = data["trace"]
        assert trace["ledger_event"] == "tool_invoked"
        assert re.fullmatch(r"[0-9a-f]{16}", trace["result_fingerprint"]), (
            "بصمة SHA-256 (16 حرفًا) مطلوبة في الأثر"
        )


# -------------------------
# الأثر السيادي — كل استدعاء يترك حدثًا (معيار الإغلاق للبند ٣.١)
# -------------------------

def test_every_invoke_leaves_sovereign_ledger_trace():
    """معيار إغلاق ٣.١: كل استدعاء يترك أثرًا — حدث tool_invoked في السجل
    السيادي (بصمة النتيجة + المدة + الأداة)، ولا سر في الحدث أبدًا."""
    with _client() as client:
        r = client.post("/tools/invoke", json={
            "tool": "brain.status", "api_key": _api_key()})
        assert r.status_code == 200
        from memory.core import get_core
        core = get_core()
        found = None
        for event in core.iterate_events(reverse=True, limit=20):
            if event.get("type") == "tool_invoked":
                payload = core.get_payload(event)
                if payload.get("tool") == "brain.status" and payload.get("caller") == "owner":
                    found = payload
                    break
        assert found is not None, (
            "لا أثر للاستدعاء في السجل السيادي — البند ٣.١ لم يُنفذ"
        )
        assert found["ok"] is True
        assert "duration_ms" in found and "result_fingerprint" in found
        # لا سر في الحدث أبدًا (المادة ٩): المفتاح لا يظهر في أي مكان
        assert _api_key() not in str(found)


# -------------------------
# الواجهة — استبدال السجل الزخرفي بمستهلك حقيقي
# -------------------------

def test_frontend_tools_registry_module_is_real_consumer():
    """البند ٣.١: وحدة الواجهة tools-registry.js تستهلك /tools/list فعلًا
    (لا نصوص مزروعة) ومحمّلة من index.html، والسجل الزخرفي القديم
    runtime-capability-registry.js أزيل (لا تحميل ولا وجود)."""
    mod = REPO_ROOT / "frontend/js/modules/tools-registry.js"
    assert mod.exists(), "وحدة سجل الأدوات الحية غير موجودة"
    text = mod.read_text(encoding="utf-8")
    assert '"/tools/list"' in text or "'/tools/list'" in text, (
        "الوحدة لا تستهلك نقطة /tools/list الفعلية"
    )
    assert "setInterval" in text, "تحديث دوري مطلوب (ربط حي لا لقطة ثابتة)"
    idx = (REPO_ROOT / "frontend/index.html").read_text(
        encoding="utf-8", errors="ignore")
    assert "js/modules/tools-registry.js" in idx, (
        "tools-registry.js غير محمّلة من index.html"
    )
    assert "runtime-capability-registry.js" not in idx, (
        "السجل الزخرفي القديم ما زال محمّلًا — البند ٣.١ استبدال لا إضافة"
    )
    assert not (REPO_ROOT / "frontend/js/modules/runtime-capability-registry.js").exists(), (
        "runtime-capability-registry.js ما زال موجودًا — ٣.١: استبدال كامل"
    )
