"""R-822: العقل مفعّل لكنه غير قابل للوصول (خادم Ollama على شبكة محلية لا يصلها السحاب)
⇒ المحادثة لا تعيد «لم أُكمل الجواب بصدق: ConnectTimeout» بل تجيب عبر الجسر الحتمي
(أدوات حقيقية) وتعلن agent_status=brain_unreachable_fallback بصدق.
"""
import chat_agent
import chat_tools
import ollama_client


def _client():
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient
    chat_rate_limiter._requests.clear()
    return TestClient(fastapi_app)


def _fake_gather(text, caps):
    return {"context": "", "tools_used": ["github.repo"],
            "direct_reply": "قراءة حقيقية للمستودع: README …"}


def test_planner_failed_with_open_latch_falls_back_to_bridge(monkeypatch):
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
    state = {"open": False}

    def _fake_respond(text, history=None, **kw):
        state["open"] = True  # فشل اتصال حقيقي يفتح المزلاج
        return {"reply": "لم أُكمل الجواب بصدق: ConnectTimeout", "status": "planner_failed",
                "tools_used": [], "steps": []}

    monkeypatch.setattr(chat_agent, "respond", _fake_respond)
    monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: state["open"])
    monkeypatch.setattr(chat_tools, "gather", _fake_gather)
    with _client() as c:
        body = c.post("/chat", json={"text": "راجع https://github.com/a/b", "user_id": "t"}).json()
    assert body["agent_status"] == "brain_unreachable_fallback"
    assert body["status"] == "ok"
    assert body["tools_used"] == ["github.repo"]
    assert "ConnectTimeout" not in body["reply"]


def test_open_latch_skips_agent_entirely(monkeypatch):
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)

    def _boom(*a, **k):
        raise AssertionError("وضع الوكيل لا يُجرَّب والمزلاج مفتوح")

    monkeypatch.setattr(chat_agent, "respond", _boom)
    monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: True)
    monkeypatch.setattr(chat_tools, "gather", _fake_gather)
    with _client() as c:
        body = c.post("/chat", json={"text": "راجع https://github.com/a/b", "user_id": "t"}).json()
    assert body["agent_status"] == "brain_unreachable_fallback"
    assert body["reply"].startswith("قراءة حقيقية")


def test_planner_failed_without_latch_stays_honest_error(monkeypatch):
    monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
    monkeypatch.setattr(chat_agent, "respond", lambda *a, **k: {
        "reply": "لم أُكمل الجواب بصدق: العقل اللغوي لم يرد.", "status": "planner_failed",
        "tools_used": [], "steps": []})
    monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: False)
    with _client() as c:
        body = c.post("/chat", json={"text": "مرحبا", "user_id": "t"}).json()
    assert body["agent_status"] == "planner_failed"
    assert body["status"] == "error"


def test_template_header_says_unreachable_not_timeout(monkeypatch):
    import sovereign_response
    monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: True)
    monkeypatch.setattr(sovereign_response, "_llm_reply", lambda *a, **k: None)
    out = sovereign_response.build_reply("question", "راجع", tool_context="بيانات حقيقية")
    assert "غير قابل للوصول" in out and out.endswith("بيانات حقيقية")
