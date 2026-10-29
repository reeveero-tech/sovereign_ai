"""R-814b (تصحيح مراجعة المستشار على R-814): سد الفجوات الوظيفية وصدق الادعاء.

عيوب المراجعة التي صُححت هنا:
- استثناء المراجع كان يمكن أن يُسقط الجواب المكتمل ⇒ حارس استثناء + reviewer_error.
- حكم المراجع لم يكن يُسجَّل في الخبرة فعلًا (مفتاح صامت يُهمل) ⇒ meta.reviewer.
- رفض المراجع لم يكن له أثر ظاهر ⇒ تحفظ المراجع يظهر في الفقاعة ويُحفظ مع الرسالة
  (err/rev يعبران جولة الخادم — الواجهة والخلفية معًا).
- سير التحقق الحي كان فيه فحص نجاح كاذب (rg غائبة داخل if) ⇒ سكربتات فحص
  مستقلة يختبرها pytest على عينات موجبة وسالبة.
- «البند ٤» لم يكن مثبتًا بعمل حقيقي بلا عقل ⇒ اختبار تشغيل حتمي عبر نقطة
  الدخول الحقيقية (سؤال القدرات يُجاب من الجرد الحي بنداء نموذج يرفض).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import chat_agent
import config
import experience

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
CHAT_UI = ROOT / "frontend" / "chat" / "index.html"
WORKFLOW = ROOT / ".github" / "workflows" / "verify-live.yml"


class FakeRegistry:
    def __init__(self, tools):
        self.tools = tools
        self.invoked = []

    def list_tools(self):
        return [{"name": n, "description": f"desc {n}", "inputs": inp, "permission": "owner"}
                for n, (inp, _) in self.tools.items()]

    def invoke(self, name, caller="owner", inputs=None):
        self.invoked.append((name, dict(inputs or {})))
        fn = self.tools[name][1]
        try:
            return {"ok": True, "result": fn(**(inputs or {})), "error": None,
                    "trace": {"result_fingerprint": "f"}}
        except Exception as e:
            return {"ok": False, "result": None, "error": str(e), "trace": {}}


def _registry():
    return FakeRegistry({
        "system.capabilities": ({}, lambda: {"tools": ["web.fetch"], "deferred": []}),
        "memory.stats": ({}, lambda: {"total_events": 140807}),
    })


class FakeBrain:
    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def __call__(self, system, user, **kw):
        self.seen.append({"system": system, "user": user})
        if not self.replies:
            return None
        r = self.replies.pop(0)
        return r if (r is None or isinstance(r, str)) else json.dumps(r, ensure_ascii=False)


class RaisingBrain:
    """عقل يرفض أصلًا — يثبت أن العمل تم بلا أي نداء نموذج."""

    def __init__(self):
        self.seen = []

    def __call__(self, system, user, **kw):
        self.seen.append({"system": system, "user": user})
        raise AssertionError("نداء نموذج ممنوع في هذا الاختبار — العمل حتمي")


@pytest.fixture(autouse=True)
def _brain_on(monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "fake-model")


# ---------------- عيوب المراجع الوظيفية ----------------

def test_reviewer_exception_preserves_answer():
    """استثناء المراجع لا يُسقط الجواب المكتمل — يُعلن reviewer_error صادقًا."""
    class ExplodingReviewerBrain(FakeBrain):
        def __call__(self, system, user, **kw):
            # أول نداءين: توجيه وجواب — الثالث (المراجع) ينفجر
            if len(self.seen) >= 2:
                raise RuntimeError("العقل انفجر في المراجعة")
            return FakeBrain.__call__(self, system, user, **kw)

    brain = ExplodingReviewerBrain([
        {"tool": "none", "inputs": {}},
        "الجواب المكتمل",
    ])
    out = chat_agent.respond("مرحبا", chat_fn=brain, registry=_registry())
    assert out["status"] == "completed"
    assert out["reply"] == "الجواب المكتمل"  # الجواب لم يُسقط
    assert out["reviewer"]["reviewer"] == "reviewer_error"
    assert out["reviewer"]["ok"] is None


def test_reviewer_receives_real_tool_evidence():
    """المراجع يرى أدلة الأداة المنفذة فعلًا لا جوابًا معلقًا في الفراغ.

    علامة الشاهد في نتيجة الأداة فقط (ليست في الجواب المزروع) — ووجودها في
    حمولة المراجع يثبت أنها وصلته من التنفيذ لا من نص الجواب. وهوية النداء
    تُفحص بنيتها: تعليمات مراجعة + حمولة JSON فيها executed_steps بنتائجها.
    """
    MARKER = "SHARED-RESULT-MARKER-R814C"

    class ReviewerBrain(FakeBrain):
        """نداء المراجع يُتعرف عليه بهوية تعليماته (لا بترتيب النداء) — الجواب
        يُعاد مباشرة عندما تصل نداءات التخطيط/الجواب، وحكم المراجع لنداء المراجعة."""

        def __call__(self, system, user, **kw):
            if "مراجع مستقل" in system:
                self.seen.append({"system": system, "user": user})
                return json.dumps({"ok": True, "issues": [],
                                   "summary": "مطابق"}, ensure_ascii=False)
            return FakeBrain.__call__(self, system, user, **kw)

    brain = ReviewerBrain([
        {"tool": "memory.stats", "inputs": {}},     # التوجيه: نفّذ الأداة
        {"tool": "none", "inputs": {}},             # اكتفاء بالنتيجة — لا خطوة أخرى
        "في الذاكرة 140807 حدث",                    # الجواب من نتيجتها (بلا العلامة)
    ])
    reg = FakeRegistry({
        "system.capabilities": ({}, lambda: {"tools": ["memory.stats"], "deferred": []}),
        # العلامة في نتيجة الأداة فقط — الجواب أعلاه لا يحويها
        "memory.stats": ({}, lambda: {"total_events": 140807, "note": MARKER}),
    })
    out = chat_agent.respond("كم حدث الذاكرة؟", chat_fn=brain, registry=reg)
    assert out["status"] in ("completed", "answered_from_results")  # عمل حقيقي مكتمل
    # الأداة نُفذت فعلًا (المنفّذ: التطبيق — البند ٤)
    assert ("memory.stats", {}) in reg.invoked
    # الجواب نفسه لا يحوي العلامة (لم تُزرع في النص)
    assert MARKER not in out["reply"]
    # نداء المراجع: تعليمات مراجعة صريحة (هوية النداء — يُتعرف بها لا بترتيب)
    reviewer_calls = [c for c in brain.seen if "مراجع مستقل" in c["system"]]
    assert len(reviewer_calls) == 1
    reviewer_call = reviewer_calls[0]
    # حمولته JSON بنيوي: هدف + خطوات منفذة بنتائجها + الجواب
    import json as _json
    payload = _json.loads(reviewer_call["user"])
    assert payload["goal"] == "كم حدث الذاكرة؟"
    executed = [s for s in payload["executed_steps"] if s.get("tool") == "memory.stats"]
    assert executed and MARKER in str(executed[0]["result"])  # الدليل وصل من التنفيذ
    # والحكم المسجل هو حكم العقل المدخل نفسه (لا مختلق)
    assert out["reviewer"]["reviewer"] == "brain"
    assert out["reviewer"]["ok"] is True
    assert out["reviewer"]["summary"] == "مطابق"


def test_no_budget_skips_reviewer_without_model_call():
    """مهلة منتهية ⇒ skipped_no_budget وبلا أي نداء عقل إضافي."""
    import time as _time
    brain = FakeBrain([])
    deadline = _time.monotonic() - 100  # انتهى قبل الآن
    verdict = chat_agent._review_answer("هدف", [], "جواب", deadline, chat_fn=brain)
    assert verdict["reviewer"] == "skipped_no_budget"
    assert not brain.seen  # لم يُستهلك أي نداء


def test_reviewer_verdict_persisted_in_experience():
    """حكم المراجع يُسجَّل في الخبرة فعلًا (meta) — لا مفتاح صامت يُهمل."""
    marker = f"فحص خبرة المراجع {id(object())}"
    brain = FakeBrain([
        {"tool": "none", "inputs": {}},
        "جواب فحص",
        {"ok": False, "issues": ["تحفظ اختباري"], "summary": "اعتراض"},
    ])
    out = chat_agent.respond(marker, chat_fn=brain, registry=_registry())
    assert out["reviewer"]["ok"] is False
    recs = experience.get_store().recall(marker, k=3)
    assert recs, "لم تُسجل الخبرة أصلًا"
    saved = next((r for r in recs if (r.get("meta") or {}).get("reviewer")), None)
    assert saved, "حكم المراجع لم يُثبت في الخبرة (meta.reviewer مفقود)"
    assert saved["meta"]["reviewer"]["ok"] is False


def test_rejected_review_visible_in_reply_payload():
    """رفض المراجع لا يُخفى — الحكم يصل الرد فيبني عليه العرض تحفظًا ظاهرًا."""
    brain = FakeBrain([
        {"tool": "none", "inputs": {}},
        "جواب",
        {"ok": False, "issues": ["الجواب لا يعالج الهدف"], "summary": "غير معالج"},
    ])
    out = chat_agent.respond("مرحبا", chat_fn=brain, registry=_registry())
    assert out["status"] == "completed"  # التطبيق حاكم — الجواب قائم بأدلته
    assert out["reviewer"]["ok"] is False  # لكن الرفض مسجل ظاهر لا نجاح مراجعة


# ---------------- البند ٤: عمل حتمي بلا نموذج عبر نقطة الدخول الحقيقية ----------------

def test_capabilities_question_answered_without_model():
    """سؤال القدرات يُجاب من الجرد الحي حتميًا — نداء النموذج مرفوض جملةً.

    (البند ٤: المشروع يقوم بالعمل بنفسه — العقل لم يُلمس أصلًا في هذا المسار.)
    """
    import app as app_mod
    import chat_tools
    from fastapi.testclient import TestClient

    brain = RaisingBrain()
    # المسار الحتمي (الجسر) لا يلمس العقل — ونداء أي نموذج يفشل الاختبار
    monkey = pytest.MonkeyPatch()
    monkey.setattr(app_mod, "_chat_agent_mode", lambda: False, raising=False)
    monkey.setattr("ollama_client.chat", lambda *a, **k: brain(*a, **k))
    try:
        with TestClient(app_mod.app) as c:
            r = c.post("/chat", json={"text": "ما هي قدراتك الحالية؟", "user_id": "t"})
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "ok"
            # الجواب من الجرد الحي — يذكر القدرات وأدواتها بلا نموذج
            assert "قدرات" in body["reply"] or "أدوات" in body["reply"]
            assert body["agent_status"] is None  # مسار قديم حتمي — لا حلقة وكيل
    finally:
        monkey.undo()
    assert not brain.seen  # لم يُلمس العقل إطلاقًا


# ---------------- سير التحقق الحي: عينات موجبة وسالبة (لا نجاح كاذب) ----------------

def _run(script, *args):
    return subprocess.run([sys.executable, str(TOOLS / script), *map(str, args)],
                          capture_output=True, text=True)


def test_root_check_fails_on_forbidden_word(tmp_path):
    bad = tmp_path / "bad.html"
    bad.write_text("<html><body>مرحبًا بك في النظام السيادي</body></html>", encoding="utf-8")
    r = subprocess.run(["bash", str(TOOLS / "live_check_root.sh"), str(bad)],
                      capture_output=True, text=True)
    assert r.returncode == 1, "صفحة تحوي الكلمة الممنوعة يجب أن تفشل الفحص"


def test_root_check_fails_on_empty_page(tmp_path):
    empty = tmp_path / "empty.html"
    empty.write_text("", encoding="utf-8")
    r = subprocess.run(["bash", str(TOOLS / "live_check_root.sh"), str(empty)],
                      capture_output=True, text=True)
    assert r.returncode == 1, "صفحة فارغة يجب أن تفشل الفحص (لا نجاح على الفراغ)"


def test_root_check_passes_on_clean_page(tmp_path):
    good = tmp_path / "good.html"
    good.write_text("<html><body>مساحة العمل</body></html>", encoding="utf-8")
    r = subprocess.run(["bash", str(TOOLS / "live_check_root.sh"), str(good)],
                      capture_output=True, text=True)
    assert r.returncode == 0


def test_health_check_rejects_nested_healthy_without_top_status(tmp_path):
    """healthy متداخل بلا حالة علوية سليمة يُرفض — فحص بنيوي لا بحث نص."""
    f = tmp_path / "h.json"
    f.write_text(json.dumps({"status": "degraded",
                             "components": {"a": {"status": "healthy"}}}), encoding="utf-8")
    r = _run("live_check_health.py", f)
    assert r.returncode == 1


def test_health_check_rejects_unhealthy_component(tmp_path):
    f = tmp_path / "h.json"
    f.write_text(json.dumps({"status": "healthy",
                             "components": {"a": {"status": "unhealthy"}}}), encoding="utf-8")
    r = _run("live_check_health.py", f)
    assert r.returncode == 1


def test_health_check_rejects_malformed(tmp_path):
    f = tmp_path / "h.json"
    f.write_text("ليس JSON", encoding="utf-8")
    r = _run("live_check_health.py", f)
    assert r.returncode == 2  # خلل فحص — لا نجاح صامت


def test_health_check_passes_on_healthy(tmp_path):
    f = tmp_path / "h.json"
    f.write_text(json.dumps({"status": "healthy",
                             "components": {"a": {"status": "healthy"}}}), encoding="utf-8")
    r = _run("live_check_health.py", f)
    assert r.returncode == 0


def test_chat_check_contract_both_ways(tmp_path):
    ok_body = tmp_path / "ok.json"
    ok_body.write_text(json.dumps({"status": "ok", "agent_status": "completed",
                                   "reply": "جاهز"}), encoding="utf-8")
    assert _run("live_check_chat.py", ok_body, "expect-ok").returncode == 0
    assert _run("live_check_chat.py", ok_body, "expect-error").returncode == 1

    err_body = tmp_path / "err.json"
    err_body.write_text(json.dumps({"status": "ok", "agent_status": "planner_failed",
                                    "reply": "فشل"}), encoding="utf-8")
    assert _run("live_check_chat.py", err_body, "expect-error").returncode == 1  # ok مع فشل = انكسار


def test_conversation_check_verifies_err_and_rev_survive(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"messages": [
        {"role": "user", "content": "سؤال الفحص"},
        {"role": "assistant", "content": "جواب الفحص", "err": True, "rev": "تحفظ"}]}), encoding="utf-8")
    assert _run("live_check_conversation.py", f).returncode == 0
    lost = json.dumps({"messages": [
        {"role": "assistant", "content": "جواب الفحص"}]})
    f2 = tmp_path / "c2.json"
    f2.write_text(lost, encoding="utf-8")
    assert _run("live_check_conversation.py", f2).returncode == 1  # ضياع العلامات = فشل


# ---------------- الواجهة: التحفظ يظهر والعلامات تعبر الحفظ ----------------

def test_ui_renders_reviewer_objection_and_persists_marks():
    ui = CHAT_UI.read_text(encoding="utf-8")
    # التحفظ يُعرض في الفقاعة
    assert 'تحفظ المراجع المستقل: " + m.rev' in ui
    # ويُلتقط من الرد
    assert "data.reviewer && data.reviewer.ok === false" in ui
    # والعلامتان تعبران جولة الحفظ (الواجهة ترسلهما والخلفية تحفظهما)
    assert "err: !!m.err, rev: m.rev || null" in ui
    svc = (ROOT / "backend" / "workspace" / "service.py").read_text(encoding="utf-8")
    assert '"err": bool(m.get("err")), "rev": m.get("rev") or None' in svc


def test_workflow_uses_no_bare_grep_or_rg_and_has_owner_job():
    wf = WORKFLOW.read_text(encoding="utf-8")
    # لا أوامر rg خام (درس أول تشغيل) — الفحوص عبر السكربتات المستقلة
    assert "\n          rg " not in wf and "| rg " not in wf
    # مهمة مصادقة المالك تستهلك سرًا منفصلًا (R-814c: KEY_SECRET يغذي CI ولا يُعاد
    # تخصيصه) بلا طباعته أبدًا
    assert "verify-owner" in wf and 'KEY: ${{ secrets.LIVE_OWNER_API_KEY }}' in wf
    assert 'secrets.KEY_SECRET' not in wf  # السر القديم لا يُستهلك في التحقق الحي
    assert 'echo "$KEY"' not in wf  # لا طباعة للسر أبدًا



# ---------------- R-814c: تشديدات المراجعة التاسعة ----------------

def test_root_check_distinguishes_grep_failure_from_clean(tmp_path):
    """فشل grep نفسه (رمز 2) ليس «صفحة نظيفة» — خلل فحص يُعلن لا نجاحًا."""
    import os
    import subprocess
    unreadable = tmp_path / "locked.html"
    unreadable.write_text("صفحة", encoding="utf-8")
    os.chmod(unreadable, 0o000)  # grep يرد 2 (خطأ قراءة) — ليس تطابقًا ولا نظافة
    try:
        r = subprocess.run(["bash", str(TOOLS / "live_check_root.sh"), str(unreadable)],
                           capture_output=True, text=True)
        assert r.returncode == 2, f"فشل grep يجب أن يظهر خلل فحص (2) لا نجاحًا — رد {r.returncode}"
    finally:
        os.chmod(unreadable, 0o644)


def test_chat_check_rejects_ok_with_empty_reply(tmp_path):
    """نجاح بلا جواب غير ذي معنى — الرد جزء من عقد النجاح."""
    f = tmp_path / "ok.json"
    f.write_text(json.dumps({"status": "ok", "agent_status": "completed",
                             "reply": ""}), encoding="utf-8")
    r = _run("live_check_chat.py", f, "expect-ok")
    assert r.returncode == 1, "نجاح بلا reply يجب أن يُرفض"


def test_health_check_rejects_missing_components(tmp_path):
    """/health بلا مكونات ليس نجاحًا ذا معنى — العقد الحي: مكونات بحالات صريحة."""
    f = tmp_path / "h.json"
    f.write_text(json.dumps({"status": "healthy"}), encoding="utf-8")
    assert _run("live_check_health.py", f).returncode == 1
    f2 = tmp_path / "h2.json"
    f2.write_text(json.dumps({"status": "healthy",
                             "components": {"a": {"other": 1}}}), encoding="utf-8")
    assert _run("live_check_health.py", f2).returncode == 1  # مكون بلا status يُرفض


def test_conversation_err_rev_survive_server_roundtrip():
    """جولة حفظ/استعادة عبر التطبيق نفسه (لا ملف مصنوع): err/rev تعبران الخادم.

    (البند من مراجعة المستشار التاسعة: اختبار JSON مصنوعًا لا يثبت الجولة الحقيقية.)
    """
    import app as app_mod
    from fastapi.testclient import TestClient

    import config as _config
    headers = {"X-Sovereign-Key": _config.SOVEREIGN_KEY}
    with TestClient(app_mod.app) as c:
        body = {"title": "جولة فحص R-814c",
                "messages": [
                    {"role": "user", "content": "سؤال الجولة"},
                    {"role": "assistant", "content": "جواب الجولة",
                     "ts": 1, "tools": [], "files": [], "err": True, "rev": "تحفظ الجولة"},
                ], "project_id": None, "model": None}
        r = c.post("/ws/conversations", json=body, headers=headers)
        assert r.status_code in (200, 201), r.text[:200]
        cid = r.json()["id"]
        r2 = c.get(f"/ws/conversations/{cid}", headers=headers)
        assert r2.status_code == 200
        msgs = r2.json()["messages"]
        bot = next(m for m in msgs if m["role"] == "assistant")
        assert bot["err"] is True, "علامة الفشل ضاعت عبر جولة الخادم الحقيقية"
        assert bot["rev"] == "تحفظ الجولة", "تحفظ المراجع ضاع عبر جولة الخادم الحقيقية"


def test_self_review_runs_without_model_via_real_entry():
    """البند ٤ (تكملة الإثبات): التفتيش الذاتي عبر نقطة الدخول الحقيقية /tools/invoke
    مع عقل رافض (أي نداء نموذج يفشل الاختبار) — التطبيق ينفذ بأدواته المسجلة."""
    import app as app_mod
    from fastapi.testclient import TestClient
    import config as _config

    brain = RaisingBrain()
    monkey = pytest.MonkeyPatch()
    monkey.setattr(_config, "OLLAMA_ENABLED", False)  # العقل معطل صراحة
    monkey.setattr("ollama_client.chat", lambda *a, **k: brain(*a, **k))
    try:
        with TestClient(app_mod.app) as c:
            r = c.post("/tools/invoke", json={
                "tool": "system.self_review", "inputs": {},
                "api_key": _config.SOVEREIGN_KEY})
            assert r.status_code == 200, r.text[:200]
            out = r.json()
            assert out.get("ok") is True
            # التنفيذ حتمي بأدوات حقيقية: فحوص المسجل نفذت ونتائجها في الأثر
            checks = out.get("result") or {}
            assert checks.get("workflow") == "self_review"
            assert "checks" in json.dumps(checks) or "reviewer" in json.dumps(checks)
    finally:
        monkey.undo()
    assert not brain.seen  # لم يُلمس النموذج إطلاقًا — التنفيذ حتمي


def test_ui_reviewer_objection_has_fallback_text():
    """رفض المراجع بلا تفصيل (summary/issues فارغتان) لا يختفي — نص افتراضي صريح."""
    ui = CHAT_UI.read_text(encoding="utf-8")
    assert '|| "اعترض المراجع المستقل على هذا الجواب (جاء الحكم بلا تفصيل)"' in ui
