# -*- coding: utf-8 -*-
"""R-834: لا فقدان سياق في المحادثة الوكيلة — درسان من محادثة المالك الحية.

الخلفية (محادثة المستودع 2026-11-02 على الإنتاج): سأل المالك عن مستودع
GitHub فأجابت الأدوات، ثم «هل هو جاهز للانتاج ؟» ففقد السؤال سياقه كليًا:
- المحلل الحتمي لم يحل الضمير المستقل «هو» (يحل الضمائر المتصلة فقط)،
  وentity_of استخرج من «المشروع المرفق <الرابط>» كيانًا غريبًا («معلومات
  كامله») لا الرابط نفسه.
- مسار الوكيل في /chat كان يمرر النص الخام لا السؤال المحلول (الجسر والبحث
  العالمي يريان المحلول — الوكيل لا).
- جولة الوكيل نفسها استُنفدت ميزانيتها (budget_exhausted بعد 176ث و3 أدوات)
  لأن كل نداء تخطيط سحابي ينتظر حد معدل المزود (~45ث) والميزانية 150ث.

هذه الاختبارات تثبت:
1. محلل السياق: رابط/مستودع هو الكيان، والضمير المستقل يُحل إليه، و«ما هو/من
   هو» لا يُمس (حارس)، والضمير المتصل يظل يعمل.
2. مسار الوكيل في /chat يرى السؤال المحلول القائم بذاته لا النص الخام.
3. ميزانية المحادثة الوكيلة تتسع للخطوات حين يخطط السحابي (مزلاج مفتوح).
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

import chat_agent  # noqa: E402
import context_resolver  # noqa: E402
import ollama_client  # noqa: E402


def _client():
    from app import app as fastapi_app, chat_rate_limiter
    from fastapi.testclient import TestClient
    chat_rate_limiter._requests.clear()
    return TestClient(fastapi_app)


_REPO_TURN = {"role": "user",
             "content": "اريد معلومات كامله عن المشروع المرفق https://github.com/vooovg-ui/AMOS-Fedration"}


class TestResolverRepoPronoun:
    """الكيان رابط المستودع والضمير المستقل يحل إليه — حالة المحادثة الحية."""

    def test_url_is_the_entity(self):
        """رابط/مستودع في الرسالة هو الكيان حرفيًا — لا «معلومات كامله»."""
        ent = context_resolver.entity_of(_REPO_TURN["content"])
        assert "github.com/vooovg-ui/AMOS-Fedration" in ent

    def test_bare_pronoun_resolves_to_repo(self):
        """«هل هو جاهز للانتاج ؟» بعد سؤال المستودع ⇒ الكيان في السؤال القائم بذاته."""
        r = context_resolver.resolve("هل هو جاهز للانتاج ؟", [_REPO_TURN])
        assert r["followup"] is True and r["kind"] == "pronoun"
        assert "github.com/vooovg-ui/AMOS-Fedration" in r["standalone"]

    def test_ma_hu_guard(self):
        """«ما هو X» صيغة سؤال لا إشارة كيان — لا استبدال (حارس ضد التخريب)."""
        r = context_resolver.resolve("ما هو البحث العميق", [_REPO_TURN])
        assert r["kind"] == "none" and r["standalone"] == "ما هو البحث العميق"

    def test_no_history_no_change(self):
        """بلا سياق سابق لا تخمين — الرسالة كما هي حرفيًا (عقد المحلل)."""
        r = context_resolver.resolve("هل هو جاهز للانتاج ؟", [])
        assert r["kind"] == "none" and r["followup"] is False

    def test_attached_pronoun_still_works(self):
        """الضمير المتصل القديم يظل يعمل — لا انحدار في القاعدة الأصلية."""
        r = context_resolver.resolve("وكم عدد سكانها",
                                    [{"role": "user", "content": "ما عاصمة اليابان"}])
        assert r["kind"] == "pronoun" and "اليابان" in r["standalone"]


class TestAgentSeesResolvedQuestion:
    """مسار الوكيل في /chat يرى السؤال المحلول — لا نصًا خامًا بلا كيانه."""

    def test_agent_receives_standalone_followup(self, monkeypatch):
        monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
        monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: False)
        captured = {}

        def _fake_respond(text, history=None, **kw):
            captured["text"] = text
            return {"reply": "تم", "status": "completed",
                    "tools_used": [], "steps": []}

        monkeypatch.setattr(chat_agent, "respond", _fake_respond)
        with _client() as c:
            body = c.post("/chat", json={
                "text": "هل هو جاهز للانتاج ؟", "user_id": "t",
                "history": [_REPO_TURN]}).json()
        assert body["status"] == "ok"
        assert "github.com/vooovg-ui/AMOS-Fedration" in captured["text"]
        assert captured["text"] != "هل هو جاهز للانتاج ؟"

    def test_agent_receives_raw_when_not_followup(self, monkeypatch):
        """رسالة مكتملة بذاتها تصل الوكيل كما هي — لا تغيير لغير المتابعة."""
        monkeypatch.setattr(chat_agent, "brain_enabled", lambda: True)
        monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: False)
        captured = {}

        def _fake_respond(text, history=None, **kw):
            captured["text"] = text
            return {"reply": "تم", "status": "completed",
                    "tools_used": [], "steps": []}

        monkeypatch.setattr(chat_agent, "respond", _fake_respond)
        with _client() as c:
            c.post("/chat", json={"text": "ما عاصمة اليابان", "user_id": "t"}).json()
        assert captured["text"] == "ما عاصمة اليابان"


class TestChatBudgetScalesForCloud:
    """ميزانية المحادثة الوكيلة تتسع لخطوات المخطط السحابي (مزلاج مفتوح)."""

    def _fake_loop(self, captured):
        import agent_loop as loop_mod

        class _FakeLoop:
            def __init__(self, registry, planner, max_steps=0,
                         max_seconds=0.0, **kw):
                captured.update(max_steps=max_steps, max_seconds=max_seconds)

            def run(self, text):
                return {"run_id": "t", "goal": text, "status": "completed",
                        "steps": [], "answer": "تم"}

        return loop_mod, _FakeLoop

    def test_budget_scaled_when_latch_open(self, monkeypatch):
        """المزلاج مفتوح (السحابي سيخطط) ⇒ الميزانية ≥ 75ث لكل خطوة."""
        captured = {}
        loop_mod, fake = self._fake_loop(captured)
        monkeypatch.setattr(loop_mod, "AgentLoop", fake)
        monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: True)
        out = chat_agent.respond("سؤال", chat_fn=lambda *a, **k: "تم")
        assert out["reply"] == "تم"
        assert captured["max_seconds"] >= 75.0 * chat_agent.MAX_STEPS

    def test_budget_default_when_brain_reachable(self, monkeypatch):
        """العقل الأساسي سليم (المزلاج مغلق) ⇒ الميزانية الافتراضية كما هي."""
        captured = {}
        loop_mod, fake = self._fake_loop(captured)
        monkeypatch.setattr(loop_mod, "AgentLoop", fake)
        monkeypatch.setattr(ollama_client, "_brain_latch_open", lambda *a, **k: False)
        chat_agent.respond("سؤال", chat_fn=lambda *a, **k: "تم")
        assert captured["max_seconds"] == chat_agent.MAX_SECONDS
