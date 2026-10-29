"""R-789: المحادثة تفهم وتنفذ عبر حلقة الوكيل — لا أجوبة مزروعة.

أمر المالك 2026-10-27: «يمنع منعًا باتًا أن تزرع أجوبة في الكود — يجب أن يستجيب النظام
فعليًا ويعرف ما يوجه له ويترجمه ثم يعيد الإجابة بناءً على الحقيقة».
العقل هنا بديل مبرمج (fake brain) يحاكي قرارات النموذج — ما يُختبر هو أن الرد نص العقل
المبني على نتائج أدوات نُفذت فعلًا، وأن لا نص مكتوب مسبقًا يحل محله.
"""

import json

import pytest


class FakeRegistry:
    def __init__(self, tools):
        self.tools = tools
        self.calls = []

    def list_tools(self):
        return [{"name": n, "description": f"desc {n}", "inputs": inp, "permission": "owner"}
                for n, (inp, _) in self.tools.items()]

    def invoke(self, name, caller="owner", inputs=None):
        self.calls.append((name, caller, dict(inputs or {})))
        fn = self.tools[name][1]
        try:
            return {"ok": True, "result": fn(**(inputs or {})), "error": None,
                    "trace": {"result_fingerprint": "f"}}
        except Exception as e:
            return {"ok": False, "result": None, "error": str(e), "trace": {}}


def _registry():
    return FakeRegistry({
        "system.capabilities": ({}, lambda: {"tools": ["web.fetch", "memory.stats"],
                                             "deferred": ["code_execution"]}),
        "memory.stats": ({}, lambda: {"total_events": 140807}),
        "web.fetch": ({"url": "u"}, lambda url: {"title": "T", "text": "page " + url}),
        "tasks.start": ({"goal": "g"}, lambda goal: {"task_id": "t1"}),
        "agent.run": ({"goal": "g"}, lambda goal: {}),
        "web.search": ({"query": "q"}, lambda query: {"results": []}),
    })


class FakeBrain:
    """يعيد ردودًا متتالية ويسجل ما رآه (للتحقق أن النتائج الحقيقية وصلته)."""

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
def _no_search(monkeypatch):
    import chat_agent
    monkeypatch.setattr(chat_agent, "search_available", lambda: False)


def test_brain_picks_real_tool_and_answers_from_its_result():
    import chat_agent
    reg = _registry()
    brain = FakeBrain([
        {"tool": "memory.stats", "inputs": {}},   # توجيه
        {"tool": "none", "inputs": {}},           # توجيه بعد النتيجة: تكفي
        "في السجل 140807 حدثًا.",                 # جواب نصي من العقل
    ])
    out = chat_agent.respond("كم حدثًا في ذاكرتك؟", registry=reg, chat_fn=brain)
    assert out["reply"] == "في السجل 140807 حدثًا."
    assert out["status"] == "completed" and out["tools_used"] == ["memory.stats"]
    assert reg.calls == [("memory.stats", "chat", {})]
    # النتيجة الحقيقية وصلت العقل قبل جوابه
    assert "140807" in brain.seen[2]["user"]
    # مرحلة التوجيه مقيدة بمخطط: الأدوات المسموحة + none فقط
    enum = brain.seen[0]["kw"]["json_schema"]["properties"]["tool"]["enum"]
    assert "none" in enum and "tasks.start" not in enum and "agent.run" not in enum
    # الفهرس في تعليمات النظام (بادئة ثابتة)، والرسالة في رسالة المستخدم
    assert "memory.stats" in brain.seen[0]["system"]
    assert "كم حدثًا" in brain.seen[0]["user"]


def test_general_question_answered_by_brain_without_tools():
    import chat_agent
    reg = _registry()
    out = chat_agent.respond("اكتب بيت شعر عن البحر", registry=reg,
                             chat_fn=FakeBrain([{"tool": "none", "inputs": {}}, "بيت من العقل"]))
    assert out["reply"] == "بيت من العقل" and reg.calls == []


def test_public_chat_cannot_run_action_tools():
    import chat_agent
    reg = _registry()
    brain = FakeBrain([{"tool": "tasks.start", "inputs": {"goal": "x"}}] * 3)
    out = chat_agent.respond("ابدأ مهمة", registry=reg, chat_fn=brain, owner=False)
    assert reg.calls == [], "non-owner chat must never invoke an action tool"
    assert out["reply"].startswith("لم أُكمل الجواب بصدق")
    assert "tasks.start" not in brain.seen[0]["system"]


def test_owner_key_unlocks_action_tools_but_never_agent_run():
    import chat_agent
    reg = _registry()
    names = chat_agent.allowed_tools(reg, owner=True)
    assert "tasks.start" in names and "agent.run" not in names
    brain = FakeBrain([{"tool": "tasks.start", "inputs": {"goal": "x"}},
                       {"tool": "none", "inputs": {}}, "بدأت المهمة t1"])
    out = chat_agent.respond("ابدأ مهمة", registry=reg, chat_fn=brain, owner=True)
    assert reg.calls == [("tasks.start", "chat", {"goal": "x"})]
    assert out["reply"] == "بدأت المهمة t1"


def test_search_tool_hidden_when_no_provider():
    import chat_agent
    assert "web.search" not in chat_agent.allowed_tools(_registry(), owner=True)
    assert "web.search" not in chat_agent.allowed_tools(_registry(), owner=False)


def test_brain_failure_is_reported_honestly_not_templated():
    import chat_agent
    out = chat_agent.respond("مرحبا", registry=_registry(), chat_fn=FakeBrain([None]))
    assert out["status"] == "planner_failed"
    assert out["reply"].startswith("لم أُكمل الجواب بصدق")
    assert "العقل اللغوي" in out["reply"]


def test_budget_exhausted_after_results_brain_answers_from_them(monkeypatch):
    import chat_agent
    monkeypatch.setattr(chat_agent, "MAX_STEPS", 1)
    # R-814: قراءة الويب معطلة بعلم المالك لا تُعرض للعقل — الاختبار يستخدم
    # web.fetch كمثال أداة؛ نحاكي توفرها ليبقى الاختبار عن الميزانية لا عن الإخفاء
    monkeypatch.setattr(chat_agent, "web_fetch_available", lambda: True)
    reg = _registry()
    brain = FakeBrain([{"tool": "web.fetch", "inputs": {"url": "https://x"}},
                       "الصفحة عنوانها T."])
    out = chat_agent.respond("ماذا في https://x", registry=reg, chat_fn=brain)
    assert out["status"] == "answered_from_results" and out["reply"] == "الصفحة عنوانها T."
    assert "page https://x" in brain.seen[1]["user"]


def test_brain_disabled_says_so():
    import chat_agent
    if chat_agent.brain_enabled():
        pytest.skip("brain enabled in this environment")
    out = chat_agent.respond("مرحبا", registry=_registry())
    assert out["status"] == "brain_disabled"


def test_chat_endpoint_uses_agent_not_planted_capabilities_reply(monkeypatch):
    """RED على R-788a: «ما هي قدراتك» كان يُجاب بنص حتمي من chat_tools.capabilities_reply."""
    import app as app_mod
    import chat_agent
    import ollama_client
    from fastapi.testclient import TestClient
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
    brain = FakeBrain([{"tool": "system.capabilities", "inputs": {}},
                       {"tool": "none", "inputs": {}}, "جواب العقل من الجرد الحي"])
    monkeypatch.setattr(ollama_client, "chat", brain)
    with TestClient(app_mod.app) as c:
        r = c.post("/chat", json={"text": "ما هي قدراتك؟"})
    body = r.json()
    assert r.status_code == 200
    assert body["reply"] == "جواب العقل من الجرد الحي"
    assert body["tools_used"] == ["system.capabilities"]
    assert body["agent_status"] == "completed"
    # النتيجة الحقيقية للأداة (الجرد) وصلت العقل
    assert "levels" in brain.seen[2]["user"] or "tools" in brain.seen[2]["user"]


def test_github_repo_tool_registered_and_parses_url(monkeypatch):
    import app as app_mod  # noqa: F401
    import chat_tools
    from tool_registry import get_registry
    names = {t["name"] for t in get_registry().list_tools()}
    assert {"github.repo", "system.capabilities"} <= names
    seen = {}
    monkeypatch.setattr(chat_tools, "github_context",
                        lambda o, r: seen.setdefault("x", (o, r)) and "ok")
    assert app_mod._github_repo_tool("https://github.com/reeveero-tech/sovereign_ai") == "ok"
    assert seen["x"] == ("reeveero-tech", "sovereign_ai")
    with pytest.raises(ValueError):
        app_mod._github_repo_tool("not a repo")


def test_chat_endpoint_passes_history_to_brain(monkeypatch):
    import app as app_mod
    import chat_agent
    import ollama_client
    from fastapi.testclient import TestClient
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
    brain = FakeBrain([{"tool": "none", "inputs": {}}, "نعم، تحدثنا عن الذاكرة"])
    monkeypatch.setattr(ollama_client, "chat", brain)
    hist = [{"role": "user", "content": "حدثني عن الذاكرة"},
            {"role": "assistant", "content": "الذاكرة دائمة وموقعة"}]
    with TestClient(app_mod.app) as c:
        r = c.post("/chat", json={"text": "هل تذكر موضوعنا؟", "history": hist})
    assert r.json()["reply"] == "نعم، تحدثنا عن الذاكرة"
    user = json.loads(brain.seen[0]["user"])
    assert [h["content"] for h in user["conversation"]] == ["حدثني عن الذاكرة", "الذاكرة دائمة وموقعة"]


def test_owner_key_checked_by_endpoint(monkeypatch):
    import app as app_mod
    import chat_agent
    import ollama_client
    from fastapi.testclient import TestClient
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
    seen = {}
    real = chat_agent.respond

    def spy(text, history=None, **kw):
        seen["owner"] = kw.get("owner")
        return {"reply": "x", "status": "completed", "tools_used": [], "steps": []}

    monkeypatch.setattr(chat_agent, "respond", spy)
    with TestClient(app_mod.app) as c:
        c.post("/chat", json={"text": "مرحبا", "api_key": "wrong-key"})
    assert seen["owner"] is False
    assert real is not spy


def test_repeating_same_tool_call_goes_to_answer_not_loop():
    import chat_agent
    reg = _registry()
    brain = FakeBrain([{"tool": "memory.stats", "inputs": {}},
                       {"tool": "memory.stats", "inputs": {}},  # تكرار ⇒ يُعامل كاكتفاء
                       "140807 حدثًا"])
    out = chat_agent.respond("كم حدثًا؟", registry=reg, chat_fn=brain)
    assert out["reply"] == "140807 حدثًا" and len(reg.calls) == 1


def test_answer_stage_is_free_text_not_json():
    import chat_agent
    brain = FakeBrain([{"tool": "none", "inputs": {}}, "طوكيو"])
    chat_agent.respond("ما عاصمة اليابان؟", registry=_registry(), chat_fn=brain)
    assert brain.seen[0]["kw"].get("json_mode") is True
    assert not brain.seen[1]["kw"].get("json_mode") and "json_schema" not in brain.seen[1]["kw"]


def test_github_repo_accepts_repo_alias(monkeypatch):
    import app as app_mod
    import chat_tools
    monkeypatch.setattr(chat_tools, "github_context", lambda o, r: f"{o}/{r}")
    assert app_mod._github_repo_tool(repo="reeveero-tech/sovereign_ai") == "reeveero-tech/sovereign_ai"


def test_compact_is_generic_and_drops_empty_values():
    import chat_agent
    txt = chat_agent._compact({"capabilities": [
        {"id": "brain", "level": "enabled", "flag": None},
        {"id": "web_tools", "level": "implemented_disabled", "note": ""}],
        "summary": {"enabled": 1}, "empty": []})
    assert "capabilities[0]: id=brain، level=enabled" in txt
    assert "capabilities[1]: id=web_tools، level=implemented_disabled" in txt
    assert "summary: enabled=1" in txt
    assert "None" not in txt and "empty" not in txt
    assert len(chat_agent._compact({"x": "a" * 5000}, 100)) < 200
