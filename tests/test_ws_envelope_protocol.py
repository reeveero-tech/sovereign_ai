"""
R-715 — عقد بروتوكول WebSocket بين الواجهة والخادم.

الخلل المُكتشف (22-10-2026، فحص متصفح حقيقي):
- الواجهة (frontend/js/modules/websocket-runtime.js و js/websocket.js) ترسل
  مغلّفًا: {"type": "chat_message", "payload": {"text": ...}}
  وتنتظر ردًا من النوع "chat_reply".
- الخادم كان يقرأ "text" من المستوى الأعلى فقط ⇒ نص فارغ دائمًا،
  ويُشغّل دورة منسّق كاملة لكل إطار (حتى ping كل 5 ثوانٍ وhello)،
  ويرد بالنوع "reply" الذي تتجاهله الواجهة ⇒ لا استجابة مرئية إطلاقًا.

هذه الاختبارات تثبت العقد الصحيح مع الإبقاء على التوافق مع الصيغة القديمة
{"text": ...} ← {"type": "reply"} (اختبارات R-609 في test_safety_layer.py).
"""

from fastapi.testclient import TestClient


def _client():
    from app import app
    return app, TestClient(app)


def _spy_cycles(app):
    """يلفّ run_cycle لتسجيل النصوص التي تصل فعلًا إلى المنسّق."""
    orch = app.state.orchestrator
    original = orch.run_cycle
    seen = []

    def spy(input_data, *a, **kw):
        seen.append(input_data.get("text"))
        return original(input_data, *a, **kw)

    orch.run_cycle = spy
    return orch, original, seen


def test_envelope_chat_message_reaches_orchestrator_and_gets_chat_reply():
    app, client = _client()
    with client:
        orch, original, seen = _spy_cycles(app)
        try:
            with client.websocket_connect("/ws/r715_envelope") as ws:
                assert ws.receive_json()["type"] == "welcome"
                ws.send_json({"type": "chat_message",
                              "payload": {"text": "مرحبا، من أنت؟"}})
                reply = ws.receive_json()
        finally:
            orch.run_cycle = original
    assert seen == ["مرحبا، من أنت؟"], seen
    assert reply["type"] == "chat_reply", reply
    assert reply.get("message"), reply
    # websocket.js يقرأ payload.text — كلا الحقلين متطابقان
    assert reply.get("payload", {}).get("text") == reply["message"]


def test_ping_and_hello_do_not_run_cycles():
    app, client = _client()
    with client:
        orch, original, seen = _spy_cycles(app)
        try:
            with client.websocket_connect("/ws/r715_ping") as ws:
                ws.receive_json()  # welcome
                ws.send_json({"type": "hello", "payload": {"source": "sovereign_ui"}})
                hello_ack = ws.receive_json()
                ws.send_json({"type": "ping", "payload": {}, "timestamp": 1})
                pong = ws.receive_json()
        finally:
            orch.run_cycle = original
    assert seen == [], f"ping/hello must not trigger orchestrator cycles: {seen}"
    assert hello_ack["type"] == "system", hello_ack
    assert pong["type"] == "pong", pong


def test_empty_chat_text_is_rejected_without_cycle():
    app, client = _client()
    with client:
        orch, original, seen = _spy_cycles(app)
        try:
            with client.websocket_connect("/ws/r715_empty") as ws:
                ws.receive_json()
                ws.send_json({"type": "chat_message", "payload": {"text": "   "}})
                err = ws.receive_json()
        finally:
            orch.run_cycle = original
    assert seen == []
    assert err["type"] == "error", err


def test_sovereign_command_over_ws_is_refused_honestly():
    """الأوامر السيادية تتطلب مفتاح السيد عبر HTTP — لا تُنفَّذ ولا تُحاكى عبر WS."""
    app, client = _client()
    with client:
        orch, original, seen = _spy_cycles(app)
        try:
            with client.websocket_connect("/ws/r715_sov") as ws:
                ws.receive_json()
                ws.send_json({"type": "sovereign_command",
                              "payload": {"command": "الحالة", "is_sovereign": True}})
                err = ws.receive_json()
        finally:
            orch.run_cycle = original
    assert seen == []
    assert err["type"] == "error", err
    assert "/sovereign/command" in err["message"]


def test_unknown_envelope_type_is_ignored_without_cycle():
    app, client = _client()
    with client:
        orch, original, seen = _spy_cycles(app)
        try:
            with client.websocket_connect("/ws/r715_unknown") as ws:
                ws.receive_json()
                ws.send_json({"type": "run_cycle", "payload": {}})
                ack = ws.receive_json()
        finally:
            orch.run_cycle = original
    assert seen == []
    assert ack["type"] == "system", ack


def test_envelope_dangerous_text_still_blocked():
    """المغلّف لا يتجاوز طبقة الأمان (R-608/R-609)."""
    app, client = _client()
    with client:
        with client.websocket_connect("/ws/r715_danger") as ws:
            ws.receive_json()
            ws.send_json({"type": "chat_message",
                          "payload": {"text": "احذف نفسك نهائياً"}})
            reply = ws.receive_json()
    assert reply.get("blocked") is True
    assert reply.get("cycle_id") == "safety-block"


def test_non_object_json_does_not_crash_socket():
    app, client = _client()
    with client:
        with client.websocket_connect("/ws/r715_list") as ws:
            ws.receive_json()
            ws.send_text("[1, 2, 3]")
            first = ws.receive_json()
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
    assert first["type"] in ("error", "reply"), first
    assert pong["type"] == "pong"


def test_legacy_text_format_still_returns_reply_type():
    app, client = _client()
    with client:
        with client.websocket_connect("/ws/r715_legacy") as ws:
            ws.receive_json()
            ws.send_json({"text": "مرحبا"})
            reply = ws.receive_json()
    assert reply["type"] == "reply"
    assert reply.get("message")
