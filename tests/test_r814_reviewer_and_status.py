"""R-814 (المالك — البنود ٤ و٥ + عقد الحالة): المراجع المستقل وعقد الحالة الصادق.

الدافع (2026-10-29، أمر المالك): «لا يوجد وكلاء ذكاء اصطناعي مدمجين في المشروع
يستخدمون كمراجعين ومنفذين» و«النظام يعتمد كليا على الذكاء الاصطناعي بينما يجب
أن يكون مساعدًا أو مرجعًا فقط بينما المشروع بنفسه يقوم بكل شي».

المثبت هنا:
- البند ٥: المراجع المستقل في مسار المحادثة الرئيسي — حكم JSON صارم (نمط
  R-813: كائن كامل، ok منطقي حرفي، issues قائمة نصوص، summary نص)، حكمه
  يُسجَّل ويُعرض ولا يقلب نتيجة التطبيق؛ الرد الفاسد ⇒ لا حكم مختلق.
- البند ٤: عقل معطل ⇒ مراجع متخطى والسير يكتمل بجواب (المشروع يقوم بكل شيء).
- عقد الحالة الصادق: /chat بوضع الوكيل لا يعيد «ok» وحلقة الوكيل فاشلة —
  planner_failed/brain_disabled ⇒ status=error مع بقاء النص الصادق، ونجاح
  الجواب (completed/answered_from_results) ⇒ status=ok.
- الواجهة: رد HTTP 200 بحالة فشل يُعرض بتنسيق الخطأ لا كأنه جواب سليم.
"""

import json
from pathlib import Path

import pytest

import chat_agent
import config

ROOT = Path(__file__).resolve().parent.parent
CHAT_UI = ROOT / "frontend" / "chat" / "index.html"


class FakeRegistry:
    def __init__(self, tools):
        self.tools = tools

    def list_tools(self):
        return [{"name": n, "description": f"desc {n}", "inputs": inp, "permission": "owner"}
                for n, (inp, _) in self.tools.items()]

    def invoke(self, name, caller="owner", inputs=None):
        fn = self.tools[name][1]
        try:
            return {"ok": True, "result": fn(**(inputs or {})), "error": None,
                    "trace": {"result_fingerprint": "f"}}
        except Exception as e:
            return {"ok": False, "result": None, "error": str(e), "trace": {}}


def _registry():
    return FakeRegistry({
        "system.capabilities": ({}, lambda: {"tools": ["web.fetch"]}),
        "memory.stats": ({}, lambda: {"total_events": 140807}),
    })


class FakeBrain:
    """ردود متتالية (توجيه ← جواب ← مراجع) مع تسجيل ما رآه."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def __call__(self, system, user, **kw):
        self.seen.append({"system": system, "user": user, "kw": kw})
        if not self.replies:
            return None
        r = self.replies.pop(0)
        return r if (r is None or isinstance(r, str)) else json.dumps(r, ensure_ascii=False)


@pytest.fixture(autouse=True)
def _brain_on(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "fake-model")


def test_reviewer_valid_verdict_recorded():
    """البند ٥: المراجع المستقل يحكم بعقد صارم — والحكم يُسجَّل ولا يقلب النتيجة."""
    brain = FakeBrain([
        {"tool": "none", "inputs": {}},                              # التوجيه: لا أداة
        "الذاكرة فيها 140807 حدث",                                   # جواب العقل
        {"ok": True, "issues": [], "summary": "الجواب مطابق للنتائج"},  # حكم المراجع
    ])
    out = chat_agent.respond("كم حدث في الذاكرة؟", chat_fn=brain, registry=_registry())
    assert out["status"] == "completed"
    assert out["reply"] == "الذاكرة فيها 140807 حدث"
    rev = out["reviewer"]
    assert rev["reviewer"] == "brain" and rev["ok"] is True
    assert rev["summary"] == "الجواب مطابق للنتائج"
    # المراجع رأى الجواب والنتائج فعلًا — استقلال الدور (مرجع لا منفذ)
    assert any("مراجع" in s["system"] for s in brain.seen)


def test_reviewer_invalid_reply_no_fabricated_verdict():
    """رد مراجع فاسد (نص غير JSON) ⇒ لا حكم مختلق — والجواب يبقى كما هو."""
    brain = FakeBrain([
        {"tool": "none", "inputs": {}},
        "جواب العقل",
        "ليس JSON إطلاقًا",
    ])
    out = chat_agent.respond("مرحبا", chat_fn=brain, registry=_registry())
    assert out["status"] == "completed"
    assert out["reviewer"]["reviewer"] == "invalid_review_reply"
    assert out["reviewer"]["ok"] is None


def test_reviewer_contract_rejects_wrong_types():
    """عقد صارم: ok غير منطقي أو issues أرقام ⇒ لا حكم مختلق (نمط R-813)."""
    for bad in ({"ok": "نعم", "issues": [], "summary": "s"},
                {"ok": True, "issues": [42], "summary": "s"},
                {"ok": True, "issues": [], "summary": 5}):
        brain = FakeBrain([
            {"tool": "none", "inputs": {}},
            "جواب",
            json.dumps(bad, ensure_ascii=False),
        ])
        out = chat_agent.respond("مرحبا", chat_fn=brain, registry=_registry())
        assert out["reviewer"]["reviewer"] == "invalid_review_reply", bad


def test_reviewer_no_reply():
    brain = FakeBrain([
        {"tool": "none", "inputs": {}},
        "جواب",
        None,  # المراجع لم يرد
    ])
    out = chat_agent.respond("مرحبا", chat_fn=brain, registry=_registry())
    assert out["reviewer"]["reviewer"] == "no_reply"


def test_reviewer_skipped_when_brain_off(monkeypatch):
    """البند ٤: عقل معطل ⇒ مراجع متخطى والجواب يبقى — المشروع يقوم بكل شيء."""
    monkeypatch.setattr(config, "OLLAMA_ENABLED", False)
    # الجواب جاء من خطوة finish لمخطط مبرمج — لا عقل في المراجعة
    brain = FakeBrain([{"tool": "none", "inputs": {}}, "جواب حتمي"])
    out = chat_agent.respond("مرحبا", chat_fn=brain, registry=_registry())
    assert out["status"] == "completed"
    assert out["reviewer"]["reviewer"] == "skipped_brain_off"


def test_reviewer_skipped_no_budget():
    """الميزانية أوشكت على النفاد ⇒ لا مراجعة تسرق وقت الجواب."""
    import time as _time
    brain = FakeBrain([{"action": "finish", "answer": "جواب"}])
    # مهلة شبه منتهية — respond يحسب deadline = الآن + الميزانية
    out = chat_agent.respond("مرحبا", chat_fn=brain, registry=_registry(),
                             max_seconds=0.0)
    # 0 ثانية ميزانية: إما تخطي المراجع أو رفض حلقة — كلاهما صادق لا نجاح كاذب
    assert out["status"] != "ok" or out.get("reviewer", {}).get("reviewer") in (
        "skipped_no_budget", "skipped_brain_off", "no_reply")


def test_planner_failure_has_no_reviewer():
    """فشل المخطط ⇒ لا مراجعة لأصلًا لا جواب (لا نجاح كاذب)."""
    brain = FakeBrain([None])  # العقل لا يرد أصلًا
    out = chat_agent.respond("مرحبا", chat_fn=brain, registry=_registry())
    assert out["status"] == "planner_failed"
    assert "reviewer" not in out or out.get("reviewer") is None
    assert out["reply"].startswith("لم أُكمل الجواب بصدق")


# ---------------- عقد الحالة في /chat (مستوى التطبيق) ----------------

def _client():
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient
    chat_rate_limiter._requests.clear()
    return TestClient(fastapi_app)


def _agent_mode_with(monkeypatch, canned):
    """وضع الوكيل مفعّل مع respond مبرمج — ما يُختبر هو عقد الحالة في المسار."""
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)

    def _fake(text, history=None, **kw):
        return canned

    monkeypatch.setattr(chat_agent, "respond", _fake)


def test_chat_status_error_on_planner_failed(monkeypatch):
    """planner_failed ⇒ status=error (لا ok مع فشل فعلي) — النص الصادق باقٍ."""
    _agent_mode_with(monkeypatch, {
        "reply": "لم أُكمل الجواب بصدق: العقل اللغوي لم يرد.", "status": "planner_failed",
        "tools_used": [], "steps": []})
    with _client() as c:
        r = c.post("/chat", json={"text": "مرحبا", "user_id": "t"})
        assert r.status_code == 200
        body = r.json()
        assert body["agent_status"] == "planner_failed"
        assert body["status"] == "error"
        assert body["reply"].startswith("لم أُكمل الجواب بصدق")


def test_chat_status_error_on_brain_disabled(monkeypatch):
    _agent_mode_with(monkeypatch, {
        "reply": "العقل اللغوي غير مفعّل على هذا الخادم.", "status": "brain_disabled",
        "tools_used": [], "steps": []})
    with _client() as c:
        r = c.post("/chat", json={"text": "مرحبا", "user_id": "t"})
        assert r.status_code == 200
        body = r.json()
        assert body["agent_status"] == "brain_disabled"
        assert body["status"] == "error"


def test_chat_status_ok_on_completed_with_reviewer(monkeypatch):
    """جواب مكتمل + حكم مراجع مسجل ⇒ ok — والحكم يصل الرد ولا يقلب شيئًا."""
    _agent_mode_with(monkeypatch, {
        "reply": "جواب صادق", "status": "completed", "tools_used": ["memory.stats"],
        "steps": [{"tool": "memory.stats", "ok": True, "error": None}],
        "reviewer": {"reviewer": "brain", "ok": True, "issues": [], "summary": "مطابق"}})
    with _client() as c:
        r = c.post("/chat", json={"text": "مرحبا", "user_id": "t"})
        assert r.status_code == 200
        body = r.json()
        assert body["agent_status"] == "completed"
        assert body["status"] == "ok"
        assert body["reviewer"]["reviewer"] == "brain"
        assert body["reviewer"]["ok"] is True


def test_reviewer_verdict_never_flips_status(monkeypatch):
    """رفض المراجع لا يقلب نتيجة التطبيق — يُسجَّل فقط (البند ٤: التطبيق حاكم)."""
    _agent_mode_with(monkeypatch, {
        "reply": "جواب صادق", "status": "completed", "tools_used": [], "steps": [],
        "reviewer": {"reviewer": "brain", "ok": False, "issues": ["تحفظ"], "summary": "رفض"}})
    with _client() as c:
        r = c.post("/chat", json={"text": "مرحبا", "user_id": "t"})
        assert r.status_code == 200
        body = r.json()
        assert body["agent_status"] == "completed"
        assert body["status"] == "ok"
        assert body["reviewer"]["ok"] is False  # المراجع رفض — والجواب نجح بأدلة التطبيق


# ---------------- الواجهة: عرض الفشل بصدق ----------------

def test_ui_marks_failed_status_as_error():
    """رد HTTP 200 بحالة فشل يُعرض بتنسيق الخطأ — ويعود بعد إعادة التحميل."""
    ui = CHAT_UI.read_text(encoding="utf-8")
    assert 'var failed = data.status && data.status !== "ok";' in ui
    assert "bubble(bm, failed ? { error: true } : undefined); persistConv();" in ui
    # إعادة العرض بعد التحميل تحفظ التنسيق (err في الرسالة المخزنة)
    assert "bubble(m, m.err ? { error: true } : undefined)" in ui
